# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Chỉ mục bài viết của kho tri thức (#321, ADR-0006).
#
# Mã bản sửa    : 0027_bai_tri_thuc
# Sửa đổi từ    : 0026_uy_quyen
#
# Bảng `knowledge_articles`: một dòng cho mỗi bài đã xuất bản, không riêng tư của Wiki.js — tiêu đề, mô tả,
# đoạn đầu, đường dẫn, mốc sửa cuối bên wiki, và véc-tơ nhúng (pgvector, phần mở rộng đã bật ở bản sửa
# 0022). Bộ lập chỉ mục `wiki-index` (app/intelligence/tri_thuc.py) đọc bài qua GraphQL, nhúng lại bài mới
# hay vừa sửa (so `wiki_updated_at`), xóa dòng của bài đã xóa hay thôi xuất bản. Bảng là bản sao dẫn xuất,
# dựng lại được từ wiki bất cứ lúc nào — không phải nguồn sự thật, nên không ghi vết, không chỉ ghi thêm.
#
# Chỉ thêm bảng: cụm cũ nâng lên không cần `down -v`.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_bai_tri_thuc"
down_revision: str | None = "0026_uy_quyen"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_articles",
        sa.Column("page_id", sa.Integer(), primary_key=True),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("locale", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("wiki_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # Kiểu `vector` không có trong SQLAlchemy — thêm bằng SQL như bản sửa 0022
    op.execute("ALTER TABLE knowledge_articles ADD COLUMN embedding vector NOT NULL")


def downgrade() -> None:
    op.drop_table("knowledge_articles")
