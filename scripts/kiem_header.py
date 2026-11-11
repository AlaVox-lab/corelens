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
# Kho theo mô hình nhiều giấy phép (#340, LICENSES.md): mã trong services/khai-pha/ theo
# AGPL-3.0-or-later, mọi nơi khác theo MIT. Tệp đạt khi trong 10 dòng đầu có dòng SPDX ĐÚNG
# giấy phép của thư mục chứa nó và dòng bản quyền; mang giấy phép của thư mục khác cũng là lỗi.
# Tệp JSON không có cú pháp chú thích nên không xét; giấy phép của gói giao diện khai ở trường
# license trong frontend/package.json.

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

DUOI_TEP_MA = {".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".sh", ".css", ".sql"}
TEN_TEP_MA = {"Dockerfile"}
GIAY_PHEP_MAC_DINH = "MIT"
# Thư mục mang giấy phép riêng, khớp với bảng trong LICENSES.md
GIAY_PHEP_THEO_THU_MUC = {
    "services/khai-pha/": "AGPL-3.0-or-later",
}
MAU_SPDX = re.compile(r"SPDX-License-Identifier:\s*(\S+)")
DONG_BAN_QUYEN = "Copyright (c)"
SO_DONG_DAU = 10


def tep_can_kiem() -> list[Path]:
    """Lấy danh sách tệp từ git để bỏ qua node_modules, .next và tệp sinh ra lúc dựng.

    Gồm cả tệp mới chưa `git add` (không nằm trong .gitignore) và bỏ tệp đã xóa mà chưa commit,
    để chạy ở máy trước khi commit kiểm đúng thứ sắp vào kho."""
    ket_qua = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    return [
        Path(ten)
        for ten in dict.fromkeys(ket_qua.split("\0"))
        if ten
        and (Path(ten).suffix in DUOI_TEP_MA or Path(ten).name in TEN_TEP_MA)
        and Path(ten).is_file()
    ]


def giay_phep_can_co(duong_dan: str) -> str:
    """Giấy phép một tệp phải mang, theo thư mục chứa nó (đường dẫn tương đối từ gốc kho)."""
    ten = PurePosixPath(duong_dan.replace("\\", "/")).as_posix()
    for thu_muc, giay_phep in GIAY_PHEP_THEO_THU_MUC.items():
        if ten.startswith(thu_muc):
            return giay_phep
    return GIAY_PHEP_MAC_DINH


def loi_header(duong_dan: str, dau_tep: str) -> str | None:
    """Mô tả lỗi header của một tệp, hoặc None nếu đạt. Tách khỏi việc đọc tệp để thử trên chuỗi mẫu."""
    can_co = giay_phep_can_co(duong_dan)
    tim_thay = MAU_SPDX.search(dau_tep)
    if not tim_thay or DONG_BAN_QUYEN not in dau_tep:
        return f"Thiếu header giấy phép (cần {can_co})"
    if tim_thay.group(1) != can_co:
        return f"Sai giấy phép theo thư mục: mang {tim_thay.group(1)}, cần {can_co}"
    return None


def doc_dau_tep(tep: Path) -> str:
    with tep.open(encoding="utf-8", errors="replace") as noi_dung:
        return "".join(next(noi_dung, "") for _ in range(SO_DONG_DAU))


def main() -> int:
    danh_sach = tep_can_kiem()
    so_loi = 0
    for tep in danh_sach:
        loi = loi_header(tep.as_posix(), doc_dau_tep(tep))
        if loi:
            so_loi += 1
            print(f"{loi}: {tep.as_posix()}")
    print(f"Đã kiểm {len(danh_sach)} tệp, {so_loi} tệp lỗi header.")
    return 1 if so_loi else 0


if __name__ == "__main__":
    sys.exit(main())
