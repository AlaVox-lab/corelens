# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Đưa tên hiển thị Corelens (#538) vào realm của cụm ĐÃ DỰNG trước bản 1.8:
#
#     python scripts/ten_hien_thi.py                 # xem sẽ đổi gì, không ghi
#     python scripts/ten_hien_thi.py --xac-nhan      # ghi
#
# Hai thứ, cả hai đọc từ chính infra/keycloak/realm-dx-os-lab.json — một nguồn sự thật cho cụm dựng mới và cụm
# nâng cấp:
#
#   - Tên hiển thị của realm (`displayName`, `displayNameHtml` nếu tệp có): hiện trên trang đăng nhập và trong
#     ứng dụng xác thực hai lớp. Chỉ đổi khi realm còn đúng tên cũ của bản trước — quản trị viên đã đặt tên
#     khác thì giữ.
#   - Email của các tài khoản mẫu trong tệp realm: chỉ tài khoản cùng tên đăng nhập mà email còn đúng địa chỉ
#     cũ `<tên>@dx-os-lab.test`. Tài khoản khác, hay tài khoản mẫu đã đổi email, không đụng tới.
#
# Vì sao cần lệnh: Keycloak chỉ nạp tệp realm lúc tạo realm, nên cụm đang chạy không thấy thay đổi trong tệp.
# Lệnh dùng API quản trị như scripts/xac_thuc_hai_lop.py (ADR-0001: chỉ cấu hình, không sửa nền tảng). Chạy lại
# bao nhiêu lần cũng được. Địa chỉ Keycloak, realm và tài khoản quản trị đọc từ tệp env của cụm (mặc định
# infra/.env). Chỉ dùng thư viện chuẩn, Python 3.10 trở lên.

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from xac_thuc_hai_lop import TEP_REALM, Keycloak, cau_hinh  # noqa: E402

# Giá trị của bản trước #538 — chỉ chỗ còn đúng các giá trị này mới đổi
TEN_CU = "DX-OS Lab — Cổng vận hành yêu cầu nội bộ"
TEN_MIEN_EMAIL_CU = "dx-os-lab.test"
KHOA_TEN = ("displayName", "displayNameHtml")


def doc_realm_mau() -> dict:
    if not TEP_REALM.is_file():
        sys.exit(f"Không thấy {TEP_REALM} — chạy kịch bản từ kho mã.")
    return json.loads(TEP_REALM.read_text(encoding="utf-8"))


def email_cu(email_moi: str) -> str:
    return f"{email_moi.rpartition('@')[0]}@{TEN_MIEN_EMAIL_CU}"


def main() -> int:
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Đưa tên hiển thị Corelens vào realm của cụm đã dựng (#538).")
    p.add_argument("--xac-nhan", action="store_true", help="ghi thay đổi; thiếu cờ này chỉ in sẽ đổi gì")
    p.add_argument("--env-file", type=Path, default=Path("infra/.env"), help="tệp env của cụm (mặc định infra/.env)")
    p.add_argument("--keycloak", help="địa chỉ Keycloak, mặc định http://localhost:<KEYCLOAK_PORT>")
    p.add_argument("--realm", help="realm, mặc định KEYCLOAK_REALM")
    ts = p.parse_args()

    mau = doc_realm_mau()
    kc = Keycloak(cau_hinh(ts))
    ghi = ts.xac_nhan
    print(f"Realm {kc.realm} tại {kc.goc}{'' if ghi else ' — chỉ xem, thêm --xac-nhan để ghi'}")

    # --- Tên hiển thị của realm ---
    r = kc.realm_rep()
    doi_ten = {k: mau[k] for k in KHOA_TEN if k in mau and r.get(k) == TEN_CU}
    for k in KHOA_TEN:
        if k in doi_ten:
            print(f"  {k}: {r.get(k)!r} → {mau[k]!r}")
        elif k in mau and r.get(k) != mau[k]:
            print(f"  {k}: giữ {r.get(k)!r} (không còn là tên cũ — có thể quản trị viên đã đặt)")
    if doi_ten and ghi:
        # Gửi lại TRỌN bản ghi realm vừa đọc, chỉ thay các khóa tên
        kc.goi("", "PUT", {**r, **doi_ten})

    # --- Email tài khoản mẫu ---
    so_doi = so_giu = 0
    for tk_mau in mau.get("users") or []:
        moi = tk_mau.get("email")
        if not moi or moi.endswith(f"@{TEN_MIEN_EMAIL_CU}"):
            continue
        tim = kc.goi(f"/users?username={urllib.parse.quote(tk_mau['username'])}&exact=true")
        if not tim:
            continue
        hien = tim[0].get("email")
        if hien == moi:
            continue
        if hien != email_cu(moi):
            so_giu += 1
            print(f"  {tk_mau['username']}: giữ email {hien!r} (không còn là email mẫu cũ)")
            continue
        so_doi += 1
        print(f"  {tk_mau['username']}: {hien} → {moi}")
        if ghi:
            # Gửi lại TRỌN bản ghi (Keycloak 24 trở đi có thể xóa thuộc tính không có trong bản gửi lên)
            day_du = kc.goi(f"/users/{tim[0]['id']}")
            kc.goi(f"/users/{tim[0]['id']}", "PUT", {**day_du, "email": moi})

    viec = "Đã đổi" if ghi else "Sẽ đổi"
    print(f"{viec}: tên hiển thị {'có' if doi_ten else 'không'}, email {so_doi} tài khoản mẫu; giữ {so_giu}.")
    if not ghi and (doi_ten or so_doi):
        print("Chạy lại kèm --xac-nhan để ghi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
