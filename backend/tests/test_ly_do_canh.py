# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm điểm cuối liệt kê cạnh kèm lý do không đi được (#424): `GET /core/v1/workflow/requests/{id}/transition-options`.
#
# Bốn nhóm bài:
#
#   1. Mỗi loại lý do một bài — sai vai, cạnh chỉ hệ thống, ràng buộc không cần nhập liệu (`actor-not-requester`,
#      `actor-in-case-department`, thu đủ nhiều ràng buộc), điều kiện trên cạnh (quy trình mua sắm, #397). Mã và
#      thông điệp so với CHÍNH lỗi `perform_transition` ném khi gọi cạnh đó — một nguồn câu chữ.
#   2. `requires_input`, hồ sơ kết thúc, 404, chỉ đọc.
#   3. Bất biến — trên hồ sơ ở mọi trạng thái của hai quy trình và nhiều vai, tập cạnh `allowed` trùng hệt
#      `allowed_transitions()` và `allowed_transitions` của chi tiết hồ sơ.
#   4. Tài khoản dịch vụ — token client credentials thật gọi qua `/core/v1`.
#
# Không bài nào viết mã trạng thái, mã cạnh hay ngưỡng: cạnh chọn theo dữ liệu quy tắc (vai, ràng buộc, điều kiện)
# rồi hồ sơ được đặt vào trạng thái nguồn của cạnh đó. Mã ràng buộc viết ra là mã của seed mà bài nói tới.

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from app.auth.dependencies import current_actor, current_claims
from app.db import get_session
from app.main import app
from app.models.case import EventLog, Request
from app.models.workflow_config import Department, RequestType, RuleSet, State, Transition, TransitionCondition
from app.rules.dieu_kien import MA_RANG_BUOC as MA_DIEU_KIEN
from app.rules.guards import GUARD_REGISTRY
from app.workflow.context import Actor
from app.workflow.coordination import VAI_TRO_DIEU_PHOI
from app.workflow.engine import allowed_transitions, create_case, perform_transition, xet_cac_canh
from app.workflow.errors import GuardViolation, RoleNotPermitted, SystemTransitionOnly, TransitionError
from app.workflow.routes import xep_o_nhap
from tests.test_loi_api import token_dich_vu  # noqa: F401 — fixture dùng lại
from tests.truong_mau import chi_tiet_mau

LOI = "/core/v1/workflow"


@pytest.fixture
def hai_phong(session) -> tuple[str, str]:
    ma = session.scalars(select(Department.code).where(Department.is_active).order_by(Department.display_order)).all()
    if len(ma) < 2:
        pytest.skip("Cần hai phòng ban đang hoạt động.")
    return ma[0], ma[1]


@pytest.fixture
def client(session):
    tac_nhan = {"actor": None}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: tac_nhan["actor"]
    app.dependency_overrides[current_claims] = lambda: {"sub": tac_nhan["actor"].id, "name": tac_nhan["actor"].name}
    with TestClient(app) as c:
        def la(ai: Actor) -> TestClient:
            tac_nhan["actor"] = ai
            return c

        c.la = la
        yield c
    app.dependency_overrides.clear()


def _lua_chon(client, ai: Actor, ma: int) -> dict:
    tra = client.la(ai).get(f"{LOI}/requests/{ma}/transition-options")
    assert tra.status_code == 200, tra.text
    return tra.json()


def _cua(ket_qua: dict, canh: Transition) -> dict:
    return next(
        c for c in ket_qua["transitions"]
        if (c["activity_code"], c["to_state"], c["is_system"]) == (canh.activity_code, canh.to_state, canh.is_system)
    )


def _ho_so(session, nguoi_gui: Actor, *, loai: str | None = None, **dat) -> Request:
    """Một hồ sơ qua engine, rồi đặt thẳng trạng thái và trường cho bài — như test_nguoi_xu_ly.py."""
    ho_so = create_case(session, title="Thử lý do cạnh #424", description="Thử #424.", requester_id=nguoi_gui.id,
                        requester_label=nguoi_gui.label, request_type_code=loai)
    if dat:
        session.execute(update(Request).where(Request.id == ho_so.id).values(**dat))
    session.commit()
    session.expire_all()
    return session.get(Request, ho_so.id)


def _loi_engine(session, ho_so: Request, ai: Actor, canh: Transition) -> TransitionError | None:
    """Lỗi `perform_transition` ném khi tác nhân cứ gọi cạnh — trong điểm lưu, hoàn tác ngay."""
    diem_luu = session.begin_nested()
    try:
        perform_transition(session, case_id=ho_so.id, to_state=canh.to_state, actor=ai, note="Thử #424.")
    except TransitionError as loi:
        return loi
    finally:
        diem_luu.rollback()
        session.expire_all()
    return None


def _cac_canh(session, rule_set_id: int) -> list[Transition]:
    return session.scalars(
        select(Transition).where(Transition.rule_set_id == rule_set_id).order_by(Transition.display_order)
    ).all()


def _canh_chi_rang_buoc_khong_nhap_lieu(session, rule_set_id: int, ma_rang_buoc: str) -> Transition:
    """Cạnh người đi đầu tiên mang ràng buộc này, mọi ràng buộc của nó đều không cần nhập liệu, không điều kiện —
    để lỗi engine ném khi gọi cạnh chắc chắn là của ràng buộc đang kiểm."""
    canh = next(
        (
            c for c in _cac_canh(session, rule_set_id)
            if not c.is_system and not c.conditions and ma_rang_buoc in c.guard_codes
            and all(GUARD_REGISTRY[g].input_free for g in c.guard_codes)
        ),
        None,
    )
    if canh is None:
        pytest.skip(f"Dữ liệu khởi tạo không có cạnh chỉ mang ràng buộc không cần nhập liệu '{ma_rang_buoc}'.")
    return canh


def _bo_mua_sam(session) -> RuleSet:
    """Bộ đang bật đầu tiên có điều kiện trên cạnh (#397) — quy trình mua sắm mẫu."""
    ma_bo = session.scalar(
        select(Transition.rule_set_id).join(TransitionCondition, TransitionCondition.transition_id == Transition.id)
        .join(RuleSet, RuleSet.id == Transition.rule_set_id).where(RuleSet.is_active).limit(1)
    )
    if ma_bo is None:
        pytest.skip("Dữ liệu khởi tạo chưa khai điều kiện trên cạnh (infra/seed/07).")
    return session.get(RuleSet, ma_bo)


def _gia_tri_lam_sai(phep: str, nguong):
    """Một giá trị làm điều kiện `trường <phep> nguong` SAI."""
    return {"<": nguong, "<=": nguong + 1, ">": nguong, ">=": nguong - 1, "=": f"khac-{nguong}", "!=": nguong}[phep]


def _loai_cua_bo(session, bo: RuleSet) -> RequestType:
    return session.scalars(
        select(RequestType).where(RequestType.process_code == bo.process_code).order_by(RequestType.code)
    ).first()


# ---------------------------------------------------------------------------
# 1. Mỗi loại lý do
# ---------------------------------------------------------------------------


def test_sai_vai(client, session, rule_set):
    """Người gửi ở trạng thái đầu: cạnh của vai khác bị chặn đúng một lý do quyền, câu chữ của engine."""
    gui = Actor(id="ldc-gui-424", name="Người gửi 424", roles=frozenset({"requester"}))
    ho_so = _ho_so(session, gui)
    ket_qua = _lua_chon(client, gui, ho_so.id)
    assert ket_qua["case_id"] == ho_so.id and ket_qua["state"]["code"] == ho_so.current_state

    cac_canh = [c for c in _cac_canh(session, rule_set.id) if c.from_state == ho_so.current_state]
    assert [(c["activity_code"], c["to_state"]) for c in ket_qua["transitions"]] == [
        (c.activity_code, c.to_state) for c in cac_canh
    ]
    sai_vai = [c for c in cac_canh if not c.is_system and not (gui.roles & c.role_codes)]
    assert sai_vai, "trạng thái đầu phải có cạnh của vai khác người gửi"
    for canh in sai_vai:
        cua = _cua(ket_qua, canh)
        assert cua["allowed"] is False
        assert [(l["code"], l["category"], l["condition"]) for l in cua["reasons"]] == [
            (RoleNotPermitted.code, RoleNotPermitted.code, None)
        ]
    loi = _loi_engine(session, ho_so, gui, sai_vai[0])
    assert isinstance(loi, RoleNotPermitted)
    assert _cua(ket_qua, sai_vai[0])["reasons"][0]["message"] == loi.message


def test_canh_chi_he_thong(client, session, rule_set):
    """Cạnh hệ thống (không có cạnh người cùng cặp trạng thái): con người nhận `system-transition-only`."""
    cac_canh = _cac_canh(session, rule_set.id)
    cap_nguoi = {(c.from_state, c.to_state) for c in cac_canh if not c.is_system}
    canh = next((c for c in cac_canh if c.is_system and (c.from_state, c.to_state) not in cap_nguoi), None)
    if canh is None:
        pytest.skip("Bộ quy tắc không có cạnh hệ thống riêng.")
    gui = Actor(id="ldc-gui-he-thong-424", name="Người gửi 424", roles=frozenset({"requester"}))
    ho_so = _ho_so(session, gui, current_state=canh.from_state)

    cua = _cua(_lua_chon(client, gui, ho_so.id), canh)
    assert cua["is_system"] is True and cua["allowed"] is False
    assert [(l["code"], l["category"]) for l in cua["reasons"]] == [
        (SystemTransitionOnly.code, SystemTransitionOnly.code)
    ]
    loi = _loi_engine(session, ho_so, gui, canh)
    assert isinstance(loi, SystemTransitionOnly)
    assert cua["reasons"][0]["message"] == loi.message


def test_rang_buoc_nguoi_thao_tac_khong_phai_nguoi_gui(client, session, rule_set):
    """`actor-not-requester` (#154): điều phối viên tự gửi hồ sơ thì cạnh điều phối có lý do là mã ràng buộc."""
    canh = _canh_chi_rang_buoc_khong_nhap_lieu(session, rule_set.id, "actor-not-requester")
    vai = next(iter(sorted(canh.role_codes)))
    tu_gui = Actor(id="ldc-tu-gui-424", name="Điều phối tự gửi 424", roles=frozenset({"requester", vai}))
    ho_so = _ho_so(session, tu_gui, current_state=canh.from_state)

    cua = _cua(_lua_chon(client, tu_gui, ho_so.id), canh)
    assert cua["allowed"] is False
    assert [(l["code"], l["category"]) for l in cua["reasons"]] == [("actor-not-requester", GuardViolation.code)]
    loi = _loi_engine(session, ho_so, tu_gui, canh)
    assert isinstance(loi, GuardViolation) and loi.guard_code == "actor-not-requester"
    assert cua["reasons"][0]["message"] == loi.message

    # Người khác cùng vai đi được — lý do đúng là ràng buộc, không phải vai. Mang thêm vai điều phối để chắc
    # chắn thấy hồ sơ dù nó đang ở phòng nào.
    khac = Actor(id="ldc-dp-khac-424", name="Điều phối khác 424", roles=frozenset({vai, VAI_TRO_DIEU_PHOI}))
    cua_khac = _cua(_lua_chon(client, khac, ho_so.id), canh)
    assert cua_khac["allowed"] is True and cua_khac["reasons"] == []


def test_rang_buoc_khong_thuoc_phong_dang_giu(client, session, rule_set, hai_phong):
    """`actor-in-case-department`: đúng vai nhưng thuộc phòng khác. Người đó là người gửi để còn thấy hồ sơ."""
    phong, khac = hai_phong
    canh = _canh_chi_rang_buoc_khong_nhap_lieu(session, rule_set.id, "actor-in-case-department")
    vai = next(iter(sorted(canh.role_codes)))
    ai = Actor(id="ldc-phong-khac-424", name="Phòng khác 424", roles=frozenset({"requester", vai}),
               departments=frozenset({khac}))
    ho_so = _ho_so(session, ai, current_state=canh.from_state, department_code=phong)

    cua = _cua(_lua_chon(client, ai, ho_so.id), canh)
    assert cua["allowed"] is False
    assert [(l["code"], l["category"]) for l in cua["reasons"]] == [("actor-in-case-department", GuardViolation.code)]
    loi = _loi_engine(session, ho_so, ai, canh)
    assert isinstance(loi, GuardViolation) and loi.guard_code == "actor-in-case-department"
    assert cua["reasons"][0]["message"] == loi.message

    dung_phong = Actor(id="ldc-dung-phong-424", name="Đúng phòng 424", roles=frozenset({vai}),
                       departments=frozenset({phong}))
    assert _cua(_lua_chon(client, dung_phong, ho_so.id), canh)["allowed"] is True


def test_thu_du_moi_rang_buoc_bi_vi_pham(client, session, rule_set):
    """Một cạnh vướng hai ràng buộc không cần nhập liệu thì trả đủ cả hai, không dừng ở cái đầu (gia hạn #101:
    `first-extension` khi đã gia hạn, `actor-not-requester` khi tự gửi)."""
    canh = next(
        (
            c for c in _cac_canh(session, rule_set.id)
            if not c.is_system and {"first-extension", "actor-not-requester"} <= set(c.guard_codes)
        ),
        None,
    )
    if canh is None:
        pytest.skip("Dữ liệu khởi tạo không có cạnh mang cả first-extension lẫn actor-not-requester.")
    vai = next(iter(sorted(canh.role_codes)))
    tu_gui = Actor(id="ldc-hai-ly-do-424", name="Tự gửi 424", roles=frozenset({"requester", vai}))
    ho_so = _ho_so(session, tu_gui, current_state=canh.from_state, sla_extension_count=1)

    cua = _cua(_lua_chon(client, tu_gui, ho_so.id), canh)
    assert cua["allowed"] is False
    assert {l["code"] for l in cua["reasons"]} == {"first-extension", "actor-not-requester"}
    assert {l["category"] for l in cua["reasons"]} == {GuardViolation.code}
    # Ràng buộc cần nhập liệu (`extend-deadline`) không xét lúc chưa biết nhập liệu: nó thành trường cần nhập
    assert cua["requires_input"] == xep_o_nhap(GUARD_REGISTRY["extend-deadline"].governs)


def test_dieu_kien_tren_canh(client, session, hai_phong):
    """Quy trình mua sắm (#397): trên ngưỡng thì cạnh "dưới ngưỡng" bị chặn bởi `edge-condition`, kèm định danh,
    trường, phép so và giá trị cần của dòng điều kiện; cạnh bù với nó đi được."""
    phong, _ = hai_phong
    bo = _bo_mua_sam(session)
    canh = next(c for c in _cac_canh(session, bo.id) if c.conditions)
    dk = canh.conditions[0]
    vai = next(iter(sorted(canh.role_codes)))
    gui = Actor(id="ldc-mua-gui-424", name="Người đề xuất 424", roles=frozenset({"requester"}))
    duyet = Actor(id="ldc-mua-duyet-424", name="Trưởng phòng 424", roles=frozenset({vai}), departments=frozenset({phong}))

    ho_so = _ho_so(session, gui, loai=_loai_cua_bo(session, bo).code, current_state=canh.from_state,
                   department_code=phong, details={dk.field_code: _gia_tri_lam_sai(dk.operator, dk.value)})

    ket_qua = _lua_chon(client, duyet, ho_so.id)
    cua = _cua(ket_qua, canh)
    assert cua["allowed"] is False
    assert [(l["code"], l["category"]) for l in cua["reasons"]] == [(MA_DIEU_KIEN, GuardViolation.code)]
    assert cua["reasons"][0]["condition"] == {
        "id": dk.id, "field": dk.field_code, "operator": dk.operator, "value": dk.value, "description": dk.description,
    }
    loi = _loi_engine(session, ho_so, duyet, canh)
    assert isinstance(loi, GuardViolation) and loi.guard_code == MA_DIEU_KIEN
    assert cua["reasons"][0]["message"] == loi.message

    # Cạnh có điều kiện khác cùng trạng thái nguồn (nhánh bù) đi được với cùng hồ sơ
    bu = [c for c in ket_qua["transitions"] if c["to_state"] != canh.to_state
          and any(t.conditions for t in _cac_canh(session, bo.id)
                  if (t.from_state, t.to_state) == (canh.from_state, c["to_state"]))]
    assert bu and all(c["allowed"] for c in bu)


# ---------------------------------------------------------------------------
# 2. requires_input, hồ sơ kết thúc, 404, chỉ đọc
# ---------------------------------------------------------------------------


def test_requires_input_tu_rang_buoc_can_nhap_lieu(client, session, rule_set):
    """Điều phối viên ở trạng thái đầu: cạnh đi được nói rõ trường cần gửi — đúng `governs` của ràng buộc KHÔNG
    `input_free` trên cạnh, theo thứ tự biểu mẫu; và là tập con của `fields` mà chi tiết hồ sơ trả."""
    gui = Actor(id="ldc-gui-nhap-424", name="Người gửi 424", roles=frozenset({"requester"}))
    dp = Actor(id="ldc-dp-nhap-424", name="Điều phối 424", roles=frozenset({"classifier"}))
    ho_so = _ho_so(session, gui)

    ket_qua = _lua_chon(client, dp, ho_so.id)
    chi_tiet = {(c["activity_code"], c["to_state"]): c["fields"]
                for c in client.la(dp).get(f"{LOI}/requests/{ho_so.id}").json()["allowed_transitions"]}
    co_nhap = 0
    for canh in (c for c in _cac_canh(session, rule_set.id) if c.from_state == ho_so.current_state):
        cua = _cua(ket_qua, canh)
        mong = xep_o_nhap(frozenset().union(
            *(GUARD_REGISTRY[g].governs for g in canh.guard_codes if not GUARD_REGISTRY[g].input_free)
        ))
        assert cua["requires_input"] == mong
        assert cua["requires_note"] is canh.requires_note
        if cua["allowed"]:
            assert set(mong) <= set(chi_tiet[(canh.activity_code, canh.to_state)])
            co_nhap += bool(mong)
    assert co_nhap, "trạng thái đầu phải có một cạnh của điều phối viên cần nhập liệu (phân loại)"


def test_ho_so_ket_thuc_khong_con_canh(client, session, rule_set):
    trang_thai_co_canh = {c.from_state for c in _cac_canh(session, rule_set.id)}
    ket_thuc = session.scalars(
        select(State.code).where(State.rule_set_id == rule_set.id, State.is_terminal).order_by(State.display_order)
    ).all()
    cuoi = next((m for m in ket_thuc if m not in trang_thai_co_canh), None)
    if cuoi is None:
        pytest.skip("Mọi trạng thái kết thúc đều có cạnh mở lại.")
    gui = Actor(id="ldc-gui-cuoi-424", name="Người gửi 424", roles=frozenset({"requester"}))
    ho_so = _ho_so(session, gui, current_state=cuoi)

    ket_qua = _lua_chon(client, gui, ho_so.id)
    assert ket_qua["state"] == {"code": cuoi, "label": ket_qua["state"]["label"], "is_terminal": True}
    assert ket_qua["transitions"] == []


def test_ho_so_khong_co_hay_khong_thay_tra_404(client, session, rule_set):
    gui = Actor(id="ldc-gui-404-424", name="Người gửi 424", roles=frozenset({"requester"}))
    nguoi_khac = Actor(id="ldc-khac-404-424", name="Người khác 424", roles=frozenset({"requester"}))
    ho_so = _ho_so(session, gui)
    khong_co = (session.scalar(select(func.max(Request.id))) or 0) + 1000

    for ai, ma in ((gui, khong_co), (nguoi_khac, ho_so.id)):
        tra = client.la(ai).get(f"{LOI}/requests/{ma}/transition-options")
        assert tra.status_code == 404, tra.text
        assert tra.json()["detail"]["code"] == "case-not-found"


def test_chi_doc_khong_ghi_nhat_ky_khong_doi_ho_so(client, session, rule_set):
    gui = Actor(id="ldc-gui-doc-424", name="Người gửi 424", roles=frozenset({"requester"}))
    ho_so = _ho_so(session, gui)

    def chup() -> tuple:
        session.expire_all()
        h = session.get(Request, ho_so.id)
        so_dong = session.scalar(select(func.count()).select_from(EventLog).where(EventLog.case_id == h.id))
        return (h.current_state, h.assignee_id, h.department_code, h.priority_code, h.details, so_dong)

    truoc = chup()
    _lua_chon(client, gui, ho_so.id)
    assert chup() == truoc


# ---------------------------------------------------------------------------
# 3. Bất biến: `allowed` trùng hệt `allowed_transitions`
# ---------------------------------------------------------------------------


def test_bat_bien_allowed_trung_allowed_transitions(client, session, rule_set, hai_phong):
    """Mọi trạng thái của quy trình mặc định và quy trình mua sắm, người gửi thường xen người gửi kiêm điều phối,
    số tiền dưới và trên ngưỡng xen nhau; mỗi vai thấy được hồ sơ thì danh sách cạnh `allowed` (đúng thứ tự)
    trùng `allowed_transitions()` và trùng `allowed_transitions` của chi tiết hồ sơ. Tác nhân hệ thống so
    thẳng trên hàm."""
    phong, khac = hai_phong
    gui = Actor(id="ldc-bb-gui-424", name="Người gửi 424", roles=frozenset({"requester"}))
    gui_dp = Actor(id="ldc-bb-gui-dp-424", name="Gửi kiêm điều phối 424", roles=frozenset({"requester", "classifier"}))
    cac_vai = [
        gui, gui_dp,
        Actor(id="ldc-bb-dp-424", name="Điều phối 424", roles=frozenset({"classifier"})),
        Actor(id="ldc-bb-tp-424", name="Trưởng phòng 424", roles=frozenset({"approver"}), departments=frozenset({phong})),
        Actor(id="ldc-bb-xl-424", name="Xử lý 424", roles=frozenset({"handler"}), departments=frozenset({phong})),
        Actor(id="ldc-bb-xlk-424", name="Xử lý phòng khác 424", roles=frozenset({"handler", "requester"}),
              departments=frozenset({khac})),
    ]
    he_thong = Actor.system()

    ho_so_thu: list[Request] = []
    for bo in session.scalars(select(RuleSet).where(RuleSet.is_active).order_by(RuleSet.id)).all():
        loai = None if bo.id == rule_set.id else _loai_cua_bo(session, bo).code
        dk = session.scalars(
            select(TransitionCondition).join(Transition).where(Transition.rule_set_id == bo.id)
        ).first()
        for i, ma in enumerate(session.scalars(select(State.code).where(State.rule_set_id == bo.id)).all()):
            dat = {"current_state": ma, "department_code": phong}
            if dk is not None:
                dat["details"] = {dk.field_code: float(dk.value) + (1 if i % 2 else -1)}
            ho_so_thu.append(_ho_so(session, gui if i % 2 == 0 else gui_dp, loai=loai, **dat))

    so_cap = so_di_duoc = so_bi_chan = 0
    for ho_so in ho_so_thu:
        for ai in cac_vai:
            tra = client.la(ai).get(f"{LOI}/requests/{ho_so.id}/transition-options")
            if tra.status_code == 404:
                continue
            assert tra.status_code == 200, tra.text
            cac = tra.json()["transitions"]
            di_duoc = [(c["activity_code"], c["to_state"], c["is_system"]) for c in cac if c["allowed"]]
            assert all(c["reasons"] == [] for c in cac if c["allowed"])
            assert all(c["reasons"] for c in cac if not c["allowed"])
            assert di_duoc == [(t.activity_code, t.to_state, t.is_system)
                               for t in allowed_transitions(session, ho_so, ai)], (ho_so.current_state, ai.id)
            chi_tiet = client.get(f"{LOI}/requests/{ho_so.id}").json()["allowed_transitions"]
            assert [(c[0], c[1]) for c in di_duoc] == [(c["activity_code"], c["to_state"]) for c in chi_tiet]
            so_cap += 1
            so_di_duoc += len(di_duoc)
            so_bi_chan += len(cac) - len(di_duoc)

        theo_ham = [t for t, ly_do in xet_cac_canh(session, ho_so, he_thong) if not ly_do]
        assert theo_ham == allowed_transitions(session, ho_so, he_thong)

    assert so_cap >= len(ho_so_thu) and so_di_duoc and so_bi_chan, (so_cap, so_di_duoc, so_bi_chan)


# ---------------------------------------------------------------------------
# 4. Tài khoản dịch vụ qua /core/v1
# ---------------------------------------------------------------------------


def test_tai_khoan_dich_vu_doc_lua_chon_canh(session, rule_set, token_dich_vu):  # noqa: F811
    """Token client credentials thật: tạo hồ sơ rồi đọc lựa chọn cạnh chỉ bằng /core/v1 — cạnh đi được trùng chi
    tiết hồ sơ, cạnh của vai khác có lý do quyền."""
    app.dependency_overrides[get_session] = lambda: session
    try:
        with TestClient(app, headers={"Authorization": f"Bearer {token_dich_vu}"}) as c:
            loai = c.get(f"{LOI}/request-types").json()[0]
            tao = c.post(f"{LOI}/requests", json={
                "title": "Lựa chọn cạnh từ ứng dụng khác", "request_type_code": loai["code"],
                "details": chi_tiet_mau(loai),
            })
            assert tao.status_code == 201, tao.text
            ma = tao.json()["id"]
            tra = c.get(f"{LOI}/requests/{ma}/transition-options")
            chi_tiet = c.get(f"{LOI}/requests/{ma}").json()["allowed_transitions"]
    finally:
        app.dependency_overrides.clear()

    assert tra.status_code == 200, tra.text
    cac = tra.json()["transitions"]
    assert [(x["activity_code"], x["to_state"]) for x in cac if x["allowed"]] == [
        (x["activity_code"], x["to_state"]) for x in chi_tiet
    ]
    assert chi_tiet, "tài khoản dịch vụ phải đi được ít nhất một bước ở trạng thái đầu"
    assert any(l["code"] == RoleNotPermitted.code for x in cac for l in x["reasons"])
