# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Đối soát docs/dependencies.md với tệp khai báo phụ thuộc (#417).
#
# Mục "Thư viện và gói đính kèm" của bảng điểm chấm trên tài liệu này; phụ thuộc trực tiếp thêm mới mà quên
# ghi thì giám khảo không thấy giấy phép của nó. Chạy ở gốc kho:
#
#     python scripts/doi_soat_phu_thuoc.py
#
# Với mỗi tệp khai báo, mọi phụ thuộc TRỰC TIẾP phải có một dòng trong bảng của mục tương ứng, cột phiên bản
# chứa đúng phiên bản đang ghim (requirements.txt: sau `==`; npm: phiên bản trong package-lock.json), và cột
# giấy phép không để trống. Phụ thuộc gián tiếp không kiểm ở đây — xem #418.
#
# Chỉ dùng thư viện chuẩn; thoát 1 khi có lệch.
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
TAI_LIEU = GOC / "docs" / "dependencies.md"

# Tệp khai báo → tiêu đề mục (## …) trong docs/dependencies.md ghi phụ thuộc của nó
PYTHON = {
    "backend/requirements.txt": "Phụ thuộc dịch vụ ứng dụng",
    "services/khai-pha/requirements.txt": "Phụ thuộc dịch vụ khai phá quy trình",
}
NPM = {
    "frontend": "Phụ thuộc giao diện",
    "docs-site": "Phụ thuộc trang tài liệu",
    "e2e": "Phụ thuộc kiểm thử giao diện",
}


def chuan_hoa(ten: str) -> str:
    return re.sub(r"[-_.]+", "-", ten).lower()


def bang_cua_muc(van_ban: str, tieu_de: str) -> dict[str, tuple[str, str]]:
    """Tên gói (chuẩn hóa) → (ô phiên bản, ô giấy phép) của mọi bảng nằm trong mục `## tieu_de`."""
    khop = re.search(rf"^## {re.escape(tieu_de)}\s*$(.*?)(?=^## |\Z)", van_ban, re.M | re.S)
    if not khop:
        sys.exit(f"docs/dependencies.md không có mục '## {tieu_de}'.")
    kq: dict[str, tuple[str, str]] = {}
    for dong in khop.group(1).splitlines():
        if not dong.startswith("|") or set(dong) <= set("|- "):
            continue
        o = [x.strip() for x in dong.strip("|").split("|")]
        if len(o) < 3 or o[0] in ("Gói", "Thành phần"):
            continue
        # Ô đầu có thể gộp nhiều gói: "`a`, `b`" hoặc "**a** và `b`"; bỏ phần chú thích *(…)*
        ten_o = re.sub(r"\*\([^)]*\)\*", "", o[0])
        for ten in re.findall(r"[@A-Za-z0-9][\w./@-]*", ten_o.replace("**", " ").replace("`", " ")):
            if ten not in ("và", "hoặc"):
                kq[chuan_hoa(ten)] = (o[1], o[2])
    return kq


def phu_thuoc_python(tep: Path) -> dict[str, str]:
    kq = {}
    for dong in tep.read_text(encoding="utf-8").splitlines():
        dong = dong.split("#")[0].strip()
        if m := re.match(r"([A-Za-z0-9_.-]+)(\[[^\]]*\])?==([^\s;]+)", dong):
            kq[m.group(1)] = m.group(3)
    return kq


def phu_thuoc_npm(thu_muc: Path) -> dict[str, str]:
    goi = json.loads((thu_muc / "package.json").read_text(encoding="utf-8"))
    khoa = json.loads((thu_muc / "package-lock.json").read_text(encoding="utf-8"))["packages"]
    ten = {**goi.get("dependencies", {}), **goi.get("devDependencies", {})}
    return {t: khoa.get(f"node_modules/{t}", {}).get("version", "?") for t in ten}


def main() -> int:
    # Bảng điều khiển Windows mặc định không phải UTF-8 (#368, #472)
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8")
    van_ban = TAI_LIEU.read_text(encoding="utf-8")
    lech: list[str] = []
    so_goi = 0
    nguon = [(GOC / f, m, phu_thuoc_python(GOC / f)) for f, m in PYTHON.items()]
    nguon += [(GOC / d / "package.json", m, phu_thuoc_npm(GOC / d)) for d, m in NPM.items()]
    for tep, muc, goi in nguon:
        bang = bang_cua_muc(van_ban, muc)
        for ten, phien_ban in sorted(goi.items()):
            so_goi += 1
            dong = bang.get(chuan_hoa(ten))
            noi = f"{tep.relative_to(GOC).as_posix()}: {ten} {phien_ban}"
            if dong is None:
                lech.append(f"{noi} — không có dòng trong mục '{muc}'")
            elif phien_ban not in dong[0]:
                lech.append(f"{noi} — tài liệu ghi phiên bản {dong[0]!r}")
            elif not dong[1]:
                lech.append(f"{noi} — tài liệu để trống giấy phép")
    if lech:
        print("docs/dependencies.md lệch với tệp khai báo:")
        print("\n".join(f"  {x}" for x in lech))
        return 1
    print(f"Đạt: {so_goi} phụ thuộc trực tiếp đều có dòng, đúng phiên bản, có giấy phép.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
