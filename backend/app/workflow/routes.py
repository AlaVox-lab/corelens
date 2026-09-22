# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Điểm cuối nghiệp vụ cho cổng người dùng (#44).
#
# Mọi lần đổi trạng thái ở đây đều gọi `perform_transition` — điểm chuyển trạng thái
# duy nhất. Không điểm cuối nào tự gán `current_state`, kể cả khi nó "chỉ sửa một
# trường". Xem ARCHITECTURE.md mục 6.1.
#
# Cổng này phục vụ **người tạo yêu cầu**: chỉ thấy hồ sơ của chính mình. Buồng lái cho
# điều phối viên và người xử lý là #45, với bộ điểm cuối riêng.

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor
from app.models.case import EventLog, Request
from app.models.workflow_config import Department, RequestType, State, Transition
from app.rules.sla import da_chay_giay, gioi_han_giay
from app.workflow.context import Actor
from app.workflow.engine import (
    allowed_transitions,
    case_history,
    create_case,
    get_active_rule_set,
)
from app.workflow.engine import perform_transition as thuc_hien_chuyen
from app.workflow.errors import (
    CaseNotFound,
    FieldNotPermitted,
    GuardViolation,
    NoteRequired,
    RoleNotPermitted,
    SystemTransitionOnly,
    TransitionError,
    TransitionNotAllowed,
)
from app.workflow.schemas import (
    CanhDiDuocRa,
    ChuyenTrangThaiVao,
    HoSoChiTietRa,
    HoSoTomTatRa,
    LoaiYeuCauRa,
    NhanCoMa,
    SuKienRa,
    TaoHoSoVao,
    TrangThaiRa,
)
from app.db import get_session

router = APIRouter(tags=["Yêu cầu"])

# Mã lỗi của engine ánh xạ sang mã HTTP. Giữ ở một chỗ để mọi điểm cuối trả lời giống
# nhau, và để #45 dùng lại được.
MA_HTTP = {
    CaseNotFound: status.HTTP_404_NOT_FOUND,
    TransitionNotAllowed: status.HTTP_409_CONFLICT,
    RoleNotPermitted: status.HTTP_403_FORBIDDEN,
    SystemTransitionOnly: status.HTTP_403_FORBIDDEN,
    # Dùng số trực tiếp: tên hằng 422 của Starlette đổi giữa các phiên bản
    GuardViolation: 422,
    NoteRequired: 422,
    FieldNotPermitted: 422,
}


def _bao_loi(loi: TransitionError) -> HTTPException:
    """Dịch lỗi engine thành phản hồi HTTP, giữ nguyên mã máy đọc được."""
    return HTTPException(
        status_code=MA_HTTP.get(type(loi), status.HTTP_400_BAD_REQUEST),
        detail={"code": loi.code, "message": loi.message},
    )


def _ma_ho_so(ho_so: Request) -> str:
    """Mã hiển thị cho người dùng, ví dụ `YC-2026-0184`.

    Dựng từ năm tạo và định danh tuần tự thay vì thêm một cột: một cột mã riêng sẽ cần
    bộ sinh số và cơ chế chống trùng, mà không đổi lại lợi ích nào ở quy mô này.
    """
    return f"YC-{ho_so.created_at.year}-{ho_so.id:04d}"


def _bang_trang_thai(session: Session, rule_set_id: int) -> dict[str, State]:
    return {
        s.code: s
        for s in session.scalars(
            select(State).where(State.rule_set_id == rule_set_id)
        ).all()
    }


def _nhan(gia_tri, mac_dinh: str = "") -> str:
    return getattr(gia_tri, "label", mac_dinh) if gia_tri is not None else mac_dinh


def _tom_tat(session: Session, ho_so: Request, states: dict[str, State]) -> dict:
    """Phần dùng chung giữa danh sách và chi tiết."""
    trang_thai = states[ho_so.current_state]

    loai = (
        session.get(RequestType, ho_so.request_type_code)
        if ho_so.request_type_code
        else None
    )
    phong = (
        session.get(Department, ho_so.department_code)
        if ho_so.department_code
        else None
    )

    gioi_han = gioi_han_giay(session, ho_so)
    da_chay = da_chay_giay(session, ho_so)

    return {
        "id": ho_so.id,
        "code": _ma_ho_so(ho_so),
        "title": ho_so.title,
        "request_type": (
            NhanCoMa(code=loai.code, label=loai.label) if loai else None
        ),
        "department": (
            NhanCoMa(code=phong.code, label=phong.label) if phong else None
        ),
        "state": TrangThaiRa(
            code=trang_thai.code,
            label=trang_thai.label,
            is_terminal=trang_thai.is_terminal,
        ),
        "created_at": ho_so.created_at,
        "updated_at": ho_so.updated_at,
        "sla_running_seconds": da_chay,
        "sla_paused_seconds": ho_so.sla_paused_seconds,
        "sla_limit_seconds": gioi_han,
        "sla_overdue": gioi_han is not None and da_chay > gioi_han,
        # Đồng hồ đang tạm dừng: đã khởi động nhưng trạng thái hiện tại không đếm giờ
        "sla_paused": (
            ho_so.sla_segment_since is not None and not trang_thai.sla_running
        ),
    }


def _su_kien(e: EventLog, states: dict[str, State], canh: dict[str, str]) -> SuKienRa:
    return SuKienRa(
        timestamp=e.timestamp,
        activity=e.activity,
        activity_label=canh.get(f"{e.from_state}->{e.to_state}"),
        actor=e.actor,
        actor_label=e.actor_label or e.actor,
        # Tác nhân hệ thống không có tên người. Nhận ra bằng cột đã ghi lúc hành động,
        # không đoán theo mã định danh.
        is_system=(e.actor_label == "Hệ thống"),
        from_state=e.from_state,
        from_state_label=_nhan(states.get(e.from_state), e.from_state),
        to_state=e.to_state,
        to_state_label=_nhan(states.get(e.to_state), e.to_state),
        note=e.note,
    )


def _lay_ho_so_cua_toi(session: Session, case_id: int, actor: Actor) -> Request:
    """Đọc một hồ sơ, chặn nếu không phải của người đang gọi.

    Cổng này chỉ cho người tạo xem hồ sơ của chính mình. Trả 404 chứ không 403 khi hồ
    sơ thuộc người khác: 403 sẽ xác nhận rằng hồ sơ đó tồn tại, để lộ thông tin cho ai
    dò số định danh.
    """
    ho_so = session.get(Request, case_id)
    if ho_so is None or ho_so.requester_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "case-not-found", "message": "Không tìm thấy hồ sơ."},
        )
    return ho_so


def _kiem_chu_so_huu(session: Session, case_id: int, actor: Actor) -> None:
    """Kiểm quyền xem hồ sơ mà KHÔNG nạp đối tượng vào phiên.

    Dùng trước khi gọi `perform_transition`. Nếu dùng `_lay_ho_so_cua_toi` ở đó, hồ sơ
    sẽ nằm sẵn trong bản đồ định danh của phiên, và lệnh khóa dòng `SELECT FOR UPDATE`
    bên trong engine có nguy cơ không được phát đi — mất luôn lớp chống hai yêu cầu
    đồng thời cùng chuyển một hồ sơ.
    """
    chu_so_huu = session.scalar(
        select(Request.requester_id).where(Request.id == case_id)
    )
    if chu_so_huu is None or chu_so_huu != actor.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "case-not-found", "message": "Không tìm thấy hồ sơ."},
        )


# ---------------------------------------------------------------------------
# Danh mục
# ---------------------------------------------------------------------------


@router.get("/request-types", response_model=list[LoaiYeuCauRa])
def danh_muc_loai_yeu_cau(
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[Actor, Depends(current_actor)],
) -> list[LoaiYeuCauRa]:
    """Bốn loại yêu cầu cho biểu mẫu gửi.

    Giao diện **phải** dựng danh sách từ đây chứ không viết cứng bốn lựa chọn, vì doanh
    nghiệp triển khai sẽ khai lại danh mục của họ — xem ARCHITECTURE.md mục 5.1.
    """
    cac_loai = session.scalars(
        select(RequestType)
        .where(RequestType.is_active)
        .order_by(RequestType.display_order)
    ).all()
    return [
        LoaiYeuCauRa(
            code=l.code,
            label=l.label,
            description=l.description,
            sla_hours=l.sla_hours,
        )
        for l in cac_loai
    ]


@router.get("/states", response_model=list[TrangThaiRa])
def danh_muc_trang_thai(
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[Actor, Depends(current_actor)],
) -> list[TrangThaiRa]:
    """Toàn bộ trạng thái của bộ quy tắc đang kích hoạt, theo thứ tự hiển thị.

    Khác `state` trong từng hồ sơ ở chỗ đây là **danh mục**: giao diện cần nó để vẽ
    bảng chú giải, chứ không phải để biết một hồ sơ cụ thể đang ở đâu. Không lấy được
    danh mục này từ danh sách hồ sơ, vì người dùng mới chỉ đi qua vài trạng thái trong
    số đó — mà bảng chú giải phải giải thích cả những trạng thái họ chưa gặp.
    """
    bo_quy_tac = get_active_rule_set(session)
    cac_trang_thai = session.scalars(
        select(State)
        .where(State.rule_set_id == bo_quy_tac.id)
        .order_by(State.display_order)
    ).all()
    return [
        TrangThaiRa(code=s.code, label=s.label, is_terminal=s.is_terminal)
        for s in cac_trang_thai
    ]


# ---------------------------------------------------------------------------
# Hồ sơ
# ---------------------------------------------------------------------------


@router.post("/requests", response_model=HoSoChiTietRa, status_code=201)
def tao_ho_so(
    du_lieu: TaoHoSoVao,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[Actor, Depends(current_actor)],
) -> HoSoChiTietRa:
    """Gửi một yêu cầu mới.

    Trạng thái đầu tiên do engine tra từ cờ `is_initial`, không do điểm cuối này chọn.

    Mức ưu tiên và phòng ban để trống — người phân loại đặt sau. Loại yêu cầu thì
    người gửi chọn ngay trên biểu mẫu, và người phân loại sửa lại được nếu chọn sai.
    """
    try:
        ho_so = create_case(
            session,
            title=du_lieu.title,
            description=du_lieu.description,
            requester_id=actor.id,
            request_type_code=du_lieu.request_type_code,
        )
    except ValueError as loi:
        # Danh mục đổi giữa lúc giao diện nạp biểu mẫu và lúc người dùng bấm gửi. Trả
        # 422 kèm mã máy đọc được để cổng mời chọn lại, thay vì để khóa ngoại nổ ra
        # thành 500 lúc ghi xuống cơ sở dữ liệu.
        raise HTTPException(
            status_code=422,
            detail={"code": "unknown-request-type", "message": str(loi)},
        ) from loi

    session.commit()
    session.refresh(ho_so)
    return _dung_chi_tiet(session, ho_so, actor)


@router.get("/requests", response_model=list[HoSoTomTatRa])
def ho_so_cua_toi(
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[Actor, Depends(current_actor)],
) -> list[HoSoTomTatRa]:
    """Danh sách hồ sơ của người đang đăng nhập, mới nhất trước."""
    cac_ho_so = session.scalars(
        select(Request)
        .where(Request.requester_id == actor.id)
        .order_by(Request.created_at.desc())
    ).all()

    if not cac_ho_so:
        return []

    states = _bang_trang_thai(session, cac_ho_so[0].rule_set_id)
    return [HoSoTomTatRa(**_tom_tat(session, h, states)) for h in cac_ho_so]


@router.get("/requests/{case_id}", response_model=HoSoChiTietRa)
def chi_tiet_ho_so(
    case_id: int,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[Actor, Depends(current_actor)],
) -> HoSoChiTietRa:
    """Chi tiết một hồ sơ, kèm dòng thời gian và những thao tác làm được lúc này."""
    ho_so = _lay_ho_so_cua_toi(session, case_id, actor)
    return _dung_chi_tiet(session, ho_so, actor)


@router.post("/requests/{case_id}/transitions", response_model=HoSoChiTietRa)
def chuyen_trang_thai(
    case_id: int,
    du_lieu: ChuyenTrangThaiVao,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[Actor, Depends(current_actor)],
) -> HoSoChiTietRa:
    """Thực hiện một thao tác trên hồ sơ.

    Điểm cuối này **không tự kiểm quyền**. Engine đã tra bảng `transitions` và ma trận
    phân quyền rồi; kiểm thêm một lớp ở đây sẽ tạo ra nguồn sự thật thứ hai, và hai
    nguồn sẽ lệch nhau. Việc duy nhất ở đây là dịch lỗi engine sang mã HTTP.
    """
    _kiem_chu_so_huu(session, case_id, actor)

    try:
        ho_so = thuc_hien_chuyen(
            session,
            case_id=case_id,
            to_state=du_lieu.to_state,
            actor=actor,
            note=du_lieu.note,
        )
    except TransitionError as loi:
        session.rollback()
        raise _bao_loi(loi) from loi

    session.commit()
    session.refresh(ho_so)
    return _dung_chi_tiet(session, ho_so, actor)


def _dung_chi_tiet(session: Session, ho_so: Request, actor: Actor) -> HoSoChiTietRa:
    states = _bang_trang_thai(session, ho_so.rule_set_id)

    # Nhãn hoạt động tra theo cặp trạng thái vì nhiều cạnh dùng chung `activity_code`
    # — bốn cạnh hủy chẳng hạn.
    canh = {
        f"{t.from_state}->{t.to_state}": t.activity_label
        for t in session.scalars(
            select(Transition).where(Transition.rule_set_id == ho_so.rule_set_id)
        ).all()
    }

    di_duoc = [
        CanhDiDuocRa(
            to_state=t.to_state,
            to_state_label=_nhan(states.get(t.to_state), t.to_state),
            activity_code=t.activity_code,
            activity_label=t.activity_label,
            requires_note=t.requires_note,
        )
        for t in allowed_transitions(session, ho_so, actor)
    ]

    return HoSoChiTietRa(
        **_tom_tat(session, ho_so, states),
        description=ho_so.description,
        requester_id=ho_so.requester_id,
        assignee_id=ho_so.assignee_id,
        history=[_su_kien(e, states, canh) for e in case_history(session, ho_so.id)],
        allowed_transitions=di_duoc,
    )
