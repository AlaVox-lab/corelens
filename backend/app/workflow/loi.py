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
#
# Đường thứ tư chỉ có ở lõi (#424): `GET …/transition-options` liệt kê MỌI cạnh rời trạng thái hiện tại kèm
# lý do không đi được — cùng cửa nhìn thấy, cùng hàm xét cạnh của engine (`xet_cac_canh`) mà
# `allowed_transitions` lọc lại, nên ứng dụng tầng trên hiển thị được vì sao một nút không có mà không đoán.

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import or_, select, true
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor
from app.auth.directory import KeycloakDirectory, get_directory
from app.db import get_session
from app.models.case import Request
from app.rules.dieu_kien import DieuKienKhongDat
from app.rules.guards import truong_can_nhap
from app.workflow.context import Actor
from app.workflow.coordination import vao_duoc_buong_lai
from app.workflow.department import vao_duoc_phong_ban
from app.workflow.engine import xet_cac_canh
from app.workflow.errors import GuardViolation, TransitionError
from app.workflow.khoa_trung_lap import KhoaGoi, chay_mot_lan, khoa_trung_lap
from app.workflow.phan_trang import ThamSoTrang, tham_so_trang
from app.workflow.routes import (
    ThamSoQuyTrinh,
    _bang_trang_thai,
    _dung_chi_tiet,
    _nhan,
    di_buoc,
    liet_ke_ho_so,
    xep_o_nhap,
)
from app.workflow.schemas import (
    BuocChuyenLoiVao,
    DanhSachHoSoRa,
    DieuKienCanhRa,
    HoSoChiTietRa,
    LuaChonCanhCuaHoSoRa,
    LuaChonCanhRa,
    LyDoChanRa,
    TrangThaiRa,
)

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
    q: Annotated[str | None, Query(description="Tìm theo mã, tiêu đề, người gửi, mô tả — không phân biệt dấu")] = None,
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


def _ly_do_ra(loi: TransitionError) -> LyDoChanRa:
    """Một lỗi engine sẽ ném thành một lý do: mã của ràng buộc nếu là ràng buộc, mã lớp lỗi nếu là quyền."""
    dk = loi.dieu_kien if isinstance(loi, DieuKienKhongDat) else None
    return LyDoChanRa(
        code=loi.guard_code if isinstance(loi, GuardViolation) else loi.code,
        category=loi.code,
        message=loi.message,
        condition=DieuKienCanhRa(
            id=dk.id, field=dk.field_code, operator=dk.operator, value=dk.value, description=dk.description
        ) if dk is not None else None,
    )


@router_loi_rieng.get("/requests/{case_id}/transition-options", response_model=LuaChonCanhCuaHoSoRa)
def lua_chon_canh_trong_pham_vi(case_id: int, session: _Phien, actor: _TacNhan) -> LuaChonCanhCuaHoSoRa:
    """Mọi cạnh rời trạng thái hiện tại của hồ sơ, mỗi cạnh kèm người gọi đi được không và vì sao (#424).

    Khác `allowed_transitions` của chi tiết hồ sơ — chỉ những cạnh đi được — ở chỗ cạnh bị chặn vẫn có mặt,
    kèm `reasons`: sai vai (`role-not-permitted`), cạnh chỉ hệ thống đi (`system-transition-only`), ràng buộc
    không cần nhập liệu (mã ràng buộc, ví dụ `actor-in-case-department`), điều kiện trên cạnh
    (`edge-condition` kèm trường, phép so, giá trị cần). Tập cạnh `allowed` trùng hệt `allowed_transitions`:
    hai đường dùng chung một hàm xét cạnh. `requires_input` là trường nhập liệu gửi trong `changes` khi đi.

    Chỉ đọc — không ghi nhật ký, không đổi hồ sơ. Phạm vi nhìn thấy như chi tiết hồ sơ: ngoài phạm vi 404.
    Hồ sơ ở trạng thái không còn cạnh nào đi ra thì `transitions` rỗng.
    """
    _kiem_nhin_thay(session, case_id, actor)
    ho_so = session.get(Request, case_id)
    states = _bang_trang_thai(session, ho_so.rule_set_id)
    hien_tai = states[ho_so.current_state]
    return LuaChonCanhCuaHoSoRa(
        case_id=ho_so.id,
        state=TrangThaiRa(code=hien_tai.code, label=hien_tai.label, is_terminal=hien_tai.is_terminal),
        transitions=[
            LuaChonCanhRa(
                activity_code=canh.activity_code,
                activity_label=canh.activity_label,
                to_state=canh.to_state,
                to_state_label=_nhan(states.get(canh.to_state), canh.to_state),
                keeps_state=canh.from_state == canh.to_state,
                is_system=canh.is_system,
                allowed=not ly_do,
                reasons=[_ly_do_ra(loi) for loi in ly_do],
                requires_input=xep_o_nhap(truong_can_nhap(canh.guard_codes)),
                requires_note=canh.requires_note,
                note_label=canh.note_label,
            )
            for canh, ly_do in xet_cac_canh(session, ho_so, actor)
        ],
    )


@router_loi_rieng.post("/requests/{case_id}/transitions", response_model=HoSoChiTietRa)
def buoc_chuyen_trong_pham_vi(
    case_id: int,
    du_lieu: BuocChuyenLoiVao,
    session: _Phien,
    actor: _TacNhan,
    danh_ba: Annotated[KeycloakDirectory, Depends(get_directory)],
    tac_vu_nen: BackgroundTasks,
    khoa: Annotated[KhoaGoi | None, Depends(khoa_trung_lap)],
) -> HoSoChiTietRa:
    """Đi một bước trên hồ sơ trong phạm vi của người gọi — mọi cạnh mà vai và phạm vi của người gọi đi
    được theo bảng `transitions`.

    Ngoài phạm vi: 404. Trong phạm vi mà cạnh không có, sai vai hay vướng ràng buộc: lỗi của engine
    (409, 403, 422) — cùng mã như ở mọi cửa khác.

    Tiêu đề `Idempotency-Key` tùy chọn (#426): gọi lặp cùng khóa, cùng lệnh nhận lại phản hồi lần đầu, không
    đi bước lần hai (app/workflow/khoa_trung_lap.py). Dấu xong của khóa ghi trong cùng giao dịch với lần chuyển
    qua móc `truoc_commit` của `di_buoc`.
    """
    def lam(danh_dau) -> HoSoChiTietRa:
        _kiem_nhin_thay(session, case_id, actor)
        ho_so = di_buoc(
            session, danh_ba, tac_vu_nen, actor, case_id,
            to_state=du_lieu.to_state, note=du_lieu.note, changes=du_lieu.changes,
            truoc_commit=(lambda h: danh_dau(h.id)),
        )
        return _dung_chi_tiet(session, ho_so, actor)

    def dung_lai(ma: int) -> HoSoChiTietRa:
        _kiem_nhin_thay(session, ma, actor)
        return _dung_chi_tiet(session, session.get(Request, ma), actor)

    return chay_mot_lan(
        session, khoa, than=du_lieu, tham_so_duong={"case_id": case_id}, lam=lam, dung_lai=dung_lai
    )
