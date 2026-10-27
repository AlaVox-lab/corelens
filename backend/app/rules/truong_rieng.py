# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Trường thông tin riêng theo loại yêu cầu (#250).
#
# Mỗi loại yêu cầu khai danh sách trường trong bảng `request_type_fields`: nhãn, kiểu, bắt buộc
# hay không, lựa chọn. Mô-đun này kiểm một bộ giá trị gửi lên theo đúng khai báo đó — lúc tạo
# hồ sơ, và lúc người gửi sửa nội dung qua cạnh tự trỏ (ràng buộc `edit-content`). Không có
# tên trường nào viết trong mã: thêm một trường là thêm một dòng dữ liệu.
#
# Giá trị trả về đã chuẩn hóa: bỏ ô rỗng, số thành số, chữ cắt khoảng trắng, xếp theo thứ tự
# khai báo. Lưu đúng bản chuẩn hóa thì phép so "có gì đổi không" của cạnh sửa nội dung không
# bị đánh lừa bởi một dấu cách thừa.

from __future__ import annotations

import datetime as dt
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workflow_config import RequestType, RequestTypeField
from app.workflow.errors import InvalidFieldValue

TRUONG = "details"
CHU_TOI_DA = 500


def truong_cua_loai(session: Session, request_type_code: str | None) -> list[RequestTypeField]:
    """Danh sách trường khai cho một loại yêu cầu, theo thứ tự hiển thị."""
    if not request_type_code:
        return []
    return list(
        session.scalars(
            select(RequestTypeField)
            .where(RequestTypeField.request_type_code == request_type_code)
            .order_by(RequestTypeField.display_order, RequestTypeField.code)
        )
    )


def _loi(ma: str, cau: str) -> InvalidFieldValue:
    return InvalidFieldValue(TRUONG, ma, cau)


def _chuan_hoa(truong: RequestTypeField, gia_tri: object) -> object:
    """Một giá trị theo kiểu khai báo; sai kiểu thì nói bằng nhãn của trường."""
    if truong.kind == "text":
        if not isinstance(gia_tri, str):
            raise _loi(truong.code, f"{truong.label} phải là chữ.")
        if len(gia_tri) > CHU_TOI_DA:
            raise _loi(truong.code, f"{truong.label} dài tối đa {CHU_TOI_DA} ký tự.")
        return gia_tri.strip()

    if truong.kind == "number":
        if isinstance(gia_tri, bool) or not isinstance(gia_tri, (int, float, str)):
            raise _loi(truong.code, f"{truong.label} phải là một số.")
        try:
            so = Decimal(str(gia_tri).strip())
        except InvalidOperation:
            raise _loi(truong.code, f"{truong.label} phải là một số.") from None
        if not so.is_finite() or so < 0:
            raise _loi(truong.code, f"{truong.label} phải là một số không âm.")
        return int(so) if so == so.to_integral_value() else float(so)

    if truong.kind == "date":
        try:
            return dt.date.fromisoformat(str(gia_tri)).isoformat()
        except ValueError:
            raise _loi(truong.code, f"{truong.label} phải là một ngày hợp lệ.") from None

    # choice
    if gia_tri not in (truong.options or []):
        raise _loi(
            truong.code,
            f"{truong.label} chỉ nhận một trong: {', '.join(truong.options or [])}.",
        )
    return gia_tri


def kiem_chi_tiet(
    session: Session, request_type_code: str | None, chi_tiet: object
) -> dict:
    """Kiểm và chuẩn hóa bộ giá trị trường riêng theo khai báo của loại yêu cầu.

    Từ chối khi: không phải một bộ khóa–giá trị; có khóa loại này không khai; sai kiểu; thiếu
    trường bắt buộc. Thông báo dùng nhãn trường và nhãn loại yêu cầu, không dùng mã.
    """
    if chi_tiet is None:
        chi_tiet = {}
    if not isinstance(chi_tiet, dict):
        raise _loi("", "Thông tin riêng của hồ sơ phải là một bộ trường và giá trị.")

    cac_truong = truong_cua_loai(session, request_type_code)
    theo_ma = {t.code: t for t in cac_truong}
    thua = sorted(k for k in chi_tiet if k not in theo_ma)
    if thua:
        loai = session.get(RequestType, request_type_code) if request_type_code else None
        ten_loai = loai.label if loai else "hồ sơ chưa có loại"
        raise _loi(thua[0], f"Loại yêu cầu “{ten_loai}” không có trường “{thua[0]}”.")

    ket_qua: dict = {}
    for truong in cac_truong:
        gia_tri = chi_tiet.get(truong.code)
        if isinstance(gia_tri, str) and not gia_tri.strip():
            gia_tri = None
        if gia_tri is None:
            if truong.required:
                raise _loi(truong.code, f"Chưa điền {truong.label}.")
            continue
        ket_qua[truong.code] = _chuan_hoa(truong, gia_tri)
    return ket_qua
