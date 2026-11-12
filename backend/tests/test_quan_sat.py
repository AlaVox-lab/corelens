# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử quan sát vận hành (#247): điểm cuối sống/sẵn sàng, mã yêu cầu, nhật ký JSON, số đo.

from __future__ import annotations

import json
import logging
from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.auth.dependencies import current_actor
from app.db import get_session
from app.main import app
from app.quan_sat import DinhDangJson, _GanMaYeuCau, ma_yeu_cau
from app.workflow.context import Actor

QUAN_TRI = Actor(id="qt-247", roles=frozenset({"administrator"}))
NGUOI_GUI = Actor(id="ng-247", roles=frozenset({"requester"}))


@contextmanager
def _may_khach(session=None, actor: Actor | None = None):
    if session is not None:
        app.dependency_overrides[get_session] = lambda: session
    if actor is not None:
        app.dependency_overrides[current_actor] = lambda: actor
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def _phien_hong():
    raise AssertionError("điểm cuối 'sống' không được mở phiên cơ sở dữ liệu")


def test_song_khong_cham_co_so_du_lieu():
    app.dependency_overrides[get_session] = _phien_hong
    try:
        with TestClient(app) as c:
            r = c.get("/health/live")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_san_sang_kiem_co_so_du_lieu(session):
    with _may_khach(session) as c:
        r = c.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["status"] in ("ok", "degraded")


def test_ma_yeu_cau_tra_lai_va_thay_khi_khong_hop_le():
    with TestClient(app) as c:
        r = c.get("/health/live", headers={"X-Request-ID": "cong-247.abc_1"})
        assert r.headers["x-request-id"] == "cong-247.abc_1"
        # Quá dài hay ký tự lạ: không nhận, tự sinh mã khác
        r = c.get("/health/live", headers={"X-Request-ID": "x" * 100})
        assert r.headers["x-request-id"] != "x" * 100
        assert len(r.headers["x-request-id"]) == 32
        r = c.get("/health/live")
        assert r.headers["x-request-id"]


def test_dong_nhat_ky_json_mang_ma_yeu_cau():
    ban_ghi = logging.LogRecord("app.thu", logging.WARNING, __file__, 1, "Hồ sơ %s lỗi", (7,), None)
    dau = ma_yeu_cau.set("ma-247")
    try:
        _GanMaYeuCau().filter(ban_ghi)
    finally:
        ma_yeu_cau.reset(dau)
    dong = json.loads(DinhDangJson().format(ban_ghi))
    assert dong["request_id"] == "ma-247"
    assert dong["msg"] == "Hồ sơ 7 lỗi"
    assert dong["level"] == "WARNING" and dong["logger"] == "app.thu"
    assert dong["ts"].endswith("+00:00")


def test_so_do_chi_quan_tri_vien(session):
    with _may_khach(session, NGUOI_GUI) as c:
        assert c.get("/metrics").status_code == 403


def test_so_do_dang_prometheus(session):
    with _may_khach(session, QUAN_TRI) as c:
        c.get("/health/live")
        r = c.get("/metrics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    chu = r.text
    # Mẫu đường dẫn, không phải đường dẫn thật
    assert 'dxlab_http_requests_total{method="GET",route="/health/live",status="200"}' in chu
    assert 'dxlab_http_request_duration_seconds_bucket{method="GET",route="/health/live",le="+Inf"}' in chu
    assert "dxlab_http_errors_total" in chu
    assert 'dxlab_email_queue{state="deliveries_pending"}' in chu
    assert "dxlab_database_up 1" in chu
