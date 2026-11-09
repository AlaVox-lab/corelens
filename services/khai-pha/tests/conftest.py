# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Hạ tầng chung cho bộ kiểm thử của dịch vụ khai phá (#314).
#
# Bài cần PostgreSQL THẬT của cụm (chạy trong container dịch vụ khai phá, nơi đã có KHAI_PHA_DATABASE_URI)
# và kết nối bằng chính tài khoản chỉ đọc của dịch vụ. Tài khoản mặc định chỉ đọc, nên phiên của bài
# mở đọc-ghi riêng để tạo BẢNG TẠM (xem tests/dap_an.py); cuối bài hoàn tác, không gì ghi vào `public`.
#
# Cách chạy (cụm đang chạy):
#
#     docker exec dxlab-khai-pha python -m pytest -q
#
# Chạy tay thì thiếu PostgreSQL chỉ bỏ qua bài. Trong quy trình tích hợp liên tục thì bỏ qua nghĩa là
# cụm dựng hỏng, nên đặt DXLAB_CAM_BO_QUA=1 để bài bị bỏ qua cũng tính là thất bại (như backend).

from __future__ import annotations

import os

import psycopg
import pytest

from app.bo_may import chon_bo_may
from app.cau_hinh import cau_hinh
from app.du_lieu import mo_ket_noi

from . import dap_an

CAM_BO_QUA = os.environ.get("DXLAB_CAM_BO_QUA") == "1"


def pytest_sessionfinish(session, exitstatus):
    if not CAM_BO_QUA or exitstatus != 0:
        return
    bao_cao = session.config.pluginmanager.get_plugin("terminalreporter")
    so_bo_qua = len(bao_cao.stats.get("skipped", [])) if bao_cao else 0
    if so_bo_qua:
        print(f"\nDXLAB_CAM_BO_QUA=1: có {so_bo_qua} bài bị bỏ qua, coi là thất bại.")
        session.exitstatus = 1


@pytest.fixture(scope="session")
def dia_chi() -> str:
    return cau_hinh().database_uri


@pytest.fixture(scope="session")
def mui_gio(dia_chi) -> str:
    """Múi giờ của lịch làm việc mặc định — bài đặt mốc theo múi giờ này, không giả định."""
    try:
        with mo_ket_noi(dia_chi) as ket_noi:
            dong = ket_noi.execute("SELECT time_zone FROM work_calendars WHERE is_default").fetchone()
    except psycopg.Error as loi:
        pytest.skip(f"Không kết nối được PostgreSQL của cụm ({loi}).")
    assert dong, "Cụm chưa có lịch làm việc mặc định"
    return dong[0]


@pytest.fixture(params=["pm4py", "noi_bo"])
def bo_may(request):
    """Mỗi phép kiểm chạy với CẢ HAI bộ máy."""
    try:
        return chon_bo_may(request.param)
    except ImportError as loi:
        pytest.skip(f"Bộ máy {request.param} không nạp được: {loi}")


@pytest.fixture
def ket_noi_ghi(dia_chi, mui_gio):
    """Phiên của tài khoản chỉ đọc nhưng MỞ ở chế độ đọc-ghi, để thử quyền và để tạo bảng tạm.
    Không bao giờ commit: cuối bài hoàn tác."""
    try:
        ket_noi = psycopg.connect(dia_chi, connect_timeout=5)
    except psycopg.Error as loi:
        pytest.skip(f"Không kết nối được PostgreSQL của cụm ({loi}).")
    ket_noi.read_only = False
    try:
        yield ket_noi
    finally:
        ket_noi.rollback()
        ket_noi.close()


@pytest.fixture
def ket_noi_thu(ket_noi_ghi, mui_gio):
    """Phiên đọc-ghi mang bốn bảng tạm đã nạp bộ dữ liệu đáp án biết trước."""
    dap_an.nap(ket_noi_ghi, mui_gio)
    return ket_noi_ghi


@pytest.fixture
def ket_noi_that(dia_chi, mui_gio):
    """Kết nối chỉ đọc của dịch vụ tới dữ liệu thật ở `public` (không có bảng tạm nào)."""
    ket_noi = mo_ket_noi(dia_chi)
    try:
        yield ket_noi
    finally:
        ket_noi.rollback()
        ket_noi.close()


@pytest.fixture
def ma_ho_so_trong_khoang():
    """Hồ sơ của bộ dữ liệu thử gửi trong khoảng thử chính (09-13/03/2026, theo giờ của lịch)."""
    return {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16}
