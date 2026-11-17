# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Điều kiện trên cạnh (#397).
#
# Bảng `transition_conditions` gắn điều kiện vào một cạnh: so một trường riêng của hồ sơ (`requests.details`)
# với một giá trị. Cạnh chỉ đi được khi mọi điều kiện của nó đúng. Không tên trường, ngưỡng hay phép so nào nằm
# trong mã — mô-đun này chỉ biết cách SO.
#
# Điều kiện chạy ở cùng hai chỗ với ràng buộc Poka-yoke (app/rules/guards.py):
#   - lúc chào nút (`input_free_guards_pass`): điều kiện không đọc gì người dùng sắp nhập — trừ trường riêng
#     đang sửa ở chính cạnh đó, mà cạnh có điều kiện là cạnh duyệt, không sửa — nên cạnh không thỏa không hiện;
#   - lúc đi thật (`run_guards`): không thỏa thì từ chối, mã ràng buộc `edge-condition`.
#
# Quy tắc so, để rẽ nhánh luôn đoán trước được:
#   - trường không có trên hồ sơ → điều kiện SAI (cạnh có điều kiện không bao giờ đi được nhờ thiếu dữ liệu);
#   - hai phía đều là số → so số; `=`, `!=` với chữ → so chữ; so lớn nhỏ giữa chữ với số → SAI.

from __future__ import annotations

import operator
from decimal import Decimal, InvalidOperation
from typing import Any

from app.workflow.context import TransitionContext
from app.workflow.errors import GuardViolation

MA_RANG_BUOC = "edge-condition"

_PHEP_SO = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "=": operator.eq,
    "!=": operator.ne,
}


def _so(gia_tri: Any) -> Decimal | None:
    if isinstance(gia_tri, bool):
        return None
    if isinstance(gia_tri, (int, float, Decimal)):
        return Decimal(str(gia_tri))
    if isinstance(gia_tri, str):
        try:
            return Decimal(gia_tri.strip())
        except InvalidOperation:
            return None
    return None


def dung(phep_so: str, ben_trai: Any, ben_phai: Any) -> bool:
    """Một điều kiện có đúng không. Phép so lạ thì ném lỗi — dữ liệu cấu hình sai, không lặng lẽ cho qua."""
    ham = _PHEP_SO.get(phep_so)
    if ham is None:
        raise ValueError(f"Phép so không hỗ trợ: {phep_so!r}")
    if ben_trai is None:
        return False
    so_trai, so_phai = _so(ben_trai), _so(ben_phai)
    if so_trai is not None and so_phai is not None:
        return ham(so_trai, so_phai)
    if phep_so in ("=", "!="):
        return ham(str(ben_trai), str(ben_phai))
    return False


def chi_tiet_khi_di(ctx: TransitionContext) -> dict:
    """Trường riêng mà hồ sơ sẽ mang khi đi cạnh này: bản đang lưu, đè bằng bản sửa gửi kèm nếu có."""
    chi_tiet = dict(ctx.case.details or {})
    moi = ctx.changes.get("details") if ctx.changes else None
    if isinstance(moi, dict):
        chi_tiet = moi
    return chi_tiet


def dieu_kien_khong_dat(ctx: TransitionContext) -> list:
    """Những điều kiện của cạnh đang SAI với hồ sơ này; rỗng là cạnh đi được."""
    cac_dieu_kien = ctx.transition.conditions
    if not cac_dieu_kien:
        return []
    chi_tiet = chi_tiet_khi_di(ctx)
    return [dk for dk in cac_dieu_kien if not dung(dk.operator, chi_tiet.get(dk.field_code), dk.value)]


def kiem_dieu_kien(ctx: TransitionContext) -> None:
    """Ném `GuardViolation` khi có điều kiện sai — gọi từ `run_guards`."""
    sai = dieu_kien_khong_dat(ctx)
    if sai:
        mo_ta = "; ".join(dk.description or f"{dk.field_code} {dk.operator} {dk.value}" for dk in sai)
        raise GuardViolation(
            MA_RANG_BUOC,
            f"Hồ sơ không thỏa điều kiện của bước “{ctx.transition.activity_label}”: {mo_ta}.",
        )
