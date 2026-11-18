# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Đọc lại một bản lưu trữ lạnh (#378): tải bản kê và từng tệp, kiểm mã băm SHA-256, giải nén, đếm dòng CSV
# và so với bản kê — chứng minh báo cáo dựng từ tầng lạnh đọc lại được. Tùy chọn `--doi-chieu` so thêm số
# dòng nhật ký với tầng nóng (nhật ký chỉ ghi thêm nên phải bằng nhau).
#
# Hai nguồn, cùng phép kiểm:
#
#   python scripts/doc_luu_tru.py 2026-10                              # qua container dịch vụ (mặc định)
#   python scripts/doc_luu_tru.py 2026-10 --container kt84-backend
#   python scripts/doc_luu_tru.py 2026-10 --api http://localhost:9080 --token "$TOKEN"   # qua API lõi
#
# Qua container: `docker exec <container> python -m app.analytics.luu_tru_lanh …` đọc thẳng kho đối tượng bằng
# cấu hình của dịch vụ — không cần token. Qua API: GET /core/v1/archive/{kỳ} và các liên kết tải của nó, token
# của một quản trị viên (biến môi trường DXLAB_TOKEN nếu không truyền `--token`).
#
# Chỉ thư viện chuẩn và lệnh `docker`. Thoát mã 0 khi mọi phép kiểm đạt, 1 khi có lệch.

from __future__ import annotations

import argparse
import calendar
import csv
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

TEP_BAN_KE = "manifest.json"


class NguonContainer:
    def __init__(self, container: str) -> None:
        self.container = container

    def _chay(self, *tham_so: str) -> bytes:
        kq = subprocess.run(
            ["docker", "exec", self.container, "python", "-m", "app.analytics.luu_tru_lanh", *tham_so],
            capture_output=True, check=False,
        )
        if kq.returncode != 0:
            sys.exit(f"Lệnh trong {self.container} thất bại: {kq.stderr.decode('utf-8', 'replace').strip()}")
        return kq.stdout

    def so(self, ky: str) -> dict:
        return json.loads(self._chay("so", ky))

    def tai(self, ky: str, ten: str) -> bytes:
        return self._chay("tai", ky, ten)

    def dem_nong(self, ky: str) -> int:
        return json.loads(self._chay("dem-nong", ky))["event_rows"]


class NguonApi:
    def __init__(self, goc: str, token: str) -> None:
        self.goc, self.token = goc.rstrip("/"), token
        self._chi_tiet: dict[str, dict] = {}

    def _goi(self, duong: str) -> bytes:
        yc = urllib.request.Request(self.goc + duong, headers={"Authorization": f"Bearer {self.token}"})
        try:
            with urllib.request.urlopen(yc, timeout=60) as tra:
                return tra.read()
        except urllib.error.HTTPError as loi:
            sys.exit(f"GET {duong} trả {loi.code}: {loi.read().decode('utf-8', 'replace')[:300]}")

    def so(self, ky: str) -> dict:
        self._chi_tiet[ky] = json.loads(self._goi(f"/core/v1/archive/{ky}"))
        return self._chi_tiet[ky]

    def tai(self, ky: str, ten: str) -> bytes:
        return self._goi(f"/core/v1/archive/{ky}/files/{ten}")

    def dem_nong(self, ky: str) -> int:
        nam, thang = int(ky[:4]), int(ky[5:])
        cuoi = calendar.monthrange(nam, thang)[1]
        than = self._goi(f"/core/v1/events?format=csv&from={ky}-01&to={ky}-{cuoi:02d}")
        return len(list(csv.reader(io.StringIO(than.decode("utf-8-sig"))))) - 1


def main() -> int:
    # Bảng điều khiển Windows mặc định không phải UTF-8: không có dòng này, lệnh in câu tiếng Việt đầu tiên
    # ném UnicodeEncodeError trừ khi người chạy tự đặt PYTHONIOENCODING (#368, #472)
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8")
    ts = argparse.ArgumentParser(description="Đọc lại và kiểm một bản lưu trữ lạnh (#378).")
    ts.add_argument("ky", help="Kỳ dạng YYYY-MM")
    ts.add_argument("--container", default="dxlab-backend", help="container dịch vụ ứng dụng (mặc định dxlab-backend)")
    ts.add_argument("--api", help="gốc cổng API, ví dụ http://localhost:9080 — đọc qua API lõi thay vì container")
    ts.add_argument("--token", default=os.environ.get("DXLAB_TOKEN"), help="token quản trị viên khi dùng --api")
    ts.add_argument("--doi-chieu", action="store_true", help="so số dòng nhật ký với tầng nóng")
    a = ts.parse_args()

    if a.api:
        if not a.token:
            sys.exit("Cần --token hoặc biến DXLAB_TOKEN khi đọc qua API.")
        nguon = NguonApi(a.api, a.token)
    else:
        nguon = NguonContainer(a.container)

    loi: list[str] = []
    so = nguon.so(a.ky)
    than_ban_ke = nguon.tai(a.ky, TEP_BAN_KE)
    sha_ban_ke = hashlib.sha256(than_ban_ke).hexdigest()
    dat = sha_ban_ke == so["manifest_sha256"]
    print(f"{'ĐẠT ' if dat else 'LỆCH'} {TEP_BAN_KE}: sha256 {sha_ban_ke[:16]}… so với sổ")
    if not dat:
        loi.append(TEP_BAN_KE)
    ban_ke = json.loads(than_ban_ke)
    if ban_ke.get("period") != a.ky:
        loi.append("kỳ trong bản kê")

    so_dong_nhat_ky = None
    for f in ban_ke["files"]:
        noi_dung = nguon.tai(a.ky, f["name"])
        sha = hashlib.sha256(noi_dung).hexdigest()
        doc = csv.reader(io.StringIO(gzip.decompress(noi_dung).decode("utf-8")))
        tieu_de = next(doc, [])
        dong = sum(1 for _ in doc)
        dat = sha == f["sha256"] and dong == f["rows"] and tieu_de == f["columns"]
        print(f"{'ĐẠT ' if dat else 'LỆCH'} {f['name']}: {dong} dòng (bản kê {f['rows']}), "
              f"sha256 {'khớp' if sha == f['sha256'] else 'KHÔNG khớp'}, cột {'khớp' if tieu_de == f['columns'] else 'KHÔNG khớp'}")
        if not dat:
            loi.append(f["name"])
        if f["content"] == "event_log":
            so_dong_nhat_ky = dong

    for ma, dem in ban_ke.get("processes", {}).items():
        print(f"     quy trình {ma}: {dem['events']} sự kiện, {dem['closed_cases']} hồ sơ kết thúc")

    if a.doi_chieu and so_dong_nhat_ky is not None:
        nong = nguon.dem_nong(a.ky)
        dat = nong == so_dong_nhat_ky
        print(f"{'ĐẠT ' if dat else 'LỆCH'} đối chiếu tầng nóng: {nong} dòng nhật ký, bản lưu {so_dong_nhat_ky}")
        if not dat:
            loi.append("đối chiếu tầng nóng")

    print(f"Kỳ {a.ky}: " + ("đọc lại khớp bản kê." if not loi else f"LỆCH ở {', '.join(loi)}."))
    return 1 if loi else 0


if __name__ == "__main__":
    sys.exit(main())
