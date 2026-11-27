# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Nhãn vai theo cách gọi chung của cổng (#561).
#
# Mã bản sửa    : 0042_ten_vai
# Sửa đổi từ    : 0041_o_nhan_xet
#
# Bảng `roles` mang nhãn "Người tạo yêu cầu", "Người phân loại yêu cầu", "Người xét duyệt yêu cầu", "Người xử lý yêu
# cầu", trong khi mọi màn gọi bốn vai đó là người gửi, điều phối viên, trưởng phòng, người xử lý. Nhãn trong dữ liệu
# lộ ra ở màn Cấu hình quy trình (cột "Ai làm"), dải "Bạn đang làm thay … (vai · phòng)" và câu lỗi "Bước này dành
# cho: …" của engine. Seed 01 mang nhãn mới cho cụm mới; bản sửa này đổi ở cụm cũ. Chỉ đổi NHÃN — mã vai trùng tên
# vai trò realm Keycloak, không đổi; mô tả vai không đụng tới.
#
# CÓ ĐIỀU KIỆN, cùng lối 0040: chỉ đổi khi nhãn còn đúng chữ cũ của dữ liệu khởi tạo — quản trị viên đã đặt tên khác
# thì giữ. `downgrade` trả ngược với cùng điều kiện: chỉ nhãn còn đúng chữ mới. Cụm mới dựng chưa có dòng nào lúc
# migration chạy (bộ nạp chạy seed sau), nên bản sửa không làm gì ở đó.
#
# Chỉ đổi dữ liệu, không đổi lược đồ: nâng cấp bằng `up -d --build`, không `down -v`.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0042_ten_vai"
down_revision: str | None = "0041_o_nhan_xet"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Mã vai của dữ liệu khởi tạo → (nhãn cũ của seed trước #561, nhãn mới)
NHAN = {
    "requester": ("Người tạo yêu cầu", "Người gửi"),
    "classifier": ("Người phân loại yêu cầu", "Điều phối viên"),
    "approver": ("Người xét duyệt yêu cầu", "Trưởng phòng"),
    "handler": ("Người xử lý yêu cầu", "Người xử lý"),
}

_DOI = sa.text("UPDATE roles SET label = :moi WHERE code = :ma AND label = :cu")


def doi_nhan(ket_noi: sa.Connection) -> int:
    """Đổi nhãn còn đúng chữ cũ sang chữ mới. Trả số vai đã đổi.

    Tách khỏi `upgrade` để bài kiểm gọi thẳng trên giao dịch của nó (backend/tests/test_ten_vai.py)."""
    return sum(ket_noi.execute(_DOI, {"ma": ma, "cu": cu, "moi": moi}).rowcount for ma, (cu, moi) in NHAN.items())


def tra_nhan(ket_noi: sa.Connection) -> int:
    """Trả nhãn còn đúng chữ mới về chữ cũ — nhãn quản trị viên tự đặt thì giữ. Trả số vai đã đổi."""
    return sum(ket_noi.execute(_DOI, {"ma": ma, "cu": moi, "moi": cu}).rowcount for ma, (cu, moi) in NHAN.items())


def upgrade() -> None:
    doi_nhan(op.get_bind())


def downgrade() -> None:
    tra_nhan(op.get_bind())
