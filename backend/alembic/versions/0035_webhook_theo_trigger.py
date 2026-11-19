# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Webhook không bỏ sót sự kiện khi nhiều giao dịch ghi nhật ký chồng nhau (#492).
#
# Mã bản sửa    : 0035_webhook_theo_trigger
# Sửa đổi từ    : 0034_thoi_gian_moi_trang_thai
#
# Trước bản này, mỗi đăng ký giữ con trỏ `last_event_id` và bộ gửi dời nó qua mã lớn nhất đã thấy. Mã của
# `event_log` cấp lúc ghi dòng, nhưng dòng chỉ thấy được khi giao dịch commit — và các giao dịch không commit
# theo thứ tự mã. Một lượt quét SLA giữ mã 500–519 chưa commit, một thao tác của người dùng commit mã 520, bộ
# gửi thấy 520 và dời con trỏ: 500–519 commit sau đó không bao giờ được xét.
#
# Nay lần gửi sinh ngay trong giao dịch ghi sự kiện, bằng trigger `AFTER INSERT` trên `event_log`: sự kiện
# commit thì lần gửi commit cùng, giao dịch hoàn tác thì cả hai cùng mất — thứ tự commit không còn quan trọng.
# Trigger chỉ chèn vào `webhook_deliveries`, không đụng dòng nhật ký, nên `event_log` vẫn chỉ ghi thêm. Bộ lọc
# (đăng ký đang bật, mã hoạt động, mã quy trình) giữ đúng như bộ gửi cũ. Đăng ký mới chỉ nhận sự kiện ghi SAU
# lúc tạo, như trước — trigger chỉ chạy cho dòng mới.
#
# Chuyển đổi: sự kiện đã ghi mà bộ gửi cũ chưa kịp xét (mã lớn hơn con trỏ) được sinh lần gửi một lần ở đây,
# rồi bỏ cột con trỏ. Không gửi lại sự kiện cũ: khóa duy nhất (đăng ký, sự kiện) bỏ qua lần gửi đã có.
#
# Không xóa dữ liệu: nâng cấp bằng `up -d --build`, không `down -v`.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035_webhook_theo_trigger"
down_revision: str | None = "0034_thoi_gian_moi_trang_thai"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Mã quy trình của hồ sơ mang sự kiện — cùng phép nối với `than_su_kien` của bộ gửi
QUY_TRINH_CUA_SU_KIEN = """
    (SELECT rs.process_code FROM requests r JOIN rule_sets rs ON rs.id = r.rule_set_id WHERE r.id = {su_kien}.case_id)
"""


def upgrade() -> None:
    op.execute(
        f"""
        CREATE FUNCTION webhook_sinh_lan_gui() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            INSERT INTO webhook_deliveries (subscription_id, event_id)
            SELECT s.id, NEW.id
            FROM webhook_subscriptions s
            WHERE s.is_active
              AND (s.activities IS NULL OR NEW.activity = ANY (s.activities))
              AND (s.process_code IS NULL OR s.process_code = {QUY_TRINH_CUA_SU_KIEN.format(su_kien="NEW")})
            ON CONFLICT ON CONSTRAINT webhook_delivery_once DO NOTHING;
            RETURN NULL;
        END;
        $$;

        CREATE TRIGGER webhook_sinh_lan_gui
            AFTER INSERT ON event_log
            FOR EACH ROW EXECUTE FUNCTION webhook_sinh_lan_gui();
        """
    )
    # Bù một lần: sự kiện sau con trỏ của từng đăng ký đang bật mà bộ gửi cũ chưa xét
    op.execute(
        f"""
        INSERT INTO webhook_deliveries (subscription_id, event_id)
        SELECT s.id, e.id
        FROM webhook_subscriptions s
        JOIN event_log e ON e.id > s.last_event_id
        WHERE s.is_active
          AND (s.activities IS NULL OR e.activity = ANY (s.activities))
          AND (s.process_code IS NULL OR s.process_code = {QUY_TRINH_CUA_SU_KIEN.format(su_kien="e")})
        ON CONFLICT ON CONSTRAINT webhook_delivery_once DO NOTHING
        """
    )
    op.drop_column("webhook_subscriptions", "last_event_id")


def downgrade() -> None:
    op.add_column("webhook_subscriptions", sa.Column("last_event_id", sa.BigInteger(), nullable=True))
    op.execute("UPDATE webhook_subscriptions SET last_event_id = (SELECT coalesce(max(id), 0) FROM event_log)")
    op.alter_column("webhook_subscriptions", "last_event_id", nullable=False)
    op.execute(
        """
        DROP TRIGGER IF EXISTS webhook_sinh_lan_gui ON event_log;
        DROP FUNCTION IF EXISTS webhook_sinh_lan_gui();
        """
    )
