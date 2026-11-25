# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ô "Cách giải quyết" ở bước Hoàn thành xử lý (#556).
#
# Mã bản sửa    : 0040_o_cach_giai_quyet
# Sửa đổi từ    : 0039_ten_hien_thi_corelens
#
# Cách giải quyết của hồ sơ tương tự (#319) lấy từ ghi chú của bước chính người được giao — cạnh "Hoàn thành xử lý"
# — cộng lời nhắn cuối phía xử lý. Cạnh đó trong dữ liệu khởi tạo không đòi ghi chú và không có tên ô, nên cổng không
# hiện ô nào: hồ sơ đi qua cổng thật gần như luôn thành "không ghi lại cách giải quyết". Navigator chốt 25/11: ô KHÔNG
# bắt buộc — dữ liệu đặt `note_label = 'Cách giải quyết'`, `requires_note` giữ FALSE; cổng hiện ô ghi chú khi cạnh có
# tên ô. Seed 01 đã mang tên ô cho cụm mới; bản sửa này đặt nó ở cụm cũ.
#
# CÓ ĐIỀU KIỆN, cùng lối 0039: chỉ đặt khi tên ô còn trống — quản trị viên đã đặt tên khác ở màn cấu hình thì giữ.
# `downgrade` gỡ ngược với cùng điều kiện: chỉ ô còn đúng tên này. Cạnh nhận ra như 0036 nhận cạnh Xác nhận đạt: mã
# hoạt động của dữ liệu khởi tạo, cạnh của người, mọi bộ quy tắc của quy trình mặc định (bộ cũ còn hồ sơ đang chạy).
# Cụm mới dựng chưa có dòng nào lúc migration chạy (bộ nạp chạy seed sau), nên bản sửa không làm gì ở đó.
#
# Chỉ đổi dữ liệu, không đổi lược đồ: nâng cấp bằng `up -d --build`, không `down -v`.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0040_o_cach_giai_quyet"
down_revision: str | None = "0039_ten_hien_thi_corelens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Mã hoạt động của cạnh Hoàn thành xử lý trong dữ liệu khởi tạo (infra/seed/01) và tên ô navigator chốt
HOAT_DONG = "complete"
TEN_O = "Cách giải quyết"

_CANH = """
    activity_code = :hoat_dong AND NOT is_system
    AND rule_set_id IN (
        SELECT id FROM rule_sets WHERE process_code = (SELECT code FROM processes WHERE is_app_default)
    )
"""
_DAT = sa.text(
    f"UPDATE transitions SET note_label = :ten WHERE {_CANH} AND coalesce(btrim(note_label), '') = ''"
)
_GO = sa.text(f"UPDATE transitions SET note_label = NULL WHERE {_CANH} AND note_label = :ten")


def dat_ten_o(ket_noi: sa.Connection) -> int:
    """Đặt tên ô cho cạnh Hoàn thành xử lý còn trống tên ô. Trả số cạnh đã đổi.

    Tách khỏi `upgrade` để bài kiểm gọi thẳng trên giao dịch của nó (backend/tests/test_cach_giai_quyet.py)."""
    return ket_noi.execute(_DAT, {"ten": TEN_O, "hoat_dong": HOAT_DONG}).rowcount


def go_ten_o(ket_noi: sa.Connection) -> int:
    """Gỡ tên ô ở cạnh còn đúng tên này — tên quản trị viên tự đặt thì giữ. Trả số cạnh đã đổi."""
    return ket_noi.execute(_GO, {"ten": TEN_O, "hoat_dong": HOAT_DONG}).rowcount


def upgrade() -> None:
    dat_ten_o(op.get_bind())


def downgrade() -> None:
    go_ten_o(op.get_bind())
