# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 AlaVox-lab
#
# Điểm vào HTTP của dịch vụ khai phá quy trình (#314).
#
# Dịch vụ KHÔNG mở cổng ra ngoài mạng của Compose và không tự kiểm danh tính: người gọi duy nhất là
# dịch vụ ứng dụng, nơi đã kiểm vai trò và gắn phạm vi phòng như bảng điều khiển (#305) rồi mới gọi
# sang đây. Dịch vụ này tắt thì phần còn lại của hệ thống vẫn chạy; chỉ màn quy trình thực tế báo
# không phản hồi.
#
#   GET  /health    — {service, status}; 503 khi không đọc được cơ sở dữ liệu
#   POST /khai-pha  — {from, to, departments|null} → kết quả của app/phan_tich.py

from __future__ import annotations

import datetime as dt
import logging

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field, model_validator

from .bo_may import chon_bo_may
from .cau_hinh import cau_hinh
from .du_lieu import doc_du_lieu, mo_ket_noi
from .phan_tich import phan_tich

log = logging.getLogger("dxlab.khai_pha")

app = FastAPI(title="Corelens — Dịch vụ khai phá quy trình", version="0.11.0")

# Chọn bộ máy một lần lúc khởi động: cấu hình sai thì dịch vụ không lên, thay vì hỏng ở lượt gọi đầu.
# Nạp PM4Py mất vài giây — trả lúc khởi động, không trả ở yêu cầu của người dùng.
BO_MAY = chon_bo_may(cau_hinh().bo_may)

# Khoảng dài nhất một lần khai phá: chặn lượt gọi nhầm đọc cả lịch sử nhiều năm
SO_NGAY_TOI_DA = 366


class YeuCau(BaseModel):
    tu: dt.date = Field(alias="from")
    den: dt.date = Field(alias="to")
    # Mã phòng ban dịch vụ ứng dụng đã đối chiếu với bảng; None là toàn công ty
    departments: list[str] | None = None
    # Mã quy trình (#376); None là quy trình mặc định của ứng dụng. Mỗi lần khai phá đúng một quy trình
    process: str | None = None

    @model_validator(mode="after")
    def _khoang_hop_le(self) -> "YeuCau":
        if self.den < self.tu:
            raise ValueError("Ngày kết thúc phải sau ngày bắt đầu.")
        if (self.den - self.tu).days >= SO_NGAY_TOI_DA:
            raise ValueError(f"Khoảng ngày tối đa {SO_NGAY_TOI_DA} ngày.")
        return self


@app.get("/health")
def suc_khoe(response: Response) -> dict:
    try:
        with mo_ket_noi(cau_hinh().database_uri) as ket_noi:
            ket_noi.execute("SELECT 1 FROM bao_cao_nhat_ky LIMIT 1")
        trang_thai = "ok"
    except Exception as loi:  # noqa: BLE001
        log.warning("Không đọc được cơ sở dữ liệu: %s", loi)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        trang_thai = "degraded"
    return {"service": "dx-os-lab-khai-pha", "status": trang_thai, "engine": BO_MAY.ten}


@app.post("/khai-pha")
def khai_pha(yeu_cau: YeuCau) -> dict:
    try:
        with mo_ket_noi(cau_hinh().database_uri) as ket_noi:
            du_lieu = doc_du_lieu(ket_noi, yeu_cau.tu, yeu_cau.den, yeu_cau.departments, yeu_cau.process)
    except Exception as loi:  # noqa: BLE001
        log.exception("Không đọc được nhật ký sự kiện")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Không đọc được nhật ký sự kiện.") from loi
    ket_qua = phan_tich(du_lieu, BO_MAY, cau_hinh())
    return {
        "range": {"from": yeu_cau.tu.isoformat(), "to": yeu_cau.den.isoformat()},
        "departments": yeu_cau.departments,
        "process": yeu_cau.process,
        **ket_qua,
    }
