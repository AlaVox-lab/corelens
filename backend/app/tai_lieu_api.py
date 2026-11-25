# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
"""Tài liệu API tự sinh cho người dùng API, không cho người đọc mã (#552).

FastAPI lấy mô tả điểm cuối, tham số và lược đồ từ docstring và `description` trong mã. Những chữ đó viết cho người
phát triển, nên hay kèm số issue và đường dẫn tệp — `(#376)`, `(app/workflow/errors.py)` — có ích khi đọc mã, vô
nghĩa với ứng dụng gọi API ở `/docs`. Thay vì xóa khỏi mã, lúc sinh đặc tả bỏ đi các cặp ngoặc CHỈ chứa số issue hay
đường dẫn tệp mã. Quy ước khi viết docstring: nhắc issue hay tệp thì đặt trong ngoặc, không chen giữa câu.
`tests/test_tai_lieu_api.py` báo lỗi khi còn số issue hay đường dẫn tệp lọt ra, và khi điểm cuối thiếu tóm tắt.
"""

from __future__ import annotations

import re
from typing import Any

# Một mục tham chiếu trong ngoặc: số issue, hay đường dẫn tệp mã (có thể kèm tên hàm trong dấu `, nối bằng "ở")
_MUC = re.compile(
    r"#\d+"
    r"|(?:`[\w.]+`\s+ở\s+)?`?(?:app|backend|frontend|infra|scripts|services)/[\w/.-]+\.(?:py|tsx?|sql)`?"
)
_NGOAC = re.compile(r"\s*\(([^()]*)\)")
_PHAN_CACH = re.compile(r"[\s,;]+")


def _chi_la_tham_chieu(ben_trong: str) -> bool:
    """Trong ngoặc chỉ có số issue, đường dẫn tệp mã và dấu phân cách."""
    if not _MUC.search(ben_trong):
        return False
    return _PHAN_CACH.sub("", _MUC.sub("", ben_trong)) == ""


def lam_sach(chu: str) -> str:
    """Bỏ các cặp ngoặc chỉ chứa tham chiếu nội bộ, cùng khoảng trắng đứng trước: "đang chạy (#376)." → "đang
    chạy."; giữ nguyên mọi chữ khác."""
    return _NGOAC.sub(lambda m: "" if _chi_la_tham_chieu(m.group(1)) else m.group(0), chu)


def lam_sach_dac_ta(nut: Any) -> None:
    """Đi khắp đặc tả OpenAPI, làm sạch mọi chuỗi `description` tại chỗ."""
    if isinstance(nut, dict):
        for khoa, gia_tri in nut.items():
            if khoa == "description" and isinstance(gia_tri, str):
                nut[khoa] = lam_sach(gia_tri)
            else:
                lam_sach_dac_ta(gia_tri)
    elif isinstance(nut, list):
        for gia_tri in nut:
            lam_sach_dac_ta(gia_tri)
