# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm số phiên bản trong tệp VERSION ở gốc kho (#552) — nguồn duy nhất của số mà /docs, màn Hệ thống và dịch vụ
# khai phá hiện ra. Số phải đúng dạng MAJOR.MINOR.PATCH và không nhỏ hơn mục phát hành mới nhất của CHANGELOG.md:
# phát hành xong mà quên nâng VERSION thì cổng lại ghi một số cũ, như 0.3.0 nằm yên qua mười mấy bản trước #552.
# Chạy ở gốc kho, chỉ thư viện chuẩn:
#
#     python scripts/kiem_phien_ban.py
from __future__ import annotations

import re
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
MAU_SO = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
# Mục phát hành của git-cliff: "## [1.8.0] - 2026-11-24"; bỏ qua "## [Unreleased]" hay mục không đánh số
MAU_MUC = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", re.MULTILINE)


def bo_so(chuoi: str) -> tuple[int, int, int]:
    m = MAU_SO.match(chuoi)
    if not m:
        raise ValueError(chuoi)
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def kiem(phien_ban: str, nhat_ky: str) -> list[str]:
    """Danh sách lỗi (rỗng là đạt) của số `phien_ban` so với nội dung CHANGELOG.md."""
    try:
        so = bo_so(phien_ban)
    except ValueError:
        return [f"VERSION ghi {phien_ban!r}, không đúng dạng MAJOR.MINOR.PATCH (ví dụ 1.8.1)."]
    cac_muc = MAU_MUC.findall(nhat_ky)
    if not cac_muc:
        return []
    moi_nhat = max(cac_muc, key=bo_so)
    if so < bo_so(moi_nhat):
        return [f"VERSION ghi {phien_ban}, nhỏ hơn bản phát hành mới nhất trong CHANGELOG.md ({moi_nhat}). "
                "Nâng VERSION — CONTRIBUTING.md, mục Phát hành."]
    return []


def main() -> int:
    # Bảng điều khiển Windows mặc định không phải UTF-8 (#368)
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8")
    tep = GOC / "VERSION"
    if not tep.is_file():
        print("Thiếu tệp VERSION ở gốc kho.")
        return 1
    phien_ban = tep.read_text(encoding="utf-8").strip()
    loi = kiem(phien_ban, (GOC / "CHANGELOG.md").read_text(encoding="utf-8"))
    for dong in loi:
        print(dong)
    if not loi:
        print(f"Đạt: VERSION {phien_ban} không nhỏ hơn mục mới nhất của CHANGELOG.md.")
    return 1 if loi else 0


if __name__ == "__main__":
    sys.exit(main())
