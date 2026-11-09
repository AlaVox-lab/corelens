# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Hàm kiểm tra tính nhất quán của cấu hình quy trình (#254).
#
# Mã bản sửa    : 0018_kiem_tra_cau_hinh
# Sửa đổi từ    : 0017_nhip_quet_gioi_han
#
# Chín phép kiểm mức đồ thị từng nằm trong dữ liệu khởi tạo (`infra/seed/99-…`) và chỉ chạy một
# lần lúc nạp. Thành hàm `kiem_tra_cau_hinh()` thì bộ nạp khởi tạo gọi được mỗi lần dịch vụ khởi
# động, và bản sửa dữ liệu cấu hình gọi được trước khi kích hoạt bộ quy tắc mới — bản cập nhật làm
# hỏng quy trình bị từ chối cùng giao dịch của nó. Nội dung ở `alembic/sql/`, cùng lý do với 0000.
#
# Chỉ thêm một hàm, không đụng dòng nào: cụm cũ nâng lên không cần `down -v`.

from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0018_kiem_tra_cau_hinh"
down_revision: str | None = "0017_nhip_quet_gioi_han"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TEP_HAM = Path(__file__).resolve().parent.parent / "sql" / "0018_kiem_tra_cau_hinh.sql"


def upgrade() -> None:
    # Qua thẳng trình điều khiển như 0000: thông báo lỗi trong hàm có dấu %, thân hàm có dấu hai chấm
    op.get_bind().connection.driver_connection.execute(TEP_HAM.read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS kiem_tra_cau_hinh()")
