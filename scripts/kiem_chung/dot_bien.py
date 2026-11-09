# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# PHÉP THỬ ĐỘT BIẾN (#249): cố ý làm hỏng mã nguồn một chỗ rồi chạy các bài kiểm thử đã khai. Bài
# kiểm thử tốt phải đỏ — đột biến BỊ BẮT. Nếu mọi bài vẫn xanh thì đột biến SỐNG: có một hành vi mà
# không bài nào canh, và bộ kiểm thử đang xanh giả ở chỗ đó.
#
#     python -m scripts.kiem_chung.dot_bien scripts/kiem_chung/vi_du/actor_not_requester.json
#
# Tệp mô tả (JSON, hoặc Python khai hai biến BAI và DOT_BIEN) gồm:
#   bai       — danh sách bài pytest, đường dẫn tính từ backend/ (vd. tests/test_x.py::test_y)
#   dot_bien  — danh sách đột biến: ten, tep (từ gốc kho, bắt đầu bằng backend/), goc, thay.
#               `goc` là đoạn chữ phải xuất hiện ĐÚNG MỘT LẦN trong tệp; `thay` là chữ thế vào.
#
# Mỗi đột biến: chép tệp đã đổi vào container dịch vụ ứng dụng của cụm thử, chạy pytest có giới hạn
# giờ, rồi LUÔN trả tệp gốc (kể cả khi lỗi hay bị ngắt). Bài chạy quá giờ thì khởi động lại container
# — đột biến bỏ khóa có thể làm bài treo — và tính là bắt được. Tệp trong kho không bao giờ bị sửa.
#
# Mã thoát: 0 khi mọi đột biến bị bắt và container đã trả lại nguyên vẹn; 1 khi còn đột biến sống,
# mô tả sai, hay không trả lại được tệp gốc; 2 khi bộ bài gốc không xanh (không có gì để so).
from __future__ import annotations

import argparse
import hashlib
import json
import runpy
import signal
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .chung import GOC_KHO, TIEN_TO_MAC_DINH, chay, cho_container, docker, dung_utf8, thoat

TIEN_TO_TEP = "backend/"
THU_MUC_UNG_DUNG = "/app"
GIOI_HAN_MAC_DINH = 180
KET_QUA_PYTEST = ("passed", "failed", "error", "skipped", "no tests")


@dataclass
class DotBien:
    ten: str
    tep: str
    goc: str
    thay: str


@dataclass
class MoTa:
    bai: list[str]
    dot_bien: list[DotBien]
    mo_ta: str = ""


def doc_mo_ta(duong: Path) -> MoTa:
    if duong.suffix == ".py":
        ns = runpy.run_path(str(duong))
        tho_bai, tho_db, mo_ta = ns.get("BAI"), ns.get("DOT_BIEN"), ns.get("MO_TA", "")
    else:
        du_lieu = json.loads(duong.read_text(encoding="utf-8"))
        tho_bai, tho_db, mo_ta = du_lieu.get("bai"), du_lieu.get("dot_bien"), du_lieu.get("mo_ta", "")
    if not tho_bai or not isinstance(tho_bai, list):
        thoat(f"{duong}: thiếu danh sách 'bai' (hay BAI).")
    if not tho_db or not isinstance(tho_db, list):
        thoat(f"{duong}: thiếu danh sách 'dot_bien' (hay DOT_BIEN).")
    ds = []
    for i, d in enumerate(tho_db, start=1):
        if isinstance(d, (list, tuple)):
            d = dict(zip(("ten", "tep", "goc", "thay"), d))
        thieu = [k for k in ("ten", "tep", "goc", "thay") if k not in d]
        if thieu:
            thoat(f"{duong}: đột biến thứ {i} thiếu khóa {', '.join(thieu)}.")
        ds.append(DotBien(d["ten"], d["tep"], d["goc"], d["thay"]))
    return MoTa(list(tho_bai), ds, mo_ta)


def duong_trong_kho(tep: str) -> Path:
    """Đường dẫn tuyệt đối của tệp trong kho; từ chối thứ nằm ngoài backend/."""
    if not tep.startswith(TIEN_TO_TEP):
        thoat(f"Tệp đột biến phải nằm dưới {TIEN_TO_TEP} (nhận {tep!r}).")
    duong = (GOC_KHO / tep).resolve()
    if (GOC_KHO / "backend").resolve() not in duong.parents:
        thoat(f"Tệp {tep!r} nằm ngoài backend/.")
    if not duong.is_file():
        thoat(f"Không có tệp {tep!r}.")
    return duong


def doc_van_ban(duong: Path) -> str:
    # Chuẩn hóa về dấu xuống dòng LF: kho đặt eol=lf, và đoạn `goc` viết bằng LF
    return duong.read_text(encoding="utf-8").replace("\r\n", "\n")


def dich_trong_container(tep: str) -> str:
    return f"{THU_MUC_UNG_DUNG}/{tep[len(TIEN_TO_TEP):]}"


class BoChay:
    def __init__(self, container: str, bai: list[str], gioi_han: int) -> None:
        self.container, self.bai, self.gioi_han = container, bai, gioi_han

    def chep_vao(self, nguon: Path, dich: str) -> None:
        kq = chay([docker(), "cp", str(nguon), f"{self.container}:{dich}"])
        if kq.ma != 0:
            raise RuntimeError(f"docker cp thất bại cho {dich}: {kq.loi.strip()}")

    def chep_van_ban(self, van_ban: str, tep: str, thu_muc_tam: Path) -> None:
        tam = thu_muc_tam / Path(tep).name
        tam.write_text(van_ban, encoding="utf-8", newline="\n")
        self.chep_vao(tam, dich_trong_container(tep))

    def chay_bai(self) -> tuple[int, str]:
        """(mã pytest, một dòng tóm tắt). 124 là quá giờ."""
        kq = chay(
            [docker(), "exec", "-w", THU_MUC_UNG_DUNG, self.container, "timeout", str(self.gioi_han),
             "python", "-m", "pytest", "-p", "no:cacheprovider", "-q", "-x", *self.bai],
            cho_toi_da=self.gioi_han + 60,
        )
        if kq.ma == 124:
            # `timeout` trong container hết giờ, hoặc chính docker exec hết giờ: giết tiến trình còn treo
            # và nhả khóa trong cơ sở dữ liệu bằng cách khởi động lại container
            chay([docker(), "restart", self.container])
            cho_container(self.container, "healthy", 300)
            return 124, f"QUÁ GIỜ {self.gioi_han} giây (bài treo, đã khởi động lại container)"
        dong = [d.strip() for d in kq.dau_ra.splitlines() if any(k in d for k in KET_QUA_PYTEST)]
        tom_tat = dong[-1] if dong else (kq.dau_ra.strip().splitlines() or kq.loi.strip().splitlines() or ["(không có đầu ra)"])[-1]
        return kq.ma, tom_tat

    def bang_bam(self, tep: str) -> str | None:
        kq = chay([docker(), "exec", self.container, "sha256sum", dich_trong_container(tep)])
        return kq.dau_ra.split()[0] if kq.ma == 0 and kq.dau_ra.split() else None


def sha(van_ban: str) -> str:
    return hashlib.sha256(van_ban.encode("utf-8")).hexdigest()


def main() -> int:
    dung_utf8()
    p = argparse.ArgumentParser(
        prog="python -m scripts.kiem_chung.dot_bien",
        description="Chạy phép thử đột biến theo một tệp mô tả; mỗi đột biến phải bị bài kiểm thử bắt.")
    p.add_argument("mo_ta", type=Path, help="Tệp mô tả đột biến (.json hay .py)")
    p.add_argument("--container", default=f"{TIEN_TO_MAC_DINH}backend",
                   help=f"Container dịch vụ ứng dụng của cụm thử (mặc định {TIEN_TO_MAC_DINH}backend)")
    p.add_argument("--gioi-han", type=int, default=GIOI_HAN_MAC_DINH,
                   help=f"Số giây tối đa cho mỗi lượt chạy bài (mặc định {GIOI_HAN_MAC_DINH})")
    p.add_argument("--chi", metavar="CHUOI", help="Chỉ chạy các đột biến có tên chứa chuỗi này")
    ts = p.parse_args()

    mo_ta = doc_mo_ta(ts.mo_ta)
    if ts.container.startswith("dxlab-"):
        thoat("Không chạy đột biến trên container của cụm đang dùng thật (dxlab-*). Dùng container của cụm thử.")
    if mo_ta.mo_ta:
        print(mo_ta.mo_ta + "\n")
    danh_sach = [d for d in mo_ta.dot_bien if not ts.chi or ts.chi in d.ten]
    if not danh_sach:
        thoat(f"Không có đột biến nào khớp --chi {ts.chi!r}.")

    bo = BoChay(ts.container, mo_ta.bai, ts.gioi_han)

    # Mọi tệp sẽ bị đổi, và mọi tệp bài kiểm thử, được đưa về đúng bản trong kho trước khi so
    tep_bai = sorted({b.split("::", 1)[0] for b in mo_ta.bai})
    tep_doi = sorted({d.tep for d in danh_sach})
    goc_van_ban = {t: doc_van_ban(duong_trong_kho(t)) for t in tep_doi}

    def tra_goc(tam: Path) -> list[str]:
        loi = []
        for t in tep_doi:
            try:
                bo.chep_van_ban(goc_van_ban[t], t, tam)
            except Exception as e:  # noqa: BLE001
                loi.append(f"{t}: {e}")
        return loi

    # SIGTERM (đóng cửa sổ terminal, `kill`) cũng phải đi qua khối finally để trả tệp gốc
    def khi_bi_ngat(_so, _khung):  # noqa: ANN001
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, khi_bi_ngat)

    with tempfile.TemporaryDirectory(prefix="dot-bien-") as tmp:
        tam = Path(tmp)
        tinh_trang: list[tuple[str, str, str]] = []  # (BẮT|SỐNG|BỎ|LỖI, tên, ghi chú)
        da_dong_den_container = False
        try:
            for t in tep_bai:
                bo.chep_vao(GOC_KHO / "backend" / t, f"{THU_MUC_UNG_DUNG}/{t}")
            tra_goc(tam)
            da_dong_den_container = True

            ma, tom_tat = bo.chay_bai()
            print(f"GỐC           | {tom_tat}")
            if ma != 0 or "skipped" in tom_tat:
                print("Bộ bài gốc không xanh hoàn toàn (hoặc có bài bị bỏ qua) nên phép thử không có nghĩa. "
                      "Sửa trước khi chạy đột biến.", file=sys.stderr)
                return 2

            for d in danh_sach:
                goc = goc_van_ban[d.tep]
                so_lan = goc.count(d.goc)
                if so_lan != 1:
                    tinh_trang.append(("BỎ", d.ten, f"chuỗi gốc xuất hiện {so_lan} lần, cần đúng 1"))
                    print(f"BỎ            | {d.ten} | chuỗi gốc xuất hiện {so_lan} lần, cần đúng 1")
                    continue
                if d.goc == d.thay:
                    tinh_trang.append(("BỎ", d.ten, "chuỗi thế giống chuỗi gốc"))
                    print(f"BỎ            | {d.ten} | chuỗi thế giống chuỗi gốc")
                    continue
                try:
                    bo.chep_van_ban(goc.replace(d.goc, d.thay), d.tep, tam)
                    ma, tom_tat = bo.chay_bai()
                finally:
                    # Trả tệp gốc NGAY sau mỗi đột biến, không đợi cuối cùng
                    bo.chep_van_ban(goc, d.tep, tam)
                if ma == 0:
                    nhan = "SỐNG"
                elif ma in (1, 2, 124):
                    nhan = "BẮT"
                else:
                    nhan = "LỖI"  # mã 3-5, 125-127…: hạ tầng hỏng, không phải bài đỏ
                tinh_trang.append((nhan, d.ten, tom_tat))
                print(f"{nhan:<5}         | {d.ten} | {tom_tat}")
        except KeyboardInterrupt:
            print("\nBị ngắt — đang trả tệp gốc vào container…", file=sys.stderr)
            tinh_trang.append(("LỖI", "(bị ngắt giữa chừng)", ""))
        finally:
            loi_tra = tra_goc(tam) if da_dong_den_container else []

        # Xác nhận đã trả sạch: bảng băm trong container phải trùng bảng băm của bản trong kho
        lech = []
        for t in tep_doi:
            trong = bo.bang_bam(t)
            if trong != sha(goc_van_ban[t]):
                lech.append(t)
        print()
        if loi_tra or lech:
            print(f"KHÔNG TRẢ ĐƯỢC TỆP GỐC: {', '.join(loi_tra + lech)}", file=sys.stderr)
            print("Container có thể đang giữ mã đã đột biến. Chép lại bằng `docker cp` hoặc khởi tạo lại cụm thử.",
                  file=sys.stderr)
            return 1
        print(f"SAU KHI TRẢ   | {len(tep_doi)} tệp trong container trùng bản trong kho (so bảng băm sha256)")

        ma, tom_tat = bo.chay_bai()
        print(f"SAU KHI TRẢ   | {tom_tat}")
        if ma != 0:
            return 1

    dem = {k: sum(1 for t in tinh_trang if t[0] == k) for k in ("BẮT", "SỐNG", "BỎ", "LỖI")}
    print(f"\nĐột biến: {len(tinh_trang)} · BẮT {dem['BẮT']} · SỐNG {dem['SỐNG']} · BỎ {dem['BỎ']} · LỖI {dem['LỖI']}")
    if dem["SỐNG"]:
        print("Còn đột biến SỐNG: bộ bài chưa canh hành vi đó. Thêm bài kiểm thử hoặc siết bài sẵn có.")
    return 0 if len(tinh_trang) == dem["BẮT"] and tinh_trang else 1


if __name__ == "__main__":
    sys.exit(main())
