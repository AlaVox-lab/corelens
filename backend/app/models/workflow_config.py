# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ánh xạ các bảng cấu hình của engine máy trạng thái.
#
# CHỈ ĐỌC từ phía mã nguồn. Mười ba bảng này do
# infra/postgres/init/02-luoc-do-quy-trinh.sql tạo và infra/seed/ nạp dữ liệu,
# nên Alembic được cấu hình bỏ qua chúng — xem alembic/env.py.
#
# Sửa quy trình nghiệp vụ nghĩa là sửa dữ liệu trong infra/seed/, không sửa tệp này.

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class RuleSet(Base):
    """Phiên bản bộ quy tắc. Hồ sơ cũ chạy theo quy tắc cũ."""

    __tablename__ = "rule_sets"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    version: Mapped[str] = mapped_column(Text, unique=True)
    label: Mapped[str] = mapped_column(Text)
    effective_from: Mapped[dt.datetime]
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text, default=None)


class Role(Base):
    """Vai trò nghiệp vụ. Mã trùng tên vai trò realm trong Keycloak."""

    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    label: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    display_order: Mapped[int] = mapped_column(SmallInteger, default=0)


class State(Base):
    """Một trạng thái trong vòng đời hồ sơ."""

    __tablename__ = "states"

    rule_set_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("rule_sets.id"), primary_key=True
    )
    code: Mapped[str] = mapped_column(Text, primary_key=True)
    label: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    is_initial: Mapped[bool] = mapped_column(Boolean, default=False)
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False)

    # Đồng hồ SLA có chạy khi hồ sơ nằm ở trạng thái này không. Một cột này trả lời
    # cả hai câu: đồng hồ bắt đầu từ đâu, và dừng ở đâu.
    sla_running: Mapped[bool] = mapped_column(Boolean, default=False)

    display_order: Mapped[int] = mapped_column(SmallInteger, default=0)


class Transition(Base):
    """Một cạnh hợp lệ giữa hai trạng thái.

    Không có dòng nghĩa là không đi được. Đây là nơi ràng buộc Poka-yoke
    "đã nhận là không trả về" được thực thi — bằng sự vắng mặt, không bằng câu lệnh if.
    """

    __tablename__ = "transitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_set_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("rule_sets.id"))
    from_state: Mapped[str] = mapped_column(Text)
    to_state: Mapped[str] = mapped_column(Text)
    activity_code: Mapped[str] = mapped_column(Text)
    activity_label: Mapped[str] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_note: Mapped[bool] = mapped_column(Boolean, default=False)
    # Tên ô ghi chú của cạnh này (#79). Trống thì giao diện gọi nó là "Lý do"; cạnh bổ
    # sung thông tin gọi nó là "Thông tin bổ sung", vì ở đó ghi chú là câu trả lời chứ
    # không phải lời giải thích.
    note_label: Mapped[str | None] = mapped_column(Text, default=None)
    display_order: Mapped[int] = mapped_column(SmallInteger, default=0)
    # Cạnh làm lại (#153): đi qua là hồ sơ bị đẩy ngược để làm lại. Dòng thời gian đếm
    # quay lui theo cờ này — xem lược đồ khởi tạo.
    is_rework: Mapped[bool] = mapped_column(Boolean, default=False)

    # Cột kỹ thuật luôn bằng FALSE, tồn tại để khóa ngoại tổng hợp chặn việc tạo
    # cạnh rời khỏi một trạng thái kết thúc. Mã nguồn không bao giờ đọc hay ghi nó.
    from_is_terminal: Mapped[bool] = mapped_column(Boolean, default=False)

    allowed_roles: Mapped[list[TransitionRole]] = relationship(
        back_populates="transition", lazy="selectin"
    )
    guards: Mapped[list[TransitionGuard]] = relationship(
        back_populates="transition", lazy="selectin"
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["rule_set_id", "to_state"], ["states.rule_set_id", "states.code"]
        ),
    )

    @property
    def role_codes(self) -> set[str]:
        """Tập vai trò đi được cạnh này. Rỗng nghĩa là chỉ hệ thống đi được."""
        return {r.role_code for r in self.allowed_roles}

    @property
    def guard_codes(self) -> list[str]:
        """Danh sách mã ràng buộc phải chạy trước khi cho đi cạnh này."""
        return [g.guard_code for g in self.guards]

    def __repr__(self) -> str:
        return f"<Transition {self.from_state} -> {self.to_state} ({self.activity_code})>"


class TransitionRole(Base):
    """Ma trận phân quyền: vai trò nào đi được cạnh nào."""

    __tablename__ = "transition_roles"

    transition_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transitions.id"), primary_key=True
    )
    role_code: Mapped[str] = mapped_column(
        Text, ForeignKey("roles.code"), primary_key=True
    )

    transition: Mapped[Transition] = relationship(back_populates="allowed_roles")


class Guard(Base):
    """Một loại ràng buộc Poka-yoke kiểm tra lúc chạy.

    Mã guard là hợp đồng giữa dữ liệu và mã nguồn: bảng này khai báo mã, còn
    app/rules/guards.py cài đặt hàm kiểm tra tương ứng. Mã có trong bảng mà thiếu
    hàm cài đặt sẽ làm engine từ chối chuyển trạng thái, không im lặng bỏ qua.
    """

    __tablename__ = "guards"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    label: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)


class TransitionGuard(Base):
    """Gán một ràng buộc Poka-yoke cho một cạnh cụ thể."""

    __tablename__ = "transition_guards"

    transition_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transitions.id"), primary_key=True
    )
    guard_code: Mapped[str] = mapped_column(
        Text, ForeignKey("guards.code"), primary_key=True
    )

    transition: Mapped[Transition] = relationship(back_populates="guards")


class Priority(Base):
    """Mức độ ưu tiên. Người tạo yêu cầu không bao giờ tự đặt được."""

    __tablename__ = "priorities"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    label: Mapped[str] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    display_order: Mapped[int] = mapped_column(SmallInteger, default=0)


class Department(Base):
    """Phòng ban. Doanh nghiệp triển khai tự khai lại theo cơ cấu của mình."""

    __tablename__ = "departments"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    label: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(SmallInteger, default=0)


class RequestType(Base):
    """Loại yêu cầu, kèm ngưỡng SLA riêng."""

    __tablename__ = "request_types"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    label: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    sla_hours: Mapped[int] = mapped_column(Integer)
    # Ân hạn sau mỗi lần hồ sơ vào lại trạng thái đếm giờ — xem rules/sla.py (#94)
    sla_grace_hours: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(SmallInteger, default=0)


class RequestTypeRouting(Base):
    """Ánh xạ loại yêu cầu sang phòng ban phụ trách."""

    __tablename__ = "request_type_routing"

    request_type_code: Mapped[str] = mapped_column(
        String, ForeignKey("request_types.code"), primary_key=True
    )
    department_code: Mapped[str] = mapped_column(
        String, ForeignKey("departments.code"), primary_key=True
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)


class MessageKind(Base):
    """Một loại lời nhắn trên hồ sơ (#128, ADR-0005).

    Lời nhắn không đổi hồ sơ nên không phải cạnh. Ai nhắn được trên hồ sơ nào do cửa
    nhìn thấy của từng buồng lái quyết — ai mở được hồ sơ thì nhắn được. Bảng này chỉ thu
    hẹp thêm, theo vai trò và theo các cờ dưới đây.
    """

    __tablename__ = "message_kinds"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    label: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    # Chỉ người gửi của chính hồ sơ gửi được — như ràng buộc requester-owns-case
    owner_only: Mapped[bool] = mapped_column(Boolean, default=False)
    # Chỉ gửi được khi hồ sơ nằm trong hàng đợi phòng ban, tập trạng thái suy từ bộ quy tắc
    department_stage_only: Mapped[bool] = mapped_column(Boolean, default=False)
    # Gửi lại chỉ được khi phía bên kia đã trả lời, hoặc đã quá chừng này giờ
    reask_after_hours: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    body_required: Mapped[bool] = mapped_column(Boolean, default=True)
    # Trò chuyện nội bộ (#156): người gửi của hồ sơ không thấy, không gửi được — theo hồ
    # sơ, không theo vai trò
    hidden_from_requester: Mapped[bool] = mapped_column(Boolean, default=False)
    display_order: Mapped[int] = mapped_column(SmallInteger, default=0)

    allowed_roles: Mapped[list[MessageKindRole]] = relationship(lazy="selectin")

    @property
    def role_codes(self) -> set[str]:
        """Tập vai trò gửi được loại lời nhắn này."""
        return {r.role_code for r in self.allowed_roles}


class MessageKindRole(Base):
    """Vai trò nào gửi được loại lời nhắn nào."""

    __tablename__ = "message_kind_roles"

    kind_code: Mapped[str] = mapped_column(
        Text, ForeignKey("message_kinds.code"), primary_key=True
    )
    role_code: Mapped[str] = mapped_column(
        Text, ForeignKey("roles.code"), primary_key=True
    )
