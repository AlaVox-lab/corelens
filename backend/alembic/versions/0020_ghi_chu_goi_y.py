# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ghi chú và mốc thử của gợi ý do mô hình ngôn ngữ sinh (#317, ADR-0008).
#
# Mã bản sửa    : 0020_ghi_chu_goi_y
# Sửa đổi từ    : 0019_tai_khoan_khai_pha
#
# Ba cột trên `requests`, cùng nhóm trường GỢI Ý với `suggested_*` — tầng I ghi, không phải trường
# quyết định, không đi qua cửa chuyển trạng thái:
#
#   suggestion_note          JSONB — lý do ngắn của từng gợi ý, mô hình nào, mất bao lâu; hay lỗi
#                            của lần thử hỏng. Xem `app/intelligence/phan_loai.py`
#   suggestion_attempted_at  mốc lần thử gần nhất
#   suggestion_attempts      số lần đã thử
#
# Hai cột sau cho bộ quét bù biết hồ sơ nào đã hỏi mô hình rồi, để không hỏi lại mãi. Hồ sơ cũ mang
# 0 lần thử: mô hình bật lên thì bộ quét bù gợi ý cả hồ sơ còn đang chờ điều phối. Chỉ thêm cột, nên
# nâng cấp cụm cũ không phải `down -v`.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_ghi_chu_goi_y"
down_revision: str | None = "0019_tai_khoan_khai_pha"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("requests", sa.Column("suggestion_note", postgresql.JSONB(), nullable=True))
    op.add_column(
        "requests", sa.Column("suggestion_attempted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "requests",
        sa.Column("suggestion_attempts", sa.SmallInteger(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("requests", "suggestion_attempts")
    op.drop_column("requests", "suggestion_attempted_at")
    op.drop_column("requests", "suggestion_note")
