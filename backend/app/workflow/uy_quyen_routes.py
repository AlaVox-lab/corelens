# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ủy quyền khi vắng mặt (#252) — điểm cuối khai, xem, thu hồi. Quyết định và cách gắn vào định danh:
# app/workflow/uy_quyen.py.
#
# Ai dùng được: người mang vai của buồng lái phòng ban (vai RIÊNG, không tính vai làm thay). Ai làm gì:
#
#   - Khai cho chính mình: ủy quyền vai riêng của mình (giao nhau với vai phòng ban) cho một người cùng
#     phòng
#   - Người giao việc của phòng (trưởng phòng — vai đi được cạnh giao việc, tra từ dữ liệu quy tắc) khai
#     thay cho một người trong phòng không mang vai giao việc (người xử lý); vai lấy từ danh bạ
#   - Thu hồi: người vắng, người đã khai, hay người giao việc của phòng
#
# Người nào thuộc phòng nào, mang vai gì tra ở danh bạ Keycloak lúc khai, như ô chọn người xử lý (#83).

from __future__ import annotations

import datetime as dt
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor
from app.auth.directory import DirectoryUnavailable, KeycloakDirectory, Person, get_directory
from app.config import get_settings
from app.db import get_session
from app.models.quan_tri import Delegation
from app.models.workflow_config import Department, Role
from app.workflow.assignment import vai_tro_giao_viec, vai_tro_phong_ban
from app.workflow.context import Actor
from app.workflow.engine import get_active_rule_set
from app.workflow.uy_quyen import hom_nay, khoang_cua_ngay, ngay_cua_khoang

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/delegations", tags=["Ủy quyền"])

Phien = Annotated[Session, Depends(get_session)]
TacNhan = Annotated[Actor, Depends(current_actor)]
DanhBa = Annotated[KeycloakDirectory, Depends(get_directory)]

# Ủy quyền đã hết hay đã thu hồi vẫn hiện thêm chừng này ngày, để người vắng đi làm lại còn thấy
SO_NGAY_GIU_TREN_MAN = 30


def _loi(ma_http: int, ma: str, thong_diep: str) -> HTTPException:
    return HTTPException(status_code=ma_http, detail={"code": ma, "message": thong_diep})


def _vai(session: Session) -> tuple[frozenset[str], frozenset[str]]:
    """(vai của buồng lái phòng ban, vai giao việc) — tra từ bộ quy tắc đang bật, không mã cứng."""
    bo = get_active_rule_set(session)
    return vai_tro_phong_ban(session, bo.id), vai_tro_giao_viec(session, bo.id)


def _cua(session: Session, actor: Actor) -> tuple[frozenset[str], frozenset[str]]:
    """Chặn người không mang vai riêng nào của phòng ban; trả về hai tập vai cho phía gọi dùng tiếp."""
    vai_phong, vai_giao = _vai(session)
    if not actor.departments or not (actor.vai_rieng & vai_phong):
        raise _loi(status.HTTP_403_FORBIDDEN, "khong-vao-duoc", "Chỉ người làm việc trong phòng ban mới khai được ủy quyền.")
    return vai_phong, vai_giao


def _phong_cua(actor: Actor, ma: str | None) -> str:
    if ma is None:
        if len(actor.departments) != 1:
            raise _loi(422, "chon-phong", "Bạn thuộc nhiều phòng — chọn phòng của ủy quyền.")
        return next(iter(actor.departments))
    if ma not in actor.departments:
        raise _loi(status.HTTP_403_FORBIDDEN, "khac-phong", "Chỉ khai được ủy quyền trong phòng của mình.")
    return ma


def _thanh_vien(danh_ba: KeycloakDirectory, phong: str) -> dict[str, Person]:
    try:
        return {p.id: p for p in danh_ba.department_members(phong)}
    except DirectoryUnavailable as loi:
        raise _loi(status.HTTP_503_SERVICE_UNAVAILABLE, "danh-ba-loi", f"Danh bạ không trả lời: {loi.message}") from loi


def _nhan_vai(session: Session) -> dict[str, str]:
    return {r.code: r.label for r in session.scalars(select(Role))}


# ---------------------------------------------------------------------------
# Xem
# ---------------------------------------------------------------------------


def _ra(session: Session, u: Delegation, actor: Actor, vai_giao: frozenset[str], nhan_vai: dict[str, str],
        nhan_phong: dict[str, str], bay_gio: dt.datetime) -> dict:
    tu, den = ngay_cua_khoang(session, u.starts_at, u.ends_at)
    if u.revoked_at is not None:
        tinh_trang = "revoked"
    elif u.ends_at <= bay_gio:
        tinh_trang = "ended"
    elif u.starts_at > bay_gio:
        tinh_trang = "upcoming"
    else:
        tinh_trang = "active"
    return {
        "id": u.id,
        "delegator_id": u.delegator_id,
        "delegator_label": u.delegator_label,
        "delegate_id": u.delegate_id,
        "delegate_label": u.delegate_label,
        "department_code": u.department_code,
        "department_label": nhan_phong.get(u.department_code, u.department_code),
        "roles": [nhan_vai.get(v, v) for v in u.roles],
        "starts_on": tu,
        "ends_on": den,
        "status": tinh_trang,
        "created_by_label": u.created_by_label,
        "revoked_by_label": u.revoked_by_label,
        "can_revoke": tinh_trang in ("active", "upcoming") and _thu_hoi_duoc(u, actor, vai_giao),
    }


def _thu_hoi_duoc(u: Delegation, actor: Actor, vai_giao: frozenset[str]) -> bool:
    return actor.id in (u.delegator_id, u.created_by_id) or (
        bool(actor.vai_rieng & vai_giao) and u.department_code in actor.departments
    )


@router.get("")
def xem_uy_quyen(session: Phien, actor: TacNhan) -> dict:
    """Ủy quyền người gọi cần thấy: của chính họ (cho hay nhận), và — với người giao việc — mọi ủy
    quyền trong phòng của họ. Ủy quyền đã hết hay thu hồi chỉ giữ trên màn thêm một tháng."""
    _, vai_giao = _cua(session, actor)
    giao_viec = bool(actor.vai_rieng & vai_giao)
    bay_gio = session.execute(select(func.now())).scalar_one()
    dieu_kien = [Delegation.delegator_id == actor.id, Delegation.delegate_id == actor.id, Delegation.created_by_id == actor.id]
    if giao_viec:
        dieu_kien.append(Delegation.department_code.in_(actor.departments))
    cac_dong = session.scalars(
        select(Delegation)
        .where(or_(*dieu_kien), Delegation.ends_at > bay_gio - dt.timedelta(days=SO_NGAY_GIU_TREN_MAN))
        .order_by(Delegation.starts_at.desc(), Delegation.id.desc())
    ).all()
    nhan_vai = _nhan_vai(session)
    nhan_phong = {p.code: p.label for p in session.scalars(select(Department))}
    return {
        "today": hom_nay(session),
        "max_days": get_settings().delegation_max_days,
        "departments": [{"code": m, "label": nhan_phong.get(m, m)} for m in sorted(actor.departments)],
        "can_grant_for_others": giao_viec,
        "items": [_ra(session, u, actor, vai_giao, nhan_vai, nhan_phong, bay_gio) for u in cac_dong],
    }


@router.get("/members")
def nguoi_trong_phong(session: Phien, actor: TacNhan, danh_ba: DanhBa, department_code: str | None = None) -> dict:
    """Người trong phòng, cho ô chọn người được ủy quyền và (với trưởng phòng) người vắng."""
    vai_phong, vai_giao = _cua(session, actor)
    phong = _phong_cua(actor, department_code)
    nhan_vai = _nhan_vai(session)
    return {
        "department_code": phong,
        "members": [
            {
                "id": p.id,
                "name": p.name,
                "roles": [nhan_vai.get(v, v) for v in sorted(p.roles & vai_phong)],
                # Trưởng phòng chỉ khai thay được cho người không mang vai giao việc
                "can_be_delegator": bool(p.roles & vai_phong) and not (p.roles & vai_giao),
            }
            for p in _thanh_vien(danh_ba, phong).values()
            if p.roles & vai_phong
        ],
    }


# ---------------------------------------------------------------------------
# Khai và thu hồi
# ---------------------------------------------------------------------------


class KhaiVao(BaseModel):
    delegate_id: str = Field(min_length=1)
    starts_on: dt.date
    ends_on: dt.date
    # Bỏ trống: chính người khai là người vắng
    delegator_id: str | None = None
    department_code: str | None = None


@router.post("", status_code=201)
def khai_uy_quyen(du_lieu: KhaiVao, session: Phien, actor: TacNhan, danh_ba: DanhBa) -> dict:
    """Khai một ủy quyền. Không cần người được ủy quyền xác nhận; có hiệu lực từ 00:00 ngày đầu."""
    vai_phong, vai_giao = _cua(session, actor)
    phong = _phong_cua(actor, du_lieu.department_code)
    thanh_vien = _thanh_vien(danh_ba, phong)

    nguoi_vang_id = du_lieu.delegator_id or actor.id
    if nguoi_vang_id == actor.id:
        # Vai riêng trong token: vai làm thay không ủy quyền tiếp được
        vai_vang = actor.vai_rieng
        ten_vang = actor.label
    else:
        if not (actor.vai_rieng & vai_giao):
            raise _loi(status.HTTP_403_FORBIDDEN, "khong-khai-thay-duoc", "Chỉ trưởng phòng khai thay ủy quyền cho người khác.")
        nguoi_vang = thanh_vien.get(nguoi_vang_id)
        if nguoi_vang is None:
            raise _loi(422, "nguoi-vang-khac-phong", "Người vắng không thuộc phòng này.")
        if nguoi_vang.roles & vai_giao:
            raise _loi(status.HTTP_403_FORBIDDEN, "chi-khai-thay-nguoi-xu-ly", f"{nguoi_vang.name} tự khai ủy quyền của mình.")
        vai_vang = nguoi_vang.roles
        ten_vang = nguoi_vang.name

    vai = sorted(vai_vang & vai_phong)
    if not vai:
        raise _loi(422, "khong-co-vai", "Người vắng không mang vai nào của phòng ban để ủy quyền.")

    nguoi_nhan = thanh_vien.get(du_lieu.delegate_id)
    if nguoi_nhan is None:
        raise _loi(422, "nguoi-nhan-khac-phong", "Chỉ ủy quyền được cho người cùng phòng.")
    if nguoi_nhan.id == nguoi_vang_id:
        raise _loi(422, "tu-uy-quyen", "Không ủy quyền cho chính người vắng.")

    hom = hom_nay(session)
    if du_lieu.starts_on < hom:
        raise _loi(422, "ngay-da-qua", "Ngày bắt đầu không được ở quá khứ.")
    if du_lieu.ends_on < du_lieu.starts_on:
        raise _loi(422, "khoang-sai", "Ngày kết thúc phải từ ngày bắt đầu trở đi.")
    toi_da = get_settings().delegation_max_days
    if (du_lieu.ends_on - du_lieu.starts_on).days + 1 > toi_da:
        raise _loi(422, "qua-dai", f"Một lần ủy quyền dài tối đa {toi_da} ngày.")

    bat_dau, ket_thuc = khoang_cua_ngay(session, du_lieu.starts_on, du_lieu.ends_on)
    u = Delegation(
        delegator_id=nguoi_vang_id,
        delegator_label=ten_vang,
        delegate_id=nguoi_nhan.id,
        delegate_label=nguoi_nhan.name,
        department_code=phong,
        roles=vai,
        starts_at=bat_dau,
        ends_at=ket_thuc,
        created_by_id=actor.id,
        created_by_label=actor.label,
    )
    session.add(u)
    session.commit()
    logger.info("Ủy quyền %d: %s → %s, phòng %s, vai %s, %s–%s", u.id, nguoi_vang_id, nguoi_nhan.id, phong,
                ",".join(vai), du_lieu.starts_on, du_lieu.ends_on)
    bay_gio = session.execute(select(func.now())).scalar_one()
    nhan_phong = {p.code: p.label for p in session.scalars(select(Department))}
    return _ra(session, u, actor, vai_giao, _nhan_vai(session), nhan_phong, bay_gio)


@router.post("/{ma}/revoke")
def thu_hoi_uy_quyen(ma: int, session: Phien, actor: TacNhan) -> dict:
    """Thu hồi sớm. Dòng giữ lại kèm người thu hồi và lúc thu hồi; quyền mất ngay ở lần bấm kế tiếp."""
    _, vai_giao = _cua(session, actor)
    u = session.get(Delegation, ma)
    if u is None or not (_thu_hoi_duoc(u, actor, vai_giao) or u.delegate_id == actor.id):
        raise _loi(status.HTTP_404_NOT_FOUND, "khong-tim-thay", "Không tìm thấy ủy quyền.")
    if not _thu_hoi_duoc(u, actor, vai_giao):
        raise _loi(status.HTTP_403_FORBIDDEN, "khong-thu-hoi-duoc", "Người được ủy quyền không tự thu hồi được.")
    bay_gio = session.execute(select(func.now())).scalar_one()
    if u.revoked_at is not None or u.ends_at <= bay_gio:
        raise _loi(status.HTTP_409_CONFLICT, "da-het", "Ủy quyền này đã hết hoặc đã thu hồi.")
    u.revoked_at = bay_gio
    u.revoked_by_id = actor.id
    u.revoked_by_label = actor.label
    session.commit()
    nhan_phong = {p.code: p.label for p in session.scalars(select(Department))}
    return _ra(session, u, actor, vai_giao, _nhan_vai(session), nhan_phong, bay_gio)
