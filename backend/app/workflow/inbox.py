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
# HAI CUỘC MỖI HỒ SƠ (#156): cuộc với người gửi, và cuộc NỘI BỘ — lời nhắn thuộc loại
# `hidden_from_requester` — chỉ nhân viên mở được hồ sơ thấy. Người gửi của chính hồ sơ
# không bao giờ có cuộc nội bộ, kể cả khi họ cũng là nhân viên. Mỗi cuộc có số chưa đọc
# và mốc đã đọc riêng. Cuộc nội bộ không có "đang chờ bạn": tin nội bộ không nhắm riêng ai.
#
# ĐÃ ĐỌC không đổi hồ sơ (ADR-0005): bảng `case_message_reads` riêng, không vào
# `event_log`, không chạm `requests`. Tệp này không có tên vai trò hay tên trạng thái nào.

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
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
from app.workflow.engine import ma_quy_trinh_ung_dung, rule_sets_in_use
from app.workflow.messages import ma_loai_noi_bo, thay_noi_bo
from app.workflow.phan_trang import ThamSoTrang, cat_trang, khop_tim, tham_so_trang
from app.workflow.routes import _ma_ho_so, _o_trang_thai
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
        # Hàng đợi điều phối của mọi bộ quy tắc còn hồ sơ mở, mỗi hồ sơ theo bộ của nó (#299)
        hang_doi = _o_trang_thai(
            {
                bo: [t.code for t in trang_thai_hang_doi_dieu_phoi(session, bo)]
                for bo in rule_sets_in_use(session, ma_quy_trinh_ung_dung(session))
            }
        )
        da_nhan = select(CaseMessage.case_id).where(CaseMessage.author == actor.id)
        dieu_kien.append(or_(hang_doi, Request.id.in_(da_nhan)))
    return or_(*dieu_kien) & Request.id.in_(select(CaseMessage.case_id))


def _so_chua_doc(session: Session, actor: Actor, case_ids) -> dict[tuple[int, bool], int]:
    """Số lời nhắn chưa đọc theo cuộc — cặp (hồ sơ, nội bộ hay không): sau mốc đã đọc của
    đúng cuộc đó, do người khác viết. Người gửi của hồ sơ không có cuộc nội bộ (#156)."""
    noi_bo = MessageKind.hidden_from_requester
    moc = (
        select(CaseMessageRead.last_read_id)
        .where(
            CaseMessageRead.case_id == CaseMessage.case_id,
            CaseMessageRead.reader == actor.id,
            CaseMessageRead.internal == noi_bo,
        )
        .scalar_subquery()
    )
    dong = session.execute(
        select(CaseMessage.case_id, noi_bo, func.count())
        .join(MessageKind, MessageKind.code == CaseMessage.kind)
        .join(Request, Request.id == CaseMessage.case_id)
        .where(
            CaseMessage.case_id.in_(case_ids),
            CaseMessage.author != actor.id,
            CaseMessage.id > func.coalesce(moc, 0),
            or_(~noi_bo, Request.requester_id != actor.id),
        )
        .group_by(CaseMessage.case_id, noi_bo)
    ).all()
    return {(case_id, noi): so for case_id, noi, so in dong}


def _loc_kenh(cau, noi_bo: bool):
    """Thu câu chọn lời nhắn về đúng một cuộc: nội bộ, hoặc với người gửi."""
    loai = ma_loai_noi_bo()
    return cau.where(CaseMessage.kind.in_(loai) if noi_bo else CaseMessage.kind.not_in(loai))


@router.get("", response_model=HopThuRa)
def hop_thu(
    session: _Phien,
    actor: _NguoiGoi,
    trang: Annotated[ThamSoTrang, Depends(tham_so_trang)],
    q: Annotated[str | None, Query(description="Tìm theo mã, tiêu đề, người gửi, mô tả — không phân biệt dấu")] = None,
    unread: Annotated[bool, Query(description="Chỉ cuộc còn lời nhắn chưa đọc")] = False,
    internal: Annotated[
        bool | None, Query(description="true: chỉ cuộc nội bộ · false: chỉ cuộc với người gửi")
    ] = None,
    case_id: Annotated[
        int | None, Query(description="Chỉ các cuộc của một hồ sơ — cuộc đang mở không ở trang này")
    ] = None,
) -> HopThuRa:
    """Các cuộc trò chuyện của người đang đăng nhập, lời nhắn mới nhất lên đầu, có phân trang (#232).

    Hộp thư phình theo lịch sử — mọi hồ sơ từng nhắn trong phạm vi — nên lời nhắn cuối của mọi
    cuộc lấy bằng MỘT truy vấn gom nhóm, không mỗi hồ sơ một truy vấn; số chưa đọc cũng một truy
    vấn. Chỉ cuộc của trang mới được dựng đầy đủ. Tổng số chưa đọc vẫn tính trên mọi cuộc — con số
    trên thanh bên.
    """
    cua = _Cua(session, actor)
    cac_ho_so = {h.id: h for h in session.scalars(select(Request).where(_pham_vi(session, cua))).all()}
    if not cac_ho_so:
        return HopThuRa(items=[], unread=0, total=0, offset=trang.offset, limit=trang.limit)

    noi_bo_cot = MessageKind.hidden_from_requester
    cuoi_moi_cuoc = session.execute(
        select(CaseMessage.case_id, noi_bo_cot, func.max(CaseMessage.id))
        .join(MessageKind, MessageKind.code == CaseMessage.kind)
        .where(CaseMessage.case_id.in_(list(cac_ho_so)))
        .group_by(CaseMessage.case_id, noi_bo_cot)
    ).all()
    chua_doc = _so_chua_doc(session, actor, list(cac_ho_so))

    # Mỗi cuộc: (hồ sơ, nội bộ hay không, mã lời nhắn cuối). Cuộc nội bộ chỉ người thấy được
    # nội bộ của hồ sơ đó mới có (#156).
    cac_khoa = [
        (cac_ho_so[ma], bool(nb), cuoi)
        for ma, nb, cuoi in cuoi_moi_cuoc
        if not nb or thay_noi_bo(cac_ho_so[ma], actor)
    ]
    tong_chua_doc = sum(chua_doc.get((h.id, nb), 0) for h, nb, _ in cac_khoa)

    # Số trên chip lọc tính trên các cuộc khớp ô tìm, trước khi lọc theo chip
    khop = [
        (h, nb, cuoi)
        for h, nb, cuoi in cac_khoa
        if khop_tim(q, h.title, h.requester_label, h.description, _ma_ho_so(h))
        and (case_id is None or h.id == case_id)
    ]
    da_loc = [
        (h, nb, cuoi)
        for h, nb, cuoi in khop
        if (not unread or chua_doc.get((h.id, nb), 0) > 0) and (internal is None or nb == internal)
    ]
    # Mã lời nhắn tăng dần theo thời gian ghi, nên xếp theo mã cuối là xếp theo lời nhắn mới nhất
    da_loc.sort(key=lambda k: k[2], reverse=True)
    trang_nay = cat_trang(da_loc, trang)

    loi_nhan = {
        m.id: m
        for m in session.scalars(
            select(CaseMessage).where(CaseMessage.id.in_([cuoi for _, _, cuoi in trang_nay]))
        ).all()
    }
    ten_loai = {k.code: k.label for k in session.scalars(select(MessageKind)).all()}
    # Hồ sơ của các cuộc có thể thuộc nhiều bộ quy tắc (#299): nhãn tra theo bộ của từng hồ sơ
    trang_thai = {
        (s.rule_set_id, s.code): s
        for s in session.scalars(
            select(State).where(State.rule_set_id.in_({h.rule_set_id for h, _, _ in trang_nay}))
        ).all()
    }

    cac_cuoc = []
    for ho_so, noi_bo, ma_cuoi in trang_nay:
        tt = trang_thai[(ho_so.rule_set_id, ho_so.current_state)]
        cuoi = loi_nhan[ma_cuoi]
        tu_nguoi_gui = cuoi.author == ho_so.requester_id
        cac_cuoc.append(
            CuocTroChuyenRa(
                case_id=ho_so.id,
                code=_ma_ho_so(ho_so),
                title=ho_so.title,
                state=TrangThaiRa(code=tt.code, label=tt.label, is_terminal=tt.is_terminal),
                requester_id=ho_so.requester_id,
                requester_label=ho_so.requester_label,
                workspace=cua.noi_mo(ho_so),
                internal=noi_bo,
                last_message=LoiNhanCuoiRa(
                    author_label=cuoi.author_label,
                    kind_label=ten_loai.get(cuoi.kind, cuoi.kind),
                    body=cuoi.body,
                    created_at=cuoi.created_at,
                    mine=cuoi.author == actor.id,
                    from_requester=tu_nguoi_gui,
                ),
                unread=chua_doc.get((ho_so.id, noi_bo), 0),
                # Phía bên kia nhắn sau cùng: người gửi chờ nhân viên, hoặc ngược lại.
                # Hồ sơ kết thúc thì không ai còn phải trả lời. Cuộc nội bộ không bao giờ
                # có dấu này (navigator chốt 06/10/2026): người gửi không nhắn được nội
                # bộ, nên mọi tin của cuộc đó đều ở phía nhân viên.
                waiting_on_me=(
                    not tt.is_terminal
                    and cuoi.author != actor.id
                    and tu_nguoi_gui != (ho_so.requester_id == actor.id)
                ),
            )
        )

    return HopThuRa(
        items=cac_cuoc,
        unread=tong_chua_doc,
        unread_conversations=sum(1 for h, nb, _ in khop if chua_doc.get((h.id, nb), 0) > 0),
        internal_conversations=sum(1 for _, nb, _ in khop if nb),
        total=len(da_loc),
        offset=trang.offset,
        limit=trang.limit,
    )


@router.get("/unread", response_model=SoChuaDocRa)
def so_chua_doc(session: _Phien, actor: _NguoiGoi) -> SoChuaDocRa:
    """Chỉ con số chưa đọc — giao diện hỏi định kỳ cho thanh bên, nên phải nhẹ."""
    cua = _Cua(session, actor)
    trong_pham_vi = select(Request.id).where(_pham_vi(session, cua))
    return SoChuaDocRa(unread=sum(_so_chua_doc(session, actor, trong_pham_vi).values()))


@router.post("/{case_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def danh_dau_da_doc(
    case_id: int, session: _Phien, actor: _NguoiGoi, internal: bool = False
) -> Response:
    """Đánh dấu đã đọc tới lời nhắn mới nhất của một cuộc trên hồ sơ — cuộc với người gửi,
    hoặc cuộc nội bộ khi `internal=true` (#156).

    Gác bằng cửa nhìn thấy, không bằng phạm vi hộp thư: mở thẻ Trao đổi trên trang hồ sơ
    cũng đánh dấu đã đọc, kể cả hồ sơ chưa vào hộp thư. Không mở được hồ sơ — hay đòi cuộc
    nội bộ của hồ sơ mình gửi — thì 404, như các cửa khác: không xác nhận điều gì tồn tại.
    Mốc chỉ dời lên, không lùi.
    """
    ho_so = session.get(Request, case_id)
    if (
        ho_so is None
        or _Cua(session, actor).noi_mo(ho_so) is None
        or (internal and not thay_noi_bo(ho_so, actor))
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "case-not-found", "message": "Không tìm thấy hồ sơ."},
        )

    moi_nhat = session.scalar(
        _loc_kenh(select(func.max(CaseMessage.id)).where(CaseMessage.case_id == case_id), internal)
    )
    if moi_nhat is not None:
        session.execute(
            insert(CaseMessageRead)
            .values(case_id=case_id, reader=actor.id, internal=internal, last_read_id=moi_nhat)
            .on_conflict_do_update(
                index_elements=[
                    CaseMessageRead.case_id,
                    CaseMessageRead.reader,
                    CaseMessageRead.internal,
                ],
                set_={
                    "last_read_id": func.greatest(CaseMessageRead.last_read_id, moi_nhat),
                    "read_at": func.now(),
                },
            )
        )
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
