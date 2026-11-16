# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Lưu trữ lạnh ra kho đối tượng (#378): đúng số dòng, mã băm khớp, chạy lại không ghi đè, bộ quét chọn đúng
# tháng đã khép, quyền của API lõi, không tên người trong bản lưu (ADR-0009).
#
# Dữ liệu thử nằm ở năm 2001 — cũ hơn mọi dữ liệu thật của cụm thử, nên là tháng sớm nhất mà bộ quét thấy —
# và chỉ sống trong giao dịch của bài. Kho đối tượng thì không hoàn tác được: mỗi bài ghi dưới một tiền tố
# riêng rồi tự dọn.

from __future__ import annotations

import contextlib
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

import app.main as main_mod
from app.analytics import luu_tru_lanh as lt
from app.analytics.xuat_du_lieu import COT
from app.auth.dependencies import current_actor
from app.config import Settings, get_settings
from app.db import get_session
from app.main import app
from app.models.luu_tru import ColdArchive
from app.models.workflow_config import RequestType, State
from app.storage import objects
from app.workflow.context import Actor
from app.workflow.engine import create_case
from app.workflow.nhip_quet import chay_luot_quet
from tests.test_tep_dinh_kem import kho_that  # noqa: F401 — fixture dùng lại

QUAN_TRI = Actor(id="qt-378", roles=frozenset({"administrator"}))
DIEU_PHOI = Actor(id="dp-378", roles=frozenset({"classifier"}))

NHAN_NGUOI_GUI = "Chị Ẩn Danh Ba Bảy Tám"
NHAN_TAC_NHAN = "Anh Tên Thật Ba Bảy Tám"
TIEU_DE = "Máy chủ in phòng kế toán 378"
NGUOI_GUI = "nguoi-gui-378"
TAC_NHAN = "nhan-vien-378"


def _moc(chuoi: str) -> dt.datetime:
    return dt.datetime.fromisoformat(chuoi).replace(tzinfo=dt.UTC)


@pytest.fixture
def tien_to(monkeypatch, kho_that):  # noqa: F811
    """Tiền tố riêng của bài trong kho; dọn sạch khi xong."""
    goc = f"kiem-thu-378/{uuid.uuid4().hex}/"
    monkeypatch.setattr(get_settings(), "archive_prefix", goc)
    yield goc
    thung = get_settings().archive_bucket_name
    trang = objects._khach().list_objects_v2(Bucket=thung, Prefix=goc)
    for o in trang.get("Contents", []):
        objects._khach().delete_object(Bucket=thung, Key=o["Key"])


def _them_su_kien(session, ma: int, moc: str, tu: str, den: str) -> None:
    session.execute(
        text(
            "INSERT INTO event_log (case_id, activity, timestamp, actor, actor_label, from_state, to_state) "
            "VALUES (:ma, 'thu-378', :moc, :ai, :nhan, :tu, :den)"
        ),
        {"ma": ma, "moc": _moc(moc), "ai": TAC_NHAN, "nhan": NHAN_TAC_NHAN, "tu": tu, "den": den},
    )


@pytest.fixture
def du_lieu_2001(session, rule_set):
    """Hai hồ sơ gửi tháng 3/2001: hồ sơ một kết thúc ngày 20/3, hồ sơ hai kết thúc ngày 2/4.

    Tháng 3: 2 sự kiện mở đầu + 2 + 1 sự kiện = 5 dòng nhật ký, 1 hồ sơ kết thúc.
    Tháng 4: 1 dòng nhật ký, 1 hồ sơ kết thúc."""
    trang_thai = session.scalars(select(State).where(State.rule_set_id == rule_set.id)).all()
    dau = next(s.code for s in trang_thai if s.is_initial)
    cuoi = next(s.code for s in trang_thai if s.is_terminal)
    giua = next(s.code for s in trang_thai if not s.is_initial and not s.is_terminal)
    loai = session.scalars(select(RequestType.code).where(RequestType.is_active)).first()

    ma = []
    for gui, ket_thuc in (("2001-03-05T08:00:00", "2001-03-20T10:00:00"), ("2001-03-25T09:00:00", "2001-04-02T11:00:00")):
        h = create_case(
            session, title=TIEU_DE, description="Mô tả có tên Chị Ẩn Danh", requester_id=NGUOI_GUI,
            requester_label=NHAN_NGUOI_GUI, request_type_code=loai,
        )
        session.flush()
        session.execute(
            text("UPDATE requests SET created_at = :gui, current_state = :cuoi, assignee_id = :ai, "
                 "assignee_label = :nhan WHERE id = :ma"),
            {"gui": _moc(gui), "cuoi": cuoi, "ai": TAC_NHAN, "nhan": NHAN_TAC_NHAN, "ma": h.id},
        )
        ma.append((h.id, gui, ket_thuc))
    (m1, g1, k1), (m2, g2, k2) = ma
    _them_su_kien(session, m1, "2001-03-06T08:00:00", dau, giua)
    _them_su_kien(session, m1, k1, giua, cuoi)
    _them_su_kien(session, m2, "2001-03-26T08:00:00", dau, giua)
    _them_su_kien(session, m2, k2, giua, cuoi)
    session.commit()
    return m1, m2


def _tep(ban_ghi: ColdArchive, ten: str) -> bytes:
    return objects.doc_tep(ban_ghi.object_prefix + ten, ban_ghi.bucket)


def _dong_csv(noi_dung: bytes) -> tuple[list[str], list[dict]]:
    doc = csv.DictReader(io.StringIO(gzip.decompress(noi_dung).decode("utf-8")))
    return list(doc.fieldnames or []), list(doc)


# ---------------------------------------------------------------------------
# Kỳ
# ---------------------------------------------------------------------------


def test_ky_da_khep_va_khoang_thang():
    assert lt.ky_khep_cuoi(_moc("2026-11-16T09:00:00"), 1) == "2026-10"
    assert lt.ky_khep_cuoi(_moc("2026-01-01T00:00:00"), 1) == "2025-12"
    assert lt.ky_khep_cuoi(_moc("2026-11-16T09:00:00"), 3) == "2026-08"
    assert lt.khoang_cua("2001-12") == (_moc("2001-12-01T00:00:00"), _moc("2002-01-01T00:00:00"))
    with pytest.raises(ValueError):
        lt.khoang_cua("2001-13")


def test_nguong_thang_toi_thieu_mot():
    """Tháng đang chạy còn nhận sự kiện — cấu hình không cho niêm phong nó."""
    with pytest.raises(ValidationError):
        Settings(archive_min_age_months=0)


# ---------------------------------------------------------------------------
# Xuất một tháng
# ---------------------------------------------------------------------------


def test_xuat_dung_so_dong_va_ma_bam(session, du_lieu_2001, tien_to):
    m1, m2 = du_lieu_2001
    ban_ghi = lt.xuat_thang(session, "2001-03")
    assert (ban_ghi.event_rows, ban_ghi.case_rows) == (5, 1)
    assert ban_ghi.object_prefix == f"{tien_to}2001-03/"

    than_ban_ke = _tep(ban_ghi, lt.TEP_BAN_KE)
    assert hashlib.sha256(than_ban_ke).hexdigest() == ban_ghi.manifest_sha256
    ban_ke = json.loads(than_ban_ke)
    assert ban_ke == ban_ghi.manifest
    assert (ban_ke["period"], ban_ke["schema_version"], ban_ke["timezone"]) == ("2001-03", 1, "UTC")
    assert ban_ke["period_start"] == "2001-03-01T00:00:00+00:00"
    assert ban_ke["period_end"] == "2001-04-01T00:00:00+00:00"
    [quy_trinh] = ban_ke["processes"].values()
    assert quy_trinh == {"events": 5, "closed_cases": 1}

    for f in ban_ke["files"]:
        noi_dung = _tep(ban_ghi, f["name"])
        assert hashlib.sha256(noi_dung).hexdigest() == f["sha256"]
        assert len(noi_dung) == f["bytes"]
        cot, dong = _dong_csv(noi_dung)
        assert cot == f["columns"]
        assert len(dong) == f["rows"]

    _, nhat_ky = _dong_csv(_tep(ban_ghi, lt.TEP_NHAT_KY))
    assert {int(d["case_id"]) for d in nhat_ky} == {m1, m2}
    assert [d["activity"] for d in nhat_ky if int(d["case_id"]) == m1] == ["create-case", "thu-378", "thu-378"]
    assert all(d["timestamp"].startswith("2001-03") and d["timestamp"].endswith("+00:00") for d in nhat_ky)
    cot, ho_so = _dong_csv(_tep(ban_ghi, lt.TEP_HO_SO))
    assert tuple(cot) == lt.COT_HO_SO
    [h] = ho_so
    assert (int(h["case_id"]), h["closed_at"]) == (m1, "2001-03-20T10:00:00+00:00")
    assert (h["requester_id"], h["assignee_id"]) == (NGUOI_GUI, TAC_NHAN)


def test_nhat_ky_cung_cot_voi_du_lieu_xuat(session, du_lieu_2001, tien_to):
    """Tệp nhật ký đọc được bằng đúng công cụ đọc GET /core/v1/events."""
    ban_ghi = lt.xuat_thang(session, "2001-03")
    cot, _ = _dong_csv(_tep(ban_ghi, lt.TEP_NHAT_KY))
    assert tuple(cot) == COT


def test_ranh_gioi_thang_theo_moc_ket_thuc(session, du_lieu_2001, tien_to):
    _, m2 = du_lieu_2001
    ban_ghi = lt.xuat_thang(session, "2001-04")
    assert (ban_ghi.event_rows, ban_ghi.case_rows) == (1, 1)
    _, ho_so = _dong_csv(_tep(ban_ghi, lt.TEP_HO_SO))
    assert [int(h["case_id"]) for h in ho_so] == [m2]


def test_khong_ten_nguoi_khong_noi_dung_tu_do(session, du_lieu_2001, tien_to):
    """ADR-0009: bản lưu bất biến nên không mang nhãn tên nào — ẩn danh hóa về sau vẫn đủ. Người chỉ có mã."""
    ban_ghi = lt.xuat_thang(session, "2001-03")
    toan_bo = "".join(
        gzip.decompress(_tep(ban_ghi, f["name"])).decode("utf-8") for f in ban_ghi.manifest["files"]
    ) + _tep(ban_ghi, lt.TEP_BAN_KE).decode("utf-8")
    for chuoi in (NHAN_NGUOI_GUI, NHAN_TAC_NHAN, TIEU_DE, "Chị Ẩn Danh"):
        assert chuoi not in toan_bo
    assert NGUOI_GUI in toan_bo and TAC_NHAN in toan_bo


# ---------------------------------------------------------------------------
# Bất biến, chạy lại an toàn
# ---------------------------------------------------------------------------


def test_chay_lai_khong_ghi_de(session, du_lieu_2001, tien_to):
    dau = lt.xuat_thang(session, "2001-03")
    ban_ke_dau = _tep(dau, lt.TEP_BAN_KE)
    # Tầng nóng có thêm một dòng của tháng đã niêm phong (nạp bù dữ liệu cũ chẳng hạn)
    _them_su_kien(session, du_lieu_2001[0], "2001-03-21T08:00:00", "x", "y")
    lai = lt.xuat_thang(session, "2001-03")
    assert lai is dau and lai.event_rows == 5
    assert _tep(lai, lt.TEP_BAN_KE) == ban_ke_dau


def test_niem_phong_roi_hong_truoc_khi_ghi_so_thi_nhan_lai(session, du_lieu_2001, tien_to):
    """Lượt hỏng sau khi ghi kho, trước khi ghi sổ: lượt sau ghi sổ theo manifest trong kho, không xuất lại."""
    diem_luu = session.begin_nested()
    dau = lt.xuat_thang(session, "2001-03")
    sha_dau, ban_ke_dau = dau.manifest_sha256, _tep(dau, lt.TEP_BAN_KE)
    diem_luu.rollback()
    session.expire_all()
    assert session.get(ColdArchive, "2001-03") is None

    _them_su_kien(session, du_lieu_2001[0], "2001-03-21T08:00:00", "x", "y")
    lai = lt.xuat_thang(session, "2001-03")
    assert lai.event_rows == 5 and lai.manifest_sha256 == sha_dau
    assert _tep(lai, lt.TEP_BAN_KE) == ban_ke_dau


def test_so_chi_ghi_them(session, du_lieu_2001, tien_to):
    lt.xuat_thang(session, "2001-03")
    session.flush()
    for cau in ("UPDATE cold_archives SET event_rows = 0 WHERE period = '2001-03'",
                "DELETE FROM cold_archives WHERE period = '2001-03'"):
        with pytest.raises(DBAPIError, match="chỉ ghi thêm"), session.begin_nested():
            session.execute(text(cau))


# ---------------------------------------------------------------------------
# Bộ quét
# ---------------------------------------------------------------------------


def test_bo_quet_chon_thang_da_khep_cu_truoc(session, du_lieu_2001, tien_to, monkeypatch):
    monkeypatch.setattr(get_settings(), "archive_max_months_per_run", 2)
    assert lt.cac_ky_can_luu(session)[:2] == ["2001-03", "2001-04"]

    luot = chay_luot_quet(session, lt.TEN_BO_QUET_LUU_TRU, lt.quet_luu_tru)
    assert luot.da_chay and luot.ket_qua == ["2001-03", "2001-04"]
    # Lượt sau bỏ qua tháng đã có, đi tiếp
    assert lt.cac_ky_can_luu(session)[0] == "2001-05"
    nhip = session.execute(
        text("SELECT consecutive_errors FROM scanner_heartbeats WHERE name = :t"), {"t": lt.TEN_BO_QUET_LUU_TRU}
    ).scalar_one()
    assert nhip == 0


def test_khong_bao_gio_niem_phong_thang_dang_chay(session, du_lieu_2001):
    bay_gio = _moc("2001-04-15T00:00:00")
    assert lt.cac_ky_can_luu(session, bay_gio) == ["2001-03"]
    assert lt.cac_ky_can_luu(session, _moc("2001-03-31T23:59:59")) == []


# ---------------------------------------------------------------------------
# API của lõi và điểm cuối vận hành
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _may_khach(session, actor: Actor):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: actor
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def test_api_liet_ke_doc_ban_ke_tai_tep(session, du_lieu_2001, tien_to):
    lt.xuat_thang(session, "2001-03")
    session.commit()
    with _may_khach(session, QUAN_TRI) as c:
        ds = c.get("/core/v1/archive")
        assert ds.status_code == 200
        [muc] = [m for m in ds.json() if m["period"] == "2001-03"]
        assert (muc["event_rows"], muc["case_rows"], muc["url"]) == (5, 1, "/core/v1/archive/2001-03")

        chi_tiet = c.get(muc["url"]).json()
        assert chi_tiet["manifest"]["period"] == "2001-03"
        ban_ke = c.get(chi_tiet["manifest_url"])
        assert ban_ke.status_code == 200
        assert hashlib.sha256(ban_ke.content).hexdigest() == chi_tiet["manifest_sha256"]
        for f in chi_tiet["files"]:
            tra = c.get(f["url"])
            assert tra.status_code == 200 and tra.headers["content-type"] == "application/gzip"
            assert hashlib.sha256(tra.content).hexdigest() == f["sha256"]
            assert len(_dong_csv(tra.content)[1]) == f["rows"]

        assert c.get("/core/v1/archive/2001-02").status_code == 404
        assert c.get("/core/v1/archive/2001-13").status_code == 422
        assert c.get("/core/v1/archive/2001-03/files/khac.csv.gz").status_code == 404


def test_api_bao_hong_khi_tep_trong_kho_bi_sua(session, du_lieu_2001, tien_to):
    ban_ghi = lt.xuat_thang(session, "2001-03")
    session.commit()
    objects.luu_tep(ban_ghi.object_prefix + lt.TEP_NHAT_KY, b"da-bi-sua", "application/gzip", ban_ghi.bucket)
    with _may_khach(session, QUAN_TRI) as c:
        tra = c.get(f"/core/v1/archive/2001-03/files/{lt.TEP_NHAT_KY}")
    assert tra.status_code == 502
    assert tra.json()["detail"]["code"] == "archive-corrupted"


@pytest.mark.parametrize(
    "duong",
    ["/core/v1/archive", "/core/v1/archive/2001-03", f"/core/v1/archive/2001-03/files/{lt.TEP_BAN_KE}"],
)
def test_api_chi_quan_tri(session, duong):
    with _may_khach(session, DIEU_PHOI) as c:
        assert c.get(duong).status_code == 403


def test_kich_hoat_mot_luot_ngay(session, du_lieu_2001, tien_to, monkeypatch):
    """`POST /archive/scan` chạy đúng bộ quét, có khóa và nhịp; chỉ quản trị viên."""
    monkeypatch.setattr(get_settings(), "archive_max_months_per_run", 1)
    monkeypatch.setattr(main_mod, "SessionLocal", lambda: contextlib.nullcontext(session))
    with _may_khach(session, DIEU_PHOI) as c:
        assert c.post("/archive/scan").status_code == 403
    with _may_khach(session, QUAN_TRI) as c:
        tra = c.post("/archive/scan")
    assert tra.status_code == 200
    assert tra.json() == {"exported_periods": ["2001-03"], "skipped": False, "triggered_by": QUAN_TRI.id}
