# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử từ ngữ của thông báo lỗi người dùng đọc được (#157).
#
# Người gặp những lỗi này thường là người bấm một nút của trang đã cũ — hồ sơ vừa được người khác
# chuyển đi — nên thông báo phải nói bằng nhãn tiếng Việt của trạng thái và vai trò, không phải mã
# tiếng Anh của bảng dữ liệu, và không dùng từ nội bộ như "cạnh".

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models.workflow_config import Priority, RequestType, Role, State, Transition
from app.rules.guards import department_unchanged
from app.workflow.context import Actor
from app.workflow.engine import create_case, perform_transition
from app.workflow.errors import (
    GuardViolation,
    RoleNotPermitted,
    SystemTransitionOnly,
    TransitionNotAllowed,
)

DIEU_PHOI = Actor(id="dp-157", roles=frozenset({"classifier"}))
NGUOI_GUI = Actor(id="gui-157", roles=frozenset({"requester"}))


def _nhan_trang_thai(session, rule_set, ma: str) -> str:
    return session.get(State, (rule_set.id, ma)).label


def test_loi_khong_co_duong_di_noi_bang_nhan_trang_thai(session, rule_set):
    ho_so = create_case(session, title="Hồ sơ thử thông báo", requester_id=NGUOI_GUI.id)
    with pytest.raises(TransitionNotAllowed) as loi:
        perform_transition(session, case_id=ho_so.id, to_state="completed", actor=DIEU_PHOI)
    thong_diep = str(loi.value)
    assert _nhan_trang_thai(session, rule_set, "submitted") in thong_diep
    assert _nhan_trang_thai(session, rule_set, "completed") in thong_diep
    assert "submitted" not in thong_diep and "completed" not in thong_diep
    # Chỉ cho người đọc biết việc cần làm tiếp theo
    assert "tải lại trang" in thong_diep


def test_loi_sai_vai_tro_noi_bang_nhan_vai_tro(session, rule_set):
    ho_so = create_case(session, title="Hồ sơ thử vai trò", requester_id=NGUOI_GUI.id)
    with pytest.raises(RoleNotPermitted) as loi:
        # Phân loại là việc của điều phối viên, không phải người gửi
        perform_transition(session, case_id=ho_so.id, to_state="classified", actor=NGUOI_GUI)
    thong_diep = str(loi.value)
    nhan = session.get(Role, "classifier").label
    assert nhan in thong_diep
    assert "classifier" not in thong_diep
    assert "Cạnh" not in thong_diep and "cạnh" not in thong_diep
    assert "Bước này dành cho" in thong_diep


def test_loi_buoc_cua_he_thong_khong_noi_canh(session, rule_set):
    ho_so = create_case(session, title="Hồ sơ thử bước của hệ thống", requester_id=NGUOI_GUI.id)
    loai = session.scalars(select(RequestType.code).order_by(RequestType.display_order)).first()
    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=DIEU_PHOI,
        changes={"priority_code": uu_tien, "request_type_code": loai},
    )
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="awaiting-acceptance",
        actor=DIEU_PHOI,
        changes={"department_code": "it"},
    )
    leo_thang = session.scalars(
        select(Transition).where(Transition.activity_code == "escalate", Transition.is_system)
    ).one()
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="in-progress",
        actor=Actor(
            id="tp-157",
            roles=frozenset({"approver"}),
            departments=frozenset({"it"}),
        ),
    )
    with pytest.raises(SystemTransitionOnly) as loi:
        perform_transition(session, case_id=ho_so.id, to_state="escalated", actor=DIEU_PHOI)
    thong_diep = str(loi.value)
    assert leo_thang.activity_label in thong_diep
    assert "do hệ thống tự thực hiện" in thong_diep
    assert "Cạnh" not in thong_diep


def test_loi_doi_phong_ban_goi_la_nguoi_xu_ly():
    """Một tên cho một vai: "người xử lý", không có lúc "người phụ trách"."""
    ctx = SimpleNamespace(
        case=SimpleNamespace(department_code="it"),
        changes={"department_code": "hr"},
    )
    with pytest.raises(GuardViolation) as loi:
        department_unchanged(ctx)
    assert "người xử lý" in str(loi.value)
    assert "phụ trách" not in str(loi.value)
