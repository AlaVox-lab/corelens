# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Điểm vào của dịch vụ ứng dụng.
#
# Bộ khung, chưa có nghiệp vụ. Máy trạng thái thuộc #41, đăng nhập thuộc #43, cổng
# gửi yêu cầu thuộc #44. Tệp này chỉ dựng ứng dụng và một điểm cuối kiểm tra sức khỏe.

from fastapi import Depends, FastAPI, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Dịch vụ ứng dụng của DX-OS Lab. Toàn bộ quy trình nghiệp vụ nằm trong bảng "
        "dữ liệu, không mã cứng trong mã nguồn."
    ),
)


@app.get("/health", tags=["Vận hành"])
def health(response: Response, session: Session = Depends(get_session)) -> dict:
    """Báo trạng thái dịch vụ và kết nối cơ sở dữ liệu.

    Trả về 503 khi cơ sở dữ liệu không dùng được. Điểm này quan trọng: một điểm cuối
    kiểm tra sức khỏe luôn trả 200 thì vô dụng. Nhóm đã vấp đúng bẫy đó với Apache
    Superset ở #38 — container báo `healthy` trong khi không ai đăng nhập được.
    """
    thong_tin: dict = {
        "service": "dx-os-lab-backend",
        "version": settings.app_version,
    }

    try:
        session.execute(text("SELECT 1"))
    except Exception as loi:  # noqa: BLE001 — cần bắt mọi lỗi kết nối để báo 503
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        thong_tin["status"] = "degraded"
        thong_tin["database"] = "unreachable"
        thong_tin["detail"] = str(loi)[:200]
        return thong_tin

    thong_tin["status"] = "ok"
    thong_tin["database"] = "ok"

    # Đếm trạng thái của bộ quy tắc đang kích hoạt. Con số này chứng minh cả chuỗi
    # khởi tạo đã chạy: lược đồ được tạo, dữ liệu khởi tạo được nạp, các phép kiểm
    # tra tính nhất quán đều qua. Bằng không thì cụm dựng lên nhưng rỗng ruột.
    try:
        so_trang_thai = session.execute(
            text(
                "SELECT count(*) FROM states s"
                " JOIN rule_sets r ON r.id = s.rule_set_id"
                " WHERE r.is_active"
            )
        ).scalar_one()
        thong_tin["active_rule_set_states"] = so_trang_thai
    except Exception:  # noqa: BLE001 — lược đồ chưa nạp thì vẫn coi là suy giảm
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        thong_tin["status"] = "degraded"
        thong_tin["detail"] = "Chưa nạp được lược đồ quy trình"

    return thong_tin


@app.get("/", tags=["Vận hành"])
def root() -> dict:
    """Chỉ đường tới tài liệu API tự sinh."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
