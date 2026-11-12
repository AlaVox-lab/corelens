# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Thông báo thư điện tử (#251): loại thông báo (dữ liệu), tùy chọn của người dùng, hàng đợi sự kiện
# và vết gửi từng thư.
#
# Hai tầng hàng đợi, vì hai việc có nhịp khác nhau:
#   notification_outbox      một dòng mỗi SỰ KIỆN (hồ sơ vào trạng thái mới, tới mốc báo trước, vừa
#                            tự đi), ghi CÙNG giao dịch nghiệp vụ — rẻ, không gọi mạng. Chưa biết gửi ai.
#   notification_deliveries  một dòng mỗi THƯ cho một người nhận, do bộ quét gửi tạo khi đã tra danh bạ;
#                            mang số lần thử, lỗi cuối, lúc gửi — là vết để đối soát.
# Địa chỉ thư không lưu ở đâu cả: tra danh bạ Keycloak lúc gửi.

from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, SmallInteger, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class NotificationType(Base):
    """Một loại thông báo — dữ liệu, nạp từ infra/seed/05-loai-thong-bao.sql.

    `trigger` là cơ chế mã biết (`state-entered`, `auto-warning`, `auto-done`); `recipients` là cách
    chọn người nhận (`primary-step` — người đang có bước chính, `requester` — người gửi hồ sơ). Tiêu
    đề và nội dung là mẫu `string.Template` (`$ma_ho_so`…), danh sách biến ở tệp dữ liệu khởi tạo.
    """

    __tablename__ = "notification_types"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    label: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    trigger: Mapped[str] = mapped_column(Text)
    recipients: Mapped[str] = mapped_column(Text)
    subject_template: Mapped[str] = mapped_column(Text)
    body_template: Mapped[str] = mapped_column(Text)
    # Người dùng chưa chọn gì thì theo giá trị này
    default_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(SmallInteger, default=0)


class NotificationPreference(Base):
    """Người dùng bật hay tắt một loại thông báo. Không có dòng là theo `default_enabled`."""

    __tablename__ = "notification_preferences"

    user_id: Mapped[str] = mapped_column(Text, primary_key=True)
    type_code: Mapped[str] = mapped_column(
        Text, ForeignKey("notification_types.code", ondelete="CASCADE"), primary_key=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class NotificationOutbox(Base):
    """Một sự kiện chờ bộ quét gửi tìm người nhận."""

    __tablename__ = "notification_outbox"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trigger: Mapped[str] = mapped_column(Text)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("requests.id"))
    # Biến cho mẫu thư chụp lúc sự kiện xảy ra (trạng thái cũ, cạnh tự đi, hạn…)
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Khóa chống trùng — mốc báo trước chỉ báo một lần mỗi lần hồ sơ vào trạng thái
    dedupe_key: Mapped[str | None] = mapped_column(Text, default=None, unique=True)
    # Người vừa làm thao tác sinh sự kiện: không gửi thư cho chính họ
    actor_id: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, default=None)


class NotificationDelivery(Base):
    """Một thư cho một người — vết gửi để đối soát (#251)."""

    __tablename__ = "notification_deliveries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    outbox_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("notification_outbox.id", ondelete="CASCADE")
    )
    type_code: Mapped[str] = mapped_column(Text, ForeignKey("notification_types.code"))
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("requests.id"))
    recipient_id: Mapped[str] = mapped_column(Text)
    # `pending` (chờ gửi hay chờ thử lại), `sent`, `failed` (hết lượt thử), `skipped` (người nhận tắt
    # loại này, hay danh bạ không có email)
    status: Mapped[str] = mapped_column(Text, default="pending")
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0)
    next_attempt_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_error: Mapped[str | None] = mapped_column(Text, default=None)
    # Tiêu đề và nội dung dựng từ mẫu lúc tìm người nhận — thư gửi đi đúng như vết ghi
    subject: Mapped[str | None] = mapped_column(Text, default=None)
    body: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)
