# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 AlaVox-lab
#
# Kết quả tuân thủ của MỘT hồ sơ (#448): bước lệch theo đúng định nghĩa nhánh lệch của kết quả toàn bộ
# (`phan_tich.buoc_lech`). Ba tầng:
#
#   1. Bộ dữ liệu đáp án biết trước (tests/dap_an.py): hồ sơ chuẩn không có bước nào; hồ sơ làm lại, leo
#      thang, hết hạn chờ, mở lại, đặt phòng hai lần ra đúng bước, đúng thứ tự, đúng mốc UTC
#   2. Khớp kết quả toàn bộ, với CẢ HAI bộ máy: hồ sơ có loại lệch k khi và chỉ khi nó nằm trong `cases`
#      của nhánh lệch k — trên bộ dữ liệu đáp án và trên dữ liệu thật của cụm
#   3. Điểm vào HTTP: hình dạng kết quả, 404 cho hồ sơ không có, 422 cho mã sai kiểu

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from app import main
from app.du_lieu import doc_du_lieu, doc_ho_so
from app.phan_tich import NHANH_LECH, phan_tich, tuan_thu_ho_so

from . import dap_an

KHOA_KET_QUA = {"case", "deviates", "steps"}
KHOA_BUOC = {"kind", "activity", "from", "to", "from_label", "to_label", "at", "actor"}

# Hồ sơ không bước lệch nào: luồng thường (1, 14, 15, 16), đổi ưu tiên hai lần không phải đặt phòng (2),
# tự trỏ (3), chờ bổ sung rồi người đi tiếp (7), đặt phòng đúng một lần (11), ngoài khoảng (13)
HO_SO_CHUAN = (1, 2, 3, 7, 11, 13, 14, 15, 16)

# Đáp án tính tay: (loại, hoạt động, từ, đến, giờ địa phương của lịch)
DAP_AN = {
    4: [("rework", "tra-lai", "xu-ly", "cho-1", "2026-03-10 10:30:00")],
    5: [("rework", "tra-lai", "xu-ly", "cho-1", "2026-03-10 14:00:00"),
        ("rework", "tra-lai", "xu-ly", "cho-1", "2026-03-10 15:00:00")],
    6: [("escalation", "len-cap", "cho-1", "cho-2", "2026-03-11 11:00:00")],
    8: [("wait_expiry", "het-han-cho", "cho-kh", "huy", "2026-03-13 09:30:00")],
    9: [("reopen", "mo-lai", "xong", "xu-ly", "2026-03-12 14:00:00")],
    # Lần đặt phòng thứ hai, không phải lần đầu
    10: [("multiple_routing", "giao", "cho-1", "xu-ly", "2026-03-12 13:30:00")],
    # Gửi trước khoảng thử chính: kết quả một hồ sơ không lọc ngày
    12: [("rework", "tra-lai", "xu-ly", "cho-1", "2026-03-09 10:00:00")],
}

NHAN = {ma: nhan for ma, nhan, *_ in dap_an.TRANG_THAI}


def _utc(ket_noi, mui_gio: str, luc: str) -> str:
    """Mốc giờ địa phương của lịch đổi ra UTC bằng chính cơ sở dữ liệu — không giả định múi giờ."""
    gio = ket_noi.execute("SELECT %s::timestamp AT TIME ZONE %s", (luc, mui_gio)).fetchone()[0]
    return gio.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- 1. Bộ dữ liệu đáp án biết trước ---------------------------------------------------------------------


@pytest.mark.parametrize("ma", HO_SO_CHUAN)
def test_ho_so_chuan_khong_co_buoc_lech(ket_noi_thu, ma):
    kq = tuan_thu_ho_so(ma, doc_ho_so(ket_noi_thu, ma))
    assert kq == {"case": ma, "deviates": False, "steps": []}


@pytest.mark.parametrize("ma", sorted(DAP_AN))
def test_ho_so_lech_ra_dung_buoc_dung_thu_tu(ket_noi_thu, mui_gio, ma):
    kq = tuan_thu_ho_so(ma, doc_ho_so(ket_noi_thu, ma))
    assert kq["case"] == ma and kq["deviates"] is True
    assert kq["steps"] == [
        {"kind": loai, "activity": hd, "from": tu, "to": den, "from_label": NHAN[tu], "to_label": NHAN[den],
         "at": _utc(ket_noi_thu, mui_gio, luc), "actor": "nguoi-xu-ly"}
        for loai, hd, tu, den, luc in DAP_AN[ma]
    ]


def test_buoc_lech_xep_theo_thoi_gian(ket_noi_thu):
    for ma in DAP_AN:
        moc = [b["at"] for b in tuan_thu_ho_so(ma, doc_ho_so(ket_noi_thu, ma))["steps"]]
        assert moc == sorted(moc), ma


def test_ho_so_khong_co_trong_nhat_ky_cho_ket_qua_rong(ket_noi_thu):
    du_lieu = doc_ho_so(ket_noi_thu, 999)
    assert du_lieu.su_kien == [] and du_lieu.trang_thai == {}
    assert tuan_thu_ho_so(999, du_lieu) == {"case": 999, "deviates": False, "steps": []}


def test_ma_loai_lech_nam_trong_nhanh_lech(ket_noi_thu):
    for ma in DAP_AN:
        for b in tuan_thu_ho_so(ma, doc_ho_so(ket_noi_thu, ma))["steps"]:
            assert b["kind"] in NHANH_LECH
            assert set(b) == KHOA_BUOC


# --- 2. Khớp kết quả toàn bộ, với cả hai bộ máy ----------------------------------------------------------


def _loai_theo_ho_so(ket_qua: dict) -> dict[int, set[str]]:
    loai: dict[int, set[str]] = {}
    for d in ket_qua["deviations"]:
        for h in d["cases"]:
            loai.setdefault(h, set()).add(d["kind"])
    return loai


def _khop_ket_qua_toan_bo(ket_noi, ket_qua: dict) -> None:
    # Không cắt danh sách hồ sơ của nhánh lệch: so được với mọi hồ sơ
    assert all(len(d["cases"]) == d["cases_count"] for d in ket_qua["deviations"])
    theo_nhanh = _loai_theo_ho_so(ket_qua)
    # Mọi hồ sơ của kết quả (biến thể không cắt), cả hồ sơ chuẩn: hồ sơ chuẩn cũng phải không có bước nào
    moi_ho_so = set(theo_nhanh) | {h for v in ket_qua["variants"] for h in v["cases"]}
    assert ket_qua["other_variants_cases"] == 0
    for ma in sorted(moi_ho_so):
        mot = tuan_thu_ho_so(ma, doc_ho_so(ket_noi, ma))
        assert {b["kind"] for b in mot["steps"]} == theo_nhanh.get(ma, set()), ma
        assert mot["deviates"] == (ma in theo_nhanh), ma


def test_khop_nhanh_lech_tren_bo_du_lieu_dap_an(ket_noi_thu, bo_may, ma_ho_so_trong_khoang):
    du_lieu = doc_du_lieu(ket_noi_thu, *dap_an.KHOANG, None)
    ket_qua = phan_tich(du_lieu, bo_may, dap_an.cau_hinh_thu(bo_may, so_bien_the=1000))
    assert {h for v in ket_qua["variants"] for h in v["cases"]} == ma_ho_so_trong_khoang
    _khop_ket_qua_toan_bo(ket_noi_thu, ket_qua)


def test_khop_nhanh_lech_tren_du_lieu_that(ket_noi_that, bo_may):
    du_lieu = doc_du_lieu(ket_noi_that, dt.date(2020, 1, 1), dt.date(2100, 1, 1), None)
    ket_qua = phan_tich(
        du_lieu, bo_may, dap_an.cau_hinh_thu(bo_may, so_bien_the=100000, so_ho_so_moi_nhom=100000)
    )
    _khop_ket_qua_toan_bo(ket_noi_that, ket_qua)


# --- 3. Điểm vào HTTP ------------------------------------------------------------------------------------


@pytest.fixture
def khach(mui_gio):
    # `mui_gio` kéo theo bài bị bỏ qua khi không có PostgreSQL của cụm
    return TestClient(main.app)


def test_http_ho_so_khong_co_tra_404(khach):
    assert khach.get("/ho-so/999999999/tuan-thu").status_code == 404


def test_http_ma_sai_kieu_tra_422(khach):
    assert khach.get("/ho-so/khong-phai-so/tuan-thu").status_code == 422


def test_http_ho_so_that_tra_dung_hop_dong(khach, ket_noi_that):
    ma = ket_noi_that.execute("SELECT min(case_id) FROM bao_cao_nhat_ky WHERE thu_tu = 0").fetchone()[0]
    if ma is None:
        # Cụm vừa dựng, chưa có hồ sơ nào: nhật ký trống thì mọi mã đều là hồ sơ không có
        assert khach.get("/ho-so/1/tuan-thu").status_code == 404
        return
    tra_loi = khach.get(f"/ho-so/{ma}/tuan-thu")
    assert tra_loi.status_code == 200
    than = tra_loi.json()
    assert set(than) == KHOA_KET_QUA and than["case"] == ma
    assert than["deviates"] == bool(than["steps"])
    for b in than["steps"]:
        assert set(b) == KHOA_BUOC and b["kind"] in NHANH_LECH and b["at"].endswith("Z")
    # Cùng kết quả với đường gọi thẳng — điểm vào không thêm, không bớt gì
    assert than == tuan_thu_ho_so(ma, doc_ho_so(ket_noi_that, ma))
