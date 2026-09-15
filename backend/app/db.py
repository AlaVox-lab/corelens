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

    Lưu ý quan trọng cho #62 và về sau: mười một bảng cấu hình của engine máy trạng
    thái KHÔNG khai báo ở đây. Chúng do infra/postgres/init/02-luoc-do-quy-trinh.sql
    tạo lúc khởi tạo thực thể, và Alembic được cấu hình bỏ qua chúng — xem
    alembic/env.py. Khai lại ở đây sẽ tạo ra hai nơi cùng sở hữu lược đồ.
    """


def get_session() -> Iterator[Session]:
    """Phụ thuộc của FastAPI: mở một phiên cho mỗi yêu cầu rồi đóng lại."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
