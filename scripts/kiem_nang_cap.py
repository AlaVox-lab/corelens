# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm một lần nâng cấp giữ nguyên dữ liệu (#254).
#
# Từ v0.9.1, nâng cụm lên bản mới chỉ cần lấy mã mới rồi `up -d --build` — Alembic chạy bản sửa còn
# thiếu, bộ nạp khởi tạo không nạp lại cấu hình đã có. Lệnh này chứng minh điều đó trên một cụm cụ
# thể: chụp số liệu trước khi nâng, nâng, rồi so.
#
#     python scripts/kiem_nang_cap.py chup truoc-nang-cap.json
#     (lấy mã bản mới, rồi: docker compose --env-file infra/.env -f infra/docker-compose.yml up -d --build)
#     python scripts/kiem_nang_cap.py so truoc-nang-cap.json
#
# Trên cụm thử cách ly (`python -m scripts.kiem_chung.cum_thu dung`) thêm `--cum-thu` vào cả hai lệnh.
#
# Thứ được so, trên các dòng đã có lúc chụp (định danh không lớn hơn định danh lớn nhất lúc đó):
#
#   - hồ sơ, dòng nhật ký sự kiện, lời nhắn, tệp đính kèm: cùng số dòng, cùng mã băm của các cột
#     không bao giờ đổi — dòng nào mất hay bị sửa là lệch
#   - tệp đính kèm: mọi khóa còn trong kho tệp, cùng kích thước
#
# Dòng mới sinh trong lúc nâng (bộ quét tự leo thang hồ sơ quá hạn chẳng hạn) không tính là lệch,
# chỉ được báo thêm. Hồ sơ có cột đổi theo trạng thái nên chỉ băm cột cố định của nó.
#
# Chỉ đọc: lệnh không ghi gì vào cơ sở dữ liệu hay kho tệp. Cần Python 3.10 trở lên và lệnh `docker`.
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.kiem_chung.chung import TIEN_TO_MAC_DINH as TIEN_TO_CUM_THU  # noqa: E402

# Bảng → cột đưa vào mã băm. Chỉ cột không bao giờ đổi sau khi ghi; bảng nào cũng có cột `id`.
BANG = {
    "requests": "id, rule_set_id, title, requester_id, created_at",
    "event_log": "id, case_id, activity, actor, from_state, to_state, timestamp",
    "case_messages": "id, case_id, kind, body, created_at",
    "case_attachments": "id, case_id, storage_key, filename, size_bytes",
}

# Chạy trong container dịch vụ ứng dụng: đọc danh sách khóa từ stdin, hỏi kho tệp từng khóa
KIEM_KHO_TEP = """
import json, sys
from app.storage.objects import _khach
from app.config import get_settings
thung = get_settings().s3_bucket
con = 0
byte = 0
thieu = []
for dong in sys.stdin.read().splitlines():
    khoa, kich_thuoc = dong.split("\\t")
    try:
        dau = _khach().head_object(Bucket=thung, Key=khoa)
    except Exception:
        thieu.append(khoa)
        continue
    if int(dau["ContentLength"]) == int(kich_thuoc):
        con += 1
        byte += int(kich_thuoc)
    else:
        thieu.append(khoa)
print(json.dumps({"con_trong_kho": con, "byte": byte, "thieu": thieu[:20]}))
"""


def psql(ts: argparse.Namespace, cau: str) -> str:
    kq = subprocess.run(
        ["docker", "exec", "-i", ts.container, "psql", "-U", ts.nguoi_dung, "-d", ts.csdl,
         "-At", "-q", "-v", "ON_ERROR_STOP=1", "-c", cau],
        capture_output=True, check=False,
    )
    if kq.returncode != 0:
        sys.exit(f"Lệnh SQL thất bại:\n{kq.stderr.decode('utf-8', 'replace')}")
    return kq.stdout.decode("utf-8").strip()


def dem(ts: argparse.Namespace, bang: str, cot: str, toi_da: int) -> dict:
    """Số dòng và mã băm của các dòng có định danh không lớn hơn `toi_da`."""
    dong = psql(
        ts,
        f"SELECT count(*) || '|' || coalesce(md5(string_agg(row({cot})::text, ',' ORDER BY id)), '') "
        f"FROM {bang} WHERE id <= {int(toi_da)}",
    )
    so, bam = dong.split("|")
    return {"so_dong": int(so), "bam": bam}


def kiem_kho_tep(ts: argparse.Namespace, toi_da: int) -> dict:
    khoa = psql(
        ts,
        "SELECT storage_key || E'\\t' || size_bytes FROM case_attachments "
        f"WHERE id <= {int(toi_da)} ORDER BY id",
    )
    kq = subprocess.run(
        ["docker", "exec", "-i", ts.backend, "python", "-c", KIEM_KHO_TEP],
        input=khoa.encode("utf-8"), capture_output=True, check=False,
    )
    if kq.returncode != 0:
        sys.exit(f"Không hỏi được kho tệp qua {ts.backend}:\n{kq.stderr.decode('utf-8', 'replace')}")
    return json.loads(kq.stdout.decode("utf-8").strip().splitlines()[-1])


def chup(ts: argparse.Namespace) -> dict:
    anh = {"ban_sua": psql(ts, "SELECT version_num FROM alembic_version"), "bang": {}}
    for bang, cot in BANG.items():
        toi_da = int(psql(ts, f"SELECT coalesce(max(id), 0) FROM {bang}"))
        anh["bang"][bang] = {"toi_da": toi_da, **dem(ts, bang, cot, toi_da)}
    anh["kho_tep"] = kiem_kho_tep(ts, anh["bang"]["case_attachments"]["toi_da"])
    return anh


def so(ts: argparse.Namespace, truoc: dict, viec: str = "nâng cấp") -> int:
    lech = 0
    print(f"Bản sửa cơ sở dữ liệu: {truoc['ban_sua']} → {psql(ts, 'SELECT version_num FROM alembic_version')}")
    for bang, cot in BANG.items():
        cu = truoc["bang"][bang]
        nay = dem(ts, bang, cot, cu["toi_da"])
        tong_nay = int(psql(ts, f"SELECT count(*) FROM {bang}"))
        dat = nay == {"so_dong": cu["so_dong"], "bam": cu["bam"]}
        lech += not dat
        them = tong_nay - nay["so_dong"]
        print(f"  {'ĐẠT ' if dat else 'LỆCH'} {bang}: {cu['so_dong']} dòng trước, {nay['so_dong']} dòng "
              f"đó sau {viec}{f'; {them} dòng mới sinh từ lúc chụp' if them else ''}")
    kho = kiem_kho_tep(ts, truoc["bang"]["case_attachments"]["toi_da"])
    cu_kho = truoc["kho_tep"]
    dat = (kho["con_trong_kho"], kho["byte"]) == (cu_kho["con_trong_kho"], cu_kho["byte"]) and not kho["thieu"]
    lech += not dat
    print(f"  {'ĐẠT ' if dat else 'LỆCH'} kho tệp: {cu_kho['con_trong_kho']} tệp ({cu_kho['byte']} byte) trước, "
          f"{kho['con_trong_kho']} tệp ({kho['byte']} byte) sau"
          f"{'; thiếu: ' + ', '.join(kho['thieu']) if kho['thieu'] else ''}")
    print(f"{viec.capitalize()} giữ nguyên dữ liệu." if not lech else f"Có {lech} mục lệch.")
    return 1 if lech else 0


def main() -> int:
    for luong in (sys.stdout, sys.stderr):
        luong.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Chụp số liệu trước khi nâng cấp, rồi so sau khi nâng.")
    p.add_argument("viec", choices=("chup", "so"), help="chup: trước khi nâng; so: sau khi nâng")
    p.add_argument("tep", type=Path, help="Tệp JSON lưu ảnh chụp")
    p.add_argument("--container", default="dxlab-postgres", help="Container PostgreSQL")
    p.add_argument("--backend", default="dxlab-backend", help="Container dịch vụ ứng dụng")
    p.add_argument("--nguoi-dung", default="dxlab")
    p.add_argument("--csdl", default="dxlab")
    p.add_argument("--cum-thu", nargs="?", const=TIEN_TO_CUM_THU, metavar="TIỀN_TỐ",
                   help="Kiểm trên cụm thử cách ly (#249): lấy tên hai container theo tiền tố của cụm thử "
                        f"(mặc định {TIEN_TO_CUM_THU!r}) thay cho --container và --backend")
    ts = p.parse_args()
    if ts.cum_thu:
        ts.container, ts.backend = f"{ts.cum_thu}postgres", f"{ts.cum_thu}backend"

    if ts.viec == "chup":
        anh = chup(ts)
        ts.tep.write_text(json.dumps(anh, ensure_ascii=False, indent=2), encoding="utf-8")
        for bang, so_lieu in anh["bang"].items():
            print(f"  {bang}: {so_lieu['so_dong']} dòng")
        print(f"  kho tệp: {anh['kho_tep']['con_trong_kho']} tệp ({anh['kho_tep']['byte']} byte)")
        print(f"Đã chụp vào {ts.tep} (bản sửa {anh['ban_sua']}).")
        return 0
    try:
        anh = json.loads(ts.tep.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"Không thấy tệp chụp {ts.tep}. Chạy `chup` trên cụm TRƯỚC khi nâng cấp để có tệp này.")
    except (json.JSONDecodeError, UnicodeDecodeError):
        sys.exit(f"{ts.tep} không phải tệp chụp của lệnh này (không đọc được JSON).")
    if not isinstance(anh, dict) or "bang" not in anh:
        sys.exit(f"{ts.tep} không phải tệp chụp của lệnh này (thiếu mục 'bang').")
    return so(ts, anh)


if __name__ == "__main__":
    sys.exit(main())
