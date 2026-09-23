# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Nhật ký sự kiện ghi lịch sử thay đổi của các trường quyết định (#100).
#
# Mã bản sửa    : 0006_thay_doi_truong
# Sửa đổi từ    : 0005_ten_nguoi_xu_ly
#
# Điều phối viên sửa loại yêu cầu người gửi chọn sai thì giá trị cũ bị ghi đè và mất
# dấu: nhật ký chỉ ghi "Phân loại yêu cầu", không ghi đổi từ loại nào sang loại nào.
# Cột mới giữ đúng phần đổi của từng lần chuyển, dạng {trường: {from, to}}; hồ sơ vẫn
# chỉ mang giá trị hiện tại. Người xử lý ghi kèm tên tại thời điểm đổi.
#
# JSONB thay vì một bảng con: mỗi lần chuyển đổi nhiều nhất bốn trường, luôn đọc cùng
# dòng nhật ký của nó, và bảng chỉ-ghi-thêm thì không bao giờ phải sửa riêng một mục.
# NULL khi lần chuyển không đổi trường nào — gồm mọi dòng có trước bản sửa này.
#
# Thêm cột vào bảng chỉ-ghi-thêm là an toàn: trigger chỉ chặn UPDATE và DELETE ở mức
# dòng, không chặn thay đổi lược đồ.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_thay_doi_truong"
down_revision: str | None = "0005_ten_nguoi_xu_ly"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("event_log", sa.Column("changes", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("event_log", "changes")
