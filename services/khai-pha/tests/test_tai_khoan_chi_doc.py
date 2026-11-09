# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Tài khoản cơ sở dữ liệu của dịch vụ khai phá phải CHỈ ĐỌC và chỉ đọc ĐÚNG những gì phép khai phá cần
# (migration 0019 của dịch vụ ứng dụng). Dịch vụ này sống trong cùng mạng với thư viện AGPL và nhận lời
# gọi qua HTTP: nếu tài khoản thừa quyền thì lỗi ở đây thành lỗi ghi vào dữ liệu nghiệp vụ.
#
# Các bài ghi mở phiên ở chế độ đọc-ghi (fixture `ket_noi_ghi`) để thử quyền của chính tài khoản, tách
# khỏi chế độ chỉ đọc của phiên; mọi lệnh bị từ chối ngay ở bước kiểm quyền và cuối bài đều hoàn tác.

from __future__ import annotations

import psycopg
import pytest
from psycopg import errors

# Đúng danh sách migration 0019 cấp SELECT
BANG_DUOC_DOC = (
    "bao_cao_nhat_ky",
    "event_log",
    "states",
    "transitions",
    "work_calendars",
    "work_hours",
    "holidays",
)
# Có trong lược đồ nhưng không được cấp: dữ liệu hồ sơ, danh mục, người dùng
BANG_KHONG_DUOC_DOC = ("requests", "departments", "request_types", "priorities", "rule_sets")


def test_phien_mac_dinh_cua_tai_khoan_la_chi_doc(dia_chi):
    try:
        with psycopg.connect(dia_chi, connect_timeout=5) as ket_noi:
            che_do = ket_noi.execute("SHOW default_transaction_read_only").fetchone()[0]
    except psycopg.OperationalError as loi:
        pytest.skip(f"Không kết nối được PostgreSQL của cụm ({loi}).")
    assert che_do == "on"


def test_tai_khoan_khong_phai_sieu_nguoi_dung(ket_noi_ghi):
    dong = ket_noi_ghi.execute(
        "SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = current_user"
    ).fetchone()
    assert dong == (False, False, False)


@pytest.mark.parametrize("bang", BANG_DUOC_DOC)
def test_doc_duoc_bang_trong_danh_sach_cap(ket_noi_ghi, bang):
    ket_noi_ghi.execute(f"SELECT count(*) FROM public.{bang}").fetchone()


@pytest.mark.parametrize("bang", BANG_KHONG_DUOC_DOC)
def test_doc_bang_ngoai_danh_sach_bi_tu_choi(ket_noi_ghi, bang):
    with pytest.raises(errors.InsufficientPrivilege):
        ket_noi_ghi.execute(f"SELECT 1 FROM public.{bang} LIMIT 1")


def test_chen_vao_nhat_ky_bi_tu_choi(ket_noi_ghi):
    # Phiên đã mở đọc-ghi, nên lệnh chỉ có thể bị chặn bởi QUYỀN của tài khoản
    with pytest.raises(errors.InsufficientPrivilege):
        ket_noi_ghi.execute(
            "INSERT INTO public.event_log (case_id, activity, actor, from_state, to_state) "
            "VALUES (1, 'thu', 'thu', 'a', 'b')"
        )


@pytest.mark.parametrize(
    "lenh",
    [
        "UPDATE public.event_log SET note = 'x'",
        "DELETE FROM public.event_log",
        "UPDATE public.transitions SET is_rework = NOT is_rework",
        "DELETE FROM public.states",
        "INSERT INTO public.holidays DEFAULT VALUES",
        "TRUNCATE public.event_log",
    ],
)
def test_sua_xoa_du_lieu_bi_tu_choi(ket_noi_ghi, lenh):
    with pytest.raises(errors.InsufficientPrivilege):
        ket_noi_ghi.execute(lenh)


def test_phien_mo_theo_mac_dinh_cua_dich_vu_tu_choi_ghi(dia_chi):
    """Cách dịch vụ thật sự mở kết nối (`mo_ket_noi`): chỉ đọc ở phiên, ghi bị chặn trước cả bước kiểm quyền."""
    from app.du_lieu import mo_ket_noi

    try:
        ket_noi = mo_ket_noi(dia_chi)
    except psycopg.OperationalError as loi:
        pytest.skip(f"Không kết nối được PostgreSQL của cụm ({loi}).")
    try:
        with pytest.raises((errors.ReadOnlySqlTransaction, errors.InsufficientPrivilege)):
            ket_noi.execute("DELETE FROM public.event_log")
    finally:
        ket_noi.rollback()
        ket_noi.close()
