# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
"""Phân trang, tìm và lọc dùng chung cho các điểm cuối danh sách (#232).

Mọi điểm cuối danh sách nhận `limit` và `offset`, trả kèm `total` — không điểm cuối nào trả cả
tập mà không có giới hạn. Ô tìm của giao diện đi qua tham số `q` phía dịch vụ: đã cắt trang thì tìm
trên trang đang tải là tìm sai.

Tìm khớp tiêu đề, tên người gửi, hay mã hồ sơ. Mã hiển thị `YC-2026-0184` dựng từ năm và định
danh (`routes._ma_ho_so`), nên chuỗi tìm có chữ số thì khớp thêm định danh — gõ `184` hay
`YC-2026-0184` đều ra hồ sơ đó.

Tìm không phân biệt dấu và hoa thường, như ô tìm trên trình duyệt trước đây: gõ "may in" ra
"Máy in", "dung" ra "Dũng". Phía SQL bỏ dấu bằng `translate` có sẵn của PostgreSQL — không cần
cài thêm phần mở rộng nào vào cơ sở dữ liệu.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Annotated, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import String, func, or_

from app.models.case import Request

GIOI_HAN_MAC_DINH = 50
GIOI_HAN_TOI_DA = 200

T = TypeVar("T")

# Bảng bỏ dấu tiếng Việt cho `translate` của SQL — mỗi ký tự có dấu (viết thường, dựng sẵn) ứng
# với một chữ không dấu cùng vị trí
_CO_DAU = "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
_KHONG_DAU = "a" * 17 + "e" * 11 + "i" * 5 + "o" * 17 + "u" * 11 + "y" * 5 + "d"


def bo_dau(chu: str) -> str:
    """Viết thường, bỏ dấu tiếng Việt: "Máy in Đà Nẵng" → "may in da nang"."""
    tach = unicodedata.normalize("NFD", chu.lower())
    return "".join(c for c in tach if not unicodedata.combining(c)).replace("đ", "d")


def _bo_dau_sql(cot):
    return func.translate(func.lower(cot), _CO_DAU, _KHONG_DAU, type_=String)


class ThamSoTrang(BaseModel):
    limit: int = GIOI_HAN_MAC_DINH
    offset: int = 0


def tham_so_trang(
    limit: Annotated[
        int, Query(ge=1, le=GIOI_HAN_TOI_DA, description="Số dòng tối đa một trang")
    ] = GIOI_HAN_MAC_DINH,
    offset: Annotated[int, Query(ge=0, description="Bỏ qua chừng này dòng đầu")] = 0,
) -> ThamSoTrang:
    return ThamSoTrang(limit=limit, offset=offset)


def cat_trang(ds: list[T], trang: ThamSoTrang) -> list[T]:
    """Cắt một danh sách đã xếp — cho hàng đợi, nơi thứ tự độ gấp tính ở dịch vụ."""
    return ds[trang.offset : trang.offset + trang.limit]


def dieu_kien_tim(q: str | None):
    """Điều kiện SQL cho chuỗi tìm, hoặc `None` khi không tìm."""
    q = (q or "").strip()
    if not q:
        return None
    khoa = bo_dau(q)
    dieu_kien = [
        _bo_dau_sql(Request.title).contains(khoa, autoescape=True),
        _bo_dau_sql(Request.requester_label).contains(khoa, autoescape=True),
    ]
    so = re.findall(r"\d+", q)
    if so:
        # Phần số cuối là định danh: "YC-2026-0184" → 184, "184" → 184
        dieu_kien.append(Request.id == int(so[-1]))
    return or_(*dieu_kien)


def khop_tim(q: str | None, *chuoi: str | None) -> bool:
    """Bản Python của `dieu_kien_tim`, cho danh sách đã dựng sẵn ở dịch vụ (hộp thư)."""
    khoa = bo_dau((q or "").strip())
    if not khoa:
        return True
    return any(khoa in bo_dau(c or "") for c in chuoi)
