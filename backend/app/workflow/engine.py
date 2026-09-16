# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# ĐIỂM CHUYỂN TRẠNG THÁI DUY NHẤT.
#
# Mọi lần đổi trạng thái hồ sơ trong toàn hệ thống đi qua đúng hàm
# `perform_transition` dưới đây. Không tồn tại đường nào khác.
#
# Vì sao chặt tới mức đó: nhật ký sự kiện chỉ có giá trị nếu KHÔNG BAO GIỜ thiếu bản
# ghi. Một nhật ký thủng làm sai lệch kết quả khai phá quy trình, và khi đó điểm sáng
# tạo của đề tài mất giá trị. Xem ARCHITECTURE.md mục 6.1 và ADR-0004.
#
# Gán thẳng vào `request.current_state` ở bất kỳ chỗ nào khác là vi phạm khuôn mẫu,
# kể cả khi nó "chỉ sửa một trường".

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.log import record_event
from app.models.case import EventLog, Request
from app.models.workflow_config import RuleSet, State, Transition
from app.rules.guards import run_guards
from app.workflow.context import Actor, TransitionContext
from app.workflow.errors import (
    CaseNotFound,
    NoteRequired,
    RoleNotPermitted,
    SystemTransitionOnly,
    TransitionNotAllowed,
)

# Những trường quyết định mà một lần chuyển trạng thái được phép đặt.
#
# `current_state` cố ý KHÔNG có mặt: nó do engine tự đặt sau khi đã ghi nhật ký. Các
# trường `suggested_*` cũng không: tầng I ghi vào chúng theo đường riêng, và nguyên
# tắc bất di dịch là AI không bao giờ chạm vào trường quyết định — CLAUDE.md mục 4.3.
CHANGEABLE_FIELDS = frozenset(
    {
        "request_type_code",
        "department_code",
        "priority_code",
        "assignee_id",
    }
)


def get_active_rule_set(session: Session) -> RuleSet:
    """Bộ quy tắc đang kích hoạt. Hồ sơ mới luôn nhận bộ này."""
    bo = session.scalars(select(RuleSet).where(RuleSet.is_active)).one()
    return bo


def create_case(
    session: Session,
    *,
    title: str,
    requester_id: str,
    description: str | None = None,
) -> Request:
    """Tạo một hồ sơ mới ở trạng thái bắt đầu của bộ quy tắc đang kích hoạt.

    Trạng thái bắt đầu **tra từ bảng** qua cờ `is_initial`, không viết cứng tên trạng
    thái nào vào mã nguồn. Đổi điểm vào của luồng chỉ là sửa dữ liệu khởi tạo.

    **Việc tạo hồ sơ không sinh bản ghi nhật ký**, vì nó không phải một lần *chuyển*
    trạng thái — không có trạng thái nào trước nó. Mốc bắt đầu của hồ sơ là cột
    `created_at`. Khi xuất dữ liệu cho khai phá quy trình, tầng `D` dựng thêm một sự
    kiện mở đầu từ cột đó nếu công cụ phân tích cần.
    """
    bo_quy_tac = get_active_rule_set(session)

    trang_thai_dau = session.scalars(
        select(State).where(
            State.rule_set_id == bo_quy_tac.id,
            State.is_initial,
        )
    ).one()

    ho_so = Request(
        rule_set_id=bo_quy_tac.id,
        current_state=trang_thai_dau.code,
        title=title,
        description=description,
        requester_id=requester_id,
    )
    session.add(ho_so)
    session.flush()
    return ho_so


def allowed_transitions(
    session: Session, case: Request, actor: Actor
) -> list[Transition]:
    """Những cạnh mà tác nhân này đi được từ trạng thái hiện tại của hồ sơ.

    Dùng để dựng danh sách nút bấm trên giao diện ở #44 và #45. Giao diện chỉ hiển
    thị thứ đi được là nửa đầu của Poka-yoke; nửa sau là engine vẫn kiểm lại khi
    yêu cầu thật gửi lên. Chặn ở giao diện thôi thì không đủ.

    Lưu ý: hàm này **không chạy ràng buộc Poka-yoke** vì chúng cần biết người dùng
    định đặt giá trị gì. Một cạnh hiện ra ở đây vẫn có thể bị từ chối lúc thực hiện.
    """
    cac_canh = session.scalars(
        select(Transition)
        .where(
            Transition.rule_set_id == case.rule_set_id,
            Transition.from_state == case.current_state,
        )
        .order_by(Transition.display_order)
    ).all()

    return [c for c in cac_canh if _actor_can_traverse(actor, c)]


def perform_transition(
    session: Session,
    *,
    case_id: int,
    to_state: str,
    actor: Actor,
    note: str | None = None,
    changes: dict | None = None,
) -> Request:
    """Đổi trạng thái một hồ sơ. Đây là cánh cửa duy nhất.

    Năm bước, đúng thứ tự quy định ở ARCHITECTURE.md mục 6.1:

    1. Tra bảng quy tắc — cạnh không có trong bảng thì không đi được
    2. Kiểm quyền theo vai trò
    3. Chạy ràng buộc Poka-yoke
    4. Ghi nhật ký sự kiện
    5. Cập nhật hồ sơ

    Toàn bộ nằm trong giao dịch của phiên đang mở, nên hoặc nhật ký và trạng thái
    cùng thay đổi, hoặc cả hai cùng không. Không có khe nào để nhật ký thủng.

    Hàm **không tự commit**: phía gọi quyết định ranh giới giao dịch. Nhờ vậy một
    yêu cầu HTTP gói được nhiều thao tác, và bộ kiểm thử hoàn tác sạch sau mỗi bài.
    """
    # Khóa dòng hồ sơ tới cuối giao dịch. Không có bước này, hai yêu cầu đồng thời
    # cùng đọc trạng thái cũ rồi cùng ghi nhật ký — sinh ra hai bản ghi cho một lần
    # chuyển, hoặc tệ hơn là hai lần chuyển từ cùng một trạng thái nguồn.
    ho_so = session.get(Request, case_id, with_for_update=True)
    if ho_so is None:
        raise CaseNotFound(f"Không tìm thấy hồ sơ mang định danh {case_id}.")

    # --- Bước 1: tra bảng quy tắc -----------------------------------------
    canh = session.scalars(
        select(Transition).where(
            Transition.rule_set_id == ho_so.rule_set_id,
            Transition.from_state == ho_so.current_state,
            Transition.to_state == to_state,
        )
    ).one_or_none()

    if canh is None:
        raise TransitionNotAllowed(
            f"Không có đường đi từ '{ho_so.current_state}' sang '{to_state}' "
            f"trong bộ quy tắc đang áp dụng."
        )

    # --- Bước 2: kiểm quyền ------------------------------------------------
    if canh.is_system and not actor.is_system:
        raise SystemTransitionOnly(
            f"Cạnh '{canh.activity_label}' do hệ thống tự đi, người dùng không "
            f"kích hoạt được."
        )
    if not canh.is_system and actor.is_system:
        raise RoleNotPermitted(
            f"Tác nhân hệ thống không đi được cạnh '{canh.activity_label}' — "
            f"cạnh này thuộc về con người."
        )
    if not canh.is_system and not (actor.roles & canh.role_codes):
        raise RoleNotPermitted(
            f"Vai trò hiện tại không thực hiện được '{canh.activity_label}'. "
            f"Cạnh này dành cho: {', '.join(sorted(canh.role_codes)) or 'không ai'}."
        )

    if canh.requires_note and not (note and note.strip()):
        raise NoteRequired(
            f"Thao tác '{canh.activity_label}' bắt buộc ghi lý do."
        )

    thay_doi = dict(changes or {})
    la_truong = set(thay_doi) - CHANGEABLE_FIELDS
    if la_truong:
        raise TransitionNotAllowed(
            f"Lần chuyển trạng thái không được đặt các trường: "
            f"{', '.join(sorted(la_truong))}."
        )

    ctx = TransitionContext(
        case=ho_so, transition=canh, actor=actor, note=note, changes=thay_doi
    )

    # --- Bước 3: ràng buộc Poka-yoke ---------------------------------------
    run_guards(ctx)

    # --- Bước 4: ghi nhật ký TRƯỚC -----------------------------------------
    record_event(session, ctx)

    # --- Bước 5: rồi mới cập nhật hồ sơ ------------------------------------
    for truong, gia_tri in thay_doi.items():
        setattr(ho_so, truong, gia_tri)
    ho_so.current_state = canh.to_state

    session.flush()
    return ho_so


def case_history(session: Session, case_id: int) -> list[EventLog]:
    """Toàn bộ nhật ký của một hồ sơ, theo đúng thứ tự thời gian."""
    return list(
        session.scalars(
            select(EventLog)
            .where(EventLog.case_id == case_id)
            .order_by(EventLog.timestamp, EventLog.id)
        ).all()
    )


def _actor_can_traverse(actor: Actor, transition: Transition) -> bool:
    """Kiểm quyền thuần túy, chưa xét ràng buộc Poka-yoke."""
    if transition.is_system:
        return actor.is_system
    if actor.is_system:
        return False
    return bool(actor.roles & transition.role_codes)
