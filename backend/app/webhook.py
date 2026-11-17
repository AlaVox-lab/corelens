# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Truyền phát sự kiện ra ngoài bằng webhook (#390) — dịch vụ lõi "trục truyền phát sự kiện" của đề thi.
#
#     POST   /core/v1/webhooks                 đăng ký một địa chỉ nhận (trả bí mật ký đúng một lần)
#     GET    /core/v1/webhooks                 các đăng ký
#     GET    /core/v1/webhooks/{id}            một đăng ký
#     DELETE /core/v1/webhooks/{id}            hủy đăng ký
#     GET    /core/v1/webhooks/{id}/deliveries các lần gửi gần đây — để biết vì sao sự kiện chưa tới
#
# Chỉ `administrator` (người hay tài khoản dịch vụ mang vai đó): một đăng ký nhận sự kiện của MỌI hồ sơ,
# ngang quyền với xuất nhật ký sự kiện `GET /core/v1/events`.
#
# Nguồn là `event_log` — chỉ ghi thêm, mỗi bước chuyển đúng một dòng. Mỗi đăng ký giữ con trỏ
# `last_event_id`; bộ gửi (chạy nền theo khuôn bộ gửi thư #251, có khóa tư vấn và dòng nhịp) làm hai việc:
#
#   1. Mở rộng: sự kiện mới hơn con trỏ, khớp bộ lọc → một dòng `webhook_deliveries` (khóa duy nhất theo
#      (đăng ký, sự kiện) nên không bao giờ gửi trùng), rồi dời con trỏ. Cùng một giao dịch.
#   2. Gửi: lần gửi đến hạn → POST JSON, ký HMAC-SHA256. 2xx là xong; khác thì thử lại sau, chờ nhân đôi
#      mỗi lần, quá số lần thì đánh dấu hỏng.
#
# Chuyển trạng thái không biết gì về webhook: không gọi mạng trong giao dịch nghiệp vụ, bên nhận sập
# không làm chậm hay hỏng thao tác nào. Bên nhận phải chịu được nhận lại một sự kiện (thử lại sau khi bên
# nhận đã xử lý mà trả lời không kịp) — dùng `X-DXOS-Event-Id` để bỏ trùng.
#
# Chữ ký: `X-DXOS-Signature: sha256=<hex HMAC-SHA256(bí mật, "<X-DXOS-Timestamp>.<thân>")>`. Bên nhận tính
# lại và so bằng phép so hằng thời gian, đồng thời từ chối mốc thời gian quá cũ để chống phát lại.

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import logging
import secrets
import time
import urllib.error
import urllib.request
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.config import get_settings
from app.db import get_session
from app.models.case import EventLog, Request
from app.models.webhook import CHO_GUI, DA_GUI, HONG, WebhookDelivery, WebhookSubscription
from app.models.workflow_config import Process, RuleSet
from app.workflow.context import Actor

logger = logging.getLogger(__name__)

TEN_BO_QUET_WEBHOOK = "webhook"
NHAN_BO_QUET_WEBHOOK = "Bộ gửi webhook"
VAI_TRO_WEBHOOK = "administrator"
DO_DAI_CAU_LOI = 300

router = APIRouter()
_QuanTri = Annotated[Actor, Depends(require_roles(VAI_TRO_WEBHOOK))]
_Phien = Annotated[Session, Depends(get_session)]


# ---------------------------------------------------------------------------
# Chữ ký
# ---------------------------------------------------------------------------


def ky(bi_mat: str, moc: str, than: bytes) -> str:
    """Giá trị tiêu đề `X-DXOS-Signature` cho một thân và mốc thời gian."""
    ma = hmac.new(bi_mat.encode(), moc.encode() + b"." + than, hashlib.sha256).hexdigest()
    return f"sha256={ma}"


def kiem_chu_ky(bi_mat: str, moc: str, than: bytes, chu_ky: str) -> bool:
    """Phía nhận dùng: chữ ký có khớp không (so hằng thời gian)."""
    return hmac.compare_digest(ky(bi_mat, moc, than), chu_ky)


# ---------------------------------------------------------------------------
# API đăng ký
# ---------------------------------------------------------------------------


class DangKyVao(BaseModel):
    url: HttpUrl = Field(description="Địa chỉ nhận, http hoặc https. Lõi POST JSON tới đây")
    description: str | None = Field(default=None, max_length=200)
    activities: list[str] | None = Field(
        default=None, description="Chỉ các mã hoạt động này (cột `activity` của nhật ký); bỏ trống là mọi hoạt động"
    )
    process: str | None = Field(
        default=None, description="Chỉ một quy trình (GET /core/v1/workflow/processes); bỏ trống là mọi quy trình"
    )


class DangKyRa(BaseModel):
    id: int
    url: str
    description: str | None
    activities: list[str] | None
    process: str | None
    is_active: bool
    owner_id: str
    last_event_id: int
    created_at: dt.datetime


class DangKyMoiRa(DangKyRa):
    secret: str = Field(description="Bí mật ký HMAC — chỉ trả đúng một lần, lúc tạo")


class LanGuiRa(BaseModel):
    event_id: int
    status: str
    attempts: int
    next_attempt_at: dt.datetime
    last_status_code: int | None
    last_error: str | None
    delivered_at: dt.datetime | None


def _ra(dk: WebhookSubscription) -> dict:
    return {
        "id": dk.id,
        "url": dk.url,
        "description": dk.description,
        "activities": dk.activities,
        "process": dk.process_code,
        "is_active": dk.is_active,
        "owner_id": dk.owner_id,
        "last_event_id": dk.last_event_id,
        "created_at": dk.created_at,
    }


def _lay(session: Session, ma: int) -> WebhookSubscription:
    dk = session.get(WebhookSubscription, ma)
    if dk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "webhook-not-found", "message": "Không có đăng ký webhook này."},
        )
    return dk


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DangKyMoiRa)
def tao_dang_ky(vao: DangKyVao, session: _Phien, actor: _QuanTri) -> dict:
    """Đăng ký một địa chỉ nhận sự kiện. Chỉ nhận sự kiện xảy ra SAU lúc đăng ký.

    Mỗi sự kiện tới là một `POST` thân JSON (mã sự kiện, hồ sơ, quy trình, hoạt động, trạng thái từ → sang,
    người làm, mốc UTC), ký bằng bí mật trả về ở đây — lưu lại, lần sau không xem được nữa.
    """
    if vao.process is not None and session.get(Process, vao.process) is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "unknown-process", "message": f"Không có quy trình mang mã {vao.process!r}."},
        )
    dk = WebhookSubscription(
        url=str(vao.url),
        secret=secrets.token_hex(32),
        description=vao.description,
        activities=sorted(set(vao.activities)) if vao.activities else None,
        process_code=vao.process,
        owner_id=actor.id,
        last_event_id=session.scalar(select(func.coalesce(func.max(EventLog.id), 0))),
    )
    session.add(dk)
    session.commit()
    session.refresh(dk)
    return {**_ra(dk), "secret": dk.secret}


@router.get("", response_model=list[DangKyRa])
def danh_sach_dang_ky(session: _Phien, _: _QuanTri) -> list[dict]:
    """Mọi đăng ký webhook, mới nhất trước. Không trả bí mật."""
    return [_ra(dk) for dk in session.scalars(select(WebhookSubscription).order_by(WebhookSubscription.id.desc()))]


@router.get("/{webhook_id}", response_model=DangKyRa)
def xem_dang_ky(webhook_id: int, session: _Phien, _: _QuanTri) -> dict:
    return _ra(_lay(session, webhook_id))


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def huy_dang_ky(webhook_id: int, session: _Phien, _: _QuanTri) -> Response:
    """Hủy đăng ký; các lần gửi đang chờ bỏ theo."""
    session.delete(_lay(session, webhook_id))
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{webhook_id}/deliveries", response_model=list[LanGuiRa])
def lan_gui_gan_day(webhook_id: int, session: _Phien, _: _QuanTri) -> list[WebhookDelivery]:
    """Năm mươi lần gửi gần nhất của một đăng ký, mới nhất trước."""
    _lay(session, webhook_id)
    return list(
        session.scalars(
            select(WebhookDelivery)
            .where(WebhookDelivery.subscription_id == webhook_id)
            .order_by(WebhookDelivery.event_id.desc())
            .limit(50)
        )
    )


# ---------------------------------------------------------------------------
# Bộ gửi
# ---------------------------------------------------------------------------


def mo_rong(session: Session) -> int:
    """Sự kiện mới hơn con trỏ của từng đăng ký đang bật → lần gửi chờ. Dời con trỏ. Không tự commit."""
    co = get_settings().webhook_batch_size
    tong = 0
    for dk in session.scalars(select(WebhookSubscription).where(WebhookSubscription.is_active)):
        hang = session.execute(
            select(EventLog.id, EventLog.activity, RuleSet.process_code)
            .join(Request, Request.id == EventLog.case_id)
            .join(RuleSet, RuleSet.id == Request.rule_set_id)
            .where(EventLog.id > dk.last_event_id)
            .order_by(EventLog.id)
            .limit(co)
        ).all()
        if not hang:
            continue
        khop = [
            ma
            for ma, hoat_dong, quy_trinh in hang
            if (not dk.activities or hoat_dong in dk.activities)
            and (dk.process_code is None or quy_trinh == dk.process_code)
        ]
        if khop:
            session.execute(
                insert(WebhookDelivery)
                .values([{"subscription_id": dk.id, "event_id": ma} for ma in khop])
                .on_conflict_do_nothing(constraint="webhook_delivery_once")
            )
            tong += len(khop)
        # Dời qua cả sự kiện không khớp: lần sau không xét lại
        dk.last_event_id = hang[-1][0]
    return tong


def than_su_kien(session: Session, event_id: int) -> dict:
    """Thân JSON gửi cho bên nhận — một sự kiện của nhật ký, mốc UTC."""
    e, ma_quy_trinh = session.execute(
        select(EventLog, RuleSet.process_code)
        .join(Request, Request.id == EventLog.case_id)
        .join(RuleSet, RuleSet.id == Request.rule_set_id)
        .where(EventLog.id == event_id)
    ).one()
    return {
        "event_id": e.id,
        "case_id": e.case_id,
        "process_code": ma_quy_trinh,
        "activity": e.activity,
        "from_state": e.from_state,
        "to_state": e.to_state,
        "actor": e.actor,
        "actor_label": e.actor_label,
        "on_behalf_of": e.on_behalf_of,
        "timestamp": e.timestamp.astimezone(dt.UTC).isoformat(),
    }


def _post(url: str, than: bytes, tieu_de: dict[str, str], han_giay: float) -> int:
    """POST một thân; trả mã phản hồi. Lỗi mạng ném ra."""
    yeu_cau = urllib.request.Request(url, data=than, headers=tieu_de, method="POST")
    try:
        with urllib.request.urlopen(yeu_cau, timeout=han_giay) as phan_hoi:  # noqa: S310 — địa chỉ do quản trị viên đăng ký
            return phan_hoi.status
    except urllib.error.HTTPError as loi:
        return loi.code


# Kiểm thử thay hàm này để không gọi mạng thật
gui_http = _post


def gui_den_han(session: Session) -> tuple[int, int]:
    """Gửi các lần đến hạn. Trả (số thành công, số hỏng ở lượt này). Không tự commit."""
    ch = get_settings()
    lan_gui = session.scalars(
        select(WebhookDelivery)
        .where(WebhookDelivery.status == CHO_GUI, WebhookDelivery.next_attempt_at <= func.now())
        .order_by(WebhookDelivery.next_attempt_at, WebhookDelivery.id)
        .limit(ch.webhook_batch_size)
        .with_for_update(skip_locked=True)
    ).all()
    thanh_cong = hong = 0
    for lg in lan_gui:
        dk = session.get(WebhookSubscription, lg.subscription_id)
        than = json.dumps(than_su_kien(session, lg.event_id), ensure_ascii=False).encode()
        moc = str(int(time.time()))
        tieu_de = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "DX-OS-Lab-Webhook",
            "X-DXOS-Event-Id": str(lg.event_id),
            "X-DXOS-Timestamp": moc,
            "X-DXOS-Signature": ky(dk.secret, moc, than),
        }
        lg.attempts += 1
        try:
            ma = gui_http(dk.url, than, tieu_de, ch.webhook_timeout_seconds)
            lg.last_status_code, lg.last_error = ma, None if 200 <= ma < 300 else f"HTTP {ma}"
        except Exception as loi:  # noqa: BLE001 — mọi lỗi mạng đều là "chưa tới", thử lại sau
            lg.last_status_code, lg.last_error = None, str(loi)[:DO_DAI_CAU_LOI]
        if lg.last_error is None:
            lg.status, lg.delivered_at = DA_GUI, func.now()
            thanh_cong += 1
        elif lg.attempts >= ch.webhook_max_attempts:
            lg.status = HONG
            hong += 1
        else:
            cho = ch.webhook_retry_after_seconds * 2 ** (lg.attempts - 1)
            lg.next_attempt_at = func.now() + dt.timedelta(seconds=cho)
    return thanh_cong, hong


def quet_webhook(session: Session) -> int:
    """Một lượt bộ gửi: mở rộng rồi gửi. Trả số lần gửi thành công. Ranh giới giao dịch do `chay_luot_quet`."""
    mo_rong(session)
    session.flush()
    thanh_cong, hong = gui_den_han(session)
    # Ghi ngay vết lần thử: phía gọi đọc lại hay làm mới đối tượng thì không mất số lần thử
    session.flush()
    if hong:
        logger.warning("Webhook: %d lần gửi hỏng hẳn sau %d lần thử", hong, get_settings().webhook_max_attempts)
    return thanh_cong


def do_dai_hang_cho(session: Session) -> int:
    """Số lần gửi đang chờ — cho màn Hệ thống."""
    return session.scalar(select(func.count()).where(WebhookDelivery.status == CHO_GUI)) or 0


def co_dang_ky_dang_bat(session: Session) -> bool:
    """Có đăng ký nào đang bật không — màn Hệ thống chỉ báo nhịp bộ gửi khi có."""
    return bool(session.scalar(select(func.count()).where(WebhookSubscription.is_active)))
