# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Điều kiện trên cạnh của động cơ luồng công việc (#397).
#
# Mã bản sửa    : 0032_dieu_kien_tren_canh
# Sửa đổi từ    : 0031_webhook
#
# Bảng `transition_conditions`: mỗi dòng gắn với một cạnh, so một trường riêng của hồ sơ (`requests.details`,
# trường khai ở `request_type_fields`) với một giá trị bằng một phép so. Cạnh có điều kiện chỉ đi được khi MỌI
# điều kiện của nó đúng; cạnh không có dòng nào chạy y như trước. Engine kiểm cùng lúc với ràng buộc Poka-yoke
# (app/rules/dieu_kien.py): lúc chào nút cạnh không thỏa không hiện ra, lúc đi thật thì bị từ chối.
#
# Rẽ nhánh theo dữ liệu vì thế là DỮ LIỆU: hai cạnh cùng nguồn, điều kiện bù nhau. Đổi ngưỡng là một câu UPDATE.
#
# Dữ liệu cho cụm cũ, khuôn 0028: cụm đã có quy trình mua sắm mẫu (`purchase-v1`) thì chạy tệp 07 của dữ liệu
# khởi tạo — thêm cạnh duyệt dưới ngưỡng và điều kiện cho hai cạnh duyệt. Cụm mới để bộ nạp chạy tệp đó sau tệp
# 06. Hồ sơ, nhật ký, tệp giữ nguyên: nâng cấp bằng `up -d --build`, không `down -v`.

import logging
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.cau_hinh.khoi_tao import bo_lenh_psql
from app.config import get_settings

revision: str = "0032_dieu_kien_tren_canh"
down_revision: str | None = "0031_webhook"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TEP_DIEU_KIEN_MAU = "07-dieu-kien-mua-sam.sql"

log = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    op.create_table(
        "transition_conditions",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column(
            "transition_id", sa.Integer(), sa.ForeignKey("transitions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("field_code", sa.Text(), nullable=False),
        sa.Column("operator", sa.Text(), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "operator IN ('<', '<=', '>', '>=', '=', '!=')", name="transition_condition_operator"
        ),
        sa.UniqueConstraint("transition_id", "field_code", "operator", name="transition_condition_once"),
    )
    op.execute(
        "COMMENT ON TABLE transition_conditions IS 'Điều kiện trên cạnh (#397): cạnh chỉ đi được khi mọi điều "
        "kiện so trường riêng của hồ sơ (requests.details) đều đúng.'"
    )

    ket_noi = op.get_bind()
    co_mua_sam = ket_noi.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM rule_sets WHERE version = 'purchase-v1')")
    ).scalar_one()
    if co_mua_sam:
        tep = Path(get_settings().seed_dir) / TEP_DIEU_KIEN_MAU
        if not tep.is_file():
            raise RuntimeError(
                f"Không thấy {TEP_DIEU_KIEN_MAU} trong {get_settings().seed_dir} — bản sửa 0032 cần nó để áp điều "
                "kiện cho quy trình mua sắm mẫu (infra/seed/ gắn vào container ở /seed)."
            )
        ket_noi.connection.driver_connection.execute(bo_lenh_psql(tep.read_text(encoding="utf-8")))
        log.info("0032: đã áp điều kiện trên cạnh cho quy trình mua sắm mẫu")


def downgrade() -> None:
    op.execute(
        "DELETE FROM transitions WHERE activity_code = 'approve-under-threshold' "
        "AND rule_set_id = (SELECT id FROM rule_sets WHERE version = 'purchase-v1')"
    )
    op.drop_table("transition_conditions")
