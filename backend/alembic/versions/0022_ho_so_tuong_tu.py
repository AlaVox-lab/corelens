# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Hồ sơ đã giải quyết tương tự (#319, ADR-0008 đợt 2): phần mở rộng `vector`, chỉ mục và lượt xem.
#
# Mã bản sửa    : 0022_ho_so_tuong_tu
# Sửa đổi từ    : 0021_goi_y_nguoi_xu_ly
#
# BƯỚC 0 — ĐỔI ẢNH POSTGRESQL. Bản này đi cùng việc đổi ảnh `postgres:16-alpine` sang
# `pgvector/pgvector:0.8.6-pg16` (Debian bookworm): cùng PostgreSQL 16 nên thư mục dữ liệu dùng tiếp được, nhưng
# Alpine sắp chữ bằng musl còn Debian bằng glibc. Cùng tên `en_US.utf8`, hai thư viện xếp thứ tự chuỗi
# khác nhau (glibc bỏ qua dấu gạch ở mức đầu, musl so từng byte) — chỉ mục B-tree trên cột chữ dựng
# dưới musl có thể sai thứ tự dưới glibc: tra trùng khóa lọt, tìm theo chỉ mục hụt dòng. PostgreSQL
# không tự báo vì musl không có số phiên bản thứ tự chữ để so.
#
# Dấu hiệu nhận ra: cơ sở dữ liệu không ghi phiên bản thứ tự chữ (`datcollversion` rỗng — dựng dưới
# musl) mà thư viện đang chạy lại có (`pg_database_collation_actual_version` khác rỗng — glibc). Gặp
# đúng dấu hiệu đó thì REINDEX từng cơ sở dữ liệu của cụm (dịch vụ, Keycloak, Superset). Cụm dựng mới
# trên ảnh Debian đã có phiên bản — bỏ qua. Bản sửa này chỉ chạy được trên ảnh có pgvector (bước 1) và
# Alembic chỉ chạy nó một lần, nên không cần dấu "đã sắp lại". Không ghi phiên bản vào `datcollversion`
# được: PostgreSQL từ chối `REFRESH COLLATION VERSION` khi phiên bản cũ rỗng — và để rỗng thì nó cũng
# không cảnh báo gì, đúng như trước khi đổi ảnh.
#
# BƯỚC 1 — `CREATE EXTENSION vector` (pgvector, giấy phép kiểu PostgreSQL).
#
# BƯỚC 2 — hai bảng của tầng I, tách khỏi bảng quyết định:
#
#   similar_case_index   một dòng cho mỗi hồ sơ ĐÃ ĐÓNG ĐẠT: tiêu đề, mô tả, cách giải quyết — đã ẩn
#                        tên người và thông tin liên hệ lúc ghi — loại, lúc đóng, mô hình nhúng và véc-tơ.
#                        Cột véc-tơ không khai số chiều: số chiều thuộc mô hình (cấu hình), không thuộc
#                        lược đồ; câu tìm chỉ so véc-tơ cùng mô hình. Không chỉ mục HNSW — ở quy mô vài
#                        nghìn hồ sơ, quét chính xác đủ nhanh và luôn đúng (ADR-0008, phép B)
#   similar_case_views   một dòng cho mỗi phiên soạn đã thấy gợi ý: hồ sơ nào được gợi ý, phiên đó có
#                        gửi hồ sơ không, hay bỏ không gửi (người gửi bấm, hoặc quá hạn chờ cấu hình)
#
# BƯỚC 3 — view `bao_cao_ngan_chan` cho bảng điều khiển, mang `ma_phong` như mọi view bảng điều khiển
# đọc (mục 6.3): phòng của hồ sơ đứng đầu gợi ý — phòng tránh được một hồ sơ.
#
# Không `down -v`: thêm phần mở rộng, bảng và view; REINDEX không đổi dữ liệu.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022_ho_so_tuong_tu"
down_revision: str | None = "0021_goi_y_nguoi_xu_ly"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


VIEW_NGAN_CHAN = """
    SELECT
        v.session_id AS ma_phien,
        v.viewed_at AS luc_xem,
        date_trunc('week', v.viewed_at) AS tuan,
        CASE
            WHEN v.submitted_case_id IS NOT NULL THEN 'Vẫn gửi yêu cầu'
            WHEN v.abandoned_at IS NOT NULL THEN 'Bỏ không gửi'
            ELSE 'Đang soạn'
        END AS ket_qua,
        (v.submitted_case_id IS NULL AND v.abandoned_at IS NOT NULL)::int AS so_ngan_chan,
        (v.submitted_case_id IS NOT NULL OR v.abandoned_at IS NOT NULL)::int AS so_da_ket_thuc,
        v.abandon_reason AS ly_do_bo,
        cardinality(v.suggested_case_ids) AS so_goi_y,
        r.department_code AS ma_phong,
        coalesce(d.label, 'Chưa rõ phòng') AS phong_ban
    FROM similar_case_views v
    LEFT JOIN requests r ON r.id = v.top_case_id
    LEFT JOIN departments d ON d.code = r.department_code
"""


def _sap_lai_chi_muc_neu_doi_thu_vien() -> None:
    """Bước 0 ở đầu tệp. Chạy ngoài giao dịch của Alembic: REINDEX DATABASE không chạy được trong một
    khối giao dịch, và giao dịch đang mở của Alembic giữ khóa trên bảng vừa sửa ở bản trước."""
    ket_noi = op.get_bind()
    dong = ket_noi.execute(
        sa.text(
            "SELECT datcollversion, pg_database_collation_actual_version(oid)"
            " FROM pg_database WHERE datname = current_database()"
        )
    ).one()
    if dong[0] is not None or dong[1] is None:
        return
    cac_csdl = [
        r[0]
        for r in ket_noi.execute(
            sa.text("SELECT datname FROM pg_database WHERE datallowconn AND NOT datistemplate")
        )
    ]
    goc = ket_noi.engine.url
    with op.get_context().autocommit_block():
        for ten in cac_csdl:
            may = sa.create_engine(goc.set(database=ten), isolation_level="AUTOCOMMIT")
            try:
                with may.connect() as c:
                    c.execute(sa.text(f'REINDEX DATABASE "{ten}"'))
            finally:
                may.dispose()


def upgrade() -> None:
    _sap_lai_chi_muc_neu_doi_thu_vien()

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "similar_case_index",
        sa.Column("case_id", sa.BigInteger(), sa.ForeignKey("requests.id"), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("request_type_code", sa.Text(), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    # Kiểu `vector` không có trong SQLAlchemy — thêm bằng SQL, không thêm gói Python nào
    op.execute("ALTER TABLE similar_case_index ADD COLUMN embedding vector NOT NULL")

    op.create_table(
        "similar_case_views",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("requester_id", sa.Text(), nullable=False),
        sa.Column(
            "viewed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("suggested_case_ids", postgresql.ARRAY(sa.BigInteger()), nullable=False),
        sa.Column("top_case_id", sa.BigInteger(), sa.ForeignKey("requests.id"), nullable=True),
        sa.Column(
            "submitted_case_id", sa.BigInteger(), sa.ForeignKey("requests.id"), nullable=True
        ),
        sa.Column("abandoned_at", sa.DateTime(timezone=True), nullable=True),
        # `requester` — người gửi bấm "không gửi nữa"; `timeout` — quá hạn chờ mà không gửi
        sa.Column("abandon_reason", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_similar_case_views_cho_het_han",
        "similar_case_views",
        ["viewed_at"],
        postgresql_where=sa.text("submitted_case_id IS NULL AND abandoned_at IS NULL"),
    )

    op.execute(f"CREATE VIEW bao_cao_ngan_chan AS {VIEW_NGAN_CHAN}")


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS bao_cao_ngan_chan")
    op.drop_table("similar_case_views")
    op.drop_table("similar_case_index")
    # Phần mở rộng giữ lại: gỡ nó cần quyền và không cần cho bản trước chạy
