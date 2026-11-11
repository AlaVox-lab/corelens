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

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.auth.directory import KeycloakDirectory, get_directory
from app.db import get_session
from app.models.case import EventLog, Request
from app.rate_limit import gioi_han_toc_do
from app.models.workflow_config import (
    Priority,
    State,
    Transition,
    TransitionRole,
)
from app.rules.han_cho import canh_tu_di_theo_trang_thai, da_toi_luc_bao, giay_da_o_trang_thai
from app.workflow.assignment import kiem_nguoi_duoc_giao
from app.workflow.contact import lien_he_nguoi_gui
from app.workflow.context import Actor
from app.workflow.engine import my_primary_steps, rule_sets_in_use
from app.workflow.engine import perform_transition as thuc_hien_chuyen
from app.workflow.errors import TransitionError
from app.workflow.messages import MessageRejected, gui_loi_nhan
from app.workflow.routes import (
    _buoc_cua_toi,
    _bang_trang_thai_nhieu,
    _bao_loi,
    _bao_loi_nhan,
    _do_gap,
    _du_lieu_chi_tiet,
    _giu_danh_muc,
    _gop_theo_ma,
    _ma_ho_so,
    _o_trang_thai,
    _tom_tat,
    goi_y_ra,
)
from app.intelligence.goi_y import goi_y_loai, goi_y_phong, goi_y_uu_tien
from app.workflow.phan_trang import ThamSoTrang, cat_trang, khop_tim, tham_so_trang
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


def trang_thai_hang_doi_dieu_phoi(session: Session, rule_set_id: int) -> list[State]:
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
        # Cùng hàm cửa chuyển trạng thái dùng để ghi giữ hay ghi đè (#239)
        suggested_department=goi_y_ra(goi_y_phong(session, ho_so, ho_so.request_type_code)),
        suggested_request_type=goi_y_ra(goi_y_loai(session, ho_so)),
        suggested_priority=goi_y_ra(goi_y_uu_tien(session, ho_so)),
        requested_by_me=ho_so.requester_id == actor.id,
    )


# ---------------------------------------------------------------------------
# Hàng đợi
# ---------------------------------------------------------------------------


@router.get("/queue", response_model=HangDoiRa)
def hang_doi(
    session: _Phien,
    actor: _Cua,
    trang: Annotated[ThamSoTrang, Depends(tham_so_trang)],
    state: Annotated[str | None, Query(description="Chỉ lấy một trạng thái")] = None,
    q: Annotated[str | None, Query(description="Tìm theo mã, tiêu đề, người gửi")] = None,
    request_type: Annotated[str | None, Query(description="Chỉ một loại yêu cầu")] = None,
    priority: Annotated[str | None, Query(description="Chỉ một mức ưu tiên")] = None,
    department: Annotated[str | None, Query(description="Chỉ hồ sơ đang gắn một phòng")] = None,
    sort: Annotated[
        Literal["cho", "gap", "moi"],
        Query(description="cho: chờ lâu nhất · gap: gấp trước · moi: mới nhất"),
    ] = "cho",
    needs_action: Annotated[bool, Query(description="Chỉ hồ sơ đang chờ chính người xem")] = False,
) -> HangDoiRa:
    """Hồ sơ đang chờ điều phối viên, mặc định chờ lâu nhất lên đầu, có phân trang (#232).

    Mặc định xếp theo thời gian chờ ở trạng thái hiện tại chứ không theo hạn SLA: đồng hồ SLA
    không chạy ở những trạng thái này — nó chỉ bắt đầu khi phòng ban nhận việc. "Gấp" ở đây là
    hệ thống sắp tự đi thay.

    Hàng đợi chỉ gồm hồ sơ đang mở ở các trạng thái của điều phối, nên lớn theo khối việc đang
    làm chứ không theo lịch sử: lọc và đếm làm trên cả hàng đợi, rồi mới cắt trang; tóm tắt đầy
    đủ — phần tốn nhất — chỉ dựng cho hồ sơ của trang.

    Gồm hồ sơ của mọi bộ quy tắc còn hồ sơ đang mở (#299): doanh nghiệp đổi bộ quy tắc thì hồ sơ
    cũ vẫn chạy theo bộ cũ tới khi kết thúc, nên vẫn phải nằm trong hàng đợi — mỗi hồ sơ vào hàng
    đợi theo các trạng thái điều phối của chính bộ nó.
    """
    cac_bo = rule_sets_in_use(session)
    theo_bo = {bo: trang_thai_hang_doi_dieu_phoi(session, bo) for bo in cac_bo}
    cac_trang_thai = _gop_theo_ma(list(theo_bo.values()))
    ma_hang_doi = [t.code for t in cac_trang_thai]

    if state is not None and state not in ma_hang_doi:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "state-not-in-queue",
                "message": f"Trạng thái '{state}' không thuộc hàng đợi điều phối.",
            },
        )

    luc_vao = _luc_vao_trang_thai().label("luc_vao")
    ca_hang = [
        (ho_so, vao, da_o)
        for ho_so, vao, da_o in session.execute(
            select(Request, luc_vao, giay_da_o_trang_thai())
            .where(_o_trang_thai({bo: [t.code for t in ds] for bo, ds in theo_bo.items()}))
            .order_by(luc_vao.asc(), Request.id)
        )
    ]
    buoc = my_primary_steps(session, [ho_so for ho_so, _, _ in ca_hang], actor)
    # (quá hạn, sắp hạn) tính một lần cho cả hàng đợi: dải lọc, cách xếp "gấp" và chấm báo trên
    # thanh bên cùng đọc, nên không kể hai chuyện
    _danh_muc = _giu_danh_muc(session, cac_bo)
    canh_tu_di = {bo: canh_tu_di_theo_trang_thai(session, bo) for bo in cac_bo}
    bao = {}
    for ho_so, _, da_o in ca_hang:
        canh = canh_tu_di[ho_so.rule_set_id].get(ho_so.current_state)
        bao[ho_so.id] = canh is not None and da_toi_luc_bao(canh, da_o)
    gap = {ho_so.id: _do_gap(session, ho_so, bao[ho_so.id]) for ho_so, _, _ in ca_hang}
    cho_toi = [ho_so for ho_so, _, _ in ca_hang if buoc[ho_so.id] is not None]

    def khop(ho_so: Request) -> bool:
        return (
            khop_tim(q, ho_so.title, ho_so.requester_label, _ma_ho_so(ho_so))
            and (not request_type or ho_so.request_type_code == request_type)
            and (not priority or ho_so.priority_code == priority)
            and (not department or ho_so.department_code == department)
            and (not needs_action or buoc[ho_so.id] is not None)
        )

    da_loc = [(h, vao) for h, vao, _ in ca_hang if khop(h)]
    dem: dict[str, list[int]] = {}
    for h, _ in da_loc:
        o = dem.setdefault(h.current_state, [0, 0, 0])
        qua, sap = gap[h.id]
        o[0] += 1
        o[1] += qua
        o[2] += sap
    if state:
        da_loc = [(h, vao) for h, vao in da_loc if h.current_state == state]

    if sort == "moi":
        da_loc.sort(key=lambda d: (d[0].created_at, d[0].id), reverse=True)
    elif sort == "gap":
        da_loc.sort(key=lambda d: (not gap[d[0].id][0], not gap[d[0].id][1], d[1], d[0].id))

    bang = _bang_trang_thai_nhieu(session, cac_bo)
    cac_muc = [
        MucHangDoiRa(
            **_tom_tat(session, ho_so, bang[ho_so.rule_set_id]),
            **_buoc_cua_toi(buoc[ho_so.id]),
            requester_label=ho_so.requester_label,
            priority=_nhan_co_ma(
                session.get(Priority, ho_so.priority_code) if ho_so.priority_code else None
            ),
            state_entered_at=vao,
            requested_by_me=ho_so.requester_id == actor.id,
        )
        for ho_so, vao in cat_trang(da_loc, trang)
    ]

    return HangDoiRa(
        groups=[
            NhomHangDoiRa(code=t.code, label=t.label, count=o[0], overdue=o[1], due_soon=o[2])
            for t in cac_trang_thai
            for o in [dem.get(t.code, [0, 0, 0])]
        ],
        items=cac_muc,
        total=len(da_loc),
        offset=trang.offset,
        limit=trang.limit,
        waiting_me=len(cho_toi),
        # Gấp như chấm báo trên thanh bên (#230): quá hạn, hay hệ thống sắp tự đi
        urgent=any(gap[h.id][0] or bao[h.id] for h in cho_toi),
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


@router.post(
    "/requests/{case_id}/messages",
    response_model=HoSoDieuPhoiRa,
    dependencies=[Depends(gioi_han_toc_do("send-message"))],
)
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
