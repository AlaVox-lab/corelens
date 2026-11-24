# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Migration 0039 (#538): mẫu thư của cụm cũ đổi tên hiển thị thành Corelens — chỉ ô còn nguyên văn chữ cũ của
# seed, ô quản trị viên đã sửa thì giữ. Chạy thẳng hàm của migration trên giao dịch của bài, hoàn tác sau bài.

import importlib.util
from pathlib import Path

from sqlalchemy import text

TEP = Path(__file__).resolve().parent.parent / "alembic" / "versions" / "0039_ten_hien_thi_corelens.py"
_spec = importlib.util.spec_from_file_location("migration_0039", TEP)
mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mig)

SUA_TAY = "Hồ sơ $ma_ho_so cần bạn xử lý"


def _mau(session) -> dict[str, tuple[str, str]]:
    return {
        ma: (tieu_de, noi_dung)
        for ma, tieu_de, noi_dung in session.execute(
            text("SELECT code, subject_template, body_template FROM notification_types")
        )
    }


def _dat_chu_cu(session) -> None:
    """Đưa ba loại về đúng chữ của seed trước #538 — như ở một cụm dựng từ bản cũ."""
    for ma, tieu_de, noi_dung in mig.MAU_THU:
        session.execute(
            text("UPDATE notification_types SET subject_template = :t, body_template = :n WHERE code = :ma"),
            {"ma": ma, "t": tieu_de.format(ten=mig.TEN_CU), "n": noi_dung.format(ten=mig.TEN_CU)},
        )


def test_cum_moi_da_mang_ten_moi(session):
    """Seed hiện hành đúng bằng chữ mà migration sinh ra: cụm mới và cụm nâng cấp gửi cùng một lời thư."""
    mau = _mau(session)
    for ma, tieu_de, noi_dung in mig.MAU_THU:
        assert mau[ma] == (tieu_de.format(ten=mig.TEN_MOI), noi_dung.format(ten=mig.TEN_MOI)), ma


def test_doi_chu_cu_giu_o_da_sua_tay(session):
    _dat_chu_cu(session)
    # Quản trị viên đã sửa tiêu đề của một loại: ô đó giữ nguyên, ô nội dung còn chữ cũ thì vẫn đổi
    session.execute(
        text("UPDATE notification_types SET subject_template = :t WHERE code = 'viec-cho-toi'"), {"t": SUA_TAY}
    )

    assert mig.doi_mau_thu(session.connection(), mig.TEN_CU, mig.TEN_MOI) == 5

    mau = _mau(session)
    assert mau["viec-cho-toi"][0] == SUA_TAY
    assert all(mig.TEN_CU not in t and mig.TEN_CU not in n for ma, (t, n) in mau.items() if ma != "viec-cho-toi")
    assert mig.TEN_CU not in mau["viec-cho-toi"][1]
    # Chạy lại không đổi gì nữa
    assert mig.doi_mau_thu(session.connection(), mig.TEN_CU, mig.TEN_MOI) == 0


def test_ha_cap_doi_nguoc_co_dieu_kien(session):
    session.execute(
        text("UPDATE notification_types SET body_template = :n WHERE code = 'da-tu-dong'"), {"n": SUA_TAY}
    )

    assert mig.doi_mau_thu(session.connection(), mig.TEN_MOI, mig.TEN_CU) == 5

    mau = _mau(session)
    assert mau["da-tu-dong"][1] == SUA_TAY
    assert mau["viec-cho-toi"][0] == mig.MAU_THU[0][1].format(ten=mig.TEN_CU)
