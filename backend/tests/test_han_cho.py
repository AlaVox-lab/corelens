# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử hạn chờ ở "Chờ phòng ban xác duyệt" (#142), "Hoàn tất" (#144) và "Chờ bổ sung
# thông tin" (#143).
#
# Giảng viên chốt ngày 08/10: phòng ban không xác duyệt trong 24 giờ làm việc thì hồ sơ tự
# trả về điều phối viên, báo trước 4 giờ; điều phối viên rút được trước hạn, có lý do; việc
# trả về ghi nhật ký. Navigator chốt 12/10: hai cạnh cùng cặp trạng thái (một người, một hệ
# thống), tự trả về không tính quay lui.
#
# Nhật ký sự kiện chỉ ghi thêm nên không lùi được lúc hồ sơ vào trạng thái; bài kiểm thử
# truyền thời điểm xét ở tương lai cho bộ quét. Lịch cả ngày cả tuần (fixture `lich_ca_ngay`)
# để "24 giờ làm việc" trùng 24 giờ lịch ở mọi lúc chạy — lịch thật kiểm ở #199.

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.dependencies import current_actor
from app.db import get_session
from app.main import app
from app.models.workflow_config import Priority, RequestType, Transition
from app.rules.han_cho import tu_dong
from app.rules.sla import bay_gio
from app.workflow.context import Actor
from app.workflow.coordination import trang_thai_hang_doi_dieu_phoi
from app.workflow.engine import (
    allowed_transitions,
    case_history,
    create_case,
    perform_transition,
)
from app.workflow.errors import GuardViolation, NoteRequired, RoleNotPermitted
from app.workflow.escalation import TAC_NHAN_HAN_CHO, quet_het_han_cho, quet_va_leo_thang

pytestmark = pytest.mark.usefixtures("lich_ca_ngay")

NGUOI_GUI = "nguoi-gui-142"
DIEU_PHOI = Actor(id="dp-142", roles=frozenset({"classifier"}))
# Người dựng cảnh: một điều phối viên khác, để dựng được cả hồ sơ do DIEU_PHOI gửi (#154)
DP_DUNG = Actor(id="dp-142-dung", roles=frozenset({"classifier"}))
GIO = dt.timedelta(hours=1)


def _cho_phong(session, phong_ban: str, nguoi_gui: str = NGUOI_GUI):
    """Hồ sơ vừa chuyển về phòng ban, đang ở Chờ phòng ban xác duyệt."""
    loai = session.scalars(
        select(RequestType).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()
    ho_so = create_case(session, title="Hồ sơ thử hạn chờ", requester_id=nguoi_gui)
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=DP_DUNG,
        changes={"priority_code": uu_tien, "request_type_code": loai.code},
    )
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="awaiting-acceptance",
        actor=DP_DUNG,
        changes={"department_code": phong_ban},
    )
    return ho_so


def _hai_canh(session, rule_set) -> tuple[Transition, Transition]:
    cac = session.scalars(
        select(Transition).where(
            Transition.rule_set_id == rule_set.id,
            Transition.from_state == "awaiting-acceptance",
            Transition.to_state == "classified",
        )
    ).all()
    nguoi = [c for c in cac if not c.is_system]
    he_thong = [c for c in cac if c.is_system]
    assert len(nguoi) == 1 and len(he_thong) == 1
    return nguoi[0], he_thong[0]


# ---------------------------------------------------------------------------
# Dữ liệu khởi tạo
# ---------------------------------------------------------------------------


def test_mot_cap_trang_thai_co_canh_nguoi_va_canh_he_thong(session, rule_set):
    rut, tu_tra = _hai_canh(session, rule_set)
    assert rut.role_codes == {"classifier"}
    assert rut.requires_note
    assert "actor-not-requester" in rut.guard_codes
    # Cạnh hệ thống không nhận vai trò hay ràng buộc của cạnh người cùng cặp
    assert tu_tra.role_codes == set() and tu_tra.guard_codes == []
    assert tu_tra.auto_after_hours == 24 and tu_tra.warn_before_hours == 4
    assert not tu_tra.is_rework and not rut.is_rework


def test_chi_mot_canh_tu_di_moi_trang_thai(session, rule_set):
    from sqlalchemy.exc import IntegrityError

    _, tu_tra = _hai_canh(session, rule_set)
    session.add(
        Transition(
            rule_set_id=rule_set.id,
            from_state="awaiting-acceptance",
            to_state="cancelled",
            activity_code="tu-huy",
            activity_label="Tự hủy",
            is_system=True,
            auto_after_hours=48,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# ---------------------------------------------------------------------------
# Điều phối viên rút hồ sơ
# ---------------------------------------------------------------------------


def test_dieu_phoi_vien_rut_ho_so_ve_co_ly_do(session, phong_ban):
    ho_so = _cho_phong(session, phong_ban)
    cac_nut = {c.activity_code for c in allowed_transitions(session, ho_so, DIEU_PHOI)}
    # Gia hạn (#101) cũng là cạnh của điều phối viên ở trạng thái này
    assert cac_nut == {"withdraw", "extend-deadline"}

    with pytest.raises(NoteRequired):
        perform_transition(session, case_id=ho_so.id, to_state="classified", actor=DIEU_PHOI)

    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=DIEU_PHOI,
        note="Phòng đang quá tải, chuyển phòng khác",
    )
    assert ho_so.current_state == "classified"
    # Phòng cũ giữ lại tới khi điều phối chọn phòng mới, như hồ sơ bị phòng ban trả
    assert ho_so.department_code == phong_ban
    cuoi = case_history(session, ho_so.id)[-1]
    assert cuoi.activity == "withdraw" and cuoi.actor == DIEU_PHOI.id


def test_phong_ban_khong_rut_duoc(session, phong_ban):
    ho_so = _cho_phong(session, phong_ban)
    truong_phong = Actor(
        id="tp-142", roles=frozenset({"approver"}), departments=frozenset({phong_ban})
    )
    with pytest.raises(RoleNotPermitted):
        perform_transition(
            session, case_id=ho_so.id, to_state="classified", actor=truong_phong, note="x"
        )


def test_khong_rut_ho_so_cua_chinh_minh(session, phong_ban):
    ho_so = _cho_phong(session, phong_ban, nguoi_gui=DIEU_PHOI.id)
    assert allowed_transitions(session, ho_so, DIEU_PHOI) == []
    with pytest.raises(GuardViolation):
        perform_transition(
            session, case_id=ho_so.id, to_state="classified", actor=DIEU_PHOI, note="x"
        )


def test_trang_thai_cho_phong_vao_hang_doi_dieu_phoi(session, rule_set):
    """Điều phối viên có cạnh đi ra từ Chờ phòng ban xác duyệt nên trạng thái đó tự vào
    hàng đợi điều phối — suy từ dữ liệu, không liệt kê."""
    ma = {t.code for t in trang_thai_hang_doi_dieu_phoi(session, rule_set.id)}
    assert "awaiting-acceptance" in ma


# ---------------------------------------------------------------------------
# Hệ thống tự trả về khi hết hạn chờ
# ---------------------------------------------------------------------------


def test_chua_het_han_cho_thi_khong_tu_tra(session, loc_cua_bai, phong_ban):
    ho_so = _cho_phong(session, phong_ban)
    assert loc_cua_bai(quet_het_han_cho(session, bay_gio(session) + 24 * GIO - dt.timedelta(minutes=1))) == []
    assert ho_so.current_state == "awaiting-acceptance"


def test_het_han_cho_thi_tu_tra_ve_dieu_phoi_va_ghi_nhat_ky(session, loc_cua_bai, phong_ban):
    ho_so = _cho_phong(session, phong_ban)
    da_di = loc_cua_bai(quet_het_han_cho(session, bay_gio(session) + 24 * GIO))

    assert da_di == [ho_so.id]
    assert ho_so.current_state == "classified"
    assert ho_so.department_code == phong_ban
    cuoi = case_history(session, ho_so.id)[-1]
    assert cuoi.activity == "auto-return"
    assert cuoi.actor == TAC_NHAN_HAN_CHO
    assert cuoi.from_state == "awaiting-acceptance"
    assert "24 giờ làm việc" in (cuoi.note or "")


def test_bo_quet_leo_thang_khong_dong_toi_canh_tu_di(session, loc_cua_bai, phong_ban):
    """Hai bộ quét, hai loại cạnh hệ thống: quét SLA không đi cạnh có hạn chờ."""
    ho_so = _cho_phong(session, phong_ban)
    assert ho_so.id not in loc_cua_bai(quet_va_leo_thang(session))
    assert ho_so.current_state == "awaiting-acceptance"


def test_nguoi_khong_di_duoc_canh_he_thong(session, phong_ban):
    """Điều phối viên gọi cùng cặp trạng thái thì đi cạnh của người — phải có lý do — chứ
    không lọt qua cạnh hệ thống không đòi lý do."""
    ho_so = _cho_phong(session, phong_ban)
    with pytest.raises(NoteRequired):
        perform_transition(session, case_id=ho_so.id, to_state="classified", actor=DIEU_PHOI)


# ---------------------------------------------------------------------------
# Báo trước trên màn hình
# ---------------------------------------------------------------------------


def test_tu_dong_cho_biet_luc_tu_tra_va_bao_truoc(session, phong_ban):
    ho_so = _cho_phong(session, phong_ban)
    bay = bay_gio(session)

    td = tu_dong(session, ho_so)
    assert td.canh.activity_code == "auto-return"
    assert td.luc == bay + 24 * GIO
    assert not td.bao_truoc

    assert not tu_dong(session, ho_so, bay + 20 * GIO - dt.timedelta(minutes=1)).bao_truoc
    assert tu_dong(session, ho_so, bay + 20 * GIO).bao_truoc


def test_trang_thai_khong_co_han_cho_thi_khong_co_tu_dong(session):
    ho_so = create_case(session, title="Mới gửi", requester_id=NGUOI_GUI)
    assert tu_dong(session, ho_so) is None


def test_danh_sach_ho_so_tra_ve_luc_tu_tra(session, phong_ban):
    ho_so = _cho_phong(session, phong_ban)
    session.commit()

    nguoi_gui = Actor(id=NGUOI_GUI, roles=frozenset({"requester"}))
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: nguoi_gui
    try:
        with TestClient(app) as c:
            ds = c.get("/requests").json()["items"]
    finally:
        app.dependency_overrides.clear()

    muc = next(m for m in ds if m["id"] == ho_so.id)
    assert muc["auto_transition"]["activity_label"] == "Tự trả về điều phối"
    assert muc["auto_transition"]["warn"] is False
    assert muc["auto_transition"]["at"] is not None


# ---------------------------------------------------------------------------
# Hoàn tất tự đóng khi người gửi không xác nhận (#144)
# ---------------------------------------------------------------------------


def _hoan_tat(session, phong_ban: str):
    """Hồ sơ phòng ban đã làm xong, đang chờ người gửi xác nhận."""
    ho_so = _cho_phong(session, phong_ban)
    tp = Actor(id="tp-144", roles=frozenset({"approver"}), departments=frozenset({phong_ban}))
    xl = Actor(id="xl-144", roles=frozenset({"handler"}), departments=frozenset({phong_ban}))
    perform_transition(session, case_id=ho_so.id, to_state="in-progress", actor=tp)
    perform_transition(session, case_id=ho_so.id, to_state="completed", actor=xl)
    return ho_so


def test_hoan_tat_co_canh_xac_nhan_va_canh_tu_dong(session, rule_set):
    cac = session.scalars(
        select(Transition).where(
            Transition.rule_set_id == rule_set.id,
            Transition.from_state == "completed",
            Transition.to_state == "closed",
        )
    ).all()
    nguoi = [c for c in cac if not c.is_system]
    he_thong = [c for c in cac if c.is_system]
    assert [c.activity_code for c in nguoi] == ["confirm"]
    assert [c.activity_code for c in he_thong] == ["auto-close"]
    # Ba ngày làm việc của lịch mẫu, báo trước một ngày
    assert he_thong[0].auto_after_hours == 24 and he_thong[0].warn_before_hours == 8
    assert he_thong[0].role_codes == set() and he_thong[0].guard_codes == []


def test_nguoi_gui_khong_xac_nhan_thi_tu_dong(session, loc_cua_bai, phong_ban):
    ho_so = _hoan_tat(session, phong_ban)
    bay = bay_gio(session)
    assert loc_cua_bai(quet_het_han_cho(session, bay + 24 * GIO - dt.timedelta(minutes=1))) == []

    assert loc_cua_bai(quet_het_han_cho(session, bay + 24 * GIO)) == [ho_so.id]
    assert ho_so.current_state == "closed"
    # Đồng hồ SLA dừng hẳn như mọi lần vào trạng thái kết thúc
    assert ho_so.sla_segment_since is None
    cuoi = case_history(session, ho_so.id)[-1]
    assert (cuoi.activity, cuoi.actor) == ("auto-close", TAC_NHAN_HAN_CHO)


def test_nguoi_gui_van_tu_xac_nhan_duoc(session, phong_ban):
    """Cạnh tự đóng cùng cặp không chiếm chỗ cạnh Xác nhận đạt: nhật ký phân biệt được hai
    cách đóng bằng mã hoạt động."""
    ho_so = _hoan_tat(session, phong_ban)
    nguoi_gui = Actor(id=NGUOI_GUI, roles=frozenset({"requester"}))
    assert {c.activity_code for c in allowed_transitions(session, ho_so, nguoi_gui)} >= {"confirm"}
    perform_transition(session, case_id=ho_so.id, to_state="closed", actor=nguoi_gui)
    cuoi = case_history(session, ho_so.id)[-1]
    assert (cuoi.activity, cuoi.actor) == ("confirm", NGUOI_GUI)


def test_hoan_tat_bao_truoc_mot_ngay_lam_viec(session, phong_ban):
    ho_so = _hoan_tat(session, phong_ban)
    bay = bay_gio(session)
    assert tu_dong(session, ho_so).luc == bay + 24 * GIO
    assert not tu_dong(session, ho_so, bay + 16 * GIO - dt.timedelta(minutes=1)).bao_truoc
    assert tu_dong(session, ho_so, bay + 16 * GIO).bao_truoc


# ---------------------------------------------------------------------------
# Chờ bổ sung thông tin tự đóng khi người gửi không trả lời (#143)
# ---------------------------------------------------------------------------


def _cho_bo_sung(session, phong_ban: str):
    """Người xử lý đã hỏi thêm, hồ sơ đang chờ người gửi bổ sung."""
    ho_so = _cho_phong(session, phong_ban)
    tp = Actor(id="tp-143", roles=frozenset({"approver"}), departments=frozenset({phong_ban}))
    xl = Actor(id="xl-143", roles=frozenset({"handler"}), departments=frozenset({phong_ban}))
    perform_transition(session, case_id=ho_so.id, to_state="in-progress", actor=tp)
    perform_transition(
        session, case_id=ho_so.id, to_state="awaiting-info", actor=xl, note="Cần số máy"
    )
    return ho_so


def test_cho_bo_sung_co_canh_tu_dong(session, rule_set):
    cac = session.scalars(
        select(Transition).where(
            Transition.rule_set_id == rule_set.id,
            Transition.from_state == "awaiting-info",
            Transition.is_system,
        )
    ).all()
    assert [(c.to_state, c.activity_code) for c in cac] == [("closed", "auto-close-no-info")]
    # Năm ngày làm việc của lịch mẫu, dấu nhắc từ ngày thứ ba (navigator chốt 15/10)
    assert cac[0].auto_after_hours == 40 and cac[0].warn_before_hours == 24
    assert cac[0].role_codes == set() and cac[0].guard_codes == []
    assert not cac[0].is_rework


def test_nguoi_gui_khong_bo_sung_thi_tu_dong(session, loc_cua_bai, phong_ban):
    ho_so = _cho_bo_sung(session, phong_ban)
    sla_truoc = ho_so.sla_running_seconds
    bay = bay_gio(session)
    assert loc_cua_bai(quet_het_han_cho(session, bay + 40 * GIO - dt.timedelta(minutes=1))) == []

    assert loc_cua_bai(quet_het_han_cho(session, bay + 40 * GIO)) == [ho_so.id]
    assert ho_so.current_state == "closed"
    # Thời gian chờ người gửi không tính vào hạn của phòng ban
    assert ho_so.sla_running_seconds == sla_truoc
    assert ho_so.sla_segment_since is None
    cuoi = case_history(session, ho_so.id)[-1]
    assert (cuoi.activity, cuoi.actor) == ("auto-close-no-info", TAC_NHAN_HAN_CHO)
    assert cuoi.note


def test_bo_sung_truoc_han_thi_khong_tu_dong(session, loc_cua_bai, phong_ban):
    ho_so = _cho_bo_sung(session, phong_ban)
    nguoi_gui = Actor(id=NGUOI_GUI, roles=frozenset({"requester"}))
    assert "auto-close-no-info" not in {
        c.activity_code for c in allowed_transitions(session, ho_so, nguoi_gui)
    }
    perform_transition(
        session, case_id=ho_so.id, to_state="in-progress", actor=nguoi_gui, note="Máy số 12"
    )
    assert loc_cua_bai(quet_het_han_cho(session, bay_gio(session) + 40 * GIO)) == []
    assert ho_so.current_state == "in-progress"


def test_cho_bo_sung_nhac_tu_ngay_thu_ba(session, phong_ban):
    ho_so = _cho_bo_sung(session, phong_ban)
    bay = bay_gio(session)
    td = tu_dong(session, ho_so)
    assert td.luc == bay + 40 * GIO
    assert td.canh.activity_label == "Tự đóng vì chưa bổ sung thông tin"
    assert not tu_dong(session, ho_so, bay + 16 * GIO - dt.timedelta(minutes=1)).bao_truoc
    assert tu_dong(session, ho_so, bay + 16 * GIO).bao_truoc
