# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 AlaVox-lab
#
# Bộ máy khai phá: phần thuật toán, tách sau một giao diện hẹp để thay được (ADR-0007, #314).
#
# Hai bộ máy cho CÙNG kết quả trên cùng dữ liệu:
#
#   pm4py   — mặc định. Thư viện PM4Py (AGPL-3.0-or-later) khám phá đồ thị trực tiếp (DFG) và biến
#             thể. Đây là NƠI DUY NHẤT trong kho `import pm4py`.
#   noi_bo  — dự phòng, Python thuần, không thư viện khai phá nào. Dùng khi giảng viên hay doanh
#             nghiệp không nhận ranh giới AGPL: đặt KHAI_PHA_BO_MAY=noi_bo và gỡ pm4py khỏi
#             requirements.txt, không phải sửa dịch vụ ứng dụng hay cổng.
#
# Đầu vào của cả hai là danh sách LƯỢT VÀO TRẠNG THÁI theo thứ tự thời gian của từng hồ sơ (hoạt
# động = trạng thái hồ sơ vào, theo ghi chú của ADR-0007: một mã hoạt động có thể đi nhiều cạnh).
# Phần còn lại — nhánh lệch, thời gian chờ, điểm nghẽn — tính từ cờ trong dữ liệu ở app/phan_tich.py,
# chung cho cả hai bộ máy. Bài kiểm thử có đáp án biết trước chạy trên cả hai.

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LuotVao:
    """Hồ sơ `ho_so` vào trạng thái `trang_thai` lúc `luc`; `thu_tu` phân xử hai lượt cùng thời điểm."""

    ho_so: int
    trang_thai: str
    luc: dt.datetime
    thu_tu: int


class BoMay(Protocol):
    ten: str

    def do_thi(self, luot: list[LuotVao]) -> dict[tuple[str, str], int]:
        """Đồ thị trực tiếp: (trạng thái trước, trạng thái sau) → số lần nối tiếp nhau."""
        ...

    def bien_the(self, luot: list[LuotVao]) -> dict[tuple[str, ...], list[int]]:
        """Biến thể: chuỗi trạng thái của một hồ sơ → các hồ sơ đi đúng chuỗi đó."""
        ...


def chon_bo_may(ten: str) -> BoMay:
    if ten == "pm4py":
        from .pm4py_bo_may import BoMayPm4py

        return BoMayPm4py()
    if ten == "noi_bo":
        from .noi_bo import BoMayNoiBo

        return BoMayNoiBo()
    raise ValueError(f"KHAI_PHA_BO_MAY không hợp lệ: {ten!r} — chọn 'pm4py' hoặc 'noi_bo'")
