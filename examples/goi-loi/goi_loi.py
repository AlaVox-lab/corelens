# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ví dụ một ứng dụng KHÁC cổng người dùng gọi nền tảng lõi của Corelens (#365).
#
#     python examples/goi-loi/goi_loi.py
#     python examples/goi-loi/goi_loi.py --env-file duong/toi/tep.env
#     python examples/goi-loi/goi_loi.py --cong-api http://localhost:9080 --keycloak http://localhost:8080
#
# Kịch bản đóng vai một hệ thống bên ngoài (phần mềm nhân sự, ứng dụng di động…), không đăng nhập người
# dùng nào, không đi qua cổng người dùng:
#
#   1. Xin token của tài khoản dịch vụ bằng luồng client credentials của Keycloak
#   2. Từ đó CHỈ gọi qua cổng API và CHỈ bằng đường `/core/v1`:
#      danh tính → danh mục loại yêu cầu → tạo hồ sơ → bước chuyển được phép → đi một bước → lịch sử
#
# Không mã cứng mã trạng thái, mã loại hay mã bước nào: mọi thứ chọn từ dữ liệu API trả về, nên kịch bản
# chạy đúng với bất kỳ quy trình nào doanh nghiệp khai trong dữ liệu. Với dữ liệu mẫu và vai `requester`
# của tài khoản dịch vụ, bước đi được duy nhất làm đổi trạng thái là "Hủy yêu cầu" — nên mỗi lần chạy để
# lại một hồ sơ đã hủy, không nằm chờ trong hàng đợi của điều phối viên.
#
# Địa chỉ và tài khoản đọc từ tệp env của cụm (mặc định infra/.env): GATEWAY_PORT, KEYCLOAK_PORT,
# KEYCLOAK_REALM, KEYCLOAK_INTEGRATION_CLIENT_ID, KEYCLOAK_INTEGRATION_SECRET. Biến môi trường cùng tên ghi
# đè tệp (thêm GATEWAY_URL, KEYCLOAK_URL cho địa chỉ đầy đủ), tham số ghi đè cả hai. Chỉ dùng thư viện
# chuẩn, Python 3.10 trở lên.

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GOC_KHO = Path(__file__).resolve().parents[2]
# Không gian địa chỉ có phiên bản của nền tảng lõi
TIEN_TO_LOI = "/core/v1"

# Giá trị mẫu cho trường riêng bắt buộc, theo KIỂU trường (từ vựng của lược đồ, không phải nghiệp vụ).
# Trường kiểu lựa chọn lấy lựa chọn đầu tiên API trả về.
MAU_THEO_KIEU = {"text": "Nhập từ ứng dụng tích hợp mẫu", "number": 1}


class LoiGoi(Exception):
    def __init__(self, ma: int, noi_dung: str) -> None:
        super().__init__(f"HTTP {ma}: {noi_dung}")
        self.ma = ma


# ---------------------------------------------------------------------------
# Cấu hình
# ---------------------------------------------------------------------------


def doc_tep_env(tep: Path) -> dict[str, str]:
    if not tep.is_file():
        return {}
    bien = {}
    for dong in tep.read_text(encoding="utf-8").splitlines():
        dong = dong.strip()
        if not dong or dong.startswith("#") or "=" not in dong:
            continue
        khoa, _, gia_tri = dong.partition("=")
        gia_tri = gia_tri.strip()
        if len(gia_tri) >= 2 and gia_tri[0] == gia_tri[-1] and gia_tri[0] in "\"'":
            gia_tri = gia_tri[1:-1]
        bien[khoa.strip()] = gia_tri
    return bien


def cau_hinh(ts: argparse.Namespace) -> dict[str, str]:
    tep = ts.env_file if ts.env_file.is_absolute() else Path.cwd() / ts.env_file
    if not tep.is_file() and not ts.env_file.is_absolute():
        tep = GOC_KHO / ts.env_file
    env = doc_tep_env(tep)

    def lay(ten: str) -> str | None:
        return os.environ.get(ten) or env.get(ten)

    def dia_chi(tham_so: str | None, bien_day_du: str, bien_cong: str) -> str | None:
        cong = lay(bien_cong)
        return tham_so or lay(bien_day_du) or (f"http://localhost:{cong}" if cong else None)

    gia_tri = {
        "cong_api": dia_chi(ts.cong_api, "GATEWAY_URL", "GATEWAY_PORT"),
        "keycloak": dia_chi(ts.keycloak, "KEYCLOAK_URL", "KEYCLOAK_PORT"),
        "realm": lay("KEYCLOAK_REALM"),
        "client": lay("KEYCLOAK_INTEGRATION_CLIENT_ID"),
        "bi_mat": lay("KEYCLOAK_INTEGRATION_SECRET"),
    }
    ten_bien = {
        "cong_api": "GATEWAY_PORT (hoặc --cong-api)",
        "keycloak": "KEYCLOAK_PORT (hoặc --keycloak)",
        "realm": "KEYCLOAK_REALM",
        "client": "KEYCLOAK_INTEGRATION_CLIENT_ID",
        "bi_mat": "KEYCLOAK_INTEGRATION_SECRET",
    }
    thieu = [k for k, v in gia_tri.items() if not v]
    if thieu:
        sys.exit(f"Thiếu {', '.join(ten_bien[k] for k in thieu)} — không thấy trong {tep} lẫn biến môi trường.")
    gia_tri["cong_api"] = gia_tri["cong_api"].rstrip("/")
    gia_tri["keycloak"] = gia_tri["keycloak"].rstrip("/")
    return gia_tri


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


def goi(url: str, *, phuong_thuc: str = "GET", token: str | None = None, json_than: object | None = None,
        form: dict[str, str] | None = None) -> object:
    tieu_de = {"Accept": "application/json"}
    du_lieu = None
    if json_than is not None:
        du_lieu = json.dumps(json_than).encode("utf-8")
        tieu_de["Content-Type"] = "application/json; charset=utf-8"
    elif form is not None:
        du_lieu = urllib.parse.urlencode(form).encode("utf-8")
        tieu_de["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        tieu_de["Authorization"] = f"Bearer {token}"
    yc = urllib.request.Request(url, data=du_lieu, headers=tieu_de, method=phuong_thuc)
    try:
        with urllib.request.urlopen(yc, timeout=30) as tl:
            return json.loads(tl.read() or b"null")
    except urllib.error.HTTPError as loi:
        than = loi.read().decode("utf-8", "replace")
        try:
            chi_tiet = json.loads(than).get("detail", than)
            if isinstance(chi_tiet, dict):
                chi_tiet = chi_tiet.get("message", chi_tiet)
        except (ValueError, AttributeError):
            chi_tiet = than
        raise LoiGoi(loi.code, str(chi_tiet)[:300]) from None
    except (urllib.error.URLError, OSError) as loi:
        sys.exit(f"Không kết nối được {url}: {loi}. Cụm đã chạy chưa?")


class NenTangLoi:
    """Máy khách của nền tảng lõi: mọi lời gọi đi qua cổng API, dưới `/core/v1`."""

    def __init__(self, cong_api: str, token: str) -> None:
        self.goc = f"{cong_api}{TIEN_TO_LOI}"
        self.token = token

    def get(self, duong: str) -> object:
        return goi(f"{self.goc}{duong}", token=self.token)

    def post(self, duong: str, than: object) -> object:
        return goi(f"{self.goc}{duong}", phuong_thuc="POST", token=self.token, json_than=than)


# ---------------------------------------------------------------------------
# Các bước
# ---------------------------------------------------------------------------


def xin_token(ch: dict[str, str]) -> str:
    try:
        ket_qua = goi(
            f"{ch['keycloak']}/realms/{urllib.parse.quote(ch['realm'])}/protocol/openid-connect/token",
            phuong_thuc="POST",
            form={"grant_type": "client_credentials", "client_id": ch["client"], "client_secret": ch["bi_mat"]},
        )
    except LoiGoi as loi:
        sys.exit(
            f"Keycloak không cấp token cho client {ch['client']} ({loi}). Cụm dựng trước #365 thì tạo client "
            "bằng: python scripts/tai_khoan_dich_vu.py"
        )
    print(f"1. Token của tài khoản dịch vụ {ch['client']}: luồng client credentials, sống {ket_qua['expires_in']} giây")
    return ket_qua["access_token"]


def chi_tiet_mau(loai: dict) -> dict:
    """Trường riêng bắt buộc của loại yêu cầu, điền theo khai báo API trả về."""
    hom_nay = dt.date.today().isoformat()
    ket_qua = {}
    for truong in loai.get("fields", []):
        if not truong["required"]:
            continue
        if truong["kind"] == "choice":
            ket_qua[truong["code"]] = truong["options"][0]
        elif truong["kind"] == "date":
            ket_qua[truong["code"]] = hom_nay
        else:
            ket_qua[truong["code"]] = MAU_THEO_KIEU.get(truong["kind"], MAU_THEO_KIEU["text"])
    return ket_qua


def chon_buoc(cac_buoc: list[dict]) -> dict:
    """Bước để đi: bước chính của người gọi nếu có, không thì bước đầu tiên làm đổi trạng thái, không thì
    bước đầu tiên. Thứ tự giữ nguyên thứ tự API trả (thứ tự hiển thị trong dữ liệu)."""
    for dieu_kien in (lambda b: b["is_primary"], lambda b: not b["keeps_state"], lambda b: True):
        for buoc in cac_buoc:
            if dieu_kien(buoc):
                return buoc
    raise AssertionError  # danh sách rỗng đã được loại trước


def in_lich_su(ho_so: dict) -> None:
    print(f"6. Lịch sử hồ sơ {ho_so['code']} ({len(ho_so['history'])} sự kiện, giờ UTC):")
    for su_kien in ho_so["history"]:
        # Python 3.10 chưa đọc được hậu tố Z
        luc = dt.datetime.fromisoformat(su_kien["timestamp"].replace("Z", "+00:00"))
        luc = luc.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        hoat_dong = su_kien["activity_label"] or su_kien["activity"]
        dong = (f"   {luc} · {su_kien['actor_label']} · {hoat_dong}: "
                f"{su_kien['from_state_label']} → {su_kien['to_state_label']}")
        if su_kien.get("note"):
            dong += f" · ghi chú: {su_kien['note']}"
        print(dong)


def chay(ch: dict[str, str]) -> int:
    nen_tang = NenTangLoi(ch["cong_api"], xin_token(ch))

    toi = nen_tang.get("/identity/me")
    print(f"2. Danh tính theo lõi: {toi['username']} · vai {', '.join(toi['roles'])}")

    cac_loai = nen_tang.get("/workflow/request-types")
    if not cac_loai:
        sys.exit("Danh mục loại yêu cầu rỗng — dữ liệu khởi tạo chưa nạp?")
    loai = cac_loai[0]
    print(f"3. Danh mục: {len(cac_loai)} loại yêu cầu ({', '.join(x['label'] for x in cac_loai)}); "
          f"chọn “{loai['label']}”")

    ho_so = nen_tang.post("/workflow/requests", {
        "title": f"Yêu cầu từ ứng dụng tích hợp mẫu, {dt.datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "description": "Tạo bằng examples/goi-loi/goi_loi.py qua API của nền tảng lõi, không qua cổng người dùng.",
        "request_type_code": loai["code"],
        "details": chi_tiet_mau(loai),
    })
    print(f"4. Đã tạo hồ sơ {ho_so['code']} (mã {ho_so['id']}), trạng thái “{ho_so['state']['label']}”")

    cac_buoc = nen_tang.get(f"/workflow/requests/{ho_so['id']}")["allowed_transitions"]
    if not cac_buoc:
        print("   Vai của tài khoản dịch vụ không đi được bước nào ở trạng thái này — dừng ở đây.")
        return 1
    print("   Bước tài khoản dịch vụ đi được: "
          + "; ".join(f"{b['activity_label']} → {b['to_state_label']}" for b in cac_buoc))
    buoc = chon_buoc(cac_buoc)
    ghi_chu = "Ứng dụng tích hợp mẫu đi bước này qua API của lõi." if buoc["requires_note"] else None
    ho_so = nen_tang.post(f"/workflow/requests/{ho_so['id']}/transitions",
                          {"to_state": buoc["to_state"], "note": ghi_chu})
    print(f"5. Đã đi bước “{buoc['activity_label']}”: hồ sơ giờ ở “{ho_so['state']['label']}”")

    in_lich_su(nen_tang.get(f"/workflow/requests/{ho_so['id']}"))
    return 0


def main() -> int:
    # Bảng điều khiển Windows mặc định không phải UTF-8
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Ví dụ ứng dụng khác gọi API của nền tảng lõi Corelens qua cổng API.")
    p.add_argument("--env-file", type=Path, default=Path("infra/.env"), help="tệp env của cụm (mặc định infra/.env)")
    p.add_argument("--cong-api", help="địa chỉ cổng API, mặc định http://localhost:<GATEWAY_PORT>")
    p.add_argument("--keycloak", help="địa chỉ Keycloak, mặc định http://localhost:<KEYCLOAK_PORT>")
    ch = cau_hinh(p.parse_args())
    try:
        return chay(ch)
    except LoiGoi as loi:
        goi_y = {401: " — token bị cổng API từ chối", 403: " — không đủ quyền", 429: " — gọi quá nhanh, thử lại sau"}
        print(f"Lõi từ chối: {loi}{goi_y.get(loi.ma, '')}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
