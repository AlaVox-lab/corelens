# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Mở lại có giới hạn và hồ sơ tạo lại (#102).
#
# Mã bản sửa    : 0011_mo_lai_co_gioi_han
# Sửa đổi từ    : 0010_gia_han_xu_ly
#
# Giảng viên chốt ngày 08/10: người gửi mở lại hồ sơ trong 7 ngày làm việc kể từ khi đóng,
# mỗi lần có lý do, tối đa 2 lần; quá số lần thì tạo hồ sơ mới liên kết hồ sơ cũ. Hai cột
# trên hồ sơ:
#
#   reopen_count       đã mở lại mấy lần — ràng buộc `reopen-limit` đếm theo cột này
#   parent_request_id  hồ sơ này được tạo lại từ hồ sơ nào — chỉ đặt lúc tạo
#
# `reopen_count` do ràng buộc tự đặt, người dùng không gửi được. Ngưỡng 2 lần nằm ở
# `request_types.reopen_max_count` (lược đồ khởi tạo), cửa sổ 7 ngày ở
# `transitions.reopen_window_hours` — dữ liệu, không phải cột ở đây.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_mo_lai_co_gioi_han"
down_revision: str | None = "0010_gia_han_xu_ly"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "requests",
        sa.Column("reopen_count", sa.SmallInteger(), server_default="0", nullable=False),
    )
    op.add_column(
        "requests",
        sa.Column("parent_request_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "requests_ho_so_goc_fkey", "requests", "requests", ["parent_request_id"], ["id"]
    )
    op.create_index("requests_tra_theo_ho_so_goc", "requests", ["parent_request_id"])
    op.create_check_constraint(
        "requests_mo_lai_khong_am", "requests", "reopen_count >= 0"
    )
    # Hồ sơ không tự là hồ sơ gốc của chính nó
    op.create_check_constraint(
        "requests_ho_so_goc_khac_chinh_no",
        "requests",
        "parent_request_id IS NULL OR parent_request_id <> id",
    )


def downgrade() -> None:
    op.drop_constraint("requests_ho_so_goc_khac_chinh_no", "requests", type_="check")
    op.drop_constraint("requests_mo_lai_khong_am", "requests", type_="check")
    op.drop_index("requests_tra_theo_ho_so_goc", table_name="requests")
    op.drop_constraint("requests_ho_so_goc_fkey", "requests", type_="foreignkey")
    op.drop_column("requests", "parent_request_id")
    op.drop_column("requests", "reopen_count")
