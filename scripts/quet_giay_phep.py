# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Quét giấy phép của MỌI gói, kể cả gói kéo theo gián tiếp, chặn giấy phép ngoài danh sách cho phép (#418).
#
# Bảng điểm trừ 5 điểm khi giấy phép không tương thích; một gói gián tiếp mang BSL, SSPL hay Commons Clause
# sẽ lọt qua mắt người đọc docs/dependencies.md. Danh sách cho phép ở scripts/giay_phep.toml. Chạy ở gốc kho:
#
#     python scripts/quet_giay_phep.py                                   # chỉ các gói npm
#     python scripts/quet_giay_phep.py --anh backend=dxlab-backend:0.3.0 --anh khai-pha=dxlab-khai-pha:0.3.0
#     python scripts/quet_giay_phep.py ... --bao-cao bao-cao-giay-phep.md
#
# Nguồn giấy phép:
#   - npm: trường `license` của từng gói trong package-lock.json — không cần cài gì
#   - Python: siêu dữ liệu gói ĐÃ CÀI TRONG ẢNH (`docker run`), đúng bộ gói người dùng nhận. Đọc bằng
#     importlib.metadata: `License-Expression` (PEP 639) trước, rồi trường `License` ngắn, rồi phân loại.
#     pip-licenses 5.0.0 chưa đọc `License-Expression` nên báo UNKNOWN cho cả chục gói — vì vậy tự đọc.
#
# Chỉ thư viện chuẩn của Python 3.11 trở lên (cần `tomllib`) và lệnh `docker`; thoát 1 khi có gói ngoài danh sách.
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
CAU_HINH = Path(__file__).with_name("giay_phep.toml")
NPM = ("frontend", "docs-site", "e2e")

# Chạy trong ảnh: in một dòng JSON mỗi gói đã cài
DOC_TRONG_ANH = r"""
import importlib.metadata as m, json
for d in m.distributions():
    md = d.metadata
    print(json.dumps({
        "ten": md["Name"], "phien_ban": md["Version"],
        "bieu_thuc": md.get("License-Expression"),
        "ghi": (md.get("License") or "").strip(),
        "phan_loai": [c.split(" :: ")[-1] for c in md.get_all("Classifier") or [] if c.startswith("License ::")],
    }))
"""

# Tên ngắn và phân loại PyPI → mã SPDX
TEN_SPDX = {
    "mit": "MIT", "mit license": "MIT", "bsd-3-clause": "BSD-3-Clause", "bsd 3-clause": "BSD-3-Clause",
    "apache-2.0": "Apache-2.0", "apache 2.0": "Apache-2.0", "apache license 2.0": "Apache-2.0",
    "apache software license": "Apache-2.0", "mpl-2.0": "MPL-2.0",
    "mozilla public license 2.0 (mpl 2.0)": "MPL-2.0", "psf-2.0": "PSF-2.0",
    "python software foundation license": "PSF-2.0", "isc": "ISC", "isc license (iscl)": "ISC",
}


def spdx_python(goi: dict) -> str | None:
    if goi["bieu_thuc"]:
        return goi["bieu_thuc"]
    ghi = goi["ghi"]
    if ghi and "\n" not in ghi and len(ghi) < 40:
        if ma := TEN_SPDX.get(ghi.lower()):
            return ma
        if re.fullmatch(r"[\w.+-]+( (AND|OR) [\w.+-]+)*", ghi):
            return ghi
    ma = {TEN_SPDX.get(p.lower()) for p in goi["phan_loai"]} - {None}
    return ma.pop() if len(ma) == 1 else None


def dat(bieu_thuc: str, cho_phep: set[str]) -> bool:
    """Biểu thức SPDX đạt khi mọi vế AND đạt, mỗi vế OR chỉ cần một nhánh đạt. Ngoặc được bỏ qua — đủ cho
    mọi biểu thức đang có trong kho; biểu thức lạ thì tính là không đạt để người đọc tận tay."""
    phang = bieu_thuc.replace("(", " ").replace(")", " ")
    return all(any(n.strip() in cho_phep for n in ve.split(" OR ")) for ve in phang.split(" AND "))


def goi_npm() -> list[tuple[str, str, str, str | None]]:
    kq = []
    for thu_muc in NPM:
        khoa = json.loads((GOC / thu_muc / "package-lock.json").read_text(encoding="utf-8"))["packages"]
        for duong, goi in khoa.items():
            if duong:
                ten = duong.rsplit("node_modules/", 1)[-1]
                kq.append((thu_muc, ten, goi.get("version", "?"), goi.get("license")))
    return kq


def goi_anh(thanh_phan: str, anh: str) -> list[tuple[str, str, str, str | None]]:
    lenh = ["docker", "run", "--rm", "--entrypoint", "python", anh, "-c", DOC_TRONG_ANH]
    ra = subprocess.run(lenh, capture_output=True, check=False)
    if ra.returncode != 0:
        sys.exit(f"Không đọc được ảnh {anh}: {ra.stderr.decode('utf-8', 'replace')}")
    kq = []
    for dong in ra.stdout.decode("utf-8").splitlines():
        goi = json.loads(dong)
        kq.append((thanh_phan, goi["ten"], goi["phien_ban"], spdx_python(goi)))
    return kq


def main() -> int:
    # Bảng điều khiển Windows mặc định không phải UTF-8 (#368, #472)
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--anh", action="append", default=[], metavar="THÀNH_PHẦN=ẢNH",
                   help="Ảnh Python cần quét, vd backend=dxlab-backend:0.3.0 (nhiều lần)")
    p.add_argument("--bao-cao", type=Path, help="Ghi báo cáo Markdown mọi gói và giấy phép vào tệp này")
    ts = p.parse_args()

    cau_hinh = tomllib.loads(CAU_HINH.read_text(encoding="utf-8"))
    chung = set(cau_hinh["cho_phep"])
    them = {k: set(v) for k, v in cau_hinh.get("them_theo_thanh_phan", {}).items()}
    ngoai_le = cau_hinh.get("ngoai_le", {})

    goi = goi_npm()
    for cap in ts.anh:
        thanh_phan, _, anh = cap.partition("=")
        goi += goi_anh(thanh_phan, anh)

    loi, dong_bao_cao = [], []
    for thanh_phan, ten, phien_ban, giay_phep in sorted(goi):
        nguon = "siêu dữ liệu"
        if ten in ngoai_le and ngoai_le[ten].get("chi_trong", thanh_phan) == thanh_phan:
            # Ngoại lệ chỉ đúng cho đúng phiên bản đã đọc tận tay (#494): bản khác có thể đã đổi giấy phép
            da_doc = ngoai_le[ten].get("phien_ban", [])
            if phien_ban not in da_doc:
                loi.append(f"{thanh_phan}: {ten} {phien_ban} — ngoại lệ chỉ ghi phiên bản đã đọc "
                           f"{', '.join(da_doc) or '(chưa ghi)'}; đọc lại giấy phép của bản này rồi thêm vào phien_ban")
                dong_bao_cao.append(f"| {thanh_phan} | {ten} | {phien_ban} | chưa đọc lại | scripts/giay_phep.toml |")
                continue
            giay_phep, nguon = ngoai_le[ten]["giay_phep"], "scripts/giay_phep.toml"
        cho = chung | them.get(thanh_phan, set())
        # Ngoại lệ đã được người đọc tận tay và ghi lý do, nên đạt dù giấy phép không nằm trong danh sách
        hop_le = nguon != "siêu dữ liệu" or (bool(giay_phep) and dat(giay_phep, cho))
        dong_bao_cao.append(f"| {thanh_phan} | {ten} | {phien_ban} | {giay_phep or '—'} | {nguon} |")
        if not hop_le:
            loi.append(f"{thanh_phan}: {ten} {phien_ban} — {giay_phep or 'không đọc được giấy phép'}")

    if ts.bao_cao:
        ts.bao_cao.write_text(
            "# Giấy phép mọi gói phụ thuộc\n\n| Thành phần | Gói | Phiên bản | Giấy phép | Nguồn |\n"
            "|---|---|---|---|---|\n" + "\n".join(dong_bao_cao) + "\n", encoding="utf-8")
    if loi:
        print("Gói cần xem lại giấy phép — ngoài danh sách cho phép, hay phiên bản chưa đọc (scripts/giay_phep.toml):")
        print("\n".join(f"  {x}" for x in loi))
        return 1
    print(f"Đạt: {len(goi)} gói, mọi giấy phép nằm trong danh sách cho phép.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
