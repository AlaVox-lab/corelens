# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Tạo hoặc cập nhật tài khoản dịch vụ để một ứng dụng khác gọi API của nền tảng lõi `/core/v1` (#365).
#
#     python scripts/tai_khoan_dich_vu.py
#     python scripts/tai_khoan_dich_vu.py --env-file infra/.env --keycloak http://localhost:8080
#
# Kết quả là một client bí mật trong realm, CHỈ bật tài khoản dịch vụ (luồng client credentials), có bộ ánh
# xạ đưa mã client của dịch vụ ứng dụng vào `aud` của token — cùng cách client của cổng người dùng đang làm
# — và tài khoản dịch vụ mang các vai realm khai ở KEYCLOAK_INTEGRATION_ROLES. Cuối cùng kịch bản xin thử
# một token bằng chính client đó để chắc mọi thứ khớp: cổng API và dịch vụ ứng dụng sẽ nhận nó.
#
# Vì sao có kịch bản này khi realm-dx-os-lab.json đã khai client dx-integration: Keycloak chỉ nạp tệp realm
# lúc tạo realm, nên cụm dựng trước #365 không bao giờ thấy client mới. Một đường duy nhất — kiểm, thiếu thì
# tạo, có rồi thì đặt lại cấu hình và bí mật theo tệp env — chạy được cho cả cụm mới lẫn cụm cũ nâng lên,
# không cần `down -v`. Cùng khuôn với infra/tri-thuc/khoi_tao.py và scripts/xac_thuc_hai_lop.py.
#
# Từ #376 kịch bản dựng thêm hai tài khoản DUYỆT cho ví dụ quy trình thứ hai (đề xuất mua sắm duyệt hai cấp):
# KEYCLOAK_INTEGRATION_HEAD_* (trưởng phòng — vai approver, vào group phòng ban ở *_GROUP, token mang claim
# `groups`) và KEYCLOAK_INTEGRATION_REVIEWER_* (duyệt cấp hai — vai classifier). Hai tài khoản này tùy chọn:
# tệp env không khai thì bỏ qua. Mỗi tài khoản đi đúng các bước như tài khoản đầu.
#
# Chạy lại bao nhiêu lần cũng được. Kịch bản không gỡ vai nào tài khoản đã có ngoài danh sách — quản trị
# viên có thể đã cố ý gán thêm — chỉ báo ra. Địa chỉ Keycloak, realm, tài khoản quản trị và các biến
# KEYCLOAK_API_CLIENT_ID, KEYCLOAK_INTEGRATION_* đọc từ tệp env của cụm (mặc định infra/.env); biến môi
# trường cùng tên ghi đè tệp, tham số ghi đè cả hai. Chỉ dùng thư viện chuẩn, Python 3.10 trở lên.

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GOC_KHO = Path(__file__).resolve().parent.parent

# Từ vựng của chính Keycloak, không phải giá trị nghiệp vụ
BO_ANH_XA_NGUOI_NHAN = "oidc-audience-mapper"
BO_ANH_XA_NHOM = "oidc-group-membership-mapper"

# (tiền tố biến, bắt buộc) — tài khoản tạo hồ sơ của #365, rồi hai tài khoản duyệt của quy trình thứ hai (#376)
TAI_KHOAN = (
    ("KEYCLOAK_INTEGRATION", True),
    ("KEYCLOAK_INTEGRATION_HEAD", False),
    ("KEYCLOAK_INTEGRATION_REVIEWER", False),
)

# Nhãn và mô tả chỉ đặt khi TẠO client; client đã có thì giữ nguyên, quản trị viên có thể đã đổi
NHAN_CLIENT = "Ứng dụng tích hợp mẫu"
MO_TA_CLIENT = (
    "Tài khoản dịch vụ để một ứng dụng khác gọi API của nền tảng lõi (/core/v1) qua cổng API (#365, #376). "
    "Chỉ bật client credentials. Tạo bởi scripts/tai_khoan_dich_vu.py."
)


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


def cau_hinh(ts: argparse.Namespace) -> dict:
    tep = ts.env_file if ts.env_file.is_absolute() else Path.cwd() / ts.env_file
    if not tep.is_file() and not ts.env_file.is_absolute():
        tep = GOC_KHO / ts.env_file
    env = doc_tep_env(tep)

    def lay(ten: str) -> str | None:
        return os.environ.get(ten) or env.get(ten)

    cong = lay("KEYCLOAK_PORT")
    gia_tri = {
        "goc": ts.keycloak or lay("KEYCLOAK_URL") or (f"http://localhost:{cong}" if cong else None),
        "realm": ts.realm or lay("KEYCLOAK_REALM"),
        "nguoi": lay("KEYCLOAK_ADMIN_USER"),
        "mat_khau": lay("KEYCLOAK_ADMIN_PASSWORD"),
        "nguoi_nhan": lay("KEYCLOAK_API_CLIENT_ID"),
    }
    ten_bien = {
        "goc": "KEYCLOAK_PORT (hoặc --keycloak)",
        "realm": "KEYCLOAK_REALM (hoặc --realm)",
        "nguoi": "KEYCLOAK_ADMIN_USER",
        "mat_khau": "KEYCLOAK_ADMIN_PASSWORD",
        "nguoi_nhan": "KEYCLOAK_API_CLIENT_ID",
    }
    thieu = [ten_bien[k] for k, v in gia_tri.items() if not v]

    # Mỗi tài khoản một tiền tố biến: _CLIENT_ID, _SECRET, _ROLES, _GROUP (tùy chọn). Tài khoản đầu bắt buộc
    # (#365); hai tài khoản duyệt của ví dụ quy trình thứ hai (#376) có biến thì dựng, không thì bỏ qua
    gia_tri["tai_khoan"] = []
    for tien_to, bat_buoc in TAI_KHOAN:
        tk = {
            "client": lay(f"{tien_to}_CLIENT_ID"),
            "bi_mat": lay(f"{tien_to}_SECRET"),
            "vai": lay(f"{tien_to}_ROLES"),
            "nhom": lay(f"{tien_to}_GROUP"),
            "tien_to": tien_to,
        }
        if not bat_buoc and not tk["client"]:
            print(f"Bỏ qua {tien_to}_*: không khai trong tệp env (tùy chọn).")
            continue
        thieu += [f"{tien_to}_{ten}" for k, ten in (("client", "CLIENT_ID"), ("bi_mat", "SECRET"), ("vai", "ROLES"))
                  if not tk[k]]
        if tk["vai"]:
            tk["vai"] = [v.strip() for v in tk["vai"].split(",") if v.strip()]
            if not tk["vai"]:
                sys.exit(f"{tien_to}_ROLES rỗng: tài khoản dịch vụ không vai nào thì không đi được bước nào.")
        gia_tri["tai_khoan"].append(tk)
    if thieu:
        sys.exit(
            f"Thiếu {', '.join(thieu)} — không thấy trong {tep} lẫn biến môi trường. "
            "Cụm nâng cấp từ bản cũ: chép các dòng KEYCLOAK_INTEGRATION_* từ infra/.env.example sang tệp env."
        )
    gia_tri["goc"] = gia_tri["goc"].rstrip("/")
    return gia_tri


# ---------------------------------------------------------------------------
# HTTP và API quản trị Keycloak
# ---------------------------------------------------------------------------


def http(url: str, phuong_thuc: str, du_lieu: bytes | None, tieu_de: dict) -> tuple[int, bytes]:
    yc = urllib.request.Request(url, data=du_lieu, headers=tieu_de, method=phuong_thuc)
    try:
        with urllib.request.urlopen(yc, timeout=30) as tl:
            return tl.status, tl.read()
    except urllib.error.HTTPError as loi:
        return loi.code, loi.read()
    except (urllib.error.URLError, OSError) as loi:
        sys.exit(f"Không kết nối được {url.split('/realms/')[0].split('/admin/')[0]}: {loi}. Cụm đã chạy chưa?")


def xin_token(goc: str, realm: str, form: dict[str, str]) -> tuple[int, bytes]:
    return http(
        f"{goc}/realms/{urllib.parse.quote(realm)}/protocol/openid-connect/token",
        "POST",
        urllib.parse.urlencode(form).encode("utf-8"),
        {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )


class Keycloak:
    def __init__(self, ch: dict) -> None:
        self.goc = ch["goc"]
        self.realm = ch["realm"]
        self._nguoi = ch["nguoi"]
        self._mat_khau = ch["mat_khau"]
        self._token: str | None = None
        self.api = f"{self.goc}/admin/realms/{urllib.parse.quote(self.realm)}"

    def dang_nhap(self) -> None:
        ma, than = xin_token(
            self.goc,
            "master",
            {"grant_type": "password", "client_id": "admin-cli", "username": self._nguoi, "password": self._mat_khau},
        )
        if ma != 200:
            sys.exit(f"Keycloak từ chối đăng nhập quản trị ({ma}). Kiểm KEYCLOAK_ADMIN_USER/KEYCLOAK_ADMIN_PASSWORD.")
        self._token = json.loads(than)["access_token"]

    def goi(self, duong: str, phuong_thuc: str = "GET", json_than: object | None = None,
            chap_nhan: tuple[int, ...] = ()) -> object:
        """Gọi API quản trị của realm. Token quản trị chỉ sống một phút, hết hạn giữa chừng thì lấy lại. Mã
        trong `chap_nhan` trả None thay vì dừng kịch bản."""
        du_lieu = json.dumps(json_than).encode("utf-8") if json_than is not None else None
        for lan in range(2):
            if self._token is None:
                self.dang_nhap()
            tieu_de = {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}
            if du_lieu is not None:
                tieu_de["Content-Type"] = "application/json; charset=utf-8"
            ma, than = http(f"{self.api}{duong}", phuong_thuc, du_lieu, tieu_de)
            if ma == 401 and lan == 0:
                self._token = None
                continue
            if ma in chap_nhan:
                return None
            if ma == 404 and duong == "":
                sys.exit(f"Không có realm {self.realm} trên {self.goc}.")
            if ma >= 300:
                sys.exit(f"{phuong_thuc} {duong or '/'} trả {ma}: {than[:300].decode('utf-8', 'replace')}")
            return json.loads(than) if than else None
        return None


# ---------------------------------------------------------------------------
# Ba việc: client, bộ ánh xạ người nhận, vai của tài khoản dịch vụ
# ---------------------------------------------------------------------------


def dam_bao_client(kc: Keycloak, tk: dict) -> tuple[str, bool]:
    """(mã nội bộ của client, vừa tạo hay không). Client đã có thì đặt lại cấu hình và bí mật theo tệp env."""
    mong_muon = {
        "clientId": tk["client"],
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,
        "clientAuthenticatorType": "client-secret",
        "secret": tk["bi_mat"],
        # Chỉ tài khoản dịch vụ: không đăng nhập người dùng qua client này
        "standardFlowEnabled": False,
        "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": True,
    }
    tim = f"/clients?clientId={urllib.parse.quote(tk['client'])}"
    co_san = kc.goi(tim)
    if co_san:
        kc.goi(f"/clients/{co_san[0]['id']}", "PUT", {**co_san[0], **mong_muon})
        return co_san[0]["id"], False
    kc.goi("/clients", "POST", {**mong_muon, "name": NHAN_CLIENT, "description": MO_TA_CLIENT})
    return kc.goi(tim)[0]["id"], True


def dam_bao_nguoi_nhan(kc: Keycloak, id_client: str, nguoi_nhan: str) -> bool:
    """Token mang mã client của dịch vụ ứng dụng trong `aud`. Trả True nếu vừa thêm bộ ánh xạ."""
    duong = f"/clients/{id_client}/protocol-mappers/models"
    for m in kc.goi(duong):
        if m.get("protocolMapper") == BO_ANH_XA_NGUOI_NHAN and \
                m.get("config", {}).get("included.client.audience") == nguoi_nhan:
            return False
    kc.goi(duong, "POST", {
        "name": f"audience-{nguoi_nhan}",
        "protocol": "openid-connect",
        "protocolMapper": BO_ANH_XA_NGUOI_NHAN,
        "config": {"included.client.audience": nguoi_nhan, "access.token.claim": "true", "id.token.claim": "false"},
    })
    return True


def dam_bao_vai(kc: Keycloak, id_client: str, vai_can: list[str]) -> tuple[list[str], list[str]]:
    """(vai vừa gán, vai khác tài khoản đã mang). Không gỡ vai nào."""
    tai_khoan = kc.goi(f"/clients/{id_client}/service-account-user")
    duong = f"/users/{tai_khoan['id']}/role-mappings/realm"
    da_co = {r["name"] for r in kc.goi(duong)}
    can_gan = []
    for ten in vai_can:
        if ten in da_co:
            continue
        vai = kc.goi(f"/roles/{urllib.parse.quote(ten)}", chap_nhan=(404,))
        if vai is None:
            sys.exit(f"Realm {kc.realm} không có vai '{ten}' (biến *_ROLES). Không gán gì thêm.")
        can_gan.append(vai)
    if can_gan:
        kc.goi(duong, "POST", can_gan)
    # Vai mặc định của realm Keycloak tự gán cho mọi tài khoản, không tính là "gán thêm"
    khac = sorted(da_co - set(vai_can) - {f"default-roles-{kc.realm}"})
    return [v["name"] for v in can_gan], khac


def kiem_token(ch: dict, tk: dict) -> dict:
    """Xin một token bằng chính client vừa dựng, kiểm `aud` và vai. Không kiểm chữ ký — việc đó cổng API và
    dịch vụ ứng dụng làm; ở đây chỉ chắc cấu hình cho ra đúng token."""
    ma, than = xin_token(ch["goc"], ch["realm"], {
        "grant_type": "client_credentials", "client_id": tk["client"], "client_secret": tk["bi_mat"],
    })
    if ma != 200:
        sys.exit(f"Không xin được token bằng client {tk['client']} ({ma}): {than[:200].decode('utf-8', 'replace')}")
    phan_giua = json.loads(than)["access_token"].split(".")[1]
    claim = json.loads(base64.urlsafe_b64decode(phan_giua + "=" * (-len(phan_giua) % 4)))
    aud = claim.get("aud")
    aud = aud if isinstance(aud, list) else [aud]
    if ch["nguoi_nhan"] not in aud:
        sys.exit(f"Token thiếu '{ch['nguoi_nhan']}' trong aud (đang là {aud}): cổng API sẽ trả 403.")
    vai = claim.get("realm_access", {}).get("roles", [])
    thieu = [v for v in tk["vai"] if v not in vai]
    if thieu:
        sys.exit(f"Token thiếu vai {', '.join(thieu)} (đang có {sorted(vai)}).")
    if tk["nhom"] and tk["nhom"] not in claim.get("groups", []):
        sys.exit(f"Token thiếu group {tk['nhom']} (đang có {claim.get('groups')}): trưởng phòng sẽ không thấy hồ sơ "
                 "của phòng mình.")
    return claim


def dam_bao_nhom(kc: Keycloak, id_client: str, nhom: str) -> tuple[bool, bool]:
    """(vừa thêm bộ ánh xạ groups, vừa vào group). Tài khoản dịch vụ thuộc group phòng ban và token mang claim
    `groups` như token của cổng người dùng — dịch vụ ứng dụng đọc phòng của người gọi từ đó (#376)."""
    duong = f"/clients/{id_client}/protocol-mappers/models"
    them_bo = not any(m.get("protocolMapper") == BO_ANH_XA_NHOM for m in kc.goi(duong))
    if them_bo:
        kc.goi(duong, "POST", {
            "name": "groups",
            "protocol": "openid-connect",
            "protocolMapper": BO_ANH_XA_NHOM,
            "config": {"full.path": "true", "claim.name": "groups", "access.token.claim": "true",
                       "id.token.claim": "false", "userinfo.token.claim": "false"},
        })
    nhom_kc = kc.goi(f"/group-by-path/{urllib.parse.quote(nhom.lstrip('/'))}", chap_nhan=(404,))
    if nhom_kc is None:
        sys.exit(f"Realm {kc.realm} không có group '{nhom}' (biến *_GROUP).")
    tai_khoan = kc.goi(f"/clients/{id_client}/service-account-user")
    da_vao = any(g.get("id") == nhom_kc["id"] for g in kc.goi(f"/users/{tai_khoan['id']}/groups"))
    if not da_vao:
        kc.goi(f"/users/{tai_khoan['id']}/groups/{nhom_kc['id']}", "PUT")
    return them_bo, not da_vao


def dung_tai_khoan(kc: Keycloak, ch: dict, tk: dict) -> None:
    id_client, moi = dam_bao_client(kc, tk)
    print(f"Client {tk['client']}: " + (
        "đã tạo — chỉ bật tài khoản dịch vụ (client credentials)" if moi
        else "đã có — đặt lại cấu hình và bí mật theo tệp env"
    ))
    them = dam_bao_nguoi_nhan(kc, id_client, ch["nguoi_nhan"])
    print(f"  Người nhận của token: {'đã thêm bộ ánh xạ' if them else 'đã có bộ ánh xạ'}, aud mang {ch['nguoi_nhan']}")
    gan, khac = dam_bao_vai(kc, id_client, tk["vai"])
    print(f"  Vai của tài khoản dịch vụ: {', '.join(tk['vai'])}"
          + (f" (vừa gán {', '.join(gan)})" if gan else " (đã có từ trước)"))
    if khac:
        print(f"  Tài khoản còn mang vai khác: {', '.join(khac)} — giữ nguyên, gỡ tay nếu không cần.")
    if tk["nhom"]:
        them_bo, vao = dam_bao_nhom(kc, id_client, tk["nhom"])
        print(f"  Group {tk['nhom']}: {'vừa thêm' if vao else 'đã ở trong'}"
              + (", vừa thêm bộ ánh xạ groups" if them_bo else ""))
    claim = kiem_token(ch, tk)
    print(f"  Kiểm token: aud {claim.get('aud')}, vai {sorted(claim.get('realm_access', {}).get('roles', []))}"
          + (f", groups {claim.get('groups')}" if tk["nhom"] else "")
          + f", sống {claim['exp'] - claim['iat']} giây.")


def main() -> int:
    # Bảng điều khiển Windows mặc định không phải UTF-8
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(
        description="Tạo hoặc cập nhật tài khoản dịch vụ cho ứng dụng khác gọi API của nền tảng lõi /core/v1."
    )
    p.add_argument("--env-file", type=Path, default=Path("infra/.env"), help="tệp env của cụm (mặc định infra/.env)")
    p.add_argument("--keycloak", help="địa chỉ Keycloak, mặc định http://localhost:<KEYCLOAK_PORT>")
    p.add_argument("--realm", help="realm, mặc định KEYCLOAK_REALM")
    ch = cau_hinh(p.parse_args())

    kc = Keycloak(ch)
    print(f"Realm {kc.realm} tại {kc.goc}")
    for tk in ch["tai_khoan"]:
        dung_tai_khoan(kc, ch, tk)
    print("Xong. Ứng dụng khác lấy token bằng client credentials rồi gọi /core/v1 qua cổng API — xem examples/goi-loi/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
