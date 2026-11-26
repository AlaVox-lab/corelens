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

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi import Request as YeuCauHttp
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.kiem_toan import XEM_HO_SO, XEM_LIEN_HE, ghi_truy_cap
from app.auth.directory import KeycloakDirectory, get_directory
from app.config import get_settings
from app.db import get_session
from app.models.case import EventLog, Request
from app.rate_limit import gioi_han_toc_do
from app.models.workflow_config import (
    Priority,
    State,
    Transition,
    TransitionRole,
)
from app.rules.guards import permitted_fields, truong_bat_buoc, truong_can_nhap
from app.rules.han_cho import canh_tu_di_theo_trang_thai, da_toi_luc_bao, giay_da_o_trang_thai
from app.workflow.assignment import kiem_nguoi_duoc_giao
from app.workflow.contact import lien_he_nguoi_gui
from app.workflow.danh_gia import danh_gia_cua
from app.workflow.context import Actor
from app.workflow.engine import (
    _nhan_trang_thai,
    ma_quy_trinh_ung_dung,
    my_primary_steps,
    rule_sets_in_use,
    xet_cac_canh,
)
from app.workflow.engine import perform_transition as thuc_hien_chuyen
from app.workflow.errors import (
    CaseNotFound,
    FieldNotPermitted,
    GuardViolation,
    TransitionError,
    TransitionNotAllowed,
)
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
    xep_o_nhap,
)
from app.intelligence.goi_y import goi_y_loai, goi_y_phong, goi_y_uu_tien
from app.intelligence.nguoi_xu_ly import hen_goi_y_neu_ve_phong
from app.workflow.phan_trang import ThamSoTrang, cat_trang, khop_tim, tham_so_trang
from app.workflow.schemas import (
    ChuyenHangLoatVao,
    ChuyenTrangThaiCoTruongVao,
    DanhSachThaoTacHangLoatRa,
    GuiLoiNhanVao,
    HangDoiRa,
    HoSoDieuPhoiRa,
    KetQuaHangLoatRa,
    LienHeNguoiGuiRa,
    LoiHangLoatRa,
    MucHangDoiRa,
    MucHangLoatRa,
    NhanCoMa,
    NhomHangDoiRa,
    ThaoTacHangLoatRa,
    TruongHangLoatRa,
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
        # Đánh giá của người gửi (#433) — điểm kèm nhận xét, chỉ đọc
        feedback=danh_gia_cua(session, ho_so.id),
    )


# ---------------------------------------------------------------------------
# Hàng đợi
# ---------------------------------------------------------------------------


@router.get("/queue", summary="Hàng đợi điều phối", response_model=HangDoiRa)
def hang_doi(
    session: _Phien,
    actor: _Cua,
    trang: Annotated[ThamSoTrang, Depends(tham_so_trang)],
    state: Annotated[str | None, Query(description="Chỉ lấy một trạng thái")] = None,
    q: Annotated[str | None, Query(description="Tìm theo mã, tiêu đề, người gửi, mô tả — không phân biệt dấu")] = None,
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
    cac_bo = rule_sets_in_use(session, ma_quy_trinh_ung_dung(session))
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
            khop_tim(q, ho_so.title, ho_so.requester_label, ho_so.description, _ma_ho_so(ho_so))
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


@router.get("/requests/{case_id}", summary="Chi tiết hồ sơ (điều phối viên)", response_model=HoSoDieuPhoiRa)
def chi_tiet(case_id: int, session: _Phien, actor: _Cua, yeu_cau: YeuCauHttp) -> HoSoDieuPhoiRa:
    """Chi tiết một hồ sơ bất kỳ, kèm những thao tác người này làm được lúc này.

    Mở được cả hồ sơ đã rời hàng đợi — ngay sau khi điều phối viên chuyển hồ sơ về
    phòng ban, giao diện đưa họ về lại trang này để thấy kết quả, và lúc đó hồ sơ đã
    không còn ở trạng thái của hàng đợi nữa.

    Mỗi lần mở ghi một dòng nhật ký truy cập (#431, app/kiem_toan.py), trừ hồ sơ do chính người gọi gửi.
    """
    ho_so = session.get(Request, case_id)
    if ho_so is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "case-not-found", "message": "Không tìm thấy hồ sơ."},
        )
    ra = _dung_chi_tiet_dieu_phoi(session, ho_so, actor)
    ghi_truy_cap(yeu_cau, actor, XEM_HO_SO, ho_so=ho_so)
    return ra


@router.get(
    "/requests/{case_id}/requester-contact", summary="Liên hệ người gửi (điều phối viên)",
    response_model=LienHeNguoiGuiRa,
    responses={
        404: {"description": "Không có hồ sơ này"},
        503: {"description": "Danh bạ Keycloak không trả lời"},
    },
)
def lien_he(
    case_id: int,
    session: _Phien,
    actor: _Cua,
    danh_ba: Annotated[KeycloakDirectory, Depends(get_directory)],
    yeu_cau: YeuCauHttp,
) -> LienHeNguoiGuiRa:
    """Email và số điện thoại của người gửi, tra từ danh bạ lúc gọi (#131).

    Cùng cửa với trang chi tiết: điều phối viên mở được mọi hồ sơ nên tra được liên hệ
    của mọi người gửi. Đây là điểm cuối riêng, tách khỏi trang chi tiết (`app/workflow/contact.py`).
    Mỗi lần tra được ghi nhật ký truy cập (#431).
    """
    ho_so = session.get(Request, case_id)
    if ho_so is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "case-not-found", "message": "Không tìm thấy hồ sơ."},
        )
    ra = lien_he_nguoi_gui(danh_ba, ho_so)
    ghi_truy_cap(yeu_cau, actor, XEM_LIEN_HE, ho_so=ho_so)
    return ra


@router.post("/requests/{case_id}/transitions", summary="Đi một bước trên hồ sơ (điều phối viên)", response_model=HoSoDieuPhoiRa)
def chuyen_trang_thai(
    case_id: int,
    du_lieu: ChuyenTrangThaiCoTruongVao,
    session: _Phien,
    actor: _Cua,
    danh_ba: Annotated[KeycloakDirectory, Depends(get_directory)],
    tac_vu_nen: BackgroundTasks,
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
    # Hồ sơ vừa về phòng: gợi ý người xử lý tính ở nền, sau khi phản hồi đã về (#318)
    hen_goi_y_neu_ve_phong(tac_vu_nen, session, ho_so)
    return _dung_chi_tiet_dieu_phoi(session, ho_so, actor)


# ---------------------------------------------------------------------------
# Thao tác hàng loạt (#440)
# ---------------------------------------------------------------------------
#
# Một VÒNG LẶP trên cửa chuyển trạng thái duy nhất, không phải đường vòng quanh nó: mỗi hồ sơ một
# lần `perform_transition`, một giao dịch, một dòng nhật ký — đúng như điều phối viên bấm lần lượt
# từng hồ sơ ở điểm cuối trên. Hồ sơ bị chặn thì hoàn tác riêng nó, đứng nguyên, vào kết quả kèm mã
# và thông điệp của chính lỗi engine; lô vẫn đi tiếp.
#
# Bước nào làm được hàng loạt là cấu hình (`DXLAB_BULK_ACTIVITIES`, mã hoạt động của bộ quy tắc);
# trạng thái nguồn, nhãn, trường cần nhập đều tra từ `transitions` và ràng buộc trên cạnh.


def _cac_thao_tac_hang_loat(session: Session) -> dict[str, tuple[ThaoTacHangLoatRa, frozenset[str]]]:
    """Bước làm được hàng loạt, kèm tập trường mà các cạnh của bước đó cho đặt — theo thứ tự khai.

    Một bước là mọi cạnh người mang mã hoạt động đó mà vai điều phối đi được, ở mọi bộ quy tắc còn hồ
    sơ đang mở — như hàng đợi (#299). Mã khai trong cấu hình mà không có cạnh nào như vậy thì bỏ.
    """
    ma_cau_hinh = get_settings().bulk_activity_codes
    cac_bo = rule_sets_in_use(session, ma_quy_trinh_ung_dung(session))
    theo_ma: dict[str, list[Transition]] = {}
    for canh in session.scalars(
        select(Transition)
        .join(TransitionRole, TransitionRole.transition_id == Transition.id)
        .where(
            Transition.rule_set_id.in_(cac_bo),
            Transition.is_system.is_(False),
            Transition.activity_code.in_(ma_cau_hinh),
            TransitionRole.role_code == VAI_TRO_DIEU_PHOI,
        )
        .order_by(Transition.display_order, Transition.id)
    ).unique():
        theo_ma.setdefault(canh.activity_code, []).append(canh)

    bang = _bang_trang_thai_nhieu(session, cac_bo)
    ket_qua: dict[str, tuple[ThaoTacHangLoatRa, frozenset[str]]] = {}
    for ma in ma_cau_hinh:
        cac_canh = theo_ma.get(ma)
        if not cac_canh:
            continue
        nguon: dict[str, NhanCoMa] = {}
        for c in cac_canh:
            trang_thai = bang[c.rule_set_id].get(c.from_state)
            nguon.setdefault(c.from_state, NhanCoMa(code=c.from_state, label=trang_thai.label if trang_thai else c.from_state))
        can_nhap = frozenset().union(*(truong_can_nhap(c.guard_codes) for c in cac_canh))
        bat_buoc = frozenset().union(*(truong_bat_buoc(c.guard_codes) for c in cac_canh))
        ket_qua[ma] = (
            ThaoTacHangLoatRa(
                activity_code=ma,
                activity_label=cac_canh[0].activity_label,
                from_states=list(nguon.values()),
                fields=[TruongHangLoatRa(code=t, required=t in bat_buoc) for t in xep_o_nhap(can_nhap)],
                requires_note=any(c.requires_note for c in cac_canh),
                note_label=next((c.note_label for c in cac_canh if c.note_label), None),
            ),
            frozenset().union(*(permitted_fields(c.guard_codes) for c in cac_canh)),
        )
    return ket_qua


@router.get("/bulk-transitions", summary="Các bước làm được cho cả lô", response_model=DanhSachThaoTacHangLoatRa)
def thao_tac_hang_loat(session: _Phien, _: _Cua) -> DanhSachThaoTacHangLoatRa:
    """Những bước điều phối viên làm được cho nhiều hồ sơ một lần, và lô lớn nhất (#440).

    Giao diện dựng nút trên thanh thao tác và ô trong hộp thoại từ đây — không biết mã bước nào.
    """
    return DanhSachThaoTacHangLoatRa(
        max_cases=get_settings().bulk_max_cases,
        actions=[ra for ra, _ in _cac_thao_tac_hang_loat(session).values()],
    )


def _canh_cua_buoc(session: Session, ho_so: Request, ma_buoc: str, actor: Actor) -> Transition | None:
    """Cạnh mang mã bước người dùng chọn, trong các cạnh rời trạng thái hiện tại của hồ sơ.

    Thường chỉ một cạnh. Một trạng thái có nhiều cạnh cùng mã (như ba cạnh "Bổ sung thông tin") thì
    lấy cạnh đầu tiên tác nhân đi được, xét bằng cùng hàm xét cạnh của engine (#424); không cạnh nào
    đi được thì vẫn trả cạnh đầu để engine báo đúng lý do của nó.
    """
    cac_canh = session.scalars(
        select(Transition)
        .where(
            Transition.rule_set_id == ho_so.rule_set_id,
            Transition.from_state == ho_so.current_state,
            Transition.activity_code == ma_buoc,
            Transition.is_system.is_(False),
        )
        .order_by(Transition.display_order, Transition.id)
    ).all()
    if len(cac_canh) <= 1:
        return cac_canh[0] if cac_canh else None
    di_duoc = {c.id for c, ly_do in xet_cac_canh(session, ho_so, actor, dung_som=True) if not ly_do}
    return next((c for c in cac_canh if c.id in di_duoc), cac_canh[0])


def _loi_hang_loat(loi: TransitionError) -> LoiHangLoatRa:
    return LoiHangLoatRa(
        code=loi.code,
        message=loi.message,
        guard=loi.guard_code if isinstance(loi, GuardViolation) else None,
    )


@router.post(
    "/bulk-transitions", summary="Đi một bước cho cả lô hồ sơ",
    response_model=KetQuaHangLoatRa,
    dependencies=[Depends(gioi_han_toc_do("bulk-transition"))],
    responses={422: {"description": "Lô quá lớn, trùng hồ sơ, bước không làm được hàng loạt, hay trường ngoài cạnh"}},
)
def chuyen_hang_loat(
    du_lieu: ChuyenHangLoatVao,
    session: _Phien,
    actor: _Cua,
    danh_ba: Annotated[KeycloakDirectory, Depends(get_directory)],
    tac_vu_nen: BackgroundTasks,
) -> KetQuaHangLoatRa:
    """Đi một bước cho cả lô hồ sơ; kết quả từng hồ sơ theo đúng thứ tự gửi lên (#440).

    Lỗi của cả lô (422, không hồ sơ nào đổi): lô vượt `DXLAB_BULK_MAX_CASES`, trùng hồ sơ, bước không
    nằm trong các bước hàng loạt, hay gửi trường mà không cạnh nào của bước cho đặt — cùng mã
    `field-not-permitted` như điểm cuối một hồ sơ.

    Còn lại là chuyện của từng hồ sơ, qua đúng đường của điểm cuối một hồ sơ: kiểm người được giao,
    `perform_transition`, commit, hẹn tác vụ nền sau khi chuyển. Thông báo thư và luồng cập nhật thời
    gian thực đi theo từng lần chuyển như cũ — hàng đợi thư cùng giao dịch, trigger của cơ sở dữ liệu.
    Không dấu giữ hay ghi đè gợi ý: không ai xem thẻ gợi ý của từng hồ sơ (`record_suggestion`).
    """
    cau_hinh = get_settings()
    if len(du_lieu.case_ids) > cau_hinh.bulk_max_cases:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "bulk-too-many-cases",
                "message": (
                    f"Mỗi lần làm hàng loạt tối đa {cau_hinh.bulk_max_cases} hồ sơ — lô này có "
                    f"{len(du_lieu.case_ids)}. Chia thành nhiều lô."
                ),
            },
        )
    if len(set(du_lieu.case_ids)) != len(du_lieu.case_ids):
        raise HTTPException(
            status_code=422,
            detail={"code": "bulk-duplicate-cases", "message": "Danh sách hồ sơ có mục trùng nhau."},
        )
    buoc = _cac_thao_tac_hang_loat(session).get(du_lieu.activity_code)
    if buoc is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "bulk-activity-not-supported",
                "message": f"Bước '{du_lieu.activity_code}' không làm hàng loạt được.",
            },
        )
    thao_tac, cho_dat = buoc
    ngoai_canh = set(du_lieu.changes) - cho_dat
    if ngoai_canh:
        raise _bao_loi(
            FieldNotPermitted(
                ngoai_canh,
                f"Thao tác '{thao_tac.activity_label}' không đặt được {', '.join(sorted(ngoai_canh))}.",
            )
        )

    cac_muc: list[MucHangLoatRa] = []
    for ma in du_lieu.case_ids:
        ma_hien_thi: str | None = None
        try:
            # Nạp KÈM khóa dòng, như chính engine: trạng thái dùng để chọn cạnh không đổi được tới lúc
            # engine khóa lại trong cùng giao dịch. `get` có `with_for_update` luôn phát câu lệnh, kể
            # cả khi hồ sơ đã nằm trong phiên, nên lệnh khóa bên trong engine vẫn chạy
            ho_so = session.get(Request, ma, with_for_update=True)
            if ho_so is None:
                raise CaseNotFound(f"Không tìm thấy hồ sơ mang định danh {ma}.")
            ma_hien_thi = _ma_ho_so(ho_so)
            bo, tu = ho_so.rule_set_id, ho_so.current_state
            canh = _canh_cua_buoc(session, ho_so, du_lieu.activity_code, actor)
            if canh is None:
                raise TransitionNotAllowed(
                    f"Hồ sơ đang ở “{_nhan_trang_thai(session, bo, tu)}” — "
                    f"bước “{thao_tac.activity_label}” không đi từ trạng thái này."
                )
            den = canh.to_state
            ten_nguoi_duoc_giao = kiem_nguoi_duoc_giao(
                session, danh_ba, case_id=ma, to_state=den, actor=actor, changes=du_lieu.changes
            )
            ho_so = thuc_hien_chuyen(
                session,
                case_id=ma,
                to_state=den,
                actor=actor,
                note=du_lieu.note,
                changes=du_lieu.changes,
                assignee_label=ten_nguoi_duoc_giao,
                record_suggestion=False,
            )
        except TransitionError as loi:
            session.rollback()
            cac_muc.append(MucHangLoatRa(case_id=ma, code=ma_hien_thi, ok=False, error=_loi_hang_loat(loi)))
            continue
        except HTTPException as loi:
            # Danh bạ không trả lời, người được giao không nhận được việc — chỉ hồ sơ này hỏng
            session.rollback()
            chi_tiet = loi.detail if isinstance(loi.detail, dict) else {}
            cac_muc.append(
                MucHangLoatRa(
                    case_id=ma,
                    code=ma_hien_thi,
                    ok=False,
                    error=LoiHangLoatRa(
                        code=str(chi_tiet.get("code", "transition-error")),
                        message=str(chi_tiet.get("message", loi.detail)),
                    ),
                )
            )
            continue

        session.commit()
        hen_goi_y_neu_ve_phong(tac_vu_nen, session, ho_so)
        cac_muc.append(
            MucHangLoatRa(
                case_id=ma,
                code=ma_hien_thi,
                ok=True,
                to_state=den,
                to_state_label=_nhan_trang_thai(session, bo, den),
            )
        )

    return KetQuaHangLoatRa(
        activity_code=du_lieu.activity_code,
        total=len(cac_muc),
        succeeded=sum(m.ok for m in cac_muc),
        items=cac_muc,
    )


@router.post(
    "/requests/{case_id}/messages", summary="Nhắn tin trên hồ sơ (điều phối viên)",
    response_model=HoSoDieuPhoiRa,
    dependencies=[Depends(gioi_han_toc_do("send-message"))],
)
def nhan_tin(
    case_id: int, du_lieu: GuiLoiNhanVao, session: _Phien, actor: _Cua
) -> HoSoDieuPhoiRa:
    """Gửi một lời nhắn trên hồ sơ (#128).

    Cùng cửa nhìn thấy với trang chi tiết: điều phối viên mở được mọi hồ sơ, nên nhắn
    được trên mọi hồ sơ — kể cả hồ sơ đã chuyển về phòng ban. Lời nhắn không đổi hồ sơ
    (app/workflow/messages.py).
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
