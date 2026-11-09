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
from sqlalchemy.orm import Session

from app.analytics.bang_dieu_khien import pham_vi_cua
from app.auth.dependencies import current_actor
from app.config import get_settings
from app.db import get_session
from app.workflow.context import Actor

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
        try:
            with urllib.request.urlopen(yeu_cau, timeout=cau_hinh.mining_timeout_seconds) as phan_hoi:
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
    }
