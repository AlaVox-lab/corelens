# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử khóa và nhịp của bộ quét nền (#253), và điểm kiểm tra sức khỏe (#243).
#
# Ba điều cần chứng minh:
# - Hai bản dịch vụ cùng quét một cơ sở dữ liệu thì mỗi lượt chỉ một bản chạy — dùng hai phiên trên
#   hai kết nối thật, vì khóa tư vấn là thứ của PostgreSQL, giả lập không chứng minh được gì.
# - Lượt quét hỏng thì tín hiệu sức khỏe xấu đi, lượt sau thành công thì tốt lại.
# - `/health` công khai không lộ chi tiết lỗi; chi tiết chỉ quản trị viên đọc được ở `/system/health`.
#
# Bài nào đụng `/health` đều thay danh sách bộ quét bằng tên riêng của bài: bộ quét thật của cụm thử
# đang chạy nền, có thể đang giữ khóa hay vừa ghi nhịp đúng lúc bài chạy.

from __future__ import annotations

import logging
import time
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app import main as main_mod
from app.auth.dependencies import current_actor
from app.config import BOI_SO_CHU_KY_QUA_LAU, Settings
from app.db import get_session
from app.main import app
from app.workflow.context import Actor
from app.workflow.escalation import BO_QUET, BoQuet
from app.workflow.nhip_quet import chay_luot_quet, khoa_cua

QUAN_TRI = Actor(id="qt-253", roles=frozenset({"administrator"}))
NGUOI_GUI = Actor(id="gui-253", roles=frozenset({"requester"}))
DIEU_PHOI = Actor(id="dp-253", roles=frozenset({"classifier"}))

# Hai bộ quét riêng của bài, không trùng tên với bộ quét thật
BO_THU = (
    BoQuet("kiem-thu-253-a", "Bộ quét thử A", lambda p: []),
    BoQuet("kiem-thu-253-b", "Bộ quét thử B", lambda p: []),
)


@contextmanager
def _may_khach(phien, actor: Actor | None = None):
    app.dependency_overrides[get_session] = lambda: phien
    if actor is not None:
        app.dependency_overrides[current_actor] = lambda: actor
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def bo_quet_thu(monkeypatch, session, rule_set):
    """Danh sách bộ quét của `/health` thành hai bộ thử, cấu hình mặc định, tiến trình mới khởi động.

    Bộ lưu trữ lạnh (#378) mặc định bật nên có dòng nhịp — tắt qua biến môi trường để mọi `Settings()` dựng
    trong bài (kể cả sau fixture) chỉ thấy hai bộ thử; bộ đó có bài riêng ở test_luu_tru_lanh.py."""
    monkeypatch.setenv("DXLAB_ARCHIVE_ENABLED", "false")
    monkeypatch.setattr(main_mod, "BO_QUET", BO_THU)
    monkeypatch.setattr(main_mod, "settings", Settings(sla_scan_interval_seconds=60))
    monkeypatch.setattr(main_mod, "THOI_DIEM_KHOI_DONG", time.monotonic())
    session.execute(text("DELETE FROM scanner_heartbeats WHERE name LIKE 'kiem-thu-253-%'"))
    session.commit()


def _da_chay_lau(monkeypatch, giay: float = 100_000):
    """Coi như tiến trình đã chạy từ lâu: bộ quét chưa có lượt thành công nào là đã chết."""
    monkeypatch.setattr(main_mod, "THOI_DIEM_KHOI_DONG", time.monotonic() - giay)


def _ghi_nhip(session, ten: str, *, thanh_cong_truoc_giay: float | None, loi_lien_tiep: int = 0):
    session.execute(
        text(
            """
            INSERT INTO scanner_heartbeats (name, last_success_at, consecutive_errors)
            VALUES (:ten, CASE WHEN CAST(:truoc AS float) IS NULL THEN NULL
                          ELSE clock_timestamp() - make_interval(secs => CAST(:truoc AS float)) END,
                    :loi)
            """
        ),
        {"ten": ten, "truoc": thanh_cong_truoc_giay, "loi": loi_lien_tiep},
    )
    session.commit()


# ---------------------------------------------------------------------------
# Khóa: hai bản cùng quét
# ---------------------------------------------------------------------------


@pytest.fixture
def hai_phien(db_engine):
    """Hai phiên trên hai kết nối riêng của cùng cơ sở dữ liệu — hai bản dịch vụ thu nhỏ.

    Mỗi phiên nằm trong một giao dịch ngoài được hoàn tác ở cuối bài, nên không có gì thoát ra cơ sở
    dữ liệu thật; khóa tư vấn mức giao dịch cũng nhả cùng lúc đó.
    """
    ket_noi = [db_engine.connect(), db_engine.connect()]
    giao_dich = [k.begin() for k in ket_noi]
    phien = [Session(bind=k, join_transaction_mode="create_savepoint") for k in ket_noi]
    try:
        yield phien
    finally:
        for p in phien:
            p.close()
        for g in giao_dich:
            g.rollback()
        for k in ket_noi:
            k.close()


def test_khoa_cua_on_dinh_va_khac_nhau_theo_ten():
    assert khoa_cua("sla-escalation") == khoa_cua("sla-escalation")
    assert khoa_cua("sla-escalation") != khoa_cua("wait-expiry")
    for so in khoa_cua("bat-ky"):
        assert -(2**31) <= so < 2**31  # vừa int4 của PostgreSQL


def test_hai_ban_cung_quet_thi_chi_mot_ban_chay(hai_phien):
    ban_a, ban_b = hai_phien
    ten = "kiem-thu-253-khoa"
    da_goi: list[str] = []

    def quet_a(phien):
        da_goi.append("a")
        # A đang quét giữa chừng, giữ khóa. B thử ngay lúc này.
        luot_b = chay_luot_quet(ban_b, ten, lambda p: da_goi.append("b") or ["b"])
        assert luot_b.da_chay is False
        return ["a"]

    luot_a = chay_luot_quet(ban_a, ten, quet_a)

    assert luot_a.da_chay is True and luot_a.ket_qua == ["a"]
    assert da_goi == ["a"], "bản B không được chạy hàm quét khi bản A đang giữ khóa"
    # B bỏ lượt chứ không ghi gì: không phải lỗi, không để lại dòng nhịp
    assert (
        ban_b.execute(
            text("SELECT count(*) FROM scanner_heartbeats WHERE name = :t"), {"t": ten}
        ).scalar_one()
        == 0
    )


def test_ban_a_xong_va_nha_khoa_thi_ban_b_quet_duoc(db_engine):
    """Khóa gắn với giao dịch: A kết thúc giao dịch thì B giành được khóa ở lượt sau. Hai kết nối
    thật không bọc giao dịch ngoài, nên `commit` của `chay_luot_quet` nhả khóa như ngoài đời — các
    dòng nhịp ghi thật xuống cơ sở dữ liệu, dọn lại ở cuối bài."""
    ten = "kiem-thu-253-nha-khoa"
    with Session(db_engine) as ban_a, Session(db_engine) as ban_b:
        try:
            tuan_tu: list[str] = []
            assert chay_luot_quet(ban_a, ten, lambda p: tuan_tu.append("a")).da_chay is True
            assert chay_luot_quet(ban_b, ten, lambda p: tuan_tu.append("b")).da_chay is True
            assert tuan_tu == ["a", "b"]
        finally:
            ban_a.rollback()
            ban_a.execute(text("DELETE FROM scanner_heartbeats WHERE name = :t"), {"t": ten})
            ban_a.commit()


def test_hai_ban_chay_dong_thoi_that_chi_mot_ban_quet(db_engine):
    """Cùng thử bằng hai luồng thật tranh nhau: hàm quét giữ khóa đủ lâu để luồng kia kịp tới."""
    import threading

    ten = "kiem-thu-253-song-song"
    dang_quet = threading.Event()
    cho_phep_xong = threading.Event()
    da_chay: list[str] = []
    ket_qua: dict[str, bool] = {}

    def quet_cham(phien):
        da_chay.append("cham")
        dang_quet.set()
        assert cho_phep_xong.wait(timeout=10)

    def luong_cham():
        with Session(db_engine) as phien:
            ket_qua["cham"] = chay_luot_quet(phien, ten, quet_cham).da_chay

    luong = threading.Thread(target=luong_cham)
    luong.start()
    try:
        assert dang_quet.wait(timeout=10)
        with Session(db_engine) as phien_hai:
            ket_qua["toi_sau"] = chay_luot_quet(
                phien_hai, ten, lambda p: da_chay.append("toi_sau")
            ).da_chay
    finally:
        cho_phep_xong.set()
        luong.join(timeout=10)
        with Session(db_engine) as don:
            don.execute(text("DELETE FROM scanner_heartbeats WHERE name = :t"), {"t": ten})
            don.commit()

    assert ket_qua == {"cham": True, "toi_sau": False}
    assert da_chay == ["cham"]


# ---------------------------------------------------------------------------
# Nhịp: thành công, hỏng, hồi phục
# ---------------------------------------------------------------------------


def _nhip(session, ten):
    return session.execute(
        text(
            "SELECT consecutive_errors, last_success_at, last_error_at, last_error,"
            " runner_host, runner_pid FROM scanner_heartbeats WHERE name = :t"
        ),
        {"t": ten},
    ).one()


def test_luot_thanh_cong_ghi_nhip_va_ban_chay(session):
    ten = "kiem-thu-253-nhip"
    chay_luot_quet(session, ten, lambda p: [1, 2])
    nhip = _nhip(session, ten)
    assert nhip.consecutive_errors == 0
    assert nhip.last_success_at is not None
    assert nhip.last_error_at is None
    assert nhip.runner_host and nhip.runner_pid  # biết bản nào đã chạy


def test_luot_hong_ghi_loi_o_giao_dich_rieng_khong_bi_hoan_tac_theo(session):
    """Hàm quét ghi dở một dòng rồi nổ. Phần ghi dở phải mất; dấu vết lỗi phải còn."""
    ten = "kiem-thu-253-hong"
    session.commit()

    def quet_hong(phien):
        phien.execute(
            text("INSERT INTO rate_limit_hits (key, window_start, hits) VALUES ('ghi-do-253', now(), 1)")
        )
        raise RuntimeError("lỗi cố ý của bài kiểm thử")

    with pytest.raises(RuntimeError, match="lỗi cố ý"):
        chay_luot_quet(session, ten, quet_hong)

    assert (
        session.execute(
            text("SELECT count(*) FROM rate_limit_hits WHERE key = 'ghi-do-253'")
        ).scalar_one()
        == 0
    ), "phần quét dở dang phải được hoàn tác"
    nhip = _nhip(session, ten)
    assert nhip.consecutive_errors == 1
    assert "lỗi cố ý của bài kiểm thử" in nhip.last_error
    assert nhip.last_error_at is not None


def test_loi_lien_tiep_cong_don_va_mot_luot_thanh_cong_dat_ve_khong(session):
    ten = "kiem-thu-253-lien-tiep"
    session.commit()

    def hong(phien):
        raise RuntimeError("hỏng")

    for lan in (1, 2, 3):
        with pytest.raises(RuntimeError):
            chay_luot_quet(session, ten, hong)
        assert _nhip(session, ten).consecutive_errors == lan

    chay_luot_quet(session, ten, lambda p: [])
    nhip = _nhip(session, ten)
    assert nhip.consecutive_errors == 0
    assert nhip.last_success_at is not None
    # Dấu vết lần lỗi gần nhất vẫn còn để quản trị viên xem lại
    assert nhip.last_error_at is not None


def test_tin_hieu_suc_khoe_xau_di_khi_quet_hong_va_tot_lai_khi_quet_duoc(
    session, bo_quet_thu, monkeypatch
):
    """Kịch bản của định nghĩa hoàn thành #253, đi qua đúng `/health` và `/system/health`."""
    ten = BO_THU[0].ten

    def hong(phien):
        raise RuntimeError("lượt quét hỏng cố ý")

    with _may_khach(session, QUAN_TRI) as c:
        assert c.get("/health").json()["status"] == "ok"

        for _ in range(3):  # ngưỡng mặc định: ba lượt hỏng liên tiếp
            with pytest.raises(RuntimeError):
                chay_luot_quet(session, ten, hong)

        xau = c.get("/health")
        assert xau.status_code == 200, "bộ quét hỏng không được làm container healthcheck rớt"
        assert xau.json()["status"] == "degraded"
        chi_tiet = c.get("/system/health").json()
        a = next(b for b in chi_tiet["scanners"] if b["name"] == ten)
        assert (a["status"], a["consecutive_errors"]) == ("failing", 3)
        assert "lượt quét hỏng cố ý" in a["last_error"]

        chay_luot_quet(session, ten, lambda p: [])

        assert c.get("/health").json()["status"] == "ok"
        a = next(b for b in c.get("/system/health").json()["scanners"] if b["name"] == ten)
        assert (a["status"], a["consecutive_errors"]) == ("ok", 0)


def test_chua_toi_nguong_loi_thi_van_tot(session, bo_quet_thu):
    ten = BO_THU[0].ten

    def hong(phien):
        raise RuntimeError("hỏng")

    with _may_khach(session) as c:
        for _ in range(2):  # ngưỡng là ba
            with pytest.raises(RuntimeError):
                chay_luot_quet(session, ten, hong)
        assert c.get("/health").json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Quá lâu không quét thành công
# ---------------------------------------------------------------------------


def test_bo_quet_im_qua_nguong_thi_degraded_van_tra_200(session, bo_quet_thu, monkeypatch):
    _da_chay_lau(monkeypatch)
    nguong = BOI_SO_CHU_KY_QUA_LAU * 60
    _ghi_nhip(session, BO_THU[0].ten, thanh_cong_truoc_giay=nguong + 600)
    _ghi_nhip(session, BO_THU[1].ten, thanh_cong_truoc_giay=5)

    with _may_khach(session, QUAN_TRI) as c:
        tra = c.get("/health")
        assert tra.status_code == 200
        assert tra.json()["status"] == "degraded"
        trang_thai = {b["name"]: b["status"] for b in c.get("/system/health").json()["scanners"]}
        assert trang_thai == {BO_THU[0].ten: "stale", BO_THU[1].ten: "ok"}


def test_quet_gan_day_thi_khoe(session, bo_quet_thu, monkeypatch):
    _da_chay_lau(monkeypatch)
    for bo in BO_THU:
        _ghi_nhip(session, bo.ten, thanh_cong_truoc_giay=10)
    with _may_khach(session) as c:
        assert c.get("/health").json()["status"] == "ok"


def test_nguong_qua_lau_doc_tu_cau_hinh(session, bo_quet_thu, monkeypatch):
    _da_chay_lau(monkeypatch)
    for bo in BO_THU:
        _ghi_nhip(session, bo.ten, thanh_cong_truoc_giay=3600)
    with _may_khach(session) as c:
        assert c.get("/health").json()["status"] == "degraded"
        # Nới ngưỡng lên 2 giờ: cùng dữ liệu, tín hiệu về tốt
        monkeypatch.setattr(
            main_mod, "settings", Settings(sla_scan_interval_seconds=60, sla_scan_stale_after_seconds=7200)
        )
        assert c.get("/health").json()["status"] == "ok"


def test_ngung_mac_dinh_la_boi_so_cua_chu_ky():
    assert Settings(sla_scan_interval_seconds=60).sla_scan_stale_threshold_seconds == (
        BOI_SO_CHU_KY_QUA_LAU * 60
    )
    assert Settings(sla_scan_interval_seconds=10).sla_scan_stale_threshold_seconds == (
        BOI_SO_CHU_KY_QUA_LAU * 10
    )
    assert Settings(sla_scan_stale_after_seconds=999).sla_scan_stale_threshold_seconds == 999


def test_chua_co_nhip_nao_thi_cho_den_khi_tien_trinh_chay_du_lau(session, bo_quet_thu, monkeypatch):
    """Vừa khởi động: bộ quét chưa kịp chạy lượt đầu, không phải đã chết. Chạy quá ngưỡng mà vẫn
    không một dòng nhịp thì mới là chết."""
    with _may_khach(session, QUAN_TRI) as c:
        assert c.get("/health").json()["status"] == "ok"
        trang_thai = {b["status"] for b in c.get("/system/health").json()["scanners"]}
        assert trang_thai == {"starting"}

        _da_chay_lau(monkeypatch)
        assert c.get("/health").json()["status"] == "degraded"


def test_khoi_dong_lai_sau_thoi_gian_dung_khong_bao_do_ngay(session, bo_quet_thu, monkeypatch):
    """Nhịp cũ hàng giờ nhưng tiến trình mới khởi động: chưa có cơ hội quét, không báo đỏ."""
    for bo in BO_THU:
        _ghi_nhip(session, bo.ten, thanh_cong_truoc_giay=7200)
    with _may_khach(session) as c:
        assert c.get("/health").json()["status"] == "ok"


def test_bo_quet_tat_bang_cau_hinh_khong_phai_su_co(session, bo_quet_thu, monkeypatch):
    _da_chay_lau(monkeypatch)
    monkeypatch.setattr(main_mod, "settings", Settings(sla_scan_enabled=False))
    with _may_khach(session, QUAN_TRI) as c:
        assert c.get("/health").json()["status"] == "ok"
        assert {b["status"] for b in c.get("/system/health").json()["scanners"]} == {"disabled"}


# ---------------------------------------------------------------------------
# /health công khai không lộ chi tiết
# ---------------------------------------------------------------------------

CHUOI_BI_MAT = (
    'connection to server at "db-noi-bo.example" (10.9.8.7), port 5432 failed: '
    'FATAL: password authentication failed for user "tai_khoan_bi_mat"'
)


class PhienHong:
    """Phiên mà mọi lệnh đều nổ lỗi kết nối — cơ sở dữ liệu chết."""

    def execute(self, *_args, **_kw):
        raise OperationalError("SELECT 1", {}, Exception(CHUOI_BI_MAT))

    def close(self):
        pass


def test_health_co_so_du_lieu_hong_tra_503_khong_lo_chi_tiet_ket_noi(caplog):
    app.dependency_overrides[get_session] = lambda: PhienHong()
    try:
        with caplog.at_level(logging.WARNING, logger="app.main"):
            with TestClient(app) as c:
                tra = c.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert tra.status_code == 503
    assert tra.json() == {"service": "dx-os-lab-backend", "status": "degraded"}
    for mau in ("db-noi-bo", "10.9.8.7", "tai_khoan_bi_mat", "password", "connection", "detail"):
        assert mau not in tra.text, f"/health công khai lộ '{mau}'"
    # Chi tiết có đi đâu đó: ghi vào nhật ký để người vận hành tra
    assert "tai_khoan_bi_mat" in caplog.text


def test_health_binh_thuong_chi_co_trang_thai_chung(session, bo_quet_thu):
    with _may_khach(session) as c:
        tra = c.get("/health")
    assert tra.status_code == 200
    assert tra.json() == {"service": "dx-os-lab-backend", "status": "ok"}


def test_chi_tiet_loi_chi_o_man_he_thong_cua_quan_tri_vien(caplog):
    """Quản trị viên được thấy câu lỗi ở `/system/health` — đó là chỗ duy nhất ngoài nhật ký."""
    app.dependency_overrides[get_session] = lambda: PhienHong()
    app.dependency_overrides[current_actor] = lambda: QUAN_TRI
    try:
        with TestClient(app) as c:
            tra = c.get("/system/health")
    finally:
        app.dependency_overrides.clear()
    assert tra.status_code == 200
    than = tra.json()
    assert than["status"] == "degraded"
    assert than["database"] == "unreachable"
    assert "tai_khoan_bi_mat" in than["detail"]


# ---------------------------------------------------------------------------
# /system/health: chỉ quản trị viên
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("nguoi", [NGUOI_GUI, DIEU_PHOI], ids=lambda a: a.id)
def test_system_health_nguoi_khac_nhan_403(session, nguoi):
    with _may_khach(session, nguoi) as c:
        tra = c.get("/system/health")
    assert tra.status_code == 403
    assert "scanners" not in tra.text and "version" not in tra.text


def test_system_health_chua_dang_nhap_nhan_401(session):
    with _may_khach(session) as c:
        assert c.get("/system/health").status_code == 401


def test_system_health_quan_tri_thay_du_chi_tiet(session, bo_quet_thu):
    _ghi_nhip(session, BO_THU[0].ten, thanh_cong_truoc_giay=3)
    with _may_khach(session, QUAN_TRI) as c:
        tra = c.get("/system/health")
    assert tra.status_code == 200
    than = tra.json()
    assert than["status"] == "ok" and than["database"] == "ok"
    assert than["version"] == main_mod.settings.app_version
    assert than["active_rule_set_states"] > 0
    assert {b["name"]: b["label"] for b in than["scanners"]} == {
        BO_THU[0].ten: "Bộ quét thử A",
        BO_THU[1].ten: "Bộ quét thử B",
    }
    cai_dat = than["scan_settings"]
    assert cai_dat["interval_seconds"] == 60
    assert cai_dat["stale_after_seconds"] == BOI_SO_CHU_KY_QUA_LAU * 60
    assert cai_dat["max_consecutive_errors"] == 3


def test_vong_nen_dang_ky_dung_hai_bo_quet_that():
    """Sổ đăng ký của `/health` và của vòng nền là cùng một: thêm bộ quét thì cả hai thấy."""
    assert [b.ten for b in BO_QUET] == ["sla-escalation", "wait-expiry"]
    assert len({khoa_cua(b.ten) for b in BO_QUET}) == len(BO_QUET)
