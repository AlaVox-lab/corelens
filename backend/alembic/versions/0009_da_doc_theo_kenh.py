# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Mốc đã đọc tính riêng cho cuộc trò chuyện nội bộ (#156).
#
# Mã bản sửa    : 0009_da_doc_theo_kenh
# Sửa đổi từ    : 0008_da_doc_loi_nhan
#
# Từ #156 mỗi hồ sơ có hai cuộc trò chuyện trong hộp thư: với người gửi, và nội bộ giữa
# nhân viên (lời nhắn thuộc loại `hidden_from_requester`). Đọc cuộc này không được làm cuộc
# kia thành đã đọc, nên mốc thêm một cột phân biệt và khóa chính gồm cả cột đó. Mốc cũ đều
# là của cuộc với người gửi — trước #156 chưa có lời nhắn nội bộ nào.
#
# Bản thân migration không cần `down -v`; cột `message_kinds.hidden_from_requester` thì nằm
# trong lược đồ khởi tạo, nên #156 vẫn phải `down -v`.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_da_doc_theo_kenh"
down_revision: str | None = "0008_da_doc_loi_nhan"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "case_message_reads",
        sa.Column("internal", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.drop_constraint("case_message_reads_pkey", "case_message_reads", type_="primary")
    op.create_primary_key(
        "case_message_reads_pkey", "case_message_reads", ["case_id", "reader", "internal"]
    )


def downgrade() -> None:
    op.execute("DELETE FROM case_message_reads WHERE internal")
    op.drop_constraint("case_message_reads_pkey", "case_message_reads", type_="primary")
    op.create_primary_key("case_message_reads_pkey", "case_message_reads", ["case_id", "reader"])
    op.drop_column("case_message_reads", "internal")
