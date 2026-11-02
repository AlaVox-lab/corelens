# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Hai bộ quy tắc chạy song song (#278).
#
# Câu hỏi của buổi báo cáo 29/10: doanh nghiệp đổi quy trình thì hồ sơ đang chạy ra sao. Câu
# trả lời của thiết kế: mỗi hồ sơ ghi `rule_set_id` lúc tạo và engine chỉ tra cạnh, trạng thái
# trong đúng bộ đó — hồ sơ cũ đi tiếp theo bộ cũ tới khi kết thúc, hồ sơ mới theo bộ đang bật.
#
# Bài dựng bộ thứ hai NGAY TRONG GIAO DỊCH CỦA BÀI bằng cách chép bộ đang bật rồi đổi ba chỗ, như
# một lần đổi quy trình thật — nên chạy được trên dữ liệu khởi tạo nào cũng được, và hoàn tác
# sạch cùng bài:
#
#   1. bỏ cạnh người gửi tự hủy ở trạng thái bắt đầu
#   2. đổi mã hoạt động của cạnh phân loại — nhật ký phải ghi đúng mã của bộ mà hồ sơ theo
#   3. bật đồng hồ SLA ở trạng thái chờ phòng ban nhận — đồng hồ của hai hồ sơ phải tính khác nhau
#   4. đổi mã trạng thái đã hủy — danh sách phải tra nhãn, kết thúc theo bộ của từng hồ sơ (#299)
#
# Nửa sau của tệp kiểm các màn liệt kê (#299): hồ sơ cũ còn mở vẫn nằm trong hàng đợi.
from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.auth.dependencies import current_actor
from app.db import get_session
from app.main import app
from app.models.case import EventLog
from app.models.workflow_config import (
    MessageKind,
    Priority,
    RequestType,
    RuleSet,
    State,
    Transition,
)
from app.rules.sla import bay_gio, da_chay_giay
from app.workflow.context import Actor
from app.workflow.messages import gui_loi_nhan
from app.workflow.engine import (
    allowed_transitions,
    case_history,
    create_case,
    get_active_rule_set,
    perform_transition,
)
from app.workflow.errors import TransitionNotAllowed

pytestmark = pytest.mark.usefixtures("lich_ca_ngay")

NGUOI_GUI = "nguoi-gui-278"
NGUOI_GUI_AI = Actor(id=NGUOI_GUI, roles=frozenset({"requester"}))
DIEU_PHOI = Actor(id="dp-278", roles=frozenset({"classifier"}))

MA_PHAN_LOAI_MOI = "classify-v2-278"
MA_HUY_MOI = "da-huy-278"


def _canh(
    session, bo: int, *, ma: str | None = None, tu: str | None = None, den: str | None = None
):
    """Cạnh người của một bộ, tra theo mã hoạt động hay theo cặp trạng thái."""
    dieu_kien = [Transition.rule_set_id == bo, Transition.is_system.is_(False)]
    if ma is not None:
        dieu_kien.append(Transition.activity_code == ma)
    if tu is not None:
        dieu_kien.append(Transition.from_state == tu)
    if den is not None:
        dieu_kien.append(Transition.to_state == den)
    return session.scalars(select(Transition).where(*dieu_kien)).first()


def _chep_bo(session, cu: int, doi_ma: tuple[str, str]) -> int:
    """Chép trạng thái, cạnh, vai trò và ràng buộc của bộ `cu` sang một bộ mới chưa bật, đổi mã
    một trạng thái `doi_ma = (mã cũ, mã mới)` trên đường chép — khóa ngoại không cho đổi sau."""
    tu, sang = doi_ma

    def ma(cot: str) -> str:
        return f"CASE WHEN {cot} = '{tu}' THEN '{sang}' ELSE {cot} END"

    moi = session.execute(text("SELECT max(id) + 1 FROM rule_sets")).scalar_one()
    session.execute(
        text(
            "INSERT INTO rule_sets (id, version, label, effective_from, is_active) "
            "VALUES (:moi, 'thu-278', 'Bộ quy tắc thử #278', now(), FALSE)"
        ),
        {"moi": moi},
    )
    session.execute(
        text(
            "INSERT INTO states (rule_set_id, code, label, description, is_initial, is_terminal, "
            "sla_running, display_order) "
            f"SELECT :moi, {ma('code')}, label, description, is_initial, is_terminal, sla_running, "
            "display_order FROM states WHERE rule_set_id = :cu"
        ),
        {"moi": moi, "cu": cu},
    )
    cot = (
        "activity_code, activity_label, is_system, requires_note, "
        "note_label, display_order, is_rework, from_is_terminal, reopen_window_hours, "
        "restarts_sla, accepts_attachments, auto_after_hours, warn_before_hours, primary_scope"
    )
    session.execute(
        text(
            f"INSERT INTO transitions (rule_set_id, from_state, to_state, {cot}) "
            f"SELECT :moi, {ma('from_state')}, {ma('to_state')}, {cot} "
            "FROM transitions WHERE rule_set_id = :cu"
        ),
        {"moi": moi, "cu": cu},
    )
    # Cạnh mới có định danh mới: ghép với cạnh cũ theo khóa duy nhất của bảng
    ghep = (
        "FROM transitions c JOIN transitions m ON m.rule_set_id = :moi AND c.rule_set_id = :cu "
        f"AND m.from_state = {ma('c.from_state')} AND m.to_state = {ma('c.to_state')} "
        "AND m.is_system = c.is_system"
    )
    for bang, cot_phu in (("transition_roles", "role_code"), ("transition_guards", "guard_code")):
        session.execute(
            text(
                f"INSERT INTO {bang} (transition_id, {cot_phu}) "
                f"SELECT m.id, x.{cot_phu} {ghep} JOIN {bang} x ON x.transition_id = c.id"
            ),
            {"moi": moi, "cu": cu},
        )
    return moi


def _bat_bo(session, ma: int) -> None:
    """Đổi bộ đang bật. Hai câu lệnh: chỉ mục duy nhất từng phần không cho hai bộ cùng bật."""
    session.execute(text("UPDATE rule_sets SET is_active = FALSE WHERE is_active"))
    session.execute(text("UPDATE rule_sets SET is_active = TRUE WHERE id = :ma"), {"ma": ma})
    session.expire_all()


@pytest.fixture
def hai_bo(session, rule_set):
    """(bộ cũ, bộ mới, trạng thái bắt đầu, trạng thái hủy, trạng thái chờ phòng ban nhận)."""
    cu = rule_set.id
    bat_dau = session.scalars(
        select(State.code).where(State.rule_set_id == cu, State.is_initial)
    ).one()
    phan_loai = _canh(session, cu, ma="classify")
    huy = _canh(session, cu, tu=bat_dau, ma="cancel")
    chuyen_phong = phan_loai and _canh(session, cu, tu=phan_loai.to_state, ma="route-to-department")
    if phan_loai is None or huy is None or chuyen_phong is None:
        pytest.skip("Dữ liệu khởi tạo không có đủ cạnh phân loại, hủy và chuyển phòng để dựng bài.")
    cho_nhan = chuyen_phong.to_state
    if session.get(State, (cu, cho_nhan)).sla_running:
        pytest.skip("Bộ đang bật đã chạy đồng hồ ở trạng thái chờ phòng ban nhận.")

    moi = _chep_bo(session, cu, doi_ma=(huy.to_state, MA_HUY_MOI))
    session.execute(
        text("DELETE FROM transitions WHERE rule_set_id = :moi AND id = :id"),
        {"moi": moi, "id": _canh(session, moi, tu=bat_dau, den=MA_HUY_MOI).id},
    )
    session.execute(
        text(
            "UPDATE transitions SET activity_code = :ma WHERE rule_set_id = :moi "
            "AND activity_code = 'classify'"
        ),
        {"ma": MA_PHAN_LOAI_MOI, "moi": moi},
    )
    session.execute(
        text("UPDATE states SET sla_running = TRUE WHERE rule_set_id = :moi AND code = :ma"),
        {"moi": moi, "ma": cho_nhan},
    )
    # Hai lần giao thêm việc cho vai trò — cùng mã trạng thái, khác hàng đợi giữa hai bộ (#299):
    # điều phối viên can thiệp được hồ sơ đang xử lý, trưởng phòng ghi nhận thay phần bổ sung
    # thông tin. Vai trò là của phép thử, không phải của dữ liệu khởi tạo
    giao_them = (
        (_dang_xu_ly(session, cu, cho_nhan), "classifier"),
        (_cho_bo_sung(session, cu, cho_nhan), "approver"),
    )
    for tu, vai in giao_them:
        session.execute(
            text(
                "INSERT INTO transition_roles (transition_id, role_code) "
                "SELECT id, :vai FROM transitions WHERE rule_set_id = :moi AND from_state = :tu "
                "AND NOT is_system ORDER BY display_order LIMIT 1 ON CONFLICT DO NOTHING"
            ),
            {"vai": vai, "moi": moi, "tu": tu},
        )
    session.flush()
    return cu, moi, bat_dau, huy.to_state, cho_nhan


def _dang_xu_ly(session, bo: int, cho_nhan: str) -> str:
    """Trạng thái phòng ban nhận việc vào — đích của bước chính rời trạng thái chờ nhận."""
    canh = session.scalars(
        select(Transition).where(
            Transition.rule_set_id == bo,
            Transition.from_state == cho_nhan,
            Transition.primary_scope.is_not(None),
        )
    ).first()
    if canh is None:
        pytest.skip("Trạng thái chờ phòng ban nhận không có bước chính.")
    return canh.to_state


def _cho_bo_sung(session, bo: int, cho_nhan: str) -> str:
    """Trạng thái phòng ban hỏi thêm người gửi từ trạng thái chờ nhận — cạnh bắt buộc ghi chú
    dẫn tới trạng thái có đường quay về chờ nhận."""
    for canh in session.scalars(
        select(Transition)
        .where(
            Transition.rule_set_id == bo,
            Transition.from_state == cho_nhan,
            Transition.requires_note,
            Transition.is_system.is_(False),
        )
        .order_by(Transition.display_order)
    ):
        if _canh(session, bo, tu=canh.to_state, den=cho_nhan) is not None:
            return canh.to_state
    pytest.skip("Phòng ban không có đường hỏi thêm người gửi từ trạng thái chờ nhận.")


def _tao(session):
    loai = session.scalars(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    return create_case(
        session,
        title="Máy chiếu phòng họp không lên hình",
        requester_id=NGUOI_GUI,
        request_type_code=loai,
    )


def _den_cho_nhan(session, ho_so, phong_ban: str, cho_nhan: str) -> None:
    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()
    phan_loai = next(c for c in allowed_transitions(session, ho_so, DIEU_PHOI) if c.primary_scope)
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state=phan_loai.to_state,
        actor=DIEU_PHOI,
        changes={"priority_code": uu_tien},
    )
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state=cho_nhan,
        actor=DIEU_PHOI,
        changes={"department_code": phong_ban},
    )


def _truong_phong(phong_ban: str) -> Actor:
    return Actor(id="tp-278", roles=frozenset({"approver"}), departments=frozenset({phong_ban}))


def _lui_dong_ho(session, ho_so, gio: float) -> None:
    ho_so.sla_segment_since = bay_gio(session) - dt.timedelta(hours=gio)
    session.flush()


# ---------------------------------------------------------------------------


def test_ho_so_moi_nhan_bo_dang_bat_ho_so_cu_giu_bo_cu(session, hai_bo):
    cu, moi, bat_dau, _, _ = hai_bo
    ho_so_cu = _tao(session)

    _bat_bo(session, moi)
    ho_so_moi = _tao(session)

    assert get_active_rule_set(session).id == moi
    assert ho_so_cu.rule_set_id == cu
    assert ho_so_moi.rule_set_id == moi
    assert ho_so_cu.current_state == ho_so_moi.current_state == bat_dau


def test_nut_cua_moi_ho_so_theo_dung_bo_cua_no(session, hai_bo):
    """Cạnh hủy chỉ còn trong bộ cũ: hồ sơ cũ vẫn thấy và đi được, hồ sơ mới thì không."""
    cu, moi, _, da_huy, _ = hai_bo
    ho_so_cu = _tao(session)
    _bat_bo(session, moi)
    ho_so_moi = _tao(session)

    nut_cu = allowed_transitions(session, ho_so_cu, NGUOI_GUI_AI)
    nut_moi = allowed_transitions(session, ho_so_moi, NGUOI_GUI_AI)

    assert {c.rule_set_id for c in nut_cu} == {cu}
    assert {c.rule_set_id for c in nut_moi} == {moi}
    assert da_huy in {c.to_state for c in nut_cu}
    assert da_huy not in {c.to_state for c in nut_moi}

    for dich in (da_huy, MA_HUY_MOI):
        with pytest.raises(TransitionNotAllowed):
            perform_transition(session, case_id=ho_so_moi.id, to_state=dich, actor=NGUOI_GUI_AI)
    perform_transition(session, case_id=ho_so_cu.id, to_state=da_huy, actor=NGUOI_GUI_AI)
    assert ho_so_cu.current_state == da_huy


def test_hai_ho_so_di_tiep_nhat_ky_ghi_dung_hoat_dong_cua_bo(session, hai_bo, phong_ban):
    _, moi, _, _, cho_nhan = hai_bo
    ho_so_cu = _tao(session)
    _bat_bo(session, moi)
    ho_so_moi = _tao(session)

    for ho_so in (ho_so_cu, ho_so_moi):
        _den_cho_nhan(session, ho_so, phong_ban, cho_nhan)
        assert ho_so.current_state == cho_nhan

    nhat_ky_cu = case_history(session, ho_so_cu.id)
    nhat_ky_moi = case_history(session, ho_so_moi.id)
    assert [d.activity for d in nhat_ky_cu][0] == "classify"
    assert [d.activity for d in nhat_ky_moi][0] == MA_PHAN_LOAI_MOI
    # Cùng một đường đi, cùng số dòng — chỉ tên hoạt động theo bộ của từng hồ sơ
    assert [(d.from_state, d.to_state) for d in nhat_ky_cu] == [
        (d.from_state, d.to_state) for d in nhat_ky_moi
    ]
    dem = session.execute(
        select(EventLog.case_id).where(EventLog.case_id.in_([ho_so_cu.id, ho_so_moi.id]))
    ).all()
    assert len(dem) == 4


def test_dong_ho_han_moi_ho_so_tinh_theo_bo_cua_no(session, hai_bo, phong_ban):
    """Bộ mới bật đồng hồ ở trạng thái chờ phòng ban nhận; bộ cũ thì không."""
    _, moi, _, _, cho_nhan = hai_bo
    ho_so_cu = _tao(session)
    _bat_bo(session, moi)
    ho_so_moi = _tao(session)
    for ho_so in (ho_so_cu, ho_so_moi):
        _den_cho_nhan(session, ho_so, phong_ban, cho_nhan)
        _lui_dong_ho(session, ho_so, gio=2)

    assert da_chay_giay(session, ho_so_cu) == 0
    assert 7100 < da_chay_giay(session, ho_so_moi) < 7300

    # Phòng ban nhận: đoạn vừa đóng chỉ cộng vào đồng hồ của hồ sơ theo bộ mới
    truong_phong = _truong_phong(phong_ban)
    for ho_so in (ho_so_cu, ho_so_moi):
        nhan = next(c for c in allowed_transitions(session, ho_so, truong_phong) if c.primary_scope)
        perform_transition(session, case_id=ho_so.id, to_state=nhan.to_state, actor=truong_phong)

    assert ho_so_cu.sla_running_seconds == 0
    assert 7100 < ho_so_moi.sla_running_seconds < 7300


def test_tat_bo_moi_bat_lai_bo_cu_khong_doi_ho_so_nao(session, hai_bo):
    """Đổi qua đổi lại bộ đang bật chỉ quyết định hồ sơ TẠO SAU đó, không chạm hồ sơ đã có."""
    cu, moi, _, _, _ = hai_bo
    _bat_bo(session, moi)
    ho_so_moi = _tao(session)
    _bat_bo(session, cu)

    assert session.get(RuleSet, moi).is_active is False
    assert ho_so_moi.rule_set_id == moi
    assert {c.rule_set_id for c in allowed_transitions(session, ho_so_moi, NGUOI_GUI_AI)} == {moi}


# ---------------------------------------------------------------------------
# Màn liệt kê sau khi đổi bộ (#299)
# ---------------------------------------------------------------------------


@pytest.fixture
def client(session):
    """Máy khách HTTP đổi được người gọi. Phần dựng cảnh phải `commit`, như test_coordination.py."""
    dang_goi = {"actor": None}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: dang_goi["actor"]
    with TestClient(app) as c:
        c.dang_goi = dang_goi
        yield c
    app.dependency_overrides.clear()


def _goi(client, actor: Actor, duong: str) -> dict:
    client.dang_goi["actor"] = actor
    tra_ve = client.get(duong)
    assert tra_ve.status_code == 200, tra_ve.text
    return tra_ve.json()


def test_hang_doi_dieu_phoi_giu_ho_so_cua_bo_cu(client, session, hai_bo):
    _, moi, bat_dau, _, _ = hai_bo
    ho_so_cu = _tao(session)
    _bat_bo(session, moi)
    ho_so_moi = _tao(session)
    session.commit()

    hang_doi = _goi(client, DIEU_PHOI, "/coordination/queue?limit=200")
    ma = {m["id"] for m in hang_doi["items"]}
    assert {ho_so_cu.id, ho_so_moi.id} <= ma
    nhom = {g["code"]: g["count"] for g in hang_doi["groups"]}
    loc = _goi(client, DIEU_PHOI, f"/coordination/queue?limit=200&state={bat_dau}")
    assert {ho_so_cu.id, ho_so_moi.id} <= {m["id"] for m in loc["items"]}
    assert nhom[bat_dau] == loc["total"]


def test_hang_doi_phong_ban_giu_ho_so_cua_bo_cu(client, session, hai_bo, phong_ban):
    _, moi, _, _, cho_nhan = hai_bo
    ho_so_cu = _tao(session)
    _den_cho_nhan(session, ho_so_cu, phong_ban, cho_nhan)
    _bat_bo(session, moi)
    ho_so_moi = _tao(session)
    _den_cho_nhan(session, ho_so_moi, phong_ban, cho_nhan)
    session.commit()

    hang_doi = _goi(client, _truong_phong(phong_ban), "/department/queue?limit=200")
    muc = {m["id"]: m for m in hang_doi["items"]}
    assert {ho_so_cu.id, ho_so_moi.id} <= set(muc)
    # Hồ sơ cũ chưa chạy đồng hồ ở trạng thái này, hồ sơ mới thì có: nhóm độ gấp theo bộ của hồ sơ
    assert muc[ho_so_cu.id]["urgency"] == cho_nhan
    assert muc[ho_so_moi.id]["urgency"] != cho_nhan
    assert muc[ho_so_cu.id]["needs_my_action"] and muc[ho_so_moi.id]["needs_my_action"]


def test_ho_so_cua_toi_tra_nhan_va_ket_thuc_theo_bo_cua_ho_so(client, session, hai_bo):
    """Bộ mới đổi mã trạng thái đã hủy: hồ sơ cũ đã hủy vẫn là hồ sơ đã kết thúc, đúng nhãn."""
    cu, moi, _, da_huy, _ = hai_bo
    ho_so_huy = _tao(session)
    perform_transition(session, case_id=ho_so_huy.id, to_state=da_huy, actor=NGUOI_GUI_AI)
    ho_so_mo = _tao(session)
    _bat_bo(session, moi)
    session.commit()

    ds = _goi(client, NGUOI_GUI_AI, "/requests?limit=200")
    muc = {m["id"]: m for m in ds["items"]}
    nhan_huy = session.get(State, (cu, da_huy)).label
    assert muc[ho_so_huy.id]["state"] == {"code": da_huy, "label": nhan_huy, "is_terminal": True}
    assert muc[ho_so_mo.id]["state"]["is_terminal"] is False
    assert ds["open_count"] == 1
    assert {"code": da_huy, "count": 1, "is_terminal": True}.items() <= {
        g["code"]: g for g in ds["groups"]
    }[da_huy].items()


def test_hop_thu_tra_nhan_theo_bo_cua_tung_ho_so(client, session, hai_bo):
    """Cuộc của hai bộ, mỗi bộ có một hồ sơ đã hủy ở mã trạng thái chỉ bộ đó có."""
    _, moi, _, da_huy, _ = hai_bo
    loai = session.scalars(
        select(MessageKind)
        .where(
            MessageKind.owner_only.is_(False),
            MessageKind.department_stage_only.is_(False),
            MessageKind.reask_after_hours.is_(None),
            MessageKind.hidden_from_requester.is_(False),
        )
        .order_by(MessageKind.display_order)
    ).first()
    if loai is None:
        pytest.skip("Dữ liệu khởi tạo chưa khai loại lời nhắn thường.")
    ho_so_cu = _tao(session)
    gui_loi_nhan(session, ho_so_cu, NGUOI_GUI_AI, loai.code, "Máy chiếu vẫn không lên hình")
    ho_so_cu_huy = _tao(session)
    gui_loi_nhan(session, ho_so_cu_huy, NGUOI_GUI_AI, loai.code, "Thôi, đã mượn được máy khác")
    perform_transition(session, case_id=ho_so_cu_huy.id, to_state=da_huy, actor=NGUOI_GUI_AI)
    _bat_bo(session, moi)
    ho_so_moi = _tao(session)
    gui_loi_nhan(session, ho_so_moi, NGUOI_GUI_AI, loai.code, "Thêm một máy chiếu nữa")
    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()
    perform_transition(
        session, case_id=ho_so_moi.id, to_state=_canh(session, moi, ma=MA_PHAN_LOAI_MOI).to_state,
        actor=DIEU_PHOI, changes={"priority_code": uu_tien},
    )
    perform_transition(session, case_id=ho_so_moi.id, to_state=MA_HUY_MOI, actor=NGUOI_GUI_AI)
    session.commit()

    cuoc = {c["case_id"]: c for c in _goi(client, NGUOI_GUI_AI, "/inbox?limit=200")["items"]}
    assert cuoc[ho_so_moi.id]["state"]["code"] == MA_HUY_MOI
    assert cuoc[ho_so_moi.id]["state"]["is_terminal"] is True
    assert cuoc[ho_so_cu.id]["state"]["is_terminal"] is False
    assert cuoc[ho_so_cu_huy.id]["state"] == {
        "code": da_huy, "label": session.get(State, (ho_so_cu_huy.rule_set_id, da_huy)).label,
        "is_terminal": True,
    }
    # Điều phối viên chưa nhắn gì: hồ sơ cũ vào hộp thư của họ vì đang ở hàng đợi điều phối
    cuoc_dp = _goi(client, DIEU_PHOI, "/inbox?limit=200")["items"]
    assert ho_so_cu.id in {c["case_id"] for c in cuoc_dp}


def test_cung_ma_trang_thai_khac_hang_doi_giua_hai_bo(client, session, hai_bo, phong_ban):
    """Bộ mới cho điều phối viên can thiệp hồ sơ đang xử lý: chỉ hồ sơ của bộ mới vào hàng đợi
    điều phối, hồ sơ bộ cũ cùng trạng thái thì không — lọc theo mã thôi là gộp nhầm hai bộ."""
    cu, moi, _, _, cho_nhan = hai_bo
    dang_xu_ly = _dang_xu_ly(session, cu, cho_nhan)
    truong_phong = _truong_phong(phong_ban)
    ho_so_cu = _tao(session)
    _bat_bo(session, moi)
    ho_so_moi = _tao(session)
    for ho_so in (ho_so_cu, ho_so_moi):
        _den_cho_nhan(session, ho_so, phong_ban, cho_nhan)
        perform_transition(session, case_id=ho_so.id, to_state=dang_xu_ly, actor=truong_phong)
    session.commit()

    ma = {m["id"] for m in _goi(client, DIEU_PHOI, "/coordination/queue?limit=200")["items"]}
    assert ho_so_moi.id in ma
    assert ho_so_cu.id not in ma


def test_nhom_theo_doi_cua_phong_ban_theo_bo_cua_ho_so(client, session, hai_bo, phong_ban):
    """Bộ mới cho trưởng phòng ghi nhận thay phần bổ sung thông tin, nên ở bộ mới trạng thái đó là
    việc của phòng; ở bộ cũ nó chỉ là nhóm theo dõi "Chờ người gửi"."""
    cu, moi, _, _, cho_nhan = hai_bo
    cho_bo_sung = _cho_bo_sung(session, cu, cho_nhan)
    truong_phong = _truong_phong(phong_ban)
    ho_so_cu = _tao(session)
    _bat_bo(session, moi)
    ho_so_moi = _tao(session)
    for ho_so in (ho_so_cu, ho_so_moi):
        _den_cho_nhan(session, ho_so, phong_ban, cho_nhan)
        perform_transition(
            session, case_id=ho_so.id, to_state=cho_bo_sung, actor=truong_phong,
            note="Cần thêm số phòng họp",
        )
    session.commit()

    muc = {m["id"]: m for m in _goi(client, truong_phong, "/department/queue?limit=200")["items"]}
    assert muc[ho_so_cu.id]["urgency"] == "cho-nguoi-gui"
    assert muc[ho_so_moi.id]["urgency"] != "cho-nguoi-gui"
