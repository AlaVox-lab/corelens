# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Môi trường chạy migration của Alembic.
#
# Vì sao mọi chú thích của dự án nằm ở đây mà không nằm trong alembic.ini: Alembic đọc
# tệp ini qua configparser với mã hóa cục bộ của hệ điều hành. Trên Windows đó là
# cp1252, nên một chữ tiếng Việt có dấu trong alembic.ini làm mọi lệnh alembic chết
# ngay lúc khởi động. Trong container thì không lộ ra vì Linux dùng UTF-8 — lỗi chỉ
# đánh vào máy thành viên. Tệp .py thì Python luôn đọc UTF-8 nên an toàn.

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db import Base

# Nhập để mọi mô hình tự đăng ký vào Base.metadata. Thiếu dòng này thì autogenerate
# nhìn thấy metadata rỗng và sinh ra migration xóa sạch bảng.
import app.models  # noqa: F401  (nhập vì tác dụng phụ, không dùng trực tiếp)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Chuỗi kết nối lấy từ biến môi trường, không ghi trong alembic.ini. Lý do: alembic.ini
# nằm trong kho mã, còn mật khẩu thì không bao giờ được nằm trong kho mã.
config.set_main_option("sqlalchemy.url", get_settings().database_uri)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# HÀNG RÀO QUAN TRỌNG NHẤT CỦA TỆP NÀY
# ---------------------------------------------------------------------------
# Các bảng cấu hình của engine máy trạng thái viết bằng SQL thô trong bản sửa gốc
# 0000_luoc_do_cau_hinh (#254; trước đó do lược đồ khởi tạo của PostgreSQL tạo). Mô hình
# SQLAlchemy chỉ khai một phần cột của vài bảng trong số đó, để đọc.
#
# Không có hàng rào này thì `alembic revision --autogenerate` thấy bảng trong cơ sở dữ
# liệu mà không thấy (hay thấy thiếu cột) trong target_metadata, và sinh ra một migration
# DROP sạch cấu hình quy trình. Đổi bảng cấu hình thì viết bản sửa bằng tay.
#
# Thêm bảng cấu hình mới vào danh sách này.
TABLES_OWNED_BY_INIT_SQL = frozenset(
    {
        "rule_sets",
        "roles",
        "states",
        "transitions",
        "transition_roles",
        "guards",
        "transition_guards",
        "departments",
        "request_types",
        "request_type_routing",
        "priorities",
        # Loại lời nhắn trên hồ sơ (#128) — bản thân lời nhắn thì Alembic sở hữu
        "message_kinds",
        "message_kind_roles",
        # Bốn bảng thêm sau mà danh sách từng bỏ sót (#250, #199)
        "request_type_fields",
        "work_calendars",
        "work_hours",
        "holidays",
    }
)


def include_object(object_, name, type_, reflected, compare_to) -> bool:
    """Giấu các bảng thuộc sở hữu của lược đồ khởi tạo khỏi mắt Alembic."""
    if type_ == "table" and name in TABLES_OWNED_BY_INIT_SQL:
        return False
    return True


def run_migrations_offline() -> None:
    """Sinh câu lệnh SQL ra màn hình thay vì chạy thẳng vào cơ sở dữ liệu."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Chạy migration trực tiếp trên kết nối thật."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
