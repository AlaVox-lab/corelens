# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Lối vào màn quy trình thực tế (#314): dịch vụ ứng dụng kiểm vai trò, gắn phạm vi phòng, rồi hỏi
# dịch vụ khai phá quy trình qua HTTP.
#
# Phạm vi xem dùng ĐÚNG hàm của bảng điều khiển (#305, `pham_vi_cua`): `roles.report_scope` quyết ai
# xem được và tới đâu — trưởng phòng thấy phòng mình, điều phối viên và quản trị viên thấy toàn công
# ty, người gửi không thấy. Danh sách phòng gửi đi đã đối chiếu với bảng `departments`, không chuỗi nào
# từ token đi thẳng sang dịch vụ khai phá.
#
# Trang hồ sơ phía nhân viên hỏi thêm kết quả tuân thủ của MỘT hồ sơ (#448): cùng luật xem với trang hồ
# sơ, trừ người gửi; dịch vụ khai phá tắt hay hỏng thì chỉ là "không có", không bao giờ là lỗi.
#
# Dịch vụ này không bao giờ nhập thư viện khai phá (ADR-0007): chỉ trao đổi JSON qua HTTP, nên giấy
# phép AGPL của thư viện dừng ở ranh giới dịch vụ khai phá.

from __future__ import annotations

import datetime as dt
import json
import logging
import urllib.error
import urllib.request
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.bang_dieu_khien import pham_vi_cua
from app.auth.dependencies import current_actor
from app.config import get_settings
from app.db import get_session
from app.intelligence import khuyen_nghi
from app.models.case import EventLog, Request
from app.models.workflow_config import Department, RequestType
from app.workflow.context import Actor
from app.workflow.coordination import vao_duoc_buong_lai
from app.workflow.department import vao_duoc_phong_ban
from app.workflow.routes import _ma_ho_so

log = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Khai phá quy trình"])

# Khoảng dài nhất một lần khai phá — cùng giới hạn với dịch vụ khai phá
SO_NGAY_TOI_DA = 366


class KhaiPhaKhongPhanHoi(Exception):
    """Dịch vụ khai phá tắt, quá thời hạn chờ, hay trả lỗi — cổng hiện màn không phản hồi."""


class KhaiPhaClient:
    """Gọi dịch vụ khai phá trong mạng của Compose."""

    def khai_pha(self, tu: dt.date, den: dt.date, phong: list[str] | None) -> dict:
        cau_hinh = get_settings()
        than = json.dumps({"from": tu.isoformat(), "to": den.isoformat(), "departments": phong}).encode()
        yeu_cau = urllib.request.Request(
            cau_hinh.mining_url.rstrip("/") + "/khai-pha",
            data=than,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._doc(yeu_cau)

    def tuan_thu(self, case_id: int) -> dict:
        """Bước lệch của một hồ sơ (#448). Hồ sơ không có trong nhật ký thì dịch vụ trả 404 — cũng là
        `KhaiPhaKhongPhanHoi`: với trang hồ sơ, hai trường hợp đều là "không có gì để nói"."""
        dia_chi = get_settings().mining_url.rstrip("/") + f"/ho-so/{int(case_id)}/tuan-thu"
        return self._doc(urllib.request.Request(dia_chi, method="GET"))

    @staticmethod
    def _doc(yeu_cau: urllib.request.Request) -> dict:
        try:
            with urllib.request.urlopen(yeu_cau, timeout=get_settings().mining_timeout_seconds) as phan_hoi:
                return json.loads(phan_hoi.read())
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as loi:
            raise KhaiPhaKhongPhanHoi(str(loi)) from loi


_may_khach: KhaiPhaClient | None = None


def khai_pha_client() -> KhaiPhaClient:
    """Phụ thuộc thay được trong bài kiểm thử, như Superset ở bảng điều khiển."""
    global _may_khach
    if _may_khach is None:
        _may_khach = KhaiPhaClient()
    return _may_khach


@router.get("/process-mining")
def quy_trinh_thuc_te(
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[Actor, Depends(current_actor)],
    may_khach: Annotated[KhaiPhaClient, Depends(khai_pha_client)],
    tu: Annotated[dt.date, Query(alias="from", description="Ngày bắt đầu, hồ sơ gửi từ ngày này")],
    den: Annotated[dt.date, Query(alias="to", description="Ngày kết thúc, tính cả ngày này")],
) -> dict:
    """Quy trình thực tế của các hồ sơ gửi trong khoảng ngày, lọc theo phạm vi của người gọi.

    403 khi vai trò của người gọi không được xem báo cáo; 422 khi khoảng ngày sai; 503 khi dịch vụ khai
    phá không phản hồi. Trả kèm phạm vi đã áp, để giao diện ghi rõ người xem đang thấy tới đâu.
    """
    return _khai_pha_trong_pham_vi(session, actor, may_khach, tu, den)[0]


@router.get("/process-mining/recommendation")
def khuyen_nghi_cai_tien(
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[Actor, Depends(current_actor)],
    may_khach: Annotated[KhaiPhaClient, Depends(khai_pha_client)],
    tu: Annotated[dt.date, Query(alias="from", description="Ngày bắt đầu, hồ sơ gửi từ ngày này")],
    den: Annotated[dt.date, Query(alias="to", description="Ngày kết thúc, tính cả ngày này")],
) -> dict:
    """Khuyến nghị cải tiến bằng câu chữ cho cùng khoảng ngày và phạm vi (#320) — gợi ý của hệ thống,
    chỉ để đọc. Cùng cửa quyền và cùng mã lỗi với `/process-mining`. `status`: `ready` (kèm câu đã qua
    phép kiểm số), `pending` (đang sinh ở nền — hỏi lại sau), `disabled` (mô hình tắt), `unavailable`
    (mô hình không trả lời), `no-data`. Không bao giờ chờ mô hình."""
    ket_qua, phong = _khai_pha_trong_pham_vi(session, actor, may_khach, tu, den)
    kn, tu_dem = khuyen_nghi.lay(tu, den, phong, ket_qua)
    return {
        "status": kn.status,
        "sentences": list(kn.sentences),
        "dropped_wrong_number": kn.dropped_wrong_number,
        "dropped_no_number": kn.dropped_no_number,
        "model": kn.model,
        "generated_at": kn.generated_at.isoformat() if kn.generated_at else None,
        "cached": tu_dem,
    }


def _xem_duoc_tuan_thu(session: Session, ho_so: Request | None, actor: Actor) -> bool:
    """Đúng luật xem hồ sơ của hai trang hồ sơ phía nhân viên — điều phối viên xem mọi hồ sơ, nhân viên
    phòng ban xem hồ sơ của phòng mình (như `mo_duoc_ho_so` của tệp đính kèm) — TRỪ luật người gửi xem
    hồ sơ của mình: kết quả tuân thủ là thông tin vận hành nội bộ, như căn cứ gợi ý ở #504."""
    if ho_so is None:
        return False
    if vao_duoc_buong_lai(actor):
        return True
    return vao_duoc_phong_ban(session, actor) and ho_so.department_code in actor.departments


@router.get("/process-mining/cases/{case_id}")
def tuan_thu_ho_so(
    case_id: int,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[Actor, Depends(current_actor)],
    may_khach: Annotated[KhaiPhaClient, Depends(khai_pha_client)],
) -> dict:
    """Hồ sơ này có đi lệch quy trình thiết kế không, lệch ở bước nào (#448) — chỉ để thông tin.

    Định nghĩa lệch là đúng định nghĩa nhánh lệch của màn quy trình thực tế (dịch vụ khai phá, hàm
    `buoc_lech`). 403 cho người không vào được buồng lái nào (vai người gửi); 404 cho hồ sơ không có hay
    ngoài phạm vi, như trang hồ sơ. KHÔNG BAO GIỜ báo lỗi vì dịch vụ khai phá: `status` là `ready` (kèm
    bước lệch), `disabled` (không cấu hình địa chỉ dịch vụ khai phá) hay `unavailable` (không trả lời,
    hay nhật ký chưa có hồ sơ) — trang hồ sơ khi đó y như trước. Không ghi gì, không đổi trạng thái."""
    if not (vao_duoc_buong_lai(actor) or vao_duoc_phong_ban(session, actor)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "conformance-forbidden",
                    "message": "Tài khoản này không xem được kết quả tuân thủ quy trình."},
        )
    ho_so = session.get(Request, case_id)
    if not _xem_duoc_tuan_thu(session, ho_so, actor):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "case-not-found", "message": "Không tìm thấy hồ sơ."},
        )
    rong = {"case_id": case_id, "deviates": False, "steps": []}
    if not get_settings().mining_url:
        return {"status": "disabled", **rong}
    try:
        ket_qua = may_khach.tuan_thu(case_id)
        buoc = [dict(b) for b in ket_qua["steps"]]
    except (KhaiPhaKhongPhanHoi, KeyError, TypeError, ValueError) as loi:
        log.info("Không có kết quả tuân thủ cho hồ sơ %s: %s", case_id, loi)
        return {"status": "unavailable", **rong}
    # Tên người thực hiện như nhật ký ghi lúc thao tác — dịch vụ khai phá chỉ có định danh
    ten = {
        a: nhan for a, nhan in session.execute(
            select(EventLog.actor, EventLog.actor_label)
            .where(EventLog.case_id == case_id, EventLog.actor_label.is_not(None))
            .order_by(EventLog.id)
        ).all()
    }
    for b in buoc:
        b["actor_label"] = ten.get(b.get("actor"))
    return {"status": "ready", "case_id": case_id, "deviates": bool(buoc), "steps": buoc}


def _khai_pha_trong_pham_vi(
    session: Session, actor: Actor, may_khach: KhaiPhaClient, tu: dt.date, den: dt.date
) -> tuple[dict, list[str] | None]:
    """Kết quả khai phá đã gắn phạm vi, nhãn và mã hiển thị, kèm danh sách phòng đã áp."""
    pham_vi = pham_vi_cua(session, actor)
    if pham_vi is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "reports-forbidden",
                    "message": "Tài khoản này không xem được quy trình thực tế."},
        )
    if den < tu or (den - tu).days >= SO_NGAY_TOI_DA:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid-range",
                    "message": f"Khoảng ngày phải hợp lệ và không quá {SO_NGAY_TOI_DA} ngày."},
        )
    phong = None if pham_vi.toan_cong_ty else [p.code for p in pham_vi.phong]
    try:
        ket_qua = may_khach.khai_pha(tu, den, phong)
    except KhaiPhaKhongPhanHoi as loi:
        log.warning("Dịch vụ khai phá không phản hồi: %s", loi)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "mining-unavailable",
                    "message": "Dịch vụ khai phá quy trình không phản hồi."},
        ) from loi
    return {
        **ket_qua,
        "scope": {
            "all": pham_vi.toan_cong_ty,
            "departments": [{"code": p.code, "label": p.label} for p in pham_vi.phong],
        },
        "labels": nhan_nhom(session),
        "case_codes": ma_hien_thi(session, ket_qua),
    }, phong


def ma_hien_thi(session: Session, ket_qua: dict) -> dict[str, str]:
    """Mã hiển thị (`YC-2026-0184`) của mọi hồ sơ mà kết quả nêu tên (#315): danh sách nhánh lệch, hồ
    sơ chờ lâu nhất, biến thể. Dựng bằng đúng hàm của trang hồ sơ, để màn quy trình thực tế và trang hồ
    sơ gọi một hồ sơ cùng một tên. Mã chỉ lấy từ kết quả trong phạm vi, nên không lộ hồ sơ ngoài phạm vi.
    Khóa JSON là chuỗi."""
    ma: set[int] = set()
    for d in ket_qua.get("deviations", []):
        ma.update(d.get("cases", []))
    for t in ket_qua.get("states", []):
        ma.update(c["case"] for c in t.get("longest_waits", []))
    for v in ket_qua.get("variants", []):
        ma.update(v.get("cases", []))
    if not ma:
        return {}
    return {str(h.id): _ma_ho_so(h) for h in session.scalars(select(Request).where(Request.id.in_(ma)))}


def nhan_nhom(session: Session) -> dict[str, dict[str, str]]:
    """Nhãn của loại yêu cầu và phòng ban mà kết quả khai phá tách nhóm theo mã (#315).

    Dịch vụ khai phá chỉ trả mã: tài khoản chỉ đọc của nó không cần quyền đọc thêm hai bảng danh mục.
    Lấy cả mục đã ngừng dùng, vì hồ sơ cũ trong khoảng ngày vẫn có thể mang mã đó.
    """
    return {
        "request_types": dict(session.execute(select(RequestType.code, RequestType.label)).all()),
        "departments": dict(session.execute(select(Department.code, Department.label)).all()),
    }
