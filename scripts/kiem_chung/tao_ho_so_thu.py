# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Tạo HỒ SƠ THỬ nằm ở từng trạng thái của bộ quy tắc đang bật (#249), để có sẵn dữ liệu mà kiểm
# từng màn hình hay từng ràng buộc, thay vì ngồi bấm tay cả quy trình.
#
#     python -m scripts.kiem_chung.tao_ho_so_thu --moi-trang-thai        # mỗi trạng thái một hồ sơ
#     python -m scripts.kiem_chung.tao_ho_so_thu --trang-thai <mã>       # chỉ trạng thái đó
#
# Mọi hồ sơ đi qua engine (`create_case` rồi `perform_transition`) chạy trong container dịch vụ ứng
# dụng của cụm thử — không INSERT thẳng vào bảng hồ sơ hay nhật ký — nên mỗi hồ sơ có đủ nhật ký sự
# kiện và mọi ràng buộc Poka-yoke đã chạy. Trạng thái nào engine không cho tới được thì được báo rõ
# là không tạo được, kèm lời từ chối của engine; công cụ không giả lập.
#
# Việc tìm đường và dựng tác nhân nằm ở tao_ho_so_trong_cum.py (chạy trong container). Hồ sơ mang
# tiền tố tiêu đề `[Thử]`; cụm đã có hồ sơ không mang tiền tố đó thì công cụ dừng, trừ khi --cho-tron.
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse

from .chung import (
    GOC_KHO,
    CumThu,
    chay,
    docker,
    dung_utf8,
    keycloak_goi,
    keycloak_token_quan_tri,
    them_tham_so_cum,
    thoat,
    trang_thai_suc_khoe,
)

TEP_TRONG_CUM = GOC_KHO / "scripts" / "kiem_chung" / "tao_ho_so_trong_cum.py"
DICH_TRONG_CUM = "/tmp/tao_ho_so_trong_cum.py"
DAU_KET_QUA = "KET_QUA_JSON "
MA_NGUOI_GUI_DU_PHONG = "nguoi-gui-thu"


def tra_nguoi_gui(cum: CumThu, ten_dang_nhap: str) -> tuple[str, str]:
    """(mã định danh `sub`, tên hiển thị) của tài khoản mẫu, hỏi Admin API của Keycloak trong cụm thử.

    Dùng định danh thật để người gửi đăng nhập vào cổng thì thấy hồ sơ trong danh sách của mình."""
    e = cum.env()
    goc = f"http://localhost:{e['KEYCLOAK_PORT']}"
    try:
        token = keycloak_token_quan_tri(goc, e["KEYCLOAK_ADMIN_USER"], e["KEYCLOAK_ADMIN_PASSWORD"])
        tim = keycloak_goi(
            f"{goc}/admin/realms/{e['KEYCLOAK_REALM']}/users?username={urllib.parse.quote(ten_dang_nhap)}&exact=true",
            token=token,
        )
    except Exception as loi:  # noqa: BLE001
        print(f"CẢNH BÁO: không hỏi được Keycloak ({loi}); dùng mã người gửi dự phòng "
              f"{MA_NGUOI_GUI_DU_PHONG!r} — hồ sơ sẽ không hiện trong cổng của {ten_dang_nhap}.", file=sys.stderr)
        return MA_NGUOI_GUI_DU_PHONG, "Người gửi thử"
    if not tim:
        print(f"CẢNH BÁO: Keycloak không có tài khoản {ten_dang_nhap!r}; dùng mã người gửi dự phòng.",
              file=sys.stderr)
        return MA_NGUOI_GUI_DU_PHONG, "Người gửi thử"
    nguoi = tim[0]
    ten = " ".join(filter(None, [nguoi.get("lastName"), nguoi.get("firstName")])) or ten_dang_nhap
    return nguoi["id"], ten


def main() -> int:
    dung_utf8()
    p = argparse.ArgumentParser(
        prog="python -m scripts.kiem_chung.tao_ho_so_thu",
        description="Tạo hồ sơ thử ở từng trạng thái của bộ quy tắc đang bật, qua engine.")
    nhom = p.add_mutually_exclusive_group(required=True)
    nhom.add_argument("--trang-thai", action="append", metavar="MÃ",
                      help="Mã trạng thái đích (nhiều lần, hay cách nhau bằng dấu phẩy)")
    nhom.add_argument("--moi-trang-thai", action="store_true",
                      help="Mỗi trạng thái của bộ quy tắc tới được một hồ sơ")
    p.add_argument("--loai", help="Mã loại yêu cầu (mặc định: loại đầu tiên đang dùng)")
    p.add_argument("--nguoi-gui", default="an.nguyen",
                   help="Tên đăng nhập của người gửi, tra định danh trong Keycloak (mặc định an.nguyen)")
    p.add_argument("--tien-to-tieu-de", default="[Thử]", help="Tiền tố tiêu đề hồ sơ thử (mặc định [Thử])")
    p.add_argument("--cho-tron", action="store_true",
                   help="Cho chạy cả khi cụm đã có hồ sơ không mang tiền tố — chỉ dùng khi chắc là cụm thử")
    p.add_argument("--container", help="Tên container dịch vụ ứng dụng (mặc định <tiền tố>backend của cụm thử)")
    them_tham_so_cum(p)
    ts = p.parse_args()

    cum = CumThu.tu_tham_so(ts)
    container = ts.container or cum.container("backend")
    if trang_thai_suc_khoe(container) not in ("healthy", "running"):
        thoat(f"Container {container} không chạy. Dựng cụm thử bằng: python -m scripts.kiem_chung.cum_thu dung")

    muc_tieu = None
    if ts.trang_thai:
        muc_tieu = [m.strip() for muc in ts.trang_thai for m in muc.split(",") if m.strip()]

    ma_gui, ten_gui = tra_nguoi_gui(cum, ts.nguoi_gui)
    yeu_cau = {
        "tien_to": ts.tien_to_tieu_de, "cho_tron": ts.cho_tron, "loai": ts.loai,
        "trang_thai": muc_tieu, "nguoi_gui": ma_gui, "nhan_nguoi_gui": ten_gui,
    }

    sao = chay([docker(), "cp", str(TEP_TRONG_CUM), f"{container}:{DICH_TRONG_CUM}"])
    if sao.ma != 0:
        thoat(f"Không chép được công cụ vào {container}: {sao.loi.strip()}")
    kq = chay([docker(), "exec", "-i", "-w", "/app", container, "python", "-X", "utf8", DICH_TRONG_CUM],
              vao=json.dumps(yeu_cau, ensure_ascii=False), cho_toi_da=600)
    dong = [d for d in kq.dau_ra.splitlines() if d.startswith(DAU_KET_QUA)]
    if kq.ma != 0 or not dong:
        print(kq.dau_ra, file=sys.stderr)
        thoat(f"Công cụ trong container thất bại (mã {kq.ma}):\n{kq.loi.strip()}")
    ket_qua = json.loads(dong[-1][len(DAU_KET_QUA):])

    if "loi" in ket_qua:
        thoat(ket_qua["loi"])
    if "chan" in ket_qua:
        thoat(f"Cụm có {ket_qua['chan']} hồ sơ không mang tiền tố {ts.tien_to_tieu_de!r} — có thể đây là hệ "
              "thống thật. Dừng. Chắc chắn là cụm thử thì chạy lại kèm --cho-tron.", 3)

    print(f"Bộ quy tắc đang bật: {ket_qua['bo_quy_tac']} · loại yêu cầu: {ket_qua['loai']} · "
          f"người gửi: {ten_gui}\n")
    dong_bang = ket_qua["ket_qua"]
    rong_ma = max(len(r["ma"]) for r in dong_bang)
    rong_nhan = max(len(r["nhan"]) for r in dong_bang)
    print(f"{'Mã trạng thái'.ljust(rong_ma)}  {'Trạng thái'.ljust(rong_nhan)}  Hồ sơ  Đường đi")
    for r in dong_bang:
        ma_ho_so = f"#{r['ho_so']}" if r["ho_so"] else "—"
        duong = " → ".join(r["buoc"]) if r["buoc"] else ("(trạng thái bắt đầu)" if r["ho_so"] else "")
        print(f"{r['ma'].ljust(rong_ma)}  {r['nhan'].ljust(rong_nhan)}  {ma_ho_so.ljust(5)}  {duong}")
    khong_duoc = [r for r in dong_bang if not r["ho_so"]]
    if khong_duoc:
        print("\nKHÔNG TẠO ĐƯỢC:")
        for r in khong_duoc:
            print(f"  {r['ma']} ({r['nhan']}): {r['ly_do']}")
    print(f"\nĐã tạo {len(dong_bang) - len(khong_duoc)}/{len(dong_bang)} hồ sơ.")
    # Chọn rõ vài trạng thái mà không tạo được là lỗi; quét cả bộ thì có trạng thái chỉ hệ thống tới được
    return 1 if (khong_duoc and muc_tieu) else 0


if __name__ == "__main__":
    sys.exit(main())
