# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Xuất quy trình ra BPMN 2.0 (#405).
#
#     GET /core/v1/workflow/processes/{code}/bpmn   → application/xml
#
# Quy trình của động cơ là DỮ LIỆU — trạng thái, cạnh, vai trò trong các bảng cấu hình. Điểm cuối này dựng bộ
# quy tắc đang bật của một quy trình thành một tệp BPMN 2.0 (chuẩn OMG, ISO/IEC 19510) kèm phần bố cục sơ đồ
# (BPMN DI), nên mở được ngay bằng công cụ nguồn mở như bpmn.io hay Camunda Modeler: người phân tích nghiệp vụ
# đọc quy trình bằng ký hiệu quen thuộc, quy trình mang sang hệ khác được — không lệ thuộc định dạng riêng.
#
# Ánh xạ, một chiều (xuất, không nhập):
#   - trạng thái không kết thúc → `userTask`, trạng thái kết thúc → `endEvent`, tên lấy nhãn trạng thái
#   - một `startEvent` nối vào trạng thái `is_initial`
#   - mỗi cạnh → `sequenceFlow` mang nhãn hoạt động; cạnh hệ thống tự đi ghi "(tự động)"; vai đi được cạnh
#     và các cờ (ghi chú bắt buộc, làm lại) vào `documentation` của cạnh
#   - bố cục: xếp cột theo độ sâu tìm theo chiều rộng từ trạng thái đầu, mỗi cột xếp dọc theo `display_order`
#
# Không gì trong tệp biết tên trạng thái hay quy trình nào. Chỉ thư viện chuẩn (`xml.etree`).

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import deque
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor
from app.db import get_session
from app.models.workflow_config import Process, State, Transition
from app.workflow.context import Actor
from app.workflow.engine import get_active_rule_set
from app.workflow.routes import chon_quy_trinh

router = APIRouter()

BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI = "http://www.omg.org/spec/BPMN/20100524/DI"
DC = "http://www.omg.org/spec/DD/20100524/DC"
DI = "http://www.omg.org/spec/DD/20100524/DI"
for _tien_to, _uri in (("bpmn", BPMN), ("bpmndi", BPMNDI), ("dc", DC), ("di", DI)):
    ET.register_namespace(_tien_to, _uri)

# Kích thước và khoảng cách bố cục, đơn vị điểm ảnh của BPMN DI
RONG_VIEC, CAO_VIEC = 140, 70
CO_SU_KIEN = 36
CACH_COT, CACH_HANG = 220, 120
LE_TRAI, LE_TREN = 60, 60


def _ma(tien_to: str, gia_tri: str) -> str:
    """Định danh hợp lệ kiểu NCName của XML từ một mã dữ liệu."""
    return f"{tien_to}_{re.sub(r'[^A-Za-z0-9_.-]', '_', gia_tri)}"


def _the(cha: ET.Element, ns: str, ten: str, **thuoc_tinh: str) -> ET.Element:
    return ET.SubElement(cha, f"{{{ns}}}{ten}", {k: v for k, v in thuoc_tinh.items() if v is not None})


def _do_sau(dau: str | None, cac_canh: list[Transition], cac_ma: list[str]) -> dict[str, int]:
    """Cột của từng trạng thái: độ sâu ngắn nhất từ trạng thái đầu; trạng thái không tới được xếp cột cuối."""
    ke: dict[str, list[str]] = {}
    for c in cac_canh:
        if c.from_state != c.to_state:
            ke.setdefault(c.from_state, []).append(c.to_state)
    sau: dict[str, int] = {}
    if dau is not None:
        sau[dau] = 0
        hang = deque([dau])
        while hang:
            dang = hang.popleft()
            for toi in ke.get(dang, []):
                if toi not in sau:
                    sau[toi] = sau[dang] + 1
                    hang.append(toi)
    cuoi = max(sau.values(), default=-1) + 1
    return {m: sau.get(m, cuoi) for m in cac_ma}


def dung_bpmn(quy_trinh: Process, cac_trang_thai: list[State], cac_canh: list[Transition]) -> bytes:
    """Tài liệu BPMN 2.0 (kèm DI) của một bộ quy tắc. Hàm thuần — kiểm thử gọi thẳng."""
    goc = ET.Element(
        f"{{{BPMN}}}definitions",
        {
            "id": _ma("Definitions", quy_trinh.code),
            "targetNamespace": "https://github.com/AlaVox-lab/corelens/bpmn",
            "exporter": "Corelens",
        },
    )
    ma_qt = _ma("Process", quy_trinh.code)
    qt = _the(goc, BPMN, "process", id=ma_qt, name=quy_trinh.label, isExecutable="false")
    if quy_trinh.description:
        _the(qt, BPMN, "documentation").text = quy_trinh.description

    cac_trang_thai = sorted(cac_trang_thai, key=lambda s: (s.display_order, s.code))
    nut = {s.code: _ma("State", s.code) for s in cac_trang_thai}
    dau = next((s.code for s in cac_trang_thai if s.is_initial), None)

    # Luồng: (mã, nguồn, đích, tên, chú thích)
    cac_luong: list[tuple[str, str, str, str | None, str | None]] = []
    if dau is not None:
        cac_luong.append(("Flow_start", "StartEvent_1", nut[dau], None, None))
    for c in sorted(cac_canh, key=lambda c: (c.display_order, c.id)):
        if c.from_state not in nut or c.to_state not in nut:
            continue
        ten = c.activity_label + (" (tự động)" if c.is_system else "")
        ghi = []
        if c.role_codes:
            ghi.append("Vai: " + ", ".join(sorted(c.role_codes)))
        if c.requires_note:
            ghi.append(f"Bắt buộc ghi: {c.note_label or 'lý do'}")
        if c.is_rework:
            ghi.append("Cạnh làm lại")
        cac_luong.append((_ma("Flow", str(c.id)), nut[c.from_state], nut[c.to_state], ten, "; ".join(ghi) or None))

    vao: dict[str, list[str]] = {}
    ra: dict[str, list[str]] = {}
    for ma, nguon, dich, _, _ in cac_luong:
        ra.setdefault(nguon, []).append(ma)
        vao.setdefault(dich, []).append(ma)

    if dau is not None:
        su_kien = _the(qt, BPMN, "startEvent", id="StartEvent_1", name="Bắt đầu")
        for ma in ra.get("StartEvent_1", []):
            _the(su_kien, BPMN, "outgoing").text = ma
    for s in cac_trang_thai:
        loai = "endEvent" if s.is_terminal else "userTask"
        el = _the(qt, BPMN, loai, id=nut[s.code], name=s.label)
        if s.description:
            _the(el, BPMN, "documentation").text = s.description
        for ma in vao.get(nut[s.code], []):
            _the(el, BPMN, "incoming").text = ma
        for ma in ra.get(nut[s.code], []):
            _the(el, BPMN, "outgoing").text = ma
    for ma, nguon, dich, ten, ghi in cac_luong:
        luong = _the(qt, BPMN, "sequenceFlow", id=ma, sourceRef=nguon, targetRef=dich, name=ten)
        if ghi:
            _the(luong, BPMN, "documentation").text = ghi

    # --- Bố cục (BPMN DI) --------------------------------------------------------------------------------
    cot = _do_sau(dau, cac_canh, [s.code for s in cac_trang_thai])
    hang_trong_cot: dict[int, int] = {}
    hop: dict[str, tuple[float, float, float, float]] = {}  # mã nút → x, y, rộng, cao
    if dau is not None:
        hop["StartEvent_1"] = (LE_TRAI, LE_TREN + (CAO_VIEC - CO_SU_KIEN) / 2, CO_SU_KIEN, CO_SU_KIEN)
    for s in cac_trang_thai:
        c = cot[s.code]
        h = hang_trong_cot.get(c, 0)
        hang_trong_cot[c] = h + 1
        x = LE_TRAI + CO_SU_KIEN + 80 + c * CACH_COT
        y = LE_TREN + h * CACH_HANG
        if s.is_terminal:
            hop[nut[s.code]] = (x + (RONG_VIEC - CO_SU_KIEN) / 2, y + (CAO_VIEC - CO_SU_KIEN) / 2, CO_SU_KIEN, CO_SU_KIEN)
        else:
            hop[nut[s.code]] = (x, y, RONG_VIEC, CAO_VIEC)

    so_do = _the(goc, BPMNDI, "BPMNDiagram", id="BPMNDiagram_1")
    mat = _the(so_do, BPMNDI, "BPMNPlane", id="BPMNPlane_1", bpmnElement=ma_qt)
    for ma, (x, y, w, h) in hop.items():
        hinh = _the(mat, BPMNDI, "BPMNShape", id=f"{ma}_di", bpmnElement=ma)
        _the(hinh, DC, "Bounds", x=str(x), y=str(y), width=str(w), height=str(h))
    for ma, nguon, dich, _, _ in cac_luong:
        canh = _the(mat, BPMNDI, "BPMNEdge", id=f"{ma}_di", bpmnElement=ma)
        for px, py in _duong(hop[nguon], hop[dich], nguon == dich):
            _the(canh, DI, "waypoint", x=str(px), y=str(py))

    ET.indent(goc)
    return ET.tostring(goc, encoding="utf-8", xml_declaration=True)


def _duong(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float], tu_tro: bool
) -> list[tuple[float, float]]:
    """Điểm gãy của một cạnh: thẳng sang phải khi đi tới, vòng xuống dưới khi đi lùi hay tự trỏ."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    if tu_tro:
        return [(ax + aw * 0.7, ay + ah), (ax + aw * 0.7, ay + ah + 30), (ax + aw * 0.3, ay + ah + 30), (ax + aw * 0.3, ay + ah)]
    if bx > ax:
        return [(ax + aw, ay + ah / 2), (bx, by + bh / 2)]
    duoi = max(ay + ah, by + bh) + 40
    return [(ax + aw / 2, ay + ah), (ax + aw / 2, duoi), (bx + bw / 2, duoi), (bx + bw / 2, by + bh)]


@router.get(
    "/processes/{code}/bpmn",
    summary="Quy trình dạng BPMN 2.0",
    response_class=Response,
    responses={200: {"content": {"application/xml": {}}, "description": "Tệp BPMN 2.0 kèm bố cục sơ đồ"}},
)
def xuat_bpmn(
    code: str,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[Actor, Depends(current_actor)],
) -> Response:
    """Bộ quy tắc đang bật của quy trình `code`, dạng BPMN 2.0 kèm bố cục — mở bằng bpmn.io, Camunda Modeler.

    Xuất một chiều để đọc và trao đổi: trạng thái thành `userTask` (kết thúc thành `endEvent`), cạnh thành
    `sequenceFlow` mang nhãn hoạt động, vai và cờ của cạnh ghi trong `documentation`. Sửa quy trình vẫn là sửa
    dữ liệu cấu hình.
    """
    ma = chon_quy_trinh(session, code)
    quy_trinh = session.get(Process, ma)
    bo = get_active_rule_set(session, ma)
    cac_trang_thai = list(session.scalars(select(State).where(State.rule_set_id == bo.id)))
    cac_canh = list(session.scalars(select(Transition).where(Transition.rule_set_id == bo.id)))
    return Response(
        dung_bpmn(quy_trinh, cac_trang_thai, cac_canh),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{ma}.bpmn"'},
    )
