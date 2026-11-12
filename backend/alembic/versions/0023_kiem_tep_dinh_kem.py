# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm nội dung, macro và quét mã độc cho tệp đính kèm (#248).
#
# Mã bản sửa    : 0023_kiem_tep_dinh_kem
# Sửa đổi từ    : 0022_ho_so_tuong_tu
#
# `attachment_file_types` — mỗi đuôi tệp một dòng: chữ ký đầu tệp (hex, `??` là byte bất kỳ), loại
# nội dung trả khi tải về, cách dò macro. Trước #248 bảng ánh xạ này nằm trong mã; nay là dữ liệu,
# nạp từ `infra/seed/04-loai-tep-dinh-kem.sql`. Đuôi nào được NHẬN vẫn do biến môi trường quyết.
#
# Hai cột mới trên `case_attachments`, ghi một lần lúc đính kèm (bảng chỉ ghi thêm):
#   has_macro    tệp mang macro (định dạng có macro, hay gói Office có `vbaProject.bin`) — nhận
#                nhưng giao diện cảnh báo ở mọi nơi liệt kê tệp
#   scan_status  `disabled` (quét mã độc tắt, như mọi tệp trước #248), `clean` (đã quét, sạch),
#                `unscanned` (quét bật mà dịch vụ quét không phản hồi; chính sách cho nhận)
#
# Dữ liệu cho cụm cũ: bộ nạp dữ liệu khởi tạo chỉ chạy khi cơ sở dữ liệu chưa có bộ quy tắc nào
# (app/cau_hinh/khoi_tao.py), nên cụm dựng trước #248 không bao giờ nạp tệp 04. Bản sửa này chạy
# chính tệp đó khi cụm đã có bộ quy tắc — một nguồn dữ liệu duy nhất, không chép lại vào đây. Cụm
# dựng mới thì bỏ qua: bộ nạp chạy tệp 04 ngay sau Alembic. Không thấy tệp (Alembic chạy ngoài
# container, không gắn `infra/seed/`) thì chỉ cảnh báo: bảng rỗng nghĩa là chỉ kiểm đuôi, như cũ.
#
# Chỉ thêm bảng và cột có mặc định, nên nâng cấp cụm cũ không phải `down -v`.

import logging
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.cau_hinh.khoi_tao import bo_lenh_psql
from app.config import get_settings

revision: str = "0023_kiem_tep_dinh_kem"
down_revision: str | None = "0022_ho_so_tuong_tu"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TEP_DU_LIEU = "04-loai-tep-dinh-kem.sql"

log = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    op.create_table(
        "attachment_file_types",
        sa.Column("extension", sa.Text(), primary_key=True),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column(
            "signatures",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("search_bytes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("text_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("macro_check", sa.Text(), nullable=True),
        sa.Column("always_macro", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "extension ~ '^[a-z0-9]+$'", name="attachment_file_types_duoi_chu_thuong"
        ),
        sa.CheckConstraint(
            "search_bytes BETWEEN 0 AND 8192", name="attachment_file_types_vung_tim"
        ),
        sa.CheckConstraint(
            "macro_check IS NULL OR macro_check IN ('ooxml', 'ole')",
            name="attachment_file_types_cach_do_macro",
        ),
        # Mỗi mẫu là cặp chữ số hex hoặc `??`; mẫu viết sai thì hỏng ngay lúc nạp, không phải lúc tải tệp
        sa.CheckConstraint(
            "array_to_string(signatures, ',') ~ '^((([0-9a-f]{2}|[?][?])+)(,|$))*$'",
            name="attachment_file_types_mau_hex",
        ),
    )

    op.add_column(
        "case_attachments",
        sa.Column("has_macro", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "case_attachments",
        sa.Column(
            "scan_status", sa.Text(), nullable=False, server_default=sa.text("'disabled'")
        ),
    )
    op.create_check_constraint(
        "case_attachments_trang_thai_quet",
        "case_attachments",
        "scan_status IN ('disabled', 'clean', 'unscanned')",
    )

    ket_noi = op.get_bind()
    cum_cu = ket_noi.execute(sa.text("SELECT EXISTS (SELECT 1 FROM rule_sets)")).scalar_one()
    if not cum_cu:
        return
    tep = Path(get_settings().seed_dir) / TEP_DU_LIEU
    if not tep.is_file():
        log.warning(
            "Không thấy %s — bảng attachment_file_types rỗng, tệp đính kèm chỉ được kiểm đuôi", tep
        )
        return
    # Gửi thẳng qua psycopg như bộ nạp: tệp có dấu `%` trong chú thích, đi qua lớp tham số của
    # SQLAlchemy thì bị hiểu nhầm là chỗ chèn tham số
    ket_noi.connection.driver_connection.execute(bo_lenh_psql(tep.read_text(encoding="utf-8")))


def downgrade() -> None:
    op.drop_constraint("case_attachments_trang_thai_quet", "case_attachments", type_="check")
    op.drop_column("case_attachments", "scan_status")
    op.drop_column("case_attachments", "has_macro")
    op.drop_table("attachment_file_types")
