# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Đánh giá mức hài lòng của người gửi khi xác nhận hồ sơ hoàn tất (#433).
#
# Điểm đi CÙNG một lần chuyển trạng thái nhưng KHÔNG qua engine và không vào nhật ký sự kiện: nó không đổi
# trường quyết định nào, nên theo ADR-0005 nó là thao tác không đổi hồ sơ — như lời nhắn. Điểm cuối của người
# gửi gọi `perform_transition` như cũ, rồi ghi một dòng `case_feedback` gắn dòng nhật ký vừa sinh, rồi mới
# commit: hỏng ở đâu thì cả hai cùng hoàn tác.
#
# Cạnh nào cho chấm là dữ liệu — cờ `transitions.collects_feedback` — tệp này không biết mã hoạt động nào.

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.case import CaseFeedback, EventLog, Request
from app.models.workflow_config import Transition
from app.workflow.schemas import DanhGiaRa, DanhGiaVao


def danh_gia_cua(session: Session, case_id: int) -> list[DanhGiaRa]:
    """Các lần chấm của một hồ sơ, theo thời gian."""
    return [
        DanhGiaRa(score=f.score, comment=f.comment, created_at=f.created_at)
        for f in session.scalars(
            select(CaseFeedback)
            .where(CaseFeedback.case_id == case_id)
            .order_by(CaseFeedback.created_at, CaseFeedback.id)
        )
    ]


def dich_cho_cham(session: Session, ho_so: Request) -> set[str]:
    """Trạng thái đích của những cạnh người rời trạng thái hiện tại mà cho chấm điểm."""
    return set(
        session.scalars(
            select(Transition.to_state).where(
                Transition.rule_set_id == ho_so.rule_set_id,
                Transition.from_state == ho_so.current_state,
                Transition.is_system.is_(False),
                Transition.collects_feedback.is_(True),
            )
        )
    )


def kiem_danh_gia(session: Session, case_id: int, to_state: str, danh_gia: DanhGiaVao) -> str | None:
    """Kiểm đánh giá TRƯỚC khi chuyển, để bị từ chối thì không có gì phải hoàn tác. Trả nhận xét đã làm sạch.

    Đọc cột chứ không nạp đối tượng `Request`: nạp trước khi gọi engine thì lệnh khóa dòng bên trong engine có
    nguy cơ không được phát (xem `_kiem_chu_so_huu`). Cạnh không có hay không cho chấm: 422
    `feedback-not-accepted`. Cạnh không có thật thì engine vẫn báo lỗi của nó khi đi — ở đây chỉ nói về điểm.
    """
    dong = session.execute(
        select(Request.rule_set_id, Request.current_state).where(Request.id == case_id)
    ).one()
    cho_cham = session.scalar(
        select(Transition.collects_feedback).where(
            Transition.rule_set_id == dong.rule_set_id,
            Transition.from_state == dong.current_state,
            Transition.to_state == to_state,
            Transition.is_system.is_(False),
        )
    )
    if not cho_cham:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "feedback-not-accepted",
                "message": "Bước này không nhận đánh giá mức hài lòng.",
            },
        )

    nhan_xet = (danh_gia.comment or "").strip() or None
    tran = get_settings().feedback_comment_max_chars
    if nhan_xet is not None and len(nhan_xet) > tran:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "feedback-comment-too-long",
                "message": f"Nhận xét dài tối đa {tran} ký tự — hiện có {len(nhan_xet)}.",
            },
        )
    return nhan_xet


def ghi_danh_gia(session: Session, ho_so: Request, diem: int, nhan_xet: str | None) -> None:
    """Ghi một dòng `case_feedback` gắn dòng nhật ký vừa sinh của lần chuyển — trong giao dịch của người gọi."""
    su_kien = session.scalar(
        select(EventLog.id).where(EventLog.case_id == ho_so.id).order_by(EventLog.id.desc()).limit(1)
    )
    session.add(CaseFeedback(case_id=ho_so.id, event_id=su_kien, score=diem, comment=nhan_xet))
    session.flush()
