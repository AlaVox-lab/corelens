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

import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor
from app.auth.directory import KeycloakDirectory, get_directory
from app.db import get_session
from app.models.case import EventLog, Request
from app.models.workflow_config import Department, Priority, State, Transition
from app.workflow.assignment import (
    kiem_nguoi_duoc_giao,
    trang_thai_hang_doi_phong_ban,
    vai_tro_phong_ban,
)
from app.workflow.contact import lien_he_nguoi_gui
from app.workflow.context import Actor
from app.workflow.coordination import _luc_vao_trang_thai, _nhan_co_ma
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
    HangDoiPhongBanRa,
    HoSoPhongBanRa,
    LienHeNguoiGuiRa,
    MucHangDoiPhongBanRa,
    NhanCoMa,
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
    return bool(actor.roles & vai_tro_phong_ban(session, get_active_rule_set(session).id))


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
    )


# ---------------------------------------------------------------------------
# Hàng đợi
# ---------------------------------------------------------------------------


@router.get("/queue", response_model=HangDoiPhongBanRa)
def hang_doi(
    session: _Phien,
    actor: _Cua,
    state: Annotated[str | None, Query(description="Chỉ lấy một trạng thái")] = None,
    mine: Annotated[bool, Query(description="Chỉ lấy hồ sơ giao cho người đang xem")] = False,
) -> HangDoiPhongBanRa:
    """Hồ sơ của phòng mình, quá hạn lên đầu rồi tới hồ sơ gần hạn nhất.

    Khác hàng đợi điều phối — xếp theo thời gian chờ — vì ở đây đồng hồ SLA đang chạy:
    thời hạn còn lại mới là con số người trong phòng cần nhìn. Hồ sơ chưa có ngưỡng SLA
    xếp sau cùng, theo thời gian chờ.

    Chỉ hồ sơ thuộc phòng của người đang xem. Số đếm trên nút lọc đi theo cùng bộ lọc
    `mine`, để con số và danh sách không bao giờ kể hai chuyện khác nhau.

    Hồ sơ đang ở lượt người gửi (nhóm theo dõi, #99) xếp sau mọi hồ sơ có việc phải làm.
    """
    bo = get_active_rule_set(session)
    co_viec = trang_thai_hang_doi_phong_ban(session, bo.id)
    theo_doi = _trang_thai_theo_doi(session, bo.id, co_viec)
    ma_theo_doi = {t.code for t in theo_doi}
    cac_trang_thai = sorted(co_viec + theo_doi, key=lambda t: t.display_order)
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
        Request.rule_set_id == bo.id,
        Request.department_code.in_(actor.departments),
        Request.current_state.in_(ma_hang_doi),
    ]
    if mine:
        dieu_kien.append(Request.assignee_id == actor.id)

    dem = dict(
        session.execute(
            select(Request.current_state, func.count())
            .where(*dieu_kien)
            .group_by(Request.current_state)
        ).all()
    )

    luc_vao = _luc_vao_trang_thai().label("luc_vao")
    truy_van = select(Request, luc_vao).where(*dieu_kien)
    if state:
        truy_van = truy_van.where(Request.current_state == state)

    states = _bang_trang_thai(session, bo.id)
    cac_muc = []
    for ho_so, vao in session.execute(truy_van).all():
        tom_tat = _tom_tat(session, ho_so, states)
        cac_muc.append(
            MucHangDoiPhongBanRa(
                **tom_tat,
                requester_label=ho_so.requester_label,
                priority=_nhan_co_ma(
                    session.get(Priority, ho_so.priority_code) if ho_so.priority_code else None
                ),
                state_entered_at=vao,
                assignee_id=ho_so.assignee_id,
                assignee_label=ho_so.assignee_label,
                assigned_to_me=ho_so.assignee_id == actor.id,
            )
        )

    def do_gap(m: MucHangDoiPhongBanRa) -> tuple:
        con_lai = (
            m.sla_limit_seconds - m.sla_running_seconds
            if m.sla_limit_seconds is not None
            else math.inf
        )
        return (m.state.code in ma_theo_doi, not m.sla_overdue, con_lai, m.state_entered_at, m.id)

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
                watch_only=t.code in ma_theo_doi,
            )
            for t in cac_trang_thai
        ],
        items=sorted(cac_muc, key=do_gap),
    )


# ---------------------------------------------------------------------------
# Hồ sơ
# ---------------------------------------------------------------------------


@router.get("/requests/{case_id}", response_model=HoSoPhongBanRa)
def chi_tiet(case_id: int, session: _Phien, actor: _Cua) -> HoSoPhongBanRa:
    """Chi tiết một hồ sơ của phòng mình, kèm những thao tác người này làm được.

    Mở được cả hồ sơ đã rời hàng đợi mà vẫn thuộc phòng — vừa hoàn thành, hay vừa bị
    trả về điều phối — để người vừa bấm nút thấy được kết quả.
    """
    ho_so = session.get(Request, case_id)
    if ho_so is None or ho_so.department_code not in actor.departments:
        raise _khong_thay()
    return _dung_chi_tiet(session, ho_so, actor)


@router.get(
    "/requests/{case_id}/requester-contact",
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
) -> LienHeNguoiGuiRa:
    """Email và số điện thoại của người gửi, tra từ danh bạ lúc gọi (#131).

    Cùng cửa với trang chi tiết: hồ sơ của phòng khác trả 404 — không lộ ra hồ sơ đó có
    tồn tại, càng không lộ liên hệ của người gửi nó.
    """
    ho_so = session.get(Request, case_id)
    if ho_so is None or ho_so.department_code not in actor.departments:
        raise _khong_thay()
    return lien_he_nguoi_gui(danh_ba, ho_so)


@router.post("/requests/{case_id}/transitions", response_model=HoSoPhongBanRa)
def chuyen_trang_thai(
    case_id: int,
    du_lieu: ChuyenTrangThaiCoTruongVao,
    session: _Phien,
    actor: _Cua,
    danh_ba: Annotated[KeycloakDirectory, Depends(get_directory)],
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
    return _dung_chi_tiet(session, ho_so, actor)


@router.post("/requests/{case_id}/messages", response_model=HoSoPhongBanRa)
def nhan_tin(
    case_id: int, du_lieu: GuiLoiNhanVao, session: _Phien, actor: _Cua
) -> HoSoPhongBanRa:
    """Gửi một lời nhắn trên hồ sơ của phòng mình (#128).

    Cùng cửa nhìn thấy với trang chi tiết: hồ sơ của phòng khác trả 404. Lời nhắn không
    đổi hồ sơ — kể cả khi trả lời một câu "Hỏi tiến độ"; xem app/workflow/messages.py.
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
