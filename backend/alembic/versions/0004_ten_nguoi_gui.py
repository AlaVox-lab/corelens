# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Thêm tên hiển thị của người gửi vào hồ sơ.
#
# Mã bản sửa    : 0004_ten_nguoi_gui
# Sửa đổi từ    : 0003_ten_nguoi_thuc_hien
#
# Cùng khuôn với 0003: lưu tên tại thời điểm hành động thay vì tra ngược từ Keycloak
# lúc đọc. Khác 0003 ở chỗ việc TẠO hồ sơ không sinh dòng nhật ký nào — nó không phải
# một lần chuyển trạng thái — nên tên người gửi không có chỗ nào khác để nằm.
#
# Cổng người gửi (#44) không cần cột này vì người xem chính là người gửi. Buồng lái
# điều phối (#82) thì cần: hàng đợi phải cho biết ai gửi.
#
# Cột để NULL được vì hồ sơ có trước bản sửa này không biết tên. Giao diện lùi về hiển
# thị mã định danh khi gặp NULL.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_ten_nguoi_gui"
down_revision: str | None = "0003_ten_nguoi_thuc_hien"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("requests", sa.Column("requester_label", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("requests", "requester_label")
