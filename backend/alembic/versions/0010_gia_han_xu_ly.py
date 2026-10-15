# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Gia hạn xử lý từng hồ sơ (#101).
#
# Mã bản sửa    : 0010_gia_han_xu_ly
# Sửa đổi từ    : 0009_da_doc_theo_kenh
#
# Giảng viên chốt ngày 08/10: điều phối viên gia hạn được từng hồ sơ, có lý do, ghi sự
# kiện; tối đa một lần, lần thứ hai chỉ trưởng bộ phận; mỗi lần tối đa X% hạn gốc. Gia hạn
# là cạnh tự trỏ (ADR-0005), nên giá trị cũ và mới nằm ở cột `changes` của nhật ký. Ba cột
# trên hồ sơ:
#
#   sla_extension_hours        số giờ của lần gia hạn gần nhất — ô người dùng nhập
#   sla_extension_total_hours  tổng số giờ đã gia hạn — cộng vào hạn gốc
#   sla_extension_count        đã gia hạn mấy lần — ràng buộc đếm theo cột này
#
# Hai cột sau do ràng buộc `extend-deadline` tự đặt, người dùng không gửi được. Hạn gốc
# (loại yêu cầu nhân hệ số ưu tiên) không lưu: tính lại được từ danh mục.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_gia_han_xu_ly"
down_revision: str | None = "0009_da_doc_theo_kenh"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "requests",
        sa.Column("sla_extension_hours", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "requests",
        sa.Column("sla_extension_total_hours", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "requests",
        sa.Column("sla_extension_count", sa.SmallInteger(), server_default="0", nullable=False),
    )
    op.create_check_constraint(
        "requests_gia_han_khong_am",
        "requests",
        "sla_extension_hours >= 0 AND sla_extension_total_hours >= 0 AND sla_extension_count >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("requests_gia_han_khong_am", "requests", type_="check")
    op.drop_column("requests", "sla_extension_count")
    op.drop_column("requests", "sla_extension_total_hours")
    op.drop_column("requests", "sla_extension_hours")
