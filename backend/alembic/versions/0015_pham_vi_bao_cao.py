# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Phạm vi xem bảng điều khiển phân tích của từng vai trò (#305).
#
# Mã bản sửa    : 0015_pham_vi_bao_cao
# Sửa đổi từ    : 0014_lop_bao_cao
#
# `roles.report_scope`: `department` là xem số của phòng mình, `all` là toàn công ty, trống là
# không thấy mục Báo cáo. Ai xem được và xem tới đâu là dữ liệu cấu hình như mọi quy tắc khác,
# không phải tên vai trò viết trong mã.
#
# Cột này có ở cả lược đồ khởi tạo (`infra/postgres/init/`), và giá trị nằm trong
# `infra/seed/01-quy-tac-quy-trinh.sql` — cụm dựng mới lấy từ đó. Bản sửa này chỉ cho cụm dựng
# trước #305 nâng cấp mà không phải `down -v`: thêm cột, rồi điền đúng giá trị của dữ liệu khởi
# tạo. Cụm đã có cột thì không đụng gì, để không ghi đè cấu hình doanh nghiệp đã sửa.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_pham_vi_bao_cao"
down_revision: str | None = "0014_lop_bao_cao"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Bản sao giá trị trong dữ liệu khởi tạo, chỉ dùng một lần lúc nâng cấp cụm cũ
PHAM_VI_KHOI_TAO = {"approver": "department", "classifier": "all", "administrator": "all"}


def upgrade() -> None:
    cot = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("roles")}
    if "report_scope" in cot:
        return
    op.add_column("roles", sa.Column("report_scope", sa.Text(), nullable=True))
    op.create_check_constraint(
        "roles_report_scope_check", "roles", "report_scope IN ('department', 'all')"
    )
    for vai_tro, pham_vi in PHAM_VI_KHOI_TAO.items():
        op.execute(
            sa.text("UPDATE roles SET report_scope = :p WHERE code = :v").bindparams(
                p=pham_vi, v=vai_tro
            )
        )


def downgrade() -> None:
    op.drop_column("roles", "report_scope")
