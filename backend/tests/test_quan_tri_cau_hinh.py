# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Màn quản trị cấu hình (#255): chỉ quản trị viên; sửa hạn áp ngay cho cả hồ sơ đang mở; chạy thử
# không để lại gì; sửa làm hỏng cấu hình bị từ chối kèm lý do; mỗi lần sửa có dòng nhật ký chỉ ghi thêm.
#
# Mã loại, phòng, mức ưu tiên lấy từ dữ liệu, không viết cứng — trừ mã trạng thái của luồng mẫu mà các
# bài khác cũng dùng để đưa hồ sơ tới phòng ban.

from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.auth.dependencies import current_actor
from app.db import get_session
from app.main import app
from app.models.quan_tri import ConfigChange
from app.models.workflow_config import Department, Priority, RequestType, RequestTypeRouting, State, Transition
from app.rules.sla import gioi_han_giay
from app.workflow.context import Actor
from app.workflow.engine import create_case, perform_transition

QUAN_TRI = Actor(id="qt-255", roles=frozenset({"administrator"}), name="Quản trị thử 255")
DIEU_PHOI = Actor(id="dp-255", roles=frozenset({"classifier"}))
NGUOI_GUI = "ng-255"


@contextmanager
def _may_khach(session, actor: Actor):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: actor
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def _loai(session) -> RequestType:
    return session.scalars(
        select(RequestType).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()


def _ho_so_da_phan_loai(session, loai: str, uu_tien: str):
    ho_so = create_case(session, title="Hồ sơ thử quản trị cấu hình", requester_id=NGUOI_GUI)
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=DIEU_PHOI,
        changes={"priority_code": uu_tien, "request_type_code": loai},
    )
    return ho_so


def _uu_tien_mac_dinh(session) -> str:
    return session.scalars(select(Priority.code).where(Priority.is_default)).one()


def _so_dong_nhat_ky(session) -> int:
    return session.scalar(select(func.count()).select_from(ConfigChange))


# ---------------------------------------------------------------------------
# Quyền
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("vai_tro", ["requester", "classifier", "approver", "handler"])
def test_vai_khac_khong_vao_duoc(session, rule_set, vai_tro):
    khach = Actor(id="khac-255", roles=frozenset({vai_tro}))
    loai = _loai(session)
    with _may_khach(session, khach) as c:
        assert c.get("/admin/config").status_code == 403
        assert (
            c.post(f"/admin/config/request-types/{loai.code}", json={"changes": {"sla_hours": 99}}).status_code
            == 403
        )
    session.refresh(loai)
    assert loai.sla_hours != 99


# ---------------------------------------------------------------------------
# Xem
# ---------------------------------------------------------------------------


def test_xem_dung_bo_quy_tac_dang_chay(session, rule_set):
    with _may_khach(session, QUAN_TRI) as c:
        than = c.get("/admin/config").json()

    so_trang_thai = session.scalar(select(func.count()).select_from(State).where(State.rule_set_id == rule_set.id))
    so_canh = session.scalar(select(func.count()).select_from(Transition).where(Transition.rule_set_id == rule_set.id))
    assert than["rule_set"]["version"] == rule_set.version
    assert len(than["states"]) == so_trang_thai
    assert len(than["transitions"]) == so_canh
    assert all(t["from_label"] and t["to_label"] for t in than["transitions"])

    mac_dinh = dict(
        session.execute(
            select(RequestTypeRouting.request_type_code, RequestTypeRouting.department_code).where(
                RequestTypeRouting.is_default
            )
        ).all()
    )
    for loai in than["request_types"]:
        assert loai["default_department"] == mac_dinh.get(loai["code"])
    assert than["calendar"]["hours"], "lịch mặc định phải có giờ làm"
    assert than["fields"]["request-types"]["sla_hours"]["affects_deadlines"] is True


# ---------------------------------------------------------------------------
# Sửa hạn: áp ngay, chạy thử, nhật ký
# ---------------------------------------------------------------------------


def test_chay_thu_dem_ho_so_va_khong_de_lai_gi(session, rule_set):
    loai = _loai(session)
    _ho_so_da_phan_loai(session, loai.code, _uu_tien_mac_dinh(session))
    cu = loai.sla_hours
    truoc = _so_dong_nhat_ky(session)

    with _may_khach(session, QUAN_TRI) as c:
        ra = c.post(
            f"/admin/config/request-types/{loai.code}",
            json={"changes": {"sla_hours": cu + 5}, "dry_run": True},
        )
    assert ra.status_code == 200, ra.text
    than = ra.json()
    assert than["applied"] is False
    assert than["affects_deadlines"] is True
    assert than["open_cases"] >= 1
    assert than["changes"] == [
        {"field": "sla_hours", "field_label": "Hạn chuẩn (giờ làm việc)", "old_value": cu, "new_value": cu + 5}
    ]

    session.refresh(loai)
    assert loai.sla_hours == cu
    assert _so_dong_nhat_ky(session) == truoc


def test_sua_han_ap_ngay_cho_ho_so_dang_mo_va_ghi_nhat_ky(session, rule_set):
    loai = _loai(session)
    ho_so = _ho_so_da_phan_loai(session, loai.code, _uu_tien_mac_dinh(session))
    cu = loai.sla_hours
    han_cu = gioi_han_giay(session, ho_so)

    with _may_khach(session, QUAN_TRI) as c:
        ra = c.post(f"/admin/config/request-types/{loai.code}", json={"changes": {"sla_hours": cu * 2}})
    assert ra.status_code == 200, ra.text
    assert ra.json()["applied"] is True

    session.refresh(loai)
    assert loai.sla_hours == cu * 2
    # Hồ sơ đang mở theo hạn mới ngay — khuôn "dữ liệu dùng chung" (ARCHITECTURE 5.4)
    assert gioi_han_giay(session, ho_so) == han_cu * 2
    # Hồ sơ mới cũng vậy
    ho_so_moi = _ho_so_da_phan_loai(session, loai.code, _uu_tien_mac_dinh(session))
    assert gioi_han_giay(session, ho_so_moi) == han_cu * 2

    dong = session.scalars(select(ConfigChange).order_by(ConfigChange.id.desc())).first()
    assert (dong.entity, dong.entity_code, dong.field) == ("request_types", loai.code, "sla_hours")
    assert (dong.old_value, dong.new_value) == (cu, cu * 2)
    assert (dong.actor_id, dong.actor_label) == (QUAN_TRI.id, QUAN_TRI.name)

    with _may_khach(session, QUAN_TRI) as c:
        nhat_ky = c.get("/admin/config").json()["changes"]
    assert nhat_ky[0]["field_label"] == "Hạn chuẩn (giờ làm việc)"
    assert nhat_ky[0]["entity_label"] == "Loại yêu cầu"


def test_sua_he_so_uu_tien(session, rule_set):
    loai = _loai(session)
    muc = _uu_tien_mac_dinh(session)
    ho_so = _ho_so_da_phan_loai(session, loai.code, muc)
    he_so = session.get(Priority, muc).sla_factor_percent
    han_cu = gioi_han_giay(session, ho_so)

    with _may_khach(session, QUAN_TRI) as c:
        ra = c.post(f"/admin/config/priorities/{muc}", json={"changes": {"sla_factor_percent": he_so * 2}})
    assert ra.status_code == 200, ra.text
    assert gioi_han_giay(session, ho_so) == han_cu * 2


def test_khong_doi_gi_thi_khong_ghi(session, rule_set):
    loai = _loai(session)
    truoc = _so_dong_nhat_ky(session)
    with _may_khach(session, QUAN_TRI) as c:
        ra = c.post(f"/admin/config/request-types/{loai.code}", json={"changes": {"label": loai.label}})
    assert ra.status_code == 200
    assert ra.json() == {**ra.json(), "applied": False, "changes": []}
    assert _so_dong_nhat_ky(session) == truoc


# ---------------------------------------------------------------------------
# Phòng ban và phòng mặc định
# ---------------------------------------------------------------------------


def test_doi_ten_phong_ban(session, rule_set, phong_ban):
    with _may_khach(session, QUAN_TRI) as c:
        ra = c.post(f"/admin/config/departments/{phong_ban}", json={"changes": {"label": "Phòng thử đổi tên"}})
    assert ra.status_code == 200, ra.text
    assert session.get(Department, phong_ban).label == "Phòng thử đổi tên"
    # Danh mục cho ô chọn phòng của điều phối viên đọc đúng tên mới, không dựng lại cụm
    with _may_khach(session, DIEU_PHOI) as c:
        ten = {p["code"]: p["label"] for p in c.get("/departments").json()}
    assert ten[phong_ban] == "Phòng thử đổi tên"


def test_doi_phong_mac_dinh(session, rule_set):
    loai = _loai(session)
    cu = session.scalars(
        select(RequestTypeRouting.department_code).where(
            RequestTypeRouting.request_type_code == loai.code, RequestTypeRouting.is_default
        )
    ).one()
    khac = session.scalars(
        select(Department.code).where(Department.is_active, Department.code != cu).order_by(Department.code)
    ).first()

    with _may_khach(session, QUAN_TRI) as c:
        ra = c.post(f"/admin/config/request-types/{loai.code}", json={"changes": {"default_department": khac}})
    assert ra.status_code == 200, ra.text
    mac_dinh = session.scalars(
        select(RequestTypeRouting.department_code).where(
            RequestTypeRouting.request_type_code == loai.code, RequestTypeRouting.is_default
        )
    ).all()
    assert mac_dinh == [khac]


# ---------------------------------------------------------------------------
# Từ chối
# ---------------------------------------------------------------------------


def test_ngung_phong_dang_la_mac_dinh_bi_tu_choi(session, rule_set):
    phong = session.scalars(
        select(RequestTypeRouting.department_code)
        .join(RequestType, RequestType.code == RequestTypeRouting.request_type_code)
        .where(RequestTypeRouting.is_default, RequestType.is_active)
    ).first()
    truoc = _so_dong_nhat_ky(session)

    with _may_khach(session, QUAN_TRI) as c:
        ra = c.post(f"/admin/config/departments/{phong}", json={"changes": {"is_active": False}})
    assert ra.status_code == 422
    loi = ra.json()["detail"]
    assert loi["code"] == "cau-hinh-khong-hop-le"
    assert "phòng ban mặc định đã ngưng" in loi["message"]
    session.expire_all()
    assert session.get(Department, phong).is_active is True
    assert _so_dong_nhat_ky(session) == truoc


def test_tat_loai_cuoi_cung_bi_tu_choi(session, rule_set):
    cac_loai = session.scalars(select(RequestType.code).where(RequestType.is_active)).all()
    cuoi = cac_loai[-1]
    session.execute(
        text("UPDATE request_types SET is_active = FALSE WHERE code <> :ma"), {"ma": cuoi}
    )
    session.flush()
    with _may_khach(session, QUAN_TRI) as c:
        ra = c.post(f"/admin/config/request-types/{cuoi}", json={"changes": {"is_active": False}})
    assert ra.status_code == 422
    assert "ít nhất một loại yêu cầu" in ra.json()["detail"]["message"]


@pytest.mark.parametrize(
    ("thay_doi", "ma_loi"),
    [
        ({"sla_warn_percent": 100}, "gia-tri-khong-hop-le"),
        ({"sla_hours": 0}, "gia-tri-khong-hop-le"),
        ({"sla_hours": "8"}, "gia-tri-khong-hop-le"),
        ({"label": "   "}, "gia-tri-khong-hop-le"),
        ({"code": "doi-ma"}, "truong-khong-sua-duoc"),
        ({"default_department": "khong-co-phong-nay"}, "gia-tri-khong-hop-le"),
    ],
)
def test_gia_tri_sai_bi_tu_choi(session, rule_set, thay_doi, ma_loi):
    loai = _loai(session)
    with _may_khach(session, QUAN_TRI) as c:
        ra = c.post(f"/admin/config/request-types/{loai.code}", json={"changes": thay_doi})
    assert ra.status_code == 422, ra.text
    assert ra.json()["detail"]["code"] == ma_loi


def test_ma_hay_danh_muc_la_thi_404(session, rule_set):
    with _may_khach(session, QUAN_TRI) as c:
        assert c.post("/admin/config/request-types/khong-co", json={"changes": {"label": "x"}}).status_code == 404
        assert c.post("/admin/config/roles/administrator", json={"changes": {"label": "x"}}).status_code == 404


def test_nhat_ky_chi_ghi_them(session, rule_set):
    loai = _loai(session)
    with _may_khach(session, QUAN_TRI) as c:
        c.post(f"/admin/config/request-types/{loai.code}", json={"changes": {"sla_hours": loai.sla_hours + 1}})
    with pytest.raises(DBAPIError, match="chỉ ghi thêm"):
        with session.begin_nested():
            session.execute(text("UPDATE config_changes SET field = 'sua-lai'"))
