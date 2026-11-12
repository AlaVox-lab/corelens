# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Thông báo thư điện tử (#251).
#
# Mã bản sửa    : 0024_thong_bao_thu
# Sửa đổi từ    : 0023_kiem_tep_dinh_kem
#
# Bốn bảng, chi tiết ở app/models/thong_bao.py:
#   notification_types        loại thông báo, mẫu tiêu đề và nội dung — DỮ LIỆU (infra/seed/05)
#   notification_preferences  người dùng bật/tắt từng loại; không có dòng là theo mặc định của loại
#   notification_outbox       sự kiện, ghi cùng giao dịch nghiệp vụ; bộ quét gửi xử lý sau
#   notification_deliveries   mỗi thư một dòng — số lần thử, lỗi cuối, lúc gửi: vết để đối soát
#
# Dữ liệu cho cụm cũ: như 0023 — cụm đã có bộ quy tắc thì chạy chính tệp 05, cụm mới để bộ nạp chạy.
# Chỉ thêm bảng, nâng cấp cụm cũ không phải `down -v`.

import logging
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.cau_hinh.khoi_tao import bo_lenh_psql
from app.config import get_settings

revision: str = "0024_thong_bao_thu"
down_revision: str | None = "0023_kiem_tep_dinh_kem"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TEP_DU_LIEU = "05-loai-thong-bao.sql"

log = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    op.create_table(
        "notification_types",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("trigger", sa.Text(), nullable=False),
        sa.Column("recipients", sa.Text(), nullable=False),
        sa.Column("subject_template", sa.Text(), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("default_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_order", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        # Cơ chế kích hoạt và cách chọn người nhận là thứ mã biết; thêm giá trị mới là thêm mã
        sa.CheckConstraint(
            "trigger IN ('state-entered', 'auto-warning', 'auto-done')",
            name="notification_types_co_che",
        ),
        sa.CheckConstraint(
            "recipients IN ('primary-step', 'requester')", name="notification_types_nguoi_nhan"
        ),
    )

    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.Text(), primary_key=True),
        sa.Column(
            "type_code",
            sa.Text(),
            sa.ForeignKey("notification_types.code", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("trigger", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("requests.id"), nullable=False),
        sa.Column(
            "context", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("dedupe_key", sa.Text(), nullable=True, unique=True),
        sa.Column("actor_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "trigger IN ('state-entered', 'auto-warning', 'auto-done')",
            name="notification_outbox_co_che",
        ),
    )
    # Bộ quét chỉ đọc sự kiện chưa xử lý
    op.create_index(
        "notification_outbox_chua_xu_ly",
        "notification_outbox",
        ["id"],
        postgresql_where=sa.text("processed_at IS NULL"),
    )

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "outbox_id",
            sa.BigInteger(),
            sa.ForeignKey("notification_outbox.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "type_code", sa.Text(), sa.ForeignKey("notification_types.code"), nullable=False
        ),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("requests.id"), nullable=False),
        sa.Column("recipient_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("attempts", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'skipped')",
            name="notification_deliveries_trang_thai",
        ),
        # Một sự kiện, một loại, một người: tối đa một thư
        sa.UniqueConstraint(
            "outbox_id", "type_code", "recipient_id", name="notification_deliveries_mot_thu"
        ),
    )
    op.create_index(
        "notification_deliveries_den_han",
        "notification_deliveries",
        ["next_attempt_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )

    ket_noi = op.get_bind()
    cum_cu = ket_noi.execute(sa.text("SELECT EXISTS (SELECT 1 FROM rule_sets)")).scalar_one()
    if not cum_cu:
        return
    tep = Path(get_settings().seed_dir) / TEP_DU_LIEU
    if not tep.is_file():
        log.warning("Không thấy %s — chưa có loại thông báo nào, không thư nào được gửi", tep)
        return
    ket_noi.connection.driver_connection.execute(bo_lenh_psql(tep.read_text(encoding="utf-8")))


def downgrade() -> None:
    op.drop_table("notification_deliveries")
    op.drop_table("notification_outbox")
    op.drop_table("notification_preferences")
    op.drop_table("notification_types")
