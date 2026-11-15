# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Tùy chọn thông báo thư của chính người dùng (#251): xem và bật/tắt từng loại.
#
# Mỗi người chỉ đọc và sửa tùy chọn của chính mình — định danh lấy từ token, không nhận từ đường dẫn.
# Danh sách loại đọc từ bảng `notification_types`, nên thêm một loại trong dữ liệu là giao diện có
# thêm một ô, không sửa mã cổng.
#
# Đây là API của nền tảng lõi (#365): app/main.py gắn router hai lần — đường cũ `/me/notifications` và
# `/core/v1/notifications/preferences`. Tiền tố và nhãn OpenAPI gắn lúc include.

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor
from app.config import get_settings
from app.db import get_session
from app.models.thong_bao import NotificationPreference, NotificationType
from app.workflow.context import Actor

router = APIRouter()


class LoaiThongBaoRa(BaseModel):
    code: str
    label: str
    description: str | None
    enabled: bool


class TuyChonThongBaoRa(BaseModel):
    # Máy chủ thư có được cấu hình không — tắt thì giao diện nói rõ là chưa gửi thư nào
    email_enabled: bool
    types: list[LoaiThongBaoRa]


class DoiTuyChonVao(BaseModel):
    enabled: bool


def _doc(session: Session, actor: Actor) -> TuyChonThongBaoRa:
    da_chon = {
        p.type_code: p.enabled
        for p in session.scalars(
            select(NotificationPreference).where(NotificationPreference.user_id == actor.id)
        )
    }
    loai = session.scalars(
        select(NotificationType)
        .where(NotificationType.is_active)
        .order_by(NotificationType.display_order, NotificationType.code)
    )
    return TuyChonThongBaoRa(
        email_enabled=get_settings().notify_enabled,
        types=[
            LoaiThongBaoRa(
                code=t.code,
                label=t.label,
                description=t.description,
                enabled=da_chon.get(t.code, t.default_enabled),
            )
            for t in loai
        ],
    )


@router.get("", response_model=TuyChonThongBaoRa)
def xem_tuy_chon(
    actor: Annotated[Actor, Depends(current_actor)],
    session: Annotated[Session, Depends(get_session)],
) -> TuyChonThongBaoRa:
    return _doc(session, actor)


@router.post("/{code}", response_model=TuyChonThongBaoRa)
def doi_tuy_chon(
    code: str,
    vao: DoiTuyChonVao,
    actor: Annotated[Actor, Depends(current_actor)],
    session: Annotated[Session, Depends(get_session)],
) -> TuyChonThongBaoRa:
    loai = session.get(NotificationType, code)
    if loai is None or not loai.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không có loại thông báo này.")
    session.execute(
        insert(NotificationPreference)
        .values(user_id=actor.id, type_code=code, enabled=vao.enabled)
        .on_conflict_do_update(
            index_elements=["user_id", "type_code"],
            set_={"enabled": vao.enabled, "updated_at": func.now()},
        )
    )
    session.commit()
    return _doc(session, actor)
