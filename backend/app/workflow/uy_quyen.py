# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ủy quyền khi vắng mặt (#252) — phần gắn vào định danh.
#
# Quyết định (navigator chốt 13/11/2026 theo đề xuất nhóm, giảng viên đồng ý làm trước thi):
#
#   1. Chỉ ủy quyền cho người CÙNG PHÒNG; người được ủy quyền mang vai của người vắng, chỉ trong phòng đó
#   2. Người vắng tự khai, hoặc người giao việc của phòng (trưởng phòng) khai thay cho người xử lý
#   3. Người được ủy quyền không phải xác nhận; trang chủ của họ hiện dải báo đang làm thay
#   4. Không chuyển tiếp: chỉ vai RIÊNG của người vắng được ủy quyền (`Actor.vai_goc`, hay vai trong
#      danh bạ khi trưởng phòng khai thay) — vai có được nhờ ủy quyền không bao giờ đi tiếp
#
# Cách gắn: mỗi yêu cầu, `current_actor` gọi `ap_uy_quyen` — ủy quyền đang hiệu lực của người gọi
# được gộp vào `Actor.roles`. Nhờ vậy hàng đợi, nút bấm, danh sách người nhận việc, báo cáo đều thấy
# người được ủy quyền "như vai tương ứng" mà không nơi nào phải biết ủy quyền tồn tại. Hai điều gộp
# vai không nói được thì cửa chuyển trạng thái tự kiểm (app/workflow/engine.py `_lam_thay_cho`): vai
# làm thay chỉ dùng cho hồ sơ của phòng được ủy quyền, không dùng cho hồ sơ do chính mình gửi; và nhật
# ký ghi người vắng ở cột `on_behalf_of`.
#
# Hiệu lực tính bằng đồng hồ của cơ sở dữ liệu ở MỖI yêu cầu, nên hết hạn hay bị thu hồi là mất quyền
# ngay ở lần bấm kế tiếp — không có phiên nào giữ quyền cũ.

from __future__ import annotations

import dataclasses
import datetime as dt
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.quan_tri import Delegation
from app.workflow.context import Actor, LamThay


def dang_hieu_luc():
    """Điều kiện SQL: ủy quyền đang có hiệu lực ngay lúc này (đồng hồ của cơ sở dữ liệu)."""
    return (
        Delegation.revoked_at.is_(None)
        & (Delegation.starts_at <= func.now())
        & (Delegation.ends_at > func.now())
    )


def ap_uy_quyen(session: Session, actor: Actor) -> Actor:
    """Gộp các ủy quyền đang hiệu lực mà `actor` được nhận vào vai của họ.

    Chỉ nhận ủy quyền của phòng mà người đó đang thuộc trong token: chuyển phòng rồi thì ủy quyền
    của phòng cũ tự hết tác dụng. Không có ủy quyền nào thì trả nguyên `actor`.
    """
    if actor.is_system or not actor.departments:
        return actor
    cac_uy_quyen = session.scalars(
        select(Delegation)
        .where(
            Delegation.delegate_id == actor.id,
            Delegation.department_code.in_(actor.departments),
            dang_hieu_luc(),
        )
        .order_by(Delegation.ends_at)
    ).all()
    if not cac_uy_quyen:
        return actor
    lam_thay = tuple(
        LamThay(
            ma=u.id,
            nguoi_vang_id=u.delegator_id,
            nguoi_vang_label=u.delegator_label,
            phong=u.department_code,
            vai=frozenset(u.roles),
        )
        for u in cac_uy_quyen
    )
    vai_them = frozenset().union(*(u.vai for u in lam_thay))
    return dataclasses.replace(
        actor, roles=actor.roles | vai_them, lam_thay=lam_thay, vai_goc=actor.roles
    )


def mui_gio_lich(session: Session) -> ZoneInfo:
    """Múi giờ của lịch làm việc mặc định — "ngày" của ủy quyền hiểu theo múi này."""
    ten = session.execute(text("SELECT time_zone FROM work_calendars WHERE is_default")).scalar_one()
    return ZoneInfo(ten)


def khoang_cua_ngay(session: Session, tu_ngay: dt.date, den_ngay: dt.date) -> tuple[dt.datetime, dt.datetime]:
    """Ngày đầu, ngày cuối (cả hai tính) → [00:00 ngày đầu, 00:00 ngày sau ngày cuối) theo giờ địa
    phương, đổi sang UTC để lưu."""
    mui = mui_gio_lich(session)
    bat_dau = dt.datetime.combine(tu_ngay, dt.time.min, tzinfo=mui)
    ket_thuc = dt.datetime.combine(den_ngay + dt.timedelta(days=1), dt.time.min, tzinfo=mui)
    return bat_dau.astimezone(dt.timezone.utc), ket_thuc.astimezone(dt.timezone.utc)


def ngay_cua_khoang(session: Session, bat_dau: dt.datetime, ket_thuc: dt.datetime) -> tuple[dt.date, dt.date]:
    """Phép ngược của `khoang_cua_ngay`: hai mốc đã lưu → ngày đầu, ngày cuối để hiển thị."""
    mui = mui_gio_lich(session)
    return bat_dau.astimezone(mui).date(), (ket_thuc.astimezone(mui) - dt.timedelta(days=1)).date()


def hom_nay(session: Session) -> dt.date:
    """Ngày hôm nay theo múi giờ của lịch, lấy từ đồng hồ của cơ sở dữ liệu."""
    bay_gio = session.execute(select(func.now())).scalar_one()
    return bay_gio.astimezone(mui_gio_lich(session)).date()
