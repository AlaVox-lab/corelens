# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử đánh giá mức hài lòng khi người gửi xác nhận hồ sơ hoàn tất (#433).
#
# Điều cốt lõi: điểm đi CÙNG lần xác nhận nhưng không qua engine, không vào nhật ký sự kiện, không chạm trường
# quyết định nào (ADR-0005). Mỗi lần xác nhận có chấm đúng một dòng `case_feedback` gắn đúng dòng nhật ký của
# lần đó; bị từ chối thì hồ sơ đứng nguyên. Cạnh nào cho chấm là dữ liệu — bài tra cờ `collects_feedback`
# từ bộ quy tắc, không viết mã hoạt động. Mọi hồ sơ do bài tự tạo.

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app.auth.dependencies import current_actor
from app.cau_hinh.bo_quy_tac import sao_chep
from app.config import Settings
from app.db import get_session
from app.main import app
from app.models.case import CaseFeedback, EventLog, Request
from app.models.workflow_config import Priority, RequestType, Transition
from app.workflow import danh_gia
from app.workflow.context import Actor
from app.workflow.engine import allowed_transitions, create_case, perform_transition
from app.workflow.escalation import TAC_NHAN_HAN_CHO

pytestmark = pytest.mark.usefixtures("lich_ca_ngay")

NGUOI_GUI = Actor(id="nd-gui-433", name="An Nguyễn", roles=frozenset({"requester"}))
NGUOI_KHAC = Actor(id="nd-khac-433", name="Người Khác", roles=frozenset({"requester"}))
DIEU_PHOI = Actor(id="nd-dp-433", name="Bình Trần", roles=frozenset({"classifier"}))


def _truong_phong(phong: str) -> Actor:
    return Actor(id="nd-tp-433", name="Dũng Phạm", roles=frozenset({"approver"}), departments=frozenset({phong}))


def _xu_ly(phong: str) -> Actor:
    return Actor(id="nd-xl-433", name="Cường Lê", roles=frozenset({"handler"}), departments=frozenset({phong}))


@pytest.fixture
def client(session):
    dang_goi = {"actor": NGUOI_GUI}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: dang_goi["actor"]
    with TestClient(app) as c:
        c.dang_goi = dang_goi
        yield c
    app.dependency_overrides.clear()


def _hoan_tat(session, phong: str) -> Request:
    """Một hồ sơ của NGUOI_GUI tới trạng thái chờ người gửi xác nhận."""
    loai = session.scalars(select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)).first()
    uu_tien = session.scalar(select(Priority.code).where(Priority.is_default))
    ho_so = create_case(session, title="Hồ sơ thử đánh giá", requester_id=NGUOI_GUI.id, requester_label=NGUOI_GUI.label)
    for den, actor, changes in (
        ("classified", DIEU_PHOI, {"priority_code": uu_tien, "request_type_code": loai}),
        ("awaiting-acceptance", DIEU_PHOI, {"department_code": phong}),
        ("in-progress", _truong_phong(phong), {}),
        ("completed", _xu_ly(phong), {}),
    ):
        perform_transition(session, case_id=ho_so.id, to_state=den, actor=actor, changes=changes)
    session.commit()
    return ho_so


def _canh_cham(session, ho_so) -> Transition:
    """Cạnh cho chấm mà người gửi đi được ở trạng thái hiện tại — tra từ dữ liệu."""
    return next(c for c in allowed_transitions(session, ho_so, NGUOI_GUI) if c.collects_feedback)


def _canh_khong_cham(session, ho_so) -> Transition:
    """Cạnh người gửi đi được mà KHÔNG cho chấm (ví dụ "Mở lại, chưa đạt")."""
    return next(c for c in allowed_transitions(session, ho_so, NGUOI_GUI) if not c.collects_feedback)


def _so_dong(session, bang, ma: int) -> int:
    return session.scalar(select(func.count()).select_from(bang).where(bang.case_id == ma))


def _xac_nhan(client, session, ho_so, feedback=None):
    than = {"to_state": _canh_cham(session, ho_so).to_state}
    if feedback is not None:
        than["feedback"] = feedback
    return client.post(f"/requests/{ho_so.id}/transitions", json=than)


def test_cung_cap_co_cham_tren_canh_cua_nguoi_gui(client, session, rule_set, phong_ban):
    ho_so = _hoan_tat(session, phong_ban)
    r = client.get(f"/requests/{ho_so.id}").json()
    cham = {c["to_state"]: c["collects_feedback"] for c in r["allowed_transitions"]}
    assert cham[_canh_cham(session, ho_so).to_state] is True
    assert cham[_canh_khong_cham(session, ho_so).to_state] is False
    assert r["feedback"] == []
    assert r["feedback_comment_max_chars"] == danh_gia.get_settings().feedback_comment_max_chars


def test_xac_nhan_kem_diem_ghi_mot_dong_gan_dung_su_kien(client, session, rule_set, phong_ban):
    ho_so = _hoan_tat(session, phong_ban)
    r = _xac_nhan(client, session, ho_so, {"score": 4, "comment": "  Xử lý nhanh, cảm ơn.  "})
    assert r.status_code == 200, r.text
    assert r.json()["feedback"][0]["score"] == 4

    dong = session.scalars(select(CaseFeedback).where(CaseFeedback.case_id == ho_so.id)).all()
    assert len(dong) == 1
    su_kien = session.get(EventLog, dong[0].event_id)
    canh_cham = session.scalars(select(Transition).where(Transition.collects_feedback, Transition.rule_set_id == ho_so.rule_set_id)).all()
    assert su_kien.case_id == ho_so.id
    assert (su_kien.activity, su_kien.from_state, su_kien.to_state) in {
        (c.activity_code, c.from_state, c.to_state) for c in canh_cham
    }
    assert dong[0].comment == "Xử lý nhanh, cảm ơn."
    # Điểm không vào nhật ký: dòng xác nhận không mang điểm hay nhận xét
    assert "nhanh" not in json.dumps(su_kien.changes or {}, ensure_ascii=False)
    assert "score" not in json.dumps(su_kien.changes or {})


def test_xac_nhan_khong_cham_van_di_nhu_cu(client, session, rule_set, phong_ban):
    ho_so = _hoan_tat(session, phong_ban)
    den = _canh_cham(session, ho_so).to_state
    r = _xac_nhan(client, session, ho_so)
    assert r.status_code == 200, r.text
    assert r.json()["state"]["code"] == den
    assert r.json()["feedback"] == []
    assert _so_dong(session, CaseFeedback, ho_so.id) == 0


@pytest.mark.parametrize("feedback", [{"score": 0}, {"score": 6}, {"score": 3, "comment": "x" * 1001}])
def test_diem_ngoai_1_5_hay_nhan_xet_qua_dai_bi_tu_choi(client, session, rule_set, phong_ban, monkeypatch, feedback):
    monkeypatch.setattr(danh_gia, "get_settings", lambda: Settings(feedback_comment_max_chars=1000))
    ho_so = _hoan_tat(session, phong_ban)
    truoc = (ho_so.current_state, _so_dong(session, EventLog, ho_so.id))
    r = _xac_nhan(client, session, ho_so, feedback)
    assert r.status_code == 422
    session.expire_all()
    assert (session.get(Request, ho_so.id).current_state, _so_dong(session, EventLog, ho_so.id)) == truoc
    assert _so_dong(session, CaseFeedback, ho_so.id) == 0


def test_cham_o_canh_khong_cho_cham_bi_tu_choi(client, session, rule_set, phong_ban):
    ho_so = _hoan_tat(session, phong_ban)
    canh = _canh_khong_cham(session, ho_so)
    truoc = (ho_so.current_state, _so_dong(session, EventLog, ho_so.id))
    r = client.post(
        f"/requests/{ho_so.id}/transitions",
        json={"to_state": canh.to_state, "note": "Máy vẫn hỏng.", "feedback": {"score": 2}},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "feedback-not-accepted"
    session.expire_all()
    assert (session.get(Request, ho_so.id).current_state, _so_dong(session, EventLog, ho_so.id)) == truoc
    assert _so_dong(session, CaseFeedback, ho_so.id) == 0


def test_mo_lai_roi_xac_nhan_lan_hai_giu_ca_hai_view_lay_moi_nhat(client, session, rule_set, phong_ban):
    ho_so = _hoan_tat(session, phong_ban)
    assert _xac_nhan(client, session, ho_so, {"score": 2, "comment": "Chưa ổn"}).status_code == 200

    # Mở lại từ trạng thái vừa đóng, xử lý lại, rồi xác nhận lần hai
    session.expire_all()
    ho_so = session.get(Request, ho_so.id)
    mo_lai = next(c for c in allowed_transitions(session, ho_so, NGUOI_GUI) if c.requires_note)
    r = client.post(f"/requests/{ho_so.id}/transitions", json={"to_state": mo_lai.to_state, "note": "Lại hỏng."})
    assert r.status_code == 200, r.text
    perform_transition(session, case_id=ho_so.id, to_state="completed", actor=_xu_ly(phong_ban))
    session.commit()
    session.expire_all()
    ho_so = session.get(Request, ho_so.id)
    assert _xac_nhan(client, session, ho_so, {"score": 5}).status_code == 200

    dong = session.scalars(select(CaseFeedback).where(CaseFeedback.case_id == ho_so.id).order_by(CaseFeedback.id)).all()
    assert [d.score for d in dong] == [2, 5]
    assert dong[0].event_id != dong[1].event_id
    assert [f["score"] for f in client.get(f"/requests/{ho_so.id}").json()["feedback"]] == [2, 5]

    bao_cao = session.execute(
        text("SELECT diem, da_cham, ma_phong FROM bao_cao_hai_long WHERE ma_ho_so = :ma"), {"ma": ho_so.id}
    ).all()
    assert [tuple(d) for d in bao_cao] == [(5, True, phong_ban)]


def test_view_co_dong_khi_xac_nhan_khong_cham_khong_co_dong_khi_tu_dong(client, session, rule_set, phong_ban):
    khong_cham = _hoan_tat(session, phong_ban)
    assert _xac_nhan(client, session, khong_cham).status_code == 200

    tu_dong = _hoan_tat(session, phong_ban)
    canh_he_thong = session.scalars(
        select(Transition).where(
            Transition.rule_set_id == tu_dong.rule_set_id,
            Transition.from_state == tu_dong.current_state,
            Transition.is_system,
        )
    ).first()
    assert canh_he_thong is not None and not canh_he_thong.collects_feedback
    perform_transition(session, case_id=tu_dong.id, to_state=canh_he_thong.to_state, actor=Actor.system(TAC_NHAN_HAN_CHO))
    session.commit()

    dong = dict(
        session.execute(
            text("SELECT ma_ho_so, da_cham FROM bao_cao_hai_long WHERE ma_ho_so IN (:a, :b)"),
            {"a": khong_cham.id, "b": tu_dong.id},
        ).all()
    )
    # Tự đóng không có dòng, nên không vào mẫu số của tỷ lệ được chấm
    assert dong == {khong_cham.id: False}


def test_khong_ghi_truong_quyet_dinh_hay_goi_y(client, session, rule_set, phong_ban):
    ho_so = _hoan_tat(session, phong_ban)
    cot = ("request_type_code", "priority_code", "department_code", "assignee_id", "suggested_request_type_code",
           "suggested_priority_code", "suggested_department_code", "suggested_assignee_id")
    truoc = {c: getattr(ho_so, c) for c in cot}
    assert _xac_nhan(client, session, ho_so, {"score": 3, "comment": "Tạm ổn"}).status_code == 200
    session.expire_all()
    ho_so = session.get(Request, ho_so.id)
    assert {c: getattr(ho_so, c) for c in cot} == truoc
    dong = session.scalars(select(EventLog).where(EventLog.case_id == ho_so.id).order_by(EventLog.id.desc())).first()
    assert dong.changes in (None, {})


def test_dieu_phoi_va_phong_ban_thay_danh_gia_nguoi_khac_khong(client, session, rule_set, phong_ban):
    ho_so = _hoan_tat(session, phong_ban)
    assert _xac_nhan(client, session, ho_so, {"score": 4, "comment": "Tốt"}).status_code == 200

    client.dang_goi["actor"] = DIEU_PHOI
    dp = client.get(f"/coordination/requests/{ho_so.id}").json()["feedback"]
    assert [(f["score"], f["comment"]) for f in dp] == [(4, "Tốt")]

    client.dang_goi["actor"] = _truong_phong(phong_ban)
    pb = client.get(f"/department/requests/{ho_so.id}").json()["feedback"]
    assert [(f["score"], f["comment"]) for f in pb] == [(4, "Tốt")]

    client.dang_goi["actor"] = NGUOI_KHAC
    assert client.get(f"/requests/{ho_so.id}").status_code == 404


def test_lo_i_ghi_diem_thi_hoan_tac_ca_lan_chuyen(client, session, rule_set, phong_ban, monkeypatch):
    """Cùng giao dịch: ghi điểm hỏng thì lần xác nhận cũng không còn."""
    ho_so = _hoan_tat(session, phong_ban)
    truoc = (ho_so.current_state, _so_dong(session, EventLog, ho_so.id))

    def hong(*_a, **_k):
        raise RuntimeError("ghi điểm hỏng")

    monkeypatch.setattr("app.workflow.routes.ghi_danh_gia", hong)
    with pytest.raises(RuntimeError):
        _xac_nhan(client, session, ho_so, {"score": 4})
    session.rollback()
    session.expire_all()
    assert (session.get(Request, ho_so.id).current_state, _so_dong(session, EventLog, ho_so.id)) == truoc


def test_sao_chep_bo_quy_tac_giu_co_cham(session, rule_set):
    moi = sao_chep(session, rule_set.id, "thu-433-chep", "Bộ chép thử #433")
    cu = {(c.from_state, c.to_state, c.is_system) for c in session.scalars(
        select(Transition).where(Transition.rule_set_id == rule_set.id, Transition.collects_feedback))}
    sau = {(c.from_state, c.to_state, c.is_system) for c in session.scalars(
        select(Transition).where(Transition.rule_set_id == moi, Transition.collects_feedback))}
    assert cu, "bộ quy tắc mẫu phải có ít nhất một cạnh cho chấm"
    assert sau == cu


# ---------------------------------------------------------------------------
# Nhãn mốc dòng thời gian khi một cặp trạng thái có nhiều cạnh (#526)
# ---------------------------------------------------------------------------


def _moc_cuoi(client, duong: str) -> dict:
    return client.get(duong).json()["history"][-1]


def _canh_da_di(session, ho_so) -> Transition:
    """Cạnh của dòng nhật ký cuối — tra từ bảng `transitions` bằng đúng mã hoạt động đã ghi."""
    e = session.scalars(select(EventLog).where(EventLog.case_id == ho_so.id).order_by(EventLog.id.desc())).first()
    return session.scalars(
        select(Transition).where(
            Transition.rule_set_id == ho_so.rule_set_id,
            Transition.from_state == e.from_state,
            Transition.to_state == e.to_state,
            Transition.activity_code == e.activity,
        )
    ).one()


def test_moc_xac_nhan_mang_nhan_canh_nguoi_gui_khong_phai_canh_he_thong(client, session, rule_set, phong_ban):
    ho_so = _hoan_tat(session, phong_ban)
    canh = _canh_cham(session, ho_so)
    # Cặp trạng thái này có cả cạnh hệ thống mang nhãn khác — đúng điều kiện của lỗi #526
    cung_cap = session.scalars(select(Transition).where(
        Transition.rule_set_id == ho_so.rule_set_id,
        Transition.from_state == canh.from_state,
        Transition.to_state == canh.to_state,
    )).all()
    assert len({c.activity_label for c in cung_cap}) > 1
    assert _xac_nhan(client, session, ho_so).status_code == 200

    for nguoi, duong in ((NGUOI_GUI, f"/requests/{ho_so.id}"), (DIEU_PHOI, f"/coordination/requests/{ho_so.id}")):
        client.dang_goi["actor"] = nguoi
        moc = _moc_cuoi(client, duong)
        assert (moc["activity"], moc["activity_label"], moc["note_label"]) == (
            canh.activity_code, canh.activity_label, canh.note_label
        )


def test_moc_tu_dong_mang_nhan_canh_he_thong(client, session, rule_set, phong_ban):
    ho_so = _hoan_tat(session, phong_ban)
    he_thong = session.scalars(select(Transition).where(
        Transition.rule_set_id == ho_so.rule_set_id,
        Transition.from_state == ho_so.current_state,
        Transition.is_system,
    )).first()
    perform_transition(session, case_id=ho_so.id, to_state=he_thong.to_state, actor=Actor.system(TAC_NHAN_HAN_CHO))
    session.commit()
    canh = _canh_da_di(session, ho_so)
    assert canh.id == he_thong.id

    moc = _moc_cuoi(client, f"/requests/{ho_so.id}")
    assert (moc["activity"], moc["activity_label"], moc["note_label"]) == (
        he_thong.activity_code, he_thong.activity_label, he_thong.note_label
    )
