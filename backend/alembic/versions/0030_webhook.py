# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Truyền phát sự kiện ra ngoài bằng webhook (#390).
#
# Mã bản sửa    : 0030_webhook
# Sửa đổi từ    : 0029_bao_thay_doi_ho_so
#
#   - `webhook_subscriptions`: một địa chỉ nhận do quản trị viên hay tài khoản dịch vụ đăng ký qua
#     `/core/v1/webhooks`. Bộ lọc là dữ liệu: `activities` (mã hoạt động của nhật ký) và `process_code`
#     (quy trình), để trống là nhận hết. `last_event_id` là con trỏ trên `event_log` — đăng ký mới đặt
#     bằng mã sự kiện lớn nhất lúc tạo, nên chỉ nhận sự kiện từ đó về sau; bộ gửi dời nó lên sau mỗi lượt.
#   - `webhook_deliveries`: mỗi (đăng ký, sự kiện) một dòng — khóa duy nhất chặn gửi trùng. Ghi số lần
#     thử, lúc thử kế, mã phản hồi và lỗi cuối để người đăng ký tra được vì sao chưa tới.
#
# `event_log` giữ nguyên: bộ gửi chỉ đọc. Không đổi dữ liệu sẵn có: nâng cấp bằng `up -d --build`.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0030_webhook"
down_revision: str | None = "0029_bao_thay_doi_ho_so"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("secret", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("activities", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("process_code", sa.Text(), sa.ForeignKey("processes.code"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("owner_id", sa.Text(), nullable=False),
        sa.Column("last_event_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("url ~* '^https?://'", name="webhook_url_http"),
    )
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "subscription_id",
            sa.BigInteger(),
            sa.ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_id", sa.BigInteger(), sa.ForeignKey("event_log.id"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_status_code", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("subscription_id", "event_id", name="webhook_delivery_once"),
        sa.CheckConstraint("status IN ('pending', 'delivered', 'failed')", name="webhook_delivery_status"),
    )
    op.create_index(
        "webhook_deliveries_due",
        "webhook_deliveries",
        ["next_attempt_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("webhook_deliveries_due", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
    op.drop_table("webhook_subscriptions")
