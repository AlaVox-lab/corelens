# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Dò ĐĂNG NHẬP THẬT (#249): đi trọn luồng OIDC của cổng như một trình duyệt — bấm đăng nhập, điền
# biểu mẫu của Keycloak, quay về cổng — rồi mở các trang và kiểm chúng có chứa chuỗi mong đợi.
#
# Vì sao không tự đúc cookie phiên: lỗi đăng nhập #87 từng bị che đúng vì kiểm thử tự đúc cookie.
# Công cụ này chỉ đi bằng đúng những gì người dùng thật đi.
#
#     python -m scripts.kiem_chung.do_dang_nhap --tai-khoan an.nguyen --tim "Gửi yêu cầu"
#     python -m scripts.kiem_chung.do_dang_nhap --tai-khoan binh.tran \
#         --trang "dieu-phoi::Hàng đợi" --trang hop-thu
#
# Mã thoát: 0 đạt · 1 đăng nhập được nhưng một trang lỗi hay thiếu chuỗi · 2 không đăng nhập được.
# Chỉ dùng trên cụm thử, với tài khoản mẫu của realm dựng thử.
#
# Tự cầm cookie bằng tay thay vì dùng http.cookiejar: Keycloak gắn cờ Secure lên cookie phiên, và
# cookiejar của Python không gửi cookie Secure qua http:// — còn trình duyệt thì cho phép với
# localhost. Dùng cookiejar sẽ ra lỗi "Restart login cookie not found" giả.
from __future__ import annotations

import argparse
import html
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from .chung import MAT_KHAU_MAU, dung_utf8, thoat

CONG_MAC_DINH = "http://localhost:23000"  # cổng người dùng của cụm thử


class KhongTuTheo(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):  # noqa: ANN002, ANN003
        return None


class PhienDuyet:
    """Một "trình duyệt" tối giản: tự theo chuyển hướng, tự giữ cookie."""

    def __init__(self, in_chang: bool) -> None:
        self.may = urllib.request.build_opener(KhongTuTheo)
        self.cookie: dict[str, str] = {}  # mọi dịch vụ đều ở localhost, cookie không phân theo cổng
        self.in_chang = in_chang

    def goi(self, url: str, than: bytes | None = None):
        yc = urllib.request.Request(url, data=than)
        if self.cookie:
            yc.add_header("Cookie", "; ".join(f"{k}={v}" for k, v in self.cookie.items()))
        try:
            r = self.may.open(yc, timeout=30)
        except urllib.error.HTTPError as loi:
            r = loi
        for dong in r.headers.get_all("Set-Cookie") or []:
            ten, _, phan_con = dong.partition("=")
            gia_tri = phan_con.split(";", 1)[0]
            thuong = dong.lower()  # Next viết hoa "Expires=", Keycloak viết thường
            if "max-age=0" in thuong or "expires=thu, 01 jan 1970" in thuong:
                self.cookie.pop(ten.strip(), None)
            else:
                self.cookie[ten.strip()] = gia_tri
        return r

    def di_theo(self, url: str, than: bytes | None = None) -> tuple[int, str, str]:
        """Đi theo chuỗi chuyển hướng. Trả (mã trạng thái cuối, địa chỉ cuối, thân trang)."""
        for _ in range(12):
            r = self.goi(url, than)
            than = None
            if self.in_chang:
                print(f"    {r.status}  {url[:110]}")
            vi_tri = r.headers.get("Location")
            if r.status in (301, 302, 303, 307, 308) and vi_tri:
                url = urllib.parse.urljoin(url, vi_tri)
                continue
            return r.status, url, r.read().decode("utf-8", "replace")
        raise RuntimeError("chuyển hướng quá nhiều lần")


def chu_nhin_thay(noi_dung_html: str) -> str:
    """Phần chữ người dùng nhìn thấy: bỏ script, style, thẻ; giải mã ký tự đặc biệt."""
    bo_script = re.sub(r"<(script|style)\b.*?</\1>", " ", noi_dung_html, flags=re.S | re.I)
    bo_the = re.sub(r"<[^>]+>", " ", bo_script)
    return re.sub(r"\s+", " ", html.unescape(bo_the)).strip()


def dang_nhap(phien: PhienDuyet, cong: str, tai_khoan: str, mat_khau: str) -> tuple[str, str]:
    """Trả (chữ trang đích, địa chỉ trang đích). Ném RuntimeError kèm lý do khi không vào được."""
    print("  1. Bấm nút đăng nhập")
    ma, url, trang = phien.di_theo(f"{cong}/api/auth/login")
    m = re.search(r'<form[^>]*id="kc-form-login"[^>]*action="([^"]+)"', trang)
    if not m:
        raise RuntimeError(f"không thấy biểu mẫu đăng nhập của Keycloak (HTTP {ma}, dừng ở {url[:100]})")

    print(f"  2. Gửi tài khoản {tai_khoan}")
    ma, url, trang = phien.di_theo(
        html.unescape(m.group(1)),
        urllib.parse.urlencode({"username": tai_khoan, "password": mat_khau}).encode(),
    )
    if 'id="kc-form-login"' in trang:
        loi = re.search(r'id="input-error[^"]*"[^>]*>(.*?)</', trang, flags=re.S)
        ly_do = chu_nhin_thay(loi.group(1)) if loi else "Keycloak hiện lại biểu mẫu"
        raise RuntimeError(f"Keycloak từ chối đăng nhập: {ly_do}")
    if ma >= 400:
        raise RuntimeError(f"sau khi gửi tài khoản, cổng trả HTTP {ma} ở {url[:100]}")
    if not any(k.startswith("dxlab") for k in phien.cookie):
        raise RuntimeError("đăng nhập xong nhưng cổng không đặt cookie phiên (dxlab*)")
    print(f"     vào được: {url[:100]}")
    return chu_nhin_thay(trang), url


def tach_trang(mo_ta: str, tim_chung: list[str]) -> tuple[str, list[str]]:
    """`duong-dan` hay `duong-dan::chuoi1,chuoi2` — vế sau thay chuỗi chung của trang đó. Dấu `/` đầu
    có hay không đều được.

    Git Bash trên Windows tự đổi tham số mở đầu bằng `/` thành đường dẫn của nó (`/dieu-phoi` thành
    `C:/Program Files/Git/dieu-phoi`) trước khi chương trình nhận được, nên hướng dẫn viết không có
    `/` đầu. Gặp đường dẫn đã bị đổi kiểu đó thì báo cách sửa thay vì gửi một địa chỉ hỏng."""
    duong, _, rieng = mo_ta.partition("::")
    if re.match(r"^[A-Za-z]:[\\/]", duong):
        thoat(f"--trang {duong!r} trông như đường dẫn đã bị Git Bash đổi. Viết không có dấu / đầu "
              f"(ví dụ --trang dieu-phoi), hoặc đặt MSYS_NO_PATHCONV=1 trước lệnh.", 2)
    return "/" + duong.lstrip("/"), ([c for c in rieng.split(",") if c] if rieng else tim_chung)


def kiem_trang(ten: str, chu: str, tho: str, can_tim: list[str], dung_tho: bool, in_chu: int) -> int:
    """In kết quả kiểm một trang, trả số chuỗi còn thiếu."""
    thieu = 0
    for c in can_tim:
        co = c in (tho if dung_tho else chu)
        thieu += not co
        print(f"    {'CÓ   ' if co else 'THIẾU'}  {c!r}")
    if in_chu:
        print(f"    --- chữ trên trang (tối đa {in_chu} ký tự) ---")
        print("    " + chu[:in_chu])
    return thieu


def main() -> int:
    dung_utf8()
    p = argparse.ArgumentParser(
        prog="python -m scripts.kiem_chung.do_dang_nhap",
        description="Đăng nhập thật qua OIDC của cổng, mở trang, kiểm chuỗi mong đợi.")
    p.add_argument("--tai-khoan", required=True, help="Tên đăng nhập của tài khoản mẫu")
    p.add_argument("--mat-khau", default=os.environ.get("MAT_KHAU", MAT_KHAU_MAU),
                   help="Mật khẩu (mặc định: biến MAT_KHAU, rồi mật khẩu mẫu công khai trong README)")
    p.add_argument("--cong", default=os.environ.get("CONG", CONG_MAC_DINH),
                   help=f"Địa chỉ cổng người dùng (mặc định biến CONG, rồi {CONG_MAC_DINH})")
    p.add_argument("--trang", action="append", default=[],
                   help="Trang cần mở thêm, ví dụ yeu-cau (không cần dấu / đầu). Thêm '::a,b' sau đường dẫn để đòi riêng "
                        "chuỗi a và b trên trang đó. Dùng nhiều lần được")
    p.add_argument("--tim", default="",
                   help="Các chuỗi phải có trên mỗi trang (cách nhau bằng dấu phẩy), kể cả trang đích "
                        "ngay sau đăng nhập; trang có '::' riêng thì dùng chuỗi riêng")
    p.add_argument("--tho", action="store_true",
                   help="So chuỗi với HTML thô thay vì chữ nhìn thấy (bắt dữ liệu nhúng trong trang)")
    p.add_argument("--in-chu", type=int, default=0, metavar="N",
                   help="In N ký tự chữ đầu tiên của mỗi trang")
    p.add_argument("--im", action="store_true", help="Không in từng chặng chuyển hướng")
    ts = p.parse_args()

    cong = ts.cong.rstrip("/")
    tim_chung = [c for c in ts.tim.split(",") if c]
    phien = PhienDuyet(in_chang=not ts.im)

    print(f"Dò đăng nhập {ts.tai_khoan} ở {cong}")
    try:
        chu, url = dang_nhap(phien, cong, ts.tai_khoan, ts.mat_khau)
    except (RuntimeError, urllib.error.URLError, OSError) as loi:
        print(f"KHÔNG ĐĂNG NHẬP ĐƯỢC: {loi}", file=sys.stderr)
        return 2

    thieu = 0
    print(f"\nTrang đích sau đăng nhập ({urllib.parse.urlparse(url).path or '/'})")
    # Trang đích đã đọc rồi; HTML thô của nó chỉ cần khi so --tho, nên mở lại đúng địa chỉ đó
    r = phien.goi(url)
    tho = r.read().decode("utf-8", "replace")
    thieu += kiem_trang("đích", chu_nhin_thay(tho), tho, tim_chung, ts.tho, ts.in_chu)

    for mo_ta in ts.trang:
        duong, can_tim = tach_trang(mo_ta, tim_chung)
        print(f"\nTrang {duong}")
        r = phien.goi(cong + duong)
        tho = r.read().decode("utf-8", "replace")
        if r.status >= 400:
            print(f"    LỖI  HTTP {r.status}")
            thieu += 1
            continue
        if 'id="kc-form-login"' in tho:
            print("    LỖI  bị đẩy về trang đăng nhập — phiên không giữ được")
            thieu += 1
            continue
        print(f"    HTTP {r.status}")
        thieu += kiem_trang(duong, chu_nhin_thay(tho), tho, can_tim, ts.tho, ts.in_chu)

    print()
    if thieu:
        print(f"KHÔNG ĐẠT: {thieu} chuỗi thiếu hay trang lỗi.")
        return 1
    print("ĐẠT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
