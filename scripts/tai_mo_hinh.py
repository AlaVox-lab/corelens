# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Tải tệp mô hình ngôn ngữ cho hồ sơ Compose `tri-tue` (#316, ADR-0008) vào volume Docker `mo-hinh`.
#
#     python scripts/tai_mo_hinh.py                     # cụm mặc định, dự án Compose `dx-os-lab`
#     python scripts/tai_mo_hinh.py --du-an kt84        # cụm thử tên khác
#     python scripts/tai_mo_hinh.py --thu-muc-tam D:/tam # nơi giữ tệp tải về (mặc định: thư mục tạm)
#
# Tệp tải từ kho chính thức của Qwen trên Hugging Face, GHIM theo mã phiên bản của kho (không theo
# nhánh `main`), và phải khớp SHA-256 ghim dưới đây — lệch là dừng, không đặt gì vào volume. Volume đã
# có tệp đúng mã băm thì không tải lại. `docker compose down -v` xóa cả volume này: chạy lại lệnh.
#
# Không thêm gói nào: chỉ thư viện chuẩn của Python (3.10 trở lên) và lệnh `docker`. Việc chép vào
# volume chạy trong chính ảnh llama.cpp mà dịch vụ `mo-hinh` dùng (thẻ đọc từ docker-compose.yml), nên
# không kéo thêm ảnh nào.
#
# Giấy phép của tệp mô hình: Apache-2.0 (xem NOTICE và docs/dependencies.md).

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

KHO = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
# Mã phiên bản (commit) của kho trên Hugging Face lúc ghim — tệp tải về không đổi dù kho cập nhật
PHIEN_BAN_KHO = "91cad51170dc346986eccefdc2dd33a9da36ead9"
TEN_TEP = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
SHA256 = "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"
KICH_THUOC = 1_117_320_736
URL = f"https://huggingface.co/{KHO}/resolve/{PHIEN_BAN_KHO}/{TEN_TEP}"

GOC_KHO_MA = Path(__file__).resolve().parent.parent
TEP_COMPOSE = GOC_KHO_MA / "infra" / "docker-compose.yml"
# Volume khai trong docker-compose.yml; Compose đặt tên thật là `<dự án>_mo-hinh`
VOLUME = "mo-hinh"
KHOI = 1 << 20


def anh_llama() -> str:
    """Thẻ ảnh của dịch vụ `mo-hinh`, đọc từ docker-compose.yml — một nơi ghim duy nhất."""
    chu = TEP_COMPOSE.read_text(encoding="utf-8")
    khop = re.search(r"^  mo-hinh:\s*\n(?:    .*\n)*?    image:\s*(\S+)", chu, re.MULTILINE)
    if not khop:
        sys.exit(f"Không tìm thấy dòng `image` của dịch vụ mo-hinh trong {TEP_COMPOSE}")
    return khop.group(1)


def docker(*doi: str, nhan_ra: bool = False) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["docker", *doi], check=False, capture_output=nhan_ra, text=True, encoding="utf-8"
        )
    except FileNotFoundError:
        sys.exit("Không tìm thấy lệnh `docker`. Cài Docker rồi chạy lại.")


def bam_trong_volume(volume: str, anh: str) -> str | None:
    """SHA-256 của tệp mô hình đang nằm trong volume, hoặc None nếu chưa có."""
    kq = docker(
        "run", "--rm", "--entrypoint", "sha256sum", "-v", f"{volume}:/m:ro", anh, f"/m/{TEN_TEP}",
        nhan_ra=True,
    )
    if kq.returncode != 0:
        return None
    return kq.stdout.split()[0] if kq.stdout.strip() else None


def bam_tep(duong_dan: Path) -> str:
    h = hashlib.sha256()
    with duong_dan.open("rb") as f:
        while khoi := f.read(KHOI):
            h.update(khoi)
    return h.hexdigest()


def tai_ve(dich: Path) -> None:
    """Tải về `dich`, tính mã băm trong lúc tải. Lệch mã băm thì xóa tệp và dừng."""
    tam = dich.with_suffix(dich.suffix + ".dang-tai")
    h = hashlib.sha256()
    da_tai = 0
    print(f"Tải {URL}\n  → {dich} ({KICH_THUOC / 1e9:.2f} GB)")
    yeu_cau = urllib.request.Request(URL, headers={"User-Agent": "dx-os-lab-tai-mo-hinh"})
    with urllib.request.urlopen(yeu_cau, timeout=60) as phan_hoi, tam.open("wb") as ra:
        while khoi := phan_hoi.read(KHOI):
            ra.write(khoi)
            h.update(khoi)
            da_tai += len(khoi)
            if da_tai % (50 * KHOI) < KHOI:
                print(f"  {da_tai / KICH_THUOC:6.1%}", end="\r", flush=True)
    print()
    if h.hexdigest() != SHA256:
        tam.unlink(missing_ok=True)
        sys.exit(f"SHA-256 không khớp: nhận {h.hexdigest()}, cần {SHA256}. Không đặt gì vào volume.")
    tam.replace(dich)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__ or "", formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--du-an", default="dx-os-lab", help="tên dự án Compose (mặc định: dx-os-lab)")
    p.add_argument(
        "--thu-muc-tam",
        type=Path,
        default=Path(tempfile.gettempdir()) / "dx-os-lab-mo-hinh",
        help="nơi giữ tệp tải về trước khi chép vào volume",
    )
    p.add_argument("--xoa-tep-tam", action="store_true", help="xóa tệp tải về sau khi chép xong")
    doi = p.parse_args()

    anh = anh_llama()
    volume = f"{doi.du_an}_{VOLUME}"

    # Tạo volume TRƯỚC mọi `docker run -v`: lệnh đó tự tạo volume trần không nhãn, và Compose sẽ cảnh
    # báo volume "không do Compose tạo". Có nhãn của dự án thì `docker compose down -v` xóa được nó
    if docker("volume", "inspect", volume, nhan_ra=True).returncode != 0:
        docker(
            "volume", "create",
            "--label", f"com.docker.compose.project={doi.du_an}",
            "--label", f"com.docker.compose.volume={VOLUME}",
            volume,
            nhan_ra=True,
        )

    if bam_trong_volume(volume, anh) == SHA256:
        print(f"Volume {volume} đã có {TEN_TEP} đúng SHA-256 — không tải lại.")
        return

    doi.thu_muc_tam.mkdir(parents=True, exist_ok=True)
    tep = doi.thu_muc_tam / TEN_TEP
    if tep.exists() and tep.stat().st_size == KICH_THUOC and bam_tep(tep) == SHA256:
        print(f"Dùng lại tệp đã tải: {tep}")
    else:
        tai_ve(tep)

    kq = docker(
        "run", "--rm", "--entrypoint", "cp",
        "-v", f"{volume}:/m",
        "-v", f"{doi.thu_muc_tam.resolve()}:/nguon:ro",
        anh, f"/nguon/{TEN_TEP}", f"/m/{TEN_TEP}",
    )
    if kq.returncode != 0:
        sys.exit("Chép tệp vào volume thất bại.")
    if bam_trong_volume(volume, anh) != SHA256:
        sys.exit(f"Tệp trong volume {volume} không khớp SHA-256 sau khi chép.")
    print(f"Đã đặt {TEN_TEP} vào volume {volume}.")
    if doi.xoa_tep_tam:
        tep.unlink(missing_ok=True)
    print(
        "Bật dịch vụ mô hình: đặt LLM_URL=http://mo-hinh:8080 trong .env rồi\n"
        "    docker compose --env-file .env --profile tri-tue up -d"
    )


if __name__ == "__main__":
    main()
