# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử cập nhật thời gian thực (#387).
#
# Bốn điều phải canh:
#
#   Nguồn     — trigger của bản sửa 0030 có mặt trên `requests` và `case_messages`, gửi đúng kênh.
#   Quyền     — chỉ đẩy mã hồ sơ người giữ luồng mở được: người gửi khác, phòng khác không nhận.
#   Khuôn     — khung SSE đúng định dạng; không có tín hiệu thì gửi dòng giữ kết nối; luồng tự dừng.
#   Biên      — thiếu token là 401, đủ số luồng là 503.
#
# NOTIFY chỉ phát khi giao dịch commit, mà mỗi bài ở đây chạy trong giao dịch bị hoàn tác (conftest.py). Vì
# vậy phần phát luồng được kiểm với nguồn tín hiệu giả; phần trigger được kiểm bằng danh mục của PostgreSQL.

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app import thoi_gian_thuc
from app.auth.dependencies import current_actor
from app.db import get_session
from app.main import app
from app.models.case import Request
from app.models.workflow_config import Priority, RequestType
from app.thoi_gian_thuc import KENH, khung, mo_duoc, phat_luong
from app.workflow.context import Actor
from app.workflow.engine import create_case, perform_transition

NGUOI_GUI = Actor(id="kc-gui-01", name="An Nguyễn", roles=frozenset({"requester"}))
NGUOI_GUI_KHAC = Actor(id="kc-gui-02", name="Chi Lê", roles=frozenset({"requester"}))
PHAN_LOAI = Actor(id="kc-pl-01", name="Bình Trần", roles=frozenset({"classifier"}))


def _truong_phong(phong: str) -> Actor:
    return Actor(id="kc-tp-01", name="Dung Phạm", roles=frozenset({"approver"}),
                 departments=frozenset({phong}))


def _tao(session) -> Request:
    loai = session.scalars(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    return create_case(
        session, title="Máy chiếu phòng họp không nhận tín hiệu", requester_id=NGUOI_GUI.id,
        requester_label=NGUOI_GUI.label, request_type_code=loai,
    )


def _toi_phong(session, phong: str) -> Request:
    ho_so = _tao(session)
    uu_tien = session.scalars(select(Priority.code).order_by(Priority.display_order)).first()
    perform_transition(session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
                       changes={"priority_code": uu_tien})
    perform_transition(session, case_id=ho_so.id, to_state="awaiting-acceptance",
                       actor=PHAN_LOAI, changes={"department_code": phong})
    return ho_so


def _gom(luong) -> list[str]:
    async def chay():
        return [phan async for phan in luong]

    return asyncio.run(chay())


def _nguon_gia(cac_dot: list[list[int]]):
    """Nguồn tín hiệu giả: mỗi lần chờ trả một đợt mã; hết đợt thì trả rỗng như khi hết hạn chờ."""
    con_lai = list(cac_dot)

    async def cho(_han_giay: float) -> list[int]:
        return con_lai.pop(0) if con_lai else []

    return cho


# ---------------------------------------------------------------------------
# Nguồn
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bang", ["requests", "case_messages"])
def test_trigger_bao_thay_doi_co_tren_bang(session, bang):
    co = session.scalar(
        text(
            "SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
            "WHERE c.relname = :bang AND t.tgname = 'bao_thay_doi_ho_so' AND NOT t.tgisinternal"
        ),
        {"bang": bang},
    )
    assert co == 1


def test_ham_trigger_gui_dung_kenh(session):
    nguon = session.scalar(text("SELECT prosrc FROM pg_proc WHERE proname = 'bao_thay_doi_ho_so'"))
    assert f"pg_notify('{KENH}'" in nguon


# ---------------------------------------------------------------------------
# Quyền
# ---------------------------------------------------------------------------


def test_nguoi_gui_mo_duoc_ho_so_cua_minh_nguoi_khac_thi_khong(session, rule_set):
    ho_so = _tao(session)
    session.flush()

    assert mo_duoc(session, NGUOI_GUI, ho_so.id)
    assert not mo_duoc(session, NGUOI_GUI_KHAC, ho_so.id)
    assert mo_duoc(session, PHAN_LOAI, ho_so.id)


def test_chi_phong_cua_ho_so_mo_duoc(session, rule_set, phong_ban):
    ho_so = _toi_phong(session, phong_ban)
    session.flush()

    assert mo_duoc(session, _truong_phong(phong_ban), ho_so.id)
    assert not mo_duoc(session, _truong_phong(f"{phong_ban}-khac"), ho_so.id)


def test_ma_khong_ton_tai_khong_mo_duoc(session, rule_set):
    assert not mo_duoc(session, PHAN_LOAI, 987_654_321)


def test_luong_loc_theo_quyen_cua_nguoi_giu_luong(session, rule_set):
    cua_an = _tao(session)
    session.flush()

    def loc(actor, cac_ma):
        return [ma for ma in dict.fromkeys(cac_ma) if mo_duoc(session, actor, ma)]

    def phat(actor):
        return _gom(phat_luong(actor, _nguon_gia([[cua_an.id, cua_an.id]]),
                               nhip_giu_giay=0.01, han_doi_giay=0.05, loc=loc))

    cua_toi = [p for p in phat(NGUOI_GUI) if p.startswith("event: ho-so")]
    cua_nguoi_khac = [p for p in phat(NGUOI_GUI_KHAC) if p.startswith("event: ho-so")]

    # Hai tín hiệu trùng mã gộp làm một
    assert cua_toi == [khung("ho-so", {"case_id": cua_an.id})]
    assert cua_nguoi_khac == []


# ---------------------------------------------------------------------------
# Khuôn
# ---------------------------------------------------------------------------


def test_khung_sse_dung_dinh_dang():
    assert khung("ho-so", {"case_id": 7}) == 'event: ho-so\ndata: {"case_id": 7}\n\n'


def test_luong_chao_giu_ket_noi_roi_tu_dung():
    cac_phan = _gom(phat_luong(NGUOI_GUI, _nguon_gia([]), nhip_giu_giay=0.01, han_doi_giay=0.05,
                               loc=lambda _a, ma: ma))

    assert cac_phan[0].startswith("retry: 3000\n")
    assert "event: san-sang" in cac_phan[0]
    assert cac_phan[1:] and all(p == ": giu-ket-noi\n\n" for p in cac_phan[1:])


# ---------------------------------------------------------------------------
# Biên
# ---------------------------------------------------------------------------


def test_khong_token_401():
    with TestClient(app) as may_khach:
        assert may_khach.get("/me/stream").status_code == 401


def test_du_so_luong_thi_503(session, monkeypatch):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: NGUOI_GUI
    monkeypatch.setattr(thoi_gian_thuc, "_so_luong_dang_mo", 10_000)
    try:
        with TestClient(app) as may_khach:
            tra = may_khach.get("/me/stream")
    finally:
        app.dependency_overrides.clear()

    assert tra.status_code == 503
    assert tra.json()["detail"]["code"] == "realtime-busy"
