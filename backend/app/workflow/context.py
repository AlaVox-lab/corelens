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
class LamThay:
    """Một ủy quyền đang hiệu lực mà tác nhân là người được ủy quyền (#252).

    Người được ủy quyền mang thêm `vai` của người vắng, nhưng chỉ dùng được trong phòng `phong`:
    engine tự kiểm phòng của hồ sơ khi một bước chỉ đi được nhờ vai làm thay.
    """

    ma: int
    nguoi_vang_id: str
    nguoi_vang_label: str
    phong: str
    vai: frozenset[str]


@dataclass(frozen=True, slots=True)
class Actor:
    """Người hoặc hệ thống đang thực hiện lần chuyển.

    Vai trò và phòng ban lấy từ token Keycloak — xem #43. Trước khi #43 xong, phía
    gọi tự truyền vào, và bộ kiểm thử cũng dựng bằng cách này.
    """

    id: str
    roles: frozenset[str] = frozenset()
    departments: frozenset[str] = frozenset()

    # Tên hiển thị tại thời điểm hành động, lấy từ claim `name` của token.
    #
    # Ghi vào nhật ký sự kiện chứ không tra ngược từ Keycloak lúc đọc: người nghỉ việc
    # thì tài khoản bị xóa, người đổi tên thì lịch sử sẽ kể sai. Nhật ký kiểm toán phải
    # giữ được sự thật của lúc đó, kể cả khi nguồn danh tính đã đổi.
    name: str | None = None

    # Đánh dấu tác nhân hệ thống, ví dụ bộ đếm SLA tự leo thang ở #42. Chỉ tác nhân
    # này mới đi được cạnh `is_system`, và ngược lại nó không đi được cạnh của người.
    is_system: bool = False

    # Ủy quyền đang hiệu lực mà người này được nhận (#252). `roles` đã gộp vai làm thay; `vai_goc`
    # giữ vai của chính người này trong token, để engine biết một bước đi được nhờ vai riêng hay chỉ
    # nhờ ủy quyền — chỉ trường hợp sau mới ghi "thay mặt". `None` nghĩa là không có ủy quyền nào.
    lam_thay: tuple[LamThay, ...] = ()
    vai_goc: frozenset[str] | None = None

    @property
    def vai_rieng(self) -> frozenset[str]:
        """Vai của chính người này, không tính vai nhận qua ủy quyền."""
        return self.roles if self.vai_goc is None else self.vai_goc

    @property
    def label(self) -> str:
        """Tên để hiển thị. Lùi về mã định danh khi token không mang tên."""
        if self.is_system:
            return "Hệ thống"
        return self.name or self.id

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

    # Trạng thái hồ sơ đã ở ngay trước trạng thái hiện tại, engine đọc từ nhật ký sự
    # kiện (#79). `None` khi hồ sơ chưa rời trạng thái bắt đầu lần nào. Engine tra sẵn
    # để ràng buộc vẫn không phải tự truy vấn — cùng lý do với cả lớp này.
    previous_state: str | None = None
