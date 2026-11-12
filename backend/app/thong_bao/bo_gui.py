# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Bộ quét gửi thư thông báo (#251), chạy theo khuôn app/workflow/nhip_quet.py: khóa tư vấn để nhiều
# bản dịch vụ không gửi trùng, dòng nhịp để màn Hệ thống thấy nó còn sống.
#
# Một lượt làm ba việc, theo thứ tự:
#   1. Phát hiện hồ sơ vừa vào khoảng báo trước của cạnh tự đi → xếp sự kiện `auto-warning`, khóa chống
#      trùng theo (hồ sơ, lúc vào trạng thái): mỗi lần vào trạng thái chỉ báo một lần.
#   2. Mở rộng sự kiện chưa xử lý thành từng thư: tra danh bạ tìm người nhận theo cột `recipients` của
#      loại thông báo, dựng tiêu đề và nội dung từ mẫu trong dữ liệu, ghi `notification_deliveries`.
#   3. Gửi thư đến hạn: kiểm tùy chọn của người nhận, tra địa chỉ trong danh bạ, gửi qua SMTP, ghi vết.
#      Hỏng thì thử lại sau, chờ nhân đôi mỗi lần, tối đa `notify_max_attempts` lần.
#
# Lỗi ở đây không bao giờ chạm chuyển trạng thái: chuyển trạng thái đã commit từ trước, cùng với sự
# kiện. Danh bạ hay máy chủ thư sập thì sự kiện và thư nằm chờ lượt sau.

from __future__ import annotations

import datetime as dt
import logging
import string
import time
from zoneinfo import ZoneInfo

from sqlalchemy import BigInteger, and_, cast, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth.directory import DirectoryUnavailable, KeycloakDirectory, Person, get_directory
from app.config import get_settings
from app.models.case import Request
from app.models.thong_bao import (
    NotificationDelivery,
    NotificationOutbox,
    NotificationPreference,
    NotificationType,
)
from app.models.workflow_config import State, Transition
from app.rules.han_cho import luc_vao_trang_thai
from app.thong_bao.hang_doi import TRIGGER_BAO_TRUOC, TRIGGER_VAO_TRANG_THAI, xep_hang
from app.thong_bao.thu import KetNoiThu, ThuLoi
from app.workflow.context import Actor
from app.workflow.engine import my_primary_steps
from app.workflow.routes import _ma_ho_so

logger = logging.getLogger(__name__)

TEN_BO_QUET_THU = "email-notify"
NHAN_BO_QUET_THU = "Bộ gửi thư thông báo"

DO_DAI_CAU_LOI = 300

# Danh bạ nhớ giữa các lượt — (lúc đọc, danh sách)
_DANH_BA_NHO: dict[str, tuple[float, list[Person]]] = {}


def _danh_ba(danh_ba: KeycloakDirectory | None) -> dict[str, Person]:
    ch = get_settings()
    nho = _DANH_BA_NHO.get("tat-ca")
    if nho is not None and time.monotonic() - nho[0] < ch.notify_directory_cache_seconds:
        return {p.id: p for p in nho[1]}
    nguoi = (danh_ba or get_directory()).everyone(max(ch.directory_timeout_seconds, 15.0))
    _DANH_BA_NHO["tat-ca"] = (time.monotonic(), nguoi)
    return {p.id: p for p in nguoi}


def quen_danh_ba() -> None:
    """Bỏ danh bạ đang nhớ — cho bài kiểm thử."""
    _DANH_BA_NHO.clear()


# --- 1. Mốc báo trước ------------------------------------------------------


def phat_hien_bao_truoc(session: Session, luc: dt.datetime | None = None) -> int:
    """Xếp sự kiện cho hồ sơ đang ở khoảng báo trước mà chưa được báo lần nào ở lần vào này."""
    moc = luc if luc is not None else func.now()
    vao = luc_vao_trang_thai().label("vao")
    da_o = func.so_giay_lam_viec(luc_vao_trang_thai(), moc)
    hang = session.execute(
        select(Request, Transition, vao)
        .join(
            Transition,
            and_(
                Transition.rule_set_id == Request.rule_set_id,
                Transition.from_state == Request.current_state,
                Transition.auto_after_hours.is_not(None),
                Transition.warn_before_hours.is_not(None),
            ),
        )
        .where(
            da_o
            >= cast(Transition.auto_after_hours - Transition.warn_before_hours, BigInteger) * 3600,
            da_o < cast(Transition.auto_after_hours, BigInteger) * 3600,
        )
        .order_by(Request.id)
    ).all()
    for ho_so, canh, luc_vao in hang:
        han = session.scalar(
            select(func.moc_sau_giay_lam_viec(luc_vao, canh.auto_after_hours * 3600))
        )
        xep_hang(
            session,
            TRIGGER_BAO_TRUOC,
            ho_so,
            context={"transition_id": canh.id, "deadline": han.isoformat() if han else None},
            dedupe_key=f"bao-truoc:{ho_so.id}:{luc_vao.isoformat()}",
        )
    return len(hang)


# --- 2. Sự kiện → thư ------------------------------------------------------


def _mui_gio(session: Session) -> ZoneInfo:
    ten = session.execute(
        text("SELECT time_zone FROM work_calendars WHERE is_default LIMIT 1")
    ).scalar_one_or_none()
    return ZoneInfo(ten or "UTC")


def _bien_mau(
    session: Session, ev: NotificationOutbox, ho_so: Request, nguoi: Person, buoc: str | None
) -> dict[str, str]:
    ten_trang_thai = {
        s.code: s.label
        for s in session.scalars(select(State).where(State.rule_set_id == ho_so.rule_set_id))
    }
    bien = {
        "ten_nguoi_nhan": nguoi.name,
        "ma_ho_so": _ma_ho_so(ho_so),
        "tieu_de": ho_so.title,
        "trang_thai": ten_trang_thai.get(ho_so.current_state, ho_so.current_state),
        "tu_trang_thai": "",
        "buoc": buoc or "",
        "han_tu_dong": "",
        "canh_tu_dong": "",
        "lien_ket": get_settings().portal_public_url.rstrip("/") + "/",
    }
    tu = ev.context.get("from_state")
    if tu:
        bien["tu_trang_thai"] = ten_trang_thai.get(tu, tu)
    if ev.context.get("transition_id"):
        canh = session.get(Transition, ev.context["transition_id"])
        if canh is not None:
            bien["canh_tu_dong"] = canh.activity_label.lower()
    if ev.context.get("deadline"):
        han = dt.datetime.fromisoformat(ev.context["deadline"]).astimezone(_mui_gio(session))
        bien["han_tu_dong"] = han.strftime("%H:%M %d/%m/%Y")
    return bien


def _nguoi_nhan(
    session: Session, loai: NotificationType, ho_so: Request, danh_ba: dict[str, Person]
) -> list[tuple[Person, str | None]]:
    """Người nhận theo `recipients` của loại, kèm nhãn bước chính đang chờ họ (nếu có)."""
    if loai.recipients == "requester":
        nguoi = danh_ba.get(ho_so.requester_id)
        return [(nguoi, None)] if nguoi else []
    # primary-step: cùng phép tính với cờ "cần tôi xử lý" (#227) — vai trò, phòng ban, người được giao
    ket_qua = []
    for nguoi in danh_ba.values():
        tac_nhan = Actor(id=nguoi.id, roles=nguoi.roles, departments=nguoi.departments)
        canh = my_primary_steps(session, [ho_so], tac_nhan).get(ho_so.id)
        if canh is not None:
            ket_qua.append((nguoi, canh.activity_label))
    return ket_qua


def mo_rong_su_kien(session: Session, danh_ba: dict[str, Person]) -> int:
    """Biến sự kiện chưa xử lý thành từng dòng thư. Trả số thư mới."""
    ch = get_settings()
    cac_su_kien = session.scalars(
        select(NotificationOutbox)
        .where(NotificationOutbox.processed_at.is_(None))
        .order_by(NotificationOutbox.id)
        .limit(ch.notify_batch_size)
    ).all()
    so_thu = 0
    for ev in cac_su_kien:
        ev.processed_at = func.now()
        ho_so = session.get(Request, ev.case_id)
        if _da_cu(session, ev, ho_so):
            continue
        loai_ap = session.scalars(
            select(NotificationType).where(
                NotificationType.trigger == ev.trigger, NotificationType.is_active
            )
        ).all()
        for loai in loai_ap:
            for nguoi, buoc in _nguoi_nhan(session, loai, ho_so, danh_ba):
                if nguoi.id == ev.actor_id:
                    continue
                bien = _bien_mau(session, ev, ho_so, nguoi, buoc)
                kq = session.execute(
                    insert(NotificationDelivery)
                    .values(
                        outbox_id=ev.id,
                        type_code=loai.code,
                        case_id=ho_so.id,
                        recipient_id=nguoi.id,
                        subject=string.Template(loai.subject_template).safe_substitute(bien),
                        body=string.Template(loai.body_template).safe_substitute(bien),
                    )
                    .on_conflict_do_nothing()
                )
                so_thu += kq.rowcount or 0
    session.flush()
    return so_thu


def _da_cu(session: Session, ev: NotificationOutbox, ho_so: Request) -> bool:
    """Sự kiện đã lỗi thời: hồ sơ đi tiếp trước khi bộ gửi kịp xử lý.

    Người nhận "có việc chờ tôi" tính theo trạng thái HIỆN TẠI, nên một sự kiện cũ mà vẫn xử lý thì
    người có việc ở trạng thái mới nhận hai thư — một cho sự kiện cũ, một cho sự kiện mới. Báo trước
    cũng vậy: hồ sơ đã rời trạng thái thì không còn gì để báo. Thư "đã tự chuyển" thì không lỗi thời.
    """
    if ev.trigger == TRIGGER_VAO_TRANG_THAI:
        return ev.context.get("to_state") not in (None, ho_so.current_state) or (
            "assignee_id" in ev.context and ev.context["assignee_id"] != ho_so.assignee_id
        )
    if ev.trigger == TRIGGER_BAO_TRUOC:
        canh = session.get(Transition, ev.context.get("transition_id"))
        return canh is None or canh.from_state != ho_so.current_state
    return False


# --- 3. Gửi ------------------------------------------------------------------


def gui_thu_den_han(session: Session, danh_ba: dict[str, Person]) -> int:
    """Gửi những thư đến hạn. Trả số thư đã gửi."""
    ch = get_settings()
    cac_thu = session.scalars(
        select(NotificationDelivery)
        .where(
            NotificationDelivery.status == "pending",
            NotificationDelivery.next_attempt_at <= func.now(),
        )
        .order_by(NotificationDelivery.id)
        .limit(ch.notify_batch_size)
    ).all()
    if not cac_thu:
        return 0

    loai = {t.code: t for t in session.scalars(select(NotificationType))}
    tuy_chon = {
        (p.user_id, p.type_code): p.enabled
        for p in session.scalars(
            select(NotificationPreference).where(
                NotificationPreference.user_id.in_({t.recipient_id for t in cac_thu})
            )
        )
    }
    bay_gio = session.execute(text("SELECT now()")).scalar_one()
    da_gui = 0
    with KetNoiThu() as ket_noi:
        for thu in cac_thu:
            loai_thu = loai[thu.type_code]
            bat = tuy_chon.get((thu.recipient_id, thu.type_code), loai_thu.default_enabled)
            if not (bat and loai_thu.is_active):
                thu.status, thu.last_error = "skipped", "Người nhận đã tắt loại thông báo này"
                continue
            nguoi = danh_ba.get(thu.recipient_id)
            if nguoi is None or not nguoi.email:
                thu.status, thu.last_error = "skipped", "Danh bạ không có địa chỉ thư của người nhận"
                continue
            thu.attempts += 1
            try:
                ket_noi.gui(nguoi.email, nguoi.name, thu.subject or "", thu.body or "")
            except ThuLoi as loi:
                thu.last_error = str(loi)[:DO_DAI_CAU_LOI]
                if thu.attempts >= ch.notify_max_attempts:
                    thu.status = "failed"
                    logger.warning("Bỏ thư %s sau %d lần thử: %s", thu.id, thu.attempts, loi)
                else:
                    cho = ch.notify_retry_after_seconds * 2 ** (thu.attempts - 1)
                    thu.next_attempt_at = bay_gio + dt.timedelta(seconds=cho)
                    logger.info("Thư %s chưa gửi được, thử lại sau %d giây: %s", thu.id, cho, loi)
                if not ket_noi.da_mo:
                    # Không mở được kết nối: các thư còn lại đợi lượt sau, khỏi chờ hạn chót từng thư
                    break
                continue
            thu.status, thu.sent_at, thu.last_error = "sent", func.now(), None
            da_gui += 1
    session.flush()
    if da_gui:
        logger.info("Đã gửi %d thư thông báo", da_gui)
    return da_gui


def quet_gui(session: Session, danh_ba: KeycloakDirectory | None = None) -> int:
    """Một lượt của bộ gửi thư. Không tự commit — `chay_luot_quet` lo ranh giới giao dịch."""
    phat_hien_bao_truoc(session)
    try:
        nguoi = _danh_ba(danh_ba)
    except DirectoryUnavailable as loi:
        # Danh bạ là phụ thuộc của việc gửi, không phải của bộ quét: sự kiện nằm chờ, nhịp vẫn tốt
        logger.warning("Bộ gửi thư chưa tra được danh bạ, để lượt sau: %s", loi)
        return 0
    mo_rong_su_kien(session, nguoi)
    return gui_thu_den_han(session, nguoi)


def do_dai_hang_doi(session: Session) -> dict[str, int]:
    """Số sự kiện chưa xử lý và số thư chờ gửi — cho màn Hệ thống và số đo (#247)."""
    return {
        "events_pending": session.scalar(
            select(func.count()).where(NotificationOutbox.processed_at.is_(None))
        )
        or 0,
        "deliveries_pending": session.scalar(
            select(func.count()).where(NotificationDelivery.status == "pending")
        )
        or 0,
        "deliveries_failed": session.scalar(
            select(func.count()).where(NotificationDelivery.status == "failed")
        )
        or 0,
    }
