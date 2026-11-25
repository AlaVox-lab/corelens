# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Sinh đặc tả OpenAPI của nền tảng lõi `/core/v1` thành tệp trong kho, và kiểm tệp đó còn khớp mã.
#
# Đặc tả đầy đủ chỉ xem được khi cụm đang chạy (`/openapi.json` sau cổng API). Tệp
# docs/api/core-v1.openapi.json cho người đọc kho — giám khảo, ứng dụng tầng trên — thấy hợp đồng API của lõi
# không cần dựng gì, và cho git ghi lại mỗi lần hợp đồng đổi. Ở gốc kho:
#
#     python scripts/dac_ta_loi.py --anh dxlab-backend:local          # ghi lại tệp
#     python scripts/dac_ta_loi.py --anh dxlab-backend:local --kiem   # chỉ so; lệch thì thoát 1 (CI)
#
# Chạy trong ảnh dịch vụ ứng dụng với mã nguồn `backend/` của kho gắn chỉ đọc, nên dùng đúng mã đang sửa mà
# không cần cơ sở dữ liệu hay cụm. FastAPI tự sinh đặc tả từ mã; kịch bản chỉ lọc đường dưới tiền tố lõi và
# bỏ lược đồ không đường nào dùng. Bỏ `info.version` để tệp không đổi mỗi lần nâng phiên bản.
#
# Chỉ thư viện chuẩn và lệnh `docker`.
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
TEP = GOC / "docs" / "api" / "core-v1.openapi.json"

SINH_TRONG_ANH = r"""
import json, re
from app.main import app, TIEN_TO_LOI
d = app.openapi()
d["paths"] = {k: v for k, v in d["paths"].items() if k.startswith(TIEN_TO_LOI)}
d["info"].pop("version", None)
# Giữ lược đồ được đường của lõi tham chiếu, kể cả gián tiếp qua lược đồ khác
lo = d.get("components", {}).get("schemas", {})
can, cho = set(), [json.dumps(d["paths"])]
while cho:
    for ten in re.findall(r'#/components/schemas/([^"]+)', cho.pop()):
        if ten not in can and ten in lo:
            can.add(ten)
            cho.append(json.dumps(lo[ten]))
if lo:
    d["components"]["schemas"] = {k: lo[k] for k in sorted(can)}
dung = {t for v in d["paths"].values() for op in v.values() if isinstance(op, dict) for t in op.get("tags", [])}
d["tags"] = [t for t in d.get("tags", []) if t["name"] in dung]
print(json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True))
"""


def sinh(anh: str) -> str:
    lenh = ["docker", "run", "--rm", "-v", f"{GOC / 'backend'}:/app:ro", "-w", "/app",
            "--entrypoint", "python", anh, "-c", SINH_TRONG_ANH]
    ra = subprocess.run(lenh, capture_output=True, check=False)
    if ra.returncode != 0:
        sys.exit(f"Không sinh được đặc tả trong ảnh {anh}:\n{ra.stderr.decode('utf-8', 'replace')}")
    return ra.stdout.decode("utf-8")


def main() -> int:
    # Bảng điều khiển Windows mặc định không phải UTF-8 (#368)
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Sinh và kiểm đặc tả OpenAPI của nền tảng lõi /core/v1.")
    p.add_argument("--anh", required=True, help="Ảnh dịch vụ ứng dụng đã dựng, vd dxlab-backend:local")
    p.add_argument("--kiem", action="store_true", help="Chỉ so với tệp trong kho; lệch thì thoát 1")
    ts = p.parse_args()

    moi = sinh(ts.anh)
    so_duong = len(json.loads(moi)["paths"])
    if ts.kiem:
        cu = TEP.read_text(encoding="utf-8") if TEP.is_file() else ""
        if cu != moi:
            print(f"{TEP.relative_to(GOC).as_posix()} lệch với mã: API lõi đã đổi mà tệp chưa sinh lại. "
                  f"Chạy: python scripts/dac_ta_loi.py --anh {ts.anh}")
            return 1
        print(f"Khớp: {so_duong} đường của lõi.")
        return 0
    TEP.parent.mkdir(parents=True, exist_ok=True)
    TEP.write_text(moi, encoding="utf-8", newline="\n")
    print(f"Đã ghi {TEP.relative_to(GOC).as_posix()}: {so_duong} đường của lõi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
