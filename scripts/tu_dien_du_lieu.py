# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Từ điển dữ liệu sinh tự động từ mô hình (#446): mỗi bảng mà dịch vụ ứng dụng ánh xạ — bảng là gì, mỗi cột
# kiểu gì, để trống được không, khóa nào, và nghĩa của nó.
#
# Kịch bản ĐỌC TĨNH mã nguồn như `scripts/pha_he.py`: phân tích cú pháp các tệp `backend/app/models/*.py`
# bằng `ast` của thư viện chuẩn, không nhập SQLAlchemy, không cần cụm đang chạy — để chạy được trong việc
# header của tích hợp liên tục. Nguồn của từng phần:
#
#   - Bảng: `__tablename__`; nghĩa là đoạn đầu của docstring lớp.
#   - Cột: mỗi thuộc tính khai `Mapped[...]` (bỏ `relationship`). Kiểu lấy từ đối số đầu của
#     `mapped_column` (`Text`, `BigInteger`, `ARRAY(Text)`…), không có thì suy từ kiểu Python của `Mapped`.
#     `X | None` là để trống được. Khóa chính, `unique`, `ForeignKey("bảng.cột")` đọc từ `mapped_column`.
#   - Nghĩa của cột: các dòng chú thích `#` liền ngay phía trên cột trong mã, hay chú thích cuối dòng.
#   - Bảng chưa có mô hình (dịch vụ đọc bằng SQL thô): dò câu tạo bảng trong `backend/alembic/`, liệt kê
#     tên kèm tệp tạo ra, để trang không im lặng bỏ sót bảng nào. `DROP TABLE` chỉ có trong `downgrade()`.
#
# Thêm cột hay sửa chú thích của cột thì sinh lại trang; `--kiem` không ghi gì, sinh trong bộ nhớ rồi so với
# tệp đang có, lệch thì thoát mã 1 — quên sinh lại là tích hợp liên tục đỏ.
#
#   python scripts/tu_dien_du_lieu.py          # sinh lại trang
#   python scripts/tu_dien_du_lieu.py --kiem   # chỉ kiểm, cho tích hợp liên tục
from __future__ import annotations

import argparse
import ast
import difflib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
THU_MUC_MO_HINH = GOC / "backend" / "app" / "models"
THU_MUC_BAN_SUA = GOC / "backend" / "alembic"
# Câu tạo bảng trong SQL thô (alembic/sql/, op.execute) và trong op.create_table của bản sửa
TAO_BANG = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)|create_table\(\s*[\"'](\w+)", re.I)
TEP_TRANG = GOC / "docs-site" / "src" / "content" / "docs" / "tham-khao" / "tu-dien-du-lieu.md"

# Kiểu Python của `Mapped[...]` → kiểu cột, khi `mapped_column` không ghi kiểu (SQLAlchemy suy cùng cách)
KIEU_TU_PYTHON = {
    "str": "Text",
    "int": "Integer",
    "bool": "Boolean",
    "float": "Float",
    "dt.datetime": "DateTime",
    "datetime": "DateTime",
    "dt.date": "Date",
    "date": "Date",
    "dict": "JSON",
    "list": "JSON",
    "Any": "JSON",
}


@dataclass
class Cot:
    ten: str
    kieu: str
    rong_duoc: bool
    rang_buoc: list[str]
    nghia: str


@dataclass
class Bang:
    ten: str
    lop: str
    tep: str
    nghia: str
    cot: list[Cot] = field(default_factory=list)


def _ten(nut: ast.AST) -> str:
    """Tên đầy đủ của một biểu thức kiểu: `Text`, `postgresql.JSONB`, `ARRAY(Text)`."""
    if isinstance(nut, ast.Name):
        return nut.id
    if isinstance(nut, ast.Attribute):
        return f"{_ten(nut.value)}.{nut.attr}"
    if isinstance(nut, ast.Call):
        # `JSONB()` và `JSONB` là cùng một kiểu
        if not nut.args:
            return _ten(nut.func)
        doi_so = ", ".join(_ten(a) for a in nut.args)
        return f"{_ten(nut.func)}({doi_so})"
    if isinstance(nut, ast.Constant):
        return repr(nut.value)
    return ast.unparse(nut)


def _doan_dau(docstring: str | None) -> str:
    if not docstring:
        return ""
    doan = docstring.strip().split("\n\n")[0]
    return " ".join(dong.strip() for dong in doan.splitlines())


def _chu_thich(dong: list[str], so_dong: int) -> str:
    """Dòng chú thích `#` liền trên dòng `so_dong` (đếm từ 1), cộng chú thích cuối chính dòng đó."""
    tren: list[str] = []
    i = so_dong - 2
    while i >= 0 and dong[i].strip().startswith("#"):
        tren.insert(0, dong[i].strip().lstrip("#").strip())
        i -= 1
    cuoi = ""
    if "  # " in dong[so_dong - 1]:
        cuoi = dong[so_dong - 1].split("  # ", 1)[1].strip()
    return " ".join(p for p in [*tren, cuoi] if p)


def _doc_cot(thuoc_tinh: ast.AnnAssign, dong: list[str]) -> Cot | None:
    if not isinstance(thuoc_tinh.target, ast.Name) or thuoc_tinh.target.id.startswith("_"):
        return None
    chu_thich_kieu = ast.unparse(thuoc_tinh.annotation)
    if not chu_thich_kieu.startswith("Mapped["):
        return None
    goi = thuoc_tinh.value
    if isinstance(goi, ast.Call) and _ten(goi.func) == "relationship":
        return None

    ben_trong = chu_thich_kieu[len("Mapped["):-1]
    rong_duoc = "None" in ben_trong or "Optional" in ben_trong
    kieu_python = ben_trong.replace("| None", "").replace("None |", "").strip()
    kieu = KIEU_TU_PYTHON.get(kieu_python.split("[")[0], kieu_python)
    rang_buoc: list[str] = []
    ten = thuoc_tinh.target.id

    if isinstance(goi, ast.Call) and _ten(goi.func) == "mapped_column":
        cac_doi_so = list(goi.args)
        # Tên cột trong cơ sở dữ liệu khác tên thuộc tính: đối số chuỗi đứng đầu
        if cac_doi_so and isinstance(cac_doi_so[0], ast.Constant) and isinstance(cac_doi_so[0].value, str):
            ten = cac_doi_so.pop(0).value
        for a in cac_doi_so:
            if isinstance(a, ast.Call) and _ten(a.func) == "ForeignKey":
                dich = a.args[0].value if a.args and isinstance(a.args[0], ast.Constant) else _ten(a.args[0])
                rang_buoc.append(f"khóa ngoại → `{dich}`")
            elif isinstance(a, ast.Call) and _ten(a.func) in ("Identity", "Computed"):
                rang_buoc.append(f"`{_ten(a.func)}`")
            else:
                kieu = _ten(a)
        for kw in goi.keywords:
            if kw.arg == "primary_key" and isinstance(kw.value, ast.Constant) and kw.value.value:
                rang_buoc.insert(0, "khóa chính")
            elif kw.arg == "unique" and isinstance(kw.value, ast.Constant) and kw.value.value:
                rang_buoc.append("duy nhất")
            elif kw.arg == "nullable" and isinstance(kw.value, ast.Constant):
                rong_duoc = bool(kw.value.value)
            elif kw.arg == "server_default":
                rang_buoc.append(f"mặc định `{ast.unparse(kw.value)}`")

    return Cot(ten, kieu, rong_duoc, rang_buoc, _chu_thich(dong, thuoc_tinh.lineno))


def doc_mo_hinh() -> list[Bang]:
    bang: list[Bang] = []
    for tep in sorted(THU_MUC_MO_HINH.glob("*.py")):
        nguon = tep.read_text(encoding="utf-8")
        dong = nguon.splitlines()
        for lop in ast.parse(nguon).body:
            if not isinstance(lop, ast.ClassDef):
                continue
            ten_bang = None
            for nut in lop.body:
                if (
                    isinstance(nut, ast.Assign)
                    and any(isinstance(d, ast.Name) and d.id == "__tablename__" for d in nut.targets)
                    and isinstance(nut.value, ast.Constant)
                ):
                    ten_bang = nut.value.value
            if ten_bang is None:
                continue
            b = Bang(ten_bang, lop.name, tep.relative_to(GOC).as_posix(), _doan_dau(ast.get_docstring(lop)))
            for nut in lop.body:
                if isinstance(nut, ast.AnnAssign) and (c := _doc_cot(nut, dong)) is not None:
                    b.cot.append(c)
            bang.append(b)
    return sorted(bang, key=lambda b: b.ten)


def bang_khong_mo_hinh(da_co: set[str]) -> dict[str, str]:
    """Bảng mà bản sửa Alembic tạo ra nhưng không lớp mô hình nào ánh xạ → tệp tạo ra nó."""
    kq: dict[str, str] = {}
    for tep in sorted([*THU_MUC_BAN_SUA.rglob("*.py"), *THU_MUC_BAN_SUA.rglob("*.sql")]):
        for m in TAO_BANG.finditer(tep.read_text(encoding="utf-8")):
            ten = (m.group(1) or m.group(2)).lower()
            if ten not in da_co and ten != "alembic_version":
                kq.setdefault(ten, tep.relative_to(GOC).as_posix())
    return dict(sorted(kq.items()))


def _o(chu: str) -> str:
    return chu.replace("|", "\\|").replace("\n", " ")


def dung_trang(cac_bang: list[Bang], khong_mo_hinh: dict[str, str]) -> str:
    d: list[str] = [
        "---",
        "title: Từ điển dữ liệu",
        "description: Mỗi bảng của dịch vụ ứng dụng — nghĩa, cột, kiểu, khóa — sinh tự động từ mô hình.",
        "sidebar:",
        "  order: 4",
        "---",
        "",
        "<!-- Tệp SINH TỰ ĐỘNG bởi scripts/tu_dien_du_lieu.py từ backend/app/models/. Đừng sửa tay: sửa mô hình",
        "     hay chú thích của cột rồi chạy python scripts/tu_dien_du_lieu.py. Tích hợp liên tục chạy --kiem",
        "     và báo đỏ khi trang này lệch với mô hình. -->",
        "",
        f"{len(cac_bang)} bảng mà dịch vụ ứng dụng ánh xạ, xếp theo tên. Nghĩa của bảng lấy từ docstring của lớp mô",
        "hình, nghĩa của cột từ chú thích ngay trên cột trong mã — cột chưa có chú thích để trống ô *Ý nghĩa*.",
        "Lược đồ do các bản sửa Alembic tạo (`backend/alembic/versions/`); các view báo cáo và nguồn gốc của",
        "chúng ở trang [Phả hệ dữ liệu](../pha-he-du-lieu/).",
        "",
        "| Bảng | Số cột | Mô hình |",
        "|---|---|---|",
    ]
    for b in cac_bang:
        d.append(f"| [`{b.ten}`](#{b.ten}) | {len(b.cot)} | `{b.lop}` · `{b.tep}` |")
    if khong_mo_hinh:
        d += [
            "",
            f"{len(khong_mo_hinh)} bảng khác không có lớp mô hình — dịch vụ đọc và ghi chúng bằng SQL thô, nên trang",
            "này chưa liệt kê cột; định nghĩa đầy đủ ở tệp bản sửa tạo ra chúng:",
            "",
            "| Bảng | Tạo ở |",
            "|---|---|",
        ]
        d += [f"| `{ten}` | `{tep}` |" for ten, tep in khong_mo_hinh.items()]
    for b in cac_bang:
        d += ["", f"## {b.ten}", ""]
        if b.nghia:
            d += [_o(b.nghia), ""]
        d += [f"Mô hình `{b.lop}` trong `{b.tep}`.", "", "| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |",
              "|---|---|---|---|---|"]
        for c in b.cot:
            d.append(
                f"| `{c.ten}` | `{_o(c.kieu)}` | {'có' if c.rong_duoc else 'không'} | "
                f"{_o(', '.join(c.rang_buoc))} | {_o(c.nghia)} |"
            )
    return "\n".join(d) + "\n"


def main() -> int:
    # Bảng điều khiển Windows mặc định không phải UTF-8 (#368, #472)
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8")
    tham_so = argparse.ArgumentParser(description="Sinh hoặc kiểm trang từ điển dữ liệu (#446).")
    tham_so.add_argument("--kiem", action="store_true", help="chỉ kiểm trang đã sinh có khớp mô hình không")
    ts = tham_so.parse_args()

    cac_bang = doc_mo_hinh()
    chu = dung_trang(cac_bang, bang_khong_mo_hinh({b.ten for b in cac_bang}))
    ten = TEP_TRANG.relative_to(GOC).as_posix()
    if not ts.kiem:
        TEP_TRANG.write_bytes(chu.encode("utf-8"))
        print(f"Đã sinh {ten}")
        return 0
    hien = TEP_TRANG.read_bytes().decode("utf-8").replace("\r\n", "\n") if TEP_TRANG.exists() else ""
    if hien == chu:
        print(f"Khớp: {ten}")
        return 0
    print(f"LỆCH: {ten} — chạy `python scripts/tu_dien_du_lieu.py` rồi commit tệp sinh lại.", file=sys.stderr)
    for dong in list(difflib.unified_diff(hien.splitlines(), chu.splitlines(), "đang có", "sinh lại", lineterm=""))[:40]:
        print(dong, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
