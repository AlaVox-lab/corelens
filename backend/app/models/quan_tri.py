# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Nhật ký thay đổi cấu hình (#255) — bản sửa 0025, chỉ ghi thêm, trigger chặn sửa và xóa.
# Ủy quyền khi vắng mặt (#252) — bản sửa 0026.
# Nhật ký kiểm toán truy cập dữ liệu cá nhân (#431) — bản sửa 0038, chỉ ghi thêm.

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, Integer, Text, func
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


class AccessKind(Base):
    """Một loại truy cập dữ liệu cá nhân được ghi kiểm toán (#431): xem chi tiết hồ sơ, xem liên hệ, tải tệp, xuất."""

    __tablename__ = "access_kinds"

    # Mã loại, ví dụ `case-view`; dịch vụ ghi đúng các mã này (`app/kiem_toan.py`)
    code: Mapped[str] = mapped_column(Text, primary_key=True)
    # Nhãn tiếng Việt hiện trên màn Hệ thống
    label: Mapped[str] = mapped_column(Text)
    # Thứ tự trong ô chọn loại
    display_order: Mapped[int] = mapped_column(Integer, default=0)


class AccessAuditLog(Base):
    """Một lần truy cập dữ liệu cá nhân của người khác (#431) — ai, lúc nào, loại gì, hồ sơ và tệp nào.

    Chỉ ghi thêm: trigger chặn sửa và xóa, trừ chính việc khóa ngoại gỡ `case_id` khi hồ sơ bị xóa. Ghi bằng
    phiên riêng (`app/kiem_toan.py`), nên ghi hỏng không làm hỏng trang người dùng đang mở.
    """

    __tablename__ = "access_audit_log"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    # Lúc truy cập, đồng hồ của cơ sở dữ liệu, UTC
    at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Mã người trong token (`sub`) — người hay tài khoản dịch vụ
    actor: Mapped[str] = mapped_column(Text)
    # Nhãn tên chụp lúc truy cập, như `event_log.actor_label` — ẩn danh hóa của ADR-0009 thay như nhau
    actor_label: Mapped[str | None] = mapped_column(Text, default=None)
    # Loại truy cập — nhãn đọc từ `access_kinds`
    access_kind: Mapped[str] = mapped_column(Text, ForeignKey("access_kinds.code"))
    # Hồ sơ được xem; NULL khi truy cập không gắn hồ sơ (xuất nhật ký) hay khi hồ sơ đã bị xóa
    case_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("requests.id", ondelete="SET NULL"), default=None
    )
    # Tệp đính kèm được tải
    attachment_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
    # `ung-dung` — các màn của ứng dụng minh họa; `loi` — API `/core/v1`
    channel: Mapped[str] = mapped_column(Text)
    # Tham số của lần truy cập, ví dụ định dạng và khoảng thời gian của lần xuất
    details: Mapped[dict | None] = mapped_column(JSONB, default=None)

    __table_args__ = (
        Index("access_audit_log_theo_ho_so", "case_id", "at"),
        Index("access_audit_log_theo_nguoi", "actor", "at"),
        Index("access_audit_log_theo_luc", "at"),
    )


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
