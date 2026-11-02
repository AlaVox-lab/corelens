# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Xuất nhật ký sự kiện CSV và JSON (#306).
from __future__ import annotations

import csv
import datetime as dt
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.analytics.xuat_du_lieu import COT
from app.auth.dependencies import current_actor
from app.db import get_session
from app.main import app
from app.models.workflow_config import Priority, RequestType
from app.rules.sla import bay_gio
from app.workflow.context import Actor
from app.workflow.engine import create_case, perform_transition

QUAN_TRI = Actor(id="qt-306", roles=frozenset({"administrator"}))
NGUOI_GUI = Actor(id="nguoi-gui-306", name="Chị Hạnh Lê", roles=frozenset({"requester"}))
DIEU_PHOI = Actor(id="dp-306", name="Anh Bảo Trần", roles=frozenset({"classifier"}))


@pytest.fixture
def client(session):
    """Máy khách HTTP đổi được người gọi. Phần dựng cảnh phải `commit`, như test_coordination.py."""
    dang_goi = {"actor": QUAN_TRI}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: dang_goi["actor"]
    with TestClient(app) as c:
        c.dang_goi = dang_goi
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def ho_so(session, rule_set):
    """Một hồ sơ đã phân loại: sự kiện mở đầu cộng một dòng nhật ký, mang tên người ở cả hai."""
    loai = session.scalars(select(RequestType.code).where(RequestType.is_active)).first()
    h = create_case(
        session, title="Máy chiếu phòng họp không lên hình", requester_id=NGUOI_GUI.id,
        requester_label=NGUOI_GUI.name, request_type_code=loai,
    )
    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()
    perform_transition(
        session, case_id=h.id, to_state="classified", actor=DIEU_PHOI,
        note="Đã gọi cho chị Hạnh", changes={"priority_code": uu_tien},
    )
    session.commit()
    return h


def _cua(dong: list[dict], ma: int) -> list[dict]:
    return [d for d in dong if str(d["case_id"]) == str(ma)]


def test_csv_co_bom_dung_cot_va_su_kien_mo_dau(client, ho_so):
    tra_ve = client.get("/analytics/event-log?format=csv")
    assert tra_ve.status_code == 200
    assert tra_ve.headers["content-type"].startswith("text/csv")
    assert "attachment" in tra_ve.headers["content-disposition"]
    assert tra_ve.content.startswith(b"\xef\xbb\xbf")

    doc = csv.DictReader(io.StringIO(tra_ve.content.decode("utf-8-sig")))
    assert tuple(doc.fieldnames) == COT
    [mo_dau, phan_loai] = _cua(list(doc), ho_so.id)
    assert (mo_dau["activity"], mo_dau["from_state"], mo_dau["actor"]) == ("create-case", "", NGUOI_GUI.id)
    assert (phan_loai["from_state"], phan_loai["to_state"]) == (mo_dau["to_state"], "classified")
    assert phan_loai["actor"] == DIEU_PHOI.id
    assert phan_loai["timestamp"].endswith("+00:00")


def test_json_cung_noi_dung_voi_csv(client, ho_so):
    dong = client.get("/analytics/event-log?format=json").json()
    cua = _cua(dong, ho_so.id)
    assert [tuple(d) for d in cua] == [COT, COT]
    assert [d["activity"] for d in cua][0] == "create-case"
    assert cua[0]["from_state"] is None
    assert cua[1]["rule_set_id"] == ho_so.rule_set_id


def test_khong_xuat_ten_nguoi_va_ghi_chu(client, ho_so):
    for dinh_dang in ("csv", "json"):
        than = client.get(f"/analytics/event-log?format={dinh_dang}").content.decode("utf-8")
        for chu in ("Hạnh", "Bảo Trần", "Đã gọi"):
            assert chu not in than


def test_loc_theo_ngay_utc_lay_tron_ngay_cuoi(client, session, ho_so):
    hom_nay = bay_gio(session).astimezone(dt.UTC).date()
    mot_ngay = dt.timedelta(days=1)

    def so_dong(tham_so: str) -> int:
        return len(_cua(client.get(f"/analytics/event-log?format=json&{tham_so}").json(), ho_so.id))

    assert so_dong(f"from={hom_nay}&to={hom_nay}") == 2
    assert so_dong(f"from={hom_nay + mot_ngay}") == 0
    assert so_dong(f"to={hom_nay - mot_ngay}") == 0
    assert client.get(f"/analytics/event-log?from={hom_nay}&to={hom_nay - mot_ngay}").status_code == 422


@pytest.mark.parametrize("vai", ["requester", "classifier", "approver", "handler"])
def test_vai_khac_quan_tri_bi_tu_choi(client, vai):
    client.dang_goi["actor"] = Actor(id="ai-do", roles=frozenset({vai}))
    assert client.get("/analytics/event-log").status_code == 403
