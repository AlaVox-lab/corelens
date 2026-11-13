# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ủy quyền khi vắng mặt (#252). Định nghĩa hoàn thành của issue: trưởng phòng ủy quyền cho người khác
# trong vài ngày — trong khoảng đó người đó xử lý được hồ sơ của phòng và nhật ký ghi "thay mặt"; hết
# khoảng thì mất quyền ngay; ủy quyền không cho duyệt hồ sơ do chính người được ủy quyền gửi.
#
# Mã vai và trạng thái theo luồng mẫu như các bài khác (test_gia_han.py); phòng lấy từ dữ liệu.

from __future__ import annotations

import datetime as dt
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth.dependencies import current_actor, current_claims
from app.auth.directory import DirectoryUnavailable, Person, get_directory
from app.db import get_session
from app.main import app
from app.models.case import EventLog
from app.models.quan_tri import Delegation
from app.workflow.context import Actor
from app.workflow.engine import create_case, my_primary_steps, perform_transition
from app.workflow.errors import RoleNotPermitted
from app.workflow.uy_quyen import ap_uy_quyen, hom_nay

DIEU_PHOI = Actor(id="dp-252", roles=frozenset({"classifier"}))
TRUONG_PHONG_ID = "tp-252"
XU_LY_ID = "xl-252"
XU_LY_2_ID = "xl2-252"
NGUOI_GUI_ID = "ng-252"


def _truong_phong(phong: str) -> Actor:
    return Actor(id=TRUONG_PHONG_ID, roles=frozenset({"approver"}), departments=frozenset({phong}), name="Trưởng phòng 252")


def _xu_ly(phong: str, ma: str = XU_LY_ID, ten: str = "Người xử lý 252") -> Actor:
    return Actor(id=ma, roles=frozenset({"handler", "requester"}), departments=frozenset({phong}), name=ten)


def _uy_quyen(session, phong: str, *, tu_vang: str, cho: str, vai: list[str], bat_dau_gio: float = -1,
              ket_thuc_gio: float = 24, thu_hoi: bool = False) -> Delegation:
    bay_gio = session.execute(select(func.now())).scalar_one()
    u = Delegation(
        delegator_id=tu_vang,
        delegator_label=f"Người vắng {tu_vang}",
        delegate_id=cho,
        delegate_label=f"Người nhận {cho}",
        department_code=phong,
        roles=vai,
        starts_at=bay_gio + dt.timedelta(hours=bat_dau_gio),
        ends_at=bay_gio + dt.timedelta(hours=ket_thuc_gio),
        created_by_id=tu_vang,
        created_by_label="thử",
        revoked_at=bay_gio if thu_hoi else None,
        revoked_by_id=tu_vang if thu_hoi else None,
    )
    session.add(u)
    session.flush()
    return u


def _ho_so_cho_phong_nhan(session, phong: str, nguoi_gui: str = NGUOI_GUI_ID):
    ho_so = create_case(session, title="Hồ sơ thử ủy quyền", requester_id=nguoi_gui)
    perform_transition(session, case_id=ho_so.id, to_state="classified", actor=DIEU_PHOI,
                       changes={"priority_code": "normal", "request_type_code": _loai(session)})
    perform_transition(session, case_id=ho_so.id, to_state="awaiting-acceptance", actor=DIEU_PHOI,
                       changes={"department_code": phong})
    return ho_so


def _loai(session) -> str:
    from app.models.workflow_config import RequestType

    return session.scalars(select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)).first()


# ---------------------------------------------------------------------------
# Gắn ủy quyền vào định danh
# ---------------------------------------------------------------------------


def test_uy_quyen_dang_hieu_luc_gop_vai(session, rule_set, phong_ban):
    _uy_quyen(session, phong_ban, tu_vang=TRUONG_PHONG_ID, cho=XU_LY_ID, vai=["approver"])
    actor = ap_uy_quyen(session, _xu_ly(phong_ban))
    assert "approver" in actor.roles
    assert actor.vai_rieng == frozenset({"handler", "requester"})
    assert [u.nguoi_vang_id for u in actor.lam_thay] == [TRUONG_PHONG_ID]


@pytest.mark.parametrize(
    "khoang",
    [
        {"bat_dau_gio": -48, "ket_thuc_gio": -1},  # đã hết
        {"bat_dau_gio": 2, "ket_thuc_gio": 48},  # chưa tới
        {"thu_hoi": True},  # đã thu hồi
    ],
)
def test_ngoai_khoang_hieu_luc_thi_khong_co_gi(session, rule_set, phong_ban, khoang):
    _uy_quyen(session, phong_ban, tu_vang=TRUONG_PHONG_ID, cho=XU_LY_ID, vai=["approver"], **khoang)
    actor = _xu_ly(phong_ban)
    assert ap_uy_quyen(session, actor) is actor


def test_uy_quyen_phong_khac_khong_ap(session, rule_set, phong_ban):
    _uy_quyen(session, phong_ban, tu_vang=TRUONG_PHONG_ID, cho=XU_LY_ID, vai=["approver"])
    nguoi_phong_khac = Actor(id=XU_LY_ID, roles=frozenset({"handler"}), departments=frozenset({"phong-khac-252"}))
    assert ap_uy_quyen(session, nguoi_phong_khac).lam_thay == ()


# ---------------------------------------------------------------------------
# Cửa chuyển trạng thái
# ---------------------------------------------------------------------------


def test_lam_thay_truong_phong_ghi_thay_mat(session, rule_set, phong_ban):
    ho_so = _ho_so_cho_phong_nhan(session, phong_ban)
    with pytest.raises(RoleNotPermitted):
        perform_transition(session, case_id=ho_so.id, to_state="in-progress", actor=_xu_ly(phong_ban))

    _uy_quyen(session, phong_ban, tu_vang=TRUONG_PHONG_ID, cho=XU_LY_ID, vai=["approver"])
    perform_transition(session, case_id=ho_so.id, to_state="in-progress", actor=ap_uy_quyen(session, _xu_ly(phong_ban)))

    dong = session.scalars(select(EventLog).where(EventLog.case_id == ho_so.id).order_by(EventLog.id.desc())).first()
    assert dong.actor == XU_LY_ID
    assert (dong.on_behalf_of, dong.on_behalf_of_label) == (TRUONG_PHONG_ID, f"Người vắng {TRUONG_PHONG_ID}")


def test_vai_rieng_thi_khong_ghi_thay_mat(session, rule_set, phong_ban):
    ho_so = _ho_so_cho_phong_nhan(session, phong_ban)
    perform_transition(session, case_id=ho_so.id, to_state="in-progress", actor=_truong_phong(phong_ban))
    # Người xử lý có ủy quyền nhưng hoàn thành bằng vai riêng của mình
    _uy_quyen(session, phong_ban, tu_vang=TRUONG_PHONG_ID, cho=XU_LY_ID, vai=["approver"])
    perform_transition(session, case_id=ho_so.id, to_state="completed", actor=ap_uy_quyen(session, _xu_ly(phong_ban)))
    dong = session.scalars(select(EventLog).where(EventLog.case_id == ho_so.id).order_by(EventLog.id.desc())).first()
    assert dong.on_behalf_of is None


def test_het_han_thi_mat_quyen_ngay(session, rule_set, phong_ban):
    ho_so = _ho_so_cho_phong_nhan(session, phong_ban)
    u = _uy_quyen(session, phong_ban, tu_vang=TRUONG_PHONG_ID, cho=XU_LY_ID, vai=["approver"])
    u.ends_at = session.execute(select(func.now())).scalar_one() - dt.timedelta(seconds=1)
    session.flush()
    with pytest.raises(RoleNotPermitted):
        perform_transition(session, case_id=ho_so.id, to_state="in-progress", actor=ap_uy_quyen(session, _xu_ly(phong_ban)))


def test_khong_dung_uy_quyen_duyet_ho_so_minh_gui(session, rule_set, phong_ban):
    ho_so = _ho_so_cho_phong_nhan(session, phong_ban, nguoi_gui=XU_LY_ID)
    _uy_quyen(session, phong_ban, tu_vang=TRUONG_PHONG_ID, cho=XU_LY_ID, vai=["approver"])
    with pytest.raises(RoleNotPermitted, match="chính mình gửi"):
        perform_transition(session, case_id=ho_so.id, to_state="in-progress", actor=ap_uy_quyen(session, _xu_ly(phong_ban)))


def test_ho_so_giao_nguoi_vang_hien_trong_viec_can_toi(session, rule_set, phong_ban):
    ho_so = _ho_so_cho_phong_nhan(session, phong_ban)
    perform_transition(session, case_id=ho_so.id, to_state="in-progress", actor=_truong_phong(phong_ban),
                       changes={"assignee_id": XU_LY_2_ID}, assignee_label="Người xử lý vắng")
    dong_nghiep = _xu_ly(phong_ban)
    assert my_primary_steps(session, [ho_so], dong_nghiep)[ho_so.id] is None

    _uy_quyen(session, phong_ban, tu_vang=XU_LY_2_ID, cho=XU_LY_ID, vai=["handler"])
    assert my_primary_steps(session, [ho_so], ap_uy_quyen(session, dong_nghiep))[ho_so.id] is not None


# ---------------------------------------------------------------------------
# Điểm cuối khai và thu hồi
# ---------------------------------------------------------------------------


class _DanhBaGia:
    """Danh bạ giả: một phòng có trưởng phòng và hai người xử lý."""

    def __init__(self, phong: str, hong: bool = False) -> None:
        self.phong, self.hong = phong, hong

    def department_members(self, ma: str) -> list[Person]:
        if self.hong:
            raise DirectoryUnavailable("thử")
        if ma != self.phong:
            return []
        return [
            Person(TRUONG_PHONG_ID, "tp", "Trưởng phòng 252", frozenset({"approver"})),
            Person(XU_LY_ID, "xl", "Người xử lý 252", frozenset({"handler", "requester"})),
            Person(XU_LY_2_ID, "xl2", "Người xử lý thứ hai", frozenset({"handler", "requester"})),
        ]


@contextmanager
def _may_khach(session, actor: Actor, phong: str, hong: bool = False):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: ap_uy_quyen(session, actor)
    app.dependency_overrides[get_directory] = lambda: _DanhBaGia(phong, hong)
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def _than(session, cho: str, so_ngay: int = 3, **them) -> dict:
    hom = hom_nay(session)
    return {"delegate_id": cho, "starts_on": hom.isoformat(), "ends_on": (hom + dt.timedelta(days=so_ngay - 1)).isoformat(), **them}


def test_truong_phong_tu_khai_roi_nguoi_nhan_co_quyen_ngay(session, rule_set, phong_ban):
    with _may_khach(session, _truong_phong(phong_ban), phong_ban) as c:
        ra = c.post("/delegations", json=_than(session, XU_LY_ID))
    assert ra.status_code == 201, ra.text
    than = ra.json()
    assert than["status"] == "active"
    assert than["roles"] and than["delegator_label"] == "Trưởng phòng 252"
    assert "approver" in ap_uy_quyen(session, _xu_ly(phong_ban)).roles

    # Dải báo trên trang chủ của người nhận đọc từ /me
    with _may_khach(session, _xu_ly(phong_ban), phong_ban) as c:
        app.dependency_overrides[current_claims] = lambda: {"sub": XU_LY_ID, "preferred_username": "xl"}
        toi = c.get("/me").json()
    assert [(d["delegator_label"], d["ends_on"]) for d in toi["acting_for"]] == [
        ("Trưởng phòng 252", (hom_nay(session) + dt.timedelta(days=2)).isoformat())
    ]
    assert "department" in toi["workspaces"]


def test_truong_phong_khai_thay_nguoi_xu_ly(session, rule_set, phong_ban):
    with _may_khach(session, _truong_phong(phong_ban), phong_ban) as c:
        ra = c.post("/delegations", json=_than(session, XU_LY_ID, delegator_id=XU_LY_2_ID))
    assert ra.status_code == 201, ra.text
    u = session.get(Delegation, ra.json()["id"])
    assert (u.delegator_id, u.roles, u.created_by_id) == (XU_LY_2_ID, ["handler"], TRUONG_PHONG_ID)


def test_khong_chuyen_tiep(session, rule_set, phong_ban):
    """Người đang làm thay trưởng phòng không khai thay cho ai, và tự khai thì chỉ ủy quyền vai riêng."""
    _uy_quyen(session, phong_ban, tu_vang=TRUONG_PHONG_ID, cho=XU_LY_ID, vai=["approver"])
    with _may_khach(session, _xu_ly(phong_ban), phong_ban) as c:
        khai_thay = c.post("/delegations", json=_than(session, XU_LY_2_ID, delegator_id=TRUONG_PHONG_ID))
        tu_khai = c.post("/delegations", json=_than(session, XU_LY_2_ID))
    assert khai_thay.status_code == 403
    assert tu_khai.status_code == 201, tu_khai.text
    assert session.get(Delegation, tu_khai.json()["id"]).roles == ["handler"]


@pytest.mark.parametrize(
    ("sua", "ma_http", "ma_loi"),
    [
        ({"delegate_id": "nguoi-ngoai-phong"}, 422, "nguoi-nhan-khac-phong"),
        ({"delegate_id": TRUONG_PHONG_ID}, 422, "tu-uy-quyen"),
        ({"starts_on": "2020-01-01"}, 422, "ngay-da-qua"),
        ({"so_ngay": 61}, 422, "qua-dai"),
    ],
)
def test_khai_sai_bi_tu_choi(session, rule_set, phong_ban, sua, ma_http, ma_loi):
    so_ngay = sua.pop("so_ngay", 3)
    than = {**_than(session, XU_LY_ID, so_ngay), **sua}
    with _may_khach(session, _truong_phong(phong_ban), phong_ban) as c:
        ra = c.post("/delegations", json=than)
    assert ra.status_code == ma_http, ra.text
    assert ra.json()["detail"]["code"] == ma_loi


def test_truong_phong_khong_khai_thay_truong_phong_khac(session, rule_set, phong_ban):
    pho_phong = Actor(id="pp-252", roles=frozenset({"approver"}), departments=frozenset({phong_ban}))
    with _may_khach(session, pho_phong, phong_ban) as c:
        ra = c.post("/delegations", json=_than(session, XU_LY_ID, delegator_id=TRUONG_PHONG_ID))
    assert ra.status_code == 403
    assert ra.json()["detail"]["code"] == "chi-khai-thay-nguoi-xu-ly"


def test_danh_ba_hong_thi_503(session, rule_set, phong_ban):
    with _may_khach(session, _truong_phong(phong_ban), phong_ban, hong=True) as c:
        assert c.post("/delegations", json=_than(session, XU_LY_ID)).status_code == 503


def test_vai_khong_phai_phong_ban_khong_vao_duoc(session, rule_set, phong_ban):
    nguoi_gui = Actor(id=NGUOI_GUI_ID, roles=frozenset({"requester"}), departments=frozenset({phong_ban}))
    with _may_khach(session, nguoi_gui, phong_ban) as c:
        assert c.get("/delegations").status_code == 403


def test_thu_hoi(session, rule_set, phong_ban):
    u = _uy_quyen(session, phong_ban, tu_vang=TRUONG_PHONG_ID, cho=XU_LY_ID, vai=["approver"])
    with _may_khach(session, _xu_ly(phong_ban), phong_ban) as c:
        assert c.post(f"/delegations/{u.id}/revoke").status_code == 403
    with _may_khach(session, _truong_phong(phong_ban), phong_ban) as c:
        ra = c.post(f"/delegations/{u.id}/revoke")
        assert ra.status_code == 200, ra.text
        assert ra.json()["status"] == "revoked"
        assert c.post(f"/delegations/{u.id}/revoke").status_code == 409
    # Mất quyền ngay
    assert ap_uy_quyen(session, _xu_ly(phong_ban)).lam_thay == ()
    with _may_khach(session, _xu_ly(phong_ban), phong_ban) as c:
        danh_sach = c.get("/delegations").json()["items"]
    assert [d["status"] for d in danh_sach if d["id"] == u.id] == ["revoked"]
