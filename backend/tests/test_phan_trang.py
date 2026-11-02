# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
"""Phân trang, tìm và lọc phía dịch vụ của các điểm cuối danh sách (#232).

Mỗi danh sách: trang đầu, giữa, cuối không trùng và không sót; tổng số và số đếm nhóm không đổi
khi sang trang; bộ lọc không có kết quả trả rỗng; giới hạn vượt trần bị từ chối. Hồ sơ dựng cảnh
mang tiêu đề có dấu riêng của từng bài, và bài lọc theo dấu đó — cụm thử có thể sẵn hồ sơ khác.
"""

from __future__ import annotations

import uuid

import pytest

from app.models.case import Request
from app.rules.sla import gioi_han_giay
from app.workflow import phan_trang
from app.workflow.context import Actor
from app.workflow.engine import create_case, perform_transition
from app.workflow.messages import gui_loi_nhan
from tests.test_department import (  # noqa: F401 — fixture `client` dùng lại
    PHAN_LOAI,
    _cho_phong_nhan,
    _dang_xu_ly,
    _goi_bang,
    _tao,
    _truong_phong,
    client,
)


def _dau() -> str:
    """Dấu riêng của một bài — tìm theo dấu này thì chỉ ra hồ sơ của bài."""
    return f"PT{uuid.uuid4().hex[:8]}"


def _trang(client, duong_dan: str, **tham_so) -> dict:
    r = client.get(duong_dan, params=tham_so)
    assert r.status_code == 200, r.text
    return r.json()


def _di_het(client, duong_dan: str, gioi_han: int, nhom: str, **tham_so) -> list[dict]:
    """Đi hết các trang, kiểm tổng và số nhóm không đổi giữa các trang; trả mọi dòng theo thứ tự."""
    dau = _trang(client, duong_dan, limit=gioi_han, offset=0, **tham_so)
    dong = list(dau["items"])
    offset = gioi_han
    while offset < dau["total"]:
        sau = _trang(client, duong_dan, limit=gioi_han, offset=offset, **tham_so)
        assert sau["total"] == dau["total"]
        assert sau[nhom] == dau[nhom], "số đếm nhóm phải tính trên cả tập, không theo trang"
        assert len(sau["items"]) <= gioi_han
        dong += sau["items"]
        offset += gioi_han
    return dong


# ---------------------------------------------------------------------------
# Hồ sơ của tôi
# ---------------------------------------------------------------------------


def test_ho_so_cua_toi_trang_dau_giua_cuoi(session, client):
    dau = _dau()
    nguoi = Actor(id=f"kc-pt-{dau}", name="Người Phân Trang", roles=frozenset({"requester"}))
    ma = []
    for i in range(7):
        h = create_case(session, title=f"{dau} hồ sơ {i}", requester_id=nguoi.id,
                        requester_label=nguoi.label, request_type_code=None)
        ma.append(h.id)
    session.commit()
    _goi_bang(client, nguoi)

    dong = _di_het(client, "/requests", 3, "groups")
    assert [d["id"] for d in dong] == sorted(ma, reverse=True), "mới nhất trước, không trùng không sót"
    cuoi = _trang(client, "/requests", limit=3, offset=6)
    assert len(cuoi["items"]) == 1 and cuoi["total"] == 7
    assert sum(g["count"] for g in cuoi["groups"]) == 7


def test_ho_so_cua_toi_tim_theo_ma_va_loc_rong(session, client):
    dau = _dau()
    nguoi = Actor(id=f"kc-pt-{dau}", name="Người Tìm", roles=frozenset({"requester"}))
    h = create_case(session, title=f"{dau} máy chiếu", requester_id=nguoi.id,
                    requester_label=nguoi.label, request_type_code=None)
    session.commit()
    _goi_bang(client, nguoi)

    theo_ma = _trang(client, "/requests", q=f"YC-{h.created_at.year}-{h.id:04d}")
    assert [d["id"] for d in theo_ma["items"]] == [h.id]
    rong = _trang(client, "/requests", q=f"{dau}-khong-co")
    assert rong == {**rong, "items": [], "total": 0, "groups": []}


def test_ho_so_cua_toi_nhom_mang_co_ket_thuc(session, client):
    """Trang chủ tách "hồ sơ đang mở" khỏi đã đóng bằng cờ trên nhóm, không tự biết mã trạng thái."""
    dau = _dau()
    nguoi = Actor(id=f"kc-pt-{dau}", name="Người Hủy", roles=frozenset({"requester"}))
    con_mo = create_case(session, title=f"{dau} còn mở", requester_id=nguoi.id,
                         requester_label=nguoi.label, request_type_code=None)
    da_huy = create_case(session, title=f"{dau} đã hủy", requester_id=nguoi.id,
                         requester_label=nguoi.label, request_type_code=None)
    perform_transition(session, case_id=da_huy.id, to_state="cancelled", actor=nguoi)
    session.commit()
    _goi_bang(client, nguoi)

    ds = _trang(client, "/requests")
    ket_thuc = {s["code"]: s["is_terminal"] for s in client.get("/states").json()}
    assert {g["code"]: g["is_terminal"] for g in ds["groups"]} == {
        con_mo.current_state: ket_thuc[con_mo.current_state],
        da_huy.current_state: True,
    }
    assert ds["open_count"] == 1 and ds["total"] == 2


def test_tim_khong_phan_biet_dau_va_hoa_thuong(session, client):
    """Như ô tìm trên trình duyệt trước #232: "may in" ra "Máy in", cả trong SQL lẫn Python."""
    dau = _dau()
    nguoi = Actor(id=f"kc-pt-{dau}", name="Người Gõ Không Dấu", roles=frozenset({"requester"}))
    h = create_case(session, title=f"{dau} Máy in Đà Nẵng kẹt giấy", requester_id=nguoi.id,
                    requester_label=nguoi.label, request_type_code=None)
    gui_loi_nhan(session, h, nguoi, "message", "Nhờ xem giúp")
    session.commit()
    _goi_bang(client, nguoi)

    for khoa in ("may in da nang", "MÁY IN đà nẵng", "Máy In"):
        assert [d["id"] for d in _trang(client, "/requests", q=f"{dau} {khoa}")["items"]] == [h.id], khoa
        assert [c["case_id"] for c in _trang(client, "/inbox", q=f"{dau} {khoa}")["items"]] == [h.id], khoa
    # Ký tự đại diện của LIKE trong chuỗi tìm là chữ thường, không phải ký tự đại diện
    assert _trang(client, "/requests", q=f"{dau}%")["total"] == 0


def test_bang_bo_dau_sql_khop_ban_python():
    """Bảng `translate` của SQL và hàm bỏ dấu Python phải cho cùng kết quả trên mọi ký tự."""
    assert len(phan_trang._CO_DAU) == len(phan_trang._KHONG_DAU)
    for co, khong in zip(phan_trang._CO_DAU, phan_trang._KHONG_DAU, strict=True):
        assert phan_trang.bo_dau(co) == khong, co


@pytest.mark.parametrize("gioi_han", [0, 201])
def test_gioi_han_ngoai_khoang_bi_tu_choi(client, gioi_han):
    for duong_dan in ("/requests", "/inbox", "/department/queue"):
        assert client.get(duong_dan, params={"limit": gioi_han}).status_code == 422, duong_dan


def test_mac_dinh_co_gioi_han(client):
    """Không điểm cuối danh sách nào trả cả tập khi người gọi không nói gì."""
    for duong_dan in ("/requests", "/inbox", "/department/queue"):
        assert _trang(client, duong_dan)["limit"] == 50, duong_dan


# ---------------------------------------------------------------------------
# Hàng đợi
# ---------------------------------------------------------------------------


def test_hang_doi_phong_ban_phan_trang_va_nhom_do_gap(session, client, phong_ban):
    dau = _dau()
    # Hai nhóm độ gấp khác nhau: ba hồ sơ đồng hồ đang chạy, hai hồ sơ chờ phòng nhận
    ma = {_dang_xu_ly(session, phong_ban, f"{dau} việc {i}").id for i in range(3)}
    ma |= {_cho_phong_nhan(session, phong_ban, f"{dau} chờ nhận {i}").id for i in range(2)}
    session.commit()
    _goi_bang(client, _truong_phong(phong_ban))

    dong = _di_het(client, "/department/queue", 2, "urgency_groups", q=dau)
    assert {d["id"] for d in dong} == ma
    nhom = _trang(client, "/department/queue", q=dau)["urgency_groups"]
    assert sum(g["count"] for g in nhom) == 5
    assert len(nhom) == 2
    # Mỗi dòng mang mã nhóm, và lọc theo nhóm ra đúng các dòng đó
    for g in nhom:
        theo_nhom = _trang(client, "/department/queue", q=dau, group=g["code"])
        assert theo_nhom["total"] == g["count"]
        assert all(d["urgency"] == g["code"] for d in theo_nhom["items"])
        # Dải lọc vẫn kể đủ mọi nhóm khi đang đứng ở một nhóm
        assert theo_nhom["urgency_groups"] == nhom


def test_hang_doi_dieu_phoi_phan_trang_va_chi_viec_cho_toi(session, client):
    dau = _dau()
    ma = {_tao(session, f"{dau} yêu cầu {i}").id for i in range(4)}
    session.commit()
    _goi_bang(client, PHAN_LOAI)

    dong = _di_het(client, "/coordination/queue", 3, "groups", q=dau)
    assert {d["id"] for d in dong} == ma
    cho_toi = _trang(client, "/coordination/queue", q=dau, needs_action="true")
    assert cho_toi["total"] == 4 and all(d["needs_my_action"] for d in cho_toi["items"])
    assert _trang(client, "/coordination/queue", q=f"{dau}-khong-co")["total"] == 0


def test_hang_doi_dieu_phoi_loc_theo_phong_va_dem_qua_han(session, client, phong_ban):
    dau = _dau()
    chua_phong = _tao(session, f"{dau} chưa có phòng")
    co_phong = _cho_phong_nhan(session, phong_ban, f"{dau} đã chuyển phòng")
    co_phong.sla_running_seconds = gioi_han_giay(session, co_phong) + 60
    session.commit()
    _goi_bang(client, PHAN_LOAI)

    theo_phong = _trang(client, "/coordination/queue", q=dau, department=phong_ban)
    assert [d["id"] for d in theo_phong["items"]] == [co_phong.id]
    assert _trang(client, "/coordination/queue", q=dau, department="khong-co-phong")["total"] == 0
    # Dòng phụ "quá hạn" trên dải lọc đếm ở dịch vụ, theo từng trạng thái
    nhom = {g["code"]: g for g in _trang(client, "/coordination/queue", q=dau)["groups"]}
    assert nhom[co_phong.current_state]["overdue"] == 1
    assert nhom[chua_phong.current_state]["overdue"] == 0
    # Xếp "gấp": hồ sơ quá hạn lên trước dù vào hàng đợi sau
    gap = _trang(client, "/coordination/queue", q=dau, sort="gap")
    assert [d["id"] for d in gap["items"]] == [co_phong.id, chua_phong.id]


def test_hang_doi_phong_ban_moi_cach_xep_deu_theo_thu_tu_nhom(session, client, phong_ban):
    """Giao diện chia trang thành nhóm, nên trang sau phải nối tiếp đúng nhóm trang trước."""
    dau = _dau()
    for i in range(2):
        _dang_xu_ly(session, phong_ban, f"{dau} đang làm {i}")
    for i in range(2):
        _cho_phong_nhan(session, phong_ban, f"{dau} chờ nhận {i}")  # tạo sau: mới hơn
    session.commit()
    _goi_bang(client, _truong_phong(phong_ban))

    for cach in ("gap", "cho", "moi"):
        dong = _di_het(client, "/department/queue", 1, "urgency_groups", q=dau, sort=cach)
        thu_tu = [g["code"] for g in _trang(client, "/department/queue", q=dau)["urgency_groups"]]
        nhom_theo_dong = [d["urgency"] for d in dong]
        assert nhom_theo_dong == sorted(nhom_theo_dong, key=thu_tu.index), cach


def test_hang_doi_phong_ban_loc_theo_loai(session, client, phong_ban):
    dau = _dau()
    h = _cho_phong_nhan(session, phong_ban, f"{dau} cần nhận")
    session.commit()
    _goi_bang(client, _truong_phong(phong_ban))

    dung_loai = _trang(client, "/department/queue", q=dau, request_type=h.request_type_code)
    assert [d["id"] for d in dung_loai["items"]] == [h.id]
    assert _trang(client, "/department/queue", q=dau, request_type="khong-co-loai")["total"] == 0


# ---------------------------------------------------------------------------
# Hộp thư
# ---------------------------------------------------------------------------


def test_hop_thu_phan_trang_moi_nhat_truoc(session, client):
    dau = _dau()
    nguoi = Actor(id=f"kc-pt-{dau}", name="Người Nhắn", roles=frozenset({"requester"}))
    ma = []
    for i in range(3):
        h = create_case(session, title=f"{dau} trao đổi {i}", requester_id=nguoi.id,
                        requester_label=nguoi.label, request_type_code=None)
        gui_loi_nhan(session, h, nguoi, "message", f"Lời nhắn {i}")
        ma.append(h.id)
    session.commit()
    _goi_bang(client, nguoi)

    dau_trang = _trang(client, "/inbox", limit=2, q=dau)
    cuoi_trang = _trang(client, "/inbox", limit=2, offset=2, q=dau)
    assert dau_trang["total"] == cuoi_trang["total"] == 3
    thu_tu = [c["case_id"] for c in dau_trang["items"] + cuoi_trang["items"]]
    assert thu_tu == list(reversed(ma)), "lời nhắn mới nhất lên đầu, không trùng không sót"
    assert _trang(client, "/inbox", q=f"{dau}-khong-co")["items"] == []


def test_hop_thu_chip_chua_doc_va_mo_dung_ho_so(session, client):
    dau = _dau()
    nguoi = Actor(id=f"kc-pt-{dau}", name="Người Chờ Đáp", roles=frozenset({"requester"}))
    ma = []
    for i in range(3):
        h = create_case(session, title=f"{dau} hỏi {i}", requester_id=nguoi.id,
                        requester_label=nguoi.label, request_type_code=None)
        gui_loi_nhan(session, h, nguoi, "message", f"Hỏi {i}")
        ma.append(h.id)
    # Điều phối viên trả lời hồ sơ đầu: người gửi có đúng một cuộc chưa đọc
    gui_loi_nhan(session, session.get(Request, ma[0]), PHAN_LOAI, "message", "Đã nhận")
    session.commit()
    _goi_bang(client, nguoi)

    tat_ca = _trang(client, "/inbox", q=dau, limit=1)
    assert tat_ca["unread_conversations"] == 1 and tat_ca["internal_conversations"] == 0
    chua_doc = _trang(client, "/inbox", q=dau, unread="true")
    assert [c["case_id"] for c in chua_doc["items"]] == [ma[0]]
    # Số trên chip không đổi khi đang đứng ở chip nào
    assert chua_doc["unread_conversations"] == 1
    assert _trang(client, "/inbox", q=dau, internal="true")["unread_conversations"] == 1
    # Cuộc đang mở không nằm ở trang đầu: hỏi riêng theo hồ sơ
    rieng = _trang(client, "/inbox", case_id=ma[1])
    assert [c["case_id"] for c in rieng["items"]] == [ma[1]]
