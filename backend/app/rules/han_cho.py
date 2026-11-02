# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Hạn chờ của cạnh tự đi (#142).
#
# Ở trạng thái chờ một người bấm — trưởng phòng xác duyệt, người gửi xác nhận — người đó
# không bấm thì hồ sơ đứng mãi, và đồng hồ SLA không giúp gì vì nó chưa chạy hay đang dừng.
# Cạnh hệ thống mang `transitions.auto_after_hours` tự đi khi hồ sơ nằm ở trạng thái nguồn
# đủ chừng ấy giờ làm việc (#199); `warn_before_hours` để màn hình báo trước. Trạng thái
# nào có hạn chờ, hạn bao lâu, đi về đâu — đều là dữ liệu.
#
# Tách khỏi app/rules/sla.py vì là một đồng hồ khác: SLA đo thời gian phòng ban xử lý, cộng
# dồn qua nhiều đoạn; hạn chờ đo thời gian nằm ở MỘT trạng thái, đặt lại mỗi lần vào.

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import BigInteger, and_, cast, func, select
from sqlalchemy.orm import Session

from app.models.case import EventLog, Request
from app.models.workflow_config import Transition


def luc_vao_trang_thai():
    """Lúc hồ sơ vào trạng thái hiện tại, dạng biểu thức SQL gắn với `Request`.

    Lấy lần chuyển gần nhất ĐỔI trạng thái sang trạng thái hiện tại: cạnh tự trỏ — nhận
    việc, sửa nội dung — không đổi chỗ hồ sơ đang đứng, nên không đặt lại hạn chờ. Chưa
    có lần chuyển nào thì hồ sơ đứng ở trạng thái đầu từ lúc tạo.
    """
    return func.coalesce(
        select(func.max(EventLog.timestamp))
        .where(
            EventLog.case_id == Request.id,
            EventLog.to_state == Request.current_state,
            EventLog.from_state != EventLog.to_state,
        )
        .scalar_subquery(),
        Request.created_at,
    )


@dataclass(frozen=True)
class TuDong:
    """Cạnh sẽ tự đi từ trạng thái hiện tại của một hồ sơ, và đi lúc nào."""

    canh: Transition
    luc: dt.datetime
    bao_truoc: bool


def tu_dong(session: Session, case: Request, luc: dt.datetime | None = None) -> TuDong | None:
    """Hồ sơ này có cạnh tự đi không, tự đi lúc nào, đã tới lúc báo trước chưa.

    `luc` là thời điểm xét, mặc định bây giờ — bài kiểm thử truyền một mốc tương lai thay
    cho việc lùi nhật ký, vốn chỉ ghi thêm.
    """
    canh = session.scalars(
        select(Transition).where(
            Transition.rule_set_id == case.rule_set_id,
            Transition.from_state == case.current_state,
            Transition.auto_after_hours.is_not(None),
        )
    ).one_or_none()
    if canh is None:
        return None

    vao = session.scalar(select(luc_vao_trang_thai()).where(Request.id == case.id))
    het = session.scalar(
        select(func.moc_sau_giay_lam_viec(vao, canh.auto_after_hours * 3600))
    )
    bao_truoc = False
    if canh.warn_before_hours is not None:
        da_o = session.scalar(
            select(func.so_giay_lam_viec(vao, luc if luc is not None else func.now()))
        )
        bao_truoc = da_toi_luc_bao(canh, da_o)
    return TuDong(canh=canh, luc=het, bao_truoc=bao_truoc)


def da_toi_luc_bao(canh: Transition, da_o_giay: int) -> bool:
    """Hồ sơ đã nằm ở trạng thái `da_o_giay` giây làm việc: đã vào khoảng báo trước khi cạnh tự
    đi chưa. Cạnh không khai báo trước thì không bao giờ báo."""
    if canh.warn_before_hours is None:
        return False
    return da_o_giay >= (canh.auto_after_hours - canh.warn_before_hours) * 3600


def canh_tu_di_theo_trang_thai(session: Session, rule_set_id: int) -> dict[str, Transition]:
    """Cạnh tự đi của từng trạng thái nguồn trong một bộ quy tắc (#232).

    Hàng đợi xét báo trước cho mọi hồ sơ của nó; tra cạnh một lần cho cả hàng đợi thay vì mỗi
    hồ sơ một lần như `tu_dong`. Mỗi trạng thái tối đa một cạnh tự đi, như `tu_dong` giả định.
    """
    return {
        canh.from_state: canh
        for canh in session.scalars(
            select(Transition).where(
                Transition.rule_set_id == rule_set_id,
                Transition.auto_after_hours.is_not(None),
            )
        )
    }


def giay_da_o_trang_thai():
    """Giây làm việc hồ sơ đã nằm ở trạng thái hiện tại tới bây giờ, dạng biểu thức SQL gắn với
    `Request` — để hàng đợi tính cho mọi hồ sơ trong cùng một truy vấn (#232)."""
    return func.so_giay_lam_viec(luc_vao_trang_thai(), func.now())


def ho_so_het_han_cho(
    session: Session, luc: dt.datetime | None = None
) -> list[tuple[Request, Transition]]:
    """Những hồ sơ đã nằm ở trạng thái hiện tại đủ hạn chờ, kèm cạnh tự đi của nó."""
    moc = luc if luc is not None else func.now()
    truy_van = (
        select(Request, Transition)
        .join(
            Transition,
            and_(
                Transition.rule_set_id == Request.rule_set_id,
                Transition.from_state == Request.current_state,
                Transition.auto_after_hours.is_not(None),
            ),
        )
        .where(
            # Ép kiểu trước khi nhân: cột là SMALLINT, nhân 3600 trong kiểu đó thì tràn
            func.so_giay_lam_viec(luc_vao_trang_thai(), moc)
            >= cast(Transition.auto_after_hours, BigInteger) * 3600
        )
        .order_by(Request.id)
    )
    return [(ho_so, canh) for ho_so, canh in session.execute(truy_van).all()]
