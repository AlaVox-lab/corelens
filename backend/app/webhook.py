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
# Nguồn là `event_log` — chỉ ghi thêm, mỗi bước chuyển đúng một dòng. Lần gửi KHÔNG do bộ gửi sinh ra: trigger
# `webhook_sinh_lan_gui` trên `event_log` (bản sửa 0035, #492) chèn một dòng `webhook_deliveries` cho mỗi đăng ký
# đang bật khớp bộ lọc, ngay trong giao dịch ghi sự kiện. Sự kiện commit thì lần gửi commit cùng, hoàn tác thì
# cùng mất — không còn con trỏ nào có thể vượt qua sự kiện của một giao dịch commit muộn. Khóa duy nhất
# (đăng ký, sự kiện) nên không bao giờ gửi trùng.
#
# Bộ gửi (chạy nền theo khuôn bộ gửi thư #251, có khóa tư vấn và dòng nhịp) chỉ gửi, và không giữ giao dịch
# trong lúc gọi mạng:
#
#   1. Nhận lô: một giao dịch ngắn khóa các lần gửi đến hạn (`SKIP LOCKED`), dời hạn của chúng qua hết lượt
#      này để bản khác không nhận trùng, đọc sẵn địa chỉ, bí mật, thân — rồi commit.
#   2. Gửi từng lần, NGOÀI giao dịch: POST JSON, ký HMAC-SHA256. Lượt có trần thời gian; một địa chỉ không
#      phản hồi (lỗi mạng, hết hạn chờ) thì các lần còn lại của đăng ký đó để lượt sau — một bên nhận treo
#      tốn nhiều nhất một lần hết hạn chờ mỗi lượt, không kéo chậm đăng ký khác.
#   3. Ghi kết quả từng lần bằng một giao dịch ngắn: 2xx là xong; khác thì thử lại sau, chờ nhân đôi mỗi
#      lần, quá số lần thì đánh dấu hỏng. Lần chưa kịp gửi trả về hạn ngay.
#
# Không giao dịch nào giữ khóa trên `webhook_subscriptions` trong lúc gọi mạng, nên hủy đăng ký không phải chờ
# hết lượt. Commit giữa lượt cũng nhả khóa tư vấn của `chay_luot_quet` — không sao: dời hạn lúc nhận lô đã
# ngăn hai bản nhận trùng một lần gửi.
#
# Chuyển trạng thái không gọi mạng: trigger chỉ chèn một dòng vào bảng hàng đợi, bên nhận sập không làm chậm
# hay hỏng thao tác nào. Bên nhận phải chịu được nhận lại một sự kiện (thử lại sau khi bên
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
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import func, select, update
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
# Trần thời gian gửi của một lượt (#492). Lần đã nhận mà chưa kịp gửi thì trả về hạn ngay cho lượt sau
THOI_GIAN_MOT_LUOT_GIAY = 30

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


@dataclass(frozen=True)
class LanGuiDaNhan:
    """Đủ mọi thứ để gửi một lần mà không cần giao dịch nào mở."""

    id: int
    subscription_id: int
    event_id: int
    url: str
    secret: str
    than: bytes


def nhan_lo(session: Session) -> list[LanGuiDaNhan]:
    """Giao dịch ngắn: nhận các lần gửi đến hạn, dời hạn qua hết lượt này, đọc sẵn thân. Tự commit."""
    ch = get_settings()
    lan_gui = session.scalars(
        select(WebhookDelivery)
        .where(WebhookDelivery.status == CHO_GUI, WebhookDelivery.next_attempt_at <= func.now())
        .order_by(WebhookDelivery.next_attempt_at, WebhookDelivery.id)
        .limit(ch.webhook_batch_size)
        .with_for_update(skip_locked=True)
    ).all()
    giu = dt.timedelta(seconds=THOI_GIAN_MOT_LUOT_GIAY + ch.webhook_timeout_seconds)
    da_nhan = []
    for lg in lan_gui:
        dk = session.get(WebhookSubscription, lg.subscription_id)
        than = json.dumps(than_su_kien(session, lg.event_id), ensure_ascii=False).encode()
        da_nhan.append(LanGuiDaNhan(lg.id, dk.id, lg.event_id, dk.url, dk.secret, than))
        lg.next_attempt_at = func.now() + giu
    session.commit()
    return da_nhan


def gui_mot_lan(lg: LanGuiDaNhan) -> tuple[int | None, str | None]:
    """Gửi một lần, ngoài mọi giao dịch. Trả (mã phản hồi, lỗi) — lỗi `None` là đã tới."""
    moc = str(int(time.time()))
    tieu_de = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "DX-OS-Lab-Webhook",
        "X-DXOS-Event-Id": str(lg.event_id),
        "X-DXOS-Timestamp": moc,
        "X-DXOS-Signature": ky(lg.secret, moc, lg.than),
    }
    try:
        ma = gui_http(lg.url, lg.than, tieu_de, get_settings().webhook_timeout_seconds)
    except Exception as loi:  # noqa: BLE001 — mọi lỗi mạng đều là "chưa tới", thử lại sau
        return None, str(loi)[:DO_DAI_CAU_LOI]
    return ma, None if 200 <= ma < 300 else f"HTTP {ma}"


def ghi_ket_qua(session: Session, ma_lan_gui: int, ma: int | None, loi: str | None) -> str | None:
    """Giao dịch ngắn: ghi kết quả một lần thử. Trả trạng thái mới, `None` nếu đăng ký đã bị hủy. Tự commit."""
    ch = get_settings()
    lg = session.get(WebhookDelivery, ma_lan_gui, with_for_update=True)
    if lg is None or lg.status != CHO_GUI:
        session.commit()
        return None
    lg.attempts += 1
    lg.last_status_code, lg.last_error = ma, loi
    if loi is None:
        lg.status, lg.delivered_at = DA_GUI, func.now()
    elif lg.attempts >= ch.webhook_max_attempts:
        lg.status = HONG
    else:
        cho = ch.webhook_retry_after_seconds * 2 ** (lg.attempts - 1)
        lg.next_attempt_at = func.now() + dt.timedelta(seconds=cho)
    trang_thai = lg.status
    session.commit()
    return trang_thai


def tra_ve_han(session: Session, cac_ma: list[int]) -> None:
    """Lần đã nhận mà chưa gửi: đến hạn lại ngay, cho lượt sau. Tự commit."""
    if cac_ma:
        session.execute(
            update(WebhookDelivery)
            .where(WebhookDelivery.id.in_(cac_ma), WebhookDelivery.status == CHO_GUI)
            .values(next_attempt_at=func.now())
        )
    session.commit()


def quet_webhook(session: Session) -> int:
    """Một lượt bộ gửi: nhận lô, gửi ngoài giao dịch, ghi từng kết quả. Trả số lần gửi thành công.

    Tự commit nhiều lần (xem đầu tệp); `chay_luot_quet` chỉ còn ghi dòng nhịp ở giao dịch cuối.
    """
    da_nhan = nhan_lo(session)
    het_gio = time.monotonic() + THOI_GIAN_MOT_LUOT_GIAY
    treo: set[int] = set()
    chua_gui: list[int] = []
    thanh_cong = hong = 0
    for lg in da_nhan:
        if lg.subscription_id in treo or time.monotonic() >= het_gio:
            chua_gui.append(lg.id)
            continue
        ma, loi = gui_mot_lan(lg)
        if ma is None:
            # Không phản hồi: đừng để mọi lần còn lại của địa chỉ này đều chờ hết hạn
            treo.add(lg.subscription_id)
        trang_thai = ghi_ket_qua(session, lg.id, ma, loi)
        thanh_cong += trang_thai == DA_GUI
        hong += trang_thai == HONG
    tra_ve_han(session, chua_gui)
    if hong:
        logger.warning("Webhook: %d lần gửi hỏng hẳn sau %d lần thử", hong, get_settings().webhook_max_attempts)
    return thanh_cong


def do_dai_hang_cho(session: Session) -> int:
    """Số lần gửi đang chờ — cho màn Hệ thống."""
    return session.scalar(select(func.count()).where(WebhookDelivery.status == CHO_GUI)) or 0


def co_dang_ky_dang_bat(session: Session) -> bool:
    """Có đăng ký nào đang bật không — màn Hệ thống chỉ báo nhịp bộ gửi khi có."""
    return bool(session.scalar(select(func.count()).where(WebhookSubscription.is_active)))
