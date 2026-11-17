# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ví dụ một ứng dụng KHÁC chạy trọn quy trình CỦA RIÊNG NÓ trên động cơ luồng công việc của nền tảng lõi (#376).
#
#     python examples/goi-loi/quy_trinh_mua_sam.py
#     python examples/goi-loi/quy_trinh_mua_sam.py --quy-trinh purchase-approval --env-file duong/toi/tep.env
#
# Đóng vai một phần mềm mua sắm: không đăng nhập người dùng nào, không đi qua cổng người dùng hay buồng lái
# nào, CHỈ gọi cổng API dưới `/core/v1` bằng ba tài khoản dịch vụ (luồng client credentials):
#
#   người đề xuất   KEYCLOAK_INTEGRATION_*            vai requester
#   trưởng phòng    KEYCLOAK_INTEGRATION_HEAD_*       vai approver, thuộc một phòng ban
#   duyệt cấp hai   KEYCLOAK_INTEGRATION_REVIEWER_*   vai classifier
#
#   1. danh mục quy trình → chọn quy trình (mặc định: quy trình đầu tiên không phải của ứng dụng minh họa)
#   2. loại yêu cầu và trạng thái của quy trình đó
#   3. người đề xuất tạo hồ sơ, gửi trưởng phòng của phòng đề xuất
#   4. trưởng phòng thấy hồ sơ trong việc chờ mình, đi bước chính
#   5. người duyệt cấp hai thấy hồ sơ trong việc chờ mình, đi bước chính — tới trạng thái kết thúc
#   6. đọc lịch sử — các dòng nhật ký sự kiện của hồ sơ
#
# Không mã cứng mã quy trình, trạng thái, loại hay bước nào: mỗi người đi BƯỚC CHÍNH mà lõi trả về cho chính
# họ (`allowed_transitions`, cờ `is_primary`), trường bắt buộc điền theo khai báo API trả về. Phòng đề xuất là
# phòng của tài khoản trưởng phòng, đọc từ `/core/v1/identity/me`. Cửa bước chuyển của lõi xét vai và phạm vi
# của từng người gọi — trưởng phòng chỉ thấy đề xuất của phòng mình.
#
# Cấu hình như goi_loi.py: tệp env của cụm (mặc định infra/.env), biến môi trường ghi đè, tham số ghi đè cả
# hai. Chỉ dùng thư viện chuẩn, Python 3.10 trở lên.

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import urllib.parse
from pathlib import Path

from goi_loi import GOC_KHO, LoiGoi, NenTangLoi, chi_tiet_mau, doc_tep_env, goi

# (tiền tố biến, vai trong ví dụ)
TAI_KHOAN = (
    ("KEYCLOAK_INTEGRATION", "người đề xuất"),
    ("KEYCLOAK_INTEGRATION_HEAD", "trưởng phòng"),
    ("KEYCLOAK_INTEGRATION_REVIEWER", "duyệt cấp hai"),
)
# Cột quyết định của hồ sơ mà bước gửi duyệt đặt (lược đồ, không phải nghiệp vụ)
TRUONG_PHONG_BAN = "department_code"
# Số tiền mẫu cho trường kiểu số — đề xuất cần một con số dương
SO_MAU = 2_500_000


def cau_hinh(ts: argparse.Namespace) -> dict:
    tep = ts.env_file if ts.env_file.is_absolute() else Path.cwd() / ts.env_file
    if not tep.is_file() and not ts.env_file.is_absolute():
        tep = GOC_KHO / ts.env_file
    env = doc_tep_env(tep)

    def lay(ten: str) -> str | None:
        return os.environ.get(ten) or env.get(ten)

    def dia_chi(tham_so: str | None, bien_day_du: str, bien_cong: str) -> str | None:
        cong = lay(bien_cong)
        return tham_so or lay(bien_day_du) or (f"http://localhost:{cong}" if cong else None)

    ch = {
        "cong_api": dia_chi(ts.cong_api, "GATEWAY_URL", "GATEWAY_PORT"),
        "keycloak": dia_chi(ts.keycloak, "KEYCLOAK_URL", "KEYCLOAK_PORT"),
        "realm": lay("KEYCLOAK_REALM"),
    }
    thieu = [ten for ten, v in (("GATEWAY_PORT (hoặc --cong-api)", ch["cong_api"]),
                                ("KEYCLOAK_PORT (hoặc --keycloak)", ch["keycloak"]),
                                ("KEYCLOAK_REALM", ch["realm"])) if not v]
    ch["tai_khoan"] = []
    for tien_to, vai in TAI_KHOAN:
        client, bi_mat = lay(f"{tien_to}_CLIENT_ID"), lay(f"{tien_to}_SECRET")
        thieu += [ten for ten, v in ((f"{tien_to}_CLIENT_ID", client), (f"{tien_to}_SECRET", bi_mat)) if not v]
        ch["tai_khoan"].append({"client": client, "bi_mat": bi_mat, "vai": vai})
    if thieu:
        sys.exit(f"Thiếu {', '.join(thieu)} — không thấy trong {tep} lẫn biến môi trường. Chép các dòng "
                 "KEYCLOAK_INTEGRATION_* từ infra/.env.example.")
    ch["cong_api"] = ch["cong_api"].rstrip("/")
    ch["keycloak"] = ch["keycloak"].rstrip("/")
    return ch


def ket_noi(ch: dict, tk: dict) -> NenTangLoi:
    try:
        token = goi(
            f"{ch['keycloak']}/realms/{urllib.parse.quote(ch['realm'])}/protocol/openid-connect/token",
            phuong_thuc="POST",
            form={"grant_type": "client_credentials", "client_id": tk["client"], "client_secret": tk["bi_mat"]},
        )["access_token"]
    except LoiGoi as loi:
        sys.exit(f"Keycloak không cấp token cho client {tk['client']} ({loi}). Cụm dựng trước #376 thì tạo các "
                 "client bằng: python scripts/tai_khoan_dich_vu.py")
    return NenTangLoi(ch["cong_api"], token)


def buoc_chinh(nen_tang: NenTangLoi, ma_ho_so: int, ai: str) -> dict:
    """Bước chính mà lõi trả về cho chính người gọi ở hồ sơ này."""
    cac_buoc = nen_tang.get(f"/workflow/requests/{ma_ho_so}")["allowed_transitions"]
    print(f"   Bước {ai} đi được: "
          + ("; ".join(f"{b['activity_label']} → {b['to_state_label']}" + (" (chính)" if b["is_primary"] else "")
                       for b in cac_buoc) or "không có"))
    chinh = next((b for b in cac_buoc if b["is_primary"]), None)
    if chinh is None:
        sys.exit(f"Lõi không trả bước chính nào cho {ai} — vai hay phạm vi của tài khoản không khớp quy trình.")
    return chinh


def di(nen_tang: NenTangLoi, ma_ho_so: int, buoc: dict, ai: str, thay_doi: dict | None = None) -> dict:
    ghi_chu = f"{ai.capitalize()} đi bước này qua API của lõi." if buoc["requires_note"] else None
    ho_so = nen_tang.post(f"/workflow/requests/{ma_ho_so}/transitions",
                          {"to_state": buoc["to_state"], "note": ghi_chu, "changes": thay_doi or {}})
    print(f"   {ai.capitalize()} đã đi “{buoc['activity_label']}”: hồ sơ giờ ở “{ho_so['state']['label']}”"
          + (" — trạng thái kết thúc" if ho_so["state"]["is_terminal"] else ""))
    return ho_so


def cho_toi(nen_tang: NenTangLoi, quy_trinh: str, ma_ho_so: int) -> bool:
    """Hồ sơ có trong danh sách "đang chờ tôi" của người gọi không — hàng việc theo vai của lõi."""
    ds = nen_tang.get(f"/workflow/requests?process={urllib.parse.quote(quy_trinh)}&needs_action=true&limit=100")
    return any(h["id"] == ma_ho_so for h in ds["items"])


def chay(ch: dict, ma_quy_trinh: str | None) -> int:
    nguoi_gui, truong_phong, duyet = (ket_noi(ch, tk) for tk in ch["tai_khoan"])
    print("1. Token client credentials của ba tài khoản dịch vụ: "
          + ", ".join(f"{tk['client']} ({tk['vai']})" for tk in ch["tai_khoan"]))

    cac_quy_trinh = nguoi_gui.get("/workflow/processes")
    print(f"2. Lõi chạy {len(cac_quy_trinh)} quy trình: "
          + "; ".join(f"{q['code']} “{q['label']}”" + (" (của ứng dụng minh họa)" if q["is_app_default"] else "")
                      for q in cac_quy_trinh))
    quy_trinh = next((q for q in cac_quy_trinh if q["code"] == ma_quy_trinh) if ma_quy_trinh
                     else (q for q in cac_quy_trinh if not q["is_app_default"]), None)
    if quy_trinh is None:
        sys.exit(f"Không có quy trình {ma_quy_trinh or 'nào ngoài quy trình của ứng dụng minh họa'}.")
    loc = f"?process={urllib.parse.quote(quy_trinh['code'])}"
    cac_loai = nguoi_gui.get(f"/workflow/request-types{loc}")
    cac_trang_thai = nguoi_gui.get(f"/workflow/states{loc}")
    if not cac_loai:
        sys.exit(f"Quy trình {quy_trinh['code']} chưa có loại yêu cầu nào đang dùng.")
    loai = cac_loai[0]
    print(f"   Chọn “{quy_trinh['label']}”: loại “{loai['label']}”, {len(cac_trang_thai)} trạng thái ("
          + ", ".join(s["label"] for s in cac_trang_thai) + ")")

    phong = truong_phong.get("/identity/me")["departments"]
    if not phong:
        sys.exit(f"Tài khoản trưởng phòng {ch['tai_khoan'][1]['client']} không thuộc phòng nào "
                 "(KEYCLOAK_INTEGRATION_HEAD_GROUP).")
    chi_tiet = chi_tiet_mau(loai)
    chi_tiet.update({t["code"]: ch["so_tien"] for t in loai["fields"] if t["required"] and t["kind"] == "number"})
    ho_so = nguoi_gui.post("/workflow/requests", {
        "title": f"Đề xuất từ ứng dụng mua sắm mẫu, {dt.datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "description": "Tạo bằng examples/goi-loi/quy_trinh_mua_sam.py qua API của nền tảng lõi.",
        "request_type_code": loai["code"],
        "details": chi_tiet,
    })
    ma = ho_so["id"]
    print(f"3. Người đề xuất tạo hồ sơ {ho_so['code']} (mã {ma}) thuộc quy trình “{ho_so['process']['label']}”, "
          f"trạng thái “{ho_so['state']['label']}”, trường riêng {ho_so['details']}")
    buoc = buoc_chinh(nguoi_gui, ma, "người đề xuất")
    thay_doi = {TRUONG_PHONG_BAN: phong[0]} if TRUONG_PHONG_BAN in buoc["fields"] else {}
    di(nguoi_gui, ma, buoc, "người đề xuất", thay_doi)

    for so, (nen_tang, ai) in enumerate(((truong_phong, "trưởng phòng"), (duyet, "người duyệt cấp hai")), 4):
        print(f"{so}. {ai.capitalize()}: hồ sơ {'CÓ' if cho_toi(nen_tang, quy_trinh['code'], ma) else 'KHÔNG'} "
              "trong danh sách đang chờ mình")
        ho_so = di(nen_tang, ma, buoc_chinh(nen_tang, ma, ai), ai)
        # Điều kiện trên cạnh (#397): dưới ngưỡng thì trưởng phòng duyệt là xong, không còn cấp hai
        if ho_so["state"]["is_terminal"]:
            break

    ho_so = nguoi_gui.get(f"/workflow/requests/{ma}")
    print(f"6. Lịch sử hồ sơ {ho_so['code']} — các dòng nhật ký sự kiện ({len(ho_so['history'])}, giờ UTC):")
    for su_kien in ho_so["history"]:
        luc = dt.datetime.fromisoformat(su_kien["timestamp"].replace("Z", "+00:00"))
        print(f"   {luc.astimezone(dt.timezone.utc):%Y-%m-%d %H:%M:%S} · {su_kien['actor_label']} · "
              f"{su_kien['activity_label'] or su_kien['activity']}: "
              f"{su_kien['from_state_label']} → {su_kien['to_state_label']}")
    return 0 if ho_so["state"]["is_terminal"] else 1


def main() -> int:
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Ví dụ ứng dụng khác chạy trọn quy trình của nó qua API của nền tảng lõi.")
    p.add_argument("--so-tien", type=int, default=SO_MAU,
                   help=f"giá trị cho trường số bắt buộc (mặc định {SO_MAU:_}); quy trình mua sắm mẫu rẽ nhánh theo nó")
    p.add_argument("--quy-trinh", help="mã quy trình; mặc định quy trình đầu tiên không phải của ứng dụng minh họa")
    p.add_argument("--env-file", type=Path, default=Path("infra/.env"), help="tệp env của cụm (mặc định infra/.env)")
    p.add_argument("--cong-api", help="địa chỉ cổng API, mặc định http://localhost:<GATEWAY_PORT>")
    p.add_argument("--keycloak", help="địa chỉ Keycloak, mặc định http://localhost:<KEYCLOAK_PORT>")
    ts = p.parse_args()
    ch = cau_hinh(ts)
    ch["so_tien"] = ts.so_tien
    try:
        return chay(ch, ts.quy_trinh)
    except LoiGoi as loi:
        print(f"Lõi từ chối: {loi}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
