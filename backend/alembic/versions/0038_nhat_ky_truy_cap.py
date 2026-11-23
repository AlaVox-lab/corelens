# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Nhật ký kiểm toán truy cập dữ liệu cá nhân (#431).
#
# Mã bản sửa    : 0038_nhat_ky_truy_cap
# Sửa đổi từ    : 0037_khoa_trung_lap
#
# Nhật ký sự kiện ghi mọi THAY ĐỔI trên hồ sơ, chưa ghi việc XEM. Bảng này ghi bốn loại truy cập vào dữ liệu cá
# nhân của người khác: mở chi tiết hồ sơ, xem liên hệ người gửi, tải tệp đính kèm, xuất nhật ký sự kiện. Xem
# app/kiem_toan.py và ARCHITECTURE.md mục "Nhật ký truy cập dữ liệu cá nhân".
#
#   - `access_kinds`: danh mục loại truy cập (mã, nhãn tiếng Việt), nạp ngay ở đây. Nhãn đọc từ bảng, không nằm
#     trong mã.
#   - `access_audit_log`: mỗi lần truy cập một dòng. `at` theo đồng hồ của cơ sở dữ liệu (UTC), như nhật ký sự
#     kiện. `actor_label` là nhãn tên chụp lúc truy cập, như `event_log.actor_label` — để thao tác ẩn danh hóa
#     của ADR-0009 đối xử với hai bảng như nhau. `case_id` trỏ `requests` với ON DELETE SET NULL: xóa hồ sơ theo
#     thời hạn lưu giữ không xóa vết kiểm toán. `channel`: `ung-dung` (các màn của ứng dụng minh họa) hay `loi`
#     (API `/core/v1`).
#
# CHỈ GHI THÊM như `case_messages`, `case_feedback`: trigger chặn UPDATE và DELETE. Ngoại lệ duy nhất là chính
# hành động ON DELETE SET NULL của khóa ngoại (chạy bên trong trigger của khóa ngoại, độ sâu trigger > 1, chỉ
# đổi `case_id` thành NULL) — không có ngoại lệ đó thì xóa một hồ sơ từng được xem sẽ bị từ chối.
#
# Chưa có thời hạn lưu giữ cho bảng này: thuộc việc tiếp sau của ADR-0009. Chỉ thêm, không đổi dữ liệu có sẵn:
# nâng cấp bằng `up -d --build`, không `down -v`.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0038_nhat_ky_truy_cap"
down_revision: str | None = "0037_khoa_trung_lap"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LOAI_TRUY_CAP = [
    ("case-view", "Xem chi tiết hồ sơ", 1),
    ("requester-contact", "Xem liên hệ người gửi", 2),
    ("attachment-download", "Tải tệp đính kèm", 3),
    ("event-log-export", "Xuất nhật ký sự kiện", 4),
]


def upgrade() -> None:
    bang_loai = op.create_table(
        "access_kinds",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.bulk_insert(bang_loai, [{"code": m, "label": n, "display_order": t} for m, n, t in LOAI_TRUY_CAP])
    op.execute(
        "COMMENT ON TABLE access_kinds IS 'Danh mục loại truy cập dữ liệu cá nhân được ghi kiểm toán (#431): "
        "mã và nhãn tiếng Việt hiện trên màn Hệ thống.'"
    )

    op.create_table(
        "access_audit_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("actor_label", sa.Text(), nullable=True),
        sa.Column("access_kind", sa.Text(), sa.ForeignKey("access_kinds.code"), nullable=False),
        sa.Column("case_id", sa.BigInteger(), sa.ForeignKey("requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("attachment_id", sa.BigInteger(), nullable=True),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("details", JSONB(), nullable=True),
        sa.CheckConstraint("channel IN ('ung-dung', 'loi')", name="access_audit_log_kenh_hop_le"),
    )
    op.create_index("access_audit_log_theo_ho_so", "access_audit_log", ["case_id", "at"])
    op.create_index("access_audit_log_theo_nguoi", "access_audit_log", ["actor", "at"])
    op.create_index("access_audit_log_theo_luc", "access_audit_log", ["at"])
    op.execute(
        "COMMENT ON TABLE access_audit_log IS 'Nhật ký kiểm toán truy cập dữ liệu cá nhân của người khác (#431): "
        "xem chi tiết hồ sơ, xem liên hệ người gửi, tải tệp, xuất nhật ký sự kiện. Chỉ ghi thêm.'"
    )
    op.execute(
        """
        CREATE FUNCTION access_audit_log_chi_ghi_them() RETURNS trigger AS $$
        BEGIN
            -- Hành động ON DELETE SET NULL của khóa ngoại case_id: chạy từ trigger của khóa ngoại (độ sâu > 1)
            -- và chỉ gỡ case_id — vết kiểm toán ở lại khi hồ sơ bị xóa
            IF TG_OP = 'UPDATE' AND pg_trigger_depth() > 1
               AND OLD.case_id IS NOT NULL AND NEW.case_id IS NULL
               AND (NEW.id, NEW.at, NEW.actor, NEW.actor_label, NEW.access_kind, NEW.attachment_id,
                    NEW.channel, NEW.details)
                   IS NOT DISTINCT FROM
                   (OLD.id, OLD.at, OLD.actor, OLD.actor_label, OLD.access_kind, OLD.attachment_id,
                    OLD.channel, OLD.details) THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION
                'Nhật ký truy cập chỉ ghi thêm: thao tác % bị từ chối', TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER access_audit_log_chan_sua_xoa
            BEFORE UPDATE OR DELETE ON access_audit_log
            FOR EACH ROW EXECUTE FUNCTION access_audit_log_chi_ghi_them();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS access_audit_log_chan_sua_xoa ON access_audit_log;")
    op.execute("DROP FUNCTION IF EXISTS access_audit_log_chi_ghi_them();")
    op.drop_index("access_audit_log_theo_luc", table_name="access_audit_log")
    op.drop_index("access_audit_log_theo_nguoi", table_name="access_audit_log")
    op.drop_index("access_audit_log_theo_ho_so", table_name="access_audit_log")
    op.drop_table("access_audit_log")
    op.drop_table("access_kinds")
