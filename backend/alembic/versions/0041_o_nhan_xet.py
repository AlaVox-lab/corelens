# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ô "Nhận xét" ở bước cho chấm mức hài lòng — Xác nhận đạt (#559).
#
# Mã bản sửa    : 0041_o_nhan_xet
# Sửa đổi từ    : 0040_o_cach_giai_quyet
#
# Từ #557 cạnh cho chấm (#433) chỉ có một ô chữ: ghi chú của bước, cũng là nhận xét kèm điểm. Cổng người gửi gọi ô
# đó là "Nhận xét" bằng chữ dự phòng, còn cạnh trong dữ liệu khởi tạo không có tên ô — nên dòng thời gian ghi chú
# của bước Xác nhận đạt dưới nhãn mặc định "Lý do", lệch với chữ người gửi vừa thấy. Seed 01 đặt `note_label =
# 'Nhận xét'` cho cụm mới; bản sửa này đặt nó ở cụm cũ.
#
# CÓ ĐIỀU KIỆN, cùng lối 0040: chỉ đặt khi tên ô còn trống — quản trị viên đã đặt tên khác ở màn cấu hình thì giữ.
# `downgrade` gỡ ngược với cùng điều kiện: chỉ ô còn đúng tên này. Cạnh nhận ra bằng cờ dữ liệu `collects_feedback`
# (0036) — không mã hoạt động nào —, cạnh của người, mọi bộ quy tắc của quy trình mặc định (bộ cũ còn hồ sơ đang
# chạy). Cụm mới dựng chưa có dòng nào lúc migration chạy (bộ nạp chạy seed sau), nên bản sửa không làm gì ở đó.
#
# Chỉ đổi dữ liệu, không đổi lược đồ: nâng cấp bằng `up -d --build`, không `down -v`.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0041_o_nhan_xet"
down_revision: str | None = "0040_o_cach_giai_quyet"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tên ô, cùng chữ dự phòng của cổng người gửi (`thao-tac-ho-so.tsx`)
TEN_O = "Nhận xét"

_CANH = """
    collects_feedback AND NOT is_system
    AND rule_set_id IN (
        SELECT id FROM rule_sets WHERE process_code = (SELECT code FROM processes WHERE is_app_default)
    )
"""
_DAT = sa.text(
    f"UPDATE transitions SET note_label = :ten WHERE {_CANH} AND coalesce(btrim(note_label), '') = ''"
)
_GO = sa.text(f"UPDATE transitions SET note_label = NULL WHERE {_CANH} AND note_label = :ten")


def dat_ten_o(ket_noi: sa.Connection) -> int:
    """Đặt tên ô cho cạnh cho chấm còn trống tên ô. Trả số cạnh đã đổi.

    Tách khỏi `upgrade` để bài kiểm gọi thẳng trên giao dịch của nó (backend/tests/test_o_nhan_xet.py)."""
    return ket_noi.execute(_DAT, {"ten": TEN_O}).rowcount


def go_ten_o(ket_noi: sa.Connection) -> int:
    """Gỡ tên ô ở cạnh còn đúng tên này — tên quản trị viên tự đặt thì giữ. Trả số cạnh đã đổi."""
    return ket_noi.execute(_GO, {"ten": TEN_O}).rowcount


def upgrade() -> None:
    dat_ten_o(op.get_bind())


def downgrade() -> None:
    go_ten_o(op.get_bind())
