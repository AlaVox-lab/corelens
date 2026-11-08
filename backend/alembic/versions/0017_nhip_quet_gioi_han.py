# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Nhịp của các bộ quét nền và bộ đếm giới hạn tốc độ (#253, #243).
#
# Mã bản sửa    : 0017_nhip_quet_gioi_han
# Sửa đổi từ    : 0016_goi_y_va_ghi_de
#
# `scanner_heartbeats` — một dòng mỗi bộ quét nền: lần chạy cuối, lần thành công cuối, lần lỗi cuối,
# số lỗi liên tiếp, và bản dịch vụ nào đã chạy (tên máy chủ, mã tiến trình). Dịch vụ ứng dụng có thể
# chạy nhiều bản; bản nào giành được khóa tư vấn của PostgreSQL thì quét và ghi dòng này, bản kia bỏ
# lượt. `/health` và màn Hệ thống đọc bảng để biết bộ quét còn sống không.
#
# `rate_limit_hits` — bộ đếm giới hạn tốc độ theo cửa sổ thời gian cố định, mỗi (khóa, mốc đầu cửa
# sổ) một dòng, tăng bằng một câu `INSERT ... ON CONFLICT DO UPDATE` nên đúng khi nhiều bản dịch vụ
# cùng ghi. Khóa là `<tên giới hạn>:<định danh người dùng>`.
#
# Chỉ thêm hai bảng mới, không đụng bảng nào đã có, nên nâng cấp cụm cũ không phải `down -v`. Cả hai
# do Alembic sở hữu: không nằm trong lược đồ khởi tạo của `infra/postgres/init/`.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_nhip_quet_gioi_han"
down_revision: str | None = "0016_goi_y_va_ghi_de"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scanner_heartbeats",
        sa.Column("name", sa.Text(), primary_key=True),
        sa.Column("last_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("consecutive_errors", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("runner_host", sa.Text(), nullable=True),
        sa.Column("runner_pid", sa.Integer(), nullable=True),
        sa.CheckConstraint("consecutive_errors >= 0", name="scanner_heartbeats_so_loi_khong_am"),
    )

    op.create_table(
        "rate_limit_hits",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("key", "window_start"),
    )
    # Dọn dòng cũ theo mốc cửa sổ: xóa mọi dòng trước một mốc, không cần quét cả bảng
    op.create_index("rate_limit_hits_theo_cua_so", "rate_limit_hits", ["window_start"])


def downgrade() -> None:
    op.drop_index("rate_limit_hits_theo_cua_so", table_name="rate_limit_hits")
    op.drop_table("rate_limit_hits")
    op.drop_table("scanner_heartbeats")
