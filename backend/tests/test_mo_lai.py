# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử mở lại có giới hạn, trạng thái Không tiếp nhận và hồ sơ tạo lại (#102).
#
# Giảng viên chốt ngày 08/10: nhánh điều phối viên đóng khi không phòng nào nhận đổi tên trạng
# thái và lý do; người gửi mở lại trong 7 ngày làm việc kể từ khi đóng, mỗi lần có lý do, tối
# đa 2 lần, cấp hạn mới cho chu kỳ xử lý mới; quá số lần thì tạo hồ sơ mới liên kết
# `parent_request_id`. Navigator chốt 15/10: mở lại từ cả Hoàn tất lẫn Đã đóng, số lần tính
# chung; chỉ hồ sơ từng làm xong mới mở lại từ Đã đóng; hạn mới tính từ lúc mở lại, gia hạn cũ
# xóa; cửa sổ và số lần nằm trong dữ liệu.
#
# Lịch cả ngày cả tuần (fixture `lich_ca_ngay`) để giờ làm việc trùng giờ lịch.

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import current_actor
from app.db import get_session
from app.main import app
from app.models.case import Request
from app.models.workflow_config import Priority, RequestType, State, Transition
from app.rules import guards
from app.rules.sla import bay_gio
from app.workflow.context import Actor
from app.workflow.engine import (
    allowed_transitions,
    case_history,
    create_case,
    kiem_ho_so_goc,
    perform_transition,
)
from app.workflow.errors import GuardViolation, NoteRequired, TransitionNotAllowed
from app.workflow.escalation import TAC_NHAN_HAN_CHO, quet_het_han_cho

pytestmark = pytest.mark.usefixtures("lich_ca_ngay")

NGUOI_GUI = "nguoi-gui-102"
NGUOI_KHAC = "nguoi-khac-102"
DIEU_PHOI = Actor(id="dp-102", roles=frozenset({"classifier"}))
CUA_SO_MO_LAI = 56 * 3600
MO_LAI_SAU_DONG = "reopen-after-close"
MO_LAI_TU_HOAN_TAT = "reopen"


def _nguoi_gui(ma: str = NGUOI_GUI) -> Actor:
    return Actor(id=ma, roles=frozenset({"requester"}))


def _truong_phong(phong_ban: str) -> Actor:
    return Actor(id="tp-102", roles=frozenset({"approver"}), departments=frozenset({phong_ban}))


def _xu_ly(phong_ban: str) -> Actor:
    return Actor(id="xl-102", roles=frozenset({"handler"}), departments=frozenset({phong_ban}))


def _nut(session, ho_so, actor) -> set[str]:
    return {c.activity_code for c in allowed_transitions(session, ho_so, actor)}


def _den_dang_xu_ly(session, phong_ban: str):
    loai = session.scalars(
        select(RequestType).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()
    ho_so = create_case(session, title="Hồ sơ thử mở lại", requester_id=NGUOI_GUI)
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=DIEU_PHOI,
        changes={"priority_code": uu_tien, "request_type_code": loai.code},
    )
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="awaiting-acceptance",
        actor=DIEU_PHOI,
        changes={"department_code": phong_ban},
    )
    perform_transition(
        session, case_id=ho_so.id, to_state="in-progress", actor=_truong_phong(phong_ban)
    )
    return ho_so


def _hoan_tat(session, phong_ban: str):
    ho_so = _den_dang_xu_ly(session, phong_ban)
    perform_transition(session, case_id=ho_so.id, to_state="completed", actor=_xu_ly(phong_ban))
    return ho_so


def _da_dong(session, phong_ban: str):
    """Hồ sơ làm xong rồi người gửi xác nhận đạt — đang ở Đã đóng."""
    ho_so = _hoan_tat(session, phong_ban)
    perform_transition(session, case_id=ho_so.id, to_state="closed", actor=_nguoi_gui())
    return ho_so


def _mo_lai_sau_dong(session, ho_so, ly_do: str = "Máy vẫn chưa chạy"):
    return perform_transition(
        session,
        case_id=ho_so.id,
        to_state="in-progress",
        actor=_nguoi_gui(),
        note=ly_do,
    )


# ---------------------------------------------------------------------------
# Dữ liệu khai đúng
# ---------------------------------------------------------------------------


def test_khong_tiep_nhan_la_trang_thai_ket_thuc_rieng(session, rule_set):
    trang_thai = {s.code: s for s in session.scalars(select(State).where(State.rule_set_id == rule_set.id))}
    assert trang_thai["rejected-unrouted"].is_terminal
    assert trang_thai["rejected-unrouted"].label == "Không tiếp nhận"
    # Khác Đã đóng: hai trạng thái là hai thứ trong báo cáo của tầng D
    assert trang_thai["closed"].label != trang_thai["rejected-unrouted"].label

    canh = session.scalars(
        select(Transition).where(
            Transition.rule_set_id == rule_set.id, Transition.from_state == "classified"
        )
    ).all()
    assert "closed" not in {c.to_state for c in canh}
    bo = next(c for c in canh if c.to_state == "rejected-unrouted")
    assert bo.requires_note and bo.note_label == "Lý do không tiếp nhận"
    assert bo.role_codes == {"classifier"}
    assert {"actor-not-requester"} <= set(bo.guard_codes)


def test_canh_mo_lai_sau_dong_khai_trong_du_lieu(session, rule_set):
    canh = session.scalars(
        select(Transition).where(
            Transition.rule_set_id == rule_set.id,
            Transition.activity_code == MO_LAI_SAU_DONG,
        )
    ).one()
    assert (canh.from_state, canh.to_state) == ("closed", "in-progress")
    assert canh.from_is_terminal and canh.is_rework and canh.restarts_sla and canh.requires_note
    # 7 ngày làm việc của lịch mẫu 8 giờ một ngày
    assert canh.reopen_window_hours == 56
    assert canh.role_codes == {"requester"}
    assert {"requester-owns-case", "reopen-limit", "reopen-window", "reopen-from-rework"} == set(
        canh.guard_codes
    )

    tu_hoan_tat = session.scalars(
        select(Transition).where(
            Transition.rule_set_id == rule_set.id, Transition.activity_code == MO_LAI_TU_HOAN_TAT
        )
    ).one()
    assert tu_hoan_tat.restarts_sla and tu_hoan_tat.reopen_window_hours is None
    assert "reopen-limit" in tu_hoan_tat.guard_codes


def test_gioi_han_mo_lai_nam_o_loai_yeu_cau(session, rule_set):
    # Loại của quy trình cổng yêu cầu nội bộ — quy trình khác có thể không cho mở lại (#376)
    cac = session.scalars(
        select(RequestType.reopen_max_count).where(RequestType.process_code == rule_set.process_code)
    ).all()
    assert cac and set(cac) == {2}


def test_chi_canh_mo_lai_co_cua_so_moi_roi_duoc_trang_thai_ket_thuc(session, rule_set):
    ket_thuc = session.scalars(
        select(State.code).where(State.rule_set_id == rule_set.id, State.is_terminal)
    ).all()
    ra = session.scalars(
        select(Transition).where(
            Transition.rule_set_id == rule_set.id, Transition.from_state.in_(ket_thuc)
        )
    ).all()
    assert [c.activity_code for c in ra] == [MO_LAI_SAU_DONG]
    assert all(c.reopen_window_hours for c in ra)


def test_luoc_do_chan_canh_roi_ket_thuc_khong_co_cua_so(session, rule_set):
    """Bỏ cửa sổ thời gian khỏi cạnh rời trạng thái kết thúc là lược đồ từ chối — mở cửa ra
    khỏi trạng thái kết thúc không thể là một cú lỡ tay."""
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.execute(
                update(Transition)
                .where(
                    Transition.rule_set_id == rule_set.id,
                    Transition.activity_code == MO_LAI_SAU_DONG,
                )
                .values(reopen_window_hours=None)
            )
            session.flush()


def test_luoc_do_chan_cua_so_tren_canh_khong_roi_ket_thuc(session, rule_set):
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.execute(
                update(Transition)
                .where(
                    Transition.rule_set_id == rule_set.id,
                    Transition.activity_code == MO_LAI_TU_HOAN_TAT,
                )
                .values(reopen_window_hours=56)
            )
            session.flush()


# ---------------------------------------------------------------------------
# Nhánh C: Không tiếp nhận
# ---------------------------------------------------------------------------


def test_khong_tiep_nhan_bat_buoc_ly_do_va_la_trang_thai_cuoi(session, rule_set):
    ho_so = create_case(session, title="Không ai nhận", requester_id=NGUOI_GUI)
    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()
    loai = session.scalars(select(RequestType.code).order_by(RequestType.display_order)).first()
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=DIEU_PHOI,
        changes={"priority_code": uu_tien, "request_type_code": loai},
    )
    with pytest.raises(NoteRequired):
        perform_transition(
            session, case_id=ho_so.id, to_state="rejected-unrouted", actor=DIEU_PHOI
        )
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="rejected-unrouted",
        actor=DIEU_PHOI,
        note="Chưa rõ cần gì, mời gửi lại với thông tin cụ thể.",
    )
    assert ho_so.current_state == "rejected-unrouted"
    cuoi = case_history(session, ho_so.id)[-1]
    assert cuoi.activity == "decline-unrouted"
    assert cuoi.note.startswith("Chưa rõ")
    # Không mở lại được: không cạnh nào đi ra, người gửi tạo hồ sơ mới
    assert _nut(session, ho_so, _nguoi_gui()) == set()
    with pytest.raises(TransitionNotAllowed):
        perform_transition(
            session, case_id=ho_so.id, to_state="in-progress", actor=_nguoi_gui(), note="x"
        )


# ---------------------------------------------------------------------------
# Mở lại từ Hoàn tất: đếm lượt, hạn mới
# ---------------------------------------------------------------------------


def test_mo_lai_tu_hoan_tat_dem_luot_va_dat_lai_han(session, phong_ban):
    ho_so = _hoan_tat(session, phong_ban)
    # Chu kỳ đầu đã chạy lâu và đã gia hạn một lần
    ho_so.sla_running_seconds = 30_000
    ho_so.sla_extension_total_hours = 4
    ho_so.sla_extension_count = 1
    ho_so.sla_extension_hours = 4
    session.flush()

    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="in-progress",
        actor=_nguoi_gui(),
        note="Chưa đạt",
    )

    assert ho_so.current_state == "in-progress"
    assert ho_so.reopen_count == 1
    # Chu kỳ xử lý mới: hạn đếm lại từ 0, gia hạn cũ không kế thừa
    assert ho_so.sla_running_seconds == 0
    assert (
        ho_so.sla_extension_hours,
        ho_so.sla_extension_total_hours,
        ho_so.sla_extension_count,
    ) == (0, 0, 0)
    assert ho_so.sla_segment_since is not None
    cuoi = case_history(session, ho_so.id)[-1]
    assert cuoi.activity == MO_LAI_TU_HOAN_TAT
    # Giá trị cũ vào nhật ký để dựng lại hạn của chu kỳ trước
    assert cuoi.changes["reopen_count"] == {"from": 0, "to": 1}
    assert cuoi.changes["sla_extension_total_hours"] == {"from": 4, "to": 0}


def test_mo_lai_phai_co_ly_do(session, phong_ban):
    ho_so = _hoan_tat(session, phong_ban)
    with pytest.raises(NoteRequired):
        perform_transition(
            session, case_id=ho_so.id, to_state="in-progress", actor=_nguoi_gui()
        )


def test_het_luot_thi_mat_nut_mo_lai_va_bi_chan(session, phong_ban):
    """Mở lại 2 lần rồi, lần thứ ba bị từ chối ở cả hai cạnh."""
    ho_so = _hoan_tat(session, phong_ban)
    for _ in range(2):
        assert MO_LAI_TU_HOAN_TAT in _nut(session, ho_so, _nguoi_gui())
        perform_transition(
            session, case_id=ho_so.id, to_state="in-progress", actor=_nguoi_gui(), note="Chưa đạt"
        )
        perform_transition(session, case_id=ho_so.id, to_state="completed", actor=_xu_ly(phong_ban))
    assert ho_so.reopen_count == 2

    assert MO_LAI_TU_HOAN_TAT not in _nut(session, ho_so, _nguoi_gui())
    with pytest.raises(GuardViolation) as loi:
        perform_transition(
            session, case_id=ho_so.id, to_state="in-progress", actor=_nguoi_gui(), note="Lại"
        )
    assert loi.value.guard_code == "reopen-limit"
    assert "tạo hồ sơ mới" in loi.value.message

    # Xác nhận rồi đóng cũng không mở lại thêm được: số lần tính chung hai cạnh
    perform_transition(session, case_id=ho_so.id, to_state="closed", actor=_nguoi_gui())
    assert MO_LAI_SAU_DONG not in _nut(session, ho_so, _nguoi_gui())


# ---------------------------------------------------------------------------
# Mở lại sau khi đã đóng
# ---------------------------------------------------------------------------


def test_nguoi_gui_thay_nut_mo_lai_sau_dong_khi_con_cua_so(session, phong_ban):
    ho_so = _da_dong(session, phong_ban)
    assert MO_LAI_SAU_DONG in _nut(session, ho_so, _nguoi_gui())
    # Người khác — kể cả mang vai trò người gửi — không thấy
    assert _nut(session, ho_so, _nguoi_gui(NGUOI_KHAC)) == set()
    assert _nut(session, ho_so, DIEU_PHOI) == set()


def test_mo_lai_sau_dong_dat_hong_ve_dang_xu_ly_voi_han_moi(session, phong_ban):
    ho_so = _da_dong(session, phong_ban)
    ho_so.sla_running_seconds = 20_000
    ho_so.sla_extension_total_hours = 4
    ho_so.sla_extension_count = 1
    session.flush()

    _mo_lai_sau_dong(session, ho_so)

    assert ho_so.current_state == "in-progress"
    assert ho_so.department_code == phong_ban  # ở lại đúng phòng đã nhận
    assert ho_so.reopen_count == 1
    assert ho_so.sla_running_seconds == 0
    assert (ho_so.sla_extension_total_hours, ho_so.sla_extension_count) == (0, 0)
    # Đồng hồ chạy lại ngay: hồ sơ không đứng yên ở Đã đóng với đồng hồ tắt
    assert ho_so.sla_segment_since is not None
    cuoi = case_history(session, ho_so.id)[-1]
    assert (cuoi.activity, cuoi.from_state, cuoi.to_state) == (MO_LAI_SAU_DONG, "closed", "in-progress")
    assert cuoi.note == "Máy vẫn chưa chạy"


def test_mo_lai_sau_dong_phai_co_ly_do_va_dung_nguoi_gui(session, phong_ban):
    ho_so = _da_dong(session, phong_ban)
    with pytest.raises(NoteRequired):
        perform_transition(
            session, case_id=ho_so.id, to_state="in-progress", actor=_nguoi_gui()
        )
    with pytest.raises(GuardViolation) as loi:
        perform_transition(
            session,
            case_id=ho_so.id,
            to_state="in-progress",
            actor=_nguoi_gui(NGUOI_KHAC),
            note="Mở hộ",
        )
    assert loi.value.guard_code == "requester-owns-case"


def test_cua_so_mo_lai_dung_o_so_gio_trong_du_lieu(session, phong_ban, monkeypatch):
    """Đúng mốc cửa sổ vẫn mở được, quá một giây thì cạnh biến mất và lần chuyển bị chặn."""
    ho_so = _da_dong(session, phong_ban)

    monkeypatch.setattr(guards, "giay_lam_viec", lambda _s, _tu, _den=None: CUA_SO_MO_LAI)
    assert MO_LAI_SAU_DONG in _nut(session, ho_so, _nguoi_gui())

    monkeypatch.setattr(guards, "giay_lam_viec", lambda _s, _tu, _den=None: CUA_SO_MO_LAI + 1)
    assert MO_LAI_SAU_DONG not in _nut(session, ho_so, _nguoi_gui())
    with pytest.raises(GuardViolation) as loi:
        _mo_lai_sau_dong(session, ho_so)
    assert loi.value.guard_code == "reopen-window"
    assert "tạo hồ sơ mới" in loi.value.message
    assert ho_so.current_state == "closed"


def test_cua_so_doi_theo_du_lieu_khong_theo_ma(session, phong_ban, monkeypatch):
    """Sửa cột `reopen_window_hours` là đổi cửa sổ, không sửa dòng mã nào."""
    ho_so = _da_dong(session, phong_ban)
    session.execute(
        update(Transition)
        .where(Transition.activity_code == MO_LAI_SAU_DONG)
        .values(reopen_window_hours=8)
    )
    session.expire_all()
    monkeypatch.setattr(guards, "giay_lam_viec", lambda _s, _tu, _den=None: 9 * 3600)
    assert MO_LAI_SAU_DONG not in _nut(session, ho_so, _nguoi_gui())
    monkeypatch.setattr(guards, "giay_lam_viec", lambda _s, _tu, _den=None: 8 * 3600)
    assert MO_LAI_SAU_DONG in _nut(session, ho_so, _nguoi_gui())


def test_cua_so_do_tu_luc_vao_da_dong_bang_gio_lam_viec(session, phong_ban):
    """Đo thật, không giả: hồ sơ vừa đóng còn nguyên cửa sổ."""
    ho_so = _da_dong(session, phong_ban)
    assert bay_gio(session) - dt.timedelta(minutes=5) < ho_so.updated_at
    assert MO_LAI_SAU_DONG in _nut(session, ho_so, _nguoi_gui())


def test_mo_lai_het_luot_tinh_chung_hai_canh(session, phong_ban):
    """Một lần mở lại từ Hoàn tất, một lần sau khi đóng — lần thứ ba hết lượt."""
    ho_so = _hoan_tat(session, phong_ban)
    perform_transition(
        session, case_id=ho_so.id, to_state="in-progress", actor=_nguoi_gui(), note="Chưa đạt"
    )
    perform_transition(session, case_id=ho_so.id, to_state="completed", actor=_xu_ly(phong_ban))
    perform_transition(session, case_id=ho_so.id, to_state="closed", actor=_nguoi_gui())
    _mo_lai_sau_dong(session, ho_so)
    assert ho_so.reopen_count == 2
    perform_transition(session, case_id=ho_so.id, to_state="completed", actor=_xu_ly(phong_ban))
    perform_transition(session, case_id=ho_so.id, to_state="closed", actor=_nguoi_gui())
    assert _nut(session, ho_so, _nguoi_gui()) == set()


def test_tu_dong_sau_hoan_tat_van_mo_lai_duoc(session, phong_ban):
    """Tự đóng sau Hoàn tất (#144) không khác người gửi xác nhận: hồ sơ đã làm xong."""
    ho_so = _hoan_tat(session, phong_ban)
    bay = bay_gio(session)
    assert quet_het_han_cho(session, bay + dt.timedelta(hours=24)) == [ho_so.id]
    assert case_history(session, ho_so.id)[-1].actor == TAC_NHAN_HAN_CHO
    assert MO_LAI_SAU_DONG in _nut(session, ho_so, _nguoi_gui())


def test_tu_dong_vi_chua_bo_sung_khong_mo_lai_duoc(session, phong_ban):
    """Hồ sơ tự đóng vì người gửi không bổ sung thông tin (#143) chưa có gì để "chưa đạt":
    nút Mở lại không hiện, lần chuyển bị từ chối — người gửi tạo hồ sơ mới."""
    ho_so = _den_dang_xu_ly(session, phong_ban)
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="awaiting-info",
        actor=_xu_ly(phong_ban),
        note="Cần số máy",
    )
    bay = bay_gio(session)
    assert quet_het_han_cho(session, bay + dt.timedelta(hours=40)) == [ho_so.id]
    assert ho_so.current_state == "closed"

    assert _nut(session, ho_so, _nguoi_gui()) == set()
    with pytest.raises(GuardViolation) as loi:
        _mo_lai_sau_dong(session, ho_so)
    assert loi.value.guard_code == "reopen-from-rework"
    assert "tạo hồ sơ mới" in loi.value.message


# ---------------------------------------------------------------------------
# Hồ sơ tạo lại — parent_request_id
# ---------------------------------------------------------------------------


def test_kiem_ho_so_goc(session, phong_ban):
    dang_chay = _den_dang_xu_ly(session, phong_ban)
    da_dong = _da_dong(session, phong_ban)

    assert kiem_ho_so_goc(session, None, NGUOI_GUI) is None
    assert kiem_ho_so_goc(session, da_dong.id, NGUOI_GUI) == da_dong.id
    # Hồ sơ đang chạy thì làm tiếp, không tạo bản sao
    with pytest.raises(ValueError):
        kiem_ho_so_goc(session, dang_chay.id, NGUOI_GUI)
    # Hồ sơ của người khác và hồ sơ không có trả lời giống nhau — không lộ hồ sơ có tồn tại
    with pytest.raises(ValueError) as cua_nguoi_khac:
        kiem_ho_so_goc(session, da_dong.id, NGUOI_KHAC)
    with pytest.raises(ValueError) as khong_co:
        kiem_ho_so_goc(session, 999_999_999, NGUOI_GUI)
    assert str(cua_nguoi_khac.value).split(":")[0] == str(khong_co.value).split(":")[0]


@pytest.fixture
def client(session):
    actor = _nguoi_gui()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: actor
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_tao_lai_ho_so_qua_diem_cuoi_va_hai_trang_noi_nhau(client, session, phong_ban):
    cu = _da_dong(session, phong_ban)
    session.commit()

    r = client.post(
        "/requests",
        json={"title": "Máy in kẹt giấy — gửi lại", "parent_request_id": cu.id},
    )
    assert r.status_code == 201, r.text
    moi = r.json()
    assert moi["parent"]["id"] == cu.id
    assert moi["parent"]["state"]["is_terminal"] is True
    assert session.get(Request, moi["id"]).parent_request_id == cu.id

    # Trang hồ sơ cũ liệt kê hồ sơ tạo lại từ nó
    goc = client.get(f"/requests/{cu.id}").json()
    assert [c["id"] for c in goc["children"]] == [moi["id"]]
    assert goc["parent"] is None
    assert goc["reopen_max_count"] == 2


def test_tao_lai_tu_ho_so_cua_nguoi_khac_hay_dang_chay_bi_tu_choi(client, session, phong_ban):
    cua_nguoi_khac = create_case(session, title="Của người khác", requester_id=NGUOI_KHAC)
    dang_chay = _den_dang_xu_ly(session, phong_ban)
    session.commit()

    for ma in (cua_nguoi_khac.id, dang_chay.id, 999_999_999):
        r = client.post("/requests", json={"title": "Gửi lại hồ sơ", "parent_request_id": ma})
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["code"] == "invalid-parent-request"
    # Không hồ sơ nào lọt vào
    assert session.scalars(
        select(Request).where(Request.title == "Gửi lại hồ sơ")
    ).first() is None


def test_ho_so_khong_tu_lam_goc_cua_chinh_no(session, phong_ban):
    ho_so = _da_dong(session, phong_ban)
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.execute(
                update(Request).where(Request.id == ho_so.id).values(parent_request_id=ho_so.id)
            )
            session.flush()


def test_ho_so_khong_co_goc_thi_khong_co_lien_ket(client, session):
    ho_so = create_case(session, title="Hồ sơ đầu tiên", requester_id=NGUOI_GUI)
    session.commit()
    chi_tiet = client.get(f"/requests/{ho_so.id}").json()
    assert chi_tiet["parent"] is None and chi_tiet["children"] == []
    assert chi_tiet["reopen_count"] == 0


def test_canh_ket_thuc_bao_giao_dien_con_mo_lai_duoc_khong(client, session, phong_ban):
    """Câu cảnh báo "không hoàn tác được" chỉ đúng với trạng thái kết thúc hẳn. Xác nhận đạt
    sang Đã đóng thì còn mở lại trong cửa sổ — dịch vụ nói rõ để giao diện không nói sai."""
    ho_so = _hoan_tat(session, phong_ban)
    session.commit()

    canh = {c["activity_code"]: c for c in client.get(f"/requests/{ho_so.id}").json()["allowed_transitions"]}
    assert canh["confirm"]["to_state_is_terminal"] is True
    assert canh["confirm"]["to_state_reopen_hours"] == 56
    assert canh[MO_LAI_TU_HOAN_TAT]["to_state_is_terminal"] is False
    assert canh[MO_LAI_TU_HOAN_TAT]["to_state_reopen_hours"] is None


def test_huy_va_khong_tiep_nhan_ket_thuc_han(client, session):
    ho_so = create_case(session, title="Hủy thử", requester_id=NGUOI_GUI)
    session.commit()
    canh = {c["activity_code"]: c for c in client.get(f"/requests/{ho_so.id}").json()["allowed_transitions"]}
    assert canh["cancel"]["to_state_is_terminal"] is True
    assert canh["cancel"]["to_state_reopen_hours"] is None
