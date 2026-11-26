# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ô "Nhận xét" ở bước cho chấm mức hài lòng (#559): dữ liệu khởi tạo đặt tên ô cho cạnh mang cờ `collects_feedback`,
# để dòng thời gian ghi chú của bước Xác nhận đạt dưới chữ người gửi đã thấy chứ không phải "Lý do"; migration 0041
# đặt tên ô ở cụm cũ CÓ ĐIỀU KIỆN — chỉ cạnh còn trống tên ô — và gỡ ngược cùng điều kiện. Chạy thẳng hàm của
# migration trên giao dịch của bài, hoàn tác sau bài (cùng lối test_cach_giai_quyet.py của 0040).

import importlib.util
from pathlib import Path

from sqlalchemy import text

TEP = Path(__file__).resolve().parent.parent / "alembic" / "versions" / "0041_o_nhan_xet.py"
_spec = importlib.util.spec_from_file_location("migration_0041", TEP)
mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mig)

TEN_TU_DAT = "Góp ý của bạn"

_CANH = """
    collects_feedback AND NOT is_system
    AND rule_set_id IN (SELECT id FROM rule_sets WHERE process_code = (SELECT code FROM processes WHERE is_app_default))
"""


def _ten_o(session) -> list[tuple[str | None, bool]]:
    return [
        (ten, bat_buoc)
        for ten, bat_buoc in session.execute(
            text(f"SELECT note_label, requires_note FROM transitions WHERE {_CANH} ORDER BY id")
        )
    ]


def _dat(session, ten: str | None) -> int:
    """Đưa cạnh cho chấm về một tên ô — NULL như cụm dựng trước #559."""
    return session.execute(text(f"UPDATE transitions SET note_label = :ten WHERE {_CANH}"), {"ten": ten}).rowcount


def _ngoai_pham_vi(session) -> list[tuple]:
    """Mọi cạnh khác — của quy trình khác hay không cho chấm — để kiểm migration không đụng tới."""
    return list(session.execute(text(f"SELECT id, note_label FROM transitions WHERE NOT ({_CANH}) ORDER BY id")))


def test_cum_moi_co_o_nhan_xet_khong_bat_buoc(session):
    """Seed hiện hành mang đúng tên ô mà migration đặt: cụm mới và cụm nâng cấp thấy cùng một ô, không bắt buộc."""
    ten_o = _ten_o(session)
    assert ten_o, "quy trình mặc định có cạnh cho chấm"
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
