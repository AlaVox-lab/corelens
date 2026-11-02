# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Lớp báo cáo của không gian D (#304, #306).
#
# Mã bản sửa    : 0014_lop_bao_cao
# Sửa đổi từ    : 0013_truong_theo_loai
#
# Các view `bao_cao_*` tính sẵn chỉ số cho bảng điều khiển phân tích và cho dữ liệu xuất. Đặt ở
# schema `public` để tài khoản chỉ đọc của nền tảng báo cáo đọc được ngay: lúc dựng cụm, tệp
# `infra/postgres/init/01-tao-cac-database.sh` đã cấp quyền đọc mặc định cho mọi bảng và view
# tạo về sau trong schema này. View chạy bằng quyền của chủ sở hữu, nên tài khoản đó không cần
# đọc thẳng bảng gốc.
#
# Không view nào viết cứng mã trạng thái. Kết thúc hay chưa tra `states.is_terminal`; hồ sơ đã
# tới phòng ban xử lý hay chưa tra `states.sla_running` — hồ sơ hủy trước khi tới phòng, hay
# *Không tiếp nhận*, không bao giờ vào trạng thái chạy đồng hồ, nên tự rơi khỏi thời gian xử lý
# và tỷ lệ vi phạm mà không cần biết tên trạng thái nào. Mỗi hồ sơ xét theo bộ quy tắc của
# chính nó (#278). Thời gian đo bằng giờ làm việc theo lịch mặc định, cùng phép đo với đồng hồ
# hạn. Ngưỡng hạn cùng phép tính với `app/rules/sla.py` `gioi_han_giay`.
#
# Mọi view mà bảng điều khiển đọc đều mang cột `ma_phong`: bản nhúng trong cổng lọc theo phòng
# của người xem bằng một điều kiện trên cột đó (#305). Trung vị không cộng gộp được giữa các
# phòng, nên biểu đồ trung vị tính trên `bao_cao_ho_so` (mỗi hồ sơ một dòng); view
# `bao_cao_thoi_gian_xu_ly` là bản tóm tắt toàn công ty cho dữ liệu xuất.
#
# Đổi một view: tạo bản sửa mới, `CREATE OR REPLACE VIEW` — không sửa tệp này.

from collections.abc import Sequence

from alembic import op

revision: str = "0014_lop_bao_cao"
down_revision: str | None = "0013_truong_theo_loai"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Thứ tự tạo: view sau đọc view trước
VIEW = {
    # Một dòng mỗi hồ sơ — nền của mọi chỉ số
    "bao_cao_ho_so": """
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
                r.sla_running_seconds
            FROM requests r
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
            -- Hàm đếm giờ trả 0 chứ không trả NULL khi thiếu mốc cuối: chặn hồ sơ đang mở
            CASE WHEN ket_thuc IS NOT NULL THEN
                round(so_giay_lam_viec(created_at, ket_thuc) / 3600.0, 2)
            END AS gio_xu_ly,
            round(nguong_giay / 3600.0, 2) AS gio_nguong,
            round(sla_running_seconds / 3600.0, 2) AS gio_dong_ho,
            -- Không cần xét qua_phong: đồng hồ chỉ chạy ở trạng thái sla_running, hồ sơ chưa tới
            -- phòng ban có 0 giây nên không bao giờ vượt ngưỡng
            is_terminal AND nguong_giay IS NOT NULL
                AND sla_running_seconds > nguong_giay AS vi_pham
        FROM co_so
    """,
    # Tồn đọng: hồ sơ chưa kết thúc theo phòng và trạng thái
    "bao_cao_ton_dong": """
        SELECT ma_phong, phong_ban, ma_trang_thai, trang_thai, count(*) AS so_ho_so
        FROM bao_cao_ho_so
        WHERE NOT da_ket_thuc
        GROUP BY ma_phong, phong_ban, ma_trang_thai, trang_thai
    """,
    # Thời gian xử lý trung vị theo loại, so với hạn chuẩn của loại
    "bao_cao_thoi_gian_xu_ly": """
        SELECT
            h.ma_loai,
            h.loai_yeu_cau,
            t.sla_hours AS gio_han_chuan,
            count(*) AS so_ho_so,
            round(percentile_cont(0.5) WITHIN GROUP (ORDER BY h.gio_xu_ly)::numeric, 2)
                AS gio_xu_ly_trung_vi,
            count(*) FILTER (WHERE h.vi_pham) AS so_vi_pham,
            round(100.0 * count(*) FILTER (WHERE h.vi_pham) / count(*), 1) AS ty_le_vi_pham
        FROM bao_cao_ho_so h
        JOIN request_types t ON t.code = h.ma_loai
        WHERE h.da_ket_thuc AND h.da_qua_phong_ban
        GROUP BY h.ma_loai, h.loai_yeu_cau, t.sla_hours
    """,
    # Vi phạm hạn theo phòng và loại — bảng điều khiển tự cộng lên theo phòng hay theo loại
    "bao_cao_vi_pham": """
        SELECT
            ma_phong,
            phong_ban,
            ma_loai,
            loai_yeu_cau,
            count(*) AS so_ho_so,
            count(*) FILTER (WHERE vi_pham) AS so_vi_pham
        FROM bao_cao_ho_so
        WHERE da_ket_thuc AND da_qua_phong_ban
        GROUP BY ma_phong, phong_ban, ma_loai, loai_yeu_cau
    """,
    # Phân bố loại yêu cầu theo tuần gửi, tuần tính theo múi giờ của lịch mặc định
    "bao_cao_phan_bo_loai": """
        SELECT
            date_trunc('week', h.luc_gui AT TIME ZONE l.time_zone)::date AS tuan,
            h.ma_phong,
            h.phong_ban,
            h.ma_loai,
            h.loai_yeu_cau,
            count(*) AS so_ho_so
        FROM bao_cao_ho_so h
        CROSS JOIN (SELECT time_zone FROM work_calendars WHERE is_default) l
        GROUP BY 1, h.ma_phong, h.phong_ban, h.ma_loai, h.loai_yeu_cau
    """,
    # Nhật ký sự kiện để xuất và khai phá quy trình (#306): sáu trường chuẩn cộng thuộc tính
    # hồ sơ, kèm một sự kiện mở đầu dựng từ lúc tạo — việc tạo hồ sơ không phải lần chuyển
    # trạng thái nên không có dòng trong event_log (xem `create_case`). Người thao tác ghi
    # bằng mã định danh; tên và ghi chú không có mặt.
    "bao_cao_nhat_ky": """
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
            0::bigint AS thu_tu
        FROM requests r
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
            e.id AS thu_tu
        FROM event_log e
        JOIN requests r ON r.id = e.case_id
    """,
}


def upgrade() -> None:
    for ten, cau in VIEW.items():
        op.execute(f"CREATE VIEW {ten} AS {cau}")


def downgrade() -> None:
    for ten in reversed(VIEW):
        op.execute(f"DROP VIEW IF EXISTS {ten}")
