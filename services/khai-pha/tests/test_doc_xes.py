# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 AlaVox-lab
#
# Tệp XES mà dịch vụ ứng dụng xuất (#444) mở được bằng một công cụ khai phá quy trình nguồn mở — PM4Py.
#
# Dịch vụ ứng dụng viết XES bằng thư viện chuẩn và không được nhập PM4Py (AGPL, ADR-0007), nên bài đọc lại nằm
# ở đây, bên trong ranh giới AGPL. `du_lieu/nhat-ky-mau.xes` là đầu ra thật của hàm `xes()` trong
# backend/app/analytics/xuat_du_lieu.py trên sáu hồ sơ trình diễn; đổi định dạng XES thì sinh lại tệp — trong
# container dịch vụ ứng dụng của một cụm thử đã nạp dữ liệu trình diễn:
#
#     from app.analytics.xuat_du_lieu import COT, xes
#     xes(phien.execute(text(f"SELECT {', '.join(COT)} FROM bao_cao_nhat_ky ORDER BY case_id, timestamp, thu_tu")).all())
#
# Bản dịch vụ chạy bộ máy dự phòng không có PM4Py (MINING_ENGINE=noi_bo, bỏ dòng pm4py) thì bỏ qua bài này.

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

pm4py = pytest.importorskip("pm4py")

TEP = Path(__file__).parent / "du_lieu" / "nhat-ky-mau.xes"


@pytest.fixture(scope="module")
def nhat_ky():
    return pm4py.read_xes(str(TEP))


def test_doc_duoc_du_trace_va_su_kien(nhat_ky):
    assert nhat_ky["case:concept:name"].nunique() == 6
    assert len(nhat_ky) == 39
    # Mỗi hồ sơ mở đầu bằng sự kiện tạo hồ sơ
    dau = nhat_ky.sort_values("time:timestamp").groupby("case:concept:name").first()
    assert set(dau["concept:name"]) == {"create-case"}


def test_moc_thoi_gian_la_utc(nhat_ky):
    moc = nhat_ky["time:timestamp"]
    assert str(moc.dt.tz) == "UTC"
    assert moc.min() > dt.datetime(2026, 1, 1, tzinfo=dt.UTC)


def test_thuoc_tinh_chuan_va_rieng(nhat_ky):
    for cot in ("concept:name", "time:timestamp", "org:resource", "to_state", "process_code"):
        assert cot in nhat_ky.columns, cot
    assert set(nhat_ky["rule_set_id"].dropna().astype(int)) == {1}


def test_khai_pha_duoc(nhat_ky):
    """Đọc được chưa đủ: thuật toán khai phá chạy được trên nhật ký đó."""
    dfg, dau, cuoi = pm4py.discover_dfg(nhat_ky)
    assert dfg and dau == {"create-case": 6}
    assert cuoi
