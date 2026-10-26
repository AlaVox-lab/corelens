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
#
# Mọi khoảng thời gian ở đây là GIỜ LÀM VIỆC theo lịch mặc định (#199): `sla_hours` 8 là
# 8 giờ làm việc, đêm và cuối tuần không trôi. Không hàm nào tự trừ hai mốc thời gian —
# phép đo đi qua hàm `so_giay_lam_viec` của PostgreSQL (lược đồ khởi tạo, mục 10), để
# Python và truy vấn tìm hồ sơ quá hạn đo cùng một cách.
#
# Mở lại (#102) là chu kỳ xử lý mới: cạnh mang cờ `transitions.restarts_sla` đưa số giây đã chạy
# về 0, và ràng buộc `reopen-limit` đưa gia hạn về 0 — hạn mới, không kế thừa hạn đã hết.
#
# Hạn của một hồ sơ (#101) = hạn chuẩn của loại yêu cầu × hệ số của mức ưu tiên, cộng tổng
# số giờ đã gia hạn. Ân hạn nhân cùng hệ số, không cộng phần gia hạn. Ba con số đều là dữ
# liệu: `request_types.sla_hours`, `priorities.sla_factor_percent`,
# `requests.sla_extension_total_hours`.

from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, cast, func, select
from sqlalchemy.orm import Session

from app.models.case import Request
from app.models.workflow_config import Priority, RequestType, State, Transition


def _trang_thai(session: Session, rule_set_id: int, ma: str) -> State:
    return session.get_one(State, (rule_set_id, ma))


def bay_gio(session: Session) -> dt.datetime:
    """Thời điểm hiện tại theo đồng hồ của PostgreSQL.

    Cố ý không dùng đồng hồ của tiến trình Python: cụm có thể chạy nhiều bản sao dịch
    vụ, và vài giây lệch giữa chúng đủ làm số liệu SLA mâu thuẫn với nhật ký sự kiện —
    vốn cũng lấy mốc thời gian từ PostgreSQL.
    """
    return session.scalar(select(func.now()))


def giay_lam_viec(session: Session, tu: dt.datetime, den: dt.datetime | None = None) -> int:
    """Số giây làm việc giữa hai mốc theo lịch mặc định. Bỏ `den` là tới bây giờ."""
    moc_den = func.now() if den is None else den
    return int(session.scalar(select(func.so_giay_lam_viec(tu, moc_den))))


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
        giay = giay_lam_viec(session, case.sla_segment_since, hien_tai)
        if tu.sla_running:
            case.sla_running_seconds += giay
        else:
            case.sla_paused_seconds += giay

    # Chu kỳ xử lý mới (#102): mở lại thì hạn đếm lại từ 0, không kế thừa hạn đã hết của chu kỳ
    # cũ. Chốt đoạn vừa qua xong mới xóa, để phần chạy dở không rơi vào chu kỳ mới. Thời gian
    # dừng (chờ bổ sung) giữ nguyên — nó không thuộc hạn.
    if transition.restarts_sla:
        case.sla_running_seconds = 0

    da_khoi_dong = case.sla_segment_since is not None or den.sla_running

    if den.is_terminal or not da_khoi_dong:
        # Hồ sơ đóng thì đồng hồ dừng hẳn; chưa khởi động thì chưa tính gì
        case.sla_segment_since = None
    else:
        case.sla_segment_since = hien_tai


def he_so_uu_tien(session: Session, case: Request) -> int:
    """Phần trăm hạn chuẩn áp cho hồ sơ theo mức ưu tiên (#101). Chưa có mức thì 100."""
    if case.priority_code is None:
        return 100
    muc = session.get(Priority, case.priority_code)
    return 100 if muc is None else muc.sla_factor_percent


def han_goc_giay(session: Session, case: Request) -> int | None:
    """Hạn gốc của hồ sơ, tính bằng giây: hạn chuẩn của loại nhân hệ số ưu tiên (#101).

    Chưa cộng phần gia hạn — đây là con số mà mỗi lần gia hạn được tính phần trăm trên.
    `None` khi chưa phân loại xong. Chia nguyên giống truy vấn ở `ho_so_qua_han`, để Python
    và SQL không lệch nhau một giây nào.
    """
    if case.request_type_code is None:
        return None
    loai = session.get(RequestType, case.request_type_code)
    if loai is None:
        return None
    return loai.sla_hours * 3600 * he_so_uu_tien(session, case) // 100


def gioi_han_giay(session: Session, case: Request) -> int | None:
    """Ngưỡng SLA của hồ sơ, tính bằng giây: hạn gốc cộng tổng giờ đã gia hạn (#101).

    `None` khi chưa phân loại xong.
    """
    goc = han_goc_giay(session, case)
    return None if goc is None else goc + case.sla_extension_total_hours * 3600


def an_han_giay(session: Session, case: Request) -> int:
    """Ân hạn của hồ sơ (#94), nhân cùng hệ số ưu tiên với hạn (#101)."""
    loai = session.get(RequestType, case.request_type_code)
    return loai.sla_grace_hours * 3600 * he_so_uu_tien(session, case) // 100


def da_chay_giay(session: Session, case: Request) -> int:
    """Tổng thời gian đồng hồ đã chạy, gồm cả đoạn đang mở."""
    tong = case.sla_running_seconds
    if case.sla_segment_since is not None:
        trang_thai = _trang_thai(session, case.rule_set_id, case.current_state)
        if trang_thai.sla_running:
            tong += giay_lam_viec(session, case.sla_segment_since)
    return tong


def sap_het_han(session: Session, case: Request) -> bool:
    """Hồ sơ đã dùng tới ngưỡng "sắp hết hạn" của loại yêu cầu mà chưa quá hạn chưa (#175).

    Ngưỡng là phần trăm cam kết (`request_types.sla_warn_percent`), tính trên hạn của chính
    hồ sơ nên tự co giãn khi hạn đổi. Đúng mốc ngưỡng là đã sắp hạn; đúng mốc hạn vẫn là
    sắp hạn, vì quá hạn là vượt hẳn — cùng phép so với cờ `sla_overdue`. So bằng số nguyên
    để không lệch vì làm tròn.
    """
    gioi_han = gioi_han_giay(session, case)
    if gioi_han is None:
        return False
    loai = session.get(RequestType, case.request_type_code)
    da_chay = da_chay_giay(session, case)
    return da_chay * 100 >= gioi_han * loai.sla_warn_percent and da_chay <= gioi_han


def han_chot(session: Session, case: Request) -> dt.datetime | None:
    """Mốc hết hạn xử lý, để giao diện ghi "hạn 15:00 thứ Hai" thay vì chỉ đếm giờ (#199).

    Chỉ có khi đồng hồ đang chạy và hạn chưa qua trong một đoạn trước: hạn là mốc sau
    phần cam kết còn lại, đếm bằng giờ làm việc từ đầu đoạn đang mở. Đồng hồ đang dừng thì
    chưa biết hạn rơi vào lúc nào — phụ thuộc lúc nó chạy lại — nên trả `None`.
    """
    gioi_han = gioi_han_giay(session, case)
    if gioi_han is None or case.sla_segment_since is None:
        return None
    if not _trang_thai(session, case.rule_set_id, case.current_state).sla_running:
        return None
    con = gioi_han - case.sla_running_seconds
    if con <= 0:
        return None
    return session.scalar(select(func.moc_sau_giay_lam_viec(case.sla_segment_since, con)))


def an_han_con_lai_giay(session: Session, case: Request) -> int | None:
    """Còn bao nhiêu giây ân hạn trước khi bộ quét được leo thang hồ sơ này (#94).

    `None` khi ân hạn không áp: hồ sơ chưa quá hạn, không ở trạng thái đếm giờ, hoặc
    đã hết ân hạn. Chỉ để giao diện nói cho trưởng phòng biết vì sao hồ sơ quá hạn mà
    chưa bị leo thang — phép kiểm thật nằm trong `ho_so_qua_han`.
    """
    gioi_han = gioi_han_giay(session, case)
    if gioi_han is None or case.sla_segment_since is None:
        return None
    if not _trang_thai(session, case.rule_set_id, case.current_state).sla_running:
        return None
    if da_chay_giay(session, case) <= gioi_han:
        return None
    da_o = giay_lam_viec(session, case.sla_segment_since)
    con = an_han_giay(session, case) - da_o
    return con if con > 0 else None


def ho_so_qua_han(session: Session) -> list[Request]:
    """Những hồ sơ đã vượt ngưỡng SLA, còn đường leo thang, và hết ân hạn.

    Năm điều kiện, tất cả đều tra từ dữ liệu:

    1. Đang ở trạng thái có `sla_running` — hồ sơ đang tạm dừng thì không quá hạn được
    2. Đã phân loại, nên biết ngưỡng áp cho nó
    3. Tổng thời gian chạy vượt ngưỡng
    4. Từ trạng thái hiện tại có một cạnh hệ thống để đi
    5. Đã ở trạng thái hiện tại lâu hơn ân hạn của loại yêu cầu (#94)

    Điều kiện thứ tư khiến hồ sơ ĐANG ở `escalated` không bị nhặt lại mỗi vòng, vì từ
    đó không có cạnh hệ thống nào. Nhưng nó không đủ: trưởng phòng phân công lại thì
    hồ sơ về `in-progress`, đồng hồ tổng vẫn quá hạn, và thiếu điều kiện thứ năm thì
    lượt quét kế tiếp leo thang lại ngay — người mới không có một phút nào để làm. Mở
    lại một hồ sơ đã quá hạn, hay bổ sung thông tin xong, cũng rơi vào đúng chỗ đó.

    Ân hạn đo từ `sla_segment_since` — mốc này mở lại ở MỖI lần chuyển trạng thái, nên
    nó chính là lúc hồ sơ vào trạng thái hiện tại. Đồng hồ tổng không đặt lại: hồ sơ
    vẫn được ghi nhận là quá hạn, và số liệu thời gian xử lý giữ đúng cho tầng `I`.
    Hết ân hạn mà vẫn chưa xong thì leo thang lại — đó là tín hiệu đúng.
    """
    # Giờ làm việc của đoạn đang mở, cùng phép đo với `da_chay_giay`
    dang_mo = func.so_giay_lam_viec(Request.sla_segment_since, func.now())

    # Cùng phép tính với `gioi_han_giay` và `an_han_giay` (#101). Ép BIGINT trước khi nhân:
    # cột SMALLINT/INTEGER nhân 3600 rồi nhân hệ số có thể tràn kiểu gốc.
    he_so = cast(func.coalesce(Priority.sla_factor_percent, 100), BigInteger)
    gioi_han = (
        cast(RequestType.sla_hours, BigInteger) * 3600 * he_so // 100
        + cast(Request.sla_extension_total_hours, BigInteger) * 3600
    )
    an_han = cast(RequestType.sla_grace_hours, BigInteger) * 3600 * he_so // 100

    dang_chay = (
        select(Transition.id)
        .where(
            Transition.rule_set_id == Request.rule_set_id,
            Transition.from_state == Request.current_state,
            Transition.is_system,
            Transition.auto_after_hours.is_(None),
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
        .outerjoin(Priority, Priority.code == Request.priority_code)
        .where(
            State.sla_running,
            Request.sla_segment_since.is_not(None),
            Request.sla_running_seconds + dang_mo > gioi_han,
            dang_mo >= an_han,
            dang_chay,
        )
        .order_by(Request.id)
    )

    return list(session.scalars(truy_van).all())
