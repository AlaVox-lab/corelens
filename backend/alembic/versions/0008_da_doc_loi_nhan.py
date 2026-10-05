# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Đã đọc tới đâu trong lời nhắn của từng hồ sơ — cho hộp thư chung (#155).
#
# Mã bản sửa    : 0008_da_doc_loi_nhan
# Sửa đổi từ    : 0007_loi_nhan_tren_ho_so
#
# Mỗi người một dòng cho mỗi hồ sơ: lời nhắn cuối cùng họ đã đọc. Số chưa đọc là số lời
# nhắn sau mốc đó do người KHÁC viết — lời nhắn của chính mình không bao giờ chưa đọc.
#
# Khác `case_messages`, bảng này ĐƯỢC sửa: đọc thêm thì mốc dời lên. Nó không phải dấu vết
# của cuộc trao đổi mà là trạng thái hiển thị của từng người, nên không chỉ ghi thêm và
# không vào nhật ký sự kiện — ghi đã đọc không đổi hồ sơ (ADR-0005), không chạm `requests`.
#
# Chỉ thêm bảng, không đổi lược đồ khởi tạo hay dữ liệu: dịch vụ tự chạy migration lúc
# khởi động, cụm đang chạy không cần `down -v`.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_da_doc_loi_nhan"
down_revision: str | None = "0007_loi_nhan_tren_ho_so"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "case_message_reads",
        sa.Column("case_id", sa.BigInteger(), nullable=False),
        # Định danh `sub` của Keycloak — cùng nguồn với `case_messages.author`
        sa.Column("reader", sa.Text(), nullable=False),
        sa.Column("last_read_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "read_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("case_id", "reader"),
        sa.ForeignKeyConstraint(["case_id"], ["requests.id"]),
        sa.ForeignKeyConstraint(["last_read_id"], ["case_messages.id"]),
    )


def downgrade() -> None:
    op.drop_table("case_message_reads")
