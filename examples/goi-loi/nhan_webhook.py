# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ví dụ bên nhận webhook của nền tảng lõi (#390): một ứng dụng khác được lõi chủ động báo mỗi khi hồ sơ
# chuyển bước, thay vì tự hỏi lại API.
#
#     python examples/goi-loi/nhan_webhook.py
#
# Kịch bản làm ba việc, chỉ dùng thư viện chuẩn của Python 3.10 trở lên:
#
#   1. Mở một máy chủ HTTP nhỏ trên máy (mặc định cổng 8765) nhận `POST /su-kien`.
#   2. Xin token của tài khoản dịch vụ `dx-integration` rồi đăng ký chính địa chỉ đó qua
#      `POST /core/v1/webhooks` — địa chỉ `host.docker.internal` để dịch vụ trong Docker gọi ra máy được.
#   3. Mỗi sự kiện tới: kiểm chữ ký HMAC bằng bí mật nhận lúc đăng ký, từ chối mốc thời gian quá 5 phút,
#      bỏ sự kiện trùng theo `X-DXOS-Event-Id`, rồi in ra. Ctrl+C thì hủy đăng ký rồi thoát.
#
# Đăng ký webhook cần vai `administrator`. Tài khoản dịch vụ mẫu chỉ mang `requester`: thêm vai cho nó một
# lần — `KEYCLOAK_INTEGRATION_ROLES=requester,administrator` trong infra/.env rồi chạy
# `python scripts/tai_khoan_dich_vu.py`. Chỉ làm vậy trên cụm thử.

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goi_loi import TIEN_TO_LOI, LoiGoi, cau_hinh, goi, xin_token  # noqa: E402 — cùng thư mục

LECH_TOI_DA_GIAY = 300

# Cửa sổ dòng lệnh Windows mặc định không in được chữ có dấu
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def kiem_chu_ky(bi_mat: str, moc: str, than: bytes, chu_ky: str) -> bool:
    mong_doi = "sha256=" + hmac.new(bi_mat.encode(), moc.encode() + b"." + than, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mong_doi, chu_ky)


def tao_bo_nhan(bi_mat: dict[str, str]):
    da_nhan: set[str] = set()
    khoa = threading.Lock()

    class BoNhan(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 — tên do http.server quy định
            than = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            moc = self.headers.get("X-DXOS-Timestamp", "")
            chu_ky = self.headers.get("X-DXOS-Signature", "")
            ma_su_kien = self.headers.get("X-DXOS-Event-Id", "")

            if not moc.isdigit() or abs(time.time() - int(moc)) > LECH_TOI_DA_GIAY:
                return self._tra(400, "mốc thời gian lạ hoặc quá cũ")
            if not bi_mat.get("gia_tri") or not kiem_chu_ky(bi_mat["gia_tri"], moc, than, chu_ky):
                return self._tra(401, "chữ ký sai")
            with khoa:
                if ma_su_kien in da_nhan:
                    return self._tra(204, None)  # gửi lại sau khi đã nhận — báo xong, không xử lý lại
                da_nhan.add(ma_su_kien)

            sk = json.loads(than)
            print(
                f"  sự kiện {sk['event_id']} · hồ sơ {sk['case_id']} ({sk['process_code']}) · {sk['activity']}: "
                f"{sk['from_state']} → {sk['to_state']} · bởi {sk['actor_label'] or sk['actor']} · {sk['timestamp']}",
                flush=True,
            )
            self._tra(204, None)

        def _tra(self, ma: int, ly_do: str | None) -> None:
            self.send_response(ma)
            self.end_headers()
            if ly_do:
                print(f"  từ chối một lời gọi: {ly_do}", flush=True)

        def log_message(self, *_args) -> None:
            pass  # đã in theo cách riêng ở trên

    return BoNhan


def main() -> int:
    p = argparse.ArgumentParser(description="Ví dụ bên nhận webhook của nền tảng lõi (#390).")
    p.add_argument("--env-file", type=Path, default=Path("infra/.env"), help="tệp env của cụm (mặc định infra/.env)")
    p.add_argument("--cong-api", help="địa chỉ cổng API, mặc định http://localhost:<GATEWAY_PORT>")
    p.add_argument("--keycloak", help="địa chỉ Keycloak, mặc định http://localhost:<KEYCLOAK_PORT>")
    p.add_argument("--cong", type=int, default=8765, help="cổng của máy chủ nhận trên máy này (mặc định 8765)")
    p.add_argument(
        "--dia-chi-nhan",
        help="địa chỉ lõi gọi tới, mặc định http://host.docker.internal:<cổng>/su-kien (Docker Desktop)",
    )
    p.add_argument("--hoat-dong", nargs="*", help="chỉ nhận các mã hoạt động này")
    ts = p.parse_args()
    ch = cau_hinh(ts)

    bi_mat: dict[str, str] = {}
    may_chu = ThreadingHTTPServer(("0.0.0.0", ts.cong), tao_bo_nhan(bi_mat))  # noqa: S104 — container phải gọi tới được
    threading.Thread(target=may_chu.serve_forever, daemon=True).start()
    print(f"1. Máy chủ nhận đang nghe cổng {ts.cong}")

    token = xin_token(ch)
    dia_chi = ts.dia_chi_nhan or f"http://host.docker.internal:{ts.cong}/su-kien"
    try:
        dk = goi(
            f"{ch['cong_api']}{TIEN_TO_LOI}/webhooks",
            phuong_thuc="POST",
            token=token,
            json_than={"url": dia_chi, "description": "Ví dụ examples/goi-loi/nhan_webhook.py", "activities": ts.hoat_dong},
        )
    except LoiGoi as loi:
        if loi.ma == 403:
            sys.exit(
                "Tài khoản dịch vụ chưa có vai administrator. Thêm vào KEYCLOAK_INTEGRATION_ROLES trong infra/.env "
                "rồi chạy: python scripts/tai_khoan_dich_vu.py"
            )
        raise
    bi_mat["gia_tri"] = dk["secret"]
    print(f"2. Đã đăng ký webhook {dk['id']} → {dia_chi}")
    print("3. Chuyển bước một hồ sơ trên cổng người dùng; sự kiện hiện dưới đây (Ctrl+C để dừng):", flush=True)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        may_chu.shutdown()
        try:
            goi(f"{ch['cong_api']}{TIEN_TO_LOI}/webhooks/{dk['id']}", phuong_thuc="DELETE", token=xin_token(ch))
            print(f"\nĐã hủy đăng ký webhook {dk['id']}")
        except (LoiGoi, OSError) as loi:
            print(f"\nKhông hủy được đăng ký {dk['id']}: {loi}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
