# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Điểm cuối của buồng lái điều phối viên (#82).
#
# Điều phối viên là nút thắt của cả luồng: hồ sơ gửi lên nằm ở trạng thái đầu cho tới
# khi có người phân loại và chuyển về phòng ban. Không có buồng lái này thì cổng gửi
# yêu cầu (#44) chỉ đi được đúng một bước rồi dừng.
#
# HAI LOẠI QUYỀN, ĐỪNG TRỘN:
#
#   Nhìn thấy hồ sơ — cửa ở đây, bằng vai trò. Người gửi chỉ thấy hồ sơ của mình qua
#                     cổng #44; điều phối viên thấy mọi hồ sơ qua cổng này.
#   Đi một cạnh     — engine quyết, bằng bảng `transition_roles` và ràng buộc trên cạnh.
#                     Tầng này KHÔNG kiểm lại. Chú thích của `require_roles` cấm đúng
#                     chuyện đó, vì hai nguồn quyền sẽ lệch nhau.
#
# Cửa nhìn thấy cũng gác luôn điểm cuối chuyển trạng thái: không nhìn thấy hồ sơ thì
# không có lý do gì được thao tác trên nó, và nếu để trống thì một người gửi dò số định
# danh sẽ đọc được từ mã lỗi của engine rằng hồ sơ nào có thật.

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.auth.directory import KeycloakDirectory, get_directory
from app.db import get_session
from app.models.case import EventLog, Request
from app.models.workflow_config import (
    Department,
    Priority,
    RequestTypeRouting,
    State,
    Transition,
    TransitionRole,
)
from app.workflow.assignment import kiem_nguoi_duoc_giao
from app.workflow.contact import lien_he_nguoi_gui
from app.workflow.context import Actor
from app.workflow.engine import get_active_rule_set
from app.workflow.engine import perform_transition as thuc_hien_chuyen
from app.workflow.errors import TransitionError
from app.workflow.messages import MessageRejected, gui_loi_nhan
from app.workflow.routes import (
    _bang_trang_thai,
    _bao_loi,
    _bao_loi_nhan,
    _du_lieu_chi_tiet,
    _tom_tat,
)
from app.workflow.schemas import (
    ChuyenTrangThaiCoTruongVao,
    GuiLoiNhanVao,
    HangDoiRa,
    HoSoDieuPhoiRa,
    LienHeNguoiGuiRa,
    MucHangDoiRa,
    NhanCoMa,
    NhomHangDoiRa,
)

# Mã vai trò mở cửa buồng lái. Đây là tên duy nhất của một vai trò nằm trong tệp này:
# trạng thái nào vào hàng đợi, cạnh nào đi được, trường nào đặt được — tất cả đều tra
# từ bộ quy tắc. Cùng cách điểm cuối /sla/scan gác bằng `administrator`.
VAI_TRO_DIEU_PHOI = "classifier"

router = APIRouter(prefix="/coordination", tags=["Buồng lái điều phối"])

_Cua = Annotated[Actor, Depends(require_roles(VAI_TRO_DIEU_PHOI))]
_Phien = Annotated[Session, Depends(get_session)]


def vao_duoc_buong_lai(actor: Actor) -> bool:
    """Người này có mở được buồng lái không. Dùng cho thanh điều hướng qua `/me`.

    Để ở đây, cạnh mã vai trò, để giao diện không phải biết tên vai trò nào cả — nó
    chỉ đọc danh sách không gian làm việc mà dịch vụ trả về.
    """
    return VAI_TRO_DIEU_PHOI in actor.roles


def _trang_thai_hang_doi(session: Session, rule_set_id: int) -> list[State]:
    """Những trạng thái mà vai trò điều phối có cạnh đi ra — theo thứ tự hiển thị.

    Suy từ `transitions` và `transition_roles`, không liệt kê cứng. Doanh nghiệp giao
    thêm một cạnh cho điều phối viên trong `infra/seed/` thì trạng thái nguồn của cạnh
    đó tự vào hàng đợi.
    """
    nguon = (
        select(Transition.from_state)
        .join(TransitionRole, TransitionRole.transition_id == Transition.id)
        .where(
            Transition.rule_set_id == rule_set_id,
            Transition.is_system.is_(False),
            TransitionRole.role_code == VAI_TRO_DIEU_PHOI,
        )
    )
    return list(
        session.scalars(
            select(State)
            .where(State.rule_set_id == rule_set_id, State.code.in_(nguon))
            .order_by(State.display_order)
        ).all()
    )


def _luc_vao_trang_thai():
    """Lúc hồ sơ vào trạng thái hiện tại, dạng biểu thức SQL.

    Mỗi lần chuyển đều ghi một dòng nhật ký, nên dòng cuối cùng chính là lúc vào trạng
    thái hiện tại. Chưa có dòng nào thì hồ sơ vẫn ở trạng thái đầu từ lúc tạo.
    """
    return func.coalesce(
        select(func.max(EventLog.timestamp))
        .where(EventLog.case_id == Request.id)
        .scalar_subquery(),
        Request.created_at,
    )


def _nhan_co_ma(ban_ghi) -> NhanCoMa | None:
    return NhanCoMa(code=ban_ghi.code, label=ban_ghi.label) if ban_ghi else None


def _phong_goi_y(session: Session, ho_so: Request) -> Department | None:
    """Phòng ban mặc định cho loại yêu cầu của hồ sơ, nếu có."""
    if not ho_so.request_type_code:
        return None
    return session.scalars(
        select(Department)
        .join(RequestTypeRouting, RequestTypeRouting.department_code == Department.code)
        .where(
            RequestTypeRouting.request_type_code == ho_so.request_type_code,
            RequestTypeRouting.is_default,
            Department.is_active,
        )
    ).first()


def _dung_chi_tiet_dieu_phoi(
    session: Session, ho_so: Request, actor: Actor
) -> HoSoDieuPhoiRa:
    luc_vao = session.scalar(
        select(func.max(EventLog.timestamp)).where(EventLog.case_id == ho_so.id)
    )
    uu_tien = session.get(Priority, ho_so.priority_code) if ho_so.priority_code else None

    return HoSoDieuPhoiRa(
        **_du_lieu_chi_tiet(session, ho_so, actor),
        requester_label=ho_so.requester_label,
        priority=_nhan_co_ma(uu_tien),
        state_entered_at=luc_vao or ho_so.created_at,
        suggested_department=_nhan_co_ma(_phong_goi_y(session, ho_so)),
    )


# ---------------------------------------------------------------------------
# Hàng đợi
# ---------------------------------------------------------------------------


@router.get("/queue", response_model=HangDoiRa)
def hang_doi(
    session: _Phien,
    _: _Cua,
    state: Annotated[str | None, Query(description="Chỉ lấy một trạng thái")] = None,
) -> HangDoiRa:
    """Hồ sơ đang chờ điều phối viên, chờ lâu nhất lên đầu.

    Xếp theo thời gian chờ ở trạng thái hiện tại chứ không theo hạn SLA: đồng hồ SLA
    không chạy ở những trạng thái này — nó chỉ bắt đầu khi phòng ban nhận việc — nên ở
    đây không có khái niệm "sắp quá hạn". Thời gian chờ mới là con số thật.

    Chỉ lấy hồ sơ của bộ quy tắc đang kích hoạt. Khi doanh nghiệp đổi bộ quy tắc, hồ
    sơ cũ vẫn chạy theo bộ cũ, và hàng đợi của chúng sẽ cần xử lý riêng.
    """
    bo = get_active_rule_set(session)
    cac_trang_thai = _trang_thai_hang_doi(session, bo.id)
    ma_hang_doi = [t.code for t in cac_trang_thai]

    if state is not None and state not in ma_hang_doi:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "state-not-in-queue",
                "message": f"Trạng thái '{state}' không thuộc hàng đợi điều phối.",
            },
        )

    dem = dict(
        session.execute(
            select(Request.current_state, func.count())
            .where(Request.rule_set_id == bo.id, Request.current_state.in_(ma_hang_doi))
            .group_by(Request.current_state)
        ).all()
    )

    luc_vao = _luc_vao_trang_thai().label("luc_vao")
    dong = session.execute(
        select(Request, luc_vao)
        .where(
            Request.rule_set_id == bo.id,
            Request.current_state.in_([state] if state else ma_hang_doi),
        )
        .order_by(luc_vao.asc(), Request.id)
    ).all()

    states = _bang_trang_thai(session, bo.id)
    cac_muc = [
        MucHangDoiRa(
            **_tom_tat(session, ho_so, states),
            requester_label=ho_so.requester_label,
            priority=_nhan_co_ma(
                session.get(Priority, ho_so.priority_code) if ho_so.priority_code else None
            ),
            state_entered_at=vao,
        )
        for ho_so, vao in dong
    ]

    return HangDoiRa(
        groups=[
            NhomHangDoiRa(code=t.code, label=t.label, count=dem.get(t.code, 0))
            for t in cac_trang_thai
        ],
        items=cac_muc,
    )


# ---------------------------------------------------------------------------
# Hồ sơ
# ---------------------------------------------------------------------------


@router.get("/requests/{case_id}", response_model=HoSoDieuPhoiRa)
def chi_tiet(case_id: int, session: _Phien, actor: _Cua) -> HoSoDieuPhoiRa:
    """Chi tiết một hồ sơ bất kỳ, kèm những thao tác người này làm được lúc này.

    Mở được cả hồ sơ đã rời hàng đợi — ngay sau khi điều phối viên chuyển hồ sơ về
    phòng ban, giao diện đưa họ về lại trang này để thấy kết quả, và lúc đó hồ sơ đã
    không còn ở trạng thái của hàng đợi nữa.
    """
    ho_so = session.get(Request, case_id)
    if ho_so is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "case-not-found", "message": "Không tìm thấy hồ sơ."},
        )
    return _dung_chi_tiet_dieu_phoi(session, ho_so, actor)


@router.get(
    "/requests/{case_id}/requester-contact",
    response_model=LienHeNguoiGuiRa,
    responses={
        404: {"description": "Không có hồ sơ này"},
        503: {"description": "Danh bạ Keycloak không trả lời"},
    },
)
def lien_he(
    case_id: int,
    session: _Phien,
    _: _Cua,
    danh_ba: Annotated[KeycloakDirectory, Depends(get_directory)],
) -> LienHeNguoiGuiRa:
    """Email và số điện thoại của người gửi, tra từ danh bạ lúc gọi (#131).

    Cùng cửa với trang chi tiết: điều phối viên mở được mọi hồ sơ nên tra được liên hệ
    của mọi người gửi. Lý do tách thành điểm cuối riêng ở `app/workflow/contact.py`.
    """
    ho_so = session.get(Request, case_id)
    if ho_so is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "case-not-found", "message": "Không tìm thấy hồ sơ."},
        )
    return lien_he_nguoi_gui(danh_ba, ho_so)


@router.post("/requests/{case_id}/transitions", response_model=HoSoDieuPhoiRa)
def chuyen_trang_thai(
    case_id: int,
    du_lieu: ChuyenTrangThaiCoTruongVao,
    session: _Phien,
    actor: _Cua,
    danh_ba: Annotated[KeycloakDirectory, Depends(get_directory)],
) -> HoSoDieuPhoiRa:
    """Thực hiện một thao tác, CÓ kèm trường quyết định.

    Mọi phép kiểm nằm trong engine: cạnh có tồn tại không, vai trò có đi được không,
    trường gửi kèm có được cạnh này cho đặt không (#78), giá trị có trong danh mục
    không, và ràng buộc Poka-yoke trên cạnh. Tầng này chỉ dịch lỗi sang mã HTTP.

    Không nạp hồ sơ trước khi gọi engine — engine tự báo `case-not-found`. Nạp trước
    thì lệnh khóa dòng `SELECT FOR UPDATE` bên trong engine có nguy cơ không được phát.

    Điều phối viên không giao được người xử lý — không cạnh nào của họ cho đặt trường
    đó. Vẫn gọi phép kiểm người được giao, vì một người có thể mang cùng lúc vai trò
    điều phối và vai trò giao việc; bỏ qua ở đây là để hở một đường vòng quanh danh bạ.
    """
    ten_nguoi_duoc_giao = kiem_nguoi_duoc_giao(
        session,
        danh_ba,
        case_id=case_id,
        to_state=du_lieu.to_state,
        actor=actor,
        changes=du_lieu.changes,
    )
    try:
        ho_so = thuc_hien_chuyen(
            session,
            case_id=case_id,
            to_state=du_lieu.to_state,
            actor=actor,
            note=du_lieu.note,
            changes=du_lieu.changes,
            assignee_label=ten_nguoi_duoc_giao,
        )
    except TransitionError as loi:
        session.rollback()
        raise _bao_loi(loi) from loi

    session.commit()
    session.refresh(ho_so)
    return _dung_chi_tiet_dieu_phoi(session, ho_so, actor)


@router.post("/requests/{case_id}/messages", response_model=HoSoDieuPhoiRa)
def nhan_tin(
    case_id: int, du_lieu: GuiLoiNhanVao, session: _Phien, actor: _Cua
) -> HoSoDieuPhoiRa:
    """Gửi một lời nhắn trên hồ sơ (#128).

    Cùng cửa nhìn thấy với trang chi tiết: điều phối viên mở được mọi hồ sơ, nên nhắn
    được trên mọi hồ sơ — kể cả hồ sơ đã chuyển về phòng ban. Lời nhắn không đổi hồ sơ;
    xem app/workflow/messages.py.
    """
    ho_so = session.get(Request, case_id)
    if ho_so is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "case-not-found", "message": "Không tìm thấy hồ sơ."},
        )
    try:
        gui_loi_nhan(session, ho_so, actor, du_lieu.kind, du_lieu.body)
    except MessageRejected as loi:
        session.rollback()
        raise _bao_loi_nhan(loi) from loi

    session.commit()
    return _dung_chi_tiet_dieu_phoi(session, ho_so, actor)
