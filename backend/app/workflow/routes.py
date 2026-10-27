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

import json

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor
from app.auth.directory import KeycloakDirectory, get_directory
from app.models.case import EventLog, Request
from app.models.workflow_config import (
    Department,
    MessageKind,
    Priority,
    RequestType,
    RequestTypeField,
    State,
    Transition,
)
from app.rules.guards import permitted_fields
from app.rules.han_cho import tu_dong
from app.rules.sla import (
    an_han_con_lai_giay,
    da_chay_giay,
    gioi_han_giay,
    han_chot,
    sap_het_han,
)
from app.workflow.assignment import kiem_nguoi_duoc_giao
from app.rules.truong_rieng import truong_cua_loai
from app.workflow.context import Actor
from app.workflow.attachments import danh_sach_tep
from app.workflow.engine import (
    CHANGEABLE_FIELDS,
    DANH_MUC_CUA_TRUONG,
    allowed_transitions,
    case_history,
    create_case,
    kiem_ho_so_goc,
    my_primary_steps,
    get_active_rule_set,
)
from app.workflow.engine import perform_transition as thuc_hien_chuyen
from app.workflow.errors import (
    CaseNotFound,
    FieldNotPermitted,
    GuardViolation,
    InvalidFieldValue,
    NoteRequired,
    RoleNotPermitted,
    SystemTransitionOnly,
    TransitionError,
    TransitionNotAllowed,
)
from app.workflow.messages import (
    MessageRejected,
    cac_loi_nhan,
    loai_gui_duoc,
    loi_nhan_cuoi_tu_nguoi_gui,
    thay_noi_bo,
)
from app.workflow.messages import gui_loi_nhan as ghi_loi_nhan
from app.workflow.schemas import (
    TruongRiengRa,
    CanhDiDuocRa,
    ChuyenTrangThaiVao,
    GuiLoiNhanVao,
    HoSoChiTietRa,
    HoSoLienQuanRa,
    HoSoTomTatRa,
    LoaiLoiNhanRa,
    LoaiYeuCauRa,
    LoiNhanRa,
    MucUuTienRa,
    NhanCoMa,
    PhongBanRa,
    SuKienRa,
    TaoHoSoVao,
    TepDinhKemRa,
    ThayDoiTruongRa,
    TrangThaiRa,
    TuDongRa,
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
    InvalidFieldValue: 422,
}


# Thứ tự ô nhập trong bảng thao tác (#152). Ràng buộc trên cạnh chỉ nói cạnh được đặt
# TRƯỜNG NÀO — một tập, không có thứ tự — nên thứ tự hiển thị khai ở đây, theo đúng
# biểu mẫu tạo hồ sơ: loại, tiêu đề, mô tả, rồi tới các trường người điều phối và
# phòng ban đặt. Trước đây trả theo chữ cái, nên bảng Sửa nội dung ra Mô tả đứng trên
# Tiêu đề và người dùng gõ nhầm ô.
#
# Đây là các cột của bảng `requests`, tức lược đồ, không phải cấu hình nghiệp vụ.
THU_TU_O_NHAP: tuple[str, ...] = (
    "request_type_code",
    "title",
    "description",
    "details",
    "priority_code",
    "department_code",
    "assignee_id",
    # Gia hạn xử lý (#101): chỉ số giờ lần này là ô nhập; hai trường sau do ràng buộc tự đặt
    "sla_extension_hours",
    "sla_extension_total_hours",
    "sla_extension_count",
    # Mở lại (#102): do ràng buộc tự đặt, không cạnh nào cho nhập
    "reopen_count",
)

# Kiểm ngay lúc nạp mô-đun, cùng khuôn với biên ngoài trong engine: thêm một trường vào
# `CHANGEABLE_FIELDS` mà quên khai thứ tự thì dịch vụ không khởi động.
if set(THU_TU_O_NHAP) != CHANGEABLE_FIELDS or len(THU_TU_O_NHAP) != len(CHANGEABLE_FIELDS):
    raise RuntimeError(
        "THU_TU_O_NHAP phải liệt kê đúng mỗi trường của CHANGEABLE_FIELDS một lần. "
        f"Thiếu: {sorted(CHANGEABLE_FIELDS - set(THU_TU_O_NHAP))}; "
        f"thừa: {sorted(set(THU_TU_O_NHAP) - CHANGEABLE_FIELDS)}."
    )


def xep_o_nhap(truong: frozenset[str] | set[str]) -> list[str]:
    """Xếp các trường một cạnh cho phép đặt theo thứ tự ô nhập trên giao diện."""
    return [ma for ma in THU_TU_O_NHAP if ma in truong]


def _bao_loi(loi: TransitionError) -> HTTPException:
    """Dịch lỗi engine thành phản hồi HTTP, giữ nguyên mã máy đọc được."""
    return HTTPException(
        status_code=MA_HTTP.get(type(loi), status.HTTP_400_BAD_REQUEST),
        detail={"code": loi.code, "message": loi.message},
    )


def _bao_loi_nhan(loi: MessageRejected) -> HTTPException:
    """Dịch lỗi lời nhắn thành phản hồi HTTP, cùng khuôn `{code, message}` với `_bao_loi`."""
    return HTTPException(
        status_code=loi.http_status, detail={"code": loi.code, "message": loi.message}
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


def _tu_dong_ra(session: Session, ho_so: Request) -> TuDongRa | None:
    """Cạnh tự đi khi hết hạn chờ của trạng thái hiện tại, nếu có (#142)."""
    td = tu_dong(session, ho_so)
    if td is None:
        return None
    return TuDongRa(activity_label=td.canh.activity_label, at=td.luc, warn=td.bao_truoc)


def _truong_ra(t: RequestTypeField) -> TruongRiengRa:
    return TruongRiengRa(
        code=t.code, label=t.label, kind=t.kind, required=t.required,
        help_text=t.help_text, unit=t.unit, options=t.options,
    )


def _buoc_cua_toi(canh: Transition | None) -> dict:
    """Cờ và nhãn bước chính cho một dòng danh sách (#227, #228)."""
    return {
        "needs_my_action": canh is not None,
        "next_step_label": canh.activity_label if canh else None,
    }


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
        # Đã dùng tới ngưỡng sắp hết hạn của loại yêu cầu mà chưa quá hạn (#175)
        "sla_due_soon": sap_het_han(session, ho_so),
        # Gia hạn (#101): hạn ở `sla_limit_seconds` đã gồm phần này
        "sla_extension_total_hours": ho_so.sla_extension_total_hours,
        "sla_extension_count": ho_so.sla_extension_count,
        # Đồng hồ đã từng khởi động chưa. Nó chỉ khởi động khi hồ sơ lần đầu vào một
        # trạng thái có `sla_running` — tức khi phòng ban nhận việc. Trước đó giao diện
        # phải nói "hạn tính từ lúc nhận việc", không được nói "còn …" (#97).
        "sla_started": ho_so.sla_segment_since is not None or ho_so.sla_running_seconds > 0,
        # Hồ sơ quá hạn nhưng vừa vào lại trạng thái đếm giờ: còn chừng này giây trước
        # khi bộ quét được leo thang lại (#94). None khi không áp.
        "sla_grace_seconds": an_han_con_lai_giay(session, ho_so),
        # Hạn chót theo lịch làm việc, để giao diện ghi "hạn 15:00 thứ Hai" (#199)
        "sla_due_at": han_chot(session, ho_so),
        "auto_transition": _tu_dong_ra(session, ho_so),
        # Đồng hồ đang tạm dừng: đã khởi động nhưng trạng thái hiện tại không đếm giờ
        "sla_paused": (
            ho_so.sla_segment_since is not None and not trang_thai.sla_running
        ),
        # Ai nhắn sau cùng — dấu hiệu "đang chờ trả lời" trên hàng đợi (#128)
        "last_message_from_requester": loi_nhan_cuoi_tu_nguoi_gui(session, ho_so),
    }


def _nhan_danh_muc(session: Session) -> dict[str, dict[str, str]]:
    """Nhãn của mọi mục trong các danh mục mà nhật ký có thể nhắc tới, theo trường.

    Lấy cả mục đã ngừng dùng: một hồ sơ cũ từng mang loại yêu cầu nay đã gỡ khỏi danh
    mục vẫn phải kể được "loại: A → B" bằng tên, không bằng mã.
    """
    nhan = {
        truong: {m.code: m.label for m in session.scalars(select(mo_hinh)).all()}
        for truong, mo_hinh in DANH_MUC_CUA_TRUONG.items()
    }
    # Trường riêng theo loại (#250): mã trường → nhãn, để kể "Vị trí: Tầng 3" thay vì mã
    nhan["details"] = {t.code: t.label for t in session.scalars(select(RequestTypeField)).all()}
    return nhan


def _thay_doi(e: EventLog, nhan: dict[str, dict[str, str]]) -> list[ThayDoiTruongRa]:
    """Đọc cột `changes` thành danh sách có nhãn, theo đúng thứ tự trường đã ghi."""

    def mot_ben(truong: str, muc: dict, ben: str) -> NhanCoMa | None:
        ma = muc.get(ben)
        if ma is None:
            return None
        # Bộ trường riêng (#250) kể thành một dòng "Nhãn: giá trị · Nhãn: giá trị"
        if isinstance(ma, dict):
            ten_truong = nhan.get(truong, {})
            ke = " · ".join(f"{ten_truong.get(k, k)}: {v}" for k, v in ma.items())
            return NhanCoMa(code=json.dumps(ma, ensure_ascii=False), label=ke or "(trống)")
        # Giá trị số — giờ và số lần gia hạn (#101) — kể lại dạng chữ, như mọi giá trị khác
        ma = str(ma)
        ten = muc.get(f"{ben}_label") or nhan.get(truong, {}).get(ma) or ma
        return NhanCoMa(code=ma, label=ten)

    return [
        ThayDoiTruongRa(
            field=truong,
            before=mot_ben(truong, muc, "from"),
            after=mot_ben(truong, muc, "to"),
        )
        for truong, muc in (e.changes or {}).items()
    ]


def _su_kien(
    e: EventLog,
    states: dict[str, State],
    canh: dict[str, Transition],
    nhan: dict[str, dict[str, str]],
) -> SuKienRa:
    di_qua = canh.get(f"{e.from_state}->{e.to_state}")
    return SuKienRa(
        timestamp=e.timestamp,
        activity=e.activity,
        activity_label=di_qua.activity_label if di_qua else None,
        note_label=di_qua.note_label if di_qua else None,
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
        changes=_thay_doi(e, nhan),
        is_rework=bool(di_qua and di_qua.is_rework),
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
            fields=[_truong_ra(t) for t in truong_cua_loai(session, l.code)],
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


@router.get("/priorities", response_model=list[MucUuTienRa])
def danh_muc_muc_uu_tien(
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[Actor, Depends(current_actor)],
) -> list[MucUuTienRa]:
    """Các mức ưu tiên, cho ô chọn ở buồng lái. Cờ `is_default` để giao diện điền sẵn."""
    return [
        MucUuTienRa(code=m.code, label=m.label, is_default=m.is_default)
        for m in session.scalars(select(Priority).order_by(Priority.display_order)).all()
    ]


@router.get("/departments", response_model=list[PhongBanRa])
def danh_muc_phong_ban(
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[Actor, Depends(current_actor)],
) -> list[PhongBanRa]:
    """Các phòng ban đang hoạt động, cho ô chọn phòng khi định tuyến hồ sơ."""
    return [
        PhongBanRa(code=p.code, label=p.label, description=p.description)
        for p in session.scalars(
            select(Department)
            .where(Department.is_active)
            .order_by(Department.display_order)
        ).all()
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
        goc = kiem_ho_so_goc(session, du_lieu.parent_request_id, actor.id)
    except ValueError as loi:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid-parent-request", "message": str(loi)},
        ) from loi

    try:
        ho_so = create_case(
            session,
            title=du_lieu.title,
            description=du_lieu.description,
            requester_id=actor.id,
            requester_label=actor.label,
            request_type_code=du_lieu.request_type_code,
            parent_request_id=goc,
            details=du_lieu.details,
        )
    except InvalidFieldValue as loi:
        # Trường riêng thiếu hay sai kiểu (#250): câu lỗi đã dùng nhãn trường
        raise HTTPException(
            status_code=422,
            detail={"code": loi.code, "field": loi.field, "message": str(loi)},
        ) from loi
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
    buoc = my_primary_steps(session, cac_ho_so, actor)
    return [HoSoTomTatRa(**_tom_tat(session, h, states), **_buoc_cua_toi(buoc[h.id])) for h in cac_ho_so]


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
    danh_ba: Annotated[KeycloakDirectory, Depends(get_directory)],
) -> HoSoChiTietRa:
    """Thực hiện một thao tác trên hồ sơ.

    Điểm cuối này **không tự kiểm quyền**. Engine đã tra bảng `transitions` và ma trận
    phân quyền rồi; kiểm thêm một lớp ở đây sẽ tạo ra nguồn sự thật thứ hai, và hai
    nguồn sẽ lệch nhau. Việc duy nhất ở đây là dịch lỗi engine sang mã HTTP.

    Từ #127 điểm cuối nhận `changes`, nên nó gọi phép kiểm người được giao như MỌI điểm
    cuối nhận `changes` (#83). Không cạnh nào của người gửi cho đặt người xử lý, nên
    phép kiểm dừng ngay mà không tra danh bạ — nhưng bỏ qua ở đây là để hở một đường
    vòng quanh danh bạ cho người mang cùng lúc vai trò người gửi và vai trò giao việc.
    """
    _kiem_chu_so_huu(session, case_id, actor)

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
    return _dung_chi_tiet(session, ho_so, actor)


@router.post("/requests/{case_id}/messages", response_model=HoSoChiTietRa)
def gui_loi_nhan(
    case_id: int,
    du_lieu: GuiLoiNhanVao,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[Actor, Depends(current_actor)],
) -> HoSoChiTietRa:
    """Gửi một lời nhắn trên hồ sơ của mình (#128).

    Không đổi hồ sơ: không trạng thái, không trường, không đồng hồ, không dòng nhật ký —
    xem app/workflow/messages.py. Cửa nhìn thấy giống hệt trang chi tiết: hồ sơ của
    người khác trả 404.
    """
    ho_so = _lay_ho_so_cua_toi(session, case_id, actor)
    try:
        ghi_loi_nhan(session, ho_so, actor, du_lieu.kind, du_lieu.body)
    except MessageRejected as loi:
        session.rollback()
        raise _bao_loi_nhan(loi) from loi

    session.commit()
    return _dung_chi_tiet(session, ho_so, actor)


def _dung_chi_tiet(session: Session, ho_so: Request, actor: Actor) -> HoSoChiTietRa:
    return HoSoChiTietRa(**_du_lieu_chi_tiet(session, ho_so, actor))


def _ho_so_lien_quan(ho_so: Request, states: dict[str, State]) -> HoSoLienQuanRa:
    trang_thai = states[ho_so.current_state]
    return HoSoLienQuanRa(
        id=ho_so.id,
        code=_ma_ho_so(ho_so),
        title=ho_so.title,
        state=TrangThaiRa(
            code=trang_thai.code,
            label=trang_thai.label,
            is_terminal=trang_thai.is_terminal,
        ),
    )


def _lien_ket_ho_so(session: Session, ho_so: Request, states: dict[str, State]) -> dict:
    """Hồ sơ gốc, các hồ sơ tạo lại và số lần mở lại của hồ sơ này (#102)."""
    goc = session.get(Request, ho_so.parent_request_id) if ho_so.parent_request_id else None
    con = session.scalars(
        select(Request).where(Request.parent_request_id == ho_so.id).order_by(Request.id)
    ).all()
    loai = (
        session.get(RequestType, ho_so.request_type_code) if ho_so.request_type_code else None
    )
    return {
        "parent": _ho_so_lien_quan(goc, states) if goc else None,
        "children": [_ho_so_lien_quan(c, states) for c in con],
        "reopen_count": ho_so.reopen_count,
        "reopen_max_count": loai.reopen_max_count if loai else None,
    }


def _du_lieu_chi_tiet(session: Session, ho_so: Request, actor: Actor) -> dict:
    """Phần chi tiết dùng chung giữa cổng người gửi và buồng lái điều phối.

    Trả về dict thay vì lược đồ để buồng lái ghép thêm trường của nó mà không phải
    dựng lại dòng thời gian và danh sách cạnh — hai thứ phải giống hệt nhau ở mọi nơi.
    """
    states = _bang_trang_thai(session, ho_so.rule_set_id)
    # Tra một lần cho cả dòng thời gian, không tra lại ở từng mốc
    nhan = _nhan_danh_muc(session)

    # Nhãn hoạt động và tên ô ghi chú tra theo cặp trạng thái vì nhiều cạnh dùng chung
    # `activity_code` — bốn cạnh hủy chẳng hạn.
    canh = {
        f"{t.from_state}->{t.to_state}": t
        for t in session.scalars(
            select(Transition).where(Transition.rule_set_id == ho_so.rule_set_id)
        ).all()
    }

    # Trạng thái kết thúc nào còn cạnh mở lại, và cửa sổ bao nhiêu giờ làm việc (#102)
    cua_so_mo_lai = {
        t.from_state: t.reopen_window_hours
        for t in canh.values()
        if t.reopen_window_hours is not None
    }

    canh_di_duoc = allowed_transitions(session, ho_so, actor)
    di_duoc = [
        CanhDiDuocRa(
            to_state=t.to_state,
            to_state_label=_nhan(states.get(t.to_state), t.to_state),
            to_state_is_terminal=bool(
                states.get(t.to_state) and states[t.to_state].is_terminal
            ),
            to_state_reopen_hours=cua_so_mo_lai.get(t.to_state),
            activity_code=t.activity_code,
            activity_label=t.activity_label,
            requires_note=t.requires_note,
            note_label=t.note_label,
            keeps_state=t.from_state == t.to_state,
            fields=xep_o_nhap(permitted_fields(t.guard_codes)),
        )
        for t in canh_di_duoc
    ]

    # Tệp đính kèm (#80): liệt kê ở mọi cổng — ai mở được hồ sơ thì thấy tệp
    tep_dinh_kem = [
        TepDinhKemRa(
            id=t.id,
            filename=t.filename,
            content_type=t.content_type,
            size_bytes=t.size_bytes,
            uploaded_by_label=t.uploaded_by_label,
            created_at=t.created_at,
        )
        for t in danh_sach_tep(session, ho_so.id)
    ]

    # Lời nhắn (#128) đi riêng khỏi `history`: nhật ký chỉ ghi những lần hồ sơ đổi
    cac_loai = {k.code: k for k in session.scalars(select(MessageKind)).all()}
    loi_nhan = [
        LoiNhanRa(
            id=m.id,
            kind=m.kind,
            kind_label=cac_loai[m.kind].label,
            internal=cac_loai[m.kind].hidden_from_requester,
            author=m.author,
            author_label=m.author_label,
            from_requester=m.author == ho_so.requester_id,
            mine=m.author == actor.id,
            body=m.body,
            created_at=m.created_at,
        )
        # Người gửi của hồ sơ không nhận lời nhắn nội bộ nào, ở bất kỳ cửa nào (#156)
        for m in cac_loi_nhan(session, ho_so, actor)
    ]
    loai_nhan_duoc = [
        LoaiLoiNhanRa(
            code=g.loai.code,
            label=g.loai.label,
            description=g.loai.description,
            body_required=g.loai.body_required,
            internal=g.loai.hidden_from_requester,
            retry_at=g.gui_lai_tu,
        )
        for g in loai_gui_duoc(session, ho_so, actor)
    ]

    return {
        **_tom_tat(session, ho_so, states),
        "description": ho_so.description,
        "details": ho_so.details or {},
        "detail_fields": [_truong_ra(t) for t in truong_cua_loai(session, ho_so.request_type_code)],
        "requester_id": ho_so.requester_id,
        "assignee_id": ho_so.assignee_id,
        **_lien_ket_ho_so(session, ho_so, states),
        "attachments": tep_dinh_kem,
        "can_attach": any(c.accepts_attachments for c in canh_di_duoc),
        "history": [_su_kien(e, states, canh, nhan) for e in case_history(session, ho_so.id)],
        "allowed_transitions": di_duoc,
        "messages": loi_nhan,
        "message_kinds": loai_nhan_duoc,
        "sees_internal": thay_noi_bo(ho_so, actor),
    }
