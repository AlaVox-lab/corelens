# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử quy tắc so của điều kiện trên cạnh (#397). Luồng thật của quy trình mua sắm mẫu — dưới ngưỡng,
# đúng ngưỡng, gọi cạnh không thỏa — kiểm ở test_nhieu_quy_trinh.py.

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.rules.dieu_kien import dieu_kien_khong_dat, dung, kiem_dieu_kien
from app.workflow.errors import GuardViolation


@pytest.mark.parametrize(
    ("phep", "trai", "phai", "ket_qua"),
    [
        ("<", 4_999_999, 5_000_000, True),
        ("<", 5_000_000, 5_000_000, False),
        (">=", 5_000_000, 5_000_000, True),
        (">", "12", 5, True),  # số lưu dạng chữ vẫn so như số
        ("=", "may-in", "may-in", True),
        ("!=", "may-in", "may-chieu", True),
        ("<", "may-in", 5, False),  # so lớn nhỏ chữ với số là sai, không ném lỗi
        ("<", None, 5, False),  # trường không có trên hồ sơ
        ("=", True, 1, False),  # đúng/sai không coi là số
    ],
)
def test_quy_tac_so(phep, trai, phai, ket_qua):
    assert dung(phep, trai, phai) is ket_qua


def test_phep_so_la_bi_tu_choi():
    with pytest.raises(ValueError):
        dung("~", 1, 1)


def _ngu_canh(chi_tiet: dict, dieu_kien: list, thay_doi: dict | None = None):
    return SimpleNamespace(
        case=SimpleNamespace(details=chi_tiet),
        transition=SimpleNamespace(conditions=dieu_kien, activity_label="Duyệt"),
        changes=thay_doi or {},
    )


def _dk(truong, phep, gia_tri):
    return SimpleNamespace(field_code=truong, operator=phep, value=gia_tri, description=None)


def test_canh_khong_dieu_kien_luon_di_duoc():
    kiem_dieu_kien(_ngu_canh({}, []))


def test_moi_dieu_kien_phai_dung():
    ctx = _ngu_canh({"so-tien": 7}, [_dk("so-tien", ">", 5), _dk("so-tien", "<", 6)])
    assert [d.operator for d in dieu_kien_khong_dat(ctx)] == ["<"]
    with pytest.raises(GuardViolation) as loi:
        kiem_dieu_kien(ctx)
    assert loi.value.guard_code == "edge-condition"


def test_ban_sua_gui_kem_thay_cho_ban_dang_luu():
    ctx = _ngu_canh({"so-tien": 1}, [_dk("so-tien", ">=", 5)], {"details": {"so-tien": 9}})
    assert dieu_kien_khong_dat(ctx) == []


def test_dieu_kien_tro_toi_truong_co_khai(session):
    """Mọi điều kiện trong dữ liệu trỏ tới một trường riêng có khai cho một loại yêu cầu cùng quy trình."""
    lac = session.execute(text(
        """
        SELECT c.id, c.field_code
        FROM transition_conditions c
        JOIN transitions t ON t.id = c.transition_id
        JOIN rule_sets b ON b.id = t.rule_set_id
        WHERE NOT EXISTS (
            SELECT 1 FROM request_type_fields f
            JOIN request_types rt ON rt.code = f.request_type_code
            WHERE f.code = c.field_code AND rt.process_code = b.process_code
        )
        """
    )).all()
    assert lac == []
