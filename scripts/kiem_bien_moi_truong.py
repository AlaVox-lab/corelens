# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm mọi biến trong infra/.env.example có dòng giải thích trên trang Cấu hình (#413).
#
# Bảng điểm trừ 5 điểm khi người dựng không cấu hình được trước khi dịch; biến không có tài liệu là
# biến người dựng không biết để đổi. Chạy ở gốc kho:
#
#     python scripts/kiem_bien_moi_truong.py
#
# Một biến tính là có tài liệu khi tên nó nằm trong dấu `…` trên trang, hoặc được viết gọn theo hai
# cách trang đang dùng: `TIEN_TO_*` (mọi biến bắt đầu bằng TIEN_TO_), và `A_B_MAX` / `_WINDOW_SECONDS`
# (biến A_B_WINDOW_SECONDS — đuôi thay cho đoạn cuối của tên đứng trước).

from __future__ import annotations

import re
import sys
from pathlib import Path

TEP_MAU = Path("infra/.env.example")
TRANG = Path("docs-site/src/content/docs/cai-dat/cau-hinh.md")
MAU_BIEN = re.compile(r"^([A-Z][A-Z0-9_]*)=", re.MULTILINE)
MAU_TEN = re.compile(r"`([A-Z_][A-Z0-9_]*\*?)`")
MAU_DUOI = re.compile(r"`([A-Z][A-Z0-9_]*)`\s*/\s*`(_[A-Z0-9_]+)`")


def bien_trong_mau(noi_dung: str) -> list[str]:
    return list(dict.fromkeys(MAU_BIEN.findall(noi_dung)))


def ten_co_tai_lieu(trang: str) -> tuple[set[str], list[str]]:
    """Tên đầy đủ, và danh sách tiền tố (từ dạng `X_*`) có trên trang."""
    tat_ca = MAU_TEN.findall(trang)
    ten = {t for t in tat_ca if not t.endswith("*")}
    tien_to = [t[:-1] for t in tat_ca if t.endswith("*")]
    for dau, duoi in MAU_DUOI.findall(trang):
        ten.add(dau.rsplit("_", 1)[0] + duoi)
    return ten, tien_to


def bien_thieu(mau: str, trang: str) -> list[str]:
    ten, tien_to = ten_co_tai_lieu(trang)
    return [b for b in bien_trong_mau(mau) if b not in ten and not any(b.startswith(t) for t in tien_to)]


def main() -> int:
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8")
    mau = TEP_MAU.read_text(encoding="utf-8")
    thieu = bien_thieu(mau, TRANG.read_text(encoding="utf-8"))
    for b in thieu:
        print(f"Biến chưa có trên trang Cấu hình: {b}")
    print(f"Đã kiểm {len(bien_trong_mau(mau))} biến, {len(thieu)} biến thiếu tài liệu.")
    return 1 if thieu else 0


if __name__ == "__main__":
    sys.exit(main())
