# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Màn quản trị cấu hình quy trình (#255).
#
# Mã bản sửa    : 0025_quan_tri_cau_hinh
# Sửa đổi từ    : 0024_thong_bao_thu
#
# Hai việc:
#
#   - Bảng `config_changes`: mỗi lần quản trị viên sửa một trường cấu hình trên màn quản trị ghi một
#     dòng — ai, lúc nào, bảng nào, dòng nào, trường nào, từ giá trị nào sang giá trị nào. Chỉ ghi
#     thêm, chặn bằng trigger như nhật ký sự kiện và lời nhắn: nhật ký sửa cấu hình mà sửa được thì
#     không còn là bằng chứng.
#   - Hàm `kiem_tra_cau_hinh()` thay bằng bản có thêm hai phép kiểm cho cơ cấu tổ chức (nội dung ở
#     `alembic/sql/0025_kiem_tra_cau_hinh.sql`, lý do trong đầu tệp đó).
#
# Chỉ thêm một bảng và thay một hàm, không đụng dòng dữ liệu nào: cụm cũ nâng lên không cần `down -v`.

from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025_quan_tri_cau_hinh"
down_revision: str | None = "0024_thong_bao_thu"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

THU_MUC_SQL = Path(__file__).resolve().parent.parent / "sql"


def _chay_tep(ten: str) -> None:
    # Qua thẳng trình điều khiển như 0018: thân hàm có dấu % và dấu hai chấm
    op.get_bind().connection.driver_connection.execute((THU_MUC_SQL / ten).read_text(encoding="utf-8"))


def upgrade() -> None:
    op.create_table(
        "config_changes",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("actor_id", sa.Text(), nullable=False),
        # Tên người sửa tại thời điểm sửa, cùng lý do với `event_log.actor_label`
        sa.Column("actor_label", sa.Text(), nullable=True),
        # Bảng cấu hình bị sửa (`request_types`, `priorities`, `departments`) và mã dòng
        sa.Column("entity", sa.Text(), nullable=False),
        sa.Column("entity_code", sa.Text(), nullable=False),
        sa.Column("field", sa.Text(), nullable=False),
        sa.Column("old_value", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("new_value", postgresql.JSONB(none_as_null=True), nullable=True),
    )
    op.create_index("config_changes_moi_nhat", "config_changes", [sa.text("changed_at DESC")])

    op.execute(
        """
        CREATE FUNCTION config_changes_chi_ghi_them() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
                'Nhật ký thay đổi cấu hình chỉ ghi thêm: thao tác % bị từ chối', TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER config_changes_chan_sua_xoa
            BEFORE UPDATE OR DELETE ON config_changes
            FOR EACH ROW EXECUTE FUNCTION config_changes_chi_ghi_them();
        """
    )

    _chay_tep("0025_kiem_tra_cau_hinh.sql")


def downgrade() -> None:
    _chay_tep("0018_kiem_tra_cau_hinh.sql")
    op.execute("DROP TRIGGER IF EXISTS config_changes_chan_sua_xoa ON config_changes;")
    op.execute("DROP FUNCTION IF EXISTS config_changes_chi_ghi_them();")
    op.drop_index("config_changes_moi_nhat", table_name="config_changes")
    op.drop_table("config_changes")
