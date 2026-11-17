# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Bật, tắt và xem xác thực hai lớp (mã dùng một lần TOTP) cho mọi tài khoản của realm (#366).
#
#     python scripts/xac_thuc_hai_lop.py trang-thai
#     python scripts/xac_thuc_hai_lop.py bat
#     python scripts/xac_thuc_hai_lop.py tat              # thôi buộc; mã đã thiết lập vẫn được hỏi
#     python scripts/xac_thuc_hai_lop.py tat --xoa-ma     # thôi buộc VÀ xóa mã đã thiết lập
#     python scripts/xac_thuc_hai_lop.py chong-do         # áp chống dò mật khẩu + chính sách mật khẩu (#377)
#
# `chong-do` đưa realm đang chạy về đúng mặc định bảo mật đăng nhập của realm mẫu: chống dò mật khẩu (khóa tạm
# tài khoản sau một số lần sai liên tiếp, tự mở sau vài phút) và chính sách mật khẩu tối thiểu. Giá trị đọc
# từ chính infra/keycloak/realm-dx-os-lab.json — một nguồn sự thật cho cụm dựng mới và cụm nâng cấp; kịch bản
# không mang con số nào. Chạy lại bao nhiêu lần cũng được. `trang-thai` in cả hai thứ này.
#
# Cách làm — chỉ cấu hình qua API quản trị của Keycloak, không sửa mã hay ảnh của nền tảng (ADR-0001):
#
#   bat  Hành động bắt buộc CONFIGURE_TOTP của Keycloak thành mặc định cho tài khoản mới, và gán cho mọi
#        tài khoản hiện có chưa có mã. Lần đăng nhập kế, người dùng phải quét mã QR bằng ứng dụng xác thực.
#        Từ đó luồng đăng nhập trình duyệt mặc định của Keycloak tự hỏi mã, vì nó hỏi mã với mọi tài khoản
#        đã có mã — kịch bản không đổi luồng nào.
#   tat  Bỏ mặc định, gỡ hành động còn treo ở tài khoản chưa kịp thiết lập. Tài khoản đã thiết lập mã vẫn
#        bị hỏi mã cho tới khi xóa mã: thêm cờ --xoa-ma, hoặc người dùng tự gỡ ở trang tài khoản Keycloak.
#
# Vì sao không sửa realm-dx-os-lab.json: Keycloak chỉ nạp tệp realm lúc tạo realm, nên cụm đang chạy không
# bao giờ thấy thay đổi trong tệp. API quản trị chạy được cho cả cụm mới lẫn cụm đã có dữ liệu.
#
# Chạy lại bao nhiêu lần cũng được: thứ đã đúng thì để yên. Địa chỉ Keycloak, realm và tài khoản quản trị
# đọc từ tệp env của cụm (mặc định infra/.env); biến môi trường cùng tên ghi đè tệp, tham số ghi đè cả hai.
# Chỉ dùng thư viện chuẩn, Python 3.10 trở lên.

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GOC_KHO = Path(__file__).resolve().parent.parent

# Từ vựng của chính Keycloak, không phải giá trị nghiệp vụ
HANH_DONG = "CONFIGURE_TOTP"
LOAI_MA = "otp"
BUOC_HOI_MA = "auth-otp-form"
TRANG = 100

# Mặc định bảo mật đăng nhập của realm mẫu (#377): các khóa này của realm-dx-os-lab.json được áp lên realm đang
# chạy. Tên khóa là từ vựng của Keycloak; giá trị nằm trong tệp realm.
TEP_REALM = GOC_KHO / "infra" / "keycloak" / "realm-dx-os-lab.json"
KHOA_CHONG_DO = (
    "bruteForceProtected",
    "permanentLockout",
    "failureFactor",
    "waitIncrementSeconds",
    "maxFailureWaitSeconds",
    "maxDeltaTimeSeconds",
    "quickLoginCheckMilliSeconds",
    "minimumQuickLoginWaitSeconds",
    "passwordPolicy",
)


def mac_dinh_bao_mat() -> dict:
    """Các khóa chống dò mật khẩu và chính sách mật khẩu, đọc từ tệp realm mẫu."""
    if not TEP_REALM.is_file():
        sys.exit(f"Không thấy {TEP_REALM} — chạy kịch bản từ kho mã.")
    realm = json.loads(TEP_REALM.read_text(encoding="utf-8"))
    thieu = [k for k in KHOA_CHONG_DO if k not in realm]
    if thieu:
        sys.exit(f"{TEP_REALM.name} thiếu khóa {', '.join(thieu)}.")
    return {k: realm[k] for k in KHOA_CHONG_DO}


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

    cong = lay("KEYCLOAK_PORT")
    goc = ts.keycloak or lay("KEYCLOAK_URL") or (f"http://localhost:{cong}" if cong else None)
    gia_tri = {
        "goc": goc,
        "realm": ts.realm or lay("KEYCLOAK_REALM"),
        "nguoi": lay("KEYCLOAK_ADMIN_USER"),
        "mat_khau": lay("KEYCLOAK_ADMIN_PASSWORD"),
    }
    thieu = [k for k, v in gia_tri.items() if not v]
    if thieu:
        ten_bien = {
            "goc": "KEYCLOAK_PORT (hoặc --keycloak)",
            "realm": "KEYCLOAK_REALM (hoặc --realm)",
            "nguoi": "KEYCLOAK_ADMIN_USER",
            "mat_khau": "KEYCLOAK_ADMIN_PASSWORD",
        }
        sys.exit(f"Thiếu {', '.join(ten_bien[k] for k in thieu)} — không thấy trong {tep} lẫn biến môi trường.")
    gia_tri["goc"] = gia_tri["goc"].rstrip("/")
    return gia_tri


# ---------------------------------------------------------------------------
# API quản trị Keycloak
# ---------------------------------------------------------------------------


class Keycloak:
    def __init__(self, ch: dict[str, str]) -> None:
        self.goc = ch["goc"]
        self.realm = ch["realm"]
        self._nguoi = ch["nguoi"]
        self._mat_khau = ch["mat_khau"]
        self._token: str | None = None
        self.api = f"{self.goc}/admin/realms/{urllib.parse.quote(self.realm)}"

    def _http(self, url: str, phuong_thuc: str, du_lieu: bytes | None, tieu_de: dict) -> tuple[int, bytes]:
        yc = urllib.request.Request(url, data=du_lieu, headers=tieu_de, method=phuong_thuc)
        try:
            with urllib.request.urlopen(yc, timeout=30) as tl:
                return tl.status, tl.read()
        except urllib.error.HTTPError as loi:
            return loi.code, loi.read()
        except (urllib.error.URLError, OSError) as loi:
            sys.exit(f"Không kết nối được Keycloak tại {self.goc}: {loi}. Cụm đã chạy chưa?")

    def dang_nhap(self) -> None:
        ma, than = self._http(
            f"{self.goc}/realms/master/protocol/openid-connect/token",
            "POST",
            urllib.parse.urlencode(
                {"grant_type": "password", "client_id": "admin-cli", "username": self._nguoi, "password": self._mat_khau}
            ).encode("utf-8"),
            {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        )
        if ma != 200:
            sys.exit(f"Keycloak từ chối đăng nhập quản trị ({ma}). Kiểm KEYCLOAK_ADMIN_USER/KEYCLOAK_ADMIN_PASSWORD.")
        self._token = json.loads(than)["access_token"]

    def goi(self, duong: str, phuong_thuc: str = "GET", json_than: object | None = None) -> object:
        """Gọi API quản trị của realm. Token quản trị chỉ sống một phút, hết hạn giữa chừng thì lấy lại."""
        du_lieu = json.dumps(json_than).encode("utf-8") if json_than is not None else None
        for lan in range(2):
            if self._token is None:
                self.dang_nhap()
            tieu_de = {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}
            if du_lieu is not None:
                tieu_de["Content-Type"] = "application/json; charset=utf-8"
            ma, than = self._http(f"{self.api}{duong}", phuong_thuc, du_lieu, tieu_de)
            if ma == 401 and lan == 0:
                self._token = None
                continue
            if ma == 404 and duong == "":
                sys.exit(f"Không có realm {self.realm} trên {self.goc}.")
            if ma >= 300:
                sys.exit(f"{phuong_thuc} {duong or '/'} trả {ma}: {than[:300].decode('utf-8', 'replace')}")
            return json.loads(than) if than else None
        return None

    # --- đọc ---

    def realm_rep(self) -> dict:
        return self.goi("")

    def hanh_dong(self) -> dict:
        return self.goi(f"/authentication/required-actions/{HANH_DONG}")

    def buoc_hoi_ma(self, luong: str) -> list[dict]:
        cac_buoc = self.goi(f"/authentication/flows/{urllib.parse.quote(luong)}/executions")
        return [b for b in cac_buoc if b.get("providerId") == BUOC_HOI_MA]

    def tai_khoan(self) -> list[dict]:
        """Mọi tài khoản đăng nhập được bằng trình duyệt — bỏ tài khoản dịch vụ của client."""
        ket_qua, dau = [], 0
        while True:
            trang = self.goi(f"/users?first={dau}&max={TRANG}&briefRepresentation=false")
            ket_qua += [u for u in trang if not u.get("serviceAccountClientId")]
            if len(trang) < TRANG:
                return ket_qua
            dau += TRANG

    def ma_da_thiet_lap(self, id_tk: str) -> list[dict]:
        return [c for c in self.goi(f"/users/{id_tk}/credentials") if c.get("type") == LOAI_MA]

    # --- ghi ---

    def dat_hanh_dong(self, mac_dinh: bool) -> bool:
        """Trả True nếu có đổi. Hành động luôn để BẬT: người dùng vẫn tự thiết lập mã được ở trang tài khoản."""
        hd = self.hanh_dong()
        if hd.get("enabled") and bool(hd.get("defaultAction")) == mac_dinh:
            return False
        self.goi(
            f"/authentication/required-actions/{HANH_DONG}",
            "PUT",
            {**hd, "enabled": True, "defaultAction": mac_dinh},
        )
        return True

    def dat_hanh_dong_tai_khoan(self, tk: dict, can: bool) -> bool:
        """Thêm hay gỡ CONFIGURE_TOTP ở một tài khoản. Gửi lại TRỌN bản ghi vừa đọc: Keycloak 24 trở đi có
        thể xóa thuộc tính hồ sơ không có trong bản gửi lên."""
        day_du = self.goi(f"/users/{tk['id']}")
        hien = list(day_du.get("requiredActions") or [])
        if (HANH_DONG in hien) == can:
            return False
        day_du["requiredActions"] = hien + [HANH_DONG] if can else [h for h in hien if h != HANH_DONG]
        self.goi(f"/users/{tk['id']}", "PUT", day_du)
        return True

    def xoa_ma(self, tk: dict, ma: dict) -> None:
        self.goi(f"/users/{tk['id']}/credentials/{ma['id']}", "DELETE")


# ---------------------------------------------------------------------------
# Lệnh
# ---------------------------------------------------------------------------


def phan_loai(kc: Keycloak) -> tuple[list[dict], list[dict], list[dict]]:
    """(đã có mã, đang chờ thiết lập, chưa có mã và không bị buộc). Mỗi tài khoản kèm danh sách mã."""
    co_ma, cho, tu_do = [], [], []
    for tk in kc.tai_khoan():
        tk["_ma"] = kc.ma_da_thiet_lap(tk["id"])
        if tk["_ma"]:
            co_ma.append(tk)
        elif HANH_DONG in (tk.get("requiredActions") or []):
            cho.append(tk)
        else:
            tu_do.append(tk)
    return co_ma, cho, tu_do


def ten_tk(cac_tk: list[dict]) -> str:
    return ", ".join(sorted(tk["username"] for tk in cac_tk))


def trang_thai(kc: Keycloak) -> int:
    r = kc.realm_rep()
    hd = kc.hanh_dong()
    co_ma, cho, tu_do = phan_loai(kc)
    mac_dinh = bool(hd.get("enabled") and hd.get("defaultAction"))

    if mac_dinh and not tu_do:
        tong = "BẬT"
    elif not mac_dinh and not cho:
        tong = "TẮT" if not co_ma else "TẮT (một số tài khoản vẫn giữ mã đã thiết lập, nên vẫn bị hỏi mã)"
    else:
        tong = "LỆCH — chạy lại `bat` hoặc `tat` để đưa về một trạng thái"

    luong = r.get("browserFlow") or "browser"
    buoc = kc.buoc_hoi_ma(luong)
    hoi_ma = [b for b in buoc if b.get("requirement") != "DISABLED"]

    print(f"Realm {kc.realm} tại {kc.goc}")
    print(f"Xác thực hai lớp: {tong}")
    print(f"  Hành động bắt buộc {HANH_DONG} (\"{hd.get('name')}\"): "
          f"{'đang bật' if hd.get('enabled') else 'đang TẮT'}, "
          f"mặc định cho tài khoản mới: {'có' if mac_dinh else 'không'}")
    if hoi_ma:
        print(f"  Luồng đăng nhập trình duyệt \"{luong}\": hỏi mã với tài khoản đã có mã "
              f"(bước {BUOC_HOI_MA}: {', '.join(b.get('requirement', '?') for b in hoi_ma)})")
    else:
        print(f"  CẢNH BÁO: luồng đăng nhập trình duyệt \"{luong}\" không có bước {BUOC_HOI_MA} nào đang bật — "
              "tài khoản có mã cũng sẽ không bị hỏi mã. Kiểm luồng trong trang quản trị Keycloak.")
    print(f"  Chính sách mã: {r.get('otpPolicyType', '?').upper()}, {r.get('otpPolicyAlgorithm', '?')}, "
          f"{r.get('otpPolicyDigits', '?')} chữ số, đổi mỗi {r.get('otpPolicyPeriod', '?')} giây")
    tong_so = len(co_ma) + len(cho) + len(tu_do)
    print(f"Tài khoản ({tong_so}):")
    print(f"  đã thiết lập mã:                    {len(co_ma)}" + (f"  ({ten_tk(co_ma)})" if co_ma else ""))
    print(f"  phải thiết lập ở lần đăng nhập kế:  {len(cho)}")
    print(f"  chưa có mã, không bị buộc:          {len(tu_do)}")
    in_chong_do(r)
    return 0


def in_chong_do(r: dict) -> None:
    mau = mac_dinh_bao_mat()
    lech = sorted(k for k, v in mau.items() if r.get(k) != v)
    if r.get("bruteForceProtected"):
        print(f"Chống dò mật khẩu: BẬT — khóa tạm sau {r.get('failureFactor')} lần sai, mỗi lần chờ thêm "
              f"{r.get('waitIncrementSeconds')} giây, tối đa {r.get('maxFailureWaitSeconds')} giây"
              + (", khóa vĩnh viễn" if r.get("permanentLockout") else ", tự mở"))
    else:
        print("Chống dò mật khẩu: TẮT")
    print(f"Chính sách mật khẩu: {r.get('passwordPolicy') or 'không có'}")
    print("  Khớp mặc định của realm mẫu." if not lech
          else f"  LỆCH realm mẫu ở {', '.join(lech)} — chạy `chong-do` để áp.")


def chong_do(kc: Keycloak) -> int:
    """Áp các khóa của realm mẫu lên realm đang chạy. Gửi TRỌN bản ghi realm vừa đọc với các khóa đã sửa."""
    r = kc.realm_rep()
    mau = mac_dinh_bao_mat()
    doi = {k: v for k, v in mau.items() if r.get(k) != v}
    if doi:
        kc.goi("", "PUT", {**r, **doi})
        print(f"Đã áp: {', '.join(f'{k}={v}' for k, v in doi.items())}")
    else:
        print("Realm đã khớp mặc định bảo mật của realm mẫu, không đổi gì.")
    in_chong_do(kc.realm_rep())
    print("Xong. Mật khẩu đã đặt trước khi có chính sách vẫn dùng được; chính sách áp ở lần đặt hay đổi mật khẩu kế.")
    return 0


def bat(kc: Keycloak) -> int:
    luong = kc.realm_rep().get("browserFlow") or "browser"
    if not [b for b in kc.buoc_hoi_ma(luong) if b.get("requirement") != "DISABLED"]:
        sys.exit(f"Luồng đăng nhập trình duyệt \"{luong}\" không có bước {BUOC_HOI_MA} đang bật: bật xác thực hai "
                 "lớp lúc này sẽ bắt người dùng thiết lập mã mà không bao giờ hỏi mã. Không đổi gì.")
    doi = kc.dat_hanh_dong(True)
    print(f"{'Đã đặt' if doi else 'Đã sẵn'}: tài khoản mới phải thiết lập mã ở lần đăng nhập đầu.")
    co_ma, cho, tu_do = phan_loai(kc)
    for tk in tu_do:
        kc.dat_hanh_dong_tai_khoan(tk, True)
    print(f"Gán thiết lập mã cho {len(tu_do)} tài khoản chưa có mã"
          + (f" ({ten_tk(tu_do)})" if tu_do else "") + ".")
    print(f"Giữ nguyên {len(co_ma)} tài khoản đã có mã, {len(cho)} tài khoản đã chờ thiết lập từ trước.")
    print("Xong. Lần đăng nhập kế, người dùng quét mã QR bằng ứng dụng xác thực (FreeOTP, Google Authenticator…).")
    return 0


def tat(kc: Keycloak, xoa: bool) -> int:
    doi = kc.dat_hanh_dong(False)
    print(f"{'Đã bỏ' if doi else 'Đã bỏ từ trước'}: tài khoản mới không còn phải thiết lập mã.")
    co_ma, cho, tu_do = phan_loai(kc)
    # Tài khoản đã có mã cũng có thể còn treo hành động (quản trị viên gán tay), nên duyệt cả ba nhóm
    so_go = sum(kc.dat_hanh_dong_tai_khoan(tk, False) for tk in co_ma + cho + tu_do
                if HANH_DONG in (tk.get("requiredActions") or []))
    print(f"Gỡ yêu cầu thiết lập mã còn treo ở {so_go} tài khoản.")
    if xoa:
        so_ma = 0
        for tk in co_ma:
            for ma in tk["_ma"]:
                kc.xoa_ma(tk, ma)
                so_ma += 1
        print(f"Xóa {so_ma} mã đã thiết lập của {len(co_ma)} tài khoản"
              + (f" ({ten_tk(co_ma)})" if co_ma else "") + ": họ đăng nhập lại chỉ bằng mật khẩu.")
    elif co_ma:
        print(f"Còn {len(co_ma)} tài khoản đã thiết lập mã ({ten_tk(co_ma)}): họ VẪN bị hỏi mã khi đăng nhập. "
              "Thêm --xoa-ma để xóa, hoặc để từng người tự gỡ ở trang tài khoản.")
    print("Xong.")
    return 0


def main() -> int:
    # Bảng điều khiển Windows mặc định không phải UTF-8
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(
        description="Bật, tắt, xem xác thực hai lớp (TOTP) cho mọi tài khoản của realm; áp chống dò mật khẩu."
    )
    p.add_argument("lenh", choices=("bat", "tat", "trang-thai", "chong-do"))
    p.add_argument("--xoa-ma", action="store_true", help="với tat: xóa luôn mã đã thiết lập của mọi tài khoản")
    p.add_argument("--env-file", type=Path, default=Path("infra/.env"), help="tệp env của cụm (mặc định infra/.env)")
    p.add_argument("--keycloak", help="địa chỉ Keycloak, mặc định http://localhost:<KEYCLOAK_PORT>")
    p.add_argument("--realm", help="realm, mặc định KEYCLOAK_REALM")
    ts = p.parse_args()
    if ts.xoa_ma and ts.lenh != "tat":
        p.error("--xoa-ma chỉ dùng với lệnh tat")

    kc = Keycloak(cau_hinh(ts))
    if ts.lenh == "bat":
        return bat(kc)
    if ts.lenh == "tat":
        return tat(kc, ts.xoa_ma)
    if ts.lenh == "chong-do":
        return chong_do(kc)
    return trang_thai(kc)


if __name__ == "__main__":
    sys.exit(main())
