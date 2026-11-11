# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Gợi ý người xử lý cho trưởng phòng (#318).
#
# Mã bản sửa    : 0021_goi_y_nguoi_xu_ly
# Sửa đổi từ    : 0020_ghi_chu_goi_y
#
# `requests.assignee_suggestion` — JSONB đi cùng cột `suggested_assignee_id` đã có từ 0001: tên người
# được gợi ý, câu lý do ("đang giữ 2 việc, đã xử lý 14 hồ sơ cùng loại"), số liệu làm căn cứ và lúc
# tính. Cùng nhóm trường GỢI Ý — tầng I ghi, không đi qua cửa chuyển trạng thái. Tách khỏi
# `suggestion_note` của mô hình phân loại (#317) để hai đường ghi không đè ghi chú của nhau.
#
# View `bao_cao_goi_y` thêm nhãn cho nguồn mới `workload` — bản sao của `NHAN_NGUON` trong
# `app/intelligence/goi_y.py`, như ở 0016. `CREATE OR REPLACE` giữ nguyên tên và thứ tự cột, nên
# dataset của Superset không phải sửa.
#
# Chỉ thêm cột và thay view, nên nâng cấp cụm cũ không phải `down -v`.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021_goi_y_nguoi_xu_ly"
down_revision: str | None = "0020_ghi_chu_goi_y"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _view(nhan_nguon_them: str) -> str:
    return f"""
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
            {nhan_nguon_them}
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
    op.add_column(
        "requests", sa.Column("assignee_suggestion", postgresql.JSONB(), nullable=True)
    )
    op.execute(
        "CREATE OR REPLACE VIEW bao_cao_goi_y AS "
        + _view("WHEN 'workload' THEN 'Tải việc và kinh nghiệm'")
    )


def downgrade() -> None:
    op.execute("CREATE OR REPLACE VIEW bao_cao_goi_y AS " + _view(""))
    op.drop_column("requests", "assignee_suggestion")
