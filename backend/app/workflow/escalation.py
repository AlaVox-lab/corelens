# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Bộ quét hồ sơ quá hạn và tự leo thang.
#
# Điểm quan trọng nhất của tệp này: **leo thang cũng đi qua điểm chuyển trạng thái
# duy nhất**, không đi tắt. Nếu bộ quét tự đặt `current_state = "escalated"` cho
# nhanh thì nhật ký sự kiện sẽ thiếu đúng những bản ghi thú vị nhất — các lần trễ
# hạn — và khai phá quy trình mất khả năng chỉ ra điểm nghẽn.
#
# Tệp nằm ở `workflow/` chứ không ở `rules/` vì nó ĐIỀU KHIỂN việc chuyển trạng thái.
# Phần kế toán thời gian thuần túy nằm ở `app/rules/sla.py` và `app/rules/han_cho.py`.
#
# Hai bộ quét, hai loại cạnh hệ thống: leo thang khi quá hạn SLA (cạnh không có hạn chờ),
# và tự đi khi hồ sơ nằm im quá hạn chờ (cạnh mang `auto_after_hours`, #142).

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workflow_config import Transition
from app.rules.han_cho import ho_so_het_han_cho
from app.rules.sla import ho_so_qua_han
from app.thong_bao.hang_doi import TRIGGER_DA_TU_DI, xep_hang
from app.workflow.context import Actor
from app.workflow.engine import perform_transition
from app.workflow.errors import TransitionError

logger = logging.getLogger(__name__)

# Tên tác nhân ghi vào cột `actor` của nhật ký sự kiện khi hệ thống tự đi.
# Khai phá quy trình dựa vào đây để tách nhánh tự động khỏi nhánh do người làm.
TAC_NHAN_SLA = "sla-watcher"
# Tác nhân của cạnh tự đi khi hết hạn chờ (#142) — tách tên để nhật ký phân biệt hai lý do.
TAC_NHAN_HAN_CHO = "wait-watcher"


def quet_va_leo_thang(session: Session) -> list[int]:
    """Quét hồ sơ quá hạn rồi đẩy từng cái qua cạnh hệ thống tương ứng.

    Trả về danh sách định danh hồ sơ đã leo thang.

    Trạng thái đích **không viết cứng**: hàm tra bảng `transitions` tìm cạnh hệ thống
    xuất phát từ trạng thái hiện tại của hồ sơ. Đổi tên trạng thái leo thang, hay thêm
    một nhánh tự động khác, chỉ là sửa dữ liệu khởi tạo.

    Hàm **không tự commit** — phía gọi quyết định ranh giới giao dịch, giống
    `perform_transition`.
    """
    he_thong = Actor.system(TAC_NHAN_SLA)
    da_leo_thang: list[int] = []

    for ho_so in ho_so_qua_han(session):
        canh = session.scalars(
            select(Transition).where(
                Transition.rule_set_id == ho_so.rule_set_id,
                Transition.from_state == ho_so.current_state,
                Transition.is_system,
                Transition.auto_after_hours.is_(None),
            )
        ).first()

        if canh is None:
            # Không nên xảy ra: truy vấn lọc quá hạn đã đòi điều kiện này. Giữ lại
            # để một thay đổi dữ liệu giữa hai truy vấn không làm sập bộ quét.
            continue

        try:
            perform_transition(
                session,
                case_id=ho_so.id,
                to_state=canh.to_state,
                actor=he_thong,
            )
        except TransitionError as loi:
            # Một hồ sơ hỏng không được làm dừng cả lượt quét. Ghi lại rồi đi tiếp.
            logger.warning(
                "Không leo thang được hồ sơ %s: %s", ho_so.id, loi.message
            )
            continue

        da_leo_thang.append(ho_so.id)

    if da_leo_thang:
        logger.info("Đã leo thang %d hồ sơ quá hạn", len(da_leo_thang))

    return da_leo_thang


def quet_het_han_cho(session: Session, luc: dt.datetime | None = None) -> list[int]:
    """Đẩy những hồ sơ nằm im quá hạn chờ qua cạnh tự đi của trạng thái đó (#142).

    Trả về danh sách định danh hồ sơ đã đi. Cạnh, hạn chờ, trạng thái đích đều tra từ
    `transitions` — bộ quét không biết "Chờ phòng ban xác duyệt" là gì. `luc` là thời điểm
    xét, mặc định bây giờ.

    Hàm **không tự commit**, giống `quet_va_leo_thang`.
    """
    he_thong = Actor.system(TAC_NHAN_HAN_CHO)
    da_di: list[int] = []

    for ho_so, canh in ho_so_het_han_cho(session, luc):
        try:
            perform_transition(
                session,
                case_id=ho_so.id,
                to_state=canh.to_state,
                actor=he_thong,
                note=f"Hết hạn chờ {canh.auto_after_hours} giờ làm việc mà chưa ai thao tác",
            )
        except TransitionError as loi:
            logger.warning("Không tự đi được hồ sơ %s: %s", ho_so.id, loi.message)
            continue
        # Thông báo "hồ sơ đã tự chuyển" (#251): cùng giao dịch của lượt quét, không gọi mạng
        xep_hang(
            session,
            TRIGGER_DA_TU_DI,
            ho_so,
            context={"from_state": canh.from_state, "transition_id": canh.id},
        )
        da_di.append(ho_so.id)

    if da_di:
        logger.info("Đã tự đi %d hồ sơ hết hạn chờ", len(da_di))

    return da_di


@dataclass(frozen=True, slots=True)
class BoQuet:
    """Một bộ quét nền: tên ổn định (khóa tư vấn và dòng nhịp lấy theo tên), nhãn cho màn Hệ thống,
    và hàm quét nhận một phiên."""

    ten: str
    nhan: str
    ham: Callable[[Session], list[int]]


# Mọi bộ quét của vòng nền, theo thứ tự chạy. Mỗi bộ có khóa và dòng nhịp riêng (#253), nên một
# bộ hỏng không che nhịp của bộ kia. Tên là định danh vận hành, không phải dữ liệu nghiệp vụ.
TEN_BO_QUET_SLA = "sla-escalation"
TEN_BO_QUET_HAN_CHO = "wait-expiry"

BO_QUET: tuple[BoQuet, ...] = (
    BoQuet(TEN_BO_QUET_SLA, "Bộ quét quá hạn SLA", quet_va_leo_thang),
    BoQuet(TEN_BO_QUET_HAN_CHO, "Bộ quét hạn chờ", quet_het_han_cho),
)
