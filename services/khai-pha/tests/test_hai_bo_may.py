# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Hai bộ máy phải cho kết quả GIỐNG HỆT nhau (ADR-0007): bộ dự phòng `noi_bo` chỉ có ý nghĩa khi thay
# được `pm4py` mà không ai nhận ra. Ba tầng so sánh:
#
#   1. Đầu vào dựng tay, đáp án tính tay — gồm ca hai lượt trùng thời điểm và mã hồ sơ nhiều chữ số
#   2. Cả kết quả `phan_tich` trên bộ dữ liệu đáp án biết trước, mọi phạm vi
#   3. Cả kết quả `phan_tich` trên dữ liệu thật của cụm (chỉ so hai bộ máy với nhau, không so số tuyệt đối)

from __future__ import annotations

import datetime as dt
import json

import pytest

from app.bo_may import LuotVao, chon_bo_may
from app.cau_hinh import cau_hinh
from app.du_lieu import doc_du_lieu
from app.phan_tich import phan_tich

from . import dap_an

GOC = dt.datetime(2026, 3, 9, 9, 0, tzinfo=dt.timezone.utc)


def luot(ho_so: int, trang_thai: str, phut: int, thu_tu: int) -> LuotVao:
    return LuotVao(ho_so=ho_so, trang_thai=trang_thai, luc=GOC + dt.timedelta(minutes=phut), thu_tu=thu_tu)


@pytest.fixture(scope="module")
def hai_bo_may():
    try:
        return chon_bo_may("pm4py"), chon_bo_may("noi_bo")
    except ImportError as loi:
        pytest.skip(f"Bộ máy pm4py không nạp được: {loi}")


def bo_khoa_engine(kq: dict) -> str:
    """Toàn bộ kết quả trừ khóa `engine`, dạng chuỗi để so từng ký tự (khóa xếp cố định)."""
    return json.dumps({k: v for k, v in kq.items() if k != "engine"}, sort_keys=True, ensure_ascii=False)


# --- 1. Đầu vào dựng tay ---------------------------------------------------------------------------------

# Đưa vào KHÔNG theo thứ tự thời gian, để bộ máy phải tự xếp.
#   hồ sơ 1 và 2: a → b → c     hồ sơ 3: a → c
#   hồ sơ 7: x và y cùng một thời điểm, y có thứ tự nhỏ hơn nên đứng trước: y → x
#   hồ sơ 10 cũng a → b → c; hồ sơ 9 và 33 cùng p → q: mã phải xếp theo SỐ (1 < 2 < 10; 9 < 33),
#                  không theo chuỗi ("10" < "2"; "33" < "9")
#   hồ sơ 40: a → b → a → b (quay lại)    hồ sơ 50: chỉ một lượt, không có cặp nào
DAU_VAO = [
    luot(1, "c", 20, 3), luot(1, "a", 0, 1), luot(1, "b", 10, 2),
    luot(2, "b", 11, 5), luot(2, "a", 1, 4), luot(2, "c", 21, 6),
    luot(10, "a", 3, 60), luot(10, "c", 23, 62), luot(10, "b", 13, 61),
    luot(3, "c", 30, 8), luot(3, "a", 2, 7),
    luot(7, "x", 5, 20), luot(7, "y", 5, 19),
    luot(33, "q", 1, 33), luot(33, "p", 0, 32),
    luot(9, "p", 0, 30), luot(9, "q", 1, 31),
    luot(40, "b", 3, 41), luot(40, "a", 1, 40), luot(40, "a", 5, 42), luot(40, "b", 7, 43),
    luot(50, "z", 0, 50),
]
DO_THI = {
    ("a", "b"): 5, ("b", "c"): 3, ("a", "c"): 1, ("y", "x"): 1, ("p", "q"): 2, ("b", "a"): 1,
}
BIEN_THE = {
    ("a", "b", "c"): [1, 2, 10], ("a", "c"): [3], ("y", "x"): [7], ("p", "q"): [9, 33],
    ("a", "b", "a", "b"): [40], ("z",): [50],
}


def test_do_thi_dung_dap_an_tinh_tay(bo_may):
    assert bo_may.do_thi(DAU_VAO) == DO_THI


def test_bien_the_dung_dap_an_tinh_tay(bo_may):
    assert bo_may.bien_the(DAU_VAO) == BIEN_THE


def test_dau_vao_rong_cho_ket_qua_rong(bo_may):
    assert bo_may.do_thi([]) == {}
    assert bo_may.bien_the([]) == {}


def test_hai_bo_may_giong_nhau_tren_dau_vao_tay(hai_bo_may):
    pm4py, noi_bo = hai_bo_may
    assert pm4py.do_thi(DAU_VAO) == noi_bo.do_thi(DAU_VAO)
    assert pm4py.bien_the(DAU_VAO) == noi_bo.bien_the(DAU_VAO)


def test_ten_bo_may_khop_ten_chon(hai_bo_may):
    assert [b.ten for b in hai_bo_may] == ["pm4py", "noi_bo"]


def test_chon_bo_may_tu_choi_ten_la():
    with pytest.raises(ValueError, match="KHAI_PHA_BO_MAY"):
        chon_bo_may("khong-co-bo-may-nay")


# --- 2. Toàn bộ kết quả trên bộ dữ liệu đáp án biết trước ----------------------------------------------------


@pytest.mark.parametrize(
    ("tu", "den", "phong"),
    [
        (dt.date(2026, 3, 9), dt.date(2026, 3, 13), None),
        (dt.date(2026, 3, 9), dt.date(2026, 3, 13), ["A"]),
        (dt.date(2026, 3, 9), dt.date(2026, 3, 13), ["B"]),
        (dt.date(2026, 3, 9), dt.date(2026, 3, 13), ["A", "B", "C"]),
        (dt.date(2026, 3, 8), dt.date(2026, 3, 14), None),
        (dt.date(2026, 3, 10), dt.date(2026, 3, 11), None),
        (dt.date(2026, 3, 15), dt.date(2026, 3, 31), None),
    ],
)
def test_hai_bo_may_giong_het_tren_bo_du_lieu_dap_an(ket_noi_thu, hai_bo_may, tu, den, phong):
    pm4py, noi_bo = hai_bo_may
    du_lieu = doc_du_lieu(ket_noi_thu, tu, den, phong)
    a = phan_tich(du_lieu, pm4py, dap_an.cau_hinh_thu(pm4py))
    b = phan_tich(du_lieu, noi_bo, dap_an.cau_hinh_thu(noi_bo))
    assert (a["engine"], b["engine"]) == ("pm4py", "noi_bo")
    assert bo_khoa_engine(a) == bo_khoa_engine(b)


@pytest.mark.parametrize("ghi_de", [{"so_bien_the": 2}, {"so_ho_so_moi_nhom": 1}, {"boi_so_nghen": 1.0}])
def test_hai_bo_may_giong_het_khi_doi_cau_hinh(ket_noi_thu, hai_bo_may, ghi_de):
    pm4py, noi_bo = hai_bo_may
    du_lieu = doc_du_lieu(ket_noi_thu, *dap_an.KHOANG, None)
    a = phan_tich(du_lieu, pm4py, dap_an.cau_hinh_thu(pm4py, **ghi_de))
    b = phan_tich(du_lieu, noi_bo, dap_an.cau_hinh_thu(noi_bo, **ghi_de))
    assert bo_khoa_engine(a) == bo_khoa_engine(b)


# --- 3. Dữ liệu thật của cụm -----------------------------------------------------------------------------------

# Khoảng rộng, không có bảng tạm: đọc `public` bằng tài khoản chỉ đọc. Chỉ so hai bộ máy với nhau —
# số hồ sơ và con số cụ thể của dữ liệu thật đổi theo cụm nên không so tuyệt đối.
KHOANG_RONG = (dt.date(2020, 1, 1), dt.date(2100, 1, 1))


def test_hai_bo_may_giong_het_tren_du_lieu_that(ket_noi_that, hai_bo_may):
    pm4py, noi_bo = hai_bo_may
    du_lieu = doc_du_lieu(ket_noi_that, *KHOANG_RONG, None)
    cau = cau_hinh()
    a = phan_tich(du_lieu, pm4py, dap_an.cau_hinh_thu(pm4py, boi_so_nghen=cau.boi_so_nghen))
    b = phan_tich(du_lieu, noi_bo, dap_an.cau_hinh_thu(noi_bo, boi_so_nghen=cau.boi_so_nghen))
    assert bo_khoa_engine(a) == bo_khoa_engine(b)


def test_hai_bo_may_giong_het_tren_du_lieu_that_tung_phong(ket_noi_that, hai_bo_may):
    pm4py, noi_bo = hai_bo_may
    phong = [
        d[0] for d in ket_noi_that.execute(
            "SELECT DISTINCT department_code FROM bao_cao_nhat_ky WHERE thu_tu = 0 "
            "AND department_code IS NOT NULL ORDER BY 1"
        ).fetchall()
    ]
    for ma in phong:
        du_lieu = doc_du_lieu(ket_noi_that, *KHOANG_RONG, [ma])
        a = phan_tich(du_lieu, pm4py, dap_an.cau_hinh_thu(pm4py))
        b = phan_tich(du_lieu, noi_bo, dap_an.cau_hinh_thu(noi_bo))
        assert bo_khoa_engine(a) == bo_khoa_engine(b), ma
