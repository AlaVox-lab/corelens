# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Cập nhật thời gian thực cho cổng người dùng (#387): báo "hồ sơ vừa đổi" qua kênh NOTIFY của PostgreSQL.
#
# Mã bản sửa    : 0029_bao_thay_doi_ho_so
# Sửa đổi từ    : 0028_nhieu_quy_trinh
#
# Một hàm trigger gửi `pg_notify('ho_so_thay_doi', <mã hồ sơ>)` sau mỗi lần:
#
#   - tạo hay sửa một dòng `requests` — mọi bước chuyển trạng thái, sửa nội dung, giao người, gia hạn đều đi
#     qua đây, nên không phải đặt trigger trên `event_log` (bảng chỉ ghi thêm, giữ nguyên);
#   - thêm một lời nhắn vào `case_messages` — lời nhắn không đổi dòng hồ sơ.
#
# Tín hiệu chỉ mang mã hồ sơ, không mang nội dung. Dịch vụ ứng dụng nghe kênh này ở `GET /me/stream`
# (app/thoi_gian_thuc.py), lọc theo quyền xem của từng người rồi mới đẩy đi. PostgreSQL chỉ phát NOTIFY khi
# giao dịch commit, và gộp các tín hiệu trùng nhau trong cùng một giao dịch — một bước chuyển sửa hồ sơ nhiều
# lần vẫn ra một tín hiệu. Không ai nghe thì tín hiệu bị bỏ, không tốn gì.
#
# Không đổi dữ liệu: nâng cấp bằng `up -d --build`, không `down -v`.

from collections.abc import Sequence

from alembic import op

revision: str = "0029_bao_thay_doi_ho_so"
down_revision: str | None = "0028_nhieu_quy_trinh"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KENH = "ho_so_thay_doi"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE FUNCTION bao_thay_doi_ho_so() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            -- Bảng hồ sơ dùng cột id, bảng lời nhắn dùng cột case_id; tham số trigger chọn cột
            IF TG_ARGV[0] = 'case_id' THEN
                PERFORM pg_notify('{KENH}', NEW.case_id::text);
            ELSE
                PERFORM pg_notify('{KENH}', NEW.id::text);
            END IF;
            RETURN NULL;
        END;
        $$;

        CREATE TRIGGER bao_thay_doi_ho_so
            AFTER INSERT OR UPDATE ON requests
            FOR EACH ROW EXECUTE FUNCTION bao_thay_doi_ho_so('id');

        CREATE TRIGGER bao_thay_doi_ho_so
            AFTER INSERT ON case_messages
            FOR EACH ROW EXECUTE FUNCTION bao_thay_doi_ho_so('case_id');
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS bao_thay_doi_ho_so ON case_messages;
        DROP TRIGGER IF EXISTS bao_thay_doi_ho_so ON requests;
        DROP FUNCTION IF EXISTS bao_thay_doi_ho_so();
        """
    )
