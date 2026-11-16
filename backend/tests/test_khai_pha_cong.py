# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Lối vào màn quy trình thực tế (#314): ai được hỏi dịch vụ khai phá, với phạm vi phòng nào.
#
# Dịch vụ khai phá được thay bằng bản giả ghi lại phạm vi dịch vụ ứng dụng gửi đi — thứ cần kiểm ở
# đây là quyết định của dịch vụ ứng dụng. Phép khai phá có bài kiểm thử đáp án biết trước riêng trong
# services/khai-pha/tests/. Client HTTP thật được thử với một máy chủ nhỏ dựng ngay trong bài.
from __future__ import annotations

import datetime as dt
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.analytics.khai_pha import KhaiPhaClient, KhaiPhaKhongPhanHoi, khai_pha_client
from app.auth.dependencies import current_actor, current_claims
from app.config import get_settings
from app.db import get_session
from app.main import app
from app.models.workflow_config import Department, RequestType
from app.workflow.engine import ma_quy_trinh_ung_dung
from app.workflow.context import Actor
from app.workflow.engine import create_case

TU, DEN = "2026-10-01", "2026-10-31"


class KhaiPhaGia:
    def __init__(self) -> None:
        self.lan_goi: list[tuple[dt.date, dt.date, list[str] | None]] = []
        self.hong = False
        self.ket_qua: dict = {"engine": "gia", "cases_count": 0, "states": [], "edges": []}

    def khai_pha(self, tu, den, phong):
        if self.hong:
            raise KhaiPhaKhongPhanHoi("tắt")
        self.lan_goi.append((tu, den, phong))
        return self.ket_qua


@pytest.fixture
def client(session):
    gia = KhaiPhaGia()
    dang_goi: dict = {}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: dang_goi["actor"]
    app.dependency_overrides[current_claims] = lambda: {}
    app.dependency_overrides[khai_pha_client] = lambda: gia
    with TestClient(app) as c:
        c.dang_goi, c.gia = dang_goi, gia
        yield c
    app.dependency_overrides.clear()


def _hoi(client, actor, tu=TU, den=DEN):
    client.dang_goi["actor"] = actor
    return client.get("/analytics/process-mining", params={"from": tu, "to": den})


def test_truong_phong_chi_hoi_phong_minh(client, phong_ban):
    tp = Actor(id="tp-314", roles=frozenset({"approver"}), departments=frozenset({phong_ban}))
    r = _hoi(client, tp)
    assert r.status_code == 200, r.text
    assert client.gia.lan_goi == [(dt.date(2026, 10, 1), dt.date(2026, 10, 31), [phong_ban])]
    assert r.json()["scope"]["all"] is False
    assert [p["code"] for p in r.json()["scope"]["departments"]] == [phong_ban]


@pytest.mark.parametrize("vai", ["classifier", "administrator"])
def test_dieu_phoi_va_quan_tri_hoi_toan_cong_ty(client, vai):
    r = _hoi(client, Actor(id=f"{vai}-314", roles=frozenset({vai})))
    assert r.status_code == 200, r.text
    assert client.gia.lan_goi[-1][2] is None
    assert r.json()["scope"] == {"all": True, "departments": []}
    assert r.json()["engine"] == "gia"


@pytest.mark.parametrize("vai", ["requester", "handler"])
def test_vai_khong_xem_bao_cao_nhan_403_va_khong_hoi_dich_vu(client, vai, phong_ban):
    r = _hoi(client, Actor(id=f"{vai}-314", roles=frozenset({vai}), departments=frozenset({phong_ban})))
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "reports-forbidden"
    assert client.gia.lan_goi == []


def test_ma_phong_la_trong_token_khong_di_toi_dich_vu(client):
    r = _hoi(client, Actor(id="tp-la-314", roles=frozenset({"approver"}),
                           departments=frozenset({"phong-khong-ton-tai-314"})))
    assert r.status_code == 403
    assert client.gia.lan_goi == []


@pytest.mark.parametrize(("tu", "den"), [("2026-10-31", "2026-10-01"), ("2025-01-01", "2026-06-01")])
def test_khoang_ngay_sai_nhan_422_va_khong_hoi_dich_vu(client, tu, den):
    r = _hoi(client, Actor(id="dp-314", roles=frozenset({"classifier"})), tu=tu, den=den)
    assert r.status_code == 422
    assert client.gia.lan_goi == []


def test_kem_nhan_loai_yeu_cau_va_phong_ban_tu_bang(client, session, phong_ban):
    # #315: dịch vụ khai phá tách nhóm theo mã; nhãn đọc từ hai bảng danh mục, không mã cứng. Loại đã
    # ngừng dùng vẫn có nhãn, vì hồ sơ cũ trong khoảng ngày có thể mang mã đó
    session.add(RequestType(code="loai-cu-315", process_code=ma_quy_trinh_ung_dung(session),
                            label="Loại đã ngừng 315", sla_hours=8, is_active=False))
    session.flush()
    r = _hoi(client, Actor(id="dp-315", roles=frozenset({"classifier"})))
    assert r.status_code == 200, r.text
    nhan = r.json()["labels"]
    assert nhan["departments"][phong_ban] == session.get(Department, phong_ban).label
    loai = session.scalars(select(RequestType)).all()
    assert loai and nhan["request_types"] == {t.code: t.label for t in loai}
    assert nhan["request_types"]["loai-cu-315"] == "Loại đã ngừng 315"


def test_kem_ma_hien_thi_cua_moi_ho_so_duoc_neu_ten(client, session, rule_set):
    # #315: hồ sơ trong nhánh lệch, chờ lâu nhất, biến thể đều có mã như trang hồ sơ (YC-năm-0000)
    hs = [create_case(session, title=f"Hồ sơ khai phá 315 số {i}", requester_id="ng-315") for i in range(3)]
    a, b, c = (h.id for h in hs)
    client.gia.ket_qua = {
        "deviations": [{"kind": "rework", "cases": [a]}],
        "states": [{"code": "x", "longest_waits": [{"case": b, "seconds": 9, "visits": 1, "current": True}]}],
        "variants": [{"sequence": ["x"], "cases": [a, c]}],
    }
    r = _hoi(client, Actor(id="dp-315", roles=frozenset({"classifier"})))
    assert r.status_code == 200, r.text
    assert r.json()["case_codes"] == {str(h.id): f"YC-{h.created_at.year}-{h.id:04d}" for h in hs}


def test_ket_qua_khong_neu_ho_so_nao_thi_ma_hien_thi_rong(client):
    r = _hoi(client, Actor(id="dp-315", roles=frozenset({"classifier"})))
    assert r.json()["case_codes"] == {}


def test_dich_vu_khai_pha_tat_thi_503(client):
    client.gia.hong = True
    r = _hoi(client, Actor(id="dp-314", roles=frozenset({"classifier"})))
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "mining-unavailable"


# ---------------------------------------------------------------------------
# Client HTTP thật
# ---------------------------------------------------------------------------


@pytest.fixture
def may_chu_gia(monkeypatch):
    """Máy chủ HTTP nhỏ đóng vai dịch vụ khai phá: ghi lại yêu cầu, trả một kết quả cố định."""
    nhan: list[tuple[str, dict]] = []

    class XuLy(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            do_dai = int(self.headers["Content-Length"])
            nhan.append((self.path, json.loads(self.rfile.read(do_dai))))
            than = json.dumps({"engine": "pm4py", "cases_count": 3}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(than)))
            self.end_headers()
            self.wfile.write(than)

        def log_message(self, *a):  # im lặng trong bài kiểm thử
            pass

    may_chu = HTTPServer(("127.0.0.1", 0), XuLy)
    luong = threading.Thread(target=may_chu.serve_forever, daemon=True)
    luong.start()
    monkeypatch.setattr(get_settings(), "mining_url", f"http://127.0.0.1:{may_chu.server_port}/")
    yield nhan
    may_chu.shutdown()


def test_client_gui_dung_khoang_va_pham_vi(may_chu_gia):
    kq = KhaiPhaClient().khai_pha(dt.date(2026, 10, 1), dt.date(2026, 10, 31), ["it"])
    assert kq == {"engine": "pm4py", "cases_count": 3}
    assert may_chu_gia == [("/khai-pha", {"from": "2026-10-01", "to": "2026-10-31", "departments": ["it"]})]


def test_client_bao_khong_phan_hoi_khi_dich_vu_tat(monkeypatch):
    # Cổng 9 (discard) trên máy cục bộ không có ai nghe: kết nối bị từ chối ngay
    monkeypatch.setattr(get_settings(), "mining_url", "http://127.0.0.1:9")
    monkeypatch.setattr(get_settings(), "mining_timeout_seconds", 2.0)
    with pytest.raises(KhaiPhaKhongPhanHoi):
        KhaiPhaClient().khai_pha(dt.date(2026, 10, 1), dt.date(2026, 10, 31), None)
