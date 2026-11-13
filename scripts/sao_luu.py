# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Sao lưu tay và khôi phục cụm (#245): ba cơ sở dữ liệu và kho tệp đính kèm trong CÙNG một lần, kèm bộ
# đối soát chạy sau khi khôi phục.
#
#     python scripts/sao_luu.py tao sao-luu/2026-12-09          # trước buổi trình diễn
#     python scripts/sao_luu.py khoi-phuc sao-luu/2026-12-09    # khi cần quay về
#     python scripts/sao_luu.py doi-soat sao-luu/2026-12-09     # chạy lại riêng bước đối soát
#
# Mục tiêu cho quy mô trình diễn (giảng viên chốt 13/11/2026): sao lưu tay trước buổi trình diễn, khôi
# phục xong trong 15 phút; dữ liệu mất tối đa là phần phát sinh sau lần sao lưu gần nhất. Không đặt lịch
# tự động — triển khai thật vẫn nằm ngoài phạm vi (docs/ARCHITECTURE.md mục 9).
#
# Vì sao hai nơi phải sao cùng lúc: bảng `case_attachments` trỏ tới tệp trong kho SeaweedFS. Sao cơ sở dữ
# liệu lúc này, kho tệp lúc khác, thì khôi phục xong sẽ có dòng trỏ tới tệp không có, hoặc tệp mồ côi.
# Cách giữ khớp: dừng cổng rồi dịch vụ ứng dụng — hai thứ DUY NHẤT ghi hồ sơ và tệp — trong lúc sao.
# Keycloak và Superset vẫn chạy: `pg_dump` tự chụp nhất quán từng cơ sở dữ liệu, mà hai cơ sở dữ liệu đó
# không trỏ sang tệp nào. Cụm ngừng nhận thao tác khoảng một phút.
#
# Thư mục sao lưu gồm:
#   vai-tro.sql           vai trò PostgreSQL (tài khoản chỉ đọc của Superset và dịch vụ khai phá), không
#                         gồm tài khoản chủ — tài khoản chủ do `.env` của cụm đích quyết
#   <tên csdl>.dump       mỗi cơ sở dữ liệu một tệp, định dạng tùy biến của pg_dump
#   kho-tep.tar.gz        toàn bộ thư mục dữ liệu của SeaweedFS
#   doi-soat.json         ảnh chụp đối soát (scripts/kiem_nang_cap.py): số dòng và mã băm của hồ sơ,
#                         nhật ký, lời nhắn, tệp đính kèm; mọi tệp còn trong kho
#   sao-luu.json          thời điểm (UTC), tên cơ sở dữ liệu, bản sửa lược đồ, SHA-256 từng tệp
#
# Khôi phục ghi đè TOÀN BỘ dữ liệu của cụm đích, kể cả tài khoản Keycloak và bảng điều khiển Superset.
# Cụm đích dựng từ cùng phiên bản mã và cùng tệp `infra/.env` (mật khẩu tài khoản chỉ đọc nằm trong bản
# sao lưu). Chỉ dùng thư viện chuẩn và lệnh `docker`; không thêm ảnh hay gói nào — nén kho tệp bằng chính
# ảnh SeaweedFS của cụm. Cần Python 3.10 trở lên.
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kiem_nang_cap  # noqa: E402 — cùng thư mục, dùng lại phần chụp và so

# Thành phần theo thứ tự bật lại. Phải dừng trước khi khôi phục: mọi thứ đọc/ghi cơ sở dữ liệu hay kho tệp
THANH_PHAN = ["seaweedfs", "keycloak", "backend", "khai-pha", "superset", "frontend"]


def chay(lenh: list[str], stdin=None, stdout=None) -> subprocess.CompletedProcess:
    """Chạy một lệnh, dừng cả kịch bản kèm lỗi của lệnh khi hỏng. `stdout` là tệp thì ghi thẳng vào đó."""
    kq = subprocess.run(
        lenh, stdin=stdin, stdout=stdout if stdout is not None else subprocess.PIPE, stderr=subprocess.PIPE
    )
    if kq.returncode != 0:
        loi = kq.stderr.decode("utf-8", "replace") if kq.stderr else ""
        sys.exit(f"Lệnh thất bại ({' '.join(lenh[:4])} …):\n{loi}")
    return kq


def ten(ts: argparse.Namespace, phan: str) -> str:
    return f"{ts.tien_to}-{phan}"


def dang_chay(container: str) -> bool:
    kq = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", container], capture_output=True, check=False
    )
    return kq.returncode == 0 and kq.stdout.decode().strip() == "true"


def doc_bien(ts: argparse.Namespace) -> dict[str, str]:
    pg = ten(ts, "postgres")
    if not dang_chay(pg):
        sys.exit(f"{pg} không chạy. Bật cụm trước: docker compose --env-file infra/.env -f infra/docker-compose.yml up -d")
    bien = {}
    for k in ("POSTGRES_USER", "POSTGRES_DB", "KEYCLOAK_DB_NAME", "SUPERSET_DB_NAME"):
        bien[k] = chay(["docker", "exec", pg, "printenv", k]).stdout.decode().strip()
    return bien


def cho_khoe(container: str, toi_da_giay: int = 600) -> None:
    """Chờ healthcheck của container báo khỏe (dịch vụ ứng dụng chạy xong migration và bộ nạp)."""
    het = time.monotonic() + toi_da_giay
    while time.monotonic() < het:
        kq = subprocess.run(
            ["docker", "inspect", "-f", "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}", container],
            capture_output=True,
            check=False,
        )
        trang_thai = kq.stdout.decode().strip()
        if trang_thai in ("healthy", "none"):
            return
        time.sleep(3)
    sys.exit(f"{container} chưa khỏe sau {toi_da_giay} giây — xem: docker logs {container}")


def bam(tep: Path) -> str:
    h = hashlib.sha256()
    with tep.open("rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()


def tham_so_doi_soat(ts: argparse.Namespace, bien: dict[str, str]) -> argparse.Namespace:
    return argparse.Namespace(
        container=ten(ts, "postgres"), backend=ten(ts, "backend"), nguoi_dung=bien["POSTGRES_USER"], csdl=bien["POSTGRES_DB"]
    )


def anh_kho_tep(ts: argparse.Namespace) -> str:
    return chay(["docker", "inspect", "-f", "{{.Config.Image}}", ten(ts, "seaweedfs")]).stdout.decode().strip()


# ---------------------------------------------------------------------------
# Sao lưu
# ---------------------------------------------------------------------------


def tao(ts: argparse.Namespace) -> int:
    bat_dau = time.monotonic()
    bien = doc_bien(ts)
    if not dang_chay(ten(ts, "backend")):
        sys.exit(f"{ten(ts, 'backend')} không chạy — cần nó để chụp số liệu đối soát.")
    thu_muc: Path = ts.thu_muc
    if thu_muc.exists() and any(thu_muc.iterdir()):
        sys.exit(f"{thu_muc} đã có tệp. Chọn thư mục mới để không ghi đè bản sao lưu cũ.")
    thu_muc.mkdir(parents=True, exist_ok=True)
    pg, nguoi = ten(ts, "postgres"), bien["POSTGRES_USER"]
    cac_csdl = [bien["POSTGRES_DB"], bien["KEYCLOAK_DB_NAME"], bien["SUPERSET_DB_NAME"]]
    dang_bat = [p for p in ("frontend", "backend") if dang_chay(ten(ts, p))]

    try:
        # 1. Ngừng nhận thao tác của người dùng, rồi chụp số liệu đối soát khi dịch vụ còn chạy
        if "frontend" in dang_bat:
            chay(["docker", "stop", ten(ts, "frontend")])
        print("Đã dừng cổng. Chụp số liệu đối soát…")
        anh = kiem_nang_cap.chup(tham_so_doi_soat(ts, bien))
        (thu_muc / "doi-soat.json").write_text(json.dumps(anh, ensure_ascii=False, indent=2), encoding="utf-8")

        # 2. Dừng dịch vụ ứng dụng: từ đây không còn gì ghi hồ sơ hay tệp
        chay(["docker", "stop", ten(ts, "backend")])

        # 3. Vai trò (bỏ tài khoản chủ) và ba cơ sở dữ liệu
        vai_tro = chay(["docker", "exec", pg, "pg_dumpall", "-U", nguoi, "--roles-only"]).stdout.decode("utf-8")
        giu = [
            d
            for d in vai_tro.splitlines()
            if not (d.startswith((f"CREATE ROLE {nguoi};", f"ALTER ROLE {nguoi} ")))
        ]
        (thu_muc / "vai-tro.sql").write_text("\n".join(giu) + "\n", encoding="utf-8")
        for csdl in cac_csdl:
            print(f"Sao cơ sở dữ liệu {csdl}…")
            with (thu_muc / f"{csdl}.dump").open("wb") as f:
                chay(["docker", "exec", pg, "pg_dump", "-U", nguoi, "-Fc", csdl], stdout=f)

        # 4. Kho tệp: dừng SeaweedFS để thư mục dữ liệu đứng yên, nén bằng chính ảnh của nó
        print("Sao kho tệp…")
        anh_sw = anh_kho_tep(ts)
        chay(["docker", "stop", ten(ts, "seaweedfs")])
        try:
            with (thu_muc / "kho-tep.tar.gz").open("wb") as f:
                chay(
                    ["docker", "run", "--rm", "--volumes-from", ten(ts, "seaweedfs"), "--entrypoint", "tar",
                     anh_sw, "-C", "/data", "-czf", "-", "."],
                    stdout=f,
                )
        finally:
            chay(["docker", "start", ten(ts, "seaweedfs")])
            cho_khoe(ten(ts, "seaweedfs"))
    finally:
        # Bật lại những gì đã dừng, kể cả khi sao lưu hỏng giữa chừng
        for phan in ("backend", "frontend"):
            if phan in dang_bat and not dang_chay(ten(ts, phan)):
                subprocess.run(["docker", "start", ten(ts, phan)], capture_output=True, check=False)

    tep = sorted(p.name for p in thu_muc.iterdir())
    (thu_muc / "sao-luu.json").write_text(
        json.dumps(
            {
                "thoi_diem_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "tien_to": ts.tien_to,
                "co_so_du_lieu": cac_csdl,
                "ban_sua": anh["ban_sua"],
                "sha256": {t: bam(thu_muc / t) for t in tep},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if "backend" in dang_bat:
        cho_khoe(ten(ts, "backend"))
    print(f"Đã sao lưu vào {thu_muc} trong {time.monotonic() - bat_dau:.0f} giây "
          f"({sum((thu_muc / t).stat().st_size for t in tep) / 1e6:.1f} MB).")
    return 0


# ---------------------------------------------------------------------------
# Khôi phục
# ---------------------------------------------------------------------------


def kiem_ban_sao(thu_muc: Path) -> dict:
    tep_mo_ta = thu_muc / "sao-luu.json"
    if not tep_mo_ta.exists():
        sys.exit(f"Không thấy {tep_mo_ta} — đây không phải thư mục sao lưu, hoặc lần sao lưu chưa xong.")
    mo_ta = json.loads(tep_mo_ta.read_text(encoding="utf-8"))
    for tep, ma in mo_ta["sha256"].items():
        if bam(thu_muc / tep) != ma:
            sys.exit(f"{tep} không khớp mã SHA-256 lúc sao lưu — bản sao lưu hỏng, dừng trước khi đụng cụm.")
    return mo_ta


def khoi_phuc(ts: argparse.Namespace) -> int:
    bat_dau = time.monotonic()
    thu_muc: Path = ts.thu_muc
    mo_ta = kiem_ban_sao(thu_muc)
    bien = doc_bien(ts)
    pg, nguoi = ten(ts, "postgres"), bien["POSTGRES_USER"]
    print(f"Khôi phục bản sao lưu lúc {mo_ta['thoi_diem_utc']} (UTC) vào cụm {ts.tien_to}-*.")

    dang_bat = [p for p in THANH_PHAN if dang_chay(ten(ts, p))]
    for phan in reversed(THANH_PHAN):
        if phan in dang_bat:
            chay(["docker", "stop", ten(ts, phan)])

    # Vai trò trước (đã có thì bỏ qua lỗi "đã tồn tại", vẫn đặt lại mật khẩu), rồi từng cơ sở dữ liệu
    with (thu_muc / "vai-tro.sql").open("rb") as f:
        subprocess.run(
            ["docker", "exec", "-i", pg, "psql", "-U", nguoi, "-d", "postgres", "-q", "-v", "ON_ERROR_STOP=0"],
            stdin=f, capture_output=True, check=False,
        )
    for csdl in mo_ta["co_so_du_lieu"]:
        print(f"Khôi phục cơ sở dữ liệu {csdl}…")
        chay(["docker", "exec", pg, "psql", "-U", nguoi, "-d", "postgres", "-q", "-v", "ON_ERROR_STOP=1",
              "-c", f'DROP DATABASE IF EXISTS "{csdl}" WITH (FORCE)'])
        with (thu_muc / f"{csdl}.dump").open("rb") as f:
            chay(["docker", "exec", "-i", pg, "pg_restore", "-U", nguoi, "-C", "-d", "postgres", "--exit-on-error"],
                 stdin=f)

    print("Khôi phục kho tệp…")
    with (thu_muc / "kho-tep.tar.gz").open("rb") as f:
        chay(
            ["docker", "run", "--rm", "-i", "--volumes-from", ten(ts, "seaweedfs"), "--entrypoint", "sh",
             anh_kho_tep(ts), "-c", "cd /data && rm -rf -- ./* ./.[!.]* 2>/dev/null; tar -xzf - -C /data"],
            stdin=f,
        )

    for phan in THANH_PHAN:
        if phan in dang_bat or phan in ("seaweedfs", "backend"):
            chay(["docker", "start", ten(ts, phan)])
            if phan in ("seaweedfs", "backend"):
                cho_khoe(ten(ts, phan))
    truoc = json.loads((thu_muc / "doi-soat.json").read_text(encoding="utf-8"))
    cho_kho_tep(tham_so_doi_soat(ts, bien), truoc)
    giay = time.monotonic() - bat_dau
    print(f"Đã khôi phục trong {giay / 60:.1f} phút (mục tiêu: dưới 15 phút). Đối soát:")
    return kiem_nang_cap.so(tham_so_doi_soat(ts, bien), truoc, "khôi phục")


def cho_kho_tep(ts_doi_soat: argparse.Namespace, truoc: dict, toi_da_giay: int = 90) -> None:
    """SeaweedFS báo khỏe trước khi nạp xong chỉ mục tệp: vài giây đầu hỏi tệp vẫn ra "không có". Chờ
    tới khi mọi tệp lúc chụp hỏi được, hoặc hết giờ — hết giờ thì để bước đối soát báo lệch."""
    het = time.monotonic() + toi_da_giay
    toi_da = truoc["bang"]["case_attachments"]["toi_da"]
    while time.monotonic() < het:
        if not kiem_nang_cap.kiem_kho_tep(ts_doi_soat, toi_da)["thieu"]:
            return
        time.sleep(5)


def doi_soat(ts: argparse.Namespace) -> int:
    kiem_ban_sao(ts.thu_muc)
    bien = doc_bien(ts)
    truoc = json.loads((ts.thu_muc / "doi-soat.json").read_text(encoding="utf-8"))
    return kiem_nang_cap.so(tham_so_doi_soat(ts, bien), truoc, "khôi phục")


def main() -> int:
    for luong in (sys.stdout, sys.stderr):
        luong.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Sao lưu tay, khôi phục và đối soát cụm dx-os-lab (#245).")
    p.add_argument("viec", choices=("tao", "khoi-phuc", "doi-soat"))
    p.add_argument("thu_muc", type=Path, help="Thư mục chứa bản sao lưu")
    p.add_argument("--tien-to", default="dxlab", help="Tiền tố tên container của cụm (mặc định dxlab)")
    ts = p.parse_args()
    return {"tao": tao, "khoi-phuc": khoi_phuc, "doi-soat": doi_soat}[ts.viec](ts)


if __name__ == "__main__":
    sys.exit(main())
