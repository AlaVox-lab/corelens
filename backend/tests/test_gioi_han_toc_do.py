# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử giới hạn tốc độ (#243).
#
# Bộ đếm nằm trong PostgreSQL, cửa sổ cố định. Cần kiểm: dưới ngưỡng thì qua, vượt thì 429 kèm
# `Retry-After` và mã `rate-limited`, sang cửa sổ mới thì qua lại, hai người dùng đếm riêng, đổi cấu
# hình thì ngưỡng đổi, và — quan trọng nhất với một biện pháp chống lạm dụng — yêu cầu bị TỪ CHỐI
# cũng được đếm, kể cả khi điểm cuối hoàn tác giao dịch của nó.

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app import rate_limit
from app.auth.dependencies import current_actor
from app.config import Settings
from app.db import get_session
from app.main import app
from app.models.van_hanh import RateLimitHit
from app.workflow.context import Actor
from app.workflow.engine import create_case

AN = Actor(id="gh-an-243", name="An thử giới hạn", roles=frozenset({"requester"}))
BINH = Actor(id="gh-binh-243", name="Bình thử giới hạn", roles=frozenset({"requester"}))


@pytest.fixture
def goi(session):
    """Hàm gọi API với tư cách một người, dùng chung phiên của bài (hoàn tác ở cuối)."""
    nguoi_goi: list[Actor] = [AN]
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: nguoi_goi[0]
    with TestClient(app) as may_khach:

        def _goi(actor: Actor, duong: str, **kieu):
            nguoi_goi[0] = actor
            return may_khach.post(duong, **kieu)

        yield _goi
    app.dependency_overrides.clear()


def _dat_gioi_han(monkeypatch, **doi):
    """Thay cấu hình mà `rate_limit` đọc — giống cách bài kiểm thử tệp đính kèm đổi giới hạn."""
    monkeypatch.setattr(rate_limit, "get_settings", lambda: Settings(**doi))


def _tao_ho_so(goi, actor=AN, tieu_de="Hồ sơ thử giới hạn tốc độ"):
    return goi(actor, "/requests", json={"title": tieu_de})


# ---------------------------------------------------------------------------
# Qua và vượt ngưỡng
# ---------------------------------------------------------------------------


def test_duoi_nguong_qua_het(goi, rule_set, monkeypatch):
    _dat_gioi_han(monkeypatch, rate_limit_create_case_max=3)
    for _ in range(3):
        assert _tao_ho_so(goi).status_code == 201


def test_vuot_nguong_tra_429_kem_thoi_gian_cho_va_cau_tieng_viet(goi, rule_set, monkeypatch):
    _dat_gioi_han(
        monkeypatch, rate_limit_create_case_max=2, rate_limit_create_case_window_seconds=60
    )
    assert _tao_ho_so(goi).status_code == 201
    assert _tao_ho_so(goi).status_code == 201

    bi_chan = _tao_ho_so(goi)
    assert bi_chan.status_code == 429
    cho = int(bi_chan.headers["Retry-After"])
    assert 1 <= cho <= 60
    chi_tiet = bi_chan.json()["detail"]
    assert chi_tiet["code"] == "rate-limited"
    # Câu tiếng Việt nói được việc gì quá nhanh và phải chờ bao lâu
    assert "gửi yêu cầu" in chi_tiet["message"]
    assert f"{cho} giây" in chi_tiet["message"]


def test_yeu_cau_bi_chan_khong_tao_ho_so(goi, session, rule_set, monkeypatch):
    _dat_gioi_han(monkeypatch, rate_limit_create_case_max=1)
    assert _tao_ho_so(goi, tieu_de="Hồ sơ đầu tiên").status_code == 201
    truoc = session.execute(text("SELECT count(*) FROM requests")).scalar_one()
    assert _tao_ho_so(goi, tieu_de="Hồ sơ bị chặn").status_code == 429
    assert session.execute(text("SELECT count(*) FROM requests")).scalar_one() == truoc


def test_chua_dang_nhap_nhan_401_chu_khong_cham_bo_dem(session, rule_set, monkeypatch):
    """Phụ thuộc đòi người gọi trước: người lạ không tiêu hao được hạn mức của ai."""
    _dat_gioi_han(monkeypatch, rate_limit_create_case_max=1)
    truoc = session.scalar(select(func.count()).select_from(RateLimitHit))
    app.dependency_overrides[get_session] = lambda: session
    try:
        with TestClient(app) as may_khach:
            assert may_khach.post("/requests", json={"title": "Không token"}).status_code == 401
    finally:
        app.dependency_overrides.clear()
    assert session.scalar(select(func.count()).select_from(RateLimitHit)) == truoc


# ---------------------------------------------------------------------------
# Hai người, hai giới hạn
# ---------------------------------------------------------------------------


def test_hai_nguoi_dem_rieng(goi, rule_set, monkeypatch):
    _dat_gioi_han(monkeypatch, rate_limit_create_case_max=1)
    assert _tao_ho_so(goi, AN).status_code == 201
    assert _tao_ho_so(goi, AN).status_code == 429
    # Bình chưa gọi lần nào nên còn nguyên hạn mức, dù An đã hết
    assert _tao_ho_so(goi, BINH).status_code == 201
    assert _tao_ho_so(goi, BINH).status_code == 429


def test_cac_gioi_han_khac_ten_dem_rieng(session):
    """Tạo hồ sơ nhiều không ăn vào hạn mức gửi lời nhắn của cùng một người."""
    for _ in range(5):
        rate_limit.ghi_nhan_luot_goi(session, "create-case", AN.id, 60)
    so_luot, _ = rate_limit.ghi_nhan_luot_goi(session, "send-message", AN.id, 60)
    assert so_luot == 1


# ---------------------------------------------------------------------------
# Cửa sổ thời gian
# ---------------------------------------------------------------------------


def test_sang_cua_so_moi_dem_lai_tu_dau(session):
    # Mốc giữa một cửa sổ 60 giây: 12:00:10, và 61 giây sau thì đã sang cửa sổ kế
    luc = dt.datetime(2030, 1, 1, 12, 0, 10, tzinfo=dt.UTC)
    ket_qua = [
        rate_limit.ghi_nhan_luot_goi(session, "create-case", AN.id, 60, luc=luc) for _ in range(3)
    ]
    assert [so_luot for so_luot, _ in ket_qua] == [1, 2, 3]
    # Còn 50 giây tới 12:01:00
    assert ket_qua[0][1] == 50

    sang = rate_limit.ghi_nhan_luot_goi(
        session, "create-case", AN.id, 60, luc=luc + dt.timedelta(seconds=61)
    )
    assert sang[0] == 1


def test_qua_cua_so_moi_thi_qua_lai_qua_api(goi, session, rule_set, monkeypatch):
    """Cùng cơ chế nhưng qua điểm cuối: đẩy các dòng đếm về quá khứ thì người dùng gọi lại được."""
    _dat_gioi_han(
        monkeypatch, rate_limit_create_case_max=1, rate_limit_create_case_window_seconds=60
    )
    assert _tao_ho_so(goi).status_code == 201
    assert _tao_ho_so(goi).status_code == 429

    session.execute(
        text("UPDATE rate_limit_hits SET window_start = window_start - interval '1 hour'")
    )
    assert _tao_ho_so(goi).status_code == 201


def test_don_dong_cu_chi_xoa_cua_so_da_qua(session):
    ten = "create-case"
    rate_limit.ghi_nhan_luot_goi(session, ten, "con-hieu-luc", 60)
    rate_limit.ghi_nhan_luot_goi(
        session, ten, "da-qua", 60, luc=dt.datetime(2020, 1, 1, tzinfo=dt.UTC)
    )
    assert rate_limit.don_dong_cu(session) >= 1
    con_lai = set(session.scalars(select(RateLimitHit.key)))
    assert f"{ten}:da-qua" not in con_lai
    assert f"{ten}:con-hieu-luc" in con_lai


# ---------------------------------------------------------------------------
# Cấu hình
# ---------------------------------------------------------------------------


def test_doi_cau_hinh_thi_nguong_doi(goi, rule_set, monkeypatch):
    _dat_gioi_han(monkeypatch, rate_limit_create_case_max=1)
    assert _tao_ho_so(goi).status_code == 201
    assert _tao_ho_so(goi).status_code == 429

    # Nâng ngưỡng: cùng bộ đếm, cùng người, lần sau qua — ngưỡng đọc ở mỗi lần gọi, không nhớ
    _dat_gioi_han(monkeypatch, rate_limit_create_case_max=10)
    assert _tao_ho_so(goi).status_code == 201


def test_so_lan_toi_da_bang_khong_la_tat_gioi_han(goi, session, rule_set, monkeypatch):
    _dat_gioi_han(monkeypatch, rate_limit_create_case_max=0)
    truoc = session.scalar(select(func.count()).select_from(RateLimitHit))
    for _ in range(5):
        assert _tao_ho_so(goi).status_code == 201
    assert session.scalar(select(func.count()).select_from(RateLimitHit)) == truoc


def test_cau_hinh_mac_dinh_doc_tu_bien_moi_truong(monkeypatch):
    monkeypatch.setenv("DXLAB_RATE_LIMIT_UPLOAD_MAX", "7")
    monkeypatch.setenv("DXLAB_RATE_LIMIT_UPLOAD_WINDOW_SECONDS", "15")
    monkeypatch.setattr(rate_limit, "get_settings", lambda: Settings())
    gh = rate_limit.gioi_han("upload-attachment")
    assert (gh.toi_da, gh.cua_so_giay) == (7, 15)


# ---------------------------------------------------------------------------
# Yêu cầu bị từ chối vẫn được đếm
# ---------------------------------------------------------------------------


def test_yeu_cau_bi_tu_choi_va_hoan_tac_van_duoc_dem(goi, session, rule_set, monkeypatch):
    """Gửi lời nhắn loại không tồn tại: điểm cuối `rollback()` rồi báo lỗi. Nếu bộ đếm nằm chung
    giao dịch đó thì vòng lặp gửi sai mãi không bao giờ chạm giới hạn."""
    _dat_gioi_han(monkeypatch, rate_limit_message_max=2)
    ho_so = create_case(session, title="Hồ sơ nhận lời nhắn", requester_id=AN.id)
    session.commit()

    duong = f"/requests/{ho_so.id}/messages"
    sai = {"json": {"kind": "loai-khong-ton-tai", "body": "x"}}
    assert goi(AN, duong, **sai).status_code == 422
    assert goi(AN, duong, **sai).status_code == 422
    bi_chan = goi(AN, duong, **sai)
    assert bi_chan.status_code == 429
    assert "gửi lời nhắn" in bi_chan.json()["detail"]["message"]


def test_tai_tep_len_co_gioi_han_rieng(goi, rule_set, monkeypatch):
    """Dùng hồ sơ không tồn tại (404) để không đụng kho tệp: bộ đếm chạy trước điểm cuối."""
    _dat_gioi_han(monkeypatch, rate_limit_upload_max=1)
    duong = "/requests/999999999/attachments"
    tep = {"files": ("ghi-chu.txt", b"xin chao", "text/plain")}
    assert goi(AN, duong, files=tep).status_code == 404
    bi_chan = goi(AN, duong, files=tep)
    assert bi_chan.status_code == 429
    assert "tải tệp lên" in bi_chan.json()["detail"]["message"]


def test_ca_ba_diem_cuoi_loi_nhan_deu_co_gioi_han():
    """Lời nhắn có ba cửa (người gửi, điều phối, phòng ban); thiếu một cửa là chừa một lối vòng."""
    # `app.routes` của FastAPI mới gói mỗi router đã gắn vào một đối tượng riêng, nên đọc thẳng từ
    # ba router nguồn
    from app.workflow import coordination, department
    from app.workflow import routes as nguoi_gui

    cac_cua = [
        r
        for router in (nguoi_gui.router, coordination.router, department.router)
        for r in router.routes
        if getattr(r, "path", "").endswith("/messages") and "POST" in getattr(r, "methods", ())
    ]
    assert len(cac_cua) == 3
    for tuyen in cac_cua:
        ten_ham = [d.call.__qualname__ for d in tuyen.dependant.dependencies]
        assert "gioi_han_toc_do.<locals>.kiem_tra" in ten_ham, tuyen.path
