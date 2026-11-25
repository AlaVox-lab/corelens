# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Nhật ký kiểm toán truy cập dữ liệu cá nhân (#431).
#
# Nhật ký sự kiện ghi mọi lần ĐỔI hồ sơ; bảng `access_audit_log` (bản sửa 0038) ghi việc XEM dữ liệu cá nhân của
# người khác, để trả lời được "ai đã xem hồ sơ này, tệp nào, lúc nào". Bốn loại, mã nằm trong danh mục
# `access_kinds` (nhãn tiếng Việt lấy từ đó):
#
#   case-view            mở chi tiết hồ sơ — buồng lái điều phối, buồng lái phòng ban, cửa hồ sơ của lõi /core/v1.
#                        Chỉ GET chi tiết: bước chuyển cũng trả chi tiết nhưng là một lần làm, không phải một lần xem
#                        (nó đã có dòng nhật ký sự kiện). Danh sách, hàng đợi, tìm kiếm không ghi.
#   requester-contact    xem thư điện tử và số điện thoại của người gửi (app/workflow/contact.py)
#   attachment-download  tải một tệp đính kèm — ghi cả mã tệp
#   event-log-export     xuất nhật ký sự kiện CSV, JSON, XES — không gắn hồ sơ, ghi tham số xuất
#
# KHÔNG GHI người gửi xem hồ sơ của chính mình: đó là dữ liệu của chính họ, không phải truy cập vào dữ liệu của
# người khác — ghi vào thì nhật ký ngập dòng vô nghĩa và che mất dòng cần tìm.
#
# Ghi bằng PHIÊN RIÊNG, COMMIT RIÊNG, sau khi đã kiểm quyền và đã có dữ liệu để trả (lần bị 403/404 không có
# dòng). Không lẫn vào giao dịch của yêu cầu: yêu cầu hoàn tác cũng không mất vết. Ghi hỏng thì chỉ ghi nhật ký lỗi
# có cấu trúc, trang vẫn trả cho người dùng — kiểm toán không được thành điểm hỏng của việc phục vụ.
#
# Tra cứu: `GET /admin/access-audit`, chỉ quản trị viên, chỉ ở ứng dụng (không thuộc /core/v1). Lần tra cứu không
# tự ghi vào nhật ký này.

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi import Request as YeuCauHttp
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import VAI_TRO_QUAN_TRI, require_roles
from app.db import get_session
from app.models.case import CaseAttachment, Request
from app.models.quan_tri import AccessAuditLog, AccessKind
from app.workflow.context import Actor
from app.workflow.phan_trang import ThamSoTrang, _bo_dau_sql, bo_dau, tham_so_trang
from app.workflow.routes import _ma_ho_so

logger = logging.getLogger(__name__)

# Mã loại truy cập — khớp danh mục `access_kinds` nạp ở bản sửa 0038 (khóa ngoại giữ hai bên khớp nhau)
XEM_HO_SO = "case-view"
XEM_LIEN_HE = "requester-contact"
TAI_TEP = "attachment-download"
XUAT_NHAT_KY = "event-log-export"

# Kênh truy cập — khớp ràng buộc CHECK của bản sửa 0038
KENH_UNG_DUNG = "ung-dung"
KENH_LOI = "loi"

MoPhien = Callable[[], AbstractContextManager[Session]]


def _mo_phien_that() -> AbstractContextManager[Session]:
    from app.db import SessionLocal

    return SessionLocal()


# Bài kiểm thay bằng phiên của bài, để dòng ghi thấy được hồ sơ bài vừa tạo và hoàn tác ở cuối bài
mo_phien: MoPhien = _mo_phien_that


def kenh_cua(yeu_cau: YeuCauHttp) -> str:
    """`loi` khi yêu cầu đi qua tiền tố `/core/v1`, `ung-dung` cho mọi đường khác. Tệp đính kèm và xuất nhật ký
    gắn ở cả hai nơi bằng cùng một hàm, nên kênh xét trên đường thật của yêu cầu."""
    # Nhập muộn: app/main.py nhập mô-đun này, còn tiền tố lõi là hằng của app/main.py
    from app.main import TIEN_TO_LOI

    return KENH_LOI if yeu_cau.url.path.startswith(TIEN_TO_LOI + "/") else KENH_UNG_DUNG


def ghi_truy_cap(
    yeu_cau: YeuCauHttp,
    actor: Actor,
    loai: str,
    *,
    ho_so: Request | None = None,
    attachment_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Ghi một lần truy cập. Không bao giờ ném lỗi ra phía gọi.

    Phía gọi chỉ gọi sau khi đã kiểm quyền và đã có dữ liệu để trả. Hồ sơ của chính người gọi (người gửi) thì
    bỏ qua — xem đầu tệp.
    """
    if ho_so is not None and ho_so.requester_id == actor.id:
        return
    kenh = kenh_cua(yeu_cau)
    try:
        with mo_phien() as phien:
            phien.add(
                AccessAuditLog(
                    actor=actor.id,
                    actor_label=actor.label,
                    access_kind=loai,
                    case_id=ho_so.id if ho_so is not None else None,
                    attachment_id=attachment_id,
                    channel=kenh,
                    details=details,
                )
            )
            phien.commit()
    except Exception as loi:  # noqa: BLE001 — kiểm toán hỏng không được làm hỏng trang người dùng đang mở
        logger.error(
            "Không ghi được nhật ký truy cập",
            extra={"fields": {
                "audit_kind": loai,
                "audit_actor": actor.id,
                "audit_case_id": ho_so.id if ho_so is not None else None,
                "audit_attachment_id": attachment_id,
                "audit_channel": kenh,
                "error": f"{type(loi).__name__}: {loi}",
            }},
        )


# ---------------------------------------------------------------------------
# Tra cứu cho quản trị viên
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/admin/access-audit", tags=["Nhật ký truy cập"])

_QuanTriVien = Annotated[Actor, Depends(require_roles(VAI_TRO_QUAN_TRI))]
_Phien = Annotated[Session, Depends(get_session)]


class LoaiTruyCapRa(BaseModel):
    code: str
    label: str


class DongTruyCapRa(BaseModel):
    id: int
    # UTC, ISO 8601 kèm múi giờ — giao diện đổi sang giờ địa phương
    at: dt.datetime
    actor: str
    actor_label: str | None
    access_kind: str
    access_kind_label: str
    case_id: int | None
    # Mã hiển thị, ví dụ `YC-2026-0184`
    case_code: str | None
    attachment_id: int | None
    attachment_filename: str | None
    channel: str
    details: dict[str, Any] | None


class DanhSachTruyCapRa(BaseModel):
    items: list[DongTruyCapRa]
    total: int
    offset: int
    limit: int


def _utc(v: dt.datetime) -> dt.datetime:
    """Mốc không mang múi giờ coi là UTC."""
    return v if v.tzinfo is not None else v.replace(tzinfo=dt.UTC)


@router.get("/kinds", summary="Danh mục loại truy cập được ghi", response_model=list[LoaiTruyCapRa])
def danh_muc_loai(session: _Phien, _: _QuanTriVien) -> list[LoaiTruyCapRa]:
    """Các loại truy cập được ghi, theo thứ tự hiển thị — cho ô lọc của màn Hệ thống."""
    return [
        LoaiTruyCapRa(code=k.code, label=k.label)
        for k in session.scalars(select(AccessKind).order_by(AccessKind.display_order, AccessKind.code))
    ]


@router.get("", summary="Tra cứu nhật ký kiểm toán truy cập", response_model=DanhSachTruyCapRa)
def tra_cuu(
    session: _Phien,
    _: _QuanTriVien,
    trang: Annotated[ThamSoTrang, Depends(tham_so_trang)],
    case_id: Annotated[int | None, Query(ge=1, description="Chỉ một hồ sơ")] = None,
    actor: Annotated[
        str | None, Query(description="Mã người (`sub`) đúng hệt, hoặc một phần tên — không phân biệt dấu")
    ] = None,
    access_kind: Annotated[str | None, Query(description="Chỉ một loại (GET /admin/access-audit/kinds)")] = None,
    tu: Annotated[dt.datetime | None, Query(alias="from", description="Từ mốc này (gồm), UTC nếu không ghi múi")] = None,
    den: Annotated[dt.datetime | None, Query(alias="to", description="Tới trước mốc này, UTC nếu không ghi múi")] = None,
) -> DanhSachTruyCapRa:
    """Nhật ký truy cập dữ liệu cá nhân, mới nhất trước, có phân trang. Chỉ quản trị viên.

    Lần tra cứu này không tự ghi vào nhật ký truy cập: nó đọc vết kiểm toán, không đọc dữ liệu của người dùng.
    """
    dieu_kien = []
    if case_id is not None:
        dieu_kien.append(AccessAuditLog.case_id == case_id)
    if actor and actor.strip():
        khoa = actor.strip()
        dieu_kien.append(or_(
            AccessAuditLog.actor == khoa,
            _bo_dau_sql(AccessAuditLog.actor_label).contains(bo_dau(khoa), autoescape=True),
        ))
    if access_kind:
        dieu_kien.append(AccessAuditLog.access_kind == access_kind)
    if tu is not None:
        dieu_kien.append(AccessAuditLog.at >= _utc(tu))
    if den is not None:
        dieu_kien.append(AccessAuditLog.at < _utc(den))
    loc = and_(*dieu_kien) if dieu_kien else None

    dem = select(func.count()).select_from(AccessAuditLog)
    cau = (
        select(AccessAuditLog, AccessKind.label, Request, CaseAttachment.filename)
        .join(AccessKind, AccessKind.code == AccessAuditLog.access_kind)
        .outerjoin(Request, Request.id == AccessAuditLog.case_id)
        .outerjoin(CaseAttachment, CaseAttachment.id == AccessAuditLog.attachment_id)
        .order_by(AccessAuditLog.at.desc(), AccessAuditLog.id.desc())
        .offset(trang.offset)
        .limit(trang.limit)
    )
    if loc is not None:
        dem, cau = dem.where(loc), cau.where(loc)

    return DanhSachTruyCapRa(
        items=[
            DongTruyCapRa(
                id=dong.id,
                at=dong.at.astimezone(dt.UTC),
                actor=dong.actor,
                actor_label=dong.actor_label,
                access_kind=dong.access_kind,
                access_kind_label=nhan,
                case_id=dong.case_id,
                case_code=_ma_ho_so(ho_so) if ho_so is not None else None,
                attachment_id=dong.attachment_id,
                attachment_filename=ten_tep,
                channel=dong.channel,
                details=dong.details,
            )
            for dong, nhan, ho_so, ten_tep in session.execute(cau).all()
        ],
        total=session.scalar(dem),
        offset=trang.offset,
        limit=trang.limit,
    )
