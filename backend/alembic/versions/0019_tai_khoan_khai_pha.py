# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Tài khoản cơ sở dữ liệu chỉ đọc riêng của dịch vụ khai phá quy trình (#314, ADR-0007).
#
# Mã bản sửa    : 0019_tai_khoan_khai_pha
# Sửa đổi từ    : 0018_kiem_tra_cau_hinh
#
# Không dùng chung tài khoản chỉ đọc của nền tảng báo cáo: mỗi dịch vụ một tài khoản, quyền vừa đúng
# việc của nó, thu hồi riêng được. Tài khoản chỉ được SELECT đúng các bảng và view mà phép khai phá đọc
# (app/du_lieu.py của services/khai-pha), không có quyền đọc mặc định trên bảng tạo về sau, và phiên
# của nó mặc định chỉ đọc.
#
# Trước #254 việc này phải nằm ở lược đồ khởi tạo và buộc cả nhóm `down -v`. Nay là một bản sửa: cụm
# cũ nâng lên bằng `up -d --build`. Tên và mật khẩu lấy từ biến môi trường của dịch vụ ứng dụng
# (DXLAB_MINING_DB_USER, DXLAB_MINING_DB_PASSWORD), Compose truyền cùng giá trị cho dịch vụ khai phá.
# Đổi mật khẩu về sau: ALTER ROLE bằng tay — bản sửa chỉ chạy một lần.

from collections.abc import Sequence

from alembic import op
from psycopg import sql

from app.config import get_settings

revision: str = "0019_tai_khoan_khai_pha"
down_revision: str | None = "0018_kiem_tra_cau_hinh"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Đúng những gì phép khai phá đọc: lớp báo cáo, cờ trên cạnh và trạng thái, cột changes của nhật ký
# (đếm lần đặt phòng ban), và ba bảng lịch mà hàm so_giay_lam_viec đọc bằng quyền của người gọi
BANG_DUOC_DOC = (
    "bao_cao_nhat_ky",
    "event_log",
    "states",
    "transitions",
    "work_calendars",
    "work_hours",
    "holidays",
)


def upgrade() -> None:
    cau_hinh = get_settings()
    ten, mat_khau = cau_hinh.mining_db_user, cau_hinh.mining_db_password
    if not mat_khau:
        raise RuntimeError(
            "Thiếu DXLAB_MINING_DB_PASSWORD cho tài khoản chỉ đọc của dịch vụ khai phá (#314) — "
            "infra/docker-compose.yml có giá trị mặc định, tệp .env có thể đặt MINING_READONLY_PASSWORD."
        )
    goc = op.get_bind().connection.driver_connection
    nguoi = sql.Identifier(ten)
    da_co = goc.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ten,)).fetchone()
    lenh = "ALTER ROLE {} LOGIN PASSWORD {}" if da_co else "CREATE ROLE {} LOGIN PASSWORD {}"
    goc.execute(sql.SQL(lenh).format(nguoi, sql.Literal(mat_khau)))
    goc.execute(sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(nguoi))
    csdl = goc.execute("SELECT current_database()").fetchone()[0]
    goc.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(csdl), nguoi))
    goc.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(nguoi))
    goc.execute(
        sql.SQL("GRANT SELECT ON {} TO {}").format(
            sql.SQL(", ").join(sql.Identifier(b) for b in BANG_DUOC_DOC), nguoi
        )
    )


def downgrade() -> None:
    goc = op.get_bind().connection.driver_connection
    nguoi = sql.Identifier(get_settings().mining_db_user)
    if goc.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (get_settings().mining_db_user,)).fetchone():
        goc.execute(sql.SQL("REVOKE ALL ON {} FROM {}").format(
            sql.SQL(", ").join(sql.Identifier(b) for b in BANG_DUOC_DOC), nguoi))
        goc.execute(sql.SQL("REVOKE USAGE ON SCHEMA public FROM {}").format(nguoi))
        csdl = goc.execute("SELECT current_database()").fetchone()[0]
        goc.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM {}").format(sql.Identifier(csdl), nguoi))
        goc.execute(sql.SQL("DROP ROLE {}").format(nguoi))
