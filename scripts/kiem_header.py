# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm header giấy phép trên mọi tệp mã nguồn kho đang theo dõi.
#
# Bảng điểm trừ 5 điểm khi một tệp mã thiếu giấy phép, nên quy trình tích hợp liên tục
# chạy kịch bản này trên mỗi pull request (#241). Chạy tay ở gốc kho:
#
#     python scripts/kiem_header.py
#
# Tệp đạt khi trong 10 dòng đầu có cả dòng SPDX lẫn dòng bản quyền. Tệp JSON không có
# cú pháp chú thích nên không xét; giấy phép của gói giao diện khai ở trường license
# trong frontend/package.json.

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

DUOI_TEP_MA = {".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".sh", ".css", ".sql"}
TEN_TEP_MA = {"Dockerfile"}
DONG_SPDX = "SPDX-License-Identifier: MIT"
DONG_BAN_QUYEN = "Copyright (c)"
SO_DONG_DAU = 10


def tep_can_kiem() -> list[Path]:
    """Lấy danh sách tệp từ git để bỏ qua node_modules, .next và tệp sinh ra lúc dựng."""
    ket_qua = subprocess.run(
        ["git", "ls-files", "-z"], capture_output=True, check=True
    ).stdout.decode("utf-8")
    return [
        Path(ten)
        for ten in ket_qua.split("\0")
        if ten and (Path(ten).suffix in DUOI_TEP_MA or Path(ten).name in TEN_TEP_MA)
    ]


def thieu_header(tep: Path) -> bool:
    with tep.open(encoding="utf-8", errors="replace") as noi_dung:
        dau_tep = "".join(next(noi_dung, "") for _ in range(SO_DONG_DAU))
    return DONG_SPDX not in dau_tep or DONG_BAN_QUYEN not in dau_tep


def main() -> int:
    danh_sach = tep_can_kiem()
    thieu = [tep for tep in danh_sach if thieu_header(tep)]
    for tep in thieu:
        print(f"Thiếu header giấy phép: {tep.as_posix()}")
    print(f"Đã kiểm {len(danh_sach)} tệp, {len(thieu)} tệp thiếu header.")
    return 1 if thieu else 0


if __name__ == "__main__":
    sys.exit(main())
