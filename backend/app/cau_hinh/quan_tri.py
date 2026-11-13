# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Màn quản trị cấu hình quy trình (#255): xem bộ quy tắc đang chạy, sửa phần cấu hình ít rủi ro.
#
# Phạm vi chốt với giảng viên ngày 13/11/2026:
#
#   - XEM: trạng thái, cạnh chuyển kèm vai trò và ràng buộc, loại yêu cầu, mức ưu tiên, phòng ban,
#     lịch làm việc, cùng nhật ký các lần sửa.
#   - SỬA: hạn chuẩn, ân hạn, ngưỡng sắp hết hạn, tên, mô tả, bật/tắt và phòng mặc định của loại
#     yêu cầu; tên và hệ số hạn của mức ưu tiên; tên, mô tả, bật/tắt của phòng ban.
#   - KHÔNG: thêm hay xóa dòng, sửa lịch, sửa đồ thị quy trình — đồ thị chỉ đổi bằng bộ quy tắc phiên
#     bản mới (docs/ARCHITECTURE.md mục 5.4).
#
# Đây là "dữ liệu dùng chung" theo mục 5.4: sửa thẳng dòng, áp ngay cho MỌI hồ sơ, kể cả hồ sơ đang
# mở — hạn của hồ sơ tính lúc đọc từ `request_types.sla_hours` × `priorities.sla_factor_percent`, nên
# không có bản sao nào phải cập nhật theo. Vì áp ngay nên màn hỏi trước: mỗi lần sửa có một lượt chạy
# thử (`dry_run`) đi trọn đường thật — ghi, kiểm, đếm hồ sơ đang mở bị ảnh hưởng — rồi hoàn tác.
#
# Mỗi lần sửa, trong MỘT giao dịch: ghi dòng cấu hình → `kiem_tra_cau_hinh()` (hỏng thì hoàn tác cả
# lần sửa, trả câu lỗi của hàm) → một dòng `config_changes` cho mỗi trường đổi giá trị.
#
# Danh sách trường sửa được dưới đây là ranh giới kiến trúc (cột nào an toàn để sửa lúc chạy), không
# phải dữ liệu nghiệp vụ: giá trị của chúng vẫn nằm trong bảng.

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.auth.dependencies import VAI_TRO_QUAN_TRI, require_roles
from app.db import get_session
from app.models.case import Request
from app.models.quan_tri import ConfigChange
from app.models.workflow_config import (
    Department,
    Guard,
    Priority,
    RequestType,
    RequestTypeRouting,
    Role,
    State,
    Transition,
)
from app.workflow.context import Actor
from app.workflow.engine import get_active_rule_set

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/config", tags=["Quản trị cấu hình"])

QuanTriVien = Annotated[Actor, Depends(require_roles(VAI_TRO_QUAN_TRI))]
Phien = Annotated[Session, Depends(get_session)]

# Số dòng nhật ký sửa trả về cùng màn xem
SO_DONG_NHAT_KY = 50


# ---------------------------------------------------------------------------
# Trường sửa được
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TruongSua:
    """Một cột sửa được trên màn quản trị."""

    nhan: str
    kieu: type
    toi_thieu: int | None = None
    toi_da: int | None = None
    # Đổi trường này là đổi hạn của hồ sơ đang mở — màn báo số hồ sơ bị ảnh hưởng trước khi lưu
    doi_han: bool = False
    # Ô bỏ trống được (mô tả)
    bo_trong: bool = False


@dataclass(frozen=True)
class LoaiDanhMuc:
    """Một bảng cấu hình mở cho màn quản trị."""

    bang: str
    nhan: str
    mo_hinh: type
    # Cột của `requests` trỏ tới bảng này — để đếm hồ sơ đang mở bị ảnh hưởng
    cot_ho_so: Any
    truong: dict[str, TruongSua] = field(default_factory=dict)


_TEN = TruongSua("Tên", str)
_MO_TA = TruongSua("Mô tả", str, bo_trong=True)
_DANG_DUNG = TruongSua("Đang dùng", bool)

DANH_MUC: dict[str, LoaiDanhMuc] = {
    "request-types": LoaiDanhMuc(
        bang="request_types",
        nhan="Loại yêu cầu",
        mo_hinh=RequestType,
        cot_ho_so=Request.request_type_code,
        truong={
            "label": _TEN,
            "description": _MO_TA,
            "sla_hours": TruongSua("Hạn chuẩn (giờ làm việc)", int, 1, 8760, doi_han=True),
            "sla_grace_hours": TruongSua("Ân hạn (giờ làm việc)", int, 0, 8760, doi_han=True),
            "sla_warn_percent": TruongSua("Ngưỡng sắp hết hạn (%)", int, 1, 99, doi_han=True),
            "is_active": _DANG_DUNG,
            # Không phải cột của `request_types`: dòng mặc định trong `request_type_routing`
            "default_department": TruongSua("Phòng xử lý mặc định", str),
        },
    ),
    "priorities": LoaiDanhMuc(
        bang="priorities",
        nhan="Mức ưu tiên",
        mo_hinh=Priority,
        cot_ho_so=Request.priority_code,
        truong={
            "label": _TEN,
            "sla_factor_percent": TruongSua("Hệ số hạn (%)", int, 1, 1000, doi_han=True),
        },
    ),
    "departments": LoaiDanhMuc(
        bang="departments",
        nhan="Phòng ban",
        mo_hinh=Department,
        cot_ho_so=Request.department_code,
        truong={"label": _TEN, "description": _MO_TA, "is_active": _DANG_DUNG},
    ),
}


def _loi(ma: str, thong_diep: str, ma_http: int = status.HTTP_422_UNPROCESSABLE_CONTENT) -> HTTPException:
    return HTTPException(status_code=ma_http, detail={"code": ma, "message": thong_diep})


def _chuan_hoa(ten: str, truong: TruongSua, gia_tri: Any) -> Any:
    """Kiểm kiểu và khoảng của một giá trị gửi lên; trả giá trị đã chuẩn hóa."""
    if truong.kieu is bool:
        if not isinstance(gia_tri, bool):
            raise _loi("gia-tri-khong-hop-le", f"{truong.nhan}: phải là có hoặc không.")
        return gia_tri
    if truong.kieu is int:
        if isinstance(gia_tri, bool) or not isinstance(gia_tri, int):
            raise _loi("gia-tri-khong-hop-le", f"{truong.nhan}: phải là số nguyên.")
        if truong.toi_thieu is not None and gia_tri < truong.toi_thieu:
            raise _loi("gia-tri-khong-hop-le", f"{truong.nhan}: không được nhỏ hơn {truong.toi_thieu}.")
        if truong.toi_da is not None and gia_tri > truong.toi_da:
            raise _loi("gia-tri-khong-hop-le", f"{truong.nhan}: không được lớn hơn {truong.toi_da}.")
        return gia_tri
    if gia_tri is None and truong.bo_trong:
        return None
    if not isinstance(gia_tri, str):
        raise _loi("gia-tri-khong-hop-le", f"{truong.nhan}: phải là chữ.")
    gia_tri = gia_tri.strip()
    if not gia_tri:
        if truong.bo_trong:
            return None
        raise _loi("gia-tri-khong-hop-le", f"{truong.nhan}: không được để trống.")
    if len(gia_tri) > 500:
        raise _loi("gia-tri-khong-hop-le", f"{truong.nhan}: dài quá 500 ký tự.")
    return gia_tri


# ---------------------------------------------------------------------------
# Đếm hồ sơ đang mở
# ---------------------------------------------------------------------------


def _dem_ho_so_mo(session: Session, cot: Any) -> dict[str, int]:
    """Số hồ sơ chưa tới trạng thái kết thúc, theo giá trị của một cột trên `requests`."""
    dong = session.execute(
        select(cot, func.count())
        .join(State, (State.rule_set_id == Request.rule_set_id) & (State.code == Request.current_state))
        .where(~State.is_terminal, cot.is_not(None))
        .group_by(cot)
    ).all()
    return {ma: so for ma, so in dong}


def _phong_mac_dinh(session: Session) -> dict[str, str]:
    return dict(
        session.execute(
            select(RequestTypeRouting.request_type_code, RequestTypeRouting.department_code).where(
                RequestTypeRouting.is_default
            )
        ).all()
    )


# ---------------------------------------------------------------------------
# Xem
# ---------------------------------------------------------------------------


@router.get("")
def xem_cau_hinh(actor: QuanTriVien, session: Phien) -> dict:
    """Toàn bộ cấu hình đang chạy cho màn quản trị. Chỉ quản trị viên.

    Đồ thị quy trình là của bộ quy tắc đang kích hoạt — bộ hồ sơ mới nhận. Danh mục (loại yêu cầu,
    mức ưu tiên, phòng ban) dùng chung mọi bộ, kèm số hồ sơ đang mở của từng dòng.
    """
    bo = get_active_rule_set(session)
    trang_thai = session.scalars(
        select(State).where(State.rule_set_id == bo.id).order_by(State.display_order)
    ).all()
    nhan_trang_thai = {s.code: s.label for s in trang_thai}
    nhan_vai_tro = {r.code: r.label for r in session.scalars(select(Role).order_by(Role.display_order))}
    nhan_rang_buoc = {g.code: g.label for g in session.scalars(select(Guard))}
    canh = session.scalars(
        select(Transition)
        .where(Transition.rule_set_id == bo.id)
        .order_by(Transition.from_state, Transition.display_order, Transition.id)
    ).all()

    mo_theo_loai = _dem_ho_so_mo(session, Request.request_type_code)
    mo_theo_muc = _dem_ho_so_mo(session, Request.priority_code)
    mo_theo_phong = _dem_ho_so_mo(session, Request.department_code)
    mac_dinh = _phong_mac_dinh(session)

    lich = session.execute(
        text("SELECT code, label, time_zone FROM work_calendars WHERE is_default")
    ).one_or_none()
    gio_lam = (
        session.execute(
            text(
                "SELECT iso_weekday, to_char(start_time, 'HH24:MI'), to_char(end_time, 'HH24:MI') "
                "FROM work_hours WHERE calendar_code = :lich ORDER BY iso_weekday, start_time"
            ),
            {"lich": lich.code},
        ).all()
        if lich
        else []
    )
    ngay_nghi = (
        session.execute(
            text(
                "SELECT day, label FROM holidays WHERE calendar_code = :lich AND day >= current_date "
                "ORDER BY day LIMIT 20"
            ),
            {"lich": lich.code},
        ).all()
        if lich
        else []
    )

    return {
        "rule_set": {"version": bo.version, "label": bo.label, "effective_from": bo.effective_from},
        "states": [
            {
                "code": s.code,
                "label": s.label,
                "description": s.description,
                "is_initial": s.is_initial,
                "is_terminal": s.is_terminal,
                "sla_running": s.sla_running,
            }
            for s in trang_thai
        ],
        "transitions": [
            {
                "from_state": t.from_state,
                "from_label": nhan_trang_thai.get(t.from_state, t.from_state),
                "to_state": t.to_state,
                "to_label": nhan_trang_thai.get(t.to_state, t.to_state),
                "activity_label": t.activity_label,
                "is_system": t.is_system,
                "is_rework": t.is_rework,
                "roles": sorted(nhan_vai_tro.get(r, r) for r in t.role_codes),
                "guards": [nhan_rang_buoc.get(g, g) for g in t.guard_codes],
                "auto_after_hours": t.auto_after_hours,
                "reopen_window_hours": t.reopen_window_hours,
            }
            for t in canh
        ],
        "request_types": [
            {
                "code": l.code,
                "label": l.label,
                "description": l.description,
                "sla_hours": l.sla_hours,
                "sla_grace_hours": l.sla_grace_hours,
                "sla_warn_percent": l.sla_warn_percent,
                "is_active": l.is_active,
                "default_department": mac_dinh.get(l.code),
                "open_cases": mo_theo_loai.get(l.code, 0),
            }
            for l in session.scalars(select(RequestType).order_by(RequestType.display_order))
        ],
        "priorities": [
            {
                "code": m.code,
                "label": m.label,
                "is_default": m.is_default,
                "sla_factor_percent": m.sla_factor_percent,
                "open_cases": mo_theo_muc.get(m.code, 0),
            }
            for m in session.scalars(select(Priority).order_by(Priority.display_order))
        ],
        "departments": [
            {
                "code": p.code,
                "label": p.label,
                "description": p.description,
                "is_active": p.is_active,
                "open_cases": mo_theo_phong.get(p.code, 0),
            }
            for p in session.scalars(select(Department).order_by(Department.display_order))
        ],
        "calendar": (
            {
                "label": lich.label,
                "time_zone": lich.time_zone,
                "hours": [{"weekday": thu, "start": tu, "end": den} for thu, tu, den in gio_lam],
                "holidays": [{"day": ngay, "label": nhan} for ngay, nhan in ngay_nghi],
            }
            if lich
            else None
        ),
        "fields": {
            loai: {ten: {"label": t.nhan, "affects_deadlines": t.doi_han} for ten, t in dm.truong.items()}
            for loai, dm in DANH_MUC.items()
        },
        "changes": _nhat_ky(session),
    }


def _nhat_ky(session: Session) -> list[dict]:
    """Các lần sửa gần nhất, mới trước, kèm tên bảng và tên trường để người đọc được."""
    theo_bang = {dm.bang: dm for dm in DANH_MUC.values()}
    dong = session.scalars(
        select(ConfigChange).order_by(ConfigChange.changed_at.desc(), ConfigChange.id.desc()).limit(SO_DONG_NHAT_KY)
    ).all()
    ra = []
    for d in dong:
        dm = theo_bang.get(d.entity)
        truong = dm.truong.get(d.field) if dm else None
        ra.append(
            {
                "changed_at": d.changed_at,
                "actor_label": d.actor_label or d.actor_id,
                "entity": d.entity,
                "entity_label": dm.nhan if dm else d.entity,
                "entity_code": d.entity_code,
                "field": d.field,
                "field_label": truong.nhan if truong else d.field,
                "old_value": d.old_value,
                "new_value": d.new_value,
            }
        )
    return ra


# ---------------------------------------------------------------------------
# Sửa
# ---------------------------------------------------------------------------


class SuaVao(BaseModel):
    """Một lần sửa: các trường đổi của MỘT dòng, và có phải chỉ chạy thử không."""

    changes: dict[str, Any] = Field(min_length=1)
    dry_run: bool = False


@router.post("/{loai}/{ma}")
def sua_cau_hinh(loai: str, ma: str, du_lieu: SuaVao, actor: QuanTriVien, session: Phien) -> dict:
    """Sửa một dòng cấu hình. Chỉ quản trị viên.

    `dry_run: true` đi trọn đường thật — ghi, `kiem_tra_cau_hinh()`, đếm hồ sơ đang mở — rồi hoàn
    tác, để màn báo trước "N hồ sơ đang mở sẽ đổi hạn" và chặn sớm lần sửa làm hỏng cấu hình.
    """
    dm = DANH_MUC.get(loai)
    if dm is None:
        raise _loi("khong-tim-thay", "Không có danh mục này.", status.HTTP_404_NOT_FOUND)
    dong = session.get(dm.mo_hinh, ma)
    if dong is None:
        raise _loi("khong-tim-thay", f"Không tìm thấy {dm.nhan.lower()} '{ma}'.", status.HTTP_404_NOT_FOUND)

    la = [ten for ten in du_lieu.changes if ten not in dm.truong]
    if la:
        raise _loi("truong-khong-sua-duoc", f"Không sửa được trường: {', '.join(sorted(la))}.")
    moi = {ten: _chuan_hoa(ten, dm.truong[ten], gt) for ten, gt in du_lieu.changes.items()}

    mac_dinh_cu = _phong_mac_dinh(session).get(ma) if "default_department" in moi else None
    cu = {ten: (mac_dinh_cu if ten == "default_department" else getattr(dong, ten)) for ten in moi}
    doi = {ten: gt for ten, gt in moi.items() if gt != cu[ten]}

    so_ho_so = _dem_ho_so_mo(session, dm.cot_ho_so).get(ma, 0)
    ket_qua = {
        "applied": False,
        "changes": [
            {"field": ten, "field_label": dm.truong[ten].nhan, "old_value": cu[ten], "new_value": gt}
            for ten, gt in doi.items()
        ],
        "open_cases": so_ho_so,
        "affects_deadlines": any(dm.truong[ten].doi_han for ten in doi),
    }
    if not doi:
        return ket_qua

    diem_luu = session.begin_nested()
    try:
        for ten, gt in doi.items():
            if ten == "default_department":
                _doi_phong_mac_dinh(session, ma, gt)
            else:
                setattr(dong, ten, gt)
        session.flush()
        session.execute(text("SELECT kiem_tra_cau_hinh()"))
        for ten, gt in doi.items():
            session.add(
                ConfigChange(
                    actor_id=actor.id,
                    actor_label=actor.label,
                    entity=dm.bang,
                    entity_code=ma,
                    field=ten,
                    old_value=cu[ten],
                    new_value=gt,
                )
            )
        session.flush()
    except HTTPException:
        diem_luu.rollback()
        raise
    except DBAPIError as loi:
        diem_luu.rollback()
        raise _loi("cau-hinh-khong-hop-le", _cau_loi(loi)) from loi

    if du_lieu.dry_run:
        diem_luu.rollback()
        session.expire(dong)
        return ket_qua

    diem_luu.commit()
    session.commit()
    logger.info(
        "Quản trị viên %s sửa %s '%s': %s",
        actor.id,
        dm.bang,
        ma,
        ", ".join(f"{ten} {cu[ten]!r} → {gt!r}" for ten, gt in doi.items()),
    )
    return {**ket_qua, "applied": True}


def _doi_phong_mac_dinh(session: Session, loai: str, phong: str) -> None:
    """Chuyển dòng mặc định của loại yêu cầu sang phòng khác. Tắt dòng cũ trước — chỉ mục duy nhất
    từng phần chỉ cho một dòng mặc định mỗi loại."""
    if session.get(Department, phong) is None:
        raise _loi("gia-tri-khong-hop-le", f"Không có phòng ban '{phong}'.")
    session.execute(
        update(RequestTypeRouting)
        .where(RequestTypeRouting.request_type_code == loai, RequestTypeRouting.is_default)
        .values(is_default=False)
        .execution_options(synchronize_session="fetch")
    )
    dong = session.get(RequestTypeRouting, (loai, phong))
    if dong is None:
        session.add(RequestTypeRouting(request_type_code=loai, department_code=phong, is_default=True))
    else:
        dong.is_default = True


def _cau_loi(loi: DBAPIError) -> str:
    """Câu lỗi cho người đọc. Lỗi của `kiem_tra_cau_hinh()` đã là câu tiếng Việt; lỗi ràng buộc
    của lược đồ thì nói chung, chi tiết vào nhật ký."""
    goc = getattr(loi, "orig", None)
    chan_doan = getattr(goc, "diag", None)
    ma_sql = getattr(goc, "sqlstate", None)
    cau = getattr(chan_doan, "message_primary", None)
    if ma_sql == "P0001" and cau:
        return f"Cấu hình sau khi sửa không hợp lệ: {cau}."
    logger.warning("Sửa cấu hình bị cơ sở dữ liệu từ chối: %s", loi)
    return "Giá trị vi phạm ràng buộc của cấu hình. Kiểm tra lại giá trị vừa nhập."
