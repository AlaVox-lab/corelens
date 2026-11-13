# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Nhật ký thay đổi cấu hình (#255) — bản sửa 0025, chỉ ghi thêm, trigger chặn sửa và xóa.
# Ủy quyền khi vắng mặt (#252) — bản sửa 0026.

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ConfigChange(Base):
    """Một trường cấu hình bị quản trị viên sửa trên màn quản trị: ai, lúc nào, từ đâu sang đâu."""

    __tablename__ = "config_changes"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    changed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actor_id: Mapped[str] = mapped_column(Text)
    actor_label: Mapped[str | None] = mapped_column(Text, default=None)
    entity: Mapped[str] = mapped_column(Text)
    entity_code: Mapped[str] = mapped_column(Text)
    field: Mapped[str] = mapped_column(Text)
    old_value: Mapped[Any] = mapped_column(JSONB(none_as_null=True), default=None)
    new_value: Mapped[Any] = mapped_column(JSONB(none_as_null=True), default=None)


class Delegation(Base):
    """Người vắng cho một người cùng phòng mang vai của mình trong phòng đó, trong một khoảng thời gian.

    Hiệu lực khi `starts_at <= bây giờ < ends_at` và chưa thu hồi. Hai mốc lưu UTC; màn khai chọn
    theo ngày, dịch vụ đổi sang 00:00 ngày đầu và 00:00 ngày sau ngày cuối theo múi giờ của lịch làm
    việc mặc định — xem app/workflow/uy_quyen.py.
    """

    __tablename__ = "delegations"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    delegator_id: Mapped[str] = mapped_column(Text)
    delegator_label: Mapped[str] = mapped_column(Text)
    delegate_id: Mapped[str] = mapped_column(Text)
    delegate_label: Mapped[str] = mapped_column(Text)
    department_code: Mapped[str] = mapped_column(Text, ForeignKey("departments.code"))
    roles: Mapped[list[str]] = mapped_column(ARRAY(Text))
    starts_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by_id: Mapped[str] = mapped_column(Text)
    created_by_label: Mapped[str] = mapped_column(Text)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    revoked_by_id: Mapped[str | None] = mapped_column(Text, default=None)
    revoked_by_label: Mapped[str | None] = mapped_column(Text, default=None)
