# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kết nối cơ sở dữ liệu dùng chung cho toàn dịch vụ.

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

_settings = get_settings()

# pool_pre_ping bắt kết nối đã chết trước khi dùng. Cần thiết vì PostgreSQL trong
# cụm Docker có thể khởi động lại độc lập với dịch vụ ứng dụng.
engine = create_engine(
    _settings.database_uri,
    echo=_settings.database_echo,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Lớp gốc cho mọi mô hình dữ liệu.

    Lưu ý quan trọng cho #62 và về sau: lược đồ các bảng cấu hình của engine máy trạng
    thái KHÔNG sinh từ đây. Chúng viết bằng SQL thô trong bản sửa gốc
    alembic/versions/0000_luoc_do_cau_hinh.py (#254), và autogenerate được cấu hình bỏ
    qua chúng — xem alembic/env.py. Mô hình trong app/models/workflow_config.py chỉ để đọc.
    """


def get_session() -> Iterator[Session]:
    """Phụ thuộc của FastAPI: mở một phiên cho mỗi yêu cầu rồi đóng lại."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
