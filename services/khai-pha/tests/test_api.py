# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Điểm vào HTTP của dịch vụ khai phá (app/main.py): hợp đồng khóa JSON mà dịch vụ ứng dụng dựa vào
# (docs/ARCHITECTURE.md mục 6.4) và việc từ chối khoảng ngày sai. Bài dùng dữ liệu thật của cụm qua
# đúng đường kết nối của dịch vụ, nên chỉ kiểm HÌNH DẠNG kết quả, không kiểm số tuyệt đối.

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import main

KHOA_HOP_DONG = {
    "range", "departments", "engine", "cases_count", "states", "edges", "designed_main_flow",
    "deviations", "bottlenecks", "variants", "other_variants_cases",
}
KHOANG_HOP_LE = {"from": "2026-08-01", "to": "2026-11-09", "departments": None}


@pytest.fixture
def khach(mui_gio):
    # `mui_gio` kéo theo bài bị bỏ qua khi không có PostgreSQL của cụm
    return TestClient(main.app)


@pytest.fixture(params=["pm4py", "noi_bo"])
def khach_theo_bo_may(request, khach, monkeypatch):
    from app.bo_may import chon_bo_may

    try:
        monkeypatch.setattr(main, "BO_MAY", chon_bo_may(request.param))
    except ImportError as loi:
        pytest.skip(f"Bộ máy {request.param} không nạp được: {loi}")
    return khach, request.param


def test_health_tra_200_dung_ba_khoa(khach):
    tra_loi = khach.get("/health")
    assert tra_loi.status_code == 200
    than = tra_loi.json()
    assert set(than) == {"service", "status", "engine"}
    assert than["status"] == "ok"
    assert than["service"] == "dx-os-lab-khai-pha"
    assert than["engine"] == main.BO_MAY.ten


def test_health_bao_dung_bo_may_dang_dung(khach_theo_bo_may):
    khach, ten = khach_theo_bo_may
    assert khach.get("/health").json()["engine"] == ten


def test_khoang_nguoc_bi_tu_choi_422(khach):
    tra_loi = khach.post("/khai-pha", json={"from": "2026-11-09", "to": "2026-08-01", "departments": None})
    assert tra_loi.status_code == 422


def test_khoang_qua_dai_bi_tu_choi_422(khach):
    tra_loi = khach.post("/khai-pha", json={"from": "2025-01-01", "to": "2026-11-09", "departments": None})
    assert tra_loi.status_code == 422


@pytest.mark.parametrize(
    "than",
    [
        {},
        {"from": "2026-08-01"},
        {"from": "khong-phai-ngay", "to": "2026-11-09"},
        {"from": "2026-08-01", "to": "2026-11-09", "departments": "A"},
    ],
)
def test_yeu_cau_thieu_hoac_sai_kieu_bi_tu_choi_422(khach, than):
    assert khach.post("/khai-pha", json=than).status_code == 422


def test_khoang_mot_ngay_hop_le(khach):
    tra_loi = khach.post("/khai-pha", json={"from": "2026-11-09", "to": "2026-11-09"})
    assert tra_loi.status_code == 200


def test_khoang_hop_le_tra_du_khoa_hop_dong(khach_theo_bo_may):
    khach, ten = khach_theo_bo_may
    tra_loi = khach.post("/khai-pha", json=KHOANG_HOP_LE)
    assert tra_loi.status_code == 200
    than = tra_loi.json()
    assert KHOA_HOP_DONG <= set(than)
    assert than["engine"] == ten
    assert than["range"] == {"from": "2026-08-01", "to": "2026-11-09"}
    assert than["departments"] is None
    assert isinstance(than["cases_count"], int) and than["cases_count"] >= 0
    assert [d["kind"] for d in than["deviations"]] == [
        "rework", "escalation", "wait_expiry", "reopen", "multiple_routing",
    ]
    assert set(than["bottlenecks"]) >= {"overall_median_wait_seconds", "factor", "threshold_seconds", "ranking"}
    assert isinstance(than["other_variants_cases"], int)


def test_pham_vi_phong_duoc_lap_lai_trong_ket_qua(khach):
    tra_loi = khach.post("/khai-pha", json={**KHOANG_HOP_LE, "departments": ["khong-co-phong-nay"]})
    assert tra_loi.status_code == 200
    than = tra_loi.json()
    assert than["departments"] == ["khong-co-phong-nay"]
    assert than["cases_count"] == 0 and than["edges"] == [] and than["variants"] == []


def test_hai_bo_may_tra_cung_ket_qua_qua_http(khach, monkeypatch):
    from app.bo_may import chon_bo_may

    ket_qua = {}
    for ten in ("pm4py", "noi_bo"):
        try:
            monkeypatch.setattr(main, "BO_MAY", chon_bo_may(ten))
        except ImportError as loi:
            pytest.skip(f"Bộ máy {ten} không nạp được: {loi}")
        than = khach.post("/khai-pha", json=KHOANG_HOP_LE).json()
        than.pop("engine")
        ket_qua[ten] = json.dumps(than, sort_keys=True, ensure_ascii=False)
    assert ket_qua["pm4py"] == ket_qua["noi_bo"]
