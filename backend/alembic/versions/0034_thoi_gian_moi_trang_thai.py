# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Thời gian ở từng trạng thái trên lớp báo cáo (#445).
#
# Mã bản sửa    : 0034_thoi_gian_moi_trang_thai
# Sửa đổi từ    : 0033_ngay_le_2027
#
# `bao_cao_thoi_gian_trang_thai` — một dòng cho mỗi LƯỢT hồ sơ ở một trạng thái, để bảng điều khiển Superset
# vẽ thời gian chờ theo trạng thái. Dịch vụ khai phá đã tính con số này (#315) nhưng chỉ trả qua HTTP cho màn
# Quy trình thực tế, không ghi ra bảng nào Superset đọc được.
#
# Định nghĩa lượt CHÉP ĐÚNG câu `CAU_LUOT` của dịch vụ khai phá (services/khai-pha/app/du_lieu.py), để hai
# nơi ra cùng con số — sửa một bên thì sửa cả bên kia:
#
#   - mỗi lần hồ sơ VÀO một trạng thái là một lượt: sự kiện mở đầu, hay sự kiện đổi trạng thái; cạnh tự trỏ
#     (thao tác không đổi trạng thái, ADR-0005) không mở lượt mới;
#   - lượt kết thúc khi hồ sơ vào trạng thái kế; lượt còn dở tính tới lúc truy vấn (`now()`), để hồ sơ đang
#     kẹt vẫn hiện ra;
#   - đo bằng `so_giay_lam_viec` — giờ làm việc theo lịch mặc định, cùng phép đo với đồng hồ hạn;
#   - trạng thái kết thúc không có thời gian chờ nên không có dòng.
#
# Chỉ quy trình mặc định của ứng dụng, như các view khác của bảng điều khiển và như dịch vụ khai phá khi
# không chỉ định quy trình. Khác dịch vụ khai phá ở một chỗ: không lọc khoảng ngày — Superset tự lọc trên
# `luc_vao`. `ma_phong` là phòng hiện tại của hồ sơ, như mọi view mà bảng điều khiển đọc (#305). Nhãn trạng
# thái lấy theo bộ quy tắc của chính hồ sơ. Quyền đọc của `superset_readonly` có sẵn qua quyền mặc định của lược đồ.
#
# Chỉ thêm view, không đổi dữ liệu: nâng cấp bằng `up -d --build`, không `down -v`.

from collections.abc import Sequence

from alembic import op

revision: str = "0034_thoi_gian_moi_trang_thai"
down_revision: str | None = "0033_ngay_le_2027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VIEW_THOI_GIAN = """
WITH vao AS (
    SELECT n.case_id, n.rule_set_id, n.process_code, n.to_state, n.timestamp AS luc_vao,
           lead(n.timestamp) OVER (PARTITION BY n.case_id ORDER BY n.timestamp, n.thu_tu) AS luc_ra
    FROM bao_cao_nhat_ky n
    WHERE n.from_state IS NULL OR n.from_state <> n.to_state
)
SELECT v.case_id AS ma_ho_so,
       v.to_state AS ma_trang_thai,
       s.label AS trang_thai,
       v.luc_vao,
       v.luc_ra,
       v.luc_ra IS NULL AS dang_o,
       so_giay_lam_viec(v.luc_vao, coalesce(v.luc_ra, now())) AS so_giay_lam_viec,
       round(so_giay_lam_viec(v.luc_vao, coalesce(v.luc_ra, now())) / 3600.0, 2) AS so_gio_lam_viec,
       r.request_type_code AS ma_loai,
       coalesce(t.label, 'Chưa phân loại') AS loai_yeu_cau,
       r.department_code AS ma_phong,
       coalesce(d.label, 'Chưa chuyển phòng') AS phong_ban
FROM vao v
JOIN states s ON s.rule_set_id = v.rule_set_id AND s.code = v.to_state
JOIN requests r ON r.id = v.case_id
LEFT JOIN request_types t ON t.code = r.request_type_code
LEFT JOIN departments d ON d.code = r.department_code
WHERE NOT s.is_terminal
  AND v.process_code = (SELECT code FROM processes WHERE is_app_default)
"""


def upgrade() -> None:
    op.execute(f"CREATE VIEW bao_cao_thoi_gian_trang_thai AS {VIEW_THOI_GIAN}")


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS bao_cao_thoi_gian_trang_thai")
