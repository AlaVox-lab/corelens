# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Cấu hình dịch vụ ứng dụng, đọc từ biến môi trường.
#
# Không có giá trị nghiệp vụ nào ở đây. Trạng thái, vai trò, phòng ban, ngưỡng SLA
# đều nằm trong bảng dữ liệu — xem ARCHITECTURE.md mục 5. Tệp này chỉ giữ những thứ
# thuộc môi trường triển khai: chuỗi kết nối, cổng, mức ghi nhật ký.

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cấu hình đọc từ biến môi trường mang tiền tố DXLAB_."""

    model_config = SettingsConfigDict(
        env_prefix="DXLAB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Chuỗi kết nối đầy đủ, dựng sẵn trong docker-compose.yml từ các biến rời rạc.
    # Dùng psycopg 3: tiền tố là postgresql+psycopg, không phải postgresql+psycopg2.
    database_uri: str = "postgresql+psycopg://dxlab:dxlab@localhost:5432/dxlab"

    # Nhãn hiển thị trong tài liệu API tự sinh
    app_name: str = "DX-OS Lab — Cổng vận hành yêu cầu nội bộ"
    app_version: str = "0.3.0"

    # Bật chế độ gỡ lỗi của SQLAlchemy. Không bao giờ bật ở bản triển khai thật.
    database_echo: bool = False


@lru_cache
def get_settings() -> Settings:
    """Đọc cấu hình đúng một lần cho cả vòng đời tiến trình."""
    return Settings()
