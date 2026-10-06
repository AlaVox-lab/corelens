# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Lời nhắn trên hồ sơ (#128, ADR-0005).
#
# RANH GIỚI CỦA TỆP NÀY: lời nhắn KHÔNG đổi hồ sơ. Không gọi `perform_transition`, không
# ghi `event_log`, không ghi một cột nào của `requests` — kể cả `updated_at` và các cột
# đồng hồ SLA. Thao tác nào đổi hồ sơ thì là cạnh và đi qua cửa chuyển trạng thái; xem
# ARCHITECTURE.md mục 6.2. Hỏi chính thức — dừng đồng hồ, bắt buộc trả lời — vẫn là cạnh
# "Yêu cầu bổ sung thông tin".
#
# Tệp này cũng KHÔNG kiểm ai nhìn thấy hồ sơ. Ai mở được hồ sơ thì nhắn được, và cửa nhìn
# thấy nằm ở từng buồng lái — routes.py, coordination.py, department.py. Ở đây chỉ thu hẹp
# thêm theo bảng `message_kinds`: vai trò, chủ hồ sơ, chặng phòng ban, luật hỏi lại.
# Không có tên vai trò, tên trạng thái hay mã loại lời nhắn nào trong mã.
#
# TRÒ CHUYỆN NỘI BỘ (#156): loại mang cờ `hidden_from_requester` thì người gửi của chính
# hồ sơ không đọc, không gửi được — kể cả khi họ cũng là nhân viên. Mọi chỗ trả lời nhắn
# hay suy điều gì từ lời nhắn đều đi qua tệp này, nên bộ lọc chỉ có ở đây. Lời nhắn nội bộ
# không tính vào "ai nhắn sau cùng" và không mở khóa luật hỏi lại: người gửi không thấy
# chúng, nên chúng không phải câu trả lời cho người gửi.

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import literal, select, tuple_
from sqlalchemy.orm import Session

from app.models.case import CaseMessage, Request
from app.models.workflow_config import MessageKind, State
from app.rules.sla import bay_gio
from app.workflow.assignment import trang_thai_hang_doi_phong_ban
from app.workflow.context import Actor


class MessageRejected(Exception):
    """Lời nhắn bị từ chối. Mang mã máy đọc được và mã HTTP, như lỗi của engine."""

    def __init__(self, code: str, message: str, http_status: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


@dataclass(frozen=True)
class LoaiGuiDuoc:
    """Một loại lời nhắn người này gửi được. `gui_lai_tu` có giá trị nghĩa là loại đó
    đang chờ luật hỏi lại, và chưa gửi được trước mốc đó."""

    loai: MessageKind
    gui_lai_tu: dt.datetime | None


def _thu_tu():
    """Thứ tự của lời nhắn: thời điểm ghi, rồi định danh cho các dòng cùng giao dịch."""
    return (CaseMessage.created_at, CaseMessage.id)


def thay_noi_bo(ho_so: Request, actor: Actor) -> bool:
    """Người này đọc được lời nhắn nội bộ của hồ sơ không (#156).

    Phía gọi đã bảo đảm người này mở được hồ sơ. Chỉ người gửi của chính hồ sơ bị chặn —
    theo hồ sơ, không theo vai trò: điều phối viên mở hồ sơ mình gửi cũng không thấy.
    """
    return actor.id != ho_so.requester_id


def ma_loai_noi_bo():
    """Câu chọn mã các loại lời nhắn nội bộ, để lọc ngay trong SQL."""
    return select(MessageKind.code).where(MessageKind.hidden_from_requester)


def cac_loi_nhan(session: Session, ho_so: Request, actor: Actor) -> list[CaseMessage]:
    """Lời nhắn của hồ sơ mà người này được đọc, theo thứ tự thời gian."""
    cau = select(CaseMessage).where(CaseMessage.case_id == ho_so.id)
    if not thay_noi_bo(ho_so, actor):
        cau = cau.where(CaseMessage.kind.not_in(ma_loai_noi_bo()))
    return list(session.scalars(cau.order_by(*_thu_tu())).all())


def loi_nhan_cuoi_tu_nguoi_gui(session: Session, ho_so: Request) -> bool | None:
    """Lời nhắn sau cùng là của người gửi hồ sơ (`True`), của nhân viên (`False`), hay
    hồ sơ chưa có lời nhắn nào (`None`).

    Nguồn của dấu hiệu trên hàng đợi: lời nhắn cuối là của người gửi thì người gửi đang
    chờ nhân viên trả lời, và ngược lại. Suy từ ai nhắn sau cùng, không theo dõi đã đọc
    hay chưa — chốt với navigator ngày 24/09/2026. Lời nhắn nội bộ không tính (#156).
    """
    tac_gia = session.scalar(
        select(CaseMessage.author)
        .where(CaseMessage.case_id == ho_so.id, CaseMessage.kind.not_in(ma_loai_noi_bo()))
        .order_by(*(c.desc() for c in _thu_tu()))
        .limit(1)
    )
    return None if tac_gia is None else tac_gia == ho_so.requester_id


def _gui_lai_tu(session: Session, ho_so: Request, loai: MessageKind) -> dt.datetime | None:
    """Mốc gửi lại được loại này, hoặc `None` nếu gửi được ngay.

    Luật hỏi lại: gửi lại chỉ được khi phía bên kia — nhân viên nếu lần trước là người gửi
    hồ sơ, và ngược lại — đã nhắn sau lần gửi trước, hoặc đã quá `reask_after_hours` giờ.
    Nhờ vậy "Hỏi tiến độ" không bấm dồn được, và số lần phòng ban bị hối mà tầng I đếm là
    số thật.
    """
    if loai.reask_after_hours is None:
        return None

    lan_truoc = session.scalars(
        select(CaseMessage)
        .where(CaseMessage.case_id == ho_so.id, CaseMessage.kind == loai.code)
        .order_by(*(c.desc() for c in _thu_tu()))
        .limit(1)
    ).first()
    if lan_truoc is None:
        return None

    tac_gia_sau_do = session.scalars(
        select(CaseMessage.author).where(
            CaseMessage.case_id == ho_so.id,
            # Nhân viên nhắn nội bộ không phải đã trả lời người gửi (#156)
            CaseMessage.kind.not_in(ma_loai_noi_bo()),
            tuple_(*_thu_tu()) > tuple_(literal(lan_truoc.created_at), literal(lan_truoc.id)),
        )
    ).all()
    ben_truoc = lan_truoc.author == ho_so.requester_id
    if any((tac_gia == ho_so.requester_id) != ben_truoc for tac_gia in tac_gia_sau_do):
        return None

    moc = lan_truoc.created_at + dt.timedelta(hours=loai.reask_after_hours)
    return moc if bay_gio(session) < moc else None


def loai_gui_duoc(session: Session, ho_so: Request, actor: Actor) -> list[LoaiGuiDuoc]:
    """Loại lời nhắn người này gửi được trên hồ sơ lúc này, theo thứ tự hiển thị.

    Phía gọi đã bảo đảm người này mở được hồ sơ. Loại không đủ điều kiện thì vắng mặt,
    như cạnh không đi được thì không thành nút. Riêng loại đang chờ luật hỏi lại thì CÓ
    mặt, kèm mốc gửi lại được — để giao diện nói rõ vì sao nút mờ và mờ tới bao giờ.

    Hồ sơ đã kết thúc thì không loại nào: lời nhắn chỉ còn để đọc.
    """
    trang_thai = session.get(State, (ho_so.rule_set_id, ho_so.current_state))
    if trang_thai.is_terminal:
        return []

    chang_phong_ban: set[str] | None = None
    ket_qua = []
    for loai in session.scalars(select(MessageKind).order_by(MessageKind.display_order)).all():
        if not actor.roles & loai.role_codes:
            continue
        if loai.owner_only and actor.id != ho_so.requester_id:
            continue
        if loai.hidden_from_requester and not thay_noi_bo(ho_so, actor):
            continue
        if loai.department_stage_only:
            if chang_phong_ban is None:
                chang_phong_ban = {
                    s.code for s in trang_thai_hang_doi_phong_ban(session, ho_so.rule_set_id)
                }
            if ho_so.current_state not in chang_phong_ban:
                continue
        ket_qua.append(LoaiGuiDuoc(loai, _gui_lai_tu(session, ho_so, loai)))
    return ket_qua


def gui_loi_nhan(
    session: Session, ho_so: Request, actor: Actor, kind: str, body: str | None
) -> CaseMessage:
    """Ghi một lời nhắn. Phía gọi đã kiểm người này mở được hồ sơ.

    Khóa dòng hồ sơ bằng `SELECT FOR UPDATE` trước khi xét luật hỏi lại, để hai lần bấm
    đồng thời không cùng lọt. Khóa không ghi gì vào dòng: `updated_at` giữ nguyên.
    """
    session.execute(select(Request.id).where(Request.id == ho_so.id).with_for_update())

    loai = session.get(MessageKind, kind)
    if loai is None:
        raise MessageRejected("unknown-message-kind", f"Không có loại lời nhắn '{kind}'.", 422)

    trang_thai = session.get(State, (ho_so.rule_set_id, ho_so.current_state))
    if trang_thai.is_terminal:
        raise MessageRejected(
            "case-closed", "Hồ sơ đã kết thúc, lời nhắn chỉ còn để đọc.", 409
        )

    gui_duoc = {g.loai.code: g for g in loai_gui_duoc(session, ho_so, actor)}
    if kind not in gui_duoc:
        raise MessageRejected(
            "message-not-permitted",
            f"Bạn không gửi được “{loai.label}” trên hồ sơ này lúc này.",
            403,
        )
    if gui_duoc[kind].gui_lai_tu is not None:
        raise MessageRejected(
            "reask-too-soon",
            f"Lần “{loai.label}” trước chưa có ai trả lời. Hỏi lại được khi đã có trả lời, "
            f"hoặc sau {loai.reask_after_hours} giờ kể từ lần hỏi đó.",
            409,
        )

    noi_dung = (body or "").strip() or None
    if loai.body_required and noi_dung is None:
        raise MessageRejected("message-body-required", "Nhập nội dung lời nhắn.", 422)

    loi_nhan = CaseMessage(
        case_id=ho_so.id,
        kind=loai.code,
        author=actor.id,
        author_label=actor.label,
        body=noi_dung,
    )
    session.add(loi_nhan)
    session.flush()
    return loi_nhan
