# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Lời nhắn trên hồ sơ (#128, ADR-0005).
#
# Mã bản sửa    : 0007_loi_nhan_tren_ho_so
# Sửa đổi từ    : 0006_thay_doi_truong
#
# Lời nhắn là thao tác KHÔNG đổi hồ sơ — nhắn điều phối viên, hỏi tiến độ, trả lời —
# nên nó không phải một lần chuyển trạng thái và không vào `event_log`. Nó có bảng
# riêng, và bảng đó giữ cùng hai tính chất với nhật ký sự kiện:
#
#   Chỉ ghi thêm   — trigger chặn UPDATE và DELETE ở tầng cơ sở dữ liệu. Lời nhắn là
#                    dấu vết của một cuộc trao đổi; sửa được thì không còn là dấu vết.
#   Giờ theo UTC   — TIMESTAMPTZ, mốc do PostgreSQL điền bằng now().
#
# Loại lời nhắn tham chiếu bảng cấu hình `message_kinds` do lược đồ khởi tạo tạo, như
# `requests` tham chiếu `states` — nên migration này cũng giả định lược đồ khởi tạo đã
# dựng xong.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_loi_nhan_tren_ho_so"
down_revision: str | None = "0006_thay_doi_truong"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "case_messages",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("case_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        # Định danh `sub` của Keycloak, và tên tại thời điểm nhắn — cùng lý do với
        # `event_log.actor_label`: người đổi tên thì lịch sử vẫn kể đúng
        sa.Column("author", sa.Text(), nullable=False),
        sa.Column("author_label", sa.Text(), nullable=False),
        # Trống được ở loại không bắt buộc nội dung, như "Hỏi tiến độ"
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["case_id"], ["requests.id"]),
        sa.ForeignKeyConstraint(["kind"], ["message_kinds.code"]),
        # Cùng giới hạn với ô ghi chú của lần chuyển trạng thái
        sa.CheckConstraint(
            "body IS NULL OR char_length(body) BETWEEN 1 AND 2000",
            name="case_messages_do_dai_noi_dung",
        ),
    )

    op.create_index(
        "case_messages_tra_theo_ho_so", "case_messages", ["case_id", "created_at"]
    )

    op.execute(
        """
        CREATE FUNCTION case_messages_chi_ghi_them() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
                'Lời nhắn chỉ ghi thêm: thao tác % bị từ chối', TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER case_messages_chan_sua_xoa
            BEFORE UPDATE OR DELETE ON case_messages
            FOR EACH ROW EXECUTE FUNCTION case_messages_chi_ghi_them();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS case_messages_chan_sua_xoa ON case_messages;")
    op.execute("DROP FUNCTION IF EXISTS case_messages_chi_ghi_them();")
    op.drop_index("case_messages_tra_theo_ho_so", table_name="case_messages")
    op.drop_table("case_messages")
