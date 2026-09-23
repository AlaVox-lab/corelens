# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Thêm tên hiển thị của người được giao xử lý vào hồ sơ.
#
# Mã bản sửa    : 0005_ten_nguoi_xu_ly
# Sửa đổi từ    : 0004_ten_nguoi_gui
#
# Cùng khuôn với 0003 và 0004: lưu tên tại thời điểm giao việc thay vì tra ngược từ
# Keycloak lúc đọc. Buồng lái phòng ban (#83) phải cho biết hồ sơ đang ở tay ai, và
# tra danh bạ ở mỗi lần mở hàng đợi thì đưa Keycloak lên đường đi của mọi trang — thứ
# #84 đã cố ý tránh. Tên do chính danh bạ trả về lúc trưởng phòng chọn người, không
# do trình duyệt gửi lên.
#
# Cột để NULL được: hồ sơ chưa giao cho ai, hoặc được giao trước bản sửa này.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_ten_nguoi_xu_ly"
down_revision: str | None = "0004_ten_nguoi_gui"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("requests", sa.Column("assignee_label", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("requests", "assignee_label")
