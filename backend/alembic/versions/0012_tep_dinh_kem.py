# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Tệp đính kèm trên hồ sơ (#80).
#
# Mã bản sửa    : 0012_tep_dinh_kem
# Sửa đổi từ    : 0011_mo_lai_co_gioi_han
#
# Bảng chỉ giữ siêu dữ liệu; nội dung nhị phân nằm trong SeaweedFS qua S3 API (ADR-0002).
# Chỉ ghi thêm, như `case_messages` và `event_log`: hồ sơ hủy vẫn giữ tệp để truy vết,
# nên không có thao tác xóa nào và trigger ở tầng cơ sở dữ liệu chặn cả UPDATE lẫn DELETE.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_tep_dinh_kem"
down_revision: str | None = "0011_mo_lai_co_gioi_han"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "case_attachments",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("case_id", sa.BigInteger(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        # Chuỗi ngẫu nhiên, không mang tên tệp do người dùng đặt
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("uploaded_by", sa.Text(), nullable=False),
        sa.Column("uploaded_by_label", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["case_id"], ["requests.id"]),
        sa.UniqueConstraint("storage_key", name="case_attachments_khoa_kho_duy_nhat"),
        sa.CheckConstraint("size_bytes > 0", name="case_attachments_kich_thuoc_duong"),
        sa.CheckConstraint(
            "char_length(filename) BETWEEN 1 AND 200",
            name="case_attachments_do_dai_ten",
        ),
    )
    op.create_index(
        "case_attachments_tra_theo_ho_so", "case_attachments", ["case_id", "created_at"]
    )

    op.execute(
        """
        CREATE FUNCTION case_attachments_chi_ghi_them() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
                'Tệp đính kèm chỉ ghi thêm: thao tác % bị từ chối', TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER case_attachments_chan_sua_xoa
            BEFORE UPDATE OR DELETE ON case_attachments
            FOR EACH ROW EXECUTE FUNCTION case_attachments_chi_ghi_them();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER case_attachments_chan_sua_xoa ON case_attachments")
    op.execute("DROP FUNCTION case_attachments_chi_ghi_them()")
    op.drop_index("case_attachments_tra_theo_ho_so", table_name="case_attachments")
    op.drop_table("case_attachments")
