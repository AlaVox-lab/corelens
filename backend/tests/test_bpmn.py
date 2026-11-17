# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử xuất quy trình ra BPMN 2.0 (#405).
#
# Đáp án biết trước là chính dữ liệu cấu hình: với MỌI quy trình đang có, tệp BPMN phải có đúng một nút cho mỗi
# trạng thái của bộ quy tắc đang bật (kết thúc là endEvent, còn lại userTask), đúng một luồng cho mỗi cạnh cộng
# luồng từ sự kiện bắt đầu, mọi luồng nối hai nút có thật, mọi nút và luồng có phần bố cục để công cụ vẽ được.

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.dependencies import current_actor
from app.db import get_session
from app.main import app
from app.models.workflow_config import Process, State, Transition
from app.workflow.bpmn import BPMN, BPMNDI
from app.workflow.context import Actor
from app.workflow.engine import get_active_rule_set

NGUOI_GUI = Actor(id="kc-gui-01", name="An Nguyễn", roles=frozenset({"requester"}))
NS = {"bpmn": BPMN, "bpmndi": BPMNDI}


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: NGUOI_GUI
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _cac_quy_trinh(session) -> list[Process]:
    ds = list(session.scalars(select(Process).order_by(Process.code)))
    if not ds:
        pytest.skip("Chưa nạp danh mục quy trình.")
    return ds


def _tai(client, ma: str) -> ET.Element:
    tra = client.get(f"/core/v1/workflow/processes/{ma}/bpmn")
    assert tra.status_code == 200, tra.text
    assert tra.headers["content-type"].startswith("application/xml")
    assert f'filename="{ma}.bpmn"' in tra.headers["content-disposition"]
    return ET.fromstring(tra.content)


def test_moi_trang_thai_va_canh_thanh_mot_phan_tu(client, session, rule_set):
    for qt in _cac_quy_trinh(session):
        bo = get_active_rule_set(session, qt.code)
        cac_trang_thai = session.scalars(select(State).where(State.rule_set_id == bo.id)).all()
        so_canh = len(session.scalars(select(Transition).where(Transition.rule_set_id == bo.id)).all())

        goc = _tai(client, qt.code)
        tien_trinh = goc.find("bpmn:process", NS)
        assert tien_trinh.get("name") == qt.label

        viec = {e.get("name") for e in tien_trinh.findall("bpmn:userTask", NS)}
        ket_thuc = {e.get("name") for e in tien_trinh.findall("bpmn:endEvent", NS)}
        assert viec == {s.label for s in cac_trang_thai if not s.is_terminal}, qt.code
        assert ket_thuc == {s.label for s in cac_trang_thai if s.is_terminal}, qt.code
        assert len(tien_trinh.findall("bpmn:startEvent", NS)) == 1
        assert len(tien_trinh.findall("bpmn:sequenceFlow", NS)) == so_canh + 1, qt.code


def test_luong_noi_hai_nut_co_that_va_co_bo_cuc(client, session, rule_set):
    for qt in _cac_quy_trinh(session):
        goc = _tai(client, qt.code)
        tien_trinh = goc.find("bpmn:process", NS)
        cac_nut = {e.get("id") for e in tien_trinh if not e.tag.endswith(("sequenceFlow", "documentation"))}
        cac_luong = tien_trinh.findall("bpmn:sequenceFlow", NS)
        for luong in cac_luong:
            assert luong.get("sourceRef") in cac_nut and luong.get("targetRef") in cac_nut, luong.get("id")

        tat_ca_ma = [e.get("id") for e in goc.iter() if e.get("id")]
        assert len(tat_ca_ma) == len(set(tat_ca_ma)), "trùng id trong tài liệu"

        co_bo_cuc = {e.get("bpmnElement") for e in goc.iter() if e.tag.endswith(("BPMNShape", "BPMNEdge"))}
        assert cac_nut | {l.get("id") for l in cac_luong} <= co_bo_cuc, qt.code


def test_canh_ghi_vai_va_nhan_hoat_dong(client, session, rule_set):
    qt = _cac_quy_trinh(session)[0]
    bo = get_active_rule_set(session, qt.code)
    canh = session.scalars(
        select(Transition).where(Transition.rule_set_id == bo.id, Transition.is_system.is_(False))
    ).first()
    goc = _tai(client, qt.code)
    luong = goc.find(f".//bpmn:sequenceFlow[@id='Flow_{canh.id}']", NS)
    assert luong.get("name") == canh.activity_label
    ghi = luong.find("bpmn:documentation", NS)
    if canh.role_codes:
        assert all(v in ghi.text for v in canh.role_codes)


def test_quy_trinh_khong_ton_tai(client):
    tra = client.get("/core/v1/workflow/processes/khong-co/bpmn")
    assert tra.status_code == 422
    assert tra.json()["detail"]["code"] == "unknown-process"
