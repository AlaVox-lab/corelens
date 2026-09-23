# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Danh sách người nhận được việc trong một phòng ban (#84).
#
# Chỗ nối giữa không gian `H` và `P`: danh bạ Keycloak biết AI ở phòng nào và mang vai
# trò gì, bộ quy tắc biết vai trò nào GIAO việc và vai trò nào NHẬN việc. Tệp này không
# chứa tên vai trò nào — cả hai tập đều suy từ bảng:
#
#   Giao việc — vai trò đi được một cạnh cho phép đặt `assignee_id`, tức cạnh mang
#               ràng buộc quản trường đó (#78). Hiện là trưởng phòng, ở hai cạnh nhận
#               việc và phân công lại.
#   Nhận việc — vai trò đi được cạnh người ra khỏi trạng thái mà cạnh giao việc dẫn
#               tới. Hồ sơ được giao thì vào `in-progress`, và ai làm tiếp được ở đó
#               thì người đó nhận được việc. Hiện là người xử lý.
#
# Đổi ma trận phân quyền trong `infra/seed/` là hai tập này đổi theo, không sửa mã.
#
# Không có danh sách này thì ô chọn người xử lý chỉ còn cách hiện chuỗi UUID — mà danh
# sách UUID thì không ai chọn được.

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor
from app.auth.directory import DirectoryUnavailable, KeycloakDirectory, get_directory
from app.db import get_session
from app.models.workflow_config import Department, Transition
from app.rules.guards import permitted_fields
from app.workflow.context import Actor
from app.workflow.engine import get_active_rule_set
from app.workflow.schemas import (
    NguoiNhanViecRa,
    NguoiNhanViecTrongPhongRa,
    PhongBanRa,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Giao việc"])

# Tên cột, không phải giá trị nghiệp vụ — cùng loại với các mã trường trong
# GUARD_REGISTRY. Cạnh nào cho đặt trường này thì do ràng buộc trong dữ liệu quyết.
_TRUONG_NGUOI_XU_LY = "assignee_id"


def _canh_giao_viec(session: Session, rule_set_id: int) -> list[Transition]:
    """Những cạnh người đi được và cho đặt người xử lý."""
    return [
        t
        for t in session.scalars(
            select(Transition).where(
                Transition.rule_set_id == rule_set_id,
                Transition.is_system.is_(False),
            )
        ).all()
        if _TRUONG_NGUOI_XU_LY in permitted_fields(t.guard_codes)
    ]


def vai_tro_giao_viec(session: Session, rule_set_id: int) -> frozenset[str]:
    """Vai trò được giao việc: đi được ít nhất một cạnh cho đặt người xử lý."""
    return frozenset().union(
        *(t.role_codes for t in _canh_giao_viec(session, rule_set_id))
    )


def vai_tro_nhan_viec(session: Session, rule_set_id: int) -> frozenset[str]:
    """Vai trò nhận được việc: đi được cạnh người ra khỏi trạng thái mà hồ sơ tới
    sau khi được giao.

    Cạnh hệ thống bị loại, vì hệ thống không phải người để giao việc cho.
    """
    dich = {t.to_state for t in _canh_giao_viec(session, rule_set_id)}
    if not dich:
        return frozenset()
    return frozenset().union(
        *(
            t.role_codes
            for t in session.scalars(
                select(Transition).where(
                    Transition.rule_set_id == rule_set_id,
                    Transition.is_system.is_(False),
                    Transition.from_state.in_(dich),
                )
            ).all()
        )
    )


@router.get(
    "/departments/{department_code}/assignees",
    response_model=NguoiNhanViecTrongPhongRa,
    responses={
        403: {"description": "Không mang vai trò giao việc, hoặc không thuộc phòng này"},
        404: {"description": "Phòng ban không tồn tại hoặc đã ngừng hoạt động"},
        503: {"description": "Danh bạ Keycloak không trả lời"},
    },
)
def nguoi_nhan_viec(
    department_code: str,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[Actor, Depends(current_actor)],
    danh_ba: Annotated[KeycloakDirectory, Depends(get_directory)],
) -> NguoiNhanViecTrongPhongRa:
    """Người trong phòng nhận được việc, kèm tên thật, cho ô chọn người xử lý.

    Chỉ người giao được việc mới gọi được, và chỉ cho phòng của chính mình: trưởng
    phòng Công nghệ thông tin không cần — và không nên — đọc được danh sách người của
    phòng Nhân sự.

    Danh bạ không trả lời thì trả 503 kèm lý do, không trả danh sách rỗng. Danh sách
    rỗng nghĩa là *phòng không có ai*, còn 503 nghĩa là *không biết phòng có ai* — gộp
    hai điều đó làm một là giả vờ ổn.
    """
    bo = get_active_rule_set(session)

    if not (actor.roles & vai_tro_giao_viec(session, bo.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ người giao được việc mới xem được danh sách này.",
        )
    if department_code not in actor.departments:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ xem được danh sách người của phòng mình.",
        )

    phong = session.scalars(
        select(Department).where(
            Department.code == department_code, Department.is_active
        )
    ).one_or_none()
    if phong is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không có phòng ban '{department_code}' đang hoạt động.",
        )

    try:
        thanh_vien = danh_ba.department_members(department_code)
    except DirectoryUnavailable as loi:
        logger.warning("Không tra được danh bạ phòng %s: %s", department_code, loi.message)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "directory-unavailable", "message": loi.message},
        ) from loi

    nhan_viec = vai_tro_nhan_viec(session, bo.id)
    return NguoiNhanViecTrongPhongRa(
        department=PhongBanRa(
            code=phong.code, label=phong.label, description=phong.description
        ),
        people=[
            NguoiNhanViecRa(id=p.id, name=p.name, username=p.username)
            for p in thanh_vien
            if p.roles & nhan_viec
        ],
    )
