# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Trường thông tin riêng theo loại yêu cầu (#250).
#
# Mã bản sửa    : 0013_truong_theo_loai
# Sửa đổi từ    : 0012_tep_dinh_kem
#
# Giá trị lưu trong một cột JSONB, khóa là mã trường khai ở bảng cấu hình
# `request_type_fields`. Một cột thay vì bảng mỗi giá trị một dòng: danh sách hồ sơ đọc một
# lần, kiểu số và ngày giữ nguyên kiểu, và PostgreSQL, Superset vẫn lọc được theo khóa.
# Hồ sơ cũ nhận `{}` — chưa có trường riêng nào, trang hồ sơ hiện "chưa có".

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0013_truong_theo_loai"
down_revision: str | None = "0012_tep_dinh_kem"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "requests",
        sa.Column("details", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("requests", "details")
