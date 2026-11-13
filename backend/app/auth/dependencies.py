# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Phụ thuộc FastAPI cho phần định danh.
#
# Điểm cuối nào cần biết người gọi là ai thì khai `actor: Actor = Depends(current_actor)`.
# Không điểm cuối nào được tự đọc header `Authorization` — đi vòng qua đây là bỏ qua
# việc kiểm chữ ký.

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.identity import actor_from_claims
from app.auth.tokens import TokenInvalid, verify_token
from app.db import get_session
from app.workflow.context import Actor
from app.workflow.uy_quyen import ap_uy_quyen

# Vai trò vận hành cụm: gác màn Hệ thống, lệnh quét SLA bằng tay, số đo và màn quản trị cấu hình
# (#255). Mã trùng vai trò realm trong Keycloak và dòng `roles` của dữ liệu khởi tạo.
VAI_TRO_QUAN_TRI = "administrator"

# `auto_error=False` để tự soạn thông điệp tiếng Việt thay vì để FastAPI trả chuỗi
# tiếng Anh mặc định.
_bearer = HTTPBearer(auto_error=False, scheme_name="Keycloak")


def current_claims(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict:
    """Phần claim đã kiểm chữ ký của token trong header `Authorization`."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu token truy cập.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return verify_token(credentials.credentials)
    except TokenInvalid as loi:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=loi.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from loi


def current_actor(
    claims: Annotated[dict, Depends(current_claims)],
    session: Annotated[Session, Depends(get_session)],
) -> Actor:
    """Tác nhân nghiệp vụ tương ứng với token, sẵn sàng đưa thẳng vào engine.

    Gộp sẵn ủy quyền đang hiệu lực mà người này được nhận (#252) — xem app/workflow/uy_quyen.py.
    FastAPI dùng chung một phiên cơ sở dữ liệu cho mọi phụ thuộc `get_session` của cùng yêu cầu, nên
    điểm cuối và lần tra ủy quyền đọc cùng một phiên.
    """
    return ap_uy_quyen(session, actor_from_claims(claims))


def require_roles(*vai_tro_can: str):
    """Dựng một phụ thuộc đòi người gọi mang ít nhất một trong các vai trò nêu ra.

    Dùng cho những điểm cuối không thuộc luồng chuyển trạng thái — ví dụ màn hình
    quản trị phòng ban, chỉ `administrator` vào được.

    **Không dùng cho việc chuyển trạng thái.** Ở đó quyền đã nằm trong bảng
    `transition_roles`, và engine tự kiểm. Kiểm thêm một lớp ở tầng định tuyến sẽ tạo
    ra nguồn sự thật thứ hai, và hai nguồn sẽ lệch nhau.
    """
    can = frozenset(vai_tro_can)

    def kiem_tra(actor: Annotated[Actor, Depends(current_actor)]) -> Actor:
        if not (actor.roles & can):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cần một trong các vai trò: {', '.join(sorted(can))}.",
            )
        return actor

    return kiem_tra
