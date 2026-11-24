# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Đo chất lượng gợi ý hồ sơ đã giải quyết tương tự (#319): recall@3 và MRR trên bộ 40 câu.
#
#     python scripts/do_ho_so_tuong_tu.py                          # cụm mặc định, container dxlab-backend
#     python scripts/do_ho_so_tuong_tu.py --container kt84-backend
#     python scripts/do_ho_so_tuong_tu.py --json ket-qua.json      # ghi thêm kết quả thô
#
# Cần: cụm chạy hồ sơ `tri-tue` có mô hình nhúng (DXLAB_EMBEDDING_URL đã đặt), đã nạp dữ liệu trình
# diễn (scripts/nap_du_lieu_trinh_dien.py — nó gắn 60 hồ sơ của scripts/du_lieu/ho_so_da_giai_quyet.json,
# đúng tiêu đề của mục)
# và bộ lập chỉ mục `similar-index` đã chạy xong (script chờ chỉ mục đủ trước khi đo).
#
# Mỗi câu chạy qua ĐÚNG đường gọi của biểu mẫu — `app.intelligence.tuong_tu.tim` bên trong container
# dịch vụ ứng dụng: lời dặn tác vụ, hạn chót, câu SQL quét pgvector như lúc chạy thật. Đo hai cách:
#
#   - XẾP HẠNG: lấy 10 hồ sơ gần nhất, không ngưỡng. recall@3 = tỷ lệ câu có hồ sơ đúng trong 3 đầu;
#     MRR = trung bình 1/hạng của hồ sơ đúng (không có trong 10 thì 0). Đo chất lượng của mô hình nhúng.
#   - NHƯ NGƯỜI GỬI THẤY: đúng cấu hình đang chạy (số gợi ý, ngưỡng độ tương đồng). Tỷ lệ câu thấy hồ
#     sơ đúng trong khối gợi ý, và số câu không hiện gì.
#
# Bộ đo do nhóm soạn bằng công cụ, navigator không duyệt — ghi rõ khi trích số. Script chỉ đọc: không
# ghi lượt xem nào (không gửi mã phiên soạn). Không thêm gói nào: thư viện chuẩn và lệnh `docker`.

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
BO_DO = GOC / "backend" / "tests" / "du_lieu" / "bo_do_tuong_tu.json"
HO_SO = GOC / "scripts" / "du_lieu" / "ho_so_da_giai_quyet.json"
SO_XEP_HANG = 10

# Chạy trong container dịch vụ ứng dụng: đọc {cau, tieu_de, cho_giay} từ stdin, in một dòng JSON mỗi câu
MA_TRONG_CONTAINER = r"""
import json, sys, time
from sqlalchemy import text
from app.config import get_settings
from app.db import SessionLocal
from app.intelligence import mo_hinh, tuong_tu

vao = json.load(sys.stdin)
ch = get_settings()
can = set(vao["tieu_de"])
het = time.monotonic() + vao["cho_giay"]
while True:
    with SessionLocal() as s:
        co = set(s.execute(text("SELECT title FROM similar_case_index WHERE model = :m"),
                           {"m": ch.embedding_model}).scalars())
    if can <= co or time.monotonic() > het:
        break
    time.sleep(5)
print(json.dumps({"model": ch.embedding_model, "url": ch.embedding_url, "enabled": ch.embedding_enabled,
                  "k": ch.similar_max_results, "min_score": ch.similar_min_score,
                  "timeout": ch.similar_timeout_seconds, "da_lap": len(can & co), "can_lap": len(can),
                  "tong_chi_muc": len(co)}, ensure_ascii=False), flush=True)
for c in vao["cau"]:
    dong = {"so": c["so"]}
    with SessionLocal() as s:
        bat_dau = time.monotonic()
        try:
            xh = tuong_tu.tim(s, c["tieu_de"], c["mo_ta"], so_ket_qua=vao["so_xep_hang"], nguong=-1.0)
            dong["xep_hang"] = [[k.title, round(k.score, 4)] for k in xh]
            dong["giay"] = round(time.monotonic() - bat_dau, 3)
            that = tuong_tu.tim(s, c["tieu_de"], c["mo_ta"])
            dong["hien"] = [k.title for k in that]
            dong["ok"] = True
        except mo_hinh.LoiMoHinh as loi:
            dong.update(ok=False, error=loi.ma, giay=round(time.monotonic() - bat_dau, 3))
    print(json.dumps(dong, ensure_ascii=False), flush=True)
"""


def main() -> None:
    for luong in (sys.stdout, sys.stderr):
        luong.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Đo recall@3 và MRR của gợi ý hồ sơ tương tự.")
    p.add_argument("--container", default="dxlab-backend", help="container dịch vụ ứng dụng")
    p.add_argument("--bo-do", type=Path, default=BO_DO)
    p.add_argument("--cho-giay", type=int, default=600, help="chờ bộ lập chỉ mục tối đa chừng này giây")
    p.add_argument("--json", type=Path, help="ghi kết quả thô từng câu ra tệp này")
    doi = p.parse_args()

    bo_do = json.loads(doi.bo_do.read_text(encoding="utf-8"))["cau"]
    # Kịch bản nạp giữ nguyên tiêu đề của mục (#541, không tiền tố), và tiêu đề hồ sơ mẫu khác không trùng chúng
    ho_so = {h["ma"]: h["tieu_de"] for h in json.loads(HO_SO.read_text(encoding="utf-8"))["ho_so"]}
    vao = {"cau": bo_do, "tieu_de": sorted(ho_so.values()), "cho_giay": doi.cho_giay,
           "so_xep_hang": SO_XEP_HANG}
    try:
        kq = subprocess.run(
            ["docker", "exec", "-i", doi.container, "python", "-c", MA_TRONG_CONTAINER],
            input=json.dumps(vao, ensure_ascii=False), capture_output=True, text=True, encoding="utf-8",
            check=False,
        )
    except FileNotFoundError:
        sys.exit("Không tìm thấy lệnh `docker`.")
    if kq.returncode != 0:
        sys.exit(f"Chạy trong container {doi.container} thất bại:\n{kq.stderr[-2000:]}")
    dong = [json.loads(d) for d in kq.stdout.splitlines() if d.strip().startswith("{")]
    tt, ket_qua = dong[0], dong[1:]
    if not tt["enabled"]:
        sys.exit("Dịch vụ ứng dụng chưa bật mô hình nhúng (DXLAB_EMBEDDING_URL rỗng) — xem README.")

    tong = len(ket_qua)
    trung3 = trung_hien = khong_hien = 0
    rr = 0.0
    loi = [k for k in ket_qua if not k["ok"]]
    for k in ket_qua:
        dung = ho_so[next(c["dung"] for c in bo_do if c["so"] == k["so"])]
        if not k["ok"]:
            continue
        ten = [t for t, _ in k["xep_hang"]]
        hang = ten.index(dung) + 1 if dung in ten else None
        k["hang"] = hang
        if hang and hang <= 3:
            trung3 += 1
        if hang:
            rr += 1 / hang
        trung_hien += dung in k["hien"]
        khong_hien += not k["hien"]
    giay = sorted(k["giay"] for k in ket_qua)

    print(f"Mô hình nhúng: {tt['model']} · chỉ mục {tt['tong_chi_muc']} hồ sơ, đủ "
          f"{tt['da_lap']}/{tt['can_lap']} hồ sơ của bộ đo · {tong} câu (bộ đo do nhóm soạn, chưa duyệt)")
    if tt["da_lap"] < tt["can_lap"]:
        print("Lưu ý: chỉ mục chưa đủ hồ sơ của bộ đo — kết quả thấp hơn thực tế.")
    if loi:
        print(f"Không nhúng được {len(loi)} câu: {sorted({k['error'] for k in loi})}")
    print(f"Xếp hạng (không ngưỡng): recall@3 = {trung3}/{tong} = {100 * trung3 / tong:.1f} % · "
          f"MRR@{SO_XEP_HANG} = {rr / tong:.3f}")
    print(f"Như người gửi thấy (tối đa {tt['k']} gợi ý, ngưỡng {tt['min_score']}): thấy hồ sơ đúng "
          f"{trung_hien}/{tong} = {100 * trung_hien / tong:.1f} % · không hiện gì {khong_hien} câu")
    print(f"Thời gian một lần tìm (nhúng + quét): trung vị {giay[len(giay) // 2]:.3f} giây, "
          f"dài nhất {giay[-1]:.3f} giây (hạn chót biểu mẫu {tt['timeout']} giây)")
    for k in ket_qua:
        if k.get("ok") and (k["hang"] is None or k["hang"] > 3):
            dau = k["xep_hang"][0] if k["xep_hang"] else ["—", 0]
            print(f"    câu {k['so']}: hồ sơ đúng ở hạng {k['hang'] or '>' + str(SO_XEP_HANG)}, "
                  f"đứng đầu là {dau[0]!r} ({dau[1]})")

    if doi.json:
        doi.json.write_text(json.dumps({"thong_tin": tt, "ket_qua": ket_qua}, ensure_ascii=False, indent=2),
                            encoding="utf-8")


if __name__ == "__main__":
    main()
