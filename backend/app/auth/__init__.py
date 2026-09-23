# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab

"""[H] Định danh, đăng nhập, phân quyền theo vai trò.

Keycloak là nguồn sự thật về danh tính; gói này chỉ kiểm chữ ký token và dịch phần
claim thành `Actor` mà không gian `P` hiểu được. Không lưu mật khẩu, không lưu phiên
làm việc, không gọi ngược sang Keycloak ở mỗi yêu cầu — xem ADR-0001.

Ngoại lệ duy nhất là danh bạ (`directory.py`, #84): tra tên người trong một phòng ban
khi trưởng phòng mở ô chọn người xử lý. Chỉ chạy lúc đó, không ở mỗi yêu cầu.
"""

from app.auth.dependencies import current_actor, current_claims, require_roles
from app.auth.directory import (
    DirectoryUnavailable,
    KeycloakDirectory,
    Person,
    get_directory,
)
from app.auth.identity import actor_from_claims
from app.auth.tokens import TokenInvalid, verify_token

__all__ = [
    "DirectoryUnavailable",
    "KeycloakDirectory",
    "Person",
    "TokenInvalid",
    "actor_from_claims",
    "current_actor",
    "current_claims",
    "get_directory",
    "require_roles",
    "verify_token",
]
