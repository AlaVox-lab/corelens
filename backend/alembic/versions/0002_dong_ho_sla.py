# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Thêm ba cột theo dõi đồng hồ SLA vào bảng hồ sơ.
#
# Mã bản sửa    : 0002_dong_ho_sla
# Sửa đổi từ    : 0001_ho_so_va_nhat_ky
#
# Cột `states.sla_running` KHÔNG tạo ở đây: bảng `states` thuộc sở hữu của lược đồ
# khởi tạo trong infra/postgres/init/, và Alembic được cấu hình bỏ qua nó. Đổi lược
# đồ khởi tạo thì phải dựng lại thực thể bằng `docker compose down -v`.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_dong_ho_sla"
down_revision: str | None = "0001_ho_so_va_nhat_ky"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Ba cột thay cho một cột hạn chót cố định. Lý do: đồng hồ dừng rồi chạy lại
    # nhiều lần trong đời một hồ sơ, nên một mốc hạn chót tính sẵn sẽ sai ngay lần
    # đầu người dùng bị hỏi thêm thông tin.
    op.add_column(
        "requests",
        sa.Column(
            "sla_running_seconds",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "requests",
        sa.Column(
            "sla_paused_seconds",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "requests",
        sa.Column("sla_segment_since", sa.DateTime(timezone=True), nullable=True),
    )

    # Bộ quét định kỳ lọc theo đúng ba điều kiện này, nên một chỉ mục phần giúp nó
    # không phải duyệt toàn bảng khi số hồ sơ lớn dần.
    op.create_index(
        "requests_dong_ho_dang_chay",
        "requests",
        ["sla_segment_since"],
        postgresql_where=sa.text("sla_segment_since IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("requests_dong_ho_dang_chay", table_name="requests")
    op.drop_column("requests", "sla_segment_since")
    op.drop_column("requests", "sla_paused_seconds")
    op.drop_column("requests", "sla_running_seconds")
