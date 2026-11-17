# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Lưu trữ lạnh dữ liệu lịch sử ra kho đối tượng (#378, nguyên lý (i) của đề thi).
#
# Mã bản sửa    : 0029_luu_tru_lanh
# Sửa đổi từ    : 0028_nhieu_quy_trinh
#
# Bảng `cold_archives`: sổ các bản lưu đã niêm phong, mỗi tháng UTC một dòng — thùng và tiền tố khóa lúc
# xuất, phiên bản lược đồ của tệp, số dòng, bản sao `manifest.json` và mã băm của nó. Bộ quét
# `cold-archive` (app/analytics/luu_tru_lanh.py) ghi; API lõi `GET /core/v1/archive` đọc.
#
# Chỉ ghi thêm như `event_log`: bản lưu trong kho không bao giờ bị ghi đè, nên dòng ghi sổ của nó cũng không
# được sửa hay xóa. Trigger đặt ở tầng cơ sở dữ liệu vì Superset, psql và công cụ quản trị đều đi vòng qua
# dịch vụ ứng dụng.
#
# Chỉ thêm bảng: cụm cũ nâng lên bằng `up -d --build`, không `down -v`. Không đổi view nào — tầng nóng giữ
# nguyên; dọn khỏi cơ sở dữ liệu đang chạy là việc tương lai theo chính sách lưu giữ của ADR-0009.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0029_luu_tru_lanh"
down_revision: str | None = "0028_nhieu_quy_trinh"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cold_archives",
        sa.Column("period", sa.Text(), primary_key=True),
        sa.Column("bucket", sa.Text(), nullable=False),
        sa.Column("object_prefix", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.SmallInteger(), nullable=False),
        sa.Column("event_rows", sa.Integer(), nullable=False),
        sa.Column("case_rows", sa.Integer(), nullable=False),
        sa.Column("manifest", postgresql.JSONB(), nullable=False),
        sa.Column("manifest_sha256", sa.Text(), nullable=False),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("period ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'", name="cold_archives_ky_hop_le"),
    )
    op.execute(
        "COMMENT ON TABLE cold_archives IS 'Sổ các bản lưu trữ lạnh đã niêm phong trong kho đối tượng (#378). "
        "Chỉ ghi thêm.'"
    )
    op.execute(
        """
        CREATE FUNCTION cold_archives_chi_ghi_them() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
                'Sổ lưu trữ lạnh chỉ ghi thêm: thao tác % bị từ chối', TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER cold_archives_chan_sua_xoa
            BEFORE UPDATE OR DELETE ON cold_archives
            FOR EACH ROW EXECUTE FUNCTION cold_archives_chi_ghi_them();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS cold_archives_chan_sua_xoa ON cold_archives")
    op.execute("DROP FUNCTION IF EXISTS cold_archives_chi_ghi_them()")
    op.drop_table("cold_archives")
