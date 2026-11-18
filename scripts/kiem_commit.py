# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm chuẩn Conventional Commits của tiêu đề pull request và của lịch sử commit (#420, #421).
#
# CHANGELOG.md sinh bằng git-cliff với filter_unconventional = true (cliff.toml): commit sai chuẩn bị
# bỏ qua lặng lẽ, và bảng điểm trừ điểm khi changelog thiếu. Pull request được squash nên tiêu đề của
# nó thành dòng đầu commit trên dev — kiểm tiêu đề là chặn lỗi ngay từ cửa. Chỉ thư viện chuẩn.
#
#     python scripts/kiem_commit.py --tieu-de "feat(p-workflow): thêm …"
#     python scripts/kiem_commit.py --lich-su origin/dev
#
# --tieu-de: loại hợp lệ, phạm vi thuộc bảng 12 phạm vi (CONTRIBUTING.md mục 4.3) hoặc hai phạm vi
# của navigator, không bỏ trống phạm vi, mô tả không rỗng, tối đa 64 ký tự (đếm theo ký tự, không byte).
# --lich-su: mọi commit không phải merge trong phạm vi git chỉ ra phải được git-cliff nhận — tức số
# commit bị bỏ qua đúng bằng số merge cộng các commit cliff.toml cố ý bỏ (Initial commit, chore(release)).

from __future__ import annotations

import argparse
import re
import subprocess
import sys

LOAI = ("feat", "fix", "perf", "refactor", "docs", "test", "build", "ci", "chore", "revert")
PHAM_VI = (
    "h-auth", "h-portal", "p-workflow", "p-rules", "d-schema", "d-analytics",
    "i-classify", "i-rag", "i-mining", "infra", "ci", "docs",
)
# Chỉ navigator dùng: cập nhật PROJECT_STATE.md và sinh changelog khi phát hành
PHAM_VI_NAVIGATOR = ("state", "release")
DO_DAI_TOI_DA = 64

# Cùng dạng git-cliff nhận ở chế độ conventional_commits: loại, phạm vi tùy chọn, dấu ! tùy chọn, ": ", mô tả
MAU_CONVENTIONAL = re.compile(r"^(?P<loai>[a-z]+)(\((?P<pham_vi>[^()\s]+)\))?(?P<pha_vo>!)?: (?P<mo_ta>\S.*)$")
# cliff.toml commit_parsers bỏ qua cố ý ba dạng này
MAU_CLIFF_BO_QUA = re.compile(r"^(Merge|Initial commit|chore\(release\))")


def loi_tieu_de(tieu_de: str) -> list[str]:
    """Danh sách lỗi của một tiêu đề pull request; rỗng là đạt."""
    loi = []
    if len(tieu_de) > DO_DAI_TOI_DA:
        loi.append(f"Dài {len(tieu_de)} ký tự, tối đa {DO_DAI_TOI_DA}")
    khop = MAU_CONVENTIONAL.match(tieu_de)
    if not khop:
        loi.append("Không đúng dạng <loại>(<phạm vi>): <mô tả>")
        return loi
    if khop["loai"] not in LOAI:
        loi.append(f"Loại {khop['loai']!r} không thuộc: {', '.join(LOAI)}")
    pham_vi = khop["pham_vi"]
    if not pham_vi:
        loi.append("Thiếu phạm vi — tài liệu chung dùng docs, CI dùng ci, Docker dùng infra")
    elif pham_vi not in PHAM_VI + PHAM_VI_NAVIGATOR:
        loi.append(f"Phạm vi {pham_vi!r} không thuộc bảng 12 phạm vi: {', '.join(PHAM_VI)}")
    return loi


def cliff_nhan(dong_dau: str) -> bool:
    """git-cliff có đưa commit này vào changelog không (bỏ qua các dạng cliff.toml cố ý bỏ)."""
    khop = MAU_CONVENTIONAL.match(dong_dau)
    return bool(khop) and khop["loai"] in LOAI


def commit_bi_bo_sot(pham_vi_git: str) -> list[tuple[str, str]]:
    """Commit sai chuẩn (không phải merge, không thuộc dạng cố ý bỏ) mà git-cliff sẽ lặng lẽ bỏ qua."""
    ra = subprocess.run(
        ["git", "log", "--format=%h%x00%s", pham_vi_git],
        capture_output=True, check=True,
    ).stdout.decode("utf-8")
    sot = []
    for dong in ra.splitlines():
        ma, dong_dau = dong.split("\0", 1)
        if not MAU_CLIFF_BO_QUA.match(dong_dau) and not cliff_nhan(dong_dau):
            sot.append((ma, dong_dau))
    return sot


def main() -> int:
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8")
    ts = argparse.ArgumentParser(description=__doc__)
    nhom = ts.add_mutually_exclusive_group(required=True)
    nhom.add_argument("--tieu-de", help="Tiêu đề pull request cần kiểm")
    nhom.add_argument("--lich-su", help="Phạm vi git cần kiểm, ví dụ origin/dev hay v1.2.0..HEAD")
    a = ts.parse_args()

    if a.tieu_de is not None:
        loi = loi_tieu_de(a.tieu_de.strip())
        for l in loi:
            print(f"Tiêu đề sai chuẩn: {l}")
        print("Tiêu đề đạt." if not loi else f"Tiêu đề: {a.tieu_de!r}")
        return 1 if loi else 0

    sot = commit_bi_bo_sot(a.lich_su)
    for ma, dong_dau in sot:
        print(f"git-cliff sẽ bỏ qua: {ma} {dong_dau}")
    print(f"{len(sot)} commit sai chuẩn trong {a.lich_su}.")
    return 1 if sot else 0


if __name__ == "__main__":
    sys.exit(main())
