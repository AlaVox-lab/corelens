# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Tạo bảng hồ sơ yêu cầu và bảng nhật ký sự kiện.
#
# Mã bản sửa    : 0001_ho_so_va_nhat_ky
# Sửa đổi từ    : (bản đầu tiên)
#
# Migration này giả định mười một bảng cấu hình của engine máy trạng thái ĐÃ TỒN TẠI,
# do infra/postgres/init/02-luoc-do-quy-trinh.sql tạo lúc PostgreSQL khởi tạo thực thể.
# Chạy trên một cơ sở dữ liệu trống hoàn toàn sẽ thất bại ở bước tạo khóa ngoại — và
# đó là thất bại đúng, nó báo rằng nền lược đồ chưa được dựng.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_ho_so_va_nhat_ky"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "requests",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("rule_set_id", sa.SmallInteger(), nullable=False),
        sa.Column("current_state", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requester_id", sa.Text(), nullable=False),
        # Trường quyết định — chỉ con người ghi
        sa.Column("request_type_code", sa.Text(), nullable=True),
        sa.Column("department_code", sa.Text(), nullable=True),
        sa.Column("priority_code", sa.Text(), nullable=True),
        sa.Column("assignee_id", sa.Text(), nullable=True),
        # Trường gợi ý — chỉ tầng I ghi, không bao giờ ghi đè trường quyết định
        sa.Column("suggested_request_type_code", sa.Text(), nullable=True),
        sa.Column("suggested_department_code", sa.Text(), nullable=True),
        sa.Column("suggested_priority_code", sa.Text(), nullable=True),
        sa.Column("suggested_assignee_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["rule_set_id"], ["rule_sets.id"]),
        # Khóa ngoại tổng hợp: trạng thái hiện tại phải là một trạng thái có thật
        # TRONG ĐÚNG bộ quy tắc mà hồ sơ đang chạy theo
        sa.ForeignKeyConstraint(
            ["rule_set_id", "current_state"],
            ["states.rule_set_id", "states.code"],
        ),
        sa.ForeignKeyConstraint(["request_type_code"], ["request_types.code"]),
        sa.ForeignKeyConstraint(["department_code"], ["departments.code"]),
        sa.ForeignKeyConstraint(["priority_code"], ["priorities.code"]),
    )

    op.create_index("requests_tra_theo_trang_thai", "requests", ["current_state"])
    op.create_index("requests_tra_theo_phong_ban", "requests", ["department_code"])

    op.create_table(
        "event_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("case_id", sa.BigInteger(), nullable=False),
        sa.Column("activity", sa.Text(), nullable=False),
        # TIMESTAMPTZ: PostgreSQL quy về UTC lúc lưu, bất kể múi giờ phía ghi vào
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("from_state", sa.Text(), nullable=False),
        sa.Column("to_state", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["case_id"], ["requests.id"]),
    )

    op.create_index("event_log_tra_theo_ho_so", "event_log", ["case_id", "timestamp"])
    op.create_index("event_log_tra_theo_hoat_dong", "event_log", ["activity"])

    # -----------------------------------------------------------------------
    # NHẬT KÝ CHỈ GHI THÊM
    # -----------------------------------------------------------------------
    # Nhật ký sự kiện là bằng chứng về những gì đã xảy ra. Sửa được thì không còn
    # là bằng chứng, và kết quả khai phá quy trình mất cơ sở.
    #
    # Ràng buộc đặt ở tầng cơ sở dữ liệu chứ không ở tầng ứng dụng, vì Superset,
    # công cụ quản trị và mọi kết nối psql đều đi vòng qua tầng ứng dụng.
    op.execute(
        """
        CREATE FUNCTION event_log_chi_ghi_them() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
                'Nhật ký sự kiện chỉ ghi thêm: thao tác % bị từ chối', TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER event_log_chan_sua_xoa
            BEFORE UPDATE OR DELETE ON event_log
            FOR EACH ROW EXECUTE FUNCTION event_log_chi_ghi_them();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS event_log_chan_sua_xoa ON event_log;")
    op.execute("DROP FUNCTION IF EXISTS event_log_chi_ghi_them();")

    op.drop_index("event_log_tra_theo_hoat_dong", table_name="event_log")
    op.drop_index("event_log_tra_theo_ho_so", table_name="event_log")
    op.drop_table("event_log")

    op.drop_index("requests_tra_theo_phong_ban", table_name="requests")
    op.drop_index("requests_tra_theo_trang_thai", table_name="requests")
    op.drop_table("requests")
