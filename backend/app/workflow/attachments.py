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

import io
import logging
import mimetypes
import re
import uuid
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from typing import NamedTuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.case import AttachmentFileType, CaseAttachment, Request
from app.storage import objects, quet_ma_doc
from app.workflow.context import Actor
from app.workflow.engine import allowed_transitions

logger = logging.getLogger(__name__)


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
    # Cách kiểm nội dung từng đuôi, nạp từ `attachment_file_types` (#248). Rỗng khi gọi không kèm
    # phiên — chỉ dùng cho điểm cuối báo giới hạn, không bao giờ cho lần nhận tệp
    loai_tep: Mapping[str, LoaiTep] = field(default_factory=dict)

    @property
    def toi_da_byte(self) -> int:
        return self.toi_da_mb * 1024 * 1024


def chinh_sach(session: Session | None = None) -> ChinhSach:
    """Giới hạn đang áp dụng. Kèm phiên thì nạp luôn bảng kiểm nội dung từng đuôi."""
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
        loai_tep=nap_loai_tep(session) if session is not None else {},
    )


@dataclass(frozen=True)
class LoaiTep:
    """Cách kiểm nội dung một đuôi tệp — một dòng của `attachment_file_types` (#248).

    Chữ ký, loại nội dung, cách dò macro đều là dữ liệu (infra/seed/04-loai-tep-dinh-kem.sql); mã
    chỉ biết ba cách đọc dữ liệu đó: so mẫu hex, kiểm văn bản thuần, dò macro theo `macro_check`.
    """

    duoi: str
    loai_noi_dung: str
    mau_chu_ky: tuple[str, ...] = ()
    vung_tim: int = 0
    van_ban: bool = False
    do_macro: str | None = None
    luon_co_macro: bool = False

    def khop_chu_ky(self, dau: bytes) -> bool:
        if self.van_ban:
            return b"\x00" not in dau
        if not self.mau_chu_ky:
            return True
        for mau in self.mau_chu_ky:
            bieu_thuc = _bieu_thuc_mau(mau)
            if self.vung_tim > 0:
                if bieu_thuc.search(dau[: self.vung_tim]):
                    return True
            elif bieu_thuc.match(dau):
                return True
        return False


@lru_cache(maxsize=128)
def _bieu_thuc_mau(mau: str) -> re.Pattern[bytes]:
    """Mẫu hex (`??` là byte bất kỳ) thành biểu thức chính quy trên byte."""
    phan = [
        b"." if mau[i : i + 2] == "??" else re.escape(bytes.fromhex(mau[i : i + 2]))
        for i in range(0, len(mau), 2)
    ]
    return re.compile(b"".join(phan), re.DOTALL)


def nap_loai_tep(session: Session) -> dict[str, LoaiTep]:
    return {
        d.extension: LoaiTep(
            duoi=d.extension,
            loai_noi_dung=d.content_type,
            mau_chu_ky=tuple(d.signatures or ()),
            vung_tim=d.search_bytes,
            van_ban=d.text_only,
            do_macro=d.macro_check,
            luon_co_macro=d.always_macro,
        )
        for d in session.scalars(select(AttachmentFileType))
    }


# Tên kho VBA trong tệp Compound File (Word, Excel, PowerPoint đời cũ): tên mục thư mục ghi bằng
# UTF-16LE, và kho macro của cả ba ứng dụng đều có luồng `_VBA_PROJECT` (MS-OVBA mục 2.2)
_VBA_OLE = "_VBA_PROJECT".encode("utf-16-le")


class _GoiHong(Exception):
    """Tệp mang chữ ký ZIP mà không mở được như gói ZIP."""


def _co_macro(loai: LoaiTep, noi_dung: bytes) -> bool:
    """Tệp có mang macro không, theo cách dò khai trong dữ liệu. Ném `_GoiHong` khi gói hỏng."""
    if loai.luon_co_macro:
        return True
    if loai.do_macro == "ooxml":
        try:
            with zipfile.ZipFile(io.BytesIO(noi_dung)) as goi:
                return any(t.lower().endswith("vbaproject.bin") for t in goi.namelist())
        except (zipfile.BadZipFile, ValueError, OSError) as loi:
            raise _GoiHong from loi
    if loai.do_macro == "ole":
        return _VBA_OLE in noi_dung
    return False

_KY_TU_DIEU_KHIEN = re.compile(r"[\x00-\x1f\x7f]")
TEN_TOI_DA = 200


def lam_sach_ten(ten: str | None) -> str:
    """Tên chỉ để hiển thị và đặt tên lúc tải về: bỏ đường dẫn, ký tự điều khiển, cắt độ dài.

    Cắt từ đầu nên đuôi tệp luôn còn. Không bao giờ dùng tên này làm khóa trong kho.
    """
    ten = (ten or "").replace("\\", "/").rsplit("/", 1)[-1]
    ten = _KY_TU_DIEU_KHIEN.sub("", ten).strip().strip(".")
    return ten[-TEN_TOI_DA:] if len(ten) > TEN_TOI_DA else ten


class TepDaKiem(NamedTuple):
    ten: str
    loai: str
    co_macro: bool


def kiem_tep(ten: str | None, noi_dung: bytes, cs: ChinhSach | None = None) -> TepDaKiem:
    """Kiểm một tệp, trả `(tên đã làm sạch, loại nội dung, có macro)`. Ném `TepBiTuChoi` khi không đạt.

    Ba lớp: đuôi nằm trong danh sách, dung lượng không vượt trần, nội dung khớp chữ ký khai cho
    đuôi trong `attachment_file_types` (#248) — đổi đuôi một tệp chạy được thành `.png` hay `.pdf`
    không qua được. Loại nội dung lấy từ cùng dòng dữ liệu, không tin tiêu đề trình duyệt gửi.

    Đuôi được phép mà bảng chưa có dòng nào thì chỉ kiểm đuôi và ghi cảnh báo: doanh nghiệp tự thêm
    đuôi vào `.env` mà quên khai chữ ký thì thà kiểm ít còn hơn chặn nhầm kiểu tệp họ chủ động mở.
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
    sai_chu_ky = TepBiTuChoi(
        "attachment-content-mismatch",
        f"Nội dung tệp '{ten_sach}' không phải tệp .{duoi} thật: phần đầu tệp không khớp chữ ký "
        f"của định dạng này. Có thể tệp đã bị đổi đuôi — mở lại bằng đúng ứng dụng rồi lưu lại.",
    )
    loai_tep = cs.loai_tep.get(duoi)
    if loai_tep is None:
        logger.warning("Đuôi .%s được phép nhưng chưa khai chữ ký trong attachment_file_types", duoi)
        loai = mimetypes.guess_type(f"x.{duoi}")[0] or "application/octet-stream"
        return TepDaKiem(ten_sach, loai, False)
    if not loai_tep.khop_chu_ky(noi_dung[:8192]):
        raise sai_chu_ky
    try:
        co_macro = _co_macro(loai_tep, noi_dung)
    except _GoiHong as loi:
        raise sai_chu_ky from loi
    return TepDaKiem(ten_sach, loai_tep.loai_noi_dung, co_macro)


def _quet(ten: str, noi_dung: bytes) -> str:
    """Quét một tệp đã qua lớp kiểm, trả giá trị cho cột `scan_status`. Ném `TepBiTuChoi` khi nhiễm.

    Quét tắt (mặc định) → `disabled`, không gọi gì ra ngoài. Dịch vụ quét không phản hồi → theo
    `clamav_on_unavailable`: nhận và gắn `unscanned` (mặc định), hay từ chối lần tải.
    """
    kq = quet_ma_doc.quet(noi_dung)
    if kq.trang_thai == quet_ma_doc.SACH:
        return "clean"
    if kq.trang_thai == quet_ma_doc.NHIEM:
        logger.warning("Từ chối tệp '%s': trình quét báo mã độc %s", ten, kq.chi_tiet)
        raise TepBiTuChoi(
            "attachment-infected",
            f"Không nhận tệp '{ten}': trình quét mã độc phát hiện {kq.chi_tiet or 'mã độc'}.",
        )
    if kq.trang_thai == quet_ma_doc.KHONG_PHAN_HOI:
        if get_settings().clamav_on_unavailable == "reject":
            raise TepBiTuChoi(
                "attachment-scan-unavailable",
                "Dịch vụ quét mã độc đang không phản hồi nên chưa nhận được tệp. Thử lại sau ít phút.",
                503,
            )
        logger.warning("Nhận tệp '%s' khi chưa quét được mã độc (%s)", ten, kq.chi_tiet)
        return "unscanned"
    return "disabled"


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
    cs = chinh_sach(session)
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

    da_kiem = [(kiem_tep(ten, nd, cs), nd) for ten, nd in cac_tep]
    # Quét mã độc sau khi cả lô đã qua lớp kiểm rẻ, trước khi ghi gì xuống kho — cùng luật cả lô
    trang_thai_quet = [_quet(kq.ten, nd) for kq, nd in da_kiem]

    moi: list[CaseAttachment] = []
    for (kq, noi_dung), quet in zip(da_kiem, trang_thai_quet, strict=True):
        khoa = f"ho-so/{ho_so.id}/{uuid.uuid4().hex}"
        objects.luu_tep(khoa, noi_dung, kq.loai)
        tep = CaseAttachment(
            case_id=ho_so.id,
            filename=kq.ten,
            content_type=kq.loai,
            size_bytes=len(noi_dung),
            storage_key=khoa,
            uploaded_by=actor.id,
            uploaded_by_label=actor.label,
            has_macro=kq.co_macro,
            scan_status=quet,
        )
        session.add(tep)
        moi.append(tep)
    session.flush()
    return moi
