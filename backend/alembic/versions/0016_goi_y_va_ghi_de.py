# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Dấu giữ hay ghi đè gợi ý của hệ thống, và chỉ số của nó trên lớp báo cáo (#239).
#
# Mã bản sửa    : 0016_goi_y_va_ghi_de
# Sửa đổi từ    : 0015_pham_vi_bao_cao
#
# `event_log.suggestion` — mỗi lần chuyển trạng thái mà người dùng gửi một trường có gợi ý, cửa
# chuyển trạng thái ghi {trường: {suggested, chosen, overridden, source, confidence}} (xem
# `app/intelligence/goi_y.py`). Cột riêng, không trộn vào `changes`: `changes` giữ đúng một nghĩa
# "trường nào đổi từ gì sang gì", và mọi chỗ đang đọc nó — dòng thời gian, dữ liệu xuất, bộ sinh
# nhật ký ảo — không phải biết thêm một khóa lạ.
#
# Bảng nhật ký chỉ ghi thêm (trigger chặn UPDATE và DELETE), nhưng thêm cột thì không đụng dòng
# nào. Các dòng cũ mang NULL — trước bản này không ai ghi giữ hay ghi đè, và không bịa ra được.
# Chỉ thêm cột và view, nên nâng cấp cụm cũ không phải `down -v`.
#
# `bao_cao_goi_y` — một dòng cho mỗi gợi ý đã được xác nhận hay ghi đè, mang `ma_phong` như mọi
# view mà bảng điều khiển đọc (#305). `ma_phong` là phòng hiện tại của hồ sơ, cùng cách các view
# của #304 lọc theo phòng.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_goi_y_va_ghi_de"
down_revision: str | None = "0015_pham_vi_bao_cao"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Nhãn của trường và của nguồn là bản sao của `NHAN_NGUON` trong `app/intelligence/goi_y.py` và
# nhãn trường của dịch vụ. Mã lạ — trường hay nguồn thêm về sau — vẫn hiện nguyên mã thay vì
# biến mất khỏi biểu đồ.
VIEW_GOI_Y = """
    SELECT
        e.id AS ma_su_kien,
        e.case_id AS ma_ho_so,
        e.timestamp AS luc,
        e.activity AS ma_hoat_dong,
        coalesce(t.activity_label, e.activity) AS hoat_dong,
        g.key AS ma_truong,
        CASE g.key
            WHEN 'department_code' THEN 'Phòng ban'
            WHEN 'request_type_code' THEN 'Loại yêu cầu'
            WHEN 'priority_code' THEN 'Mức ưu tiên'
            WHEN 'assignee_id' THEN 'Người xử lý'
            ELSE g.key
        END AS truong,
        g.value ->> 'source' AS ma_nguon,
        CASE g.value ->> 'source'
            WHEN 'routing' THEN 'Bảng ánh xạ loại yêu cầu'
            WHEN 'model' THEN 'Mô hình phân loại'
            ELSE g.value ->> 'source'
        END AS nguon,
        g.value ->> 'suggested' AS gia_tri_goi_y,
        g.value ->> 'chosen' AS gia_tri_chon,
        (g.value ->> 'overridden')::boolean AS ghi_de,
        (g.value ->> 'overridden')::boolean::int AS so_ghi_de,
        (g.value ->> 'confidence')::numeric AS do_tin_cay,
        r.department_code AS ma_phong,
        coalesce(d.label, 'Chưa chuyển phòng') AS phong_ban
    FROM event_log e
    -- Chỉ đối tượng mới bung được: dòng không có gợi ý mang NULL (hay JSON `null` nếu ai đó ghi
    -- thẳng), và `jsonb_each(NULL)` trả không dòng nào. Điều kiện nằm TRONG lời gọi chứ không ở
    -- WHERE, vì PostgreSQL không hứa lọc trước khi gọi hàm của LATERAL.
    CROSS JOIN LATERAL jsonb_each(
        CASE WHEN jsonb_typeof(e.suggestion) = 'object' THEN e.suggestion END
    ) g
    JOIN requests r ON r.id = e.case_id
    LEFT JOIN transitions t
        ON t.rule_set_id = r.rule_set_id
        AND t.from_state = e.from_state
        AND t.to_state = e.to_state
        AND NOT t.is_system
    LEFT JOIN departments d ON d.code = r.department_code
"""


def upgrade() -> None:
    op.add_column("event_log", sa.Column("suggestion", postgresql.JSONB(), nullable=True))
    op.execute(f"CREATE VIEW bao_cao_goi_y AS {VIEW_GOI_Y}")


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS bao_cao_goi_y")
    op.drop_column("event_log", "suggestion")
