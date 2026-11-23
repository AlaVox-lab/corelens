# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Bước ngôn ngữ của khởi tạo kho tri thức (#535): gói ngôn ngữ Wiki.js tải hỏng ở bất kỳ lần chạy nào thì giao
# diện lùi về tiếng Anh, bài mẫu vẫn tạo được, bước khởi tạo không chết.
#
# Wiki.js giả lập ở mức GraphQL (`WikiGia.graphql`), giữ đúng hai điều của bản thật làm nên lỗi: cấu hình ngôn
# ngữ (`config.locale`) và bảng ngôn ngữ đã cài (`locales`) là hai thứ riêng, `updateLocale` ghi cấu hình rồi mới
# hỏng; và bài tạo bằng ngôn ngữ chưa cài bị khóa ngoại `pages_localecode_foreign` chặn.
#
# Chỉ thư viện chuẩn: tích hợp liên tục chạy bằng `python3 -m unittest discover -s infra/tri-thuc` trong job
# header (dịch vụ ứng dụng không có thư mục này trong ảnh). Ở máy: cùng lệnh đó, hay pytest trỏ vào tệp này.

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

THU_MUC = Path(__file__).resolve().parent
sys.path.insert(0, str(THU_MUC))

import khoi_tao  # noqa: E402 — nạp sau khi thêm đúng thư mục vào đường tìm

LOI_KHOA_NGOAI = 'insert into "pages" violates foreign key constraint "pages_localecode_foreign"'


class WikiGia:
    """Wiki.js giả: đủ các câu GraphQL mà bước ngôn ngữ và bước bài mẫu gọi."""

    def __init__(self, *, cau_hinh="en", da_cai=("en",), tai="duoc", doi="duoc"):
        self.cau_hinh = cau_hinh
        self.da_cai = set(da_cai)
        # tai: "duoc" — cài trọn; "bao-loi" — responseResult hỏng; "khong-tron" — báo thành công mà không cài;
        #      "mang" — lỗi kết nối
        self.tai = tai
        # doi: "duoc"; "ghi-roi-hong" — với mọi ngôn ngữ trừ `en`, ghi cấu hình rồi báo lỗi (đúng tình huống thật)
        self.doi = doi
        self.bai: dict[tuple[str, str], str] = {}
        self.lan_tai = 0

    @staticmethod
    def _kq(dung: bool, tin: str = "") -> dict:
        return {"responseResult": {"succeeded": dung, "message": tin}}

    def graphql(self, truy_van: str, bien_so: dict | None = None, token: str | None = None) -> dict:
        b = bien_so or {}
        if "downloadLocale" in truy_van:
            self.lan_tai += 1
            if self.tai == "mang":
                raise OSError("Network is unreachable")
            if self.tai == "duoc":
                self.da_cai.add(b["l"])
            if self.tai == "bao-loi":
                return {"localization": {"downloadLocale": self._kq(False, "Failed to download locale")}}
            return {"localization": {"downloadLocale": self._kq(True)}}
        if "updateLocale" in truy_van:
            self.cau_hinh = b["l"]
            if self.doi == "ghi-roi-hong" and b["l"] != "en":
                return {"localization": {"updateLocale": self._kq(False, "Cannot read properties of undefined (reading 'isRTL')")}}
            return {"localization": {"updateLocale": self._kq(True)}}
        if "locales" in truy_van:
            return {"localization": {"locales": [{"code": c, "isInstalled": True} for c in sorted(self.da_cai)]}}
        if "config { locale }" in truy_van:
            return {"localization": {"config": {"locale": self.cau_hinh}}}
        if "singleByPath" in truy_van:
            if (b["p"], b["l"]) not in self.bai:
                raise RuntimeError("GraphQL báo lỗi: This page does not exist.")
            return {"pages": {"singleByPath": {"id": 1}}}
        if "create(" in truy_van:
            if b["l"] not in self.da_cai:
                return {"pages": {"create": self._kq(False, LOI_KHOA_NGOAI)}}
            self.bai[(b["p"], b["l"])] = b["ti"]
            return {"pages": {"create": self._kq(True)}}
        raise AssertionError(f"câu GraphQL lạ trong bài kiểm: {truy_van[:80]}")


class BuocNgonNgu(unittest.TestCase):
    def setUp(self) -> None:
        self.env_cu = {k: os.environ.get(k) for k in ("WIKI_LOCALE", "WIKI_SEED_DIR")}
        os.environ["WIKI_LOCALE"] = "vi"
        os.environ["WIKI_SEED_DIR"] = str(THU_MUC / "bai-mau")
        self.so_bai = len(list((THU_MUC / "bai-mau").glob("*.md")))
        self.assertGreater(self.so_bai, 0, "thư mục bài mẫu phải có bài")

    def tearDown(self) -> None:
        for k, v in self.env_cu.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def chay(self, w: WikiGia) -> str:
        """Bước ngôn ngữ rồi bước bài mẫu, như `khoi_tao()`; SystemExit ở đây là bước khởi tạo chết (mã khác 0)."""
        try:
            ngon_ngu = khoi_tao.ngon_ngu(w)
            khoi_tao.nap_bai_mau(w, ngon_ngu)
        except SystemExit as loi:
            self.fail(f"bước khởi tạo thoát: {loi}")
        return ngon_ngu

    def test_tai_duoc_thi_giao_dien_va_bai_mau_tieng_viet(self):
        w = WikiGia()
        self.assertEqual(self.chay(w), "vi")
        self.assertEqual(w.cau_hinh, "vi")
        self.assertEqual({l for _, l in w.bai}, {"vi"})
        self.assertEqual(len(w.bai), self.so_bai)

    def test_tai_bao_loi_thi_tieng_anh_va_van_du_bai_mau(self):
        w = WikiGia(tai="bao-loi")
        self.assertEqual(self.chay(w), "en")
        self.assertEqual(w.cau_hinh, "en")
        self.assertEqual({l for _, l in w.bai}, {"en"})
        self.assertEqual(len(w.bai), self.so_bai)

    def test_loi_mang_khi_tai_thi_tieng_anh(self):
        w = WikiGia(tai="mang")
        self.assertEqual(self.chay(w), "en")
        self.assertEqual(len(w.bai), self.so_bai)

    def test_tai_bao_thanh_cong_ma_goi_khong_tron_thi_khong_doi_giao_dien(self):
        """#535: downloadLocale báo thành công nhưng `vi` không vào bảng ngôn ngữ đã cài — không gọi updateLocale."""
        w = WikiGia(tai="khong-tron", doi="ghi-roi-hong")
        self.assertEqual(self.chay(w), "en")
        self.assertEqual(w.cau_hinh, "en", "cấu hình không được trỏ tới ngôn ngữ chưa cài")
        self.assertEqual({l for _, l in w.bai}, {"en"})
        self.assertEqual(len(w.bai), self.so_bai)

    def test_updateLocale_ghi_vi_roi_hong_thi_dat_cau_hinh_ve_tieng_anh(self):
        """#535: updateLocale ghi cấu hình `vi` rồi ném lỗi `isRTL` — cấu hình phải được đặt về `en`."""
        w = WikiGia(tai="duoc", doi="ghi-roi-hong")
        self.assertEqual(self.chay(w), "en")
        self.assertEqual(w.cau_hinh, "en")
        self.assertEqual({l for _, l in w.bai}, {"en"})
        self.assertEqual(len(w.bai), self.so_bai)

    def test_chay_lai_khi_cau_hinh_da_la_vi_ma_chua_cai(self):
        """Lần chạy sau của #535: cấu hình đã `vi`, gói chưa cài. Phải thử tải lại; hỏng thì về `en`, không lỗi
        khóa ngoại khi tạo bài."""
        w = WikiGia(cau_hinh="vi", tai="bao-loi")
        self.assertEqual(self.chay(w), "en")
        self.assertEqual(w.lan_tai, 1, "phải thử tải lại gói ngôn ngữ")
        self.assertEqual(w.cau_hinh, "en")
        self.assertEqual(len(w.bai), self.so_bai)

    def test_chay_lai_khi_cau_hinh_vi_va_tai_duoc_lan_nay(self):
        w = WikiGia(cau_hinh="vi", tai="duoc")
        self.assertEqual(self.chay(w), "vi")
        self.assertEqual({l for _, l in w.bai}, {"vi"})

    def test_da_cai_va_dang_dung_thi_khong_tai_lai(self):
        w = WikiGia(cau_hinh="vi", da_cai=("en", "vi"))
        self.assertEqual(self.chay(w), "vi")
        self.assertEqual(w.lan_tai, 0)

    def test_chay_lai_nhieu_lan_khong_tao_trung_bai(self):
        w = WikiGia(tai="bao-loi")
        self.chay(w)
        self.chay(w)
        self.chay(w)
        self.assertEqual(len(w.bai), self.so_bai)

    def test_doi_ngon_ngu_giua_hai_lan_chay(self):
        """Hành vi hiện có, ghi lại để biết: bài đã có kiểm theo (đường dẫn, ngôn ngữ), nên lần đầu không tải được
        (bài `en`) rồi lần sau tải được (`vi`) thì có thêm bản `vi` của cùng đường dẫn — không trùng trong một
        ngôn ngữ."""
        w = WikiGia(tai="bao-loi")
        self.chay(w)
        w.tai = "duoc"
        self.assertEqual(self.chay(w), "vi")
        self.assertEqual(len(w.bai), 2 * self.so_bai)
        self.assertEqual(len({p for p, _ in w.bai}), self.so_bai)

    def test_dat_ngon_ngu_tieng_anh_thi_khong_tai_gi(self):
        os.environ["WIKI_LOCALE"] = "en"
        w = WikiGia()
        self.assertEqual(self.chay(w), "en")
        self.assertEqual(w.lan_tai, 0)


if __name__ == "__main__":
    unittest.main()
