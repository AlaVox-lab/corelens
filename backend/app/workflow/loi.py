# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Cửa hồ sơ trung lập với vai của nền tảng lõi (#376, Mức 2).
#
# Dưới `/core/v1/workflow` có cùng ba đường với cổng người gửi — danh sách, chi tiết, bước chuyển — nhưng cửa
# nhìn thấy không còn là "hồ sơ do chính mình tạo". Một ứng dụng khác chạy quy trình của nó chỉ bằng API của
# lõi, nên người duyệt của ứng dụng đó cũng phải đi bước được qua lõi, không qua buồng lái của ứng dụng minh
# họa.
#
# KHÔNG CÓ BỘ KIỂM QUYỀN THỨ HAI Ở ĐÂY. Cùng hai loại quyền như hai buồng lái:
#
#   Nhìn thấy hồ sơ — hợp đúng ba cửa nhìn thấy đang có, bằng chính hàm của chúng:
#                       cổng người gửi   hồ sơ do người gọi tạo (`requester_id`)
#                       buồng lái phòng  người mang vai của phòng ban (`vao_duoc_phong_ban`) thấy hồ sơ của
#                                        phòng mình (`department_code` trong phòng của người gọi)
#                       buồng lái điều   người mở được buồng lái điều phối (`vao_duoc_buong_lai`) thấy mọi hồ
#                       phối             sơ
#                     Hồ sơ ngoài phạm vi trả 404, không 403 — không ai dò được hồ sơ nào có thật.
#   Đi một cạnh     — engine quyết, bằng bảng `transitions`, `transition_roles` và ràng buộc trên cạnh
#                     (`requester-owns-case`, `actor-in-case-department`, `actor-not-requester`…). Tầng này
#                     không kiểm lại.
#
# Nên một trưởng phòng đi được "Duyệt cấp một" trên đề xuất của phòng mình, không thấy đề xuất của phòng
# khác, và một người gửi gọi nhầm cạnh của trưởng phòng nhận 403 của engine. `allowed_transitions` của chi
# tiết hồ sơ tính theo người gọi, như ở mọi cửa khác.

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import or_, select, true
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor
from app.auth.directory import KeycloakDirectory, get_directory
from app.db import get_session
from app.models.case import Request
from app.workflow.context import Actor
from app.workflow.coordination import vao_duoc_buong_lai
from app.workflow.department import vao_duoc_phong_ban
from app.workflow.phan_trang import ThamSoTrang, tham_so_trang
from app.workflow.routes import (
    ThamSoQuyTrinh,
    _dung_chi_tiet,
    di_buoc,
    liet_ke_ho_so,
)
from app.workflow.schemas import BuocChuyenLoiVao, DanhSachHoSoRa, HoSoChiTietRa

router_loi_rieng = APIRouter()

_Phien = Annotated[Session, Depends(get_session)]
_TacNhan = Annotated[Actor, Depends(current_actor)]


def pham_vi_nhin_thay(session: Session, actor: Actor):
    """Điều kiện SQL: hồ sơ người gọi được thấy qua lõi — hợp của ba cửa nhìn thấy sẵn có (đầu tệp)."""
    if vao_duoc_buong_lai(actor):
        return true()
    cac_cua = [Request.requester_id == actor.id]
    if vao_duoc_phong_ban(session, actor):
        cac_cua.append(Request.department_code.in_(actor.departments))
    return or_(*cac_cua)


def _khong_thay() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "case-not-found", "message": "Không tìm thấy hồ sơ."},
    )


def _kiem_nhin_thay(session: Session, case_id: int, actor: Actor) -> None:
    """Chặn hồ sơ ngoài phạm vi bằng 404, đọc một cột chứ không nạp đối tượng: nạp trước thì lệnh khóa
    dòng `SELECT FOR UPDATE` bên trong engine có nguy cơ không được phát (cùng lý do `_kiem_chu_so_huu`)."""
    if session.scalar(
        select(Request.id).where(Request.id == case_id, pham_vi_nhin_thay(session, actor))
    ) is None:
        raise _khong_thay()


@router_loi_rieng.get("/requests", response_model=DanhSachHoSoRa)
def ho_so_trong_pham_vi(
    session: _Phien,
    actor: _TacNhan,
    trang: Annotated[ThamSoTrang, Depends(tham_so_trang)],
    q: Annotated[str | None, Query(description="Tìm theo mã, tiêu đề")] = None,
    state: Annotated[str | None, Query(description="Chỉ một trạng thái")] = None,
    request_type: Annotated[str | None, Query(description="Chỉ một loại yêu cầu")] = None,
    needs_action: Annotated[bool, Query(description="Chỉ hồ sơ đang chờ chính người gọi")] = False,
    process: ThamSoQuyTrinh = None,
) -> DanhSachHoSoRa:
    """Hồ sơ của một quy trình mà người gọi được thấy, mới nhất trước, có phân trang.

    Phạm vi theo vai, đúng luật của ba cửa nhìn thấy sẵn có: hồ sơ mình tạo; hồ sơ của phòng mình nếu mang
    vai phòng ban; mọi hồ sơ nếu là điều phối viên. `needs_action=true` lọc hồ sơ đang chờ chính người gọi
    làm bước chính — hàng việc của một người duyệt.
    """
    return liet_ke_ho_so(
        session, actor, trang, pham_vi_nhin_thay(session, actor),
        q=q, state=state, request_type=request_type, needs_action=needs_action, process=process,
    )


@router_loi_rieng.get("/requests/{case_id}", response_model=HoSoChiTietRa)
def chi_tiet_trong_pham_vi(case_id: int, session: _Phien, actor: _TacNhan) -> HoSoChiTietRa:
    """Chi tiết một hồ sơ trong phạm vi của người gọi, kèm lịch sử và `allowed_transitions` — những bước
    người gọi đi được lúc này, tính theo vai và ràng buộc của chính họ."""
    _kiem_nhin_thay(session, case_id, actor)
    return _dung_chi_tiet(session, session.get(Request, case_id), actor)


@router_loi_rieng.post("/requests/{case_id}/transitions", response_model=HoSoChiTietRa)
def buoc_chuyen_trong_pham_vi(
    case_id: int,
    du_lieu: BuocChuyenLoiVao,
    session: _Phien,
    actor: _TacNhan,
    danh_ba: Annotated[KeycloakDirectory, Depends(get_directory)],
    tac_vu_nen: BackgroundTasks,
) -> HoSoChiTietRa:
    """Đi một bước trên hồ sơ trong phạm vi của người gọi — mọi cạnh mà vai và phạm vi của người gọi đi
    được theo bảng `transitions`.

    Ngoài phạm vi: 404. Trong phạm vi mà cạnh không có, sai vai hay vướng ràng buộc: lỗi của engine
    (409, 403, 422) — cùng mã như ở mọi cửa khác.
    """
    _kiem_nhin_thay(session, case_id, actor)
    ho_so = di_buoc(
        session, danh_ba, tac_vu_nen, actor, case_id,
        to_state=du_lieu.to_state, note=du_lieu.note, changes=du_lieu.changes,
    )
    return _dung_chi_tiet(session, ho_so, actor)
