# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Đánh giá mức hài lòng của người gửi khi xác nhận hồ sơ hoàn tất (#433).
#
# Mã bản sửa    : 0036_danh_gia_hai_long
# Sửa đổi từ    : 0035_webhook_theo_trigger
#
# Ba phần:
#
#   - Cột `transitions.collects_feedback`: cạnh nào cho người đi cạnh chấm điểm là DỮ LIỆU, không có mã
#     hoạt động nào trong mã nguồn ứng dụng. Cụm cũ: bật cho cạnh Xác nhận đạt của mọi bộ quy tắc thuộc quy
#     trình mặc định của ứng dụng. Cụm mới: bản sửa chạy trước dữ liệu khởi tạo nên câu UPDATE không chạm
#     dòng nào, tệp `infra/seed/01-quy-tac-quy-trinh.sql` tự bật cờ. Quy trình mua sắm mẫu không có cạnh xác
#     nhận của người gửi — để FALSE.
#   - Bảng `case_feedback`: mỗi lần xác nhận có chấm một dòng, gắn đúng dòng nhật ký của lần xác nhận đó
#     (`event_id`), nên hồ sơ mở lại rồi xác nhận lần nữa có dòng thứ hai mà lịch sử vẫn giữ. Chỉ ghi thêm như
#     `case_messages`: trigger chặn sửa và xóa. Không lưu tên người — người chấm là người gửi của hồ sơ.
#   - View `bao_cao_hai_long` cho bảng điều khiển: mỗi hồ sơ đã đóng qua cạnh cho chấm một dòng, điểm của
#     LẦN CHẤM MỚI NHẤT (NULL khi chưa chấm lần nào), mang `ma_phong`/`phong_ban` như mọi view bảng điều khiển
#     đọc (#305). Hồ sơ tự đóng (cạnh không cho chấm) không có dòng nên không vào mẫu số tỷ lệ. Không có cột
#     nhận xét: bảng điều khiển chỉ có số tổng hợp.
#
# Điểm KHÔNG vào nhật ký sự kiện và không qua engine: nó không đổi trường quyết định nào (ADR-0005) — xem
# ARCHITECTURE.md mục 6.1. Quyền đọc view của `superset_readonly` có sẵn qua quyền mặc định của lược đồ.
#
# Chỉ thêm, không đổi dữ liệu có sẵn: nâng cấp bằng `up -d --build`, không `down -v`.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_danh_gia_hai_long"
down_revision: str | None = "0035_webhook_theo_trigger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VIEW_HAI_LONG = """
WITH dong AS (
    SELECT DISTINCT ON (e.case_id) e.case_id, e.timestamp AS luc_dong
    FROM event_log e
    JOIN requests r ON r.id = e.case_id
    JOIN transitions t ON t.rule_set_id = r.rule_set_id
                      AND t.from_state = e.from_state
                      AND t.to_state = e.to_state
                      AND t.activity_code = e.activity
    WHERE t.collects_feedback
    ORDER BY e.case_id, e.timestamp DESC, e.id DESC
),
cham AS (
    SELECT DISTINCT ON (f.case_id) f.case_id, f.score
    FROM case_feedback f
    ORDER BY f.case_id, f.created_at DESC, f.id DESC
)
SELECT d.case_id AS ma_ho_so,
       d.luc_dong,
       c.score AS diem,
       c.score IS NOT NULL AS da_cham,
       r.request_type_code AS ma_loai,
       coalesce(t.label, 'Chưa phân loại') AS loai_yeu_cau,
       r.department_code AS ma_phong,
       coalesce(p.label, 'Chưa chuyển phòng') AS phong_ban
FROM dong d
JOIN requests r ON r.id = d.case_id
JOIN rule_sets rs ON rs.id = r.rule_set_id
LEFT JOIN cham c ON c.case_id = d.case_id
LEFT JOIN request_types t ON t.code = r.request_type_code
LEFT JOIN departments p ON p.code = r.department_code
WHERE rs.process_code = (SELECT code FROM processes WHERE is_app_default)
"""


def upgrade() -> None:
    op.add_column(
        "transitions",
        sa.Column("collects_feedback", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        "COMMENT ON COLUMN transitions.collects_feedback IS 'Người đi cạnh này chấm được mức hài lòng 1–5 kèm "
        "nhận xét, đều tùy chọn (#433) — cạnh Xác nhận đạt của người gửi.'"
    )
    # Cụm cũ: cạnh Xác nhận đạt của quy trình mặc định của ứng dụng, mọi bộ quy tắc (bộ cũ còn hồ sơ đang chạy)
    op.execute(
        """
        UPDATE transitions SET collects_feedback = TRUE
        WHERE activity_code = 'confirm' AND NOT is_system
          AND rule_set_id IN (
              SELECT id FROM rule_sets WHERE process_code = (SELECT code FROM processes WHERE is_app_default)
          )
        """
    )

    op.create_table(
        "case_feedback",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("case_id", sa.BigInteger(), sa.ForeignKey("requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", sa.BigInteger(), sa.ForeignKey("event_log.id"), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("score BETWEEN 1 AND 5", name="case_feedback_score_1_5"),
        sa.UniqueConstraint("event_id", name="case_feedback_once_per_event"),
    )
    op.create_index("case_feedback_tra_theo_ho_so", "case_feedback", ["case_id", "created_at"])
    op.execute(
        "COMMENT ON TABLE case_feedback IS 'Mức hài lòng người gửi chấm khi xác nhận hoàn tất (#433): mỗi lần "
        "xác nhận có chấm một dòng, gắn dòng nhật ký của lần đó. Chỉ ghi thêm; không lưu tên người.'"
    )
    op.execute(
        """
        CREATE FUNCTION case_feedback_chi_ghi_them() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
                'Đánh giá chỉ ghi thêm: thao tác % bị từ chối', TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER case_feedback_chan_sua_xoa
            BEFORE UPDATE OR DELETE ON case_feedback
            FOR EACH ROW EXECUTE FUNCTION case_feedback_chi_ghi_them();
        """
    )

    op.execute(f"CREATE VIEW bao_cao_hai_long AS {VIEW_HAI_LONG}")


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS bao_cao_hai_long")
    op.execute("DROP TRIGGER IF EXISTS case_feedback_chan_sua_xoa ON case_feedback;")
    op.execute("DROP FUNCTION IF EXISTS case_feedback_chi_ghi_them();")
    op.drop_index("case_feedback_tra_theo_ho_so", table_name="case_feedback")
    op.drop_table("case_feedback")
    op.drop_column("transitions", "collects_feedback")
