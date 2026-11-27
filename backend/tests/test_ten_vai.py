# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Nhãn vai theo cách gọi chung của cổng (#561): dữ liệu khởi tạo mang nhãn mới; migration 0042 đổi nhãn ở cụm cũ CÓ
# ĐIỀU KIỆN — chỉ nhãn còn đúng chữ cũ — và trả ngược cùng điều kiện. Chạy thẳng hàm của migration trên giao dịch của
# bài, hoàn tác sau bài (cùng lối test_cach_giai_quyet.py của 0040).

import importlib.util
from pathlib import Path

from sqlalchemy import text

TEP = Path(__file__).resolve().parent.parent / "alembic" / "versions" / "0042_ten_vai.py"
_spec = importlib.util.spec_from_file_location("migration_0042", TEP)
mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mig)

TEN_TU_DAT = "Điều phối viên trung tâm"


def _nhan(session) -> dict[str, str]:
    return dict(session.execute(text("SELECT code, label FROM roles")).all())


def _dat(session, nhan: dict[str, str]) -> None:
    for ma, ten in nhan.items():
        session.execute(text("UPDATE roles SET label = :ten WHERE code = :ma"), {"ma": ma, "ten": ten})


CU = {ma: cu for ma, (cu, _) in mig.NHAN.items()}
MOI = {ma: moi for ma, (_, moi) in mig.NHAN.items()}


def test_cum_moi_co_nhan_moi(session):
    """Seed hiện hành mang đúng nhãn mà migration đổi sang: cụm mới và cụm nâng cấp gọi vai như nhau."""
    nhan = _nhan(session)
    assert {ma: nhan.get(ma) for ma in MOI} == MOI


def test_nang_cap_doi_dung_bon_nhan(session):
    _dat(session, CU)
    khac = {ma: ten for ma, ten in _nhan(session).items() if ma not in MOI}

    assert mig.doi_nhan(session.connection()) == len(MOI) == 4
    nhan = _nhan(session)
    assert {ma: nhan[ma] for ma in MOI} == MOI
    assert {ma: ten for ma, ten in nhan.items() if ma not in MOI} == khac, "không đụng vai khác"
    # Chạy lại không đổi gì nữa
    assert mig.doi_nhan(session.connection()) == 0


def test_nhan_doi_tay_giu_nguyen(session):
    _dat(session, {**CU, "classifier": TEN_TU_DAT})
    assert mig.doi_nhan(session.connection()) == 3
    nhan = _nhan(session)
    assert nhan["classifier"] == TEN_TU_DAT
    assert {ma: nhan[ma] for ma in MOI if ma != "classifier"} == {ma: t for ma, t in MOI.items() if ma != "classifier"}


def test_ha_cap_tra_ve_nhan_cu_co_dieu_kien(session):
    _dat(session, MOI)
    assert mig.tra_nhan(session.connection()) == 4
    nhan = _nhan(session)
    assert {ma: nhan[ma] for ma in CU} == CU

    # Nhãn quản trị viên tự đặt thì hạ cấp không trả về
    _dat(session, {**MOI, "classifier": TEN_TU_DAT})
    assert mig.tra_nhan(session.connection()) == 3
    assert _nhan(session)["classifier"] == TEN_TU_DAT
