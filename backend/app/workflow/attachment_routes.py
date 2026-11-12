# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Điểm cuối tệp đính kèm (#80).
#
# Ba việc: cho giao diện biết giới hạn, nhận tệp từ người gửi, trả tệp cho người mở được hồ sơ.
# Trình duyệt không bao giờ nói chuyện với kho (navigator chốt 26/10): tệp đi qua đây nên quyền
# kiểm ở MỖI lần, và người không có quyền nhận 404 — không 403, vì 403 xác nhận tệp có tồn tại,
# cùng lý do với hồ sơ ở #44.

from __future__ import annotations

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor
from app.db import get_session
from app.models.case import CaseAttachment, Request
from app.rate_limit import gioi_han_toc_do
from app.storage import objects
from app.workflow.attachments import TepBiTuChoi, chinh_sach, them_tep
from app.workflow.context import Actor
from app.workflow.coordination import vao_duoc_buong_lai
from app.workflow.department import vao_duoc_phong_ban
from app.workflow.routes import _lay_ho_so_cua_toi
from app.workflow.schemas import ChinhSachTepRa, TepDinhKemRa

router = APIRouter(tags=["Tệp đính kèm"])

_Phien = Annotated[Session, Depends(get_session)]
_Cua = Annotated[Actor, Depends(current_actor)]


def _khong_thay() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "attachment-not-found", "message": "Không tìm thấy tệp."},
    )


def _bao_loi(loi: TepBiTuChoi) -> HTTPException:
    return HTTPException(
        status_code=loi.http_status, detail={"code": loi.code, "message": loi.message}
    )


def mo_duoc_ho_so(session: Session, ho_so: Request, actor: Actor) -> bool:
    """Người này mở được hồ sơ ở một trong ba cổng không — đúng ba luật xem hồ sơ đang có.

    Người gửi xem hồ sơ của mình; điều phối viên xem mọi hồ sơ; nhân viên phòng ban xem hồ sơ
    của phòng mình. Tệp dùng lại chính ba luật đó chứ không viết luật quyền thứ hai: hai luật
    quyền cho cùng một hồ sơ sớm muộn sẽ lệch nhau (navigator chốt 26/10).
    """
    if ho_so.requester_id == actor.id:
        return True
    if vao_duoc_buong_lai(actor):
        return True
    return vao_duoc_phong_ban(session, actor) and ho_so.department_code in actor.departments


@router.get("/attachments/policy", response_model=ChinhSachTepRa)
def chinh_sach_tep(_actor: _Cua) -> ChinhSachTepRa:
    """Giới hạn đang áp dụng. Giao diện chặn theo con số này ở lớp của nó, còn lớp ở đây vẫn
    kiểm lại — chặn ở giao diện thôi thì không đủ, ai cũng gọi thẳng API được."""
    cs = chinh_sach()
    return ChinhSachTepRa(
        allowed_extensions=list(cs.duoi_cho_phep),
        max_mb=cs.toi_da_mb,
        max_files=cs.toi_da_tep,
        max_files_per_case=cs.toi_da_tep_moi_ho_so,
    )


@router.post(
    "/requests/{case_id}/attachments",
    response_model=list[TepDinhKemRa],
    status_code=201,
    dependencies=[Depends(gioi_han_toc_do("upload-attachment"))],
)
def tai_len(
    case_id: int,
    session: _Phien,
    actor: _Cua,
    files: Annotated[list[UploadFile], File(description="Một hay nhiều tệp")],
) -> list[TepDinhKemRa]:
    """Người gửi đính kèm tệp vào hồ sơ của chính mình, ở những bước cho phép."""
    ho_so = _lay_ho_so_cua_toi(session, case_id, actor)

    # Đọc thừa một byte so với trần để biết tệp có vượt hay không mà không nạp cả tệp khổng lồ
    tran = chinh_sach().toi_da_byte + 1
    cac_tep = [(f.filename, f.file.read(tran)) for f in files]

    try:
        moi = them_tep(session, ho_so, actor, cac_tep)
    except TepBiTuChoi as loi:
        session.rollback()
        raise _bao_loi(loi) from loi
    except objects.KhoLoi as loi:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "storage-unavailable", "message": str(loi)},
        ) from loi

    session.commit()
    return [
        TepDinhKemRa(
            id=t.id,
            filename=t.filename,
            content_type=t.content_type,
            size_bytes=t.size_bytes,
            uploaded_by_label=t.uploaded_by_label,
            has_macro=t.has_macro,
            scan_status=t.scan_status,
            created_at=t.created_at,
        )
        for t in moi
    ]


@router.get("/attachments/{attachment_id}")
def tai_ve(attachment_id: int, session: _Phien, actor: _Cua) -> Response:
    """Trả nội dung một tệp cho người mở được hồ sơ của nó. Người khác nhận 404."""
    tep = session.get(CaseAttachment, attachment_id)
    ho_so = session.get(Request, tep.case_id) if tep is not None else None
    if tep is None or ho_so is None or not mo_duoc_ho_so(session, ho_so, actor):
        raise _khong_thay()

    try:
        noi_dung = objects.doc_tep(tep.storage_key)
    except objects.KhongCoTep as loi:
        raise _khong_thay() from loi
    except objects.KhoLoi as loi:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "storage-unavailable", "message": str(loi)},
        ) from loi

    return Response(
        content=noi_dung,
        media_type=tep.content_type,
        headers={
            # Luôn tải về, không mở thẳng trong trình duyệt: tệp là của người dùng, nên không
            # để trình duyệt tự chạy nội dung của nó trên địa chỉ của hệ thống
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(tep.filename)}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )
