# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Bối cảnh của một lần chuyển trạng thái.
#
# Gói mọi thứ mà ràng buộc Poka-yoke cần biết để ra quyết định, để hàm kiểm tra
# không phải tự đi truy vấn cơ sở dữ liệu.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.case import Request
    from app.models.workflow_config import Transition


@dataclass(frozen=True, slots=True)
class Actor:
    """Người hoặc hệ thống đang thực hiện lần chuyển.

    Vai trò và phòng ban lấy từ token Keycloak — xem #43. Trước khi #43 xong, phía
    gọi tự truyền vào, và bộ kiểm thử cũng dựng bằng cách này.
    """

    id: str
    roles: frozenset[str] = frozenset()
    departments: frozenset[str] = frozenset()

    # Đánh dấu tác nhân hệ thống, ví dụ bộ đếm SLA tự leo thang ở #42. Chỉ tác nhân
    # này mới đi được cạnh `is_system`, và ngược lại nó không đi được cạnh của người.
    is_system: bool = False

    @classmethod
    def system(cls, name: str = "system") -> Actor:
        """Tác nhân hệ thống, dùng cho các cạnh tự động."""
        return cls(id=name, is_system=True)


@dataclass(frozen=True, slots=True)
class TransitionContext:
    """Mọi dữ liệu một ràng buộc Poka-yoke cần để phán quyết."""

    case: Request
    transition: Transition
    actor: Actor
    note: str | None = None

    # Các trường quyết định mà lần chuyển này muốn đặt, ví dụ
    # {"priority_code": "high", "department_code": "it"}.
    #
    # CHỈ chứa trường quyết định. Tầng I ghi vào trường gợi ý theo đường riêng, không
    # bao giờ đi qua đây — xem CLAUDE.md mục 4.3.
    changes: dict[str, Any] = field(default_factory=dict)
