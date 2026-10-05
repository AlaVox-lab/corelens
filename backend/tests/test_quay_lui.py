# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử đếm quay lui theo cạnh làm lại (#153).
#
# "Quay lui" là hồ sơ bị đẩy ngược để làm lại — đi qua cạnh mang cờ `is_rework` trong dữ
# liệu. Đáp án là bảng navigator chốt ngày 02/10/2026 từ lượt chạy tay:
#
#   B2  hỏi thêm rồi người gửi trả lời       → 0   (đi vòng rồi về, không phải làm lại)
#   C1  phòng trả một lần, định tuyến lại    → 1
#   C6  phòng trả hai lần                    → 2
#   C5  leo thang rồi phân công lại          → 0   (chỉ đổi người làm)
#   C3  người gửi mở lại vì chưa đạt         → 1
#   sửa nội dung sau khi đã phân loại        → 1
#
# Mỗi tình huống dựng qua đúng các cạnh thật, rồi đọc lịch sử qua điểm cuối của người gửi —
# đúng thứ dòng thời gian nhận.

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.dependencies import current_actor
from app.db import get_session
from app.main import app
from app.models.case import Request
from app.models.workflow_config import Priority, RequestType, Transition
from app.workflow.context import Actor
from app.workflow.engine import create_case, perform_transition

NGUOI_GUI = Actor(id="ql-gui-01", name="An Nguyễn", roles=frozenset({"requester"}))
PHAN_LOAI = Actor(id="ql-pl-01", name="Bình Trần", roles=frozenset({"classifier"}))


def _truong_phong(phong: str) -> Actor:
    return Actor(id="ql-tp-01", name="Dung Phạm", roles=frozenset({"approver"}),
                 departments=frozenset({phong}))


def _xu_ly(phong: str) -> Actor:
    return Actor(id="ql-xl-01", name="Cường Lê", roles=frozenset({"handler"}),
                 departments=frozenset({phong}))


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: NGUOI_GUI
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _chuyen(session, ho_so: Request, den: str, actor: Actor, **kem) -> None:
    perform_transition(session, case_id=ho_so.id, to_state=den, actor=actor, **kem)


def _tao_va_phan_loai(session) -> Request:
    loai = session.scalars(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    ho_so = create_case(session, title="Máy in tầng ba kẹt giấy", requester_id=NGUOI_GUI.id,
                        requester_label=NGUOI_GUI.label, request_type_code=loai)
    uu_tien = session.scalars(select(Priority.code).order_by(Priority.display_order)).first()
    _chuyen(session, ho_so, "classified", PHAN_LOAI, changes={"priority_code": uu_tien})
    return ho_so


def _ve_phong(session, ho_so: Request, phong: str) -> None:
    _chuyen(session, ho_so, "awaiting-acceptance", PHAN_LOAI, changes={"department_code": phong})


def _so_quay_lui(client, ho_so: Request) -> int:
    lich_su = client.get(f"/requests/{ho_so.id}").json()["history"]
    return sum(1 for e in lich_su if e["is_rework"])


def test_hoi_them_roi_tra_loi_khong_phai_quay_lui(client, session, rule_set, phong_ban):
    """B2."""
    ho_so = _tao_va_phan_loai(session)
    _ve_phong(session, ho_so, phong_ban)
    _chuyen(session, ho_so, "in-progress", _truong_phong(phong_ban))
    _chuyen(session, ho_so, "awaiting-info", _xu_ly(phong_ban), note="Máy in ở tầng mấy?")
    _chuyen(session, ho_so, "in-progress", NGUOI_GUI, note="Tầng ba, cạnh cửa sổ")
    session.commit()
    assert _so_quay_lui(client, ho_so) == 0


def test_phong_tra_mot_lan_la_mot_lan_quay_lui(client, session, rule_set, phong_ban):
    """C1."""
    ho_so = _tao_va_phan_loai(session)
    _ve_phong(session, ho_so, phong_ban)
    _chuyen(session, ho_so, "rejected-by-department", _truong_phong(phong_ban),
            note="Không thuộc phòng này")
    _chuyen(session, ho_so, "classified", PHAN_LOAI)
    _ve_phong(session, ho_so, phong_ban)
    _chuyen(session, ho_so, "in-progress", _truong_phong(phong_ban))
    session.commit()
    assert _so_quay_lui(client, ho_so) == 1

    # Nhãn gắn đúng mốc trả hồ sơ, không gắn mốc định tuyến lại hay mốc nhận việc
    lich_su = client.get(f"/requests/{ho_so.id}").json()["history"]
    assert [e["to_state"] for e in lich_su if e["is_rework"]] == ["rejected-by-department"]


def test_phong_tra_hai_lan_la_hai_lan_quay_lui(client, session, rule_set, phong_ban):
    """C6."""
    ho_so = _tao_va_phan_loai(session)
    for _ in range(2):
        _ve_phong(session, ho_so, phong_ban)
        _chuyen(session, ho_so, "rejected-by-department", _truong_phong(phong_ban),
                note="Không thuộc phòng này")
        _chuyen(session, ho_so, "classified", PHAN_LOAI)
    session.commit()
    assert _so_quay_lui(client, ho_so) == 2


def test_leo_thang_roi_phan_cong_lai_khong_phai_quay_lui(client, session, rule_set, phong_ban):
    """C5."""
    ho_so = _tao_va_phan_loai(session)
    _ve_phong(session, ho_so, phong_ban)
    _chuyen(session, ho_so, "in-progress", _truong_phong(phong_ban))
    _chuyen(session, ho_so, "escalated", Actor.system())
    _chuyen(session, ho_so, "in-progress", _truong_phong(phong_ban))
    session.commit()
    assert _so_quay_lui(client, ho_so) == 0


def test_mo_lai_vi_chua_dat_la_quay_lui(client, session, rule_set, phong_ban):
    """C3."""
    ho_so = _tao_va_phan_loai(session)
    _ve_phong(session, ho_so, phong_ban)
    _chuyen(session, ho_so, "in-progress", _truong_phong(phong_ban))
    _chuyen(session, ho_so, "completed", _xu_ly(phong_ban))
    _chuyen(session, ho_so, "in-progress", NGUOI_GUI, note="Máy vẫn kẹt giấy")
    session.commit()
    assert _so_quay_lui(client, ho_so) == 1


def test_sua_noi_dung_sau_khi_phan_loai_la_quay_lui(client, session, rule_set):
    ho_so = _tao_va_phan_loai(session)
    _chuyen(session, ho_so, "submitted", NGUOI_GUI, changes={"title": "Máy in tầng năm kẹt giấy"})
    session.commit()
    assert _so_quay_lui(client, ho_so) == 1


def test_canh_lam_lai_khong_phai_canh_he_thong(session, rule_set):
    """Leo thang là việc của hệ thống, không phải làm lại — dữ liệu không được đánh dấu nhầm."""
    canh = session.scalars(
        select(Transition).where(Transition.rule_set_id == rule_set.id, Transition.is_rework)
    ).all()
    assert canh, "dữ liệu khởi tạo phải khai ít nhất một cạnh làm lại"
    assert not [c for c in canh if c.is_system]
