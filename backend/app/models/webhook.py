# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Hai bảng của webhook (#390) — lược đồ ở bản sửa 0031_webhook. Lần gửi do trigger trên `event_log` sinh ra
# (0035, #492), không còn con trỏ trên đăng ký.

from __future__ import annotations

import datetime as dt

from sqlalchemy import ARRAY, BigInteger, Boolean, ForeignKey, Identity, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

CHO_GUI = "pending"
DA_GUI = "delivered"
HONG = "failed"


class WebhookSubscription(Base):
    """Một địa chỉ nhận sự kiện. `activities`, `process_code` để trống là nhận mọi sự kiện."""

    __tablename__ = "webhook_subscriptions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    secret: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    activities: Mapped[list[str] | None] = mapped_column(ARRAY(Text), default=None)
    process_code: Mapped[str | None] = mapped_column(Text, ForeignKey("processes.code"), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    owner_id: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())


class WebhookDelivery(Base):
    """Một lần đưa một sự kiện tới một đăng ký, kèm vết các lần thử."""

    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("webhook_subscriptions.id", ondelete="CASCADE")
    )
    event_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("event_log.id"))
    status: Mapped[str] = mapped_column(Text, default=CHO_GUI)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    last_status_code: Mapped[int | None] = mapped_column(Integer, default=None)
    last_error: Mapped[str | None] = mapped_column(Text, default=None)
    delivered_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
