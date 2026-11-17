# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử hồ sơ đã giải quyết tương tự (#319).
#
#   1. Chỉ hồ sơ người gửi xác nhận đạt vào chỉ mục — tự đóng, hủy, chưa đóng thì không. Nhận ra bằng
#      bộ quy tắc (cạnh tra từ dữ liệu), không mã trạng thái nào trong bài.
#   2. Cách giải quyết lấy ghi chú hoàn thành và lời nhắn người gửi thấy được — không lời nhắn nội bộ;
#      tên người, email, số điện thoại bị ẩn trước khi ghi.
#   3. Tìm qua đúng đường gọi (mô hình nhúng giả bằng HTTP, như CI không tải mô hình): hồ sơ đúng đứng
#      đầu; mô hình tắt, cổng đóng, trả chậm — danh sách rỗng, không lỗi, trong hạn chót.
#   4. Ghi nhận đã xem, đã gửi, bỏ không gửi (bấm và quá hạn).

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import re
import socket
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text, update

from app.auth.dependencies import current_actor
from app.config import Settings
from app.db import get_session
from app.intelligence import mo_hinh, tuong_tu
from app.main import app
from app.models.case import CaseMessage, EventLog, Request
from app.models.workflow_config import MessageKind, RequestType, State, Transition
from app.workflow.context import Actor
from app.workflow.engine import create_case
from tests.truong_mau import chi_tiet_mau

SO_CHIEU = 64
HAN_CHOT = 1.0


def _vec(chu: str) -> list[float]:
    """Véc-tơ túi từ: mỗi từ băm vào một chiều. Đủ để câu cùng từ gần nhau, câu khác từ xa nhau."""
    v = [0.0] * SO_CHIEU
    for tu in re.findall(r"\w+", chu.lower()):
        v[int(hashlib.md5(tu.encode()).hexdigest(), 16) % SO_CHIEU] += 1.0
    do_dai = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / do_dai for x in v]


class NhungGia:
    """Thay dịch vụ nhúng: điểm cuối `/v1/embeddings` kiểu OpenAI. Bỏ phần lời dặn trước `Query:`."""

    def __init__(self) -> None:
        self.cham = 0.0
        self.so_lan = 0
        gia = self

        class XuLy(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                than = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                gia.so_lan += 1
                if gia.cham:
                    time.sleep(gia.cham)
                du_lieu = [
                    {"index": i, "embedding": _vec(doan.split("Query:", 1)[-1])}
                    for i, doan in enumerate(than["input"])
                ]
                ra = json.dumps({"data": du_lieu}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(ra)))
                self.end_headers()
                self.wfile.write(ra)

            def log_message(self, *a):
                pass

        self.may_chu = HTTPServer(("127.0.0.1", 0), XuLy)
        self.url = f"http://127.0.0.1:{self.may_chu.server_address[1]}"


def dat_cau_hinh(monkeypatch, **gia_tri) -> Settings:
    cau_hinh = Settings(**{"similar_min_score": 0.2, **gia_tri})
    for tep in (mo_hinh, tuong_tu):
        monkeypatch.setattr(tep, "get_settings", lambda: cau_hinh)
    return cau_hinh


@pytest.fixture
def nhung_gia(monkeypatch):
    gia = NhungGia()
    luong = threading.Thread(target=gia.may_chu.serve_forever, daemon=True)
    luong.start()
    dat_cau_hinh(
        monkeypatch,
        embedding_url=gia.url,
        embedding_timeout_seconds=HAN_CHOT,
        similar_timeout_seconds=HAN_CHOT,
    )
    try:
        yield gia
    finally:
        gia.may_chu.shutdown()
        gia.may_chu.server_close()


def _cong_dong() -> str:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return f"http://127.0.0.1:{s.getsockname()[1]}"


# ---------------------------------------------------------------------------
# Ẩn tên người và liên hệ
# ---------------------------------------------------------------------------


def test_an_danh_email_so_dien_thoai_ten_nguoi():
    ten = frozenset({"Lê Văn Cường", "Nguyễn Thị Mai"})
    van_ban = (
        "Đã gọi anh Cường (0912 345 678, cuong.le@congty.vn) và Nguyễn Thị Mai; chị mai xác nhận. "
        "Số máy +84 912345678. An toàn thông tin không đổi."
    )
    ra = tuong_tu.an_danh(van_ban, ten)
    assert "Cường" not in ra and "Mai" not in ra.replace("mai", "") and "mai xác" not in ra
    assert "0912" not in ra and "912345678" not in ra and "@" not in ra
    assert ra.count(tuong_tu.AN_TEN) == 3
    assert ra.count(tuong_tu.AN_SO_DIEN_THOAI) == 2
    assert tuong_tu.AN_EMAIL in ra
    # Chữ thường trùng tên một chữ không bị đụng
    assert "An toàn thông tin" in ra


# ---------------------------------------------------------------------------
# Dựng cảnh theo bộ quy tắc
# ---------------------------------------------------------------------------


@pytest.fixture
def canh(session, rule_set):
    """Cạnh tra từ dữ liệu: làm xong (bước chính người được giao), xác nhận đạt (người, từ trạng thái
    sau làm xong vào trạng thái kết thúc), tự đóng (hệ thống, cùng cặp), hủy (người, vào kết thúc, xuất
    phát từ trạng thái khác)."""
    ket_thuc = set(
        session.scalars(
            select(State.code).where(State.rule_set_id == rule_set.id, State.is_terminal)
        )
    )
    tat_ca = session.scalars(select(Transition).where(Transition.rule_set_id == rule_set.id)).all()
    xong = next(
        (t for t in tat_ca if t.primary_scope == tuong_tu.PHAM_VI_NGUOI_DUOC_GIAO and not t.is_system),
        None,
    )
    if xong is None:
        pytest.skip("Bộ quy tắc không có bước chính của người được giao.")
    dat = next(
        (t for t in tat_ca if t.from_state == xong.to_state and t.to_state in ket_thuc and not t.is_system),
        None,
    )
    tu_dong = next(
        (t for t in tat_ca if t.from_state == xong.to_state and t.to_state in ket_thuc and t.is_system),
        None,
    )
    huy = next(
        (t for t in tat_ca if t.from_state != xong.to_state and t.to_state in ket_thuc and not t.is_system),
        None,
    )
    if dat is None:
        pytest.skip("Bộ quy tắc không có cạnh xác nhận đạt.")
    return {"xong": xong, "dat": dat, "tu_dong": tu_dong, "huy": huy}


def _loai(session) -> str:
    return session.scalars(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()


NGUOI_GUI = Actor(id="nd-gui-319", name="Mai Nguyễn", roles=frozenset({"requester"}))


def _dung_ho_so(session, tieu_de: str, mo_ta: str, cac_canh: list[Transition], ghi_chu_xong: str = "") -> Request:
    """Hồ sơ đi lần lượt các cạnh (dòng nhật ký như engine ghi), trạng thái cuối = đích cạnh cuối."""
    ho_so = create_case(
        session,
        title=tieu_de,
        description=mo_ta,
        requester_id=NGUOI_GUI.id,
        requester_label=NGUOI_GUI.label,
        request_type_code=_loai(session),
    )
    session.flush()
    for t in cac_canh:
        session.add(
            EventLog(
                case_id=ho_so.id,
                activity=t.activity_code,
                actor="nd-xu-ly-319" if not t.is_system else "system",
                actor_label="Lê Văn Cường" if not t.is_system else "Hệ thống",
                from_state=t.from_state,
                to_state=t.to_state,
                note=ghi_chu_xong if t.primary_scope == tuong_tu.PHAM_VI_NGUOI_DUOC_GIAO else None,
            )
        )
        session.flush()
    if cac_canh:
        session.execute(
            update(Request).where(Request.id == ho_so.id).values(current_state=cac_canh[-1].to_state)
        )
    session.flush()
    session.refresh(ho_so)
    return ho_so


def test_chi_ho_so_xac_nhan_dat_vao_chi_muc(session, canh):
    dat = _dung_ho_so(session, "Máy chiếu phòng họp không lên hình", "", [canh["xong"], canh["dat"]])
    chua_dong = _dung_ho_so(session, "Chuột không dây mất kết nối", "", [canh["xong"]])
    khac = []
    if canh["tu_dong"]:
        khac.append(_dung_ho_so(session, "Quên mật khẩu email", "", [canh["xong"], canh["tu_dong"]]))
    if canh["huy"]:
        khac.append(_dung_ho_so(session, "Xin giấy xác nhận", "", [canh["huy"]]))
    session.commit()

    can = {ma for ma, _ in tuong_tu.ho_so_can_lap(session, 100_000)}
    assert dat.id in can
    assert chua_dong.id not in can
    for h in khac:
        assert h.id not in can


def test_cach_giai_quyet_khong_lay_loi_nhan_noi_bo_va_da_an_ten(session, canh):
    ho_so = _dung_ho_so(
        session,
        "Máy in tầng 3 kẹt giấy",
        "Liên hệ chị Mai Nguyễn qua mai.nguyen@congty.vn",
        [canh["xong"], canh["dat"]],
        ghi_chu_xong="Anh Cường đã thay trục kéo giấy, gọi 0987654321 nếu tái diễn.",
    )
    noi_bo = session.scalars(select(MessageKind.code).where(MessageKind.hidden_from_requester)).first()
    cong_khai = session.scalars(
        select(MessageKind.code).where(MessageKind.hidden_from_requester.is_(False))
    ).first()
    session.add(CaseMessage(case_id=ho_so.id, kind=cong_khai, author="nd-xu-ly-319", author_label="Lê Văn Cường", body="Đã vệ sinh khay giấy."))
    session.flush()
    if noi_bo:
        session.add(CaseMessage(case_id=ho_so.id, kind=noi_bo, author="nd-xu-ly-319", author_label="Lê Văn Cường", body="BÍ MẬT NỘI BỘ"))
    session.commit()

    tai_lieu = tuong_tu.doc_tai_lieu(session, ho_so.id, ho_so.created_at, tuong_tu.ten_nguoi_da_biet(session))
    assert "thay trục kéo giấy" in tai_lieu.resolution
    assert "vệ sinh khay giấy" in tai_lieu.resolution
    assert "BÍ MẬT" not in tai_lieu.resolution
    for lo in ("Cường", "0987654321", "mai.nguyen@", "Mai Nguyễn"):
        assert lo not in tai_lieu.resolution + tai_lieu.description


@pytest.fixture
def chi_muc(session, canh, nhung_gia):
    """Ba hồ sơ đã đóng đạt trong chỉ mục, nhúng qua máy chủ giả."""
    cac = {
        "may-chieu": _dung_ho_so(session, "Máy chiếu phòng họp không lên hình", "Cắm cáp HDMI vào laptop nhưng máy chiếu báo không có tín hiệu", [canh["xong"], canh["dat"]], "Đổi cáp HDMI mới và chọn nguồn vào HDMI2."),
        "mat-khau": _dung_ho_so(session, "Quên mật khẩu phần mềm kế toán", "Đăng nhập phần mềm kế toán báo sai mật khẩu nhiều lần, tài khoản bị khóa", [canh["xong"], canh["dat"]], "Mở khóa tài khoản và đặt lại mật khẩu tạm."),
        "giay-xac-nhan": _dung_ho_so(session, "Xin giấy xác nhận công tác", "Cần giấy xác nhận đang công tác để làm hồ sơ vay ngân hàng", [canh["xong"], canh["dat"]], "Phòng nhân sự cấp giấy xác nhận có dấu đỏ."),
    }
    session.commit()
    can = tuong_tu.ho_so_can_lap(session, 100_000)
    tuong_tu.lap_chi_muc(
        [(ma, luc) for ma, luc in can if ma in {h.id for h in cac.values()}],
        mo_phien=lambda: contextlib.nullcontext(session),
    )
    return cac


def test_tim_hop_so_dung_dung_dau(session, chi_muc):
    ket_qua = tuong_tu.tim(session, "máy chiếu không có tín hiệu", "cắm HDMI vào laptop không lên hình")
    assert ket_qua and ket_qua[0].case_id == chi_muc["may-chieu"].id
    assert "cáp HDMI" in ket_qua[0].resolution
    assert len(ket_qua) <= 3


def test_da_lap_thi_khong_lap_lai(session, chi_muc):
    can = {ma for ma, _ in tuong_tu.ho_so_can_lap(session, 100_000)}
    assert not (can & {h.id for h in chi_muc.values()})


def test_ho_so_mo_lai_khong_con_duoc_goi_y(session, chi_muc, canh):
    ho_so = chi_muc["may-chieu"]
    session.execute(update(Request).where(Request.id == ho_so.id).values(current_state=canh["xong"].from_state))
    session.commit()
    ket_qua = tuong_tu.tim(session, "máy chiếu không có tín hiệu", "cắm HDMI")
    assert ho_so.id not in [k.case_id for k in ket_qua]


# ---------------------------------------------------------------------------
# Điểm cuối của biểu mẫu
# ---------------------------------------------------------------------------


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: NGUOI_GUI
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _tim(client, phien=None):
    return client.post(
        "/similar-cases/search",
        json={"title": "Máy chiếu không có tín hiệu", "description": "Cắm HDMI vào laptop không lên hình", "session_id": str(phien) if phien else None},
    )


def test_mo_hinh_tat_thi_bieu_mau_khong_hien_gi(client, monkeypatch):
    dat_cau_hinh(monkeypatch, embedding_url="")
    tra = _tim(client)
    assert tra.status_code == 200
    # Từ #321 phản hồi có thêm phần bài kho tri thức, rỗng khi tắt
    assert tra.json() == {"items": [], "articles": [], "articles_source_url": None, "enabled": False}


def test_cong_dong_thi_rong_khong_loi(client, monkeypatch):
    dat_cau_hinh(monkeypatch, embedding_url=_cong_dong(), similar_timeout_seconds=HAN_CHOT)
    tra = _tim(client)
    assert tra.status_code == 200 and tra.json()["items"] == []


def test_cham_hon_han_chot_thi_rong_dung_han(client, chi_muc, nhung_gia):
    nhung_gia.cham = HAN_CHOT * 3
    bat_dau = time.monotonic()
    tra = _tim(client)
    assert time.monotonic() - bat_dau < HAN_CHOT + 1.0
    assert tra.status_code == 200 and tra.json()["items"] == []


def test_xem_roi_gui_thi_khong_tinh_ngan_chan(client, session, chi_muc):
    phien = uuid.uuid4()
    tra = _tim(client, phien)
    assert tra.json()["items"], tra.json()
    dong = session.execute(text("SELECT top_case_id, submitted_case_id FROM similar_case_views WHERE session_id = :p"), {"p": phien}).one()
    assert dong[0] == chi_muc["may-chieu"].id and dong[1] is None
    # Không lộ mã hồ sơ hay tên người
    assert "case_id" not in tra.json()["items"][0]

    loai = client.get("/request-types").json()[0]
    gui = client.post(
        "/requests",
        json={
            "title": "Máy chiếu không lên hình",
            "request_type_code": loai["code"],
            "details": chi_tiet_mau(loai),
            "similar_session_id": str(phien),
        },
    )
    assert gui.status_code in (200, 201), gui.text
    dong = session.execute(text("SELECT submitted_case_id, abandoned_at FROM similar_case_views WHERE session_id = :p"), {"p": phien}).one()
    assert dong[0] == gui.json()["id"] and dong[1] is None


def test_bam_khong_gui_nua_la_ngan_chan(client, session, chi_muc):
    phien = uuid.uuid4()
    _tim(client, phien)
    assert client.post("/similar-cases/abandon", json={"session_id": str(phien)}).status_code == 204
    dong = session.execute(text("SELECT ket_qua, so_ngan_chan, ma_phong FROM bao_cao_ngan_chan WHERE ma_phien = :p"), {"p": phien}).one()
    assert dong[0] == "Bỏ không gửi" and dong[1] == 1


def test_qua_han_khong_gui_la_ngan_chan(session, chi_muc, monkeypatch):
    phien = uuid.uuid4()
    tuong_tu.ghi_da_xem(session, phien, NGUOI_GUI.id, tuong_tu.tim(session, "máy chiếu", "HDMI không tín hiệu"))
    session.execute(text("UPDATE similar_case_views SET viewed_at = now() - interval '2 hours' WHERE session_id = :p"), {"p": phien})
    dat_cau_hinh(monkeypatch, similar_abandon_after_minutes=30)
    assert tuong_tu.danh_dau_bo_khong_gui(session) >= 1
    ly_do = session.execute(text("SELECT abandon_reason FROM similar_case_views WHERE session_id = :p"), {"p": phien}).scalar_one()
    assert ly_do == tuong_tu.BO_HET_GIO


def test_phien_cua_nguoi_khac_khong_bi_dung(session, chi_muc):
    phien = uuid.uuid4()
    tuong_tu.ghi_da_xem(session, phien, NGUOI_GUI.id, tuong_tu.tim(session, "máy chiếu", "HDMI"))
    assert tuong_tu.ghi_bo_khong_gui(session, phien, "nguoi-khac") is False
    tuong_tu.ghi_da_gui(session, phien, "nguoi-khac", chi_muc["mat-khau"].id)
    dong = session.execute(text("SELECT submitted_case_id, abandoned_at FROM similar_case_views WHERE session_id = :p"), {"p": phien}).one()
    assert dong == (None, None)


def test_quet_khi_mo_hinh_tat_van_danh_dau_bo_khong_gui_va_khong_lap(session, monkeypatch):
    dat_cau_hinh(monkeypatch, embedding_url="")
    assert tuong_tu.quet_chi_muc(session) == 0
