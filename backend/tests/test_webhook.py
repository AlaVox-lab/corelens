# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử truyền phát sự kiện bằng webhook (#390).
#
# Năm điều phải canh:
#
#   Quyền      — chỉ quản trị viên đăng ký, xem, hủy; bí mật chỉ trả một lần.
#   Con trỏ    — đăng ký mới không nhận sự kiện cũ; mỗi sự kiện mới đúng một lần gửi, kể cả khi mở rộng
#                chạy hai lượt.
#   Lọc        — theo mã hoạt động và quy trình là dữ liệu của đăng ký.
#   Gửi        — thân JSON đúng sự kiện, chữ ký HMAC kiểm lại được; 2xx là xong.
#   Thử lại    — hỏng thì chờ rồi thử lại, quá số lần thì đánh dấu hỏng; lỗi mạng không ném ra ngoài.
#
# Không gọi mạng thật: `app.webhook.gui_http` được thay bằng hàm ghi lại lời gọi.

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app import webhook
from app.auth.dependencies import current_actor
from app.db import get_session
from app.main import app
from app.models.case import EventLog, Request
from app.models.webhook import CHO_GUI, DA_GUI, HONG, WebhookDelivery, WebhookSubscription
from app.models.workflow_config import Priority, RequestType
from app.webhook import kiem_chu_ky, mo_rong, quet_webhook
from app.workflow.context import Actor
from app.workflow.engine import create_case, perform_transition

QUAN_TRI = Actor(id="kc-qt-01", name="Võ Khánh", roles=frozenset({"administrator"}))
NGUOI_GUI = Actor(id="kc-gui-01", name="An Nguyễn", roles=frozenset({"requester"}))
PHAN_LOAI = Actor(id="kc-pl-01", name="Bình Trần", roles=frozenset({"classifier"}))


@pytest.fixture
def client(session):
    trang_thai = {"actor": QUAN_TRI}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: trang_thai["actor"]
    with TestClient(app) as c:
        c.trang_thai = trang_thai
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mang_gia(monkeypatch):
    """Thay lời gọi HTTP: ghi lại (url, thân, tiêu đề), trả mã theo hàng đợi `ma` (mặc định 200)."""
    goi: list[tuple[str, bytes, dict]] = []
    ma: list[int | Exception] = []

    def gui(url, than, tieu_de, _han):
        goi.append((url, than, tieu_de))
        kq = ma.pop(0) if ma else 200
        if isinstance(kq, Exception):
            raise kq
        return kq

    monkeypatch.setattr(webhook, "gui_http", gui)
    return goi, ma


def _dang_ky(session, **kw) -> WebhookSubscription:
    dk = WebhookSubscription(
        url="http://ben-nhan.test/su-kien",
        secret="bi-mat-thu",
        owner_id=QUAN_TRI.id,
        last_event_id=session.scalar(text("SELECT coalesce(max(id), 0) FROM event_log")),
        **kw,
    )
    session.add(dk)
    session.flush()
    return dk


def _phan_loai(session) -> Request:
    """Một hồ sơ mới đi một bước — sinh đúng một dòng nhật ký."""
    loai = session.scalars(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    ho_so = create_case(
        session, title="Màn hình phòng họp nhấp nháy", requester_id=NGUOI_GUI.id,
        requester_label=NGUOI_GUI.label, request_type_code=loai,
    )
    uu_tien = session.scalars(select(Priority.code).order_by(Priority.display_order)).first()
    perform_transition(session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
                       changes={"priority_code": uu_tien})
    session.flush()
    return ho_so


def _lan_gui(session, dk) -> list[WebhookDelivery]:
    return list(session.scalars(
        select(WebhookDelivery).where(WebhookDelivery.subscription_id == dk.id).order_by(WebhookDelivery.id)
    ))


def _den_han_ngay(session) -> None:
    session.execute(text("UPDATE webhook_deliveries SET next_attempt_at = now() - interval '1 second'"))


# ---------------------------------------------------------------------------
# Quyền
# ---------------------------------------------------------------------------


def test_quan_tri_dang_ky_nhan_bi_mat_mot_lan(client, rule_set):
    tao = client.post("/core/v1/webhooks", json={"url": "http://ben-nhan.test/a", "description": "Bot chat"})
    assert tao.status_code == 201, tao.text
    assert len(tao.json()["secret"]) == 64

    ma = tao.json()["id"]
    xem = client.get(f"/core/v1/webhooks/{ma}")
    assert xem.status_code == 200
    assert "secret" not in xem.json()
    assert any(d["id"] == ma for d in client.get("/core/v1/webhooks").json())

    assert client.delete(f"/core/v1/webhooks/{ma}").status_code == 204
    assert client.get(f"/core/v1/webhooks/{ma}").status_code == 404


def test_nguoi_khong_phai_quan_tri_bi_chan(client):
    client.trang_thai["actor"] = NGUOI_GUI
    assert client.post("/core/v1/webhooks", json={"url": "http://ben-nhan.test/a"}).status_code == 403
    assert client.get("/core/v1/webhooks").status_code == 403


@pytest.mark.parametrize("url", ["ftp://ben-nhan.test/a", "khong-phai-dia-chi"])
def test_dia_chi_khong_phai_http_bi_tu_choi(client, url):
    assert client.post("/core/v1/webhooks", json={"url": url}).status_code == 422


def test_quy_trinh_khong_ton_tai_bi_tu_choi(client):
    tra = client.post("/core/v1/webhooks", json={"url": "http://ben-nhan.test/a", "process": "khong-co"})
    assert tra.status_code == 422
    assert tra.json()["detail"]["code"] == "unknown-process"


def test_khong_token_401():
    with TestClient(app) as may_khach:
        assert may_khach.get("/core/v1/webhooks").status_code == 401


# ---------------------------------------------------------------------------
# Con trỏ và lọc
# ---------------------------------------------------------------------------


def test_dang_ky_moi_chi_nhan_su_kien_sau_luc_tao(session, rule_set):
    _phan_loai(session)
    dk = _dang_ky(session)
    assert mo_rong(session) == 0

    _phan_loai(session)
    assert mo_rong(session) == 1
    # Lượt thứ hai không sinh trùng
    assert mo_rong(session) == 0
    assert len(_lan_gui(session, dk)) == 1


def test_loc_theo_hoat_dong(session, rule_set):
    hoat_dong = None
    dk_khop = _dang_ky(session)
    _phan_loai(session)
    hoat_dong = session.scalars(select(EventLog.activity).order_by(EventLog.id.desc())).first()

    dk_dung = _dang_ky(session, activities=[hoat_dong])
    dk_lech = _dang_ky(session, activities=["khong-bao-gio-xay-ra"])
    _phan_loai(session)
    mo_rong(session)

    assert len(_lan_gui(session, dk_dung)) == 1
    assert len(_lan_gui(session, dk_lech)) == 0
    assert len(_lan_gui(session, dk_khop)) == 2
    # Không khớp vẫn dời con trỏ
    session.refresh(dk_lech)
    assert dk_lech.last_event_id == session.scalar(select(EventLog.id).order_by(EventLog.id.desc()))


def test_loc_theo_quy_trinh(session, rule_set):
    ma_quy_trinh = session.scalar(text(
        "SELECT rs.process_code FROM rule_sets rs WHERE rs.id = :id"), {"id": rule_set.id})
    quy_trinh_khac = session.scalar(text(
        "SELECT code FROM processes WHERE code <> :ma ORDER BY code LIMIT 1"), {"ma": ma_quy_trinh})
    if quy_trinh_khac is None:
        pytest.skip("Cần ít nhất hai quy trình.")

    dk_dung = _dang_ky(session, process_code=ma_quy_trinh)
    dk_khac = _dang_ky(session, process_code=quy_trinh_khac)
    _phan_loai(session)
    mo_rong(session)

    assert len(_lan_gui(session, dk_dung)) == 1
    assert len(_lan_gui(session, dk_khac)) == 0


def test_dang_ky_tat_khong_nhan(session, rule_set):
    dk = _dang_ky(session, is_active=False)
    _phan_loai(session)
    mo_rong(session)
    assert _lan_gui(session, dk) == []


# ---------------------------------------------------------------------------
# Gửi
# ---------------------------------------------------------------------------


def test_gui_than_dung_su_kien_va_chu_ky_kiem_duoc(session, rule_set, mang_gia):
    goi, _ = mang_gia
    dk = _dang_ky(session)
    ho_so = _phan_loai(session)

    assert quet_webhook(session) == 1

    url, than, tieu_de = goi[0]
    assert url == dk.url
    du_lieu = json.loads(than)
    su_kien = session.get(EventLog, du_lieu["event_id"])
    assert du_lieu["case_id"] == ho_so.id
    assert (du_lieu["activity"], du_lieu["from_state"], du_lieu["to_state"]) == (
        su_kien.activity, su_kien.from_state, su_kien.to_state)
    assert du_lieu["timestamp"].endswith("+00:00")
    assert tieu_de["X-DXOS-Event-Id"] == str(su_kien.id)
    assert kiem_chu_ky(dk.secret, tieu_de["X-DXOS-Timestamp"], than, tieu_de["X-DXOS-Signature"])
    assert not kiem_chu_ky("bi-mat-khac", tieu_de["X-DXOS-Timestamp"], than, tieu_de["X-DXOS-Signature"])

    (lg,) = _lan_gui(session, dk)
    assert (lg.status, lg.attempts, lg.last_status_code) == (DA_GUI, 1, 200)


def test_hong_thi_thu_lai_roi_toi(session, rule_set, mang_gia):
    goi, ma = mang_gia
    dk = _dang_ky(session)
    _phan_loai(session)
    ma.extend([503, OSError("Connection refused")])

    assert quet_webhook(session) == 0
    (lg,) = _lan_gui(session, dk)
    assert (lg.status, lg.attempts, lg.last_error) == (CHO_GUI, 1, "HTTP 503")
    # Chưa tới hạn thử lại: lượt sau không gửi
    assert quet_webhook(session) == 0
    assert len(goi) == 1

    _den_han_ngay(session)
    assert quet_webhook(session) == 0
    session.refresh(lg)
    assert lg.attempts == 2 and "Connection refused" in lg.last_error

    _den_han_ngay(session)
    assert quet_webhook(session) == 1
    session.refresh(lg)
    assert (lg.status, lg.attempts) == (DA_GUI, 3)


def test_qua_so_lan_thi_hong_han(session, rule_set, mang_gia, monkeypatch):
    _, ma = mang_gia
    monkeypatch.setattr(webhook.get_settings(), "webhook_max_attempts", 2)
    dk = _dang_ky(session)
    _phan_loai(session)
    ma.extend([500, 500, 500])

    quet_webhook(session)
    _den_han_ngay(session)
    quet_webhook(session)
    _den_han_ngay(session)
    quet_webhook(session)

    (lg,) = _lan_gui(session, dk)
    assert (lg.status, lg.attempts) == (HONG, 2)


def test_xem_lan_gui_qua_api(client, session, rule_set, mang_gia):
    dk = _dang_ky(session)
    _phan_loai(session)
    quet_webhook(session)
    session.commit()

    tra = client.get(f"/core/v1/webhooks/{dk.id}/deliveries")
    assert tra.status_code == 200
    assert [d["status"] for d in tra.json()] == [DA_GUI]
