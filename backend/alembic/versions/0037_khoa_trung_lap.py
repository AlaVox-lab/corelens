# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Khóa trùng lặp `Idempotency-Key` cho hai lệnh của nền tảng lõi (#426): tạo hồ sơ và đi một bước chuyển.
#
# Mã bản sửa    : 0037_khoa_trung_lap
# Sửa đổi từ    : 0036_danh_gia_hai_long
#
# Bảng `idempotency_keys`: mỗi lần một người gọi gửi một khóa tới một điểm cuối của lõi là một dòng, duy nhất
# theo (người gọi, điểm cuối, khóa) — hai tài khoản dùng cùng chuỗi khóa không đụng nhau. Dòng sinh ra ở
# trạng thái `in_progress` trong một giao dịch riêng, rồi đổi sang `completed` TRONG CÙNG giao dịch với lần
# tạo hồ sơ hay lần chuyển trạng thái, nên máy chết ngay sau commit thì lần gọi lặp vẫn thấy khóa đã xong và
# không chuyển lần hai. Chỉ lần thành công được giữ: lần bị từ chối xóa dòng của nó, người tích hợp sửa rồi
# gửi lại cùng khóa được. Xem app/workflow/khoa_trung_lap.py.
#
# Không phải dữ liệu nghiệp vụ, không vào nhật ký sự kiện. Không lưu tên người — `actor` là mã người gọi trong
# token. Dòng hết hạn (`expires_at`) được bộ quét nền dọn, cạnh bộ đếm giới hạn tốc độ.
#
# Chỉ thêm, không đổi dữ liệu có sẵn: nâng cấp bằng `up -d --build`, không `down -v`.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0037_khoa_trung_lap"
down_revision: str | None = "0036_danh_gia_hai_long"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("request_hash", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("case_id", sa.BigInteger(), nullable=True),
        sa.Column("response_status", sa.SmallInteger(), nullable=True),
        sa.Column("response_body", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('in_progress', 'completed')", name="idempotency_keys_status_hop_le"),
        sa.CheckConstraint("char_length(key) BETWEEN 1 AND 255", name="idempotency_keys_key_1_255"),
        sa.UniqueConstraint("actor", "endpoint", "key", name="idempotency_keys_mot_khoa_moi_nguoi_goi"),
    )
    op.create_index("idempotency_keys_theo_han", "idempotency_keys", ["expires_at"])
    op.execute(
        "COMMENT ON TABLE idempotency_keys IS 'Khóa trùng lặp Idempotency-Key của lệnh tạo hồ sơ và bước "
        "chuyển ở lõi /core/v1 (#426): gọi lặp cùng khóa trả lại kết quả đã lưu, không chạy lệnh lần hai. "
        "Chỉ giữ lần thành công; không lưu tên người.'"
    )


def downgrade() -> None:
    op.drop_index("idempotency_keys_theo_han", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
