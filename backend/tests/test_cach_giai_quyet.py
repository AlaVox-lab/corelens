# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ô "Cách giải quyết" ở bước Hoàn thành xử lý (#556): dữ liệu khởi tạo đặt tên ô, ô không bắt buộc; migration 0040
# đặt tên ô ở cụm cũ CÓ ĐIỀU KIỆN — chỉ cạnh còn trống tên ô — và gỡ ngược cùng điều kiện. Chạy thẳng hàm của
# migration trên giao dịch của bài, hoàn tác sau bài (cùng lối test_ten_hien_thi.py của 0039).

import importlib.util
from pathlib import Path

from sqlalchemy import text

TEP = Path(__file__).resolve().parent.parent / "alembic" / "versions" / "0040_o_cach_giai_quyet.py"
_spec = importlib.util.spec_from_file_location("migration_0040", TEP)
mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mig)

TEN_TU_DAT = "Ghi chú bàn giao"

_CANH = """
    activity_code = :hoat_dong AND NOT is_system
    AND rule_set_id IN (SELECT id FROM rule_sets WHERE process_code = (SELECT code FROM processes WHERE is_app_default))
"""


def _ten_o(session) -> list[tuple[str | None, bool]]:
    return [
        (ten, bat_buoc)
        for ten, bat_buoc in session.execute(
            text(f"SELECT note_label, requires_note FROM transitions WHERE {_CANH} ORDER BY id"),
            {"hoat_dong": mig.HOAT_DONG},
        )
    ]


def _dat(session, ten: str | None) -> int:
    """Đưa cạnh Hoàn thành xử lý về một tên ô — NULL như cụm dựng trước #556."""
    return session.execute(
        text(f"UPDATE transitions SET note_label = :ten WHERE {_CANH}"), {"ten": ten, "hoat_dong": mig.HOAT_DONG}
    ).rowcount


def _ngoai_pham_vi(session) -> list[tuple]:
    """Mọi cạnh khác — của quy trình khác hay hoạt động khác — để kiểm migration không đụng tới."""
    return list(
        session.execute(
            text(f"SELECT id, note_label FROM transitions WHERE NOT ({_CANH}) ORDER BY id"),
            {"hoat_dong": mig.HOAT_DONG},
        )
    )


def test_cum_moi_co_o_cach_giai_quyet_khong_bat_buoc(session):
    """Seed hiện hành mang đúng tên ô mà migration đặt: cụm mới và cụm nâng cấp thấy cùng một ô, không bắt buộc."""
    ten_o = _ten_o(session)
    assert ten_o, "quy trình mặc định có cạnh Hoàn thành xử lý"
    assert all(ten == mig.TEN_O and not bat_buoc for ten, bat_buoc in ten_o), ten_o


def test_nang_cap_dat_ten_o_chi_khi_con_trong(session):
    so_canh = _dat(session, None)
    khac = _ngoai_pham_vi(session)

    assert mig.dat_ten_o(session.connection()) == so_canh
    assert all(ten == mig.TEN_O for ten, _ in _ten_o(session))
    assert all(not bat_buoc for _, bat_buoc in _ten_o(session)), "ô vẫn không bắt buộc"
    assert _ngoai_pham_vi(session) == khac, "không đụng cạnh nào khác"
    # Chạy lại không đổi gì nữa
    assert mig.dat_ten_o(session.connection()) == 0

    # Chuỗi rỗng, chỉ dấu cách cũng là còn trống
    _dat(session, "  ")
    assert mig.dat_ten_o(session.connection()) == so_canh


def test_nang_cap_giu_ten_o_quan_tri_vien_da_dat(session):
    _dat(session, TEN_TU_DAT)
    assert mig.dat_ten_o(session.connection()) == 0
    assert all(ten == TEN_TU_DAT for ten, _ in _ten_o(session))


def test_ha_cap_go_nguoc_co_dieu_kien(session):
    so_canh = _dat(session, mig.TEN_O)
    assert mig.go_ten_o(session.connection()) == so_canh
    assert all(ten is None for ten, _ in _ten_o(session))

    # Tên quản trị viên tự đặt thì hạ cấp không gỡ
    _dat(session, TEN_TU_DAT)
    assert mig.go_ten_o(session.connection()) == 0
    assert all(ten == TEN_TU_DAT for ten, _ in _ten_o(session))
