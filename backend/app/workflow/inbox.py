# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Hộp thư chung (#155): lời nhắn của mọi hồ sơ người này đang giữ, gom một chỗ.
#
# KHÔNG CÓ KHO TIN NHẮN THỨ HAI. Hộp thư đọc đúng bảng `case_messages` của lời nhắn trên
# hồ sơ (#128); mỗi cuộc trò chuyện là lời nhắn của MỘT hồ sơ. Gửi lời nhắn vẫn qua điểm
# cuối `/…/requests/{id}/messages` của từng buồng lái, nên mọi luật của #128 — loại lời
# nhắn, hồ sơ kết thúc chỉ đọc, luật hỏi lại — giữ nguyên.
#
# CỬA NHÌN THẤY không viết lại ở đây. Một hồ sơ chỉ vào hộp thư khi người này mở được nó
# qua một trong ba cửa sẵn có:
#
#   portal       — người gửi của hồ sơ (cửa `/requests/{id}`)
#   department   — người của phòng đang giữ hồ sơ (cửa `/department/…`)
#   coordination — điều phối viên (cửa `/coordination/…`, mở được mọi hồ sơ)
#
# Rồi THU HẸP theo việc đang giữ (navigator chốt 05/10/2026): điều phối viên mở được mọi
# hồ sơ, nhưng hộp thư của họ chỉ có hồ sơ đang ở hàng đợi điều phối và hồ sơ họ đã từng
# nhắn — không phải mọi cuộc trò chuyện của cả công ty. Phòng ban thấy mọi hồ sơ của phòng
# có lời nhắn, để người mới được giao lại hồ sơ đọc được trao đổi cũ.
#
# ĐÃ ĐỌC không đổi hồ sơ (ADR-0005): bảng `case_message_reads` riêng, không vào
# `event_log`, không chạm `requests`. Tệp này không có tên vai trò hay tên trạng thái nào.

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor
from app.db import get_session
from app.models.case import CaseMessage, CaseMessageRead, Request
from app.models.workflow_config import MessageKind, State
from app.workflow.context import Actor
from app.workflow.coordination import trang_thai_hang_doi_dieu_phoi, vao_duoc_buong_lai
from app.workflow.department import vao_duoc_phong_ban
from app.workflow.engine import get_active_rule_set
from app.workflow.routes import _ma_ho_so
from app.workflow.schemas import CuocTroChuyenRa, HopThuRa, LoiNhanCuoiRa, SoChuaDocRa, TrangThaiRa

router = APIRouter(prefix="/inbox", tags=["Hộp thư"])

_Phien = Annotated[Session, Depends(get_session)]
_NguoiGoi = Annotated[Actor, Depends(current_actor)]


class _Cua:
    """Người này qua được những cửa nào — tính một lần cho cả lần gọi."""

    def __init__(self, session: Session, actor: Actor) -> None:
        self.actor = actor
        self.phong_ban = vao_duoc_phong_ban(session, actor)
        self.dieu_phoi = vao_duoc_buong_lai(actor)

    def noi_mo(self, ho_so: Request) -> str | None:
        """Cửa người này mở hồ sơ, hoặc `None` nếu không mở được.

        Người gửi của hồ sơ đi cửa của người gửi trước — kể cả khi họ cũng là nhân viên —
        vì ở cổng đó họ có đủ thao tác của chủ hồ sơ.
        """
        if ho_so.requester_id == self.actor.id:
            return "portal"
        if self.phong_ban and ho_so.department_code in self.actor.departments:
            return "department"
        if self.dieu_phoi:
            return "coordination"
        return None


def _pham_vi(session: Session, cua: _Cua):
    """Điều kiện SQL chọn hồ sơ vào hộp thư: mở được VÀ đang giữ việc. Chỉ hồ sơ có ít nhất
    một lời nhắn mới thành cuộc trò chuyện."""
    actor = cua.actor
    dieu_kien = [Request.requester_id == actor.id]
    if cua.phong_ban:
        dieu_kien.append(Request.department_code.in_(actor.departments))
    if cua.dieu_phoi:
        rule_set = get_active_rule_set(session)
        hang_doi = [t.code for t in trang_thai_hang_doi_dieu_phoi(session, rule_set.id)]
        da_nhan = select(CaseMessage.case_id).where(CaseMessage.author == actor.id)
        dieu_kien.append(or_(Request.current_state.in_(hang_doi), Request.id.in_(da_nhan)))
    return or_(*dieu_kien) & Request.id.in_(select(CaseMessage.case_id))


def _so_chua_doc(session: Session, actor: Actor, case_ids) -> dict[int, int]:
    """Số lời nhắn chưa đọc theo hồ sơ: sau mốc đã đọc, do người khác viết."""
    moc = (
        select(CaseMessageRead.last_read_id)
        .where(CaseMessageRead.case_id == CaseMessage.case_id, CaseMessageRead.reader == actor.id)
        .scalar_subquery()
    )
    dong = session.execute(
        select(CaseMessage.case_id, func.count())
        .where(
            CaseMessage.case_id.in_(case_ids),
            CaseMessage.author != actor.id,
            CaseMessage.id > func.coalesce(moc, 0),
        )
        .group_by(CaseMessage.case_id)
    ).all()
    return {case_id: so for case_id, so in dong}


@router.get("", response_model=HopThuRa)
def hop_thu(session: _Phien, actor: _NguoiGoi) -> HopThuRa:
    """Các cuộc trò chuyện của người đang đăng nhập, lời nhắn mới nhất lên đầu."""
    cua = _Cua(session, actor)
    cac_ho_so = session.scalars(select(Request).where(_pham_vi(session, cua))).all()
    if not cac_ho_so:
        return HopThuRa(items=[], unread=0)

    chua_doc = _so_chua_doc(session, actor, [h.id for h in cac_ho_so])
    ten_loai = {k.code: k.label for k in session.scalars(select(MessageKind)).all()}
    trang_thai = {
        s.code: s
        for s in session.scalars(
            select(State).where(State.rule_set_id == cac_ho_so[0].rule_set_id)
        ).all()
    }

    cac_cuoc = []
    for ho_so in cac_ho_so:
        cuoi = session.scalars(
            select(CaseMessage)
            .where(CaseMessage.case_id == ho_so.id)
            .order_by(CaseMessage.created_at.desc(), CaseMessage.id.desc())
            .limit(1)
        ).one()
        tu_nguoi_gui = cuoi.author == ho_so.requester_id
        tt = trang_thai[ho_so.current_state]
        cac_cuoc.append(
            CuocTroChuyenRa(
                case_id=ho_so.id,
                code=_ma_ho_so(ho_so),
                title=ho_so.title,
                state=TrangThaiRa(code=tt.code, label=tt.label, is_terminal=tt.is_terminal),
                requester_id=ho_so.requester_id,
                requester_label=ho_so.requester_label,
                workspace=cua.noi_mo(ho_so),
                last_message=LoiNhanCuoiRa(
                    author_label=cuoi.author_label,
                    kind_label=ten_loai.get(cuoi.kind, cuoi.kind),
                    body=cuoi.body,
                    created_at=cuoi.created_at,
                    mine=cuoi.author == actor.id,
                    from_requester=tu_nguoi_gui,
                ),
                unread=chua_doc.get(ho_so.id, 0),
                # Phía bên kia nhắn sau cùng: người gửi chờ nhân viên, hoặc ngược lại.
                # Hồ sơ kết thúc thì không ai còn phải trả lời.
                waiting_on_me=(
                    not tt.is_terminal
                    and cuoi.author != actor.id
                    and tu_nguoi_gui != (ho_so.requester_id == actor.id)
                ),
            )
        )

    cac_cuoc.sort(key=lambda c: c.last_message.created_at, reverse=True)
    return HopThuRa(items=cac_cuoc, unread=sum(c.unread for c in cac_cuoc))


@router.get("/unread", response_model=SoChuaDocRa)
def so_chua_doc(session: _Phien, actor: _NguoiGoi) -> SoChuaDocRa:
    """Chỉ con số chưa đọc — giao diện hỏi định kỳ cho thanh bên, nên phải nhẹ."""
    cua = _Cua(session, actor)
    trong_pham_vi = select(Request.id).where(_pham_vi(session, cua))
    return SoChuaDocRa(unread=sum(_so_chua_doc(session, actor, trong_pham_vi).values()))


@router.post("/{case_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def danh_dau_da_doc(case_id: int, session: _Phien, actor: _NguoiGoi) -> Response:
    """Đánh dấu đã đọc tới lời nhắn mới nhất của hồ sơ.

    Gác bằng cửa nhìn thấy, không bằng phạm vi hộp thư: mở thẻ Trao đổi trên trang hồ sơ
    cũng đánh dấu đã đọc, kể cả hồ sơ chưa vào hộp thư. Không mở được hồ sơ thì 404, như
    các cửa khác — không xác nhận hồ sơ đó có tồn tại. Mốc chỉ dời lên, không lùi.
    """
    ho_so = session.get(Request, case_id)
    if ho_so is None or _Cua(session, actor).noi_mo(ho_so) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "case-not-found", "message": "Không tìm thấy hồ sơ."},
        )

    moi_nhat = session.scalar(
        select(func.max(CaseMessage.id)).where(CaseMessage.case_id == case_id)
    )
    if moi_nhat is not None:
        session.execute(
            insert(CaseMessageRead)
            .values(case_id=case_id, reader=actor.id, last_read_id=moi_nhat)
            .on_conflict_do_update(
                index_elements=[CaseMessageRead.case_id, CaseMessageRead.reader],
                set_={
                    "last_read_id": func.greatest(CaseMessageRead.last_read_id, moi_nhat),
                    "read_at": func.now(),
                },
            )
        )
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
