# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Bảng điều khiển phân tích nhúng trong cổng (#305): cấp token khách của Superset cho đúng
# người đang xem, kèm điều kiện lọc theo phòng.
#
# Người xem không đăng nhập Superset. Cổng hỏi điểm cuối này; dịch vụ kiểm vai trò bằng token
# Keycloak như mọi điểm cuối khác, rồi thay mặt người xem xin Superset một token khách ngắn hạn
# (`GUEST_TOKEN_JWT_EXP_SECONDS` bên Superset). Token chỉ mở đúng một dashboard, và mang điều
# kiện lọc theo dòng (RLS) mà Superset gắn vào MỌI câu truy vấn của dashboard đó — trình duyệt
# có sửa gì cũng không nới được, vì token do Superset ký.
#
# Ai xem được và xem tới đâu là cột `roles.report_scope` (migration 0015), không phải tên vai trò
# trong mã: `all` là toàn công ty, `department` là phòng của chính người xem (claim `groups`).
# Mang nhiều vai trò thì lấy phạm vi rộng nhất — điều phối viên kiêm trưởng phòng thấy toàn
# công ty.
#
# Gọi Superset bằng thư viện chuẩn như danh bạ Keycloak (`app/auth/directory.py`), không thêm
# thư viện HTTP. API của Superset đòi phiên cookie + mã CSRF cho mọi lệnh ghi, kể cả xin token
# khách, nên mỗi lần xin là một phiên ngắn: đăng nhập → lấy mã CSRF → xin token.

from __future__ import annotations

import http.cookiejar
import json
import logging
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor
from app.config import get_settings
from app.db import get_session
from app.models.workflow_config import Department, Role
from app.workflow.context import Actor

log = logging.getLogger(__name__)

# Mọi view `bao_cao_*` mà dashboard đọc đều mang cột này (migration 0014). Đây là tên cột trong
# lược đồ của chính dự án, không phải giá trị nghiệp vụ: giá trị lọc vẫn là mã phòng tra từ bảng.
COT_PHONG = "ma_phong"

PHAM_VI_TOAN_CONG_TY = "all"
PHAM_VI_PHONG = "department"

router = APIRouter(prefix="/analytics", tags=["Bảng điều khiển phân tích"])


@dataclass(frozen=True, slots=True)
class PhamVi:
    """Người xem thấy tới đâu. `phong` rỗng khi thấy toàn công ty."""

    toan_cong_ty: bool
    phong: tuple[Department, ...] = ()


def pham_vi_cua(session: Session, actor: Actor) -> PhamVi | None:
    """Phạm vi xem bảng điều khiển của người này, `None` khi không được xem.

    Trưởng phòng chưa thuộc phòng nào (thiếu nhóm trong Keycloak) cũng là `None`: không có
    phòng thì không có gì để lọc, và một dashboard trống trơn chỉ làm người xem tưởng hệ thống
    hỏng. Mã phòng trong token đối chiếu với bảng `departments` — giá trị lạ bị bỏ, nên không
    chuỗi nào từ token đi thẳng vào điều kiện lọc.
    """
    if not actor.roles:
        return None
    cac_pham_vi = set(
        session.scalars(
            select(Role.report_scope).where(
                Role.code.in_(actor.roles), Role.report_scope.is_not(None)
            )
        )
    )
    if PHAM_VI_TOAN_CONG_TY in cac_pham_vi:
        return PhamVi(toan_cong_ty=True)
    if PHAM_VI_PHONG in cac_pham_vi and actor.departments:
        phong = tuple(
            session.scalars(
                select(Department)
                .where(Department.code.in_(actor.departments))
                .order_by(Department.display_order, Department.code)
            )
        )
        if phong:
            return PhamVi(toan_cong_ty=False, phong=phong)
    return None


def dieu_kien_loc(pham_vi: PhamVi) -> list[dict[str, str]]:
    """Điều kiện lọc theo dòng gửi kèm yêu cầu token khách. Toàn công ty thì không lọc."""
    if pham_vi.toan_cong_ty:
        return []
    # Mã phòng đã đối chiếu với bảng; vẫn nhân đôi dấu nháy để mệnh đề luôn là chuỗi SQL hợp lệ
    gia_tri = ", ".join("'" + p.code.replace("'", "''") + "'" for p in pham_vi.phong)
    return [{"clause": f"{COT_PHONG} IN ({gia_tri})"}]


class SupersetKhongPhanHoi(Exception):
    """Superset tắt, quá thời hạn chờ, hay trả lỗi — cổng hiện màn không phản hồi."""


class SupersetClient:
    """Phiên làm việc với API của Superset bằng tài khoản quản trị."""

    def __init__(self) -> None:
        cau_hinh = get_settings()
        self._goc = cau_hinh.superset_internal_url.rstrip("/")
        self._tai_khoan = (cau_hinh.superset_admin_user, cau_hinh.superset_admin_password)
        self._slug = cau_hinh.superset_dashboard_slug
        self._mien_nhung = cau_hinh.portal_public_url.rstrip("/")
        self._tran_giay = cau_hinh.superset_timeout_seconds
        # Mã nhúng của dashboard đổi chỉ khi cấu hình nhúng bị xóa, nên nhớ trong tiến trình
        self._ma_nhung: str | None = None
        self._khoa = threading.Lock()

    def _goi(self, mo: urllib.request.OpenerDirector, phuong: str, duong: str,
             du_lieu: Any = None, tieu_de: dict[str, str] | None = None) -> Any:
        yeu_cau = urllib.request.Request(
            self._goc + duong,
            data=None if du_lieu is None else json.dumps(du_lieu).encode("utf-8"),
            headers={"Content-Type": "application/json", "Referer": self._goc, **(tieu_de or {})},
            method=phuong,
        )
        try:
            with mo.open(yeu_cau, timeout=self._tran_giay) as phan_hoi:
                return json.loads(phan_hoi.read() or b"null")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as loi:
            raise SupersetKhongPhanHoi(f"{phuong} {duong}: {loi}") from loi

    def _phien(self) -> tuple[urllib.request.OpenerDirector, dict[str, str]]:
        mo = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        ten, mat_khau = self._tai_khoan
        dang_nhap = self._goi(mo, "POST", "/api/v1/security/login",
                              {"username": ten, "password": mat_khau, "provider": "db"})
        tieu_de = {"Authorization": f"Bearer {dang_nhap['access_token']}"}
        csrf = self._goi(mo, "GET", "/api/v1/security/csrf_token/", tieu_de=tieu_de)
        return mo, {**tieu_de, "X-CSRFToken": csrf["result"]}

    def _bat_nhung(self, mo: urllib.request.OpenerDirector, tieu_de: dict[str, str]) -> str:
        # Tạo hoặc cập nhật cấu hình nhúng — Superset giữ nguyên mã nhúng nếu đã có. Cấu hình này
        # nằm trong cơ sở dữ liệu của Superset, không xuất được ra tệp YAML, nên dịch vụ tự bật ở
        # lần xin đầu tiên thay vì bắt người dựng cụm bấm tay
        kq = self._goi(mo, "POST", f"/api/v1/dashboard/{self._slug}/embedded",
                       {"allowed_domains": [self._mien_nhung]}, tieu_de)
        return kq["result"]["uuid"]

    def xin_token(self, actor: Actor, loc: list[dict[str, str]]) -> tuple[str, str]:
        """Token khách cho một người xem, cùng mã nhúng của dashboard."""
        with self._khoa:
            mo, tieu_de = self._phien()
            if self._ma_nhung is None:
                self._ma_nhung = self._bat_nhung(mo, tieu_de)
            ma_nhung = self._ma_nhung
        try:
            kq = self._goi(mo, "POST", "/api/v1/security/guest_token/", {
                "user": {"username": actor.id, "first_name": actor.label, "last_name": ""},
                "resources": [{"type": "dashboard", "id": ma_nhung}],
                "rls": loc,
            }, tieu_de)
        except SupersetKhongPhanHoi:
            # Cấu hình nhúng có thể vừa bị xóa trên giao diện Superset: lần sau bật lại từ đầu
            self._ma_nhung = None
            raise
        return kq["token"], ma_nhung


_may_khach: SupersetClient | None = None


def superset_client() -> SupersetClient:
    """Một máy khách cho cả tiến trình, để nhớ được mã nhúng. Bài kiểm thử thay bằng bản giả."""
    global _may_khach
    if _may_khach is None:
        _may_khach = SupersetClient()
    return _may_khach


@router.post("/dashboard/guest-token")
def cap_token_khach(
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[Actor, Depends(current_actor)],
    may_khach: Annotated[SupersetClient, Depends(superset_client)],
) -> dict:
    """Token khách để cổng nhúng bảng điều khiển phân tích, lọc theo phạm vi của người gọi.

    403 khi vai trò của người gọi không được xem bảng điều khiển; 503 khi Superset không phản
    hồi. Trả kèm địa chỉ công khai của Superset và mã nhúng, để giao diện không giữ cấu hình.
    """
    pham_vi = pham_vi_cua(session, actor)
    if pham_vi is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "reports-forbidden",
                    "message": "Tài khoản này không xem được bảng điều khiển phân tích."},
        )
    try:
        token, ma_nhung = may_khach.xin_token(actor, dieu_kien_loc(pham_vi))
    except SupersetKhongPhanHoi as loi:
        log.warning("Không xin được token khách của Superset: %s", loi)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "reports-unavailable",
                    "message": "Nền tảng báo cáo không phản hồi."},
        ) from loi
    return {
        "token": token,
        "dashboard_id": ma_nhung,
        "superset_url": get_settings().superset_public_url.rstrip("/"),
        "scope": {
            "all": pham_vi.toan_cong_ty,
            "departments": [{"code": p.code, "label": p.label} for p in pham_vi.phong],
        },
    }
