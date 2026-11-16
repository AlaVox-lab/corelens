# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Nền tảng lõi Mức 2: động cơ luồng công việc chạy nhiều quy trình (#376).
#
# Mã bản sửa    : 0028_nhieu_quy_trinh
# Sửa đổi từ    : 0027_bai_tri_thuc
#
# Trước bản sửa này cả hệ thống có đúng một bộ quy tắc đang bật, nên engine chỉ chạy được quy trình của cổng
# yêu cầu nội bộ. Từ đây:
#
#   - Bảng `processes`: danh mục quy trình — mã, tên, mô tả, thứ tự, cờ `is_app_default` (đúng một dòng: quy
#     trình mà các màn của ứng dụng minh họa dùng). Dữ liệu ở infra/seed/00-quy-trinh.sql.
#   - `rule_sets.process_code` và `request_types.process_code` (khóa ngoại, NOT NULL): bộ quy tắc thuộc một
#     quy trình, loại yêu cầu quyết định hồ sơ chạy theo quy trình nào. `requests` không thêm cột: quy trình
#     của hồ sơ suy từ `rule_set_id` mà hồ sơ đã ghim lúc tạo — một nguồn sự thật.
#   - Chỉ mục "cả hệ thống một bộ đang bật" thay bằng "mỗi quy trình một bộ đang bật". `rule_sets.version`
#     vẫn duy nhất toàn bảng: bộ của quy trình khác đặt mã phiên bản khác hẳn (ít đụng nhất — mọi chỗ tra bộ
#     theo version vẫn đúng).
#   - `kiem_tra_cau_hinh()` thêm phép kiểm 11 cho danh mục quy trình (alembic/sql/0028_kiem_tra_cau_hinh.sql).
#   - View báo cáo: `bao_cao_ho_so` — nền mọi biểu đồ của bảng điều khiển — chỉ còn hồ sơ của quy trình mặc
#     định, nên số trên biểu đồ cũ không đổi khi có quy trình thứ hai; thêm cột `ma_quy_trinh`.
#     `bao_cao_nhat_ky` — xuất dữ liệu mở và khai phá — giữ mọi quy trình, thêm cột `process_code` để người
#     đọc tách theo quy trình. Tài khoản chỉ đọc của dịch vụ khai phá được đọc `processes` để tìm quy trình
#     mặc định.
#
# Dữ liệu cho cụm cũ, khuôn 0023/0024: cụm đã có bộ quy tắc thì chạy chính tệp 00 (danh mục quy trình), gán
# mọi bộ và mọi loại yêu cầu sẵn có vào quy trình mặc định, rồi chạy tệp 06 (quy trình mẫu thứ hai) và
# `kiem_tra_cau_hinh()`. Cụm mới để bộ nạp chạy cả hai tệp. Hồ sơ, nhật ký, tệp giữ nguyên: nâng cấp bằng
# `up -d --build`, không `down -v`.

import importlib.util
import logging
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from psycopg import sql

from app.cau_hinh.khoi_tao import bo_lenh_psql
from app.config import get_settings

revision: str = "0028_nhieu_quy_trinh"
down_revision: str | None = "0027_bai_tri_thuc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

THU_MUC_SQL = Path(__file__).resolve().parent.parent / "sql"
TEP_DANH_MUC = "00-quy-trinh.sql"
TEP_QUY_TRINH_MAU = "06-quy-trinh-mua-sam.sql"

log = logging.getLogger("alembic.runtime.migration")

# `bao_cao_ho_so` của 0014, thêm phép nối tới quy trình: chỉ hồ sơ của quy trình mặc định, thêm cột cuối
# `ma_quy_trinh` (CREATE OR REPLACE VIEW chỉ cho thêm cột ở cuối). View tổng hợp đọc view này nên lọc theo.
VIEW_HO_SO = """
    WITH luc_cuoi AS (
        SELECT case_id, max(timestamp) AS luc FROM event_log GROUP BY case_id
    ),
    qua_phong AS (
        SELECT DISTINCT e.case_id
        FROM event_log e
        JOIN requests r ON r.id = e.case_id
        JOIN states s ON s.rule_set_id = r.rule_set_id AND s.code = e.to_state
        WHERE s.sla_running
    ),
    co_so AS (
        SELECT
            r.id,
            r.rule_set_id,
            r.request_type_code,
            t.label AS loai_label,
            r.department_code,
            d.label AS phong_label,
            r.priority_code,
            p.label AS uu_tien_label,
            r.current_state,
            s.label AS trang_thai_label,
            s.is_terminal,
            q.case_id IS NOT NULL AS qua_phong,
            r.created_at,
            CASE WHEN s.is_terminal THEN coalesce(l.luc, r.created_at) END AS ket_thuc,
            CASE WHEN t.code IS NOT NULL THEN
                t.sla_hours::bigint * 3600 * coalesce(p.sla_factor_percent, 100) / 100
                + r.sla_extension_total_hours::bigint * 3600
            END AS nguong_giay,
            r.sla_running_seconds,
            rs.process_code
        FROM requests r
        JOIN rule_sets rs ON rs.id = r.rule_set_id
        JOIN processes pr ON pr.code = rs.process_code AND pr.is_app_default
        JOIN states s ON s.rule_set_id = r.rule_set_id AND s.code = r.current_state
        LEFT JOIN request_types t ON t.code = r.request_type_code
        LEFT JOIN departments d ON d.code = r.department_code
        LEFT JOIN priorities p ON p.code = r.priority_code
        LEFT JOIN luc_cuoi l ON l.case_id = r.id
        LEFT JOIN qua_phong q ON q.case_id = r.id
    )
    SELECT
        id AS ma_ho_so,
        rule_set_id AS bo_quy_tac,
        request_type_code AS ma_loai,
        coalesce(loai_label, 'Chưa phân loại') AS loai_yeu_cau,
        department_code AS ma_phong,
        coalesce(phong_label, 'Chưa chuyển phòng') AS phong_ban,
        priority_code AS ma_uu_tien,
        uu_tien_label AS muc_uu_tien,
        current_state AS ma_trang_thai,
        trang_thai_label AS trang_thai,
        is_terminal AS da_ket_thuc,
        qua_phong AS da_qua_phong_ban,
        created_at AS luc_gui,
        ket_thuc AS luc_ket_thuc,
        CASE WHEN ket_thuc IS NOT NULL THEN
            round(so_giay_lam_viec(created_at, ket_thuc) / 3600.0, 2)
        END AS gio_xu_ly,
        round(nguong_giay / 3600.0, 2) AS gio_nguong,
        round(sla_running_seconds / 3600.0, 2) AS gio_dong_ho,
        is_terminal AND nguong_giay IS NOT NULL
            AND sla_running_seconds > nguong_giay AS vi_pham,
        process_code AS ma_quy_trinh
    FROM co_so
"""

# `bao_cao_nhat_ky` của 0014 thêm cột cuối `process_code`, mọi quy trình
VIEW_NHAT_KY = """
    SELECT
        r.id AS case_id,
        'create-case'::text AS activity,
        r.created_at AS timestamp,
        r.requester_id AS actor,
        NULL::text AS from_state,
        s.code AS to_state,
        r.request_type_code,
        r.department_code,
        r.priority_code,
        r.rule_set_id,
        0::bigint AS thu_tu,
        rs.process_code
    FROM requests r
    JOIN rule_sets rs ON rs.id = r.rule_set_id
    JOIN states s ON s.rule_set_id = r.rule_set_id AND s.is_initial
    UNION ALL
    SELECT
        e.case_id,
        e.activity,
        e.timestamp,
        e.actor,
        e.from_state,
        e.to_state,
        r.request_type_code,
        r.department_code,
        r.priority_code,
        r.rule_set_id,
        e.id AS thu_tu,
        rs.process_code
    FROM event_log e
    JOIN requests r ON r.id = e.case_id
    JOIN rule_sets rs ON rs.id = r.rule_set_id
"""


def _chay_tep_sql(ten: str) -> None:
    # Qua thẳng trình điều khiển như 0018: thân hàm có dấu % và dấu hai chấm
    op.get_bind().connection.driver_connection.execute((THU_MUC_SQL / ten).read_text(encoding="utf-8"))


def _chay_tep_du_lieu(ten: str) -> bool:
    tep = Path(get_settings().seed_dir) / ten
    if not tep.is_file():
        return False
    op.get_bind().connection.driver_connection.execute(bo_lenh_psql(tep.read_text(encoding="utf-8")))
    return True


def _cap_quyen_khai_pha(lenh: str) -> None:
    """Cho (hay thu) tài khoản chỉ đọc của dịch vụ khai phá đọc `processes` — tài khoản tạo ở 0019."""
    goc = op.get_bind().connection.driver_connection
    ten = get_settings().mining_db_user
    if goc.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ten,)).fetchone():
        goc.execute(sql.SQL(lenh).format(sql.Identifier(ten)))


def upgrade() -> None:
    ket_noi = op.get_bind()
    cum_cu = ket_noi.execute(sa.text("SELECT EXISTS (SELECT 1 FROM rule_sets)")).scalar_one()

    op.create_table(
        "processes",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("display_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("is_app_default", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        "COMMENT ON TABLE processes IS 'Danh mục quy trình của động cơ luồng công việc (#376). Mỗi quy "
        "trình có đúng một bộ quy tắc đang bật; loại yêu cầu thuộc một quy trình.'"
    )
    # Đúng một quy trình của ứng dụng minh họa — "không quá một" ở đây, "ít nhất một" ở kiem_tra_cau_hinh()
    op.create_index(
        "processes_mot_quy_trinh_ung_dung", "processes", ["is_app_default"], unique=True,
        postgresql_where=sa.text("is_app_default"),
    )

    for bang in ("rule_sets", "request_types"):
        op.add_column(bang, sa.Column("process_code", sa.Text(), sa.ForeignKey("processes.code"), nullable=True))

    if cum_cu:
        if not _chay_tep_du_lieu(TEP_DANH_MUC):
            raise RuntimeError(
                f"Không thấy {TEP_DANH_MUC} trong {get_settings().seed_dir} — bản sửa 0028 cần danh mục quy "
                "trình để gán bộ quy tắc và loại yêu cầu sẵn có (infra/seed/ gắn vào container ở /seed)."
            )
        for bang in ("rule_sets", "request_types"):
            ket_noi.execute(sa.text(
                f"UPDATE {bang} SET process_code = (SELECT code FROM processes WHERE is_app_default) "
                "WHERE process_code IS NULL"
            ))

    for bang in ("rule_sets", "request_types"):
        op.alter_column(bang, "process_code", nullable=False)
        op.create_index(f"{bang}_theo_quy_trinh", bang, ["process_code"])

    # Một bộ đang bật cho MỖI quy trình, thay cho một bộ cả hệ thống
    op.drop_index("rule_sets_chi_mot_bo_kich_hoat", table_name="rule_sets")
    op.create_index(
        "rule_sets_mot_bo_bat_moi_quy_trinh", "rule_sets", ["process_code"], unique=True,
        postgresql_where=sa.text("is_active"),
    )

    _chay_tep_sql("0028_kiem_tra_cau_hinh.sql")

    op.execute(f"CREATE OR REPLACE VIEW bao_cao_ho_so AS {VIEW_HO_SO}")
    op.execute(f"CREATE OR REPLACE VIEW bao_cao_nhat_ky AS {VIEW_NHAT_KY}")
    _cap_quyen_khai_pha("GRANT SELECT ON processes TO {}")

    if cum_cu:
        if _chay_tep_du_lieu(TEP_QUY_TRINH_MAU):
            log.info("Đã thêm quy trình mẫu thứ hai từ %s", TEP_QUY_TRINH_MAU)
        else:
            log.warning("Không thấy %s — cụm chỉ có quy trình cổng yêu cầu nội bộ", TEP_QUY_TRINH_MAU)
        ket_noi.execute(sa.text("SELECT kiem_tra_cau_hinh()"))


def _view_0014() -> dict[str, str]:
    """Định nghĩa view của 0014 — tên tệp bắt đầu bằng chữ số nên nạp theo đường dẫn."""
    tep = Path(__file__).resolve().parent / "0014_lop_bao_cao.py"
    dac_ta = importlib.util.spec_from_file_location("ban_sua_0014", tep)
    mo_dun = importlib.util.module_from_spec(dac_ta)
    dac_ta.loader.exec_module(mo_dun)
    return mo_dun.VIEW


def downgrade() -> None:
    """Về một quy trình: chỉ được khi cụm chưa có hồ sơ nào của quy trình khác."""
    ket_noi = op.get_bind()
    khac = ket_noi.execute(sa.text(
        "SELECT count(*) FROM requests r JOIN rule_sets rs ON rs.id = r.rule_set_id "
        "JOIN processes p ON p.code = rs.process_code WHERE NOT p.is_app_default"
    )).scalar_one()
    if khac:
        raise RuntimeError(f"Còn {khac} hồ sơ của quy trình khác quy trình mặc định — không hạ được về 0027.")

    _cap_quyen_khai_pha("REVOKE ALL ON processes FROM {}")
    view = _view_0014()
    # Cột thêm ở cuối không gỡ được bằng CREATE OR REPLACE: xóa rồi dựng lại theo 0014, view sau đọc view trước
    op.execute("DROP VIEW bao_cao_phan_bo_loai, bao_cao_vi_pham, bao_cao_thoi_gian_xu_ly, bao_cao_ton_dong, "
               "bao_cao_ho_so, bao_cao_nhat_ky")
    for ten, cau in view.items():
        op.execute(f"CREATE VIEW {ten} AS {cau}")
    _cap_quyen_khai_pha("GRANT SELECT ON bao_cao_nhat_ky TO {}")

    _chay_tep_sql("0025_kiem_tra_cau_hinh.sql")

    # Gỡ quy trình khác cùng cấu hình của nó (chưa có hồ sơ nào, đã kiểm ở trên)
    ket_noi.execute(sa.text(
        "DELETE FROM request_types WHERE process_code IN (SELECT code FROM processes WHERE NOT is_app_default)"
    ))
    khac_bo = "(SELECT id FROM rule_sets WHERE process_code IN (SELECT code FROM processes WHERE NOT is_app_default))"
    for cau in (
        f"DELETE FROM transition_guards WHERE transition_id IN (SELECT id FROM transitions WHERE rule_set_id IN {khac_bo})",
        f"DELETE FROM transition_roles WHERE transition_id IN (SELECT id FROM transitions WHERE rule_set_id IN {khac_bo})",
        f"DELETE FROM transitions WHERE rule_set_id IN {khac_bo}",
        f"DELETE FROM states WHERE rule_set_id IN {khac_bo}",
        f"DELETE FROM rule_sets WHERE id IN {khac_bo}",
    ):
        ket_noi.execute(sa.text(cau))

    op.drop_index("rule_sets_mot_bo_bat_moi_quy_trinh", table_name="rule_sets")
    op.create_index(
        "rule_sets_chi_mot_bo_kich_hoat", "rule_sets", ["is_active"], unique=True,
        postgresql_where=sa.text("is_active"),
    )
    for bang in ("rule_sets", "request_types"):
        op.drop_index(f"{bang}_theo_quy_trinh", table_name=bang)
        op.drop_column(bang, "process_code")
    op.drop_index("processes_mot_quy_trinh_ung_dung", table_name="processes")
    op.drop_table("processes")
