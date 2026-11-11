# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Lớp DUY NHẤT gọi mô hình ngôn ngữ cục bộ (#316, ADR-0008).
#
# Mô hình chạy ở dịch vụ riêng — llama.cpp server, điểm cuối kiểu OpenAI — chỉ nghe trong mạng của
# Compose và chỉ có khi bật hồ sơ `tri-tue`. Dịch vụ ứng dụng gọi nó bằng HTTP của thư viện chuẩn,
# không thêm gói nào, không khung LLM nào (ADR-0008, phương án C1).
#
# BA LỜI HỨA CỦA LỚP NÀY
#
# 1. Đầu ra chỉ nằm trong danh mục ĐANG BẬT, đọc từ bảng lúc gọi. Lược đồ JSON gửi kèm lời gọi đặt
#    `enum` bằng chính các mã đó, nên llama.cpp ràng buộc ngữ pháp sinh ra không thể ra mã lạ; và
#    phía này vẫn kiểm lại — máy chủ khác, hay phiên bản khác bỏ qua lược đồ, không làm lọt mã lạ.
# 2. Có hạn chót cứng. Mỗi lời gọi chạy trong luồng riêng và chờ bằng `result(timeout=...)`, vì
#    `timeout` của urllib không phủ bước tra DNS (đo ở #84: tra tên dịch vụ đã tắt treo 8 giây).
# 3. Mọi lỗi — mô hình tắt, cổng đóng, quá hạn, JSON sai, mã ngoài danh mục — thành MỘT loại lỗi
#    `LoiMoHinh` có mã, và hàm tiện dụng `goi_y_phan_loai` đổi nó thành `None`: "không có gợi ý".
#    Không lỗi nào của mô hình được nổi lên tới người dùng hay chặn một thao tác.
#
# Lớp này KHÔNG ghi gì vào cơ sở dữ liệu. Ghi trường gợi ý là việc của `phan_loai.py`, và không bao
# giờ là trường quyết định (CLAUDE.md mục 4.3).

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as HetGio
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.case import Request
from app.models.workflow_config import Department, Priority, RequestType, RequestTypeField

log = logging.getLogger(__name__)

# Tình trạng dịch vụ mô hình cho `/system/health` và màn Hệ thống
TAT = "disabled"
SAN_SANG = "ready"
KHONG_PHAN_HOI = "unreachable"

# Mã lỗi của một lần hỏi. Hai mã đầu nghĩa là mô hình KHÔNG TỚI ĐƯỢC — không phải lỗi của hồ sơ
# này, nên bộ quét bù không tính là một lần thử (xem `phan_loai.py`).
LOI_TAT = "disabled"
LOI_KHONG_KET_NOI = "unreachable"
LOI_QUA_HAN = "timeout"
LOI_MAY_CHU = "server-error"
LOI_SAI_DINH_DANG = "invalid-output"
LOI_NGOAI_DANH_MUC = "out-of-catalog"
LOI_THIEU_DANH_MUC = "empty-catalog"

# Câu lý do mô hình viết cho mỗi gợi ý: một câu ngắn trên thẻ gợi ý
DO_DAI_LY_DO = 120

# Ba trường quyết định mô hình gợi ý — tên cột của lược đồ hồ sơ, không phải dữ liệu nghiệp vụ
TRUONG_LOAI = "request_type_code"
TRUONG_MUC = "priority_code"
TRUONG_PHONG = "department_code"
CAC_TRUONG = (TRUONG_LOAI, TRUONG_MUC, TRUONG_PHONG)

# Luồng riêng giữ hạn chót cứng; vài luồng là đủ — tác vụ nền và bộ quét bù gọi lần lượt
_LUONG_GOI = ThreadPoolExecutor(max_workers=4, thread_name_prefix="mo-hinh")


class LoiMoHinh(Exception):
    """Một lần hỏi mô hình không cho được gợi ý. `ma` là một trong các hằng `LOI_*`."""

    def __init__(self, ma: str, chi_tiet: str = "") -> None:
        super().__init__(f"{ma}: {chi_tiet}" if chi_tiet else ma)
        self.ma = ma

    @property
    def khong_toi_duoc(self) -> bool:
        return self.ma in (LOI_TAT, LOI_KHONG_KET_NOI)


# ---------------------------------------------------------------------------
# Đề bài: nội dung hồ sơ và danh mục đang bật, đọc từ bảng lúc gọi
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MucDanhMuc:
    code: str
    label: str
    description: str | None = None


@dataclass(frozen=True)
class DeBai:
    """Mọi thứ một lần hỏi cần, đã đọc xong từ cơ sở dữ liệu.

    Tách khỏi lời gọi HTTP để phía gọi đóng phiên trước khi chờ mô hình — không giữ giao dịch hay
    kết nối nào trong lúc chờ.
    """

    title: str
    description: str
    # (nhãn trường, giá trị) của trường thông tin riêng, theo thứ tự hiển thị
    details: tuple[tuple[str, str], ...]
    request_types: tuple[MucDanhMuc, ...]
    # Từ thấp tới cao, theo `display_order` của bảng
    priorities: tuple[MucDanhMuc, ...]
    departments: tuple[MucDanhMuc, ...]
    danh_muc: dict[str, frozenset[str]] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "danh_muc",
            {
                TRUONG_LOAI: frozenset(m.code for m in self.request_types),
                TRUONG_MUC: frozenset(m.code for m in self.priorities),
                TRUONG_PHONG: frozenset(m.code for m in self.departments),
            },
        )

    def luoc_do(self) -> dict[str, Any]:
        """Lược đồ JSON ràng buộc đầu ra: `enum` là mã danh mục đang bật."""

        def ma(truong: str) -> dict[str, Any]:
            return {"type": "string", "enum": sorted(self.danh_muc[truong])}

        ly_do = {"type": "string", "minLength": 1, "maxLength": DO_DAI_LY_DO}
        thuoc_tinh: dict[str, Any] = {}
        # Mã đứng trước lý do. llama.cpp sinh theo đúng thứ tự thuộc tính; đã thử đặt lý do trước
        # (#317): trên bộ mẫu, loại yêu cầu tụt từ 92,5 % xuống 81,2 %, nên giữ thứ tự này
        for truong in CAC_TRUONG:
            thuoc_tinh[truong] = ma(truong)
            thuoc_tinh[_khoa_ly_do(truong)] = ly_do
        return {
            "type": "object",
            "properties": thuoc_tinh,
            "required": list(thuoc_tinh),
            "additionalProperties": False,
        }

    def tin_nhan(self) -> list[dict[str, str]]:
        """Lời dặn và nội dung hồ sơ. Không câu nào nêu mã hay nhãn nghiệp vụ cụ thể: mọi danh mục
        đến từ bảng, doanh nghiệp đổi danh mục thì lời dặn đổi theo."""

        def dong(m: MucDanhMuc) -> str:
            return f"- {m.code}: {m.label}" + (f" — {m.description}" if m.description else "")

        loi_dan = "\n".join(
            [
                "Bạn là trợ lý phân loại yêu cầu nội bộ của một doanh nghiệp. Đọc yêu cầu của nhân "
                "viên rồi chọn đúng một loại yêu cầu, một mức ưu tiên và một phòng ban phụ trách, "
                "chỉ trong các danh mục dưới đây. Trả lời bằng JSON đúng lược đồ đã cho.",
                "Mỗi lựa chọn kèm một câu lý do ngắn bằng tiếng Việt, nêu chi tiết trong yêu cầu "
                "dẫn tới lựa chọn đó.",
                "Mức ưu tiên chọn theo mức ảnh hưởng (bao nhiêu người bị ảnh hưởng, công việc có bị "
                "ngừng không) và độ gấp về thời gian nêu trong yêu cầu. Phòng ban chọn theo việc cần "
                "làm, đối chiếu với phần mô tả của từng phòng.",
                "",
                "Loại yêu cầu:",
                *[dong(m) for m in self.request_types],
                "",
                "Mức ưu tiên, xếp từ thấp tới cao:",
                *[dong(m) for m in self.priorities],
                "",
                "Phòng ban:",
                *[dong(m) for m in self.departments],
            ]
        )
        noi_dung = [f"Tiêu đề: {self.title}", f"Mô tả: {self.description or '(không có)'}"]
        if self.details:
            noi_dung.append("Thông tin thêm:")
            noi_dung.extend(f"- {nhan}: {gia_tri}" for nhan, gia_tri in self.details)
        return [
            {"role": "system", "content": loi_dan},
            {"role": "user", "content": "\n".join(noi_dung)},
        ]


def _khoa_ly_do(truong: str) -> str:
    return truong.removesuffix("_code") + "_reason"


def _gia_tri_chu(gia_tri: Any) -> str:
    if isinstance(gia_tri, list):
        return ", ".join(str(g) for g in gia_tri)
    return str(gia_tri)


def dung_de_bai(
    session: Session,
    *,
    title: str,
    description: str | None,
    details: dict | None,
    request_type_code: str | None,
) -> DeBai:
    """Đề bài cho một nội dung hồ sơ. Danh mục đọc ngay lúc này: loại và phòng ĐANG BẬT, mọi mức
    ưu tiên. Danh mục nào trống thì không có gì để gợi ý — ném `LoiMoHinh`."""
    loai = tuple(
        MucDanhMuc(r.code, r.label, r.description)
        for r in session.scalars(
            select(RequestType).where(RequestType.is_active).order_by(RequestType.display_order)
        )
    )
    muc = tuple(
        MucDanhMuc(p.code, p.label)
        for p in session.scalars(select(Priority).order_by(Priority.display_order))
    )
    phong = tuple(
        MucDanhMuc(d.code, d.label, d.description)
        for d in session.scalars(
            select(Department).where(Department.is_active).order_by(Department.display_order)
        )
    )
    if not (loai and muc and phong):
        raise LoiMoHinh(LOI_THIEU_DANH_MUC, "một danh mục không có mục nào đang bật")

    # Trường riêng gọi bằng nhãn, theo loại người gửi đã chọn — mã trường không nói gì với mô hình
    chi_tiet: list[tuple[str, str]] = []
    if details and request_type_code:
        nhan = {
            t.code: t.label
            for t in session.scalars(
                select(RequestTypeField)
                .where(RequestTypeField.request_type_code == request_type_code)
                .order_by(RequestTypeField.display_order)
            )
        }
        for ma_truong, ten in nhan.items():
            gia_tri = details.get(ma_truong)
            if gia_tri not in (None, "", []):
                chi_tiet.append((ten, _gia_tri_chu(gia_tri)))
    return DeBai(
        title=title,
        description=description or "",
        details=tuple(chi_tiet),
        request_types=loai,
        priorities=muc,
        departments=phong,
    )


def de_bai_cua_ho_so(session: Session, ho_so: Request) -> DeBai:
    return dung_de_bai(
        session,
        title=ho_so.title,
        description=ho_so.description,
        details=ho_so.details,
        request_type_code=ho_so.request_type_code,
    )


# ---------------------------------------------------------------------------
# Lời gọi
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PhanLoai:
    """Ba mã gợi ý, đã kiểm nằm trong danh mục của đề bài, kèm lý do từng mã."""

    request_type_code: str
    priority_code: str
    department_code: str
    reasons: dict[str, str]
    elapsed_ms: int
    model: str

    def ma(self, truong: str) -> str:
        return getattr(self, truong)


def _goi_trong_han(ham, han_giay: float):
    """Chạy `ham()` ở luồng riêng và chờ đúng `han_giay` — hạn chót cứng, kể cả bước tra DNS."""
    tuong_lai = _LUONG_GOI.submit(ham)
    try:
        return tuong_lai.result(timeout=han_giay)
    except HetGio as loi:
        tuong_lai.cancel()
        raise LoiMoHinh(LOI_QUA_HAN, f"quá {han_giay:g} giây") from loi


def _post_json(url: str, than: dict, han_giay: float) -> dict:
    yeu_cau = urllib.request.Request(
        url,
        data=json.dumps(than).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(yeu_cau, timeout=han_giay) as phan_hoi:
            du_lieu = phan_hoi.read()
    except urllib.error.HTTPError as loi:
        raise LoiMoHinh(LOI_MAY_CHU, f"HTTP {loi.code}") from loi
    except (TimeoutError, ConnectionError) as loi:
        # `TimeoutError` ở đây là hết hạn đọc của socket — cùng nghĩa với hạn chót
        ma = LOI_QUA_HAN if isinstance(loi, TimeoutError) else LOI_KHONG_KET_NOI
        raise LoiMoHinh(ma, str(loi)) from loi
    except (urllib.error.URLError, OSError) as loi:
        ly_do = getattr(loi, "reason", loi)
        ma = LOI_QUA_HAN if isinstance(ly_do, TimeoutError) else LOI_KHONG_KET_NOI
        raise LoiMoHinh(ma, str(ly_do)) from loi
    try:
        return json.loads(du_lieu)
    except ValueError as loi:
        raise LoiMoHinh(LOI_SAI_DINH_DANG, "phản hồi không phải JSON") from loi


def _doc_ket_qua(de_bai: DeBai, phan_hoi: dict) -> tuple[dict[str, str], dict[str, str]]:
    """(mã theo trường, lý do theo trường) từ phản hồi kiểu OpenAI, đã kiểm danh mục."""
    try:
        noi_dung = phan_hoi["choices"][0]["message"]["content"]
        dap_an = json.loads(noi_dung)
    except (KeyError, IndexError, TypeError, ValueError) as loi:
        raise LoiMoHinh(LOI_SAI_DINH_DANG, "không đọc được JSON trong câu trả lời") from loi
    if not isinstance(dap_an, dict):
        raise LoiMoHinh(LOI_SAI_DINH_DANG, "câu trả lời không phải đối tượng JSON")

    ma: dict[str, str] = {}
    ly_do: dict[str, str] = {}
    for truong in CAC_TRUONG:
        gia_tri = dap_an.get(truong)
        if not isinstance(gia_tri, str):
            raise LoiMoHinh(LOI_SAI_DINH_DANG, f"thiếu {truong}")
        # Kiểm lại dù lược đồ đã ràng buộc: không mã nào ngoài danh mục đi qua được lớp này
        if gia_tri not in de_bai.danh_muc[truong]:
            raise LoiMoHinh(LOI_NGOAI_DANH_MUC, f"{truong}={gia_tri!r}")
        ma[truong] = gia_tri
        cau = dap_an.get(_khoa_ly_do(truong))
        ly_do[truong] = " ".join(cau.split())[:DO_DAI_LY_DO] if isinstance(cau, str) else ""
    return ma, ly_do


def hoi_phan_loai(
    de_bai: DeBai, *, url: str | None = None, han_giay: float | None = None
) -> PhanLoai:
    """Hỏi mô hình ba gợi ý cho một đề bài. Ném `LoiMoHinh` nếu không có gợi ý dùng được."""
    cau_hinh = get_settings()
    goc = (url if url is not None else cau_hinh.llm_url).strip().rstrip("/")
    if not goc:
        raise LoiMoHinh(LOI_TAT, "chưa cấu hình địa chỉ mô hình")
    han = han_giay if han_giay is not None else cau_hinh.llm_timeout_seconds

    than = {
        "model": cau_hinh.llm_model,
        "messages": de_bai.tin_nhan(),
        "temperature": 0,
        "max_tokens": cau_hinh.llm_max_tokens,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "phan_loai", "strict": True, "schema": de_bai.luoc_do()},
        },
    }
    bat_dau = time.monotonic()
    phan_hoi = _goi_trong_han(lambda: _post_json(goc + "/v1/chat/completions", than, han), han)
    ma, ly_do = _doc_ket_qua(de_bai, phan_hoi)
    return PhanLoai(
        request_type_code=ma[TRUONG_LOAI],
        priority_code=ma[TRUONG_MUC],
        department_code=ma[TRUONG_PHONG],
        reasons=ly_do,
        elapsed_ms=round((time.monotonic() - bat_dau) * 1000),
        model=cau_hinh.llm_model,
    )


def goi_y_phan_loai(session: Session, ho_so: Request) -> PhanLoai | None:
    """Ba gợi ý cho một hồ sơ, hoặc `None` — "không có gợi ý" — với mọi lỗi."""
    try:
        return hoi_phan_loai(de_bai_cua_ho_so(session, ho_so))
    except LoiMoHinh as loi:
        if loi.ma != LOI_TAT:
            log.warning("Mô hình không cho gợi ý cho hồ sơ %s: %s", ho_so.id, loi)
        return None


# ---------------------------------------------------------------------------
# Tình trạng
# ---------------------------------------------------------------------------


def tinh_trang() -> dict[str, Any]:
    """Tình trạng dịch vụ mô hình: `disabled` (địa chỉ rỗng), `ready`, hay `unreachable`.

    Hỏi điểm `/health` của llama.cpp server, hạn chót ngắn: người quản trị đang chờ màn Hệ thống.
    Mô hình đang nạp (llama.cpp trả 503) cũng là chưa phản hồi được, kèm chi tiết.
    """
    cau_hinh = get_settings()
    ket_qua: dict[str, Any] = {"status": TAT, "model": cau_hinh.llm_model}
    goc = cau_hinh.llm_url.strip().rstrip("/")
    if not goc:
        return ket_qua
    han = cau_hinh.llm_health_timeout_seconds

    def hoi() -> int:
        try:
            with urllib.request.urlopen(goc + "/health", timeout=han) as phan_hoi:
                return phan_hoi.status
        except urllib.error.HTTPError as loi:
            return loi.code

    try:
        ma = _goi_trong_han(hoi, han)
    except LoiMoHinh:
        return {**ket_qua, "status": KHONG_PHAN_HOI, "detail": f"không trả lời trong {han:g} giây"}
    except (urllib.error.URLError, OSError) as loi:
        return {**ket_qua, "status": KHONG_PHAN_HOI, "detail": str(getattr(loi, "reason", loi))[:200]}
    if ma == 200:
        return {**ket_qua, "status": SAN_SANG}
    chi_tiet = "đang nạp mô hình" if ma == 503 else f"HTTP {ma}"
    return {**ket_qua, "status": KHONG_PHAN_HOI, "detail": chi_tiet}
