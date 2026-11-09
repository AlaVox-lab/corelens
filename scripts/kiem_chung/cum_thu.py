# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Dựng, hỏi trạng thái và gỡ CỤM THỬ CÁCH LY (#249): một bản cụm đầy đủ chạy cạnh cụm đang dùng, với
# tên container, nhãn ảnh, tên dự án Compose và cổng đều riêng, nên không đụng tới cụm kia.
#
# Ở gốc kho mã:
#
#     python -m scripts.kiem_chung.cum_thu dung                 # dựng, chờ sẵn sàng, in địa chỉ
#     python -m scripts.kiem_chung.cum_thu dung --khong-superset  # nhẹ máy hơn, bỏ Superset
#     python -m scripts.kiem_chung.cum_thu trang-thai
#     python -m scripts.kiem_chung.cum_thu go --xoa-anh         # xóa dữ liệu và ảnh của CỤM THỬ
#
# Cổng mặc định = cổng trong infra/.env.example cộng 20000 (cổng người dùng 23000, Keycloak 28080…).
# Chỉ cần Python 3.10 trở lên và lệnh `docker`.
from __future__ import annotations

import argparse
import socket
import sys
import time
import urllib.parse

from .chung import (
    CumThu,
    chay,
    chay_truc_tiep,
    cho_container,
    docker,
    dung_utf8,
    http_lay,
    keycloak_goi,
    keycloak_token_quan_tri,
    them_tham_so_cum,
    thoat,
    trang_thai_suc_khoe,
    GOC_KHO,
)

DICH_VU_KHONG_SUPERSET = ("postgres", "keycloak", "seaweedfs", "backend", "frontend")


def cong_dang_dung(cong: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", cong)) == 0


def cum_dang_chay(cum: CumThu) -> bool:
    kq = chay([docker(), "ps", "-q", "--filter", f"label=com.docker.compose.project={cum.du_an}"])
    return bool(kq.dau_ra.strip())


def them_chuyen_huong_cong(cum: CumThu, env: dict[str, str]) -> bool:
    """Thêm địa chỉ cổng của cụm thử vào client của cổng người dùng trong Keycloak.

    Realm nạp từ infra/keycloak chỉ biết cổng của cụm chính; cổng của cụm thử không nằm trong danh
    sách chuyển hướng hợp lệ, nên đăng nhập sẽ bị Keycloak từ chối cho tới khi thêm. Làm qua Admin
    API chứ không sửa tệp realm — tệp đó là dữ liệu của cụm chính. Chạy lại nhiều lần vẫn an toàn.
    Trả True khi đã sửa gì đó.
    """
    goc = f"http://localhost:{env['KEYCLOAK_PORT']}"
    cong = f"http://localhost:{env['FRONTEND_PORT']}"
    token = keycloak_token_quan_tri(goc, env["KEYCLOAK_ADMIN_USER"], env["KEYCLOAK_ADMIN_PASSWORD"])
    r = f"{goc}/admin/realms/{env['KEYCLOAK_REALM']}"
    client_id = urllib.parse.quote(env["KEYCLOAK_PORTAL_CLIENT_ID"])
    tim = keycloak_goi(f"{r}/clients?clientId={client_id}", token=token)
    if not tim:
        thoat(f"Keycloak không có client {env['KEYCLOAK_PORTAL_CLIENT_ID']!r}.")
    day_du = keycloak_goi(f"{r}/clients/{tim[0]['id']}", token=token)

    doi = False
    if f"{cong}/*" not in day_du["redirectUris"]:
        day_du["redirectUris"].append(f"{cong}/*")
        doi = True
    if cong not in day_du.get("webOrigins", []):
        day_du.setdefault("webOrigins", []).append(cong)
        doi = True
    thuoc_tinh = day_du.setdefault("attributes", {})
    sau_dang_xuat = thuoc_tinh.get("post.logout.redirect.uris", "")
    if f"{cong}/*" not in sau_dang_xuat.split("##"):
        thuoc_tinh["post.logout.redirect.uris"] = "##".join(filter(None, [sau_dang_xuat, f"{cong}/*"]))
        doi = True
    if doi:
        keycloak_goi(f"{r}/clients/{tim[0]['id']}", token=token, phuong_thuc="PUT", json_body=day_du)
    return doi


def cho_keycloak(env: dict[str, str], toi_da_giay: int) -> bool:
    url = f"http://localhost:{env['KEYCLOAK_PORT']}/realms/{env['KEYCLOAK_REALM']}/.well-known/openid-configuration"
    han = time.monotonic() + toi_da_giay
    while time.monotonic() < han:
        if http_lay(url) == 200:
            return True
        time.sleep(3)
    return False


def lenh_dung(ts: argparse.Namespace) -> int:
    cum = CumThu.tu_tham_so(ts)
    if cum_dang_chay(cum):
        print(f"Cụm thử {cum.du_an!r} đã có container đang chạy — dựng bồi thêm (không xóa gì).")
    else:
        e = cum.sinh_env()
        bi_chiem = [(k, int(e[k])) for k in ("POSTGRES_PORT", "KEYCLOAK_PORT", "SEAWEEDFS_S3_PORT",
                                              "SUPERSET_PORT", "BACKEND_PORT", "FRONTEND_PORT")
                    if cong_dang_dung(int(e[k]))]
        if bi_chiem:
            thoat("Cổng đã có tiến trình khác dùng: "
                  + ", ".join(f"{k}={v}" for k, v in bi_chiem)
                  + ". Dừng cụm đang giữ cổng đó, hoặc đổi --dich-cong.")
    env = cum.sinh_env()

    dich_vu = list(DICH_VU_KHONG_SUPERSET) if ts.khong_superset else []
    lenh = cum.lenh_compose("up", "-d", "--build", *dich_vu)
    print("Dựng cụm thử bằng một lệnh:")
    print("  " + " ".join(lenh))
    if chay_truc_tiep(lenh, cwd=GOC_KHO) != 0:
        thoat("Dựng cụm thử thất bại. Xem nhật ký ở trên.")

    backend = cum.container("backend")
    print(f"\nChờ dịch vụ ứng dụng ({backend}) khỏe — lần đầu có thể mất vài phút…")
    if not cho_container(backend, "healthy", ts.cho):
        thoat(f"{backend} không báo khỏe sau {ts.cho} giây (đang ở {trang_thai_suc_khoe(backend)}). "
              f"Xem nhật ký: docker logs {backend}")

    print("Chờ Keycloak nạp xong realm…")
    if not cho_keycloak(env, ts.cho):
        thoat(f"Keycloak chưa trả tài liệu discovery sau {ts.cho} giây. Xem: docker logs {cum.container('keycloak')}")

    print("Thêm địa chỉ chuyển hướng của cổng thử vào client đăng nhập…")
    doi = them_chuyen_huong_cong(cum, env)
    print("  đã thêm" if doi else "  đã có sẵn")

    cong_url = f"http://localhost:{env['FRONTEND_PORT']}/"
    han = time.monotonic() + ts.cho
    while time.monotonic() < han and http_lay(cong_url) is None:
        time.sleep(2)
    if http_lay(cong_url) is None:
        thoat(f"Cổng người dùng chưa trả lời ở {cong_url}. Xem: docker logs {cum.container('frontend')}")

    cum.in_dia_chi(co_superset=not ts.khong_superset)
    print("\nTài khoản mẫu và mật khẩu mẫu: xem README. Gỡ cụm thử khi xong:")
    print(f"  python -m scripts.kiem_chung.cum_thu go --xoa-anh")
    return 0


def lenh_go(ts: argparse.Namespace) -> int:
    cum = CumThu.tu_tham_so(ts)
    cum.sinh_env()  # Compose cần biến để đọc tệp ghi đè, kể cả khi chỉ để gỡ
    lenh = cum.lenh_compose("down", "-v", "--remove-orphans")
    print("SẮP XÓA DỮ LIỆU CỦA CỤM THỬ (volume của dự án Compose "
          f"{cum.du_an!r}), không đụng cụm nào khác:")
    print("  " + " ".join(lenh))
    if chay_truc_tiep(lenh, cwd=GOC_KHO) != 0:
        thoat("Gỡ cụm thử thất bại. Xem thông báo ở trên.")

    if ts.xoa_anh:
        print("\nXóa các ảnh mang nhãn riêng của cụm thử, theo đúng tên:")
        for ten in cum.ten_cac_anh:
            kq = chay([docker(), "rmi", ten])
            if kq.ma == 0:
                print(f"  đã xóa {ten}")
            elif "No such image" in kq.loi or "No such image" in kq.dau_ra:
                print(f"  không có {ten}")
            else:
                print(f"  KHÔNG xóa được {ten}: {kq.loi.strip()}")
    else:
        print("\nẢnh dựng cho cụm thử vẫn còn (để lần dựng sau nhanh hơn). Xóa kèm cờ --xoa-anh.")

    try:
        cum.tep_env.unlink()
    except FileNotFoundError:
        pass
    print("\nĐã gỡ cụm thử.")
    return 0


def lenh_trang_thai(ts: argparse.Namespace) -> int:
    cum = CumThu.tu_tham_so(ts)
    kq = chay([docker(), "ps", "-a", "--filter", f"label=com.docker.compose.project={cum.du_an}",
               "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"])
    if kq.ma != 0:
        thoat(f"Không hỏi được docker: {kq.loi.strip()}")
    dong = [d for d in kq.dau_ra.splitlines() if d.strip()]
    if not dong:
        print(f"Không có cụm thử {cum.du_an!r}. Dựng bằng: python -m scripts.kiem_chung.cum_thu dung")
        return 1
    print(f"Cụm thử {cum.du_an!r}:")
    for d in dong:
        ten, trang_thai, cong = (d.split("\t") + ["", ""])[:3]
        print(f"  {ten:<22} {trang_thai:<28} {cong}")
    if cum.tep_env.is_file():
        e = cum.env()
        cong_url = f"http://localhost:{e['FRONTEND_PORT']}/"
        dap = http_lay(cong_url)
        print(f"\nCổng người dùng {cong_url}: " + (f"đáp (HTTP {dap})" if dap else "không đáp"))
        cum.in_dia_chi(co_superset=trang_thai_suc_khoe(cum.container("superset")) != "khong-co")
    return 0


def main() -> int:
    dung_utf8()
    p = argparse.ArgumentParser(
        prog="python -m scripts.kiem_chung.cum_thu",
        description="Dựng, hỏi trạng thái và gỡ cụm thử cách ly.")
    con = p.add_subparsers(dest="lenh", required=True)

    d = con.add_parser("dung", help="Dựng cụm thử bằng một lệnh, chờ sẵn sàng, in địa chỉ")
    d.add_argument("--khong-superset", action="store_true", help="Bỏ Superset cho nhẹ máy")
    d.add_argument("--cho", type=int, default=900, help="Số giây tối đa chờ mỗi dịch vụ sẵn sàng (mặc định 900)")
    them_tham_so_cum(d)
    d.set_defaults(ham=lenh_dung)

    g = con.add_parser("go", help="Gỡ cụm thử: xóa container và dữ liệu của đúng dự án Compose đó")
    g.add_argument("--xoa-anh", action="store_true",
                   help="Xóa luôn ba ảnh mang nhãn riêng của cụm thử (theo đúng tên)")
    them_tham_so_cum(g)
    g.set_defaults(ham=lenh_go)

    t = con.add_parser("trang-thai", help="Cụm thử đang chạy hay không, ở địa chỉ nào")
    them_tham_so_cum(t)
    t.set_defaults(ham=lenh_trang_thai)

    ts = p.parse_args()
    return ts.ham(ts)


if __name__ == "__main__":
    sys.exit(main())
