# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử thông báo thư điện tử (#251).
#
# Định nghĩa hoàn thành của issue: hồ sơ tới mốc báo trước thì người có việc nhận một thư, hồ sơ tự
# đóng thì người gửi nhận thư; tắt cấu hình thì không thư nào và không lỗi; máy chủ thư sập thì chuyển
# trạng thái vẫn thành công; mỗi thư có một dòng vết.
#
# Danh bạ và máy chủ thư là giả ở đây: danh bạ trả một danh sách người cố định, máy chủ thư ghi lại
# thư thay vì gửi. Gửi thật qua SMTP vào Mailpit được kiểm trên cụm có hồ sơ `thu-thu`.

from __future__ import annotations

import datetime as dt
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.dependencies import current_actor
from app.auth.directory import DirectoryUnavailable, Person
from app.config import Settings
from app.db import get_session
from app.main import app
from app.models.thong_bao import (
    NotificationDelivery,
    NotificationOutbox,
    NotificationPreference,
    NotificationType,
)
from app.models.workflow_config import Priority, RequestType
from app.rules.sla import bay_gio
from app.thong_bao import bo_gui, hang_doi, thu
from app.workflow.context import Actor
from app.workflow.engine import create_case, perform_transition
from app.workflow.escalation import quet_het_han_cho

pytestmark = pytest.mark.usefixtures("lich_ca_ngay")

GIO = dt.timedelta(hours=1)
NGUOI_GUI = "nguoi-gui-251"
DP_DUNG = Actor(id="dp-251", roles=frozenset({"classifier"}))


def _cau_hinh(**doi) -> Settings:
    return Settings(**doi)


@pytest.fixture
def thu_bat(monkeypatch):
    """Máy chủ thư được cấu hình (giả) — mọi mô-đun đọc cùng một cấu hình."""
    ch = _cau_hinh(smtp_host="may-chu-thu-gia", notify_max_attempts=3, notify_retry_after_seconds=60)
    for mo_dun in (hang_doi, bo_gui, thu):
        monkeypatch.setattr(mo_dun, "get_settings", lambda ch=ch: ch)
    bo_gui.quen_danh_ba()
    yield ch
    bo_gui.quen_danh_ba()


class _DanhBaGia:
    def __init__(self, nguoi: list[Person], hong: bool = False):
        self.nguoi = nguoi
        self.hong = hong

    def everyone(self, timeout_seconds: float) -> list[Person]:
        if self.hong:
            raise DirectoryUnavailable("Keycloak giả đang tắt")
        return self.nguoi


class _MayThuGia:
    """Thay `KetNoiThu`: ghi lại thư, hay hỏng theo lệnh."""

    hop_thu: list[tuple[str, str, str]] = []
    hong = False

    def __init__(self, han_chot: float | None = None):
        self.da_mo = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def gui(self, den, ten, tieu_de, noi_dung):
        if _MayThuGia.hong:
            self.da_mo = False
            raise thu.ThuLoi("ConnectionRefusedError: máy chủ thư giả đang tắt")
        self.da_mo = True
        _MayThuGia.hop_thu.append((den, tieu_de, noi_dung))


@pytest.fixture
def may_thu(monkeypatch):
    _MayThuGia.hop_thu = []
    _MayThuGia.hong = False
    monkeypatch.setattr(bo_gui, "KetNoiThu", _MayThuGia)
    return _MayThuGia


def _danh_ba(phong_ban: str) -> _DanhBaGia:
    return _DanhBaGia(
        [
            Person(NGUOI_GUI, "an", "An Nguyễn", frozenset({"requester"}), email="an@thu.test"),
            Person("dp-251", "binh", "Bình Trần", frozenset({"classifier"}), email="binh@thu.test"),
            Person(
                "tp-251",
                "dung",
                "Dũng Phạm",
                frozenset({"approver"}),
                departments=frozenset({phong_ban}),
                email="dung@thu.test",
            ),
            Person(
                "tp-khac",
                "giang",
                "Giang Hoàng",
                frozenset({"approver"}),
                departments=frozenset({"phong-khac-251"}),
                email="giang@thu.test",
            ),
        ]
    )


def _cho_phong(session, phong_ban: str):
    loai = session.scalars(
        select(RequestType).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()
    ho_so = create_case(session, title="Máy chiếu phòng họp hỏng", requester_id=NGUOI_GUI)
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=DP_DUNG,
        changes={"priority_code": uu_tien, "request_type_code": loai.code},
    )
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="awaiting-acceptance",
        actor=DP_DUNG,
        changes={"department_code": phong_ban},
    )
    session.flush()
    return ho_so


def _su_kien(session, ho_so, trigger=None):
    cau = select(NotificationOutbox).where(NotificationOutbox.case_id == ho_so.id)
    if trigger:
        cau = cau.where(NotificationOutbox.trigger == trigger)
    return session.scalars(cau.order_by(NotificationOutbox.id)).all()


def _thu(session, ho_so):
    return session.scalars(
        select(NotificationDelivery)
        .where(NotificationDelivery.case_id == ho_so.id)
        .order_by(NotificationDelivery.id)
    ).all()


# ---------------------------------------------------------------------------
# Dữ liệu và tắt mặc định
# ---------------------------------------------------------------------------


def test_loai_thong_bao_nam_trong_du_lieu(session):
    loai = {t.code: t for t in session.scalars(select(NotificationType))}
    assert {t.trigger for t in loai.values()} == {"state-entered", "auto-warning", "auto-done"}
    for t in loai.values():
        assert t.subject_template and t.body_template


def test_tat_mac_dinh_khong_xep_hang_khong_gui(session, phong_ban, monkeypatch):
    """Máy chủ thư không cấu hình (mặc định): không sự kiện nào, bộ gửi không có gì để làm."""
    assert not Settings().notify_enabled
    ho_so = _cho_phong(session, phong_ban)
    assert _su_kien(session, ho_so) == []
    assert quet_het_han_cho(session, bay_gio(session) + 24 * GIO) == [ho_so.id]
    assert _su_kien(session, ho_so) == []


# ---------------------------------------------------------------------------
# Có việc chờ tôi
# ---------------------------------------------------------------------------


def test_chuyen_trang_thai_xep_su_kien_cung_giao_dich(session, phong_ban, thu_bat):
    ho_so = _cho_phong(session, phong_ban)
    su_kien = _su_kien(session, ho_so, hang_doi.TRIGGER_VAO_TRANG_THAI)
    # Tạo hồ sơ không qua cổng chuyển; hai lần chuyển của điều phối viên là hai sự kiện
    assert len(su_kien) == 2
    assert su_kien[-1].context == {"from_state": "classified", "to_state": "awaiting-acceptance"}
    assert su_kien[-1].actor_id == DP_DUNG.id


def test_thu_viec_cho_toi_toi_dung_truong_phong(session, phong_ban, thu_bat, may_thu):
    ho_so = _cho_phong(session, phong_ban)
    bo_gui.quet_gui(session, _danh_ba(phong_ban))

    nhan = {d.recipient_id for d in _thu(session, ho_so) if d.type_code == "viec-cho-toi"}
    # Sự kiện thứ nhất (vào Đã phân loại): bước chính là của điều phối viên — chính người vừa làm
    # thao tác, nên không ai nhận. Sự kiện thứ hai: trưởng phòng của đúng phòng, không phòng khác
    assert nhan == {"tp-251"}
    den = [h for h in may_thu.hop_thu if h[0] == "dung@thu.test"]
    assert len(den) == 1
    tieu_de, noi_dung = den[0][1], den[0][2]
    assert f"-{ho_so.id:04d}" in tieu_de
    assert "Máy chiếu phòng họp hỏng" in noi_dung and "Dũng Phạm" in noi_dung
    # Mỗi thư một dòng vết, đã gửi
    vet = [d for d in _thu(session, ho_so) if d.recipient_id == "tp-251"]
    assert [(d.status, d.attempts) for d in vet] == [("sent", 1)]
    assert vet[0].sent_at is not None and vet[0].body == noi_dung
    # Lượt sau không gửi lại
    bo_gui.quet_gui(session, _danh_ba(phong_ban))
    assert len([h for h in may_thu.hop_thu if h[0] == "dung@thu.test"]) == 1


def test_nguoi_dung_tat_loai_thi_khong_nhan(session, phong_ban, thu_bat, may_thu):
    session.add(NotificationPreference(user_id="tp-251", type_code="viec-cho-toi", enabled=False))
    ho_so = _cho_phong(session, phong_ban)
    bo_gui.quet_gui(session, _danh_ba(phong_ban))
    assert may_thu.hop_thu == []
    assert [(d.recipient_id, d.status) for d in _thu(session, ho_so)] == [("tp-251", "skipped")]


def test_danh_ba_sap_thi_su_kien_nam_cho(session, phong_ban, thu_bat, may_thu):
    ho_so = _cho_phong(session, phong_ban)
    assert bo_gui.quet_gui(session, _DanhBaGia([], hong=True)) == 0
    assert all(ev.processed_at is None for ev in _su_kien(session, ho_so))
    bo_gui.quet_gui(session, _danh_ba(phong_ban))
    assert len(may_thu.hop_thu) == 1


# ---------------------------------------------------------------------------
# Máy chủ thư sập
# ---------------------------------------------------------------------------


def test_may_chu_thu_sap_khong_lam_hong_chuyen_trang_thai(session, phong_ban, thu_bat, may_thu):
    may_thu.hong = True
    ho_so = _cho_phong(session, phong_ban)
    bo_gui.quet_gui(session, _danh_ba(phong_ban))
    # Chuyển trạng thái đã xong trước và không phụ thuộc thư
    assert ho_so.current_state == "awaiting-acceptance"
    (vet,) = _thu(session, ho_so)
    assert (vet.status, vet.attempts) == ("pending", 1)
    assert "máy chủ thư giả đang tắt" in vet.last_error
    assert vet.next_attempt_at >= bay_gio(session) + dt.timedelta(seconds=59)

    # Chuyển tiếp vẫn được khi thư còn nằm chờ
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=Actor(id="dp-khac-251", roles=frozenset({"classifier"})),
        note="Rút về để phân lại",
    )
    assert ho_so.current_state == "classified"


def test_thu_lai_co_gioi_han_roi_bao_hong(session, phong_ban, thu_bat, may_thu):
    may_thu.hong = True
    ho_so = _cho_phong(session, phong_ban)
    for _ in range(thu_bat.notify_max_attempts):
        bo_gui.quet_gui(session, _danh_ba(phong_ban))
        for d in _thu(session, ho_so):
            d.next_attempt_at = bay_gio(session) - GIO  # tới hạn ngay cho lượt sau
        session.flush()
    (vet,) = _thu(session, ho_so)
    assert (vet.status, vet.attempts) == ("failed", thu_bat.notify_max_attempts)
    # Hết lượt thử thì không thử nữa, kể cả khi máy chủ thư đã sống lại
    may_thu.hong = False
    bo_gui.quet_gui(session, _danh_ba(phong_ban))
    assert may_thu.hop_thu == []


def test_may_chu_song_lai_thi_thu_di(session, phong_ban, thu_bat, may_thu):
    may_thu.hong = True
    ho_so = _cho_phong(session, phong_ban)
    bo_gui.quet_gui(session, _danh_ba(phong_ban))
    may_thu.hong = False
    for d in _thu(session, ho_so):
        d.next_attempt_at = bay_gio(session) - GIO
    session.flush()
    bo_gui.quet_gui(session, _danh_ba(phong_ban))
    (vet,) = _thu(session, ho_so)
    assert (vet.status, vet.attempts) == ("sent", 2)


# ---------------------------------------------------------------------------
# Sắp tự chuyển, đã tự chuyển
# ---------------------------------------------------------------------------


def test_moc_bao_truoc_bao_mot_lan(session, phong_ban, thu_bat, may_thu):
    ho_so = _cho_phong(session, phong_ban)
    bay = bay_gio(session)
    # Chưa tới khoảng báo trước (24 giờ, báo trước 4 giờ)
    bo_gui.phat_hien_bao_truoc(session, bay + 20 * GIO - dt.timedelta(minutes=1))
    assert _su_kien(session, ho_so, hang_doi.TRIGGER_BAO_TRUOC) == []
    bo_gui.phat_hien_bao_truoc(session, bay + 20 * GIO)
    bo_gui.phat_hien_bao_truoc(session, bay + 21 * GIO)
    (ev,) = _su_kien(session, ho_so, hang_doi.TRIGGER_BAO_TRUOC)
    assert ev.context["deadline"]

    bo_gui.mo_rong_su_kien(session, bo_gui._danh_ba(_danh_ba(phong_ban)))
    bo_gui.gui_thu_den_han(session, bo_gui._danh_ba(None))
    canh_bao = [d for d in _thu(session, ho_so) if d.type_code == "sap-tu-dong"]
    assert [d.recipient_id for d in canh_bao] == ["tp-251"]
    assert "lúc" in canh_bao[0].subject and "$" not in canh_bao[0].body


def test_tu_dong_xong_thi_nguoi_gui_nhan_thu(session, phong_ban, thu_bat, may_thu):
    ho_so = _cho_phong(session, phong_ban)
    assert quet_het_han_cho(session, bay_gio(session) + 24 * GIO) == [ho_so.id]
    (ev,) = _su_kien(session, ho_so, hang_doi.TRIGGER_DA_TU_DI)
    assert ev.context["from_state"] == "awaiting-acceptance"
    bo_gui.quet_gui(session, _danh_ba(phong_ban))
    da_tu_dong = [d for d in _thu(session, ho_so) if d.type_code == "da-tu-dong"]
    assert [(d.recipient_id, d.status) for d in da_tu_dong] == [(NGUOI_GUI, "sent")]
    assert any(h[0] == "an@thu.test" for h in may_thu.hop_thu)


# ---------------------------------------------------------------------------
# Tùy chọn của người dùng qua API
# ---------------------------------------------------------------------------


@contextmanager
def _may_khach(session, actor: Actor):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: actor
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def test_api_tuy_chon_cua_chinh_minh(session):
    toi = Actor(id="nguoi-251-api", roles=frozenset({"requester"}))
    with _may_khach(session, toi) as c:
        r = c.get("/me/notifications")
        assert r.status_code == 200
        du_lieu = r.json()
        assert du_lieu["email_enabled"] is False
        assert all(t["enabled"] for t in du_lieu["types"])
        r = c.post("/me/notifications/viec-cho-toi", json={"enabled": False})
        assert r.status_code == 200
        bat = {t["code"]: t["enabled"] for t in r.json()["types"]}
        assert bat["viec-cho-toi"] is False and bat["da-tu-dong"] is True
        assert c.post("/me/notifications/khong-co", json={"enabled": False}).status_code == 404
    luu = session.get(NotificationPreference, ("nguoi-251-api", "viec-cho-toi"))
    assert luu is not None and luu.enabled is False
