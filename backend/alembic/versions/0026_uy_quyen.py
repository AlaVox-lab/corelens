# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ủy quyền khi vắng mặt (#252).
#
# Mã bản sửa    : 0026_uy_quyen
# Sửa đổi từ    : 0025_quan_tri_cau_hinh
#
# Hai việc:
#
#   - Bảng `delegations`: người vắng (`delegator`) cho một người cùng phòng (`delegate`) mang vai của
#     mình trong phòng đó, từ `starts_at` tới trước `ends_at`. Vai được ủy quyền chụp lúc khai, chỉ
#     gồm vai riêng của người vắng — vai có được nhờ ủy quyền không ủy quyền tiếp được. Thu hồi sớm thì
#     điền `revoked_*`, không xóa dòng: lịch sử ai làm thay ai phải đọc lại được.
#   - Hai cột `event_log.on_behalf_of`, `on_behalf_of_label`: lần chuyển chỉ đi được nhờ ủy quyền ghi
#     người vắng bên cạnh người thật bấm. Thêm cột không chạm trigger chỉ ghi thêm (trigger chặn
#     UPDATE và DELETE trên dòng, không chặn ALTER), dòng cũ để NULL.
#
# Chỉ thêm bảng và cột: cụm cũ nâng lên không cần `down -v`.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026_uy_quyen"
down_revision: str | None = "0025_quan_tri_cau_hinh"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delegations",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("delegator_id", sa.Text(), nullable=False),
        sa.Column("delegator_label", sa.Text(), nullable=False),
        sa.Column("delegate_id", sa.Text(), nullable=False),
        sa.Column("delegate_label", sa.Text(), nullable=False),
        sa.Column(
            "department_code",
            sa.Text(),
            sa.ForeignKey("departments.code", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("roles", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by_id", sa.Text(), nullable=False),
        sa.Column("created_by_label", sa.Text(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_id", sa.Text(), nullable=True),
        sa.Column("revoked_by_label", sa.Text(), nullable=True),
        sa.CheckConstraint("ends_at > starts_at", name="delegations_khoang_hop_le"),
        sa.CheckConstraint("delegator_id <> delegate_id", name="delegations_khong_tu_uy_quyen"),
        sa.CheckConstraint("cardinality(roles) > 0", name="delegations_co_vai"),
        sa.CheckConstraint(
            "(revoked_at IS NULL) = (revoked_by_id IS NULL)", name="delegations_thu_hoi_du_vet"
        ),
    )
    # Mỗi yêu cầu của người được ủy quyền tra ủy quyền đang hiệu lực của họ
    op.create_index("delegations_tra_nguoi_nhan", "delegations", ["delegate_id", "ends_at"])
    op.create_index("delegations_tra_phong", "delegations", ["department_code", "ends_at"])

    op.add_column("event_log", sa.Column("on_behalf_of", sa.Text(), nullable=True))
    op.add_column("event_log", sa.Column("on_behalf_of_label", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("event_log", "on_behalf_of_label")
    op.drop_column("event_log", "on_behalf_of")
    op.drop_index("delegations_tra_phong", table_name="delegations")
    op.drop_index("delegations_tra_nguoi_nhan", table_name="delegations")
    op.drop_table("delegations")
