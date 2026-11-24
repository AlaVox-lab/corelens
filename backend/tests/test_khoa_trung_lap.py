# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Khóa trùng lặp `Idempotency-Key` cho hai lệnh của lõi (#426): tạo hồ sơ và bước chuyển dưới /core/v1.
#
# Định nghĩa hoàn thành của issue: gọi lặp cùng khóa trả cùng kết quả và chỉ sinh một sự kiện. Các bài:
#
#   Trong phiên của bài (conftest.py, hoàn tác ở cuối) — lặp cùng khóa; khác thân; lần đầu bị chặn rồi sửa;
#     hết hạn; dòng đang chạy và dòng bỏ dở; hai người gọi; không tiêu đề; đường của cổng; khóa sai định dạng;
#     dọn dòng hết hạn; máy chết sau commit (dựng lại phản hồi); mất khóa giữa chừng; đặc tả OpenAPI.
#   Hai luồng thật, hai phiên thật — lời gọi thứ hai tới khi lời thứ nhất còn đang chạy: một thành công, một
#     409, rồi lần lặp nhận lại kết quả; tổng cộng một sự kiện. Dữ liệu ghi thật được dọn ở cuối bài.

from __future__ import annotations

import threading
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor, current_claims
from app.db import get_session
from app.main import app
from app.models.case import EventLog, Request
from app.workflow import khoa_trung_lap as ktl
from app.workflow import routes
from app.workflow.context import Actor
from app.workflow.engine import create_case
from app.workflow.schemas import BuocChuyenLoiVao, TaoHoSoVao
from tests.truong_mau import chi_tiet_mau

NGUOI_GUI = Actor(id="ktl-gui-426", name="Người gửi 426", roles=frozenset({"requester"}))
NGUOI_KHAC = Actor(id="ktl-khac-426", name="Người khác 426", roles=frozenset({"requester"}))

TAO = "/core/v1/workflow/requests"
TIEU_DE = ktl.TIEU_DE_KHOA
TRA_LAI = ktl.TIEU_DE_TRA_LAI


def _buoc(ma: int) -> str:
    return f"/core/v1/workflow/requests/{ma}/transitions"


def _khoa() -> dict[str, str]:
    return {TIEU_DE: str(uuid.uuid4())}


@pytest.fixture
def client(session):
    """Máy khách dùng chung phiên của bài; đổi tác nhân bằng `client.tac_nhan["actor"] = …`."""
    tac_nhan = {"actor": NGUOI_GUI}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: tac_nhan["actor"]
    app.dependency_overrides[current_claims] = lambda: {
        "sub": tac_nhan["actor"].id, "preferred_username": "nguoi.gui.426", "name": tac_nhan["actor"].name,
    }
    with TestClient(app) as c:
        c.tac_nhan = tac_nhan
        yield c
    app.dependency_overrides.clear()


def _than_tao(client, tieu_de: str = "Máy in tầng ba kẹt giấy") -> dict:
    loai = client.get("/core/v1/workflow/request-types").json()[0]
    return {"title": tieu_de, "description": "Thử #426.", "request_type_code": loai["code"],
            "details": chi_tiet_mau(loai)}


def _so_ho_so(session, actor: Actor = NGUOI_GUI) -> int:
    return session.scalar(select(func.count()).select_from(Request).where(Request.requester_id == actor.id))


def _so_su_kien(session, ma: int) -> int:
    return session.scalar(select(func.count()).select_from(EventLog).where(EventLog.case_id == ma))


def _so_khoa(session, actor: Actor = NGUOI_GUI) -> int:
    return session.execute(
        text("SELECT count(*) FROM idempotency_keys WHERE actor = :a"), {"a": actor.id}
    ).scalar_one()


def _ho_so(session, actor: Actor = NGUOI_GUI) -> Request:
    ho_so = create_case(session, title="Màn hình phòng họp nhấp nháy", description="Thử #426.",
                        requester_id=actor.id, requester_label=actor.label)
    session.commit()
    return ho_so


def _than_buoc(client, ma: int) -> dict:
    """Một bước người gửi đi được ngay, đổi trạng thái, không cần nhập trường — tra từ dữ liệu, không mã cứng."""
    cac_buoc = client.get(f"/core/v1/workflow/requests/{ma}").json()["allowed_transitions"]
    buoc = next((b for b in cac_buoc if not b["keeps_state"] and not b["fields"]), None)
    if buoc is None:
        pytest.skip("Bộ quy tắc không có bước nào người gửi đi được ngay ở trạng thái đầu.")
    return {"to_state": buoc["to_state"], "note": "Thử #426." if buoc["requires_note"] else None}


# ---------------------------------------------------------------------------
# Lặp cùng khóa
# ---------------------------------------------------------------------------


def test_tao_lap_cung_khoa_tra_lai_va_chi_mot_ho_so(client, session, rule_set):
    than, khoa = _than_tao(client), _khoa()
    dau = client.post(TAO, json=than, headers=khoa)
    lap = client.post(TAO, json=than, headers=khoa)

    assert dau.status_code == 201, dau.text
    assert TRA_LAI not in dau.headers
    assert lap.status_code == 201
    assert lap.headers[TRA_LAI] == "true"
    assert lap.json() == dau.json()
    assert _so_ho_so(session) == 1
    assert _so_khoa(session) == 1


def test_buoc_lap_cung_khoa_tra_lai_va_chi_mot_su_kien(client, session, rule_set):
    ho_so = _ho_so(session)
    than, khoa = _than_buoc(client, ho_so.id), _khoa()
    dau = client.post(_buoc(ho_so.id), json=than, headers=khoa)
    lap = client.post(_buoc(ho_so.id), json=than, headers=khoa)

    assert dau.status_code == 200, dau.text
    assert TRA_LAI not in dau.headers
    assert lap.status_code == 200
    assert lap.headers[TRA_LAI] == "true"
    assert lap.json() == dau.json()
    assert _so_su_kien(session, ho_so.id) == 1
    dong = session.execute(
        text("SELECT status, case_id, response_status FROM idempotency_keys WHERE actor = :a"), {"a": NGUOI_GUI.id}
    ).one()
    assert tuple(dong) == ("completed", ho_so.id, 200)


def test_than_khac_thu_tu_khoa_van_la_cung_lenh(client, session, rule_set):
    """Băm trên thân đã chuẩn hóa: đổi thứ tự khóa JSON không thành lệnh khác."""
    than, khoa = _than_tao(client), _khoa()
    assert client.post(TAO, json=than, headers=khoa).status_code == 201
    dao = dict(reversed(list(than.items())))
    lap = client.post(TAO, json=dao, headers=khoa)
    assert lap.status_code == 201 and lap.headers[TRA_LAI] == "true"
    assert _so_ho_so(session) == 1


# ---------------------------------------------------------------------------
# Cùng khóa, khác lệnh
# ---------------------------------------------------------------------------


def test_tao_cung_khoa_khac_than_422_khong_doi_gi(client, session, rule_set):
    khoa = _khoa()
    dau = client.post(TAO, json=_than_tao(client), headers=khoa)
    khac = client.post(TAO, json=_than_tao(client, "Tiêu đề khác hẳn"), headers=khoa)

    assert khac.status_code == 422
    assert khac.json()["detail"]["code"] == "idempotency-key-reused"
    assert _so_ho_so(session) == 1
    # Khóa cũ còn nguyên: lần lặp đúng thân vẫn nhận lại kết quả cũ
    lap = client.post(TAO, json=_than_tao(client), headers=khoa)
    assert lap.headers[TRA_LAI] == "true" and lap.json() == dau.json()


def test_buoc_cung_khoa_khac_ho_so_hay_khac_than_422(client, session, rule_set):
    mot, hai = _ho_so(session), _ho_so(session)
    than, khoa = _than_buoc(client, mot.id), _khoa()
    assert client.post(_buoc(mot.id), json=than, headers=khoa).status_code == 200

    khac_ho_so = client.post(_buoc(hai.id), json=than, headers=khoa)
    khac_than = client.post(_buoc(mot.id), json={**than, "note": "Ghi chú khác"}, headers=khoa)
    for tra in (khac_ho_so, khac_than):
        assert tra.status_code == 422
        assert tra.json()["detail"]["code"] == "idempotency-key-reused"
    assert _so_su_kien(session, mot.id) == 1
    assert _so_su_kien(session, hai.id) == 0


# ---------------------------------------------------------------------------
# Chỉ giữ lần thành công
# ---------------------------------------------------------------------------


def test_tao_lan_dau_bi_tu_choi_thi_sua_roi_gui_lai_cung_khoa(client, session, rule_set):
    khoa = _khoa()
    sai = client.post(TAO, json={**_than_tao(client), "request_type_code": "khong-co-loai-nay-426"}, headers=khoa)
    assert sai.status_code == 422
    assert sai.json()["detail"]["code"] == "unknown-request-type"
    assert _so_khoa(session) == 0

    dung = client.post(TAO, json=_than_tao(client), headers=khoa)
    assert dung.status_code == 201, dung.text
    assert TRA_LAI not in dung.headers
    assert _so_ho_so(session) == 1


def test_buoc_lan_dau_bi_engine_chan_thi_sua_roi_gui_lai_cung_khoa(client, session, rule_set):
    ho_so = _ho_so(session)
    trang_thai = [s["code"] for s in client.get("/core/v1/workflow/states").json()]
    di_duoc = {b["to_state"] for b in client.get(f"/core/v1/workflow/requests/{ho_so.id}").json()[
        "allowed_transitions"]}
    cam = next(s for s in trang_thai if s not in di_duoc)
    khoa = _khoa()

    sai = client.post(_buoc(ho_so.id), json={"to_state": cam}, headers=khoa)
    assert sai.status_code in (403, 409)
    assert _so_khoa(session) == 0

    dung = client.post(_buoc(ho_so.id), json=_than_buoc(client, ho_so.id), headers=khoa)
    assert dung.status_code == 200, dung.text
    assert TRA_LAI not in dung.headers
    assert _so_su_kien(session, ho_so.id) == 1


# ---------------------------------------------------------------------------
# Hết hạn, đang chạy, bỏ dở
# ---------------------------------------------------------------------------


def _het_han(session, actor: Actor = NGUOI_GUI) -> None:
    session.execute(
        text("UPDATE idempotency_keys SET expires_at = clock_timestamp() - interval '1 second' WHERE actor = :a"),
        {"a": actor.id},
    )
    session.commit()


def test_tao_het_han_thi_chay_nhu_lenh_moi(client, session, rule_set):
    than, khoa = _than_tao(client), _khoa()
    dau = client.post(TAO, json=than, headers=khoa)
    _het_han(session)
    moi = client.post(TAO, json=than, headers=khoa)

    assert moi.status_code == 201
    assert TRA_LAI not in moi.headers
    assert moi.json()["id"] != dau.json()["id"]
    assert _so_ho_so(session) == 2
    assert _so_khoa(session) == 1


def test_buoc_het_han_thi_engine_xet_lai_nhu_lenh_moi(client, session, rule_set):
    ho_so = _ho_so(session)
    than, khoa = _than_buoc(client, ho_so.id), _khoa()
    assert client.post(_buoc(ho_so.id), json=than, headers=khoa).status_code == 200
    _het_han(session)

    # Bước đã đi rồi: lệnh mới tới engine và bị engine từ chối — không phải kết quả trả lại
    moi = client.post(_buoc(ho_so.id), json=than, headers=khoa)
    assert moi.status_code in (403, 409)
    assert TRA_LAI not in moi.headers
    assert _so_su_kien(session, ho_so.id) == 1
    assert _so_khoa(session) == 0


def _chen_dong(session, than, tham_so_duong, endpoint: str, khoa: str, giu: str) -> None:
    """Một dòng `in_progress` như của lần gọi khác, khóa giữ tới `now() + giu`."""
    session.execute(
        text(
            "INSERT INTO idempotency_keys (actor, endpoint, key, request_hash, status, locked_until, expires_at)"
            " VALUES (:a, :e, :k, :h, 'in_progress', clock_timestamp() + CAST(:giu AS interval),"
            " clock_timestamp() + interval '1 day')"
        ),
        {"a": NGUOI_GUI.id, "e": endpoint, "k": khoa, "h": ktl.bam_lenh(than, tham_so_duong), "giu": giu},
    )
    session.commit()


def test_dang_chay_thi_409_kem_retry_after(client, session, rule_set):
    ho_so = _ho_so(session)
    than = _than_buoc(client, ho_so.id)
    khoa = str(uuid.uuid4())
    _chen_dong(session, BuocChuyenLoiVao(**than), {"case_id": ho_so.id},
               "POST /core/v1/workflow/requests/{case_id}/transitions", khoa, "30 seconds")

    tra = client.post(_buoc(ho_so.id), json=than, headers={TIEU_DE: khoa})
    assert tra.status_code == 409
    assert tra.json()["detail"]["code"] == "idempotency-request-in-progress"
    assert 1 <= int(tra.headers["Retry-After"]) <= 30
    assert _so_su_kien(session, ho_so.id) == 0


def test_bo_do_qua_locked_until_thi_chiem_lai(client, session, rule_set):
    ho_so = _ho_so(session)
    than = _than_buoc(client, ho_so.id)
    khoa = str(uuid.uuid4())
    _chen_dong(session, BuocChuyenLoiVao(**than), {"case_id": ho_so.id},
               "POST /core/v1/workflow/requests/{case_id}/transitions", khoa, "-1 second")

    tra = client.post(_buoc(ho_so.id), json=than, headers={TIEU_DE: khoa})
    assert tra.status_code == 200, tra.text
    assert TRA_LAI not in tra.headers
    assert _so_su_kien(session, ho_so.id) == 1
    assert session.execute(
        text("SELECT status FROM idempotency_keys WHERE key = :k"), {"k": khoa}
    ).scalar_one() == "completed"


def test_tao_bo_do_qua_locked_until_thi_chiem_lai(client, session, rule_set):
    than = _than_tao(client)
    khoa = str(uuid.uuid4())
    _chen_dong(session, TaoHoSoVao(**than), {}, "POST /core/v1/workflow/requests", khoa, "-1 second")

    tra = client.post(TAO, json=than, headers={TIEU_DE: khoa})
    assert tra.status_code == 201, tra.text
    assert _so_ho_so(session) == 1


# ---------------------------------------------------------------------------
# Người gọi, tiêu đề vắng, đường của cổng, định dạng
# ---------------------------------------------------------------------------


def test_hai_nguoi_goi_cung_chuoi_khoa_doc_lap(client, session, rule_set):
    khoa = _khoa()
    mot = client.post(TAO, json=_than_tao(client), headers=khoa)
    client.tac_nhan["actor"] = NGUOI_KHAC
    hai = client.post(TAO, json=_than_tao(client), headers=khoa)

    assert mot.status_code == hai.status_code == 201
    assert TRA_LAI not in hai.headers
    assert mot.json()["id"] != hai.json()["id"]
    assert _so_ho_so(session, NGUOI_GUI) == _so_ho_so(session, NGUOI_KHAC) == 1


def test_khong_tieu_de_thi_y_nhu_cu(client, session, rule_set):
    than = _than_tao(client)
    assert client.post(TAO, json=than).status_code == 201
    assert client.post(TAO, json=than).status_code == 201
    assert _so_ho_so(session) == 2

    ho_so = _ho_so(session)
    than_buoc = _than_buoc(client, ho_so.id)
    assert client.post(_buoc(ho_so.id), json=than_buoc).status_code == 200
    # Lần thứ hai tới engine như trước #426: bước đã đi nên bị từ chối
    assert client.post(_buoc(ho_so.id), json=than_buoc).status_code in (403, 409)
    assert _so_su_kien(session, ho_so.id) == 1
    assert _so_khoa(session) == 0


def test_duong_cua_cong_bo_qua_tieu_de(client, session, rule_set):
    """Lệnh tạo hồ sơ dùng chung hàm với cổng người dùng: ở đường không có /core/v1, tiêu đề bị bỏ qua —
    kể cả khóa sai định dạng."""
    than, khoa = _than_tao(client), _khoa()
    mot = client.post("/requests", json=than, headers=khoa)
    hai = client.post("/requests", json=than, headers=khoa)
    sai = client.post("/requests", json=than, headers={TIEU_DE: ""})

    assert mot.status_code == hai.status_code == sai.status_code == 201
    assert TRA_LAI not in hai.headers
    assert _so_ho_so(session) == 3
    assert _so_khoa(session) == 0


@pytest.mark.parametrize("gia_tri", ["", "k" * 256, "café".encode("latin-1")], ids=["rong", "dai-256", "ngoai-ascii"])
def test_khoa_sai_dinh_dang_422(client, session, rule_set, gia_tri):
    tra = client.post(TAO, json=_than_tao(client), headers={TIEU_DE: gia_tri})
    assert tra.status_code == 422
    assert tra.json()["detail"]["code"] == "idempotency-key-invalid"
    ho_so = _ho_so(session)
    buoc = client.post(_buoc(ho_so.id), json=_than_buoc(client, ho_so.id), headers={TIEU_DE: gia_tri})
    assert buoc.status_code == 422
    assert buoc.json()["detail"]["code"] == "idempotency-key-invalid"
    assert _so_ho_so(session) == 1
    assert _so_su_kien(session, ho_so.id) == 0


def test_khoa_dai_dung_255_ky_tu_duoc_nhan(client, session, rule_set):
    tra = client.post(TAO, json=_than_tao(client), headers={TIEU_DE: "k" * 255})
    assert tra.status_code == 201, tra.text


# ---------------------------------------------------------------------------
# Dọn, máy chết sau commit, mất khóa giữa chừng
# ---------------------------------------------------------------------------


def test_don_dong_het_han(client, session, rule_set):
    cu, moi = _khoa(), _khoa()
    client.post(TAO, json=_than_tao(client), headers=cu)
    _het_han(session)
    client.post(TAO, json=_than_tao(client, "Hồ sơ thứ hai"), headers=moi)

    assert ktl.don_khoa_het_han(session) >= 1
    session.commit()
    con = session.execute(
        text("SELECT key FROM idempotency_keys WHERE actor = :a"), {"a": NGUOI_GUI.id}
    ).scalars().all()
    assert con == [moi[TIEU_DE]]


@pytest.mark.parametrize("lenh", ["tao", "buoc"])
def test_may_chet_sau_commit_lan_lap_dung_lai_khong_chay_hai_lan(client, session, rule_set, monkeypatch, lenh):
    """Lệnh đã commit nhưng chưa kịp ghi thân phản hồi. Dấu xong nằm cùng giao dịch với lệnh nên lần lặp vẫn
    thấy khóa đã xong: dựng lại chi tiết hồ sơ, không chạy lần hai. Bài này bắt đột biến "đánh dấu xong sau
    commit" — khi đó dòng còn `in_progress` và lần lặp nhận 409."""
    if lenh == "tao":
        duong, than, ma_tt = TAO, _than_tao(client), 201
    else:
        ho_so = _ho_so(session)
        duong, than, ma_tt = _buoc(ho_so.id), _than_buoc(client, ho_so.id), 200
    khoa = _khoa()

    def chet(*_a, **_k):
        raise RuntimeError("máy chết ngay sau commit")

    monkeypatch.setattr(ktl, "_ghi_ket_qua", chet)
    hong = TestClient(app, raise_server_exceptions=False).post(duong, json=than, headers=khoa)
    assert hong.status_code == 500
    monkeypatch.undo()

    lap = client.post(duong, json=than, headers=khoa)
    assert lap.status_code == ma_tt, lap.text
    assert lap.headers[TRA_LAI] == "true"
    ma = lap.json()["id"]
    assert lap.json() == client.get(f"/core/v1/workflow/requests/{ma}").json()
    assert _so_ho_so(session) == 1
    if lenh == "buoc":
        assert _so_su_kien(session, ma) == 1


def test_mat_khoa_giua_chung_thi_lenh_hoan_tac(client, session, rule_set, monkeypatch):
    """Lần chạy quá lâu, lần khác đã chiếm khóa (mốc `locked_until` đổi): không được đánh dấu xong, lần chuyển
    hoàn tác, trả 409."""
    ho_so = _ho_so(session)
    goc = routes.thuc_hien_chuyen

    def bi_chiem(*a, **k):
        kq = goc(*a, **k)
        session.execute(
            text("UPDATE idempotency_keys SET locked_until = locked_until + interval '1 second' WHERE actor = :a"),
            {"a": NGUOI_GUI.id},
        )
        return kq

    monkeypatch.setattr(routes, "thuc_hien_chuyen", bi_chiem)
    tra = client.post(_buoc(ho_so.id), json=_than_buoc(client, ho_so.id), headers=_khoa())
    assert tra.status_code == 409
    assert tra.json()["detail"]["code"] == "idempotency-request-in-progress"
    assert _so_su_kien(session, ho_so.id) == 0


# ---------------------------------------------------------------------------
# Đặc tả OpenAPI
# ---------------------------------------------------------------------------


def test_openapi_chi_khai_o_hai_lenh_cua_loi():
    duong = app.openapi()["paths"]
    for mau, phuong_thuc, ma in [
        (TAO, "post", "201"),
        ("/core/v1/workflow/requests/{case_id}/transitions", "post", "200"),
    ]:
        tt = duong[mau][phuong_thuc]
        assert any(p["name"] == TIEU_DE and p["in"] == "header" and not p["required"] for p in tt["parameters"])
        assert TRA_LAI in tt["responses"][ma]["headers"]
        assert "409" in tt["responses"]
        # Phản hồi sẵn có còn nguyên
        assert "content" in tt["responses"][ma] and "422" in tt["responses"]
    # Đường của cổng dùng chung hàm tạo hồ sơ nhưng không khai tiêu đề
    cong = duong["/requests"]["post"]
    assert all(p["name"] != TIEU_DE for p in cong.get("parameters", []))
    assert "409" not in cong["responses"]
    assert TRA_LAI not in cong["responses"]["201"].get("headers", {})


# ---------------------------------------------------------------------------
# Hai luồng thật, hai phiên thật
# ---------------------------------------------------------------------------


def _don_that(db_engine, actor_id: str) -> None:
    """Dọn dữ liệu ghi thật của một người gọi. Nhật ký chỉ ghi thêm nên tạm tắt trigger chặn xóa, trong cùng
    giao dịch, như test_webhook.py."""
    ho_so = "SELECT id FROM requests WHERE requester_id = :a"
    with db_engine.begin() as don:
        don.execute(text("DELETE FROM idempotency_keys WHERE actor = :a"), {"a": actor_id})
        don.execute(text("ALTER TABLE event_log DISABLE TRIGGER USER"))
        don.execute(text("DELETE FROM webhook_deliveries WHERE event_id IN "
                         f"(SELECT id FROM event_log WHERE case_id IN ({ho_so}))"), {"a": actor_id})
        don.execute(text(f"DELETE FROM notification_deliveries WHERE case_id IN ({ho_so})"), {"a": actor_id})
        don.execute(text(f"DELETE FROM notification_outbox WHERE case_id IN ({ho_so})"), {"a": actor_id})
        don.execute(text(f"DELETE FROM event_log WHERE case_id IN ({ho_so})"), {"a": actor_id})
        don.execute(text("ALTER TABLE event_log ENABLE TRIGGER USER"))
        don.execute(text("DELETE FROM requests WHERE requester_id = :a"), {"a": actor_id})


@pytest.mark.parametrize("lenh", ["tao", "buoc"])
def test_hai_loi_goi_dong_thoi_cung_khoa_chi_mot_lan_chay(db_engine, rule_set, monkeypatch, lenh):
    """Lời gọi thứ nhất dừng giữa lệnh (sau engine, trước commit); lời thứ hai cùng khóa tới đúng lúc đó, ở
    luồng khác, phiên khác: nhận 409 kèm `Retry-After`. Lời thứ nhất xong thì lần lặp nhận lại kết quả."""
    actor = Actor(id=f"ktl-song-song-{uuid.uuid4().hex[:8]}", name="Song song 426", roles=frozenset({"requester"}))
    app.dependency_overrides[current_actor] = lambda: actor
    dang_chay, cho_xong = threading.Event(), threading.Event()
    ket_qua: dict[str, object] = {}
    try:
        with TestClient(app) as c:
            loai = c.get("/core/v1/workflow/request-types").json()[0]
            than_tao = {"title": "Hai lời gọi song song", "description": "Thử #426.",
                        "request_type_code": loai["code"], "details": chi_tiet_mau(loai)}
            if lenh == "tao":
                duong, than, ten_ham = TAO, than_tao, "create_case"
            else:
                ma = c.post(TAO, json=than_tao).json()["id"]  # không khóa: hồ sơ nền của bài
                duong, ten_ham = _buoc(ma), "thuc_hien_chuyen"
                cac_buoc = c.get(f"/core/v1/workflow/requests/{ma}").json()["allowed_transitions"]
                buoc = next(b for b in cac_buoc if not b["keeps_state"] and not b["fields"])
                than = {"to_state": buoc["to_state"], "note": "Thử #426." if buoc["requires_note"] else None}
            goc = getattr(routes, ten_ham)
            da_dung: list[int] = []

            def cham(*a, **k):
                kq = goc(*a, **k)
                if not da_dung:
                    da_dung.append(1)
                    dang_chay.set()
                    assert cho_xong.wait(timeout=20)
                return kq

            monkeypatch.setattr(routes, ten_ham, cham)
            khoa = _khoa()
            luong = threading.Thread(target=lambda: ket_qua.update(dau=c.post(duong, json=than, headers=khoa)))
            luong.start()
            try:
                assert dang_chay.wait(timeout=20)
                ket_qua["giua"] = c.post(duong, json=than, headers=khoa)
            finally:
                cho_xong.set()
                luong.join(timeout=20)
            ket_qua["lap"] = c.post(duong, json=than, headers=khoa)

        dau, giua, lap = ket_qua["dau"], ket_qua["giua"], ket_qua["lap"]
        ma_tt = 201 if lenh == "tao" else 200
        assert dau.status_code == ma_tt, dau.text
        assert giua.status_code == 409 and giua.json()["detail"]["code"] == "idempotency-request-in-progress"
        assert int(giua.headers["Retry-After"]) >= 1
        assert lap.status_code == ma_tt and lap.headers[TRA_LAI] == "true"
        assert lap.json() == dau.json()
        with Session(db_engine) as doc:
            ma_ho_so = doc.scalars(select(Request.id).where(Request.requester_id == actor.id)).all()
            assert len(ma_ho_so) == 1
            so_su_kien = doc.scalar(select(func.count()).select_from(EventLog).where(
                EventLog.case_id == ma_ho_so[0]))
        assert so_su_kien == (0 if lenh == "tao" else 1)
    finally:
        app.dependency_overrides.clear()
        _don_that(db_engine, actor.id)
