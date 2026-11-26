# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Điểm cuối của buồng lái phòng ban (#83).
#
# Nửa sau của quy trình: từ lúc điều phối viên chuyển hồ sơ về phòng ban, mọi việc
# thuộc về hai vai trong phòng — người giao việc và người nhận việc. Một buồng lái cho
# cả hai, vì họ dùng chung hàng đợi và chung trang chi tiết; khác nhau chỉ ở danh sách
# nút, mà danh sách đó do engine sinh.
#
# KHÔNG CÓ TÊN VAI TRÒ NÀO TRONG TỆP NÀY. Ai vào được buồng lái là người giao việc hoặc
# nhận việc — hai tập suy từ bộ quy tắc ở app/workflow/assignment.py (#84). Trạng thái
# nào vào hàng đợi là trạng thái mà hai vai đó có cạnh đi ra.
#
# Cùng hai loại quyền như buồng lái điều phối (#82), không trộn:
#
#   Nhìn thấy hồ sơ — cửa ở đây: người gọi phải thuộc phòng đang giữ hồ sơ. Hồ sơ của
#                     phòng khác trả 404, để không ai dò được hồ sơ nào có thật.
#   Đi một cạnh     — engine quyết, bằng `transition_roles` và ràng buộc trên cạnh, kể
#                     cả `actor-in-case-department`. Tầng này không kiểm lại.

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi import Request as YeuCauHttp
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor
from app.kiem_toan import XEM_HO_SO, XEM_LIEN_HE, ghi_truy_cap
from app.auth.directory import KeycloakDirectory, get_directory
from app.db import get_session
from app.intelligence.goi_y import goi_y_nguoi_xu_ly
from app.intelligence.nguoi_xu_ly import dang_cho_giao_viec, hen_goi_y_neu_ve_phong
from app.models.case import EventLog, Request
from app.rate_limit import gioi_han_toc_do
from app.models.workflow_config import Department, Priority, State, Transition
from app.workflow.assignment import (
    kiem_nguoi_duoc_giao,
    trang_thai_hang_doi_phong_ban,
    vai_tro_phong_ban,
)
from app.workflow.contact import lien_he_nguoi_gui
from app.workflow.context import Actor
from app.workflow.coordination import _luc_vao_trang_thai, _nhan_co_ma
from app.workflow.danh_gia import danh_gia_cua
from app.workflow.engine import (
    get_active_rule_set,
    ma_quy_trinh_ung_dung,
    my_primary_steps,
    rule_sets_in_use,
)
from app.workflow.engine import perform_transition as thuc_hien_chuyen
from app.workflow.errors import TransitionError
from app.workflow.messages import MessageRejected, gui_loi_nhan
from app.workflow.routes import (
    _buoc_cua_toi,
    _bang_trang_thai_nhieu,
    _bao_loi,
    _bao_loi_nhan,
    _du_lieu_chi_tiet,
    _giu_danh_muc,
    _gop_theo_ma,
    _ma_ho_so,
    _o_trang_thai,
    _tom_tat,
    goi_y_ra,
)
from app.rules.han_cho import canh_tu_di_theo_trang_thai, da_toi_luc_bao, giay_da_o_trang_thai
from app.rules.sla import da_chay_giay, gioi_han_giay, sap_het_han
from app.workflow.phan_trang import ThamSoTrang, cat_trang, khop_tim, tham_so_trang
from app.workflow.schemas import (
    ChuyenTrangThaiCoTruongVao,
    GuiLoiNhanVao,
    HangDoiPhongBanRa,
    HoSoPhongBanRa,
    LienHeNguoiGuiRa,
    MucHangDoiPhongBanRa,
    NhanCoMa,
    NhomDoGapRa,
    NhomHangDoiRa,
)

router = APIRouter(prefix="/department", tags=["Buồng lái phòng ban"])

_Phien = Annotated[Session, Depends(get_session)]


def vao_duoc_phong_ban(session: Session, actor: Actor) -> bool:
    """Người này có mở được buồng lái phòng ban không. Dùng cho `/me`.

    Cần cả hai: mang một vai trò của phòng ban, và thuộc ít nhất một phòng. Trưởng
    phòng chưa được xếp vào phòng nào thì không có hàng đợi nào để xem.
    """
    if not actor.departments:
        return False
    bo = get_active_rule_set(session, ma_quy_trinh_ung_dung(session))
    return bool(actor.roles & vai_tro_phong_ban(session, bo.id))


def _cua(
    session: _Phien, actor: Annotated[Actor, Depends(current_actor)]
) -> Actor:
    if not vao_duoc_phong_ban(session, actor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Buồng lái phòng ban dành cho người giao việc và người xử lý của một phòng.",
        )
    return actor


_Cua = Annotated[Actor, Depends(_cua)]


def _trang_thai_theo_doi(
    session: Session, rule_set_id: int, hang_doi: list[State]
) -> list[State]:
    """Trạng thái phòng ban chỉ THEO DÕI: hồ sơ đang ở lượt người gửi nhưng sẽ quay về (#99).

    Thiếu nhóm này thì người xử lý bấm "Yêu cầu bổ sung thông tin" xong, hồ sơ biến khỏi
    hàng đợi của họ — họ quên mình đang có việc treo. Suy từ bộ quy tắc, không liệt kê
    cứng. Một trạng thái được theo dõi khi đủ hai điều:

    1. Cạnh của vai trò phòng ban DẪN TỚI nó, và nó chưa nằm trong hàng đợi
    2. Từ nó có cạnh quay về một trạng thái của hàng đợi

    Không cần loại riêng trạng thái kết thúc: trạng thái kết thúc không có cạnh nào đi
    ra, nên không bao giờ thỏa điều thứ hai. Phép thử đột biến xác nhận một phép loại
    riêng là thừa — gỡ nó đi không bài nào đổ.

    Với bộ quy tắc hiện tại: *Chờ bổ sung thông tin* (bổ sung xong thì về đang xử lý)
    và *Hoàn tất* (mở lại thì về đang xử lý). *Bị phòng ban từ chối* bị loại tự nhiên vì
    từ đó hồ sơ chỉ về điều phối, không về phòng.
    """
    ma_hang_doi = {t.code for t in hang_doi}
    vai_tro = vai_tro_phong_ban(session, rule_set_id)
    canh = session.scalars(
        select(Transition).where(
            Transition.rule_set_id == rule_set_id, Transition.is_system.is_(False)
        )
    ).all()

    dich = {
        t.to_state for t in canh if t.from_state in ma_hang_doi and t.role_codes & vai_tro
    } - ma_hang_doi
    quay_ve = {t.from_state for t in canh if t.to_state in ma_hang_doi}

    return list(
        session.scalars(
            select(State)
            .where(
                State.rule_set_id == rule_set_id,
                State.code.in_(dich & quay_ve),
            )
            .order_by(State.display_order)
        ).all()
    )


def _khong_thay() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "case-not-found", "message": "Không tìm thấy hồ sơ trong phòng của bạn."},
    )


def _dung_chi_tiet(session: Session, ho_so: Request, actor: Actor) -> HoSoPhongBanRa:
    luc_vao = session.scalar(
        select(func.max(EventLog.timestamp)).where(EventLog.case_id == ho_so.id)
    )
    uu_tien = session.get(Priority, ho_so.priority_code) if ho_so.priority_code else None
    return HoSoPhongBanRa(
        **_du_lieu_chi_tiet(session, ho_so, actor),
        requester_label=ho_so.requester_label,
        priority=_nhan_co_ma(uu_tien),
        state_entered_at=luc_vao or ho_so.created_at,
        assignee_label=ho_so.assignee_label,
        assigned_to_me=ho_so.assignee_id == actor.id,
        suggested_assignee=(
            goi_y_ra(goi_y_nguoi_xu_ly(session, ho_so))
            if dang_cho_giao_viec(session, ho_so)
            else None
        ),
        # Đánh giá của người gửi (#433) — điểm kèm nhận xét, chỉ đọc
        feedback=danh_gia_cua(session, ho_so.id),
    )


# ---------------------------------------------------------------------------
# Hàng đợi
# ---------------------------------------------------------------------------


@dataclass
class _Hang:
    """Một hồ sơ của hàng đợi kèm các cờ hạn cần để chia nhóm và xếp — tính cho cả hàng đợi,
    rẻ hơn nhiều so với tóm tắt đầy đủ mà chỉ hồ sơ của trang mới được dựng."""

    ho_so: Request
    vao: dt.datetime
    qua_han: bool
    sap_han: bool
    bao_tu_di: bool
    con_lai: float
    nhom: str


# Nhóm độ gấp cố định của hàng đợi phòng ban — tên nhóm, không phải tên trạng thái. Nhóm theo
# trạng thái (đồng hồ chưa chạy) lấy nhãn từ bộ quy tắc.
_NHOM_HAN = {"qua-han": "Quá hạn", "sap-het-han": "Sắp hết hạn", "trong-han": "Trong hạn"}
_NHOM_THEO_DOI = ("cho-nguoi-gui", "Chờ người gửi")


@router.get("/queue", summary="Hàng đợi của phòng ban", response_model=HangDoiPhongBanRa)
def hang_doi(
    session: _Phien,
    actor: _Cua,
    trang: Annotated[ThamSoTrang, Depends(tham_so_trang)],
    state: Annotated[str | None, Query(description="Chỉ lấy một trạng thái")] = None,
    mine: Annotated[bool, Query(description="Chỉ lấy hồ sơ giao cho người đang xem")] = False,
    group: Annotated[str | None, Query(description="Chỉ một nhóm độ gấp")] = None,
    q: Annotated[str | None, Query(description="Tìm theo mã, tiêu đề, người gửi, mô tả — không phân biệt dấu")] = None,
    request_type: Annotated[str | None, Query(description="Chỉ một loại yêu cầu")] = None,
    priority: Annotated[str | None, Query(description="Chỉ một mức ưu tiên")] = None,
    sort: Annotated[
        Literal["gap", "cho", "moi"],
        Query(description="gap: độ gấp · cho: chờ lâu nhất · moi: mới nhất"),
    ] = "gap",
    needs_action: Annotated[bool, Query(description="Chỉ hồ sơ đang chờ chính người xem")] = False,
) -> HangDoiPhongBanRa:
    """Hồ sơ của phòng mình, mặc định quá hạn lên đầu rồi tới hồ sơ gần hạn nhất (#232).

    Khác hàng đợi điều phối — xếp theo thời gian chờ — vì ở đây đồng hồ SLA đang chạy:
    thời hạn còn lại mới là con số người trong phòng cần nhìn. Hồ sơ chưa có ngưỡng SLA
    xếp sau cùng, theo thời gian chờ. Hồ sơ đang ở lượt người gửi (nhóm theo dõi) xếp sau
    mọi hồ sơ có việc phải làm (#99).

    Nhóm độ gấp — quá hạn, sắp hết hạn, trong hạn, từng trạng thái đồng hồ chưa chạy, chờ người
    gửi — chia ở đây trên cả hàng đợi đã lọc, để số trên dải lọc đúng dù chỉ trả một trang. Hàng
    đợi chỉ gồm hồ sơ đang mở của phòng, nên lớn theo khối việc chứ không theo lịch sử; tóm tắt
    đầy đủ — phần tốn nhất — chỉ dựng cho hồ sơ của trang.

    Số đếm trạng thái và nhóm đi theo cùng bộ lọc `mine`, để con số và danh sách không bao giờ
    kể hai chuyện khác nhau.

    Gồm hồ sơ của mọi bộ quy tắc còn hồ sơ đang mở (#299), mỗi hồ sơ xét theo trạng thái hàng đợi
    và trạng thái theo dõi của chính bộ nó — như hàng đợi điều phối.
    """
    cac_bo = rule_sets_in_use(session, ma_quy_trinh_ung_dung(session))
    co_viec_bo = {bo: trang_thai_hang_doi_phong_ban(session, bo) for bo in cac_bo}
    theo_doi_bo = {bo: _trang_thai_theo_doi(session, bo, co_viec_bo[bo]) for bo in cac_bo}
    ma_theo_doi = {(bo, t.code) for bo, ds in theo_doi_bo.items() for t in ds}
    co_viec = _gop_theo_ma(list(co_viec_bo.values()))
    cac_trang_thai = _gop_theo_ma(
        [sorted(co_viec_bo[bo] + theo_doi_bo[bo], key=lambda t: t.display_order) for bo in cac_bo]
    )
    ma_hang_doi = [t.code for t in cac_trang_thai]

    if state is not None and state not in ma_hang_doi:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "state-not-in-queue",
                "message": f"Trạng thái '{state}' không thuộc hàng đợi phòng ban.",
            },
        )

    dieu_kien = [
        _o_trang_thai(
            {bo: [t.code for t in co_viec_bo[bo] + theo_doi_bo[bo]] for bo in cac_bo}
        ),
        Request.department_code.in_(actor.departments),
    ]
    if mine:
        # Việc của tôi gồm cả việc của người vắng đang ủy quyền cho tôi (#252) — tác nhân chỉ nhận
        # ủy quyền của phòng mình, nên điều kiện phòng ngay trên vẫn giữ đúng phạm vi
        dieu_kien.append(Request.assignee_id.in_([actor.id, *(u.nguoi_vang_id for u in actor.lam_thay)]))

    luc_vao = _luc_vao_trang_thai().label("luc_vao")
    ca_hang = session.execute(select(Request, luc_vao, giay_da_o_trang_thai()).where(*dieu_kien)).all()
    buoc = my_primary_steps(session, [ho_so for ho_so, _, _ in ca_hang], actor)
    _danh_muc = _giu_danh_muc(session, cac_bo)
    canh_tu_di = {bo: canh_tu_di_theo_trang_thai(session, bo) for bo in cac_bo}

    def hang(ho_so: Request, vao: dt.datetime, da_o: int) -> _Hang:
        gioi_han = gioi_han_giay(session, ho_so)
        da_dem = da_chay_giay(session, ho_so)
        qua = gioi_han is not None and da_dem > gioi_han
        sap = not qua and sap_het_han(session, ho_so)
        chay = ho_so.sla_segment_since is not None or ho_so.sla_running_seconds > 0
        canh = canh_tu_di[ho_so.rule_set_id].get(ho_so.current_state)
        if (ho_so.rule_set_id, ho_so.current_state) in ma_theo_doi:
            nhom = _NHOM_THEO_DOI[0]
        elif qua:
            nhom = "qua-han"
        elif sap:
            nhom = "sap-het-han"
        elif chay:
            nhom = "trong-han"
        else:
            nhom = ho_so.current_state
        return _Hang(
            ho_so=ho_so,
            vao=vao,
            qua_han=qua,
            sap_han=sap,
            bao_tu_di=canh is not None and da_toi_luc_bao(canh, da_o),
            con_lai=(gioi_han - da_dem) if gioi_han is not None else math.inf,
            nhom=nhom,
        )

    ca = [hang(h, vao, da_o) for h, vao, da_o in ca_hang]
    cho_toi = [d for d in ca if buoc[d.ho_so.id] is not None]

    da_loc = [
        d
        for d in ca
        if khop_tim(q, d.ho_so.title, d.ho_so.requester_label, d.ho_so.description, _ma_ho_so(d.ho_so))
        and (not request_type or d.ho_so.request_type_code == request_type)
        and (not priority or d.ho_so.priority_code == priority)
        and (not needs_action or buoc[d.ho_so.id] is not None)
    ]

    # Số đếm trên cả tập đã lọc, trước khi lọc theo nhóm hay trạng thái
    dem: dict[str, int] = {}
    for d in da_loc:
        dem[d.ho_so.current_state] = dem.get(d.ho_so.current_state, 0) + 1
    nhan_nhom = {**_NHOM_HAN, **{t.code: t.label for t in co_viec}, _NHOM_THEO_DOI[0]: _NHOM_THEO_DOI[1]}
    nhom_do_gap = []
    for ma in nhan_nhom:
        trong = [d for d in da_loc if d.nhom == ma]
        if trong:
            nhom_do_gap.append(
                NhomDoGapRa(
                    code=ma,
                    label=nhan_nhom[ma],
                    count=len(trong),
                    overdue=sum(1 for d in trong if d.qua_han),
                    due_soon=sum(1 for d in trong if (d.sap_han or d.bao_tu_di) and not d.qua_han),
                )
            )

    if group:
        da_loc = [d for d in da_loc if d.nhom == group]
    if state:
        da_loc = [d for d in da_loc if d.ho_so.current_state == state]

    # Giao diện chia trang thành các nhóm độ gấp, nên mọi cách xếp đều xếp theo thứ tự nhóm
    # trước: trang sau nối tiếp đúng nhóm trang trước dừng, cách xếp chỉ đổi thứ tự trong nhóm
    thu_tu = {ma: i for i, ma in enumerate(nhan_nhom)}
    if sort == "cho":
        da_loc.sort(key=lambda d: (thu_tu[d.nhom], d.vao, d.ho_so.id))
    elif sort == "moi":
        da_loc.sort(key=lambda d: (thu_tu[d.nhom], -d.ho_so.created_at.timestamp(), -d.ho_so.id))
    else:
        da_loc.sort(key=lambda d: (thu_tu[d.nhom], d.con_lai, d.vao, d.ho_so.id))

    bang = _bang_trang_thai_nhieu(session, cac_bo)
    cac_muc = []
    for d in cat_trang(da_loc, trang):
        ho_so = d.ho_so
        cac_muc.append(
            MucHangDoiPhongBanRa(
                **_tom_tat(session, ho_so, bang[ho_so.rule_set_id]),
                **_buoc_cua_toi(buoc[ho_so.id]),
                requester_label=ho_so.requester_label,
                priority=_nhan_co_ma(
                    session.get(Priority, ho_so.priority_code) if ho_so.priority_code else None
                ),
                state_entered_at=d.vao,
                assignee_id=ho_so.assignee_id,
                assignee_label=ho_so.assignee_label,
                assigned_to_me=ho_so.assignee_id == actor.id,
                urgency=d.nhom,
            )
        )

    phong = session.scalars(
        select(Department)
        .where(Department.code.in_(actor.departments))
        .order_by(Department.display_order)
    ).all()

    return HangDoiPhongBanRa(
        departments=[NhanCoMa(code=p.code, label=p.label) for p in phong],
        groups=[
            NhomHangDoiRa(
                code=t.code,
                label=t.label,
                count=dem.get(t.code, 0),
                watch_only=(t.rule_set_id, t.code) in ma_theo_doi,
            )
            for t in cac_trang_thai
        ],
        urgency_groups=nhom_do_gap,
        items=cac_muc,
        total=len(da_loc),
        offset=trang.offset,
        limit=trang.limit,
        waiting_me=len(cho_toi),
        urgent=any(d.qua_han or d.bao_tu_di for d in cho_toi),
    )


# ---------------------------------------------------------------------------
# Hồ sơ
# ---------------------------------------------------------------------------


@router.get("/requests/{case_id}", summary="Chi tiết hồ sơ (phòng ban)", response_model=HoSoPhongBanRa)
def chi_tiet(case_id: int, session: _Phien, actor: _Cua, yeu_cau: YeuCauHttp) -> HoSoPhongBanRa:
    """Chi tiết một hồ sơ của phòng mình, kèm những thao tác người này làm được.

    Mở được cả hồ sơ đã rời hàng đợi mà vẫn thuộc phòng — vừa hoàn thành, hay vừa bị
    trả về điều phối — để người vừa bấm nút thấy được kết quả.

    Mỗi lần mở ghi một dòng nhật ký truy cập (#431, app/kiem_toan.py), trừ hồ sơ do chính người gọi gửi.
    """
    ho_so = session.get(Request, case_id)
    if ho_so is None or ho_so.department_code not in actor.departments:
        raise _khong_thay()
    ra = _dung_chi_tiet(session, ho_so, actor)
    ghi_truy_cap(yeu_cau, actor, XEM_HO_SO, ho_so=ho_so)
    return ra


@router.get(
    "/requests/{case_id}/requester-contact", summary="Liên hệ người gửi (phòng ban)",
    response_model=LienHeNguoiGuiRa,
    responses={
        404: {"description": "Không có hồ sơ này trong phòng của người gọi"},
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

    Cùng cửa với trang chi tiết: hồ sơ của phòng khác trả 404 — không lộ ra hồ sơ đó có
    tồn tại, càng không lộ liên hệ của người gửi nó. Mỗi lần tra được ghi nhật ký truy cập (#431).
    """
    ho_so = session.get(Request, case_id)
    if ho_so is None or ho_so.department_code not in actor.departments:
        raise _khong_thay()
    ra = lien_he_nguoi_gui(danh_ba, ho_so)
    ghi_truy_cap(yeu_cau, actor, XEM_LIEN_HE, ho_so=ho_so)
    return ra


@router.post("/requests/{case_id}/transitions", summary="Đi một bước trên hồ sơ (phòng ban)", response_model=HoSoPhongBanRa)
def chuyen_trang_thai(
    case_id: int,
    du_lieu: ChuyenTrangThaiCoTruongVao,
    session: _Phien,
    actor: _Cua,
    danh_ba: Annotated[KeycloakDirectory, Depends(get_directory)],
    tac_vu_nen: BackgroundTasks,
) -> HoSoPhongBanRa:
    """Thực hiện một thao tác, có kèm trường quyết định.

    Người được giao phải nhận được việc của phòng — kiểm bằng danh bạ trước khi gọi
    engine, và tên của họ lấy từ danh bạ chứ không từ trình duyệt. Mọi phép kiểm còn
    lại nằm trong engine.

    Cửa nhìn thấy đọc cột phòng ban bằng một câu truy vấn cột, không nạp đối tượng hồ
    sơ: nạp trước thì lệnh khóa dòng bên trong engine có nguy cơ không được phát.
    """
    phong = session.scalar(select(Request.department_code).where(Request.id == case_id))
    if phong is None or phong not in actor.departments:
        raise _khong_thay()

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
    hen_goi_y_neu_ve_phong(tac_vu_nen, session, ho_so)
    return _dung_chi_tiet(session, ho_so, actor)


@router.post(
    "/requests/{case_id}/messages", summary="Nhắn tin trên hồ sơ (phòng ban)",
    response_model=HoSoPhongBanRa,
    dependencies=[Depends(gioi_han_toc_do("send-message"))],
)
def nhan_tin(
    case_id: int, du_lieu: GuiLoiNhanVao, session: _Phien, actor: _Cua
) -> HoSoPhongBanRa:
    """Gửi một lời nhắn trên hồ sơ của phòng mình (#128).

    Cùng cửa nhìn thấy với trang chi tiết: hồ sơ của phòng khác trả 404. Lời nhắn không
    đổi hồ sơ — kể cả khi trả lời một câu "Hỏi tiến độ" (app/workflow/messages.py).
    """
    ho_so = session.get(Request, case_id)
    if ho_so is None or ho_so.department_code not in actor.departments:
        raise _khong_thay()
    try:
        gui_loi_nhan(session, ho_so, actor, du_lieu.kind, du_lieu.body)
    except MessageRejected as loi:
        session.rollback()
        raise _bao_loi_nhan(loi) from loi

    session.commit()
    return _dung_chi_tiet(session, ho_so, actor)
