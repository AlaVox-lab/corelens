# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Thêm tên hiển thị của người thực hiện vào nhật ký sự kiện.
#
# Mã bản sửa    : 0003_ten_nguoi_thuc_hien
# Sửa đổi từ    : 0002_dong_ho_sla
#
# Vì sao lưu kèm thay vì tra ngược từ Keycloak lúc đọc: người nghỉ việc thì tài khoản
# bị xóa và dòng thời gian mất tên; người đổi tên thì lịch sử sẽ kể sai. Nhật ký kiểm
# toán phải giữ được sự thật của thời điểm đó, kể cả khi nguồn danh tính đã đổi.
#
# Cột để NULL được vì những bản ghi có trước bản sửa này không biết tên. Giao diện lùi
# về hiển thị mã định danh khi gặp NULL.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_ten_nguoi_thuc_hien"
down_revision: str | None = "0002_dong_ho_sla"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Thêm cột vào bảng chỉ-ghi-thêm là an toàn: trigger chỉ chặn UPDATE và DELETE ở
    # mức dòng, không chặn thay đổi lược đồ.
    op.add_column("event_log", sa.Column("actor_label", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("event_log", "actor_label")
