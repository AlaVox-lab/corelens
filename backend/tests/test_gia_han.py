# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử hạn theo mức ưu tiên và gia hạn xử lý từng hồ sơ (#101).
#
# Giảng viên chốt ngày 08/10: hạn mặc định đi theo loại yêu cầu và mức ưu tiên (Khẩn 50%,
# Cao 75%, Bình thường 100%, Thấp 150% hạn chuẩn); điều phối viên gia hạn được, có lý do và
# ghi sự kiện, tối đa một lần; lần thứ hai chỉ trưởng bộ phận; mỗi lần tối đa X% hạn gốc;
# không gia hạn sau khi đóng. Navigator chốt 15/10: X = 50%, tổng tối đa 2 lần, nhập số giờ
# cộng thêm, ân hạn nhân cùng hệ số, trưởng phòng gia hạn khi hồ sơ đã leo thang.
#
# Lịch cả ngày cả tuần (fixture `lich_ca_ngay`) để giờ làm việc trùng giờ lịch — lịch thật
# kiểm ở test_lich_lam_viec.py (#199).

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import select

from app.models.workflow_config import Priority, RequestType, State, Transition
from app.rules.sla import an_han_giay, bay_gio, gioi_han_giay, han_goc_giay, ho_so_qua_han
from app.workflow.context import Actor
from app.workflow.engine import allowed_transitions, case_history, create_case, perform_transition
from app.workflow.errors import GuardViolation, NoteRequired
from app.workflow.escalation import quet_va_leo_thang

pytestmark = pytest.mark.usefixtures("lich_ca_ngay")

NGUOI_GUI = "nguoi-gui-101"
DIEU_PHOI = Actor(id="dp-101", roles=frozenset({"classifier"}))
GIO = 3600
GIA_HAN = "extend-deadline"


def _loai(session) -> RequestType:
    """Loại đầu tiên — Sự cố thiết bị trong dữ liệu mẫu, hạn chuẩn 8 giờ."""
    return session.scalars(
        select(RequestType).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()


def _truong_phong(phong_ban: str) -> Actor:
    return Actor(id="tp-101", roles=frozenset({"approver"}), departments=frozenset({phong_ban}))


def _da_phan_loai(session, uu_tien: str = "normal"):
    ho_so = create_case(session, title="Hồ sơ thử gia hạn", requester_id=NGUOI_GUI)
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=DIEU_PHOI,
        changes={"priority_code": uu_tien, "request_type_code": _loai(session).code},
    )
    return ho_so


def _dang_xu_ly(session, phong_ban: str, uu_tien: str = "normal"):
    ho_so = _da_phan_loai(session, uu_tien)
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


def _lui_dong_ho(session, ho_so, gio: float) -> None:
    ho_so.sla_segment_since = bay_gio(session) - dt.timedelta(hours=gio)
    session.flush()


def _gia_han(session, ho_so, actor, so_gio, ly_do: str | None = "Chờ linh kiện thay thế"):
    return perform_transition(
        session,
        case_id=ho_so.id,
        to_state=ho_so.current_state,
        actor=actor,
        note=ly_do,
        changes={"sla_extension_hours": so_gio},
    )


def _co_nut_gia_han(session, ho_so, actor) -> bool:
    return GIA_HAN in {c.activity_code for c in allowed_transitions(session, ho_so, actor)}


# ---------------------------------------------------------------------------
# Hạn theo mức ưu tiên
# ---------------------------------------------------------------------------


def test_he_so_uu_tien_nam_trong_du_lieu(session, rule_set):
    he_so = {m.code: m.sla_factor_percent for m in session.scalars(select(Priority)).all()}
    assert he_so == {"urgent": 50, "high": 75, "normal": 100, "low": 150}


@pytest.mark.parametrize(
    ("uu_tien", "han_gio", "an_han_gio"),
    [("urgent", 4, 1), ("high", 6, 1.5), ("normal", 8, 2), ("low", 12, 3)],
)
def test_han_va_an_han_theo_muc_uu_tien(session, rule_set, uu_tien, han_gio, an_han_gio):
    loai = _loai(session)
    assert (loai.sla_hours, loai.sla_grace_hours) == (8, 2)
    ho_so = _da_phan_loai(session, uu_tien)
    assert gioi_han_giay(session, ho_so) == han_gio * GIO
    assert an_han_giay(session, ho_so) == an_han_gio * GIO


def test_bo_quet_dung_han_theo_muc_uu_tien(session, rule_set, phong_ban):
    """Cùng chạy 5 giờ: hồ sơ Khẩn (hạn 4 giờ) quá hạn, hồ sơ Bình thường (8 giờ) thì chưa."""
    khan = _dang_xu_ly(session, phong_ban, "urgent")
    thuong = _dang_xu_ly(session, phong_ban, "normal")
    _lui_dong_ho(session, khan, 5)
    _lui_dong_ho(session, thuong, 5)
    qua_han = ho_so_qua_han(session)
    assert khan in qua_han and thuong not in qua_han


def test_doi_he_so_chi_can_sua_du_lieu(session, rule_set):
    ho_so = _da_phan_loai(session, "normal")
    session.get(Priority, "normal").sla_factor_percent = 200
    session.flush()
    assert gioi_han_giay(session, ho_so) == 16 * GIO


# ---------------------------------------------------------------------------
# Cạnh gia hạn trong dữ liệu
# ---------------------------------------------------------------------------


def test_ba_canh_gia_han_dung_vai_tro_va_rang_buoc(session, rule_set):
    cac = session.scalars(
        select(Transition).where(
            Transition.rule_set_id == rule_set.id, Transition.activity_code == GIA_HAN
        )
    ).all()
    theo_trang_thai = {c.from_state: c for c in cac}
    assert set(theo_trang_thai) == {"classified", "awaiting-acceptance", "escalated"}
    for c in cac:
        assert c.from_state == c.to_state and not c.is_system and c.requires_note
        assert GIA_HAN in c.guard_codes
    for ma in ("classified", "awaiting-acceptance"):
        c = theo_trang_thai[ma]
        assert c.role_codes == {"classifier"}
        assert {"first-extension", "actor-not-requester"} <= set(c.guard_codes)
    leo = theo_trang_thai["escalated"]
    assert leo.role_codes == {"approver"}
    assert {"extension-limit", "actor-in-case-department"} <= set(leo.guard_codes)


def test_khong_gia_han_duoc_khi_dang_xu_ly_hay_da_dong(session, rule_set, phong_ban):
    ho_so = _dang_xu_ly(session, phong_ban)
    assert not _co_nut_gia_han(session, ho_so, _truong_phong(phong_ban))
    # Trạng thái kết thúc không có cạnh nào đi ra — hết hồ sơ là hết gia hạn
    ket_thuc = session.scalars(
        select(State.code).where(State.rule_set_id == rule_set.id, State.is_terminal)
    ).all()
    assert not session.scalars(
        select(Transition).where(
            Transition.rule_set_id == rule_set.id, Transition.from_state.in_(ket_thuc)
        )
    ).all()


# ---------------------------------------------------------------------------
# Điều phối viên gia hạn lần đầu
# ---------------------------------------------------------------------------


def test_dieu_phoi_gia_han_thi_hon_dai_them_va_ghi_nhat_ky(session, rule_set):
    ho_so = _da_phan_loai(session)
    assert _co_nut_gia_han(session, ho_so, DIEU_PHOI)

    _gia_han(session, ho_so, DIEU_PHOI, "4")

    assert ho_so.current_state == "classified"
    assert (ho_so.sla_extension_hours, ho_so.sla_extension_total_hours) == (4, 4)
    assert ho_so.sla_extension_count == 1
    assert han_goc_giay(session, ho_so) == 8 * GIO
    assert gioi_han_giay(session, ho_so) == 12 * GIO

    cuoi = case_history(session, ho_so.id)[-1]
    assert cuoi.activity == GIA_HAN and cuoi.actor == DIEU_PHOI.id
    assert cuoi.note == "Chờ linh kiện thay thế"
    assert cuoi.changes["sla_extension_total_hours"] == {"from": 0, "to": 4}
    assert cuoi.changes["sla_extension_count"] == {"from": 0, "to": 1}


def test_dieu_phoi_chi_gia_han_mot_lan(session, rule_set, phong_ban):
    ho_so = _da_phan_loai(session)
    _gia_han(session, ho_so, DIEU_PHOI, "2")
    assert not _co_nut_gia_han(session, ho_so, DIEU_PHOI)

    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="awaiting-acceptance",
        actor=DIEU_PHOI,
        changes={"department_code": phong_ban},
    )
    assert not _co_nut_gia_han(session, ho_so, DIEU_PHOI)
    with pytest.raises(GuardViolation):
        _gia_han(session, ho_so, DIEU_PHOI, "2")


def test_dieu_phoi_gia_han_duoc_o_cho_phong_ban(session, rule_set, phong_ban):
    ho_so = _da_phan_loai(session)
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="awaiting-acceptance",
        actor=DIEU_PHOI,
        changes={"department_code": phong_ban},
    )
    _gia_han(session, ho_so, DIEU_PHOI, "3")
    assert ho_so.current_state == "awaiting-acceptance"
    assert gioi_han_giay(session, ho_so) == 11 * GIO


@pytest.mark.parametrize(
    ("uu_tien", "tran"), [("normal", 4), ("urgent", 2), ("low", 6)]
)
def test_moi_lan_toi_da_nua_han_goc(session, rule_set, uu_tien, tran):
    ho_so = _da_phan_loai(session, uu_tien)
    with pytest.raises(GuardViolation, match=f"tối đa {tran} giờ"):
        _gia_han(session, ho_so, DIEU_PHOI, str(tran + 1))
    _gia_han(session, ho_so, DIEU_PHOI, str(tran))
    assert ho_so.sla_extension_total_hours == tran


def test_doi_tran_gia_han_chi_can_sua_du_lieu(session, rule_set):
    ho_so = _da_phan_loai(session)
    _loai(session).sla_extension_max_percent = 25
    session.flush()
    with pytest.raises(GuardViolation, match="tối đa 2 giờ"):
        _gia_han(session, ho_so, DIEU_PHOI, "3")


@pytest.mark.parametrize("so_gio", ["0", "-1", "abc", "1.5", ""])
def test_so_gio_phai_la_so_nguyen_duong(session, rule_set, so_gio):
    ho_so = _da_phan_loai(session)
    with pytest.raises(GuardViolation):
        _gia_han(session, ho_so, DIEU_PHOI, so_gio)
    assert ho_so.sla_extension_count == 0


def test_gia_han_bat_buoc_ly_do(session, rule_set):
    ho_so = _da_phan_loai(session)
    with pytest.raises(NoteRequired):
        _gia_han(session, ho_so, DIEU_PHOI, "2", ly_do=None)


def test_khong_gui_duoc_tong_hay_so_lan(session, rule_set):
    """Tổng giờ và số lần do ràng buộc tự đặt — người dùng gửi kèm thì bị từ chối."""
    from app.workflow.errors import FieldNotPermitted

    ho_so = _da_phan_loai(session)
    with pytest.raises(FieldNotPermitted):
        perform_transition(
            session,
            case_id=ho_so.id,
            to_state="classified",
            actor=DIEU_PHOI,
            note="Thử",
            changes={"sla_extension_hours": "1", "sla_extension_total_hours": 99},
        )


# ---------------------------------------------------------------------------
# Trưởng phòng gia hạn lần hai, khi hồ sơ đã leo thang
# ---------------------------------------------------------------------------


def _da_leo_thang(session, phong_ban: str, gia_han_truoc: str | None = None):
    ho_so = _da_phan_loai(session)
    if gia_han_truoc:
        _gia_han(session, ho_so, DIEU_PHOI, gia_han_truoc)
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
    _lui_dong_ho(session, ho_so, gioi_han_giay(session, ho_so) / GIO + 3)
    quet_va_leo_thang(session)
    assert ho_so.current_state == "escalated"
    return ho_so


def test_truong_phong_gia_han_lan_hai_roi_het_luot(session, rule_set, phong_ban):
    ho_so = _da_leo_thang(session, phong_ban, gia_han_truoc="4")
    tp = _truong_phong(phong_ban)
    # Điều phối viên không có cạnh ở Đã leo thang
    assert not _co_nut_gia_han(session, ho_so, DIEU_PHOI)
    assert _co_nut_gia_han(session, ho_so, tp)

    _gia_han(session, ho_so, tp, "4")
    assert ho_so.current_state == "escalated"
    assert (ho_so.sla_extension_total_hours, ho_so.sla_extension_count) == (8, 2)
    assert gioi_han_giay(session, ho_so) == 16 * GIO

    # Hai lần là hết lượt: không còn nút, gọi thẳng cũng bị chặn
    assert not _co_nut_gia_han(session, ho_so, tp)
    with pytest.raises(GuardViolation):
        _gia_han(session, ho_so, tp, "1")


def test_truong_phong_gia_han_duoc_hai_lan_neu_dieu_phoi_chua_gia_han(
    session, rule_set, phong_ban
):
    ho_so = _da_leo_thang(session, phong_ban)
    tp = _truong_phong(phong_ban)
    _gia_han(session, ho_so, tp, "2")
    _gia_han(session, ho_so, tp, "2")
    assert ho_so.sla_extension_count == 2
    assert not _co_nut_gia_han(session, ho_so, tp)


def test_truong_phong_phong_khac_khong_gia_han_duoc(session, rule_set, phong_ban):
    ho_so = _da_leo_thang(session, phong_ban)
    nguoi_ngoai = Actor(
        id="tp-khac", roles=frozenset({"approver"}), departments=frozenset({"phong-khac"})
    )
    assert not _co_nut_gia_han(session, ho_so, nguoi_ngoai)


def test_gia_han_thi_het_qua_han(session, rule_set, phong_ban):
    """Đã chạy 11 giờ trên hạn 8 giờ: gia hạn 4 giờ thì hạn mới 12 giờ, không còn quá hạn."""
    ho_so = _da_leo_thang(session, phong_ban)
    tp = _truong_phong(phong_ban)
    assert ho_so.sla_running_seconds > gioi_han_giay(session, ho_so)
    _gia_han(session, ho_so, tp, "4")
    perform_transition(session, case_id=ho_so.id, to_state="in-progress", actor=tp)
    assert ho_so.sla_running_seconds < gioi_han_giay(session, ho_so)
    assert ho_so not in ho_so_qua_han(session)


def test_bo_quet_tinh_ca_phan_gia_han(session, rule_set, phong_ban):
    """Điều phối đã gia hạn 4 giờ: chạy 10 giờ là vượt hạn gốc 8 nhưng còn trong hạn 12.

    Đoạn đồng hồ mở đã lâu hơn ân hạn, nên chỉ phần gia hạn trong truy vấn của bộ quét giữ
    hồ sơ khỏi bị leo thang — bài này canh đúng chỗ đó.
    """
    ho_so = _da_phan_loai(session)
    _gia_han(session, ho_so, DIEU_PHOI, "4")
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
    _lui_dong_ho(session, ho_so, 10)
    assert ho_so not in ho_so_qua_han(session)
    _lui_dong_ho(session, ho_so, 13)
    assert ho_so in ho_so_qua_han(session)


def test_dong_thoi_gian_ke_lai_duoc_gia_tri_so(session, rule_set):
    """Giá trị gia hạn là số; phần kể lại thay đổi trên dòng thời gian phải đọc được nó.

    Trước khi có bài này, trang hồ sơ đã gia hạn trả lỗi 500 — chỉ lộ ra ở đường thật.
    """
    from app.workflow.routes import _nhan_danh_muc, _thay_doi

    ho_so = _da_phan_loai(session)
    _gia_han(session, ho_so, DIEU_PHOI, "3")
    ke = {
        t.field: (t.before.label if t.before else None, t.after.label)
        for t in _thay_doi(case_history(session, ho_so.id)[-1], _nhan_danh_muc(session))
    }
    assert ke["sla_extension_total_hours"] == ("0", "3")
    assert ke["sla_extension_count"] == ("0", "1")
