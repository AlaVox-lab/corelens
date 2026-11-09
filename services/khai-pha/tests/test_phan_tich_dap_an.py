# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Phép phân tích trên bộ dữ liệu ĐÁP ÁN BIẾT TRƯỚC (tests/dap_an.py), chạy với cả hai bộ máy.
#
# Mọi con số trong tệp này tính tay từ bảng hồ sơ ở đầu tests/dap_an.py. Chỗ nào đáp án phụ thuộc lịch
# làm việc (thời gian chờ), bài vừa so với giá trị tính tay vừa so với chính hàm `so_giay_lam_viec`.

from __future__ import annotations

import datetime as dt
import statistics

import pytest

from app.du_lieu import doc_du_lieu

from . import dap_an
from .dap_an import chay_phan_tich

TRONG_KHOANG = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16}
TONG = len(TRONG_KHOANG)  # 14 hồ sơ


def ngay(thang: int, ngay_: int) -> dt.date:
    return dt.date(2026, thang, ngay_)


def ma_ho_so_doc_duoc(ket_noi, tu, den, phong) -> set[int]:
    return {s.ho_so for s in doc_du_lieu(ket_noi, tu, den, phong).su_kien}


# --- 1. Số hồ sơ, nhánh lệch, cạnh, trạng thái -----------------------------------------------------


def test_so_ho_so_va_so_su_kien(ket_noi_thu, bo_may):
    kq = chay_phan_tich(ket_noi_thu, bo_may)
    assert kq["engine"] == bo_may.ten
    assert kq["cases_count"] == TONG
    # 14 sự kiện mở đầu + 55 lần chuyển, tính cả lần xu-ly → xu-ly của hồ sơ 3
    assert kq["events_count"] == 69


# nhánh lệch → hồ sơ (hồ sơ 12 làm lại nhưng gửi ngoài khoảng nên không được tính)
NHANH_LECH = {
    "rework": [4, 5],
    "escalation": [6],
    "wait_expiry": [8],
    "reopen": [9],
    "multiple_routing": [10],
}


def test_nhanh_lech_dung_so_va_dung_ho_so(ket_noi_thu, bo_may):
    kq = chay_phan_tich(ket_noi_thu, bo_may)
    assert [d["kind"] for d in kq["deviations"]] == list(NHANH_LECH)
    for d in kq["deviations"]:
        co = NHANH_LECH[d["kind"]]
        assert d["cases"] == co, d["kind"]
        assert d["cases_count"] == len(co), d["kind"]
        assert d["ratio"] == round(len(co) / TONG, 4), d["kind"]


def test_dat_phong_mot_lan_hay_doi_truong_khac_khong_phai_dat_phong_hai_lan(ket_noi_thu, bo_may):
    # Hồ sơ 11 đặt phòng một lần, hồ sơ 2 đổi ưu tiên hai lần: chỉ hồ sơ 10 (hai lần department_code)
    kq = chay_phan_tich(ket_noi_thu, bo_may)
    dinh_tuyen = next(d for d in kq["deviations"] if d["kind"] == "multiple_routing")
    assert dinh_tuyen["cases"] == [10]


# (từ, đến) → (số lần, số hồ sơ, là luồng chính, số lần theo loại)
CANH = {
    ("moi", "cho-1"): (14, 14, True, {"main": 14}),
    ("cho-1", "xu-ly"): (16, 13, True, {"main": 16}),
    ("xu-ly", "xong"): (14, 13, True, {"main": 14}),
    ("xu-ly", "cho-1"): (3, 2, False, {"rework": 3}),
    ("xu-ly", "cho-kh"): (2, 2, True, {"main": 2}),
    ("cho-1", "cho-2"): (1, 1, False, {"escalation": 1}),
    ("cho-2", "xu-ly"): (1, 1, True, {"main": 1}),
    ("cho-kh", "xu-ly"): (1, 1, True, {"main": 1}),
    ("cho-kh", "huy"): (1, 1, False, {"wait_expiry": 1}),
    ("xong", "xu-ly"): (1, 1, False, {"reopen": 1}),
}


def test_canh_dung_so_lan_so_ho_so_loai(ket_noi_thu, bo_may):
    kq = chay_phan_tich(ket_noi_thu, bo_may)
    thuc_te = {
        (e["from"], e["to"]): (e["count"], e["cases"], e["is_main"], e["kinds"]) for e in kq["edges"]
    }
    assert thuc_te == CANH
    # Xếp theo số lần giảm dần, hai cạnh bằng nhau thì theo cặp trạng thái
    khoa = [(-e["count"], e["from"], e["to"]) for e in kq["edges"]]
    assert khoa == sorted(khoa)


def test_canh_tu_tro_khong_thanh_canh_khong_thanh_luot(ket_noi_thu, bo_may):
    # Hồ sơ 3 có một sự kiện xu-ly → xu-ly (ADR-0005)
    kq = chay_phan_tich(ket_noi_thu, bo_may)
    assert all(e["from"] != e["to"] for e in kq["edges"])
    xu_ly = next(t for t in kq["states"] if t["code"] == "xu-ly")
    # 19 lần vào xu-ly = 16 từ cho-1 + 1 từ cho-2 + 1 từ cho-kh + 1 mở lại; lần tự trỏ không cộng
    assert xu_ly["visits"] == 19
    assert xu_ly["cases"] == TONG
    # Nhưng sự kiện đó vẫn là một sự kiện của nhật ký
    assert kq["events_count"] == 69


# mã → (nhãn, bắt đầu, kết thúc, số lượt vào, số hồ sơ), theo thứ tự hiển thị của bộ quy tắc
TRANG_THAI = [
    ("moi", "Mới", True, False, 14, 14),
    ("cho-1", "Chờ cấp 1", False, False, 17, 14),
    ("cho-2", "Chờ cấp 2", False, False, 1, 1),
    ("xu-ly", "Đang xử lý", False, False, 19, 14),
    ("cho-kh", "Chờ bổ sung", False, False, 2, 2),
    ("xong", "Xong", False, True, 14, 13),
    ("huy", "Hủy", False, True, 1, 1),
]


def test_trang_thai_nhan_co_va_so_lan_vao(ket_noi_thu, bo_may):
    kq = chay_phan_tich(ket_noi_thu, bo_may)
    thuc_te = [
        (t["code"], t["label"], t["is_initial"], t["is_terminal"], t["visits"], t["cases"])
        for t in kq["states"]
    ]
    assert thuc_te == TRANG_THAI


def test_luong_chinh_theo_thiet_ke_doc_tu_bo_quy_tac(ket_noi_thu, bo_may):
    # Cạnh người, không làm lại, không mở lại, có đổi trạng thái. Không có tra-lai (làm lại), len-cap
    # và het-han-cho (hệ thống), mo-lai (mở lại), tu-xet (tự trỏ)
    kq = chay_phan_tich(ket_noi_thu, bo_may)
    thuc_te = [(c["from"], c["to"]) for c in kq["designed_main_flow"]]
    assert len(thuc_te) == len(set(thuc_te))
    assert set(thuc_te) == {
        ("moi", "cho-1"),
        ("cho-1", "xu-ly"),
        ("xu-ly", "xong"),
        ("cho-2", "xu-ly"),
        ("xu-ly", "cho-kh"),
        ("cho-kh", "xu-ly"),
    }


# --- 2. Phạm vi phòng và khoảng ngày ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("phong", "mong_doi"),
    [
        (["A"], {1, 2, 3, 4, 5, 9, 14}),
        (["B"], {6, 7, 8, 10, 15}),
        (["C"], {11}),
        (["A", "B"], {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 14, 15}),
        (None, TRONG_KHOANG),  # None là toàn công ty, kể cả hồ sơ 16 chưa có phòng
        (["Z"], set()),
        ([], set()),
    ],
)
def test_pham_vi_phong(ket_noi_thu, bo_may, phong, mong_doi):
    assert ma_ho_so_doc_duoc(ket_noi_thu, *dap_an.KHOANG, phong) == mong_doi
    kq = chay_phan_tich(ket_noi_thu, bo_may, phong=phong)
    assert kq["cases_count"] == len(mong_doi)
    # Mọi hồ sơ trong mọi nhánh lệch và biến thể đều thuộc phạm vi
    for d in kq["deviations"]:
        assert set(d["cases"]) <= mong_doi
    for v in kq["variants"]:
        assert set(v["cases"]) <= mong_doi
    assert sum(v["cases_count"] for v in kq["variants"]) + kq["other_variants_cases"] == len(mong_doi)


def test_pham_vi_phong_b_chi_con_nhanh_lech_cua_phong_b(ket_noi_thu, bo_may):
    kq = chay_phan_tich(ket_noi_thu, bo_may, phong=["B"])
    co = {d["kind"]: d["cases"] for d in kq["deviations"]}
    assert co == {"rework": [], "escalation": [6], "wait_expiry": [8], "reopen": [], "multiple_routing": [10]}


def test_pham_vi_rong_tra_ket_qua_rong_chu_khong_loi(ket_noi_thu, bo_may):
    kq = chay_phan_tich(ket_noi_thu, bo_may, phong=["Z"])
    assert kq["cases_count"] == 0
    assert kq["events_count"] == 0
    assert kq["states"] == [] and kq["edges"] == [] and kq["variants"] == []
    assert kq["other_variants_cases"] == 0
    assert kq["bottlenecks"]["ranking"] == []
    assert all(d["cases_count"] == 0 and d["ratio"] == 0.0 for d in kq["deviations"])


# Hồ sơ 12 gửi 23:59:59 ngày 08/03 và hồ sơ 13 gửi 00:00:00 ngày 14/03 (giờ của lịch) nằm ngay sát biên;
# tính theo UTC thì cả hai lọt vào khoảng 09-13/03 sai chỗ, và hồ sơ 14 (00:00:00 ngày 09/03) rơi ra ngoài
@pytest.mark.parametrize(
    ("tu", "den", "mong_doi"),
    [
        (ngay(3, 9), ngay(3, 13), TRONG_KHOANG),
        (ngay(3, 9), ngay(3, 9), {1, 2, 14}),
        (ngay(3, 13), ngay(3, 13), {11, 15, 16}),  # ngày cuối tính cả ngày, tới 23:59:59
        (ngay(3, 8), ngay(3, 8), {12}),
        (ngay(3, 14), ngay(3, 14), {13}),
        (ngay(3, 8), ngay(3, 14), set(range(1, 17))),
        (ngay(3, 10), ngay(3, 12), {3, 4, 5, 6, 7, 8, 9, 10}),
        (ngay(3, 15), ngay(3, 31), set()),
    ],
)
def test_khoang_ngay_cat_dung_bien_theo_mui_gio_cua_lich(ket_noi_thu, bo_may, tu, den, mong_doi):
    assert ma_ho_so_doc_duoc(ket_noi_thu, tu, den, None) == mong_doi
    assert chay_phan_tich(ket_noi_thu, bo_may, tu, den)["cases_count"] == len(mong_doi)


def test_su_kien_sau_ngay_cuoi_van_thuoc_ho_so_trong_khoang(ket_noi_thu, bo_may):
    # Hồ sơ 15 gửi ngày 13/03 nhưng được nhận, giao, xong ngày 16/03: cả đường đi vẫn nằm trong kết quả
    kq = chay_phan_tich(ket_noi_thu, bo_may, ngay(3, 13), ngay(3, 13))
    assert kq["cases_count"] == 3
    assert kq["variants"][0]["sequence"] == ["moi", "cho-1", "xu-ly", "xong"]
    assert kq["variants"][0]["cases"] == [11, 15, 16]


def test_khoang_khong_co_ho_so_cho_do_thi_rong(ket_noi_thu, bo_may):
    # Bộ dữ liệu thử chỉ có hồ sơ tháng 3/2026: khoảng không chứa hồ sơ nào cho đồ thị rỗng
    kq = chay_phan_tich(ket_noi_thu, bo_may, ngay(1, 1), ngay(1, 31))
    assert kq["cases_count"] == 0 and kq["edges"] == []


# --- 3. Thời gian chờ và điểm nghẽn -------------------------------------------------------------------

# Thời gian chờ từng lượt (giây làm việc), tính tay từ bảng giờ trong tests/dap_an.py. Bài
# test_lich_dung_gia_dinh so khớp từng giá trị với hàm `so_giay_lam_viec` của cơ sở dữ liệu.
GIAY_CHO = {
    "moi": [300] * 3 + [600] * 8 + [1800, 3600, 3600],
    "cho-1": [1200] * 6 + [1500] + [1800] * 6 + [2400, 3000, 3600, 6900],
    "xu-ly": [1200] + [1800] * 7 + [2400] * 2 + [2700] + [3600] * 7 + [5400],
    "cho-2": [1800],
    "cho-kh": [5400, 28800],
}
TRUNG_VI = {"moi": 600, "cho-1": 1800, "cho-2": 1800, "xu-ly": 2400, "cho-kh": 17100}
TRUNG_VI_CHUNG = 1800  # 53 lượt, lượt thứ 27 là 1800


def test_lich_dung_gia_dinh(ket_noi_thu, mui_gio, ma_ho_so_trong_khoang):
    """Hồ sơ thử đặt mốc trong giờ làm việc 08-12 và 13-17 các ngày thứ Hai-thứ Sáu của lịch mẫu.
    Lịch cụm này khác thì bài nào dưới đây sai theo, và bài này chỉ rõ nguyên nhân."""
    giay = dap_an.giay_cho_mong_doi(ket_noi_thu, mui_gio, ma_ho_so_trong_khoang)
    assert {ma: sorted(ds) for ma, ds in giay.items()} == {ma: sorted(ds) for ma, ds in GIAY_CHO.items()}


def test_trung_vi_cho_bang_trung_vi_tinh_rieng(ket_noi_thu, bo_may, mui_gio, ma_ho_so_trong_khoang):
    giay = dap_an.giay_cho_mong_doi(ket_noi_thu, mui_gio, ma_ho_so_trong_khoang)
    kq = chay_phan_tich(ket_noi_thu, bo_may)
    theo_ma = {t["code"]: t for t in kq["states"]}
    for ma, ds in giay.items():
        assert theo_ma[ma]["median_wait_seconds"] == int(round(statistics.median(ds))), ma
    tat_ca = [g for ds in giay.values() for g in ds]
    assert kq["bottlenecks"]["overall_median_wait_seconds"] == int(round(statistics.median(tat_ca)))


def test_trung_vi_cho_dung_gia_tri_tinh_tay(ket_noi_thu, bo_may):
    kq = chay_phan_tich(ket_noi_thu, bo_may)
    theo_ma = {t["code"]: t["median_wait_seconds"] for t in kq["states"]}
    assert theo_ma == {**TRUNG_VI, "xong": None, "huy": None}
    assert kq["bottlenecks"]["overall_median_wait_seconds"] == TRUNG_VI_CHUNG


def test_trang_thai_ket_thuc_khong_co_thoi_gian_cho(ket_noi_thu, bo_may):
    kq = chay_phan_tich(ket_noi_thu, bo_may)
    for t in kq["states"]:
        if t["is_terminal"]:
            assert t["median_wait_seconds"] is None and not t["is_bottleneck"], t["code"]
    ma_xep_hang = [r["code"] for r in kq["bottlenecks"]["ranking"]]
    assert "xong" not in ma_xep_hang and "huy" not in ma_xep_hang


def test_trang_thai_nghen_nhat_dung_dau_xep_hang(ket_noi_thu, bo_may):
    kq = chay_phan_tich(ket_noi_thu, bo_may)
    xep_hang = kq["bottlenecks"]["ranking"]
    # Hai trạng thái cùng trung vị 1800 (cho-1, cho-2) xếp theo mã
    assert [r["code"] for r in xep_hang] == ["cho-kh", "xu-ly", "cho-1", "cho-2", "moi"]
    assert xep_hang[0]["median_wait_seconds"] == 17100
    assert [r["median_wait_seconds"] for r in xep_hang] == sorted(
        (r["median_wait_seconds"] for r in xep_hang), reverse=True
    )


@pytest.mark.parametrize(
    ("boi_so", "nghen", "nguong"),
    [
        (1.0, {"cho-1", "cho-2", "xu-ly", "cho-kh"}, 1800),
        (2.0, {"cho-kh"}, 3600),
        (9.5, {"cho-kh"}, 17100),  # đúng ngưỡng vẫn là nghẽn
        (9.6, set(), 17280),
    ],
)
def test_diem_nghen_theo_boi_so_cau_hinh(ket_noi_thu, bo_may, boi_so, nghen, nguong):
    kq = chay_phan_tich(ket_noi_thu, bo_may, boi_so_nghen=boi_so)
    assert kq["bottlenecks"]["factor"] == boi_so
    assert kq["bottlenecks"]["threshold_seconds"] == nguong
    assert {t["code"] for t in kq["states"] if t["is_bottleneck"]} == nghen
    assert {r["code"] for r in kq["bottlenecks"]["ranking"] if r["is_bottleneck"]} == nghen


# --- 4. Biến thể --------------------------------------------------------------------------------------

# (chuỗi, số hồ sơ, hồ sơ), nhiều hồ sơ nhất trước; số hồ sơ bằng nhau thì theo chuỗi tăng dần
BIEN_THE = [
    (["moi", "cho-1", "xu-ly", "xong"], [1, 2, 3, 10, 11, 14, 15, 16]),
    (["moi", "cho-1", "cho-2", "xu-ly", "xong"], [6]),
    (["moi", "cho-1", "xu-ly", "cho-1", "xu-ly", "cho-1", "xu-ly", "xong"], [5]),
    (["moi", "cho-1", "xu-ly", "cho-1", "xu-ly", "xong"], [4]),
    (["moi", "cho-1", "xu-ly", "cho-kh", "huy"], [8]),
    (["moi", "cho-1", "xu-ly", "cho-kh", "xu-ly", "xong"], [7]),
    (["moi", "cho-1", "xu-ly", "xong", "xu-ly", "xong"], [9]),
]


def test_bien_the_dung_chuoi_so_ho_so_va_thu_tu(ket_noi_thu, bo_may):
    kq = chay_phan_tich(ket_noi_thu, bo_may)
    thuc_te = [(v["sequence"], v["cases"]) for v in kq["variants"]]
    assert thuc_te == BIEN_THE
    for v, (_, ho_so) in zip(kq["variants"], BIEN_THE):
        assert v["cases_count"] == len(ho_so)
        assert v["ratio"] == round(len(ho_so) / TONG, 4)
    assert kq["other_variants_cases"] == 0
    dem = [v["cases_count"] for v in kq["variants"]]
    assert dem == sorted(dem, reverse=True)


@pytest.mark.parametrize(("so_bien_the", "con_lai"), [(10, 0), (7, 0), (3, 4), (1, 6)])
def test_bien_the_gioi_han_so_luong_va_dem_phan_con_lai(ket_noi_thu, bo_may, so_bien_the, con_lai):
    kq = chay_phan_tich(ket_noi_thu, bo_may, so_bien_the=so_bien_the)
    assert [v["sequence"] for v in kq["variants"]] == [c for c, _ in BIEN_THE[:so_bien_the]]
    assert kq["other_variants_cases"] == con_lai
    # Hồ sơ không bao giờ biến mất: phần hiện và phần gộp cộng đủ tổng
    assert sum(v["cases_count"] for v in kq["variants"]) + kq["other_variants_cases"] == TONG


def test_gioi_han_ma_ho_so_moi_nhom_van_dem_du(ket_noi_thu, bo_may):
    kq = chay_phan_tich(ket_noi_thu, bo_may, so_ho_so_moi_nhom=2)
    chinh = kq["variants"][0]
    assert chinh["cases_count"] == 8 and chinh["cases"] == [1, 2]
    lam_lai = next(d for d in kq["deviations"] if d["kind"] == "rework")
    assert lam_lai["cases_count"] == 2 and lam_lai["cases"] == [4, 5]
    lam_lai = chay_phan_tich(ket_noi_thu, bo_may, so_ho_so_moi_nhom=1)["deviations"][0]
    assert lam_lai["cases_count"] == 2 and lam_lai["cases"] == [4]


# --- 5. Đổi cờ trong dữ liệu thì kết quả đổi theo, không cần sửa mã -------------------------------------


def cap_nhat_canh(ket_noi, dat: str, hoat_dong: str) -> None:
    """Sửa một cạnh của bộ quy tắc giả (bảng tạm). Hoàn tác cùng giao dịch của bài."""
    ket_noi.execute(f"UPDATE pg_temp.transitions SET {dat} WHERE activity_code = %s", (hoat_dong,))


def nhanh(kq: dict, loai: str) -> dict:
    return next(d for d in kq["deviations"] if d["kind"] == loai)


def canh(kq: dict, tu: str, den: str) -> dict:
    return next(e for e in kq["edges"] if (e["from"], e["to"]) == (tu, den))


def test_tat_co_lam_lai_thi_nhanh_lam_lai_het_va_canh_thanh_luong_chinh(ket_noi_thu, bo_may):
    truoc = chay_phan_tich(ket_noi_thu, bo_may)
    assert nhanh(truoc, "rework")["cases_count"] == 2
    cap_nhat_canh(ket_noi_thu, "is_rework = false", "tra-lai")
    sau = chay_phan_tich(ket_noi_thu, bo_may)
    assert nhanh(sau, "rework")["cases"] == [] and nhanh(sau, "rework")["cases_count"] == 0
    cong = canh(sau, "xu-ly", "cho-1")
    assert cong["is_main"] is True and cong["kinds"] == {"main": 3}
    assert ("xu-ly", "cho-1") in {(c["from"], c["to"]) for c in sau["designed_main_flow"]}
    # Đồ thị không đổi: chỉ cách PHÂN LOẠI đổi
    assert [(e["from"], e["to"], e["count"]) for e in sau["edges"]] == [
        (e["from"], e["to"], e["count"]) for e in truoc["edges"]
    ]


def test_bat_co_lam_lai_tren_canh_khac_thi_nhanh_lam_lai_doi_dung_so(ket_noi_thu, bo_may):
    # Đánh dấu cạnh giao (cho-1 → xu-ly) là làm lại: mọi hồ sơ từng đi qua nó, trừ hồ sơ 6 leo thang
    # sang cho-2 nên đi cạnh giao-cap-2
    cap_nhat_canh(ket_noi_thu, "is_rework = true", "giao")
    kq = chay_phan_tich(ket_noi_thu, bo_may)
    mong_doi = sorted(TRONG_KHOANG - {6})
    assert nhanh(kq, "rework")["cases"] == mong_doi
    assert nhanh(kq, "rework")["cases_count"] == 13
    cong = canh(kq, "cho-1", "xu-ly")
    assert cong["is_main"] is False and cong["kinds"] == {"rework": 16}
    assert ("cho-1", "xu-ly") not in {(c["from"], c["to"]) for c in kq["designed_main_flow"]}


def test_them_han_cho_vao_canh_he_thong_thi_leo_thang_thanh_het_han_cho(ket_noi_thu, bo_may):
    cap_nhat_canh(ket_noi_thu, "auto_after_hours = 24", "len-cap")
    kq = chay_phan_tich(ket_noi_thu, bo_may)
    assert nhanh(kq, "escalation")["cases"] == []
    assert nhanh(kq, "wait_expiry")["cases"] == [6, 8]
    assert canh(kq, "cho-1", "cho-2")["kinds"] == {"wait_expiry": 1}


def test_bo_cua_so_mo_lai_thi_het_nhanh_mo_lai(ket_noi_thu, bo_may):
    cap_nhat_canh(ket_noi_thu, "reopen_window_hours = NULL", "mo-lai")
    kq = chay_phan_tich(ket_noi_thu, bo_may)
    assert nhanh(kq, "reopen")["cases_count"] == 0
    cong = canh(kq, "xong", "xu-ly")
    assert cong["is_main"] is True and cong["kinds"] == {"main": 1}


def test_doi_nhan_va_co_trang_thai_thi_ket_qua_doi_theo(ket_noi_thu, bo_may):
    # Trạng thái kết thúc cũng nằm trong dữ liệu: coi cho-kh là kết thúc thì nó hết thời gian chờ
    ket_noi_thu.execute("UPDATE pg_temp.states SET is_terminal = true, label = 'Chờ (đóng)' WHERE code = 'cho-kh'")
    kq = chay_phan_tich(ket_noi_thu, bo_may)
    cho_kh = next(t for t in kq["states"] if t["code"] == "cho-kh")
    assert cho_kh["label"] == "Chờ (đóng)" and cho_kh["is_terminal"] is True
    assert cho_kh["median_wait_seconds"] is None
    assert "cho-kh" not in {r["code"] for r in kq["bottlenecks"]["ranking"]}
    assert {t["code"] for t in kq["states"] if t["is_bottleneck"]} == set()
