# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Tệp đính kèm trên hồ sơ (#80): giới hạn, kiểm tệp, ghi, liệt kê.
#
# Navigator chốt 26/10: tệp đi qua dịch vụ ứng dụng chứ không presigned URL — quyền kiểm ở mỗi
# lần tải và người ngoài nhận 404; ai mở được hồ sơ thì xem được tệp; chỉ người gửi đính kèm,
# vào những lúc họ có một cạnh mang cờ `transitions.accepts_attachments`; hồ sơ hủy vẫn giữ
# tệp; danh sách đuôi tệp, dung lượng và số tệp nằm trong biến môi trường.
#
# Đính kèm KHÔNG đổi hồ sơ nên không đi qua `perform_transition` và không vào nhật ký (ADR-0005),
# như lời nhắn. Điểm cuối ở `attachment_routes.py`; tệp này không biết HTTP là gì.

from __future__ import annotations

import mimetypes
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.case import CaseAttachment, Request
from app.storage import objects
from app.workflow.context import Actor
from app.workflow.engine import allowed_transitions


class TepBiTuChoi(Exception):
    """Tệp hay lần tải bị từ chối. `http_status` để điểm cuối dịch, cùng khuôn `MessageRejected`."""

    def __init__(self, code: str, message: str, http_status: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


@dataclass(frozen=True)
class ChinhSach:
    """Giới hạn đang áp dụng, đọc từ cấu hình mỗi lần để đổi `.env` rồi khởi động lại là xong."""

    duoi_cho_phep: tuple[str, ...]
    toi_da_mb: int
    toi_da_tep: int
    toi_da_tep_moi_ho_so: int

    @property
    def toi_da_byte(self) -> int:
        return self.toi_da_mb * 1024 * 1024


def chinh_sach() -> ChinhSach:
    cau_hinh = get_settings()
    duoi = tuple(
        dict.fromkeys(  # giữ thứ tự, bỏ trùng
            d.strip().lower().lstrip(".")
            for d in cau_hinh.attachment_allowed_extensions.split(",")
            if d.strip()
        )
    )
    return ChinhSach(
        duoi_cho_phep=duoi,
        toi_da_mb=cau_hinh.attachment_max_mb,
        toi_da_tep=cau_hinh.attachment_max_files,
        toi_da_tep_moi_ho_so=cau_hinh.attachment_max_files_per_case,
    )


# Chữ ký đầu tệp của những đuôi mà ta biết. Đuôi doanh nghiệp tự thêm vào `.env` mà ở đây chưa
# có chữ ký thì chỉ kiểm đuôi — thà kiểm ít còn hơn chặn nhầm một kiểu tệp họ chủ động mở.
_CHU_KY_ZIP = b"PK\x03\x04"
_CHU_KY_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def _la_van_ban(dau: bytes) -> bool:
    return b"\x00" not in dau


_KIEM_NOI_DUNG = {
    "png": lambda d: d.startswith(b"\x89PNG\r\n\x1a\n"),
    "jpg": lambda d: d.startswith(b"\xff\xd8\xff"),
    "jpeg": lambda d: d.startswith(b"\xff\xd8\xff"),
    "gif": lambda d: d.startswith((b"GIF87a", b"GIF89a")),
    "webp": lambda d: d.startswith(b"RIFF") and d[8:12] == b"WEBP",
    "pdf": lambda d: b"%PDF-" in d[:1024],
    "docx": lambda d: d.startswith(_CHU_KY_ZIP),
    "xlsx": lambda d: d.startswith(_CHU_KY_ZIP),
    "doc": lambda d: d.startswith(_CHU_KY_OLE),
    "xls": lambda d: d.startswith(_CHU_KY_OLE),
    "txt": _la_van_ban,
    "csv": _la_van_ban,
}

_KY_TU_DIEU_KHIEN = re.compile(r"[\x00-\x1f\x7f]")
TEN_TOI_DA = 200


def lam_sach_ten(ten: str | None) -> str:
    """Tên chỉ để hiển thị và đặt tên lúc tải về: bỏ đường dẫn, ký tự điều khiển, cắt độ dài.

    Cắt từ đầu nên đuôi tệp luôn còn. Không bao giờ dùng tên này làm khóa trong kho.
    """
    ten = (ten or "").replace("\\", "/").rsplit("/", 1)[-1]
    ten = _KY_TU_DIEU_KHIEN.sub("", ten).strip().strip(".")
    return ten[-TEN_TOI_DA:] if len(ten) > TEN_TOI_DA else ten


def kiem_tep(ten: str | None, noi_dung: bytes, cs: ChinhSach | None = None) -> tuple[str, str]:
    """Kiểm một tệp, trả `(tên đã làm sạch, loại nội dung)`. Ném `TepBiTuChoi` khi không đạt.

    Ba lớp: đuôi nằm trong danh sách, dung lượng không vượt trần, nội dung khớp đuôi — đổi đuôi
    một tệp chạy được thành `.png` không qua được. Loại nội dung suy từ đuôi, không tin tiêu đề
    trình duyệt gửi.
    """
    cs = cs or chinh_sach()
    ten_sach = lam_sach_ten(ten)
    if not ten_sach:
        raise TepBiTuChoi("attachment-bad-name", "Tệp không có tên.")

    duoi = ten_sach.rsplit(".", 1)[-1].lower() if "." in ten_sach else ""
    if duoi not in cs.duoi_cho_phep:
        raise TepBiTuChoi(
            "attachment-type-not-allowed",
            f"Không nhận tệp '{ten_sach}': chỉ nhận đuôi {', '.join(cs.duoi_cho_phep)}.",
        )
    if not noi_dung:
        raise TepBiTuChoi("attachment-empty", f"Tệp '{ten_sach}' rỗng.")
    if len(noi_dung) > cs.toi_da_byte:
        raise TepBiTuChoi(
            "attachment-too-large",
            f"Tệp '{ten_sach}' lớn hơn giới hạn: tối đa {cs.toi_da_mb} MB mỗi tệp.",
            413,
        )
    kiem = _KIEM_NOI_DUNG.get(duoi)
    if kiem is not None and not kiem(noi_dung[:8192]):
        raise TepBiTuChoi(
            "attachment-content-mismatch",
            f"Nội dung tệp '{ten_sach}' không đúng với đuôi .{duoi}.",
        )

    loai = mimetypes.guess_type(f"x.{duoi}")[0] or "application/octet-stream"
    return ten_sach, loai


def cho_phep_dinh_kem(session: Session, ho_so: Request, actor: Actor) -> bool:
    """Người này đính kèm được vào hồ sơ này lúc này không.

    Đúng khi họ đang có một cạnh mang cờ `accepts_attachments` — danh sách cạnh đã lọc theo vai
    trò và ràng buộc không cần nhập liệu, nên cờ chỉ bật với chính người gửi, ở đúng những bước
    còn chuyện để nói với người nhận. Không có tên trạng thái hay vai trò nào trong mã.
    """
    return any(c.accepts_attachments for c in allowed_transitions(session, ho_so, actor))


def danh_sach_tep(session: Session, case_id: int) -> list[CaseAttachment]:
    return list(
        session.scalars(
            select(CaseAttachment)
            .where(CaseAttachment.case_id == case_id)
            .order_by(CaseAttachment.created_at, CaseAttachment.id)
        ).all()
    )


def them_tep(
    session: Session,
    ho_so: Request,
    actor: Actor,
    cac_tep: list[tuple[str | None, bytes]],
) -> list[CaseAttachment]:
    """Đính kèm một lô tệp vào hồ sơ. Hoặc nhận cả lô, hoặc từ chối cả lô.

    Kiểm hết trước khi ghi gì xuống kho: một tệp hỏng thì không tệp nào của lần tải đó vào hồ sơ,
    để người gửi sửa rồi tải lại cả lô thay vì không biết đã vào những tệp nào. Không tự commit —
    phía gọi quyết định ranh giới giao dịch, như `perform_transition`.
    """
    cs = chinh_sach()
    if not cho_phep_dinh_kem(session, ho_so, actor):
        raise TepBiTuChoi(
            "attachment-not-allowed",
            "Ở bước này hồ sơ không nhận thêm tệp đính kèm.",
            409,
        )
    if not cac_tep:
        raise TepBiTuChoi("attachment-none", "Chưa chọn tệp nào.")
    if len(cac_tep) > cs.toi_da_tep:
        raise TepBiTuChoi(
            "attachment-too-many",
            f"Mỗi lần chỉ tải lên tối đa {cs.toi_da_tep} tệp.",
        )
    da_co = session.scalar(
        select(func.count()).select_from(CaseAttachment).where(CaseAttachment.case_id == ho_so.id)
    )
    if da_co + len(cac_tep) > cs.toi_da_tep_moi_ho_so:
        raise TepBiTuChoi(
            "attachment-case-full",
            f"Một hồ sơ chứa tối đa {cs.toi_da_tep_moi_ho_so} tệp; hồ sơ này đã có {da_co}.",
            409,
        )

    da_kiem = [(*kiem_tep(ten, nd, cs), nd) for ten, nd in cac_tep]

    moi: list[CaseAttachment] = []
    for ten, loai, noi_dung in da_kiem:
        khoa = f"ho-so/{ho_so.id}/{uuid.uuid4().hex}"
        objects.luu_tep(khoa, noi_dung, loai)
        tep = CaseAttachment(
            case_id=ho_so.id,
            filename=ten,
            content_type=loai,
            size_bytes=len(noi_dung),
            storage_key=khoa,
            uploaded_by=actor.id,
            uploaded_by_label=actor.label,
        )
        session.add(tep)
        moi.append(tep)
    session.flush()
    return moi
