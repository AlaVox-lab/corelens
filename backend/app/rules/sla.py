# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Đồng hồ SLA.
#
# ADR-0004 ghi rõ: chọn tự viết engine đồng nghĩa nhận trách nhiệm tự làm bộ đếm thời
# gian, thứ mà một nền tảng workflow có sẵn sẽ cho không. Đây là món nợ đó.
#
# Ba cột trên bảng `requests` thay cho một cột hạn chót tính sẵn. Lý do: đồng hồ dừng
# rồi chạy lại nhiều lần trong đời một hồ sơ, nên một mốc hạn chót cố định sẽ sai ngay
# lần đầu người dùng bị hỏi thêm thông tin.
#
# Trạng thái nào làm đồng hồ chạy do cột `states.sla_running` quyết định, không phải
# do mã nguồn. Muốn tính cả thời gian chờ bổ sung vào SLA thì bật cờ đó cho
# `awaiting-info` trong infra/seed/ — sửa dữ liệu, không sửa mã.

from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.case import Request
from app.models.workflow_config import RequestType, State, Transition


def _trang_thai(session: Session, rule_set_id: int, ma: str) -> State:
    return session.get_one(State, (rule_set_id, ma))


def bay_gio(session: Session) -> dt.datetime:
    """Thời điểm hiện tại theo đồng hồ của PostgreSQL.

    Cố ý không dùng đồng hồ của tiến trình Python: cụm có thể chạy nhiều bản sao dịch
    vụ, và vài giây lệch giữa chúng đủ làm số liệu SLA mâu thuẫn với nhật ký sự kiện —
    vốn cũng lấy mốc thời gian từ PostgreSQL.
    """
    return session.scalar(select(func.now()))


def cap_nhat_dong_ho(session: Session, case: Request, transition: Transition) -> None:
    """Chốt đoạn đang tính rồi mở đoạn mới, theo đúng một lần chuyển trạng thái.

    Gọi từ bước 5 của `perform_transition`, TRƯỚC khi `current_state` được đổi — hàm
    này cần biết hồ sơ đang rời khỏi trạng thái nào.

    Đồng hồ chỉ khởi động lần đầu khi hồ sơ bước vào một trạng thái có `sla_running`.
    Thời gian trước đó không tính vào đâu cả: quãng chờ phân loại và chờ phòng ban
    nhận việc không phải lỗi của người xử lý.
    """
    hien_tai = bay_gio(session)

    tu = _trang_thai(session, case.rule_set_id, transition.from_state)
    den = _trang_thai(session, case.rule_set_id, transition.to_state)

    # Chốt đoạn vừa qua, cộng vào đúng ngăn
    if case.sla_segment_since is not None:
        giay = int((hien_tai - case.sla_segment_since).total_seconds())
        if tu.sla_running:
            case.sla_running_seconds += giay
        else:
            case.sla_paused_seconds += giay

    da_khoi_dong = case.sla_segment_since is not None or den.sla_running

    if den.is_terminal or not da_khoi_dong:
        # Hồ sơ đóng thì đồng hồ dừng hẳn; chưa khởi động thì chưa tính gì
        case.sla_segment_since = None
    else:
        case.sla_segment_since = hien_tai


def gioi_han_giay(session: Session, case: Request) -> int | None:
    """Ngưỡng SLA của hồ sơ, tính bằng giây. `None` khi chưa phân loại xong."""
    if case.request_type_code is None:
        return None
    loai = session.get(RequestType, case.request_type_code)
    return None if loai is None else loai.sla_hours * 3600


def da_chay_giay(session: Session, case: Request) -> int:
    """Tổng thời gian đồng hồ đã chạy, gồm cả đoạn đang mở."""
    tong = case.sla_running_seconds
    if case.sla_segment_since is not None:
        trang_thai = _trang_thai(session, case.rule_set_id, case.current_state)
        if trang_thai.sla_running:
            tong += int((bay_gio(session) - case.sla_segment_since).total_seconds())
    return tong


def ho_so_qua_han(session: Session) -> list[Request]:
    """Những hồ sơ đã vượt ngưỡng SLA và còn đường leo thang để đi.

    Bốn điều kiện, tất cả đều tra từ dữ liệu:

    1. Đang ở trạng thái có `sla_running` — hồ sơ đang tạm dừng thì không quá hạn được
    2. Đã phân loại, nên biết ngưỡng áp cho nó
    3. Tổng thời gian chạy vượt ngưỡng
    4. Từ trạng thái hiện tại có một cạnh hệ thống để đi

    Điều kiện thứ tư quan trọng: nhờ nó mà hồ sơ đã leo thang rồi không bị bộ quét
    nhặt lại mỗi vòng, vì từ `escalated` không có cạnh hệ thống nào nữa. Cơ chế tự
    giới hạn bằng dữ liệu, không cần cột "đã leo thang chưa".
    """
    dang_chay = (
        select(Transition.id)
        .where(
            Transition.rule_set_id == Request.rule_set_id,
            Transition.from_state == Request.current_state,
            Transition.is_system,
        )
        .exists()
    )

    truy_van = (
        select(Request)
        .join(
            State,
            (State.rule_set_id == Request.rule_set_id)
            & (State.code == Request.current_state),
        )
        .join(RequestType, RequestType.code == Request.request_type_code)
        .where(
            State.sla_running,
            Request.sla_segment_since.is_not(None),
            Request.sla_running_seconds
            + func.extract("epoch", func.now() - Request.sla_segment_since)
            > RequestType.sla_hours * 3600,
            dang_chay,
        )
        .order_by(Request.id)
    )

    return list(session.scalars(truy_van).all())
