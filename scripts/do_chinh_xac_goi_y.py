# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Đo độ chính xác gợi ý loại yêu cầu, mức ưu tiên, phòng ban của mô hình ngôn ngữ (#317).
#
#     python scripts/do_chinh_xac_goi_y.py                         # cụm mặc định, container dxlab-backend
#     python scripts/do_chinh_xac_goi_y.py --container kt84-backend
#     python scripts/do_chinh_xac_goi_y.py --json ket-qua.json     # ghi thêm kết quả thô
#
# Cần cụm đang chạy hồ sơ `tri-tue` (dịch vụ mô hình đã nạp xong) và LLM_URL đã đặt cho dịch vụ ứng
# dụng — xem README, mục "Mô hình ngôn ngữ". Bộ mẫu có nhãn ở backend/tests/du_lieu/bo_mau_phan_loai.json.
#
# Mỗi hồ sơ mẫu chạy qua ĐÚNG lớp mà hệ thống dùng — `app/intelligence/mo_hinh.py`, gọi bên trong
# container dịch vụ ứng dụng: danh mục đọc từ cơ sở dữ liệu của cụm, lược đồ ràng buộc, hạn chót như
# lúc chạy thật. Script chỉ đọc, không ghi gì vào cơ sở dữ liệu.
#
# In ra: độ chính xác từng loại gợi ý, ma trận nhầm gọn (chỉ các cặp nhầm), thời gian trung bình mỗi hồ
# sơ, và so gợi ý PHÒNG của mô hình với gợi ý theo bảng ánh xạ `request_type_routing` (theo loại người
# gửi chọn) — căn cứ cho cờ DXLAB_SUGGEST_DEPARTMENT_FROM_MODEL, chỉ khuyên bật khi mô hình đạt từ 80 %.
#
# Không thêm gói nào: thư viện chuẩn và lệnh `docker`.

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
BO_MAU = GOC / "backend" / "tests" / "du_lieu" / "bo_mau_phan_loai.json"
CAC_TRUONG = ("request_type_code", "priority_code", "department_code")
TEN_TRUONG = {
    "request_type_code": "Loại yêu cầu",
    "priority_code": "Mức ưu tiên",
    "department_code": "Phòng ban",
}
NGUONG_PHONG = 0.80

# Chạy trong container dịch vụ ứng dụng: đọc bộ mẫu từ stdin, in một dòng JSON cho mỗi hồ sơ
MA_TRONG_CONTAINER = r"""
import json, sys, time
from app.db import SessionLocal
from app.intelligence import mo_hinh
from app.intelligence.goi_y import goi_y_phong_theo_loai
from app.config import get_settings

mau = json.load(sys.stdin)
print(json.dumps({"model": get_settings().llm_model, "url": get_settings().llm_url,
                  "timeout": get_settings().llm_timeout_seconds}), flush=True)
for m in mau:
    with SessionLocal() as phien:
        de_bai = mo_hinh.dung_de_bai(phien, title=m["title"], description=m.get("description"),
                                     details=m.get("details"),
                                     request_type_code=m.get("loai_nguoi_gui_chon"))
        anh_xa = goi_y_phong_theo_loai(phien, m.get("loai_nguoi_gui_chon"))
    bat_dau = time.monotonic()
    dong = {"so": m["so"], "routing_department": anh_xa.code if anh_xa else None}
    try:
        kq = mo_hinh.hoi_phan_loai(de_bai)
        dong.update(ok=True, request_type_code=kq.request_type_code, priority_code=kq.priority_code,
                    department_code=kq.department_code, reasons=kq.reasons)
    except mo_hinh.LoiMoHinh as loi:
        dong.update(ok=False, error=loi.ma)
    dong["giay"] = round(time.monotonic() - bat_dau, 3)
    print(json.dumps(dong, ensure_ascii=False), flush=True)
"""


def chay(container: str, mau: list[dict]) -> tuple[dict, list[dict]]:
    lenh = ["docker", "exec", "-i", container, "python", "-c", MA_TRONG_CONTAINER]
    try:
        kq = subprocess.run(
            lenh,
            input=json.dumps(mau, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except FileNotFoundError:
        sys.exit("Không tìm thấy lệnh `docker`.")
    if kq.returncode != 0:
        sys.exit(f"Chạy trong container {container} thất bại:\n{kq.stderr[-2000:]}")
    dong = [json.loads(d) for d in kq.stdout.splitlines() if d.strip().startswith("{")]
    return dong[0], dong[1:]


def phan_tram(a: int, b: int) -> str:
    return f"{100 * a / b:.1f} %" if b else "—"


def main() -> None:
    p = argparse.ArgumentParser(description="Đo độ chính xác gợi ý của mô hình trên bộ mẫu có nhãn.")
    p.add_argument("--container", default="dxlab-backend", help="container dịch vụ ứng dụng")
    p.add_argument("--bo-mau", type=Path, default=BO_MAU)
    p.add_argument("--json", type=Path, help="ghi kết quả thô từng hồ sơ ra tệp này")
    doi = p.parse_args()

    du_lieu = json.loads(doi.bo_mau.read_text(encoding="utf-8"))
    mau = du_lieu["mau"]
    theo_so = {m["so"]: m for m in mau}
    thong_tin, ket_qua = chay(doi.container, mau)
    if not thong_tin.get("url"):
        sys.exit("Dịch vụ ứng dụng chưa bật mô hình (LLM_URL rỗng) — xem README.")

    co_tra_loi = [k for k in ket_qua if k["ok"]]
    loi = Counter(k["error"] for k in ket_qua if not k["ok"])
    tong = len(ket_qua)
    print(f"Mô hình: {thong_tin['model']} · hạn chót {thong_tin['timeout']} giây · {tong} hồ sơ mẫu")
    if not du_lieu.get("nhan_da_duyet"):
        print("Lưu ý: đo trên bộ mẫu CHƯA được navigator duyệt nhãn.")
    print(f"Có gợi ý: {len(co_tra_loi)}/{tong}" + (f" · không có gợi ý: {dict(loi)}" if loi else ""))
    print(f"Thời gian trung bình mỗi hồ sơ: {sum(k['giay'] for k in ket_qua) / max(tong, 1):.2f} giây"
          f" (dài nhất {max((k['giay'] for k in ket_qua), default=0):.2f} giây)")
    print()

    tom_tat: dict[str, float] = {}
    for truong in CAC_TRUONG:
        dung = sum(1 for k in co_tra_loi if k[truong] == theo_so[k["so"]]["nhan"][truong])
        # Mẫu số là toàn bộ bộ mẫu: hồ sơ không có gợi ý tính là sai
        tom_tat[truong] = dung / tong if tong else 0
        print(f"{TEN_TRUONG[truong]:<14} đúng {dung}/{tong} = {phan_tram(dung, tong)}")
        nham = Counter(
            (theo_so[k["so"]]["nhan"][truong], k[truong])
            for k in co_tra_loi
            if k[truong] != theo_so[k["so"]]["nhan"][truong]
        )
        for (dung_la, doan), so in nham.most_common():
            print(f"    nhầm {dung_la} → {doan}: {so}")

    dung_anh_xa = sum(
        1 for k in ket_qua if k["routing_department"] == theo_so[k["so"]]["nhan"]["department_code"]
    )
    tom_tat["routing_department"] = dung_anh_xa / tong if tong else 0
    print()
    print(f"Phòng ban theo bảng ánh xạ (loại người gửi chọn): đúng {dung_anh_xa}/{tong} = "
          f"{phan_tram(dung_anh_xa, tong)}")
    phong = tom_tat["department_code"]
    khuyen = "CÓ THỂ bật" if phong >= NGUONG_PHONG and phong > tom_tat["routing_department"] else "GIỮ TẮT"
    print(f"Cờ DXLAB_SUGGEST_DEPARTMENT_FROM_MODEL: {khuyen} "
          f"(mô hình {phong:.1%}, ngưỡng {NGUONG_PHONG:.0%}, bảng ánh xạ {tom_tat['routing_department']:.1%})")

    if doi.json:
        doi.json.write_text(
            json.dumps({"thong_tin": thong_tin, "tom_tat": tom_tat, "ket_qua": ket_qua},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
