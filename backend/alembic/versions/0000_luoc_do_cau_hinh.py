# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Lược đồ cấu hình của engine máy trạng thái — bản sửa gốc của cả chuỗi (#254).
#
# Mã bản sửa    : 0000_luoc_do_cau_hinh
# Sửa đổi từ    : (bản gốc)
#
# Trước #254, mười bảy bảng cấu hình (bộ quy tắc, trạng thái, cạnh, vai trò, ràng buộc, cơ cấu tổ
# chức, loại lời nhắn, lịch làm việc) và hai hàm giờ làm việc do lược đồ khởi tạo của PostgreSQL
# tạo — chạy đúng một lần lúc tạo thực thể, ngoài tầm Alembic. Hai nguồn sự thật cho lược đồ, và
# mọi thay đổi cấu hình đều buộc `down -v`. Bản sửa này đưa phần đó về Alembic.
#
# Nội dung là ảnh chụp lược đồ tại v0.9.1, để nguyên văn trong `alembic/sql/` vì nó dài và có hàm
# PL/pgSQL. Không sửa tệp đó nữa: đổi lược đồ cấu hình từ nay là một bản sửa mới.
#
# Hai đường vào:
#
#   Cụm dựng mới    — bảng chưa có, bản sửa tạo đủ, rồi Alembic chạy tiếp 0001 trở đi.
#   Cụm từ v0.9.x   — `alembic_version` đã ở một bản sau, Alembic coi bản gốc là tổ tiên đã chạy và
#                     không chạy lại. Hàng rào dưới đây chỉ phòng trường hợp lạ: bảng đã có mà bảng
#                     phiên bản Alembic thì trống — khi đó không tạo lại, để không hỏng dữ liệu.

from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0000_luoc_do_cau_hinh"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TEP_LUOC_DO = Path(__file__).resolve().parent.parent / "sql" / "0000_luoc_do_cau_hinh.sql"


def upgrade() -> None:
    ket_noi = op.get_bind()
    if ket_noi.exec_driver_sql("SELECT to_regclass('public.rule_sets')").scalar() is not None:
        return
    # Chạy thẳng qua trình điều khiển, không qua text() của SQLAlchemy: tệp có dấu hai chấm trong
    # phép ép kiểu và giờ, text() sẽ đọc nhầm thành tham số. Không truyền tham số thì psycopg gửi
    # nguyên khối nhiều câu lệnh trong cùng giao dịch của Alembic.
    ket_noi.connection.driver_connection.execute(TEP_LUOC_DO.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Không hạ dưới bản gốc: gỡ lược đồ cấu hình là xóa bộ quy tắc — dựng lại cụm nếu cần"
    )
