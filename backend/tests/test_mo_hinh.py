# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử lớp gọi mô hình ngôn ngữ (#316, ADR-0008) — `app/intelligence/mo_hinh.py`.
#
# Điều phải đúng:
#
#   1. Mô hình tắt (địa chỉ rỗng), cổng đóng, trả chậm hơn hạn chót, JSON sai, mã ngoài danh mục
#      → "không có gợi ý" (`None`), và luôn TRONG hạn chót — không lỗi nào nổi lên phía gọi.
#   2. Lược đồ JSON gửi kèm đặt `enum` bằng mã danh mục ĐANG BẬT, đọc từ bảng lúc gọi: tắt một loại
#      trong bảng thì lời gọi sau không còn mã đó.
#   3. Tình trạng cho màn Hệ thống: tắt / sẵn sàng / không phản hồi.
#
# Mô hình là một máy chủ HTTP giả trong bài (khuôn `test_khai_pha_cong.py`) — CI không tải mô hình.
# Đáp án tra từ bảng của dữ liệu khởi tạo, không chép mã nghiệp vụ vào đây.

from __future__ import annotations

import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from sqlalchemy import select, update

from app.config import Settings
from app.intelligence import mo_hinh
from app.models.workflow_config import Department, Priority, RequestType
from app.workflow.engine import create_case

HAN_CHOT = 1.0


class MoHinhGia:
    """Máy chủ kiểu OpenAI giả. `tra_loi(than_yeu_cau)` trả (mã HTTP, thân trả về dạng bytes)."""

    def __init__(self) -> None:
        self.cac_yeu_cau: list[dict] = []
        self.tra_loi = lambda than: (200, b"{}")
        self.cham_giay = 0.0
        self.ma_suc_khoe = 200
        gia = self

        class XuLy(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                than = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                gia.cac_yeu_cau.append(than)
                if gia.cham_giay:
                    time.sleep(gia.cham_giay)
                ma, du_lieu = gia.tra_loi(than)
                self._gui(ma, du_lieu)

            def do_GET(self):  # noqa: N802
                self._gui(gia.ma_suc_khoe, b'{"status":"ok"}')

            def _gui(self, ma: int, du_lieu: bytes) -> None:
                try:
                    self.send_response(ma)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(du_lieu)))
                    self.end_headers()
                    self.wfile.write(du_lieu)
                except (BrokenPipeError, ConnectionResetError):
                    pass  # phía gọi đã bỏ vì quá hạn

            def log_message(self, *a):  # im lặng trong bài kiểm thử
                pass

        self.may_chu = HTTPServer(("127.0.0.1", 0), XuLy)
        self.url = f"http://127.0.0.1:{self.may_chu.server_port}"

    def tra_dap_an(self, dap_an: dict) -> None:
        noi_dung = json.dumps(dap_an, ensure_ascii=False)
        than = {"choices": [{"message": {"role": "assistant", "content": noi_dung}}]}
        self.tra_loi = lambda _: (200, json.dumps(than).encode("utf-8"))


def dat_cau_hinh(monkeypatch, **gia_tri) -> Settings:
    """Cấu hình riêng cho bài: thay `get_settings` ở mọi tệp tầng I đọc nó."""
    cau_hinh = Settings(**gia_tri)
    from app.intelligence import phan_loai

    for tep in (mo_hinh, phan_loai):
        monkeypatch.setattr(tep, "get_settings", lambda: cau_hinh)
    return cau_hinh


@pytest.fixture
def mo_hinh_gia(monkeypatch):
    gia = MoHinhGia()
    luong = threading.Thread(target=gia.may_chu.serve_forever, daemon=True)
    luong.start()
    dat_cau_hinh(monkeypatch, llm_url=gia.url, llm_timeout_seconds=HAN_CHOT)
    try:
        yield gia
    finally:
        gia.may_chu.shutdown()
        gia.may_chu.server_close()


def dap_an_hop_le(session) -> dict:
    """Một câu trả lời đúng lược đồ, mã lấy từ danh mục đang bật của bảng."""
    return {
        "request_type_code": session.scalar(
            select(RequestType.code).where(RequestType.is_active).order_by(RequestType.code.desc())
        ),
        "request_type_reason": "Nhân viên nêu rõ việc cần làm.",
        "priority_code": session.scalar(select(Priority.code).order_by(Priority.display_order.desc())),
        "priority_reason": "Cả phòng đang phải dừng việc.",
        "department_code": session.scalar(
            select(Department.code).where(Department.is_active).order_by(Department.code.desc())
        ),
        "department_reason": "Đúng phần việc của phòng này.",
    }


@pytest.fixture
def ho_so(session, rule_set):
    ma_loai = session.scalar(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    )
    h = create_case(
        session,
        title="Máy chiếu phòng họp tầng 5 không lên hình",
        description="Cắm cáp HDMI vào máy tính thì máy chiếu báo không có tín hiệu.",
        requester_id="nd-gui-316",
        request_type_code=ma_loai,
    )
    session.flush()
    return h


def _cong_dong() -> str:
    """Một cổng trên máy này mà không ai nghe."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        cong = s.getsockname()[1]
    return f"http://127.0.0.1:{cong}"


# ---------------------------------------------------------------------------
# Mọi lỗi thành "không có gợi ý", trong hạn chót
# ---------------------------------------------------------------------------


def test_dia_chi_rong_la_tat_khong_goi_ai(session, ho_so, monkeypatch):
    dat_cau_hinh(monkeypatch, llm_url="")
    assert mo_hinh.goi_y_phan_loai(session, ho_so) is None
    with pytest.raises(mo_hinh.LoiMoHinh) as loi:
        mo_hinh.hoi_phan_loai(mo_hinh.de_bai_cua_ho_so(session, ho_so))
    assert loi.value.ma == mo_hinh.LOI_TAT and loi.value.khong_toi_duoc


def test_cong_dong_la_khong_toi_duoc(session, ho_so, monkeypatch):
    dat_cau_hinh(monkeypatch, llm_url=_cong_dong(), llm_timeout_seconds=HAN_CHOT)
    bat_dau = time.monotonic()
    with pytest.raises(mo_hinh.LoiMoHinh) as loi:
        mo_hinh.hoi_phan_loai(mo_hinh.de_bai_cua_ho_so(session, ho_so))
    assert loi.value.ma == mo_hinh.LOI_KHONG_KET_NOI and loi.value.khong_toi_duoc
    assert mo_hinh.goi_y_phan_loai(session, ho_so) is None
    assert time.monotonic() - bat_dau < 2 * HAN_CHOT + 1


def test_tra_cham_hon_han_chot_thi_bo_dung_han(session, ho_so, mo_hinh_gia):
    mo_hinh_gia.tra_dap_an(dap_an_hop_le(session))
    mo_hinh_gia.cham_giay = HAN_CHOT + 2
    bat_dau = time.monotonic()
    with pytest.raises(mo_hinh.LoiMoHinh) as loi:
        mo_hinh.hoi_phan_loai(mo_hinh.de_bai_cua_ho_so(session, ho_so))
    da_cho = time.monotonic() - bat_dau
    assert loi.value.ma == mo_hinh.LOI_QUA_HAN and not loi.value.khong_toi_duoc
    assert da_cho < HAN_CHOT + 0.8, f"phải bỏ đúng hạn chót, đã chờ {da_cho:.2f} giây"


@pytest.mark.parametrize(
    "noi_dung",
    [
        "đây không phải JSON",
        '{"request_type_code": ',
        "[1, 2, 3]",
        '{"request_type_code": "x"}',
    ],
)
def test_json_sai_la_khong_co_goi_y(session, ho_so, mo_hinh_gia, noi_dung):
    than = {"choices": [{"message": {"content": noi_dung}}]}
    mo_hinh_gia.tra_loi = lambda _: (200, json.dumps(than).encode("utf-8"))
    with pytest.raises(mo_hinh.LoiMoHinh) as loi:
        mo_hinh.hoi_phan_loai(mo_hinh.de_bai_cua_ho_so(session, ho_so))
    assert loi.value.ma in (mo_hinh.LOI_SAI_DINH_DANG, mo_hinh.LOI_NGOAI_DANH_MUC)
    assert mo_hinh.goi_y_phan_loai(session, ho_so) is None


def test_phan_hoi_khong_phai_json_va_loi_may_chu(session, ho_so, mo_hinh_gia):
    mo_hinh_gia.tra_loi = lambda _: (200, b"<html>bad gateway</html>")
    assert mo_hinh.goi_y_phan_loai(session, ho_so) is None
    mo_hinh_gia.tra_loi = lambda _: (500, b'{"error":"oom"}')
    with pytest.raises(mo_hinh.LoiMoHinh) as loi:
        mo_hinh.hoi_phan_loai(mo_hinh.de_bai_cua_ho_so(session, ho_so))
    assert loi.value.ma == mo_hinh.LOI_MAY_CHU


@pytest.mark.parametrize("truong", list(mo_hinh.CAC_TRUONG))
def test_ma_ngoai_danh_muc_bi_chan_du_may_chu_bo_qua_luoc_do(session, ho_so, mo_hinh_gia, truong):
    dap_an = dap_an_hop_le(session)
    dap_an[truong] = "ma-khong-co-trong-bang"
    mo_hinh_gia.tra_dap_an(dap_an)
    with pytest.raises(mo_hinh.LoiMoHinh) as loi:
        mo_hinh.hoi_phan_loai(mo_hinh.de_bai_cua_ho_so(session, ho_so))
    assert loi.value.ma == mo_hinh.LOI_NGOAI_DANH_MUC
    assert mo_hinh.goi_y_phan_loai(session, ho_so) is None


# ---------------------------------------------------------------------------
# Đường thành công và lược đồ ràng buộc
# ---------------------------------------------------------------------------


def test_tra_loi_hop_le_cho_ba_ma_va_ly_do(session, ho_so, mo_hinh_gia):
    dap_an = dap_an_hop_le(session)
    mo_hinh_gia.tra_dap_an(dap_an)

    ket_qua = mo_hinh.goi_y_phan_loai(session, ho_so)

    assert ket_qua is not None
    for truong in mo_hinh.CAC_TRUONG:
        assert ket_qua.ma(truong) == dap_an[truong]
    assert ket_qua.reasons["priority_code"] == dap_an["priority_reason"]
    assert ket_qua.elapsed_ms >= 0


def test_luoc_do_gui_kem_la_danh_muc_dang_bat_doc_tu_bang(session, ho_so, mo_hinh_gia):
    mo_hinh_gia.tra_dap_an(dap_an_hop_le(session))
    mo_hinh.goi_y_phan_loai(session, ho_so)

    than = mo_hinh_gia.cac_yeu_cau[-1]
    assert than["response_format"]["type"] == "json_schema"
    luoc_do = than["response_format"]["json_schema"]["schema"]
    loai_bat = set(session.scalars(select(RequestType.code).where(RequestType.is_active)))
    assert set(luoc_do["properties"]["request_type_code"]["enum"]) == loai_bat
    assert set(luoc_do["properties"]["priority_code"]["enum"]) == set(
        session.scalars(select(Priority.code))
    )
    assert set(luoc_do["properties"]["department_code"]["enum"]) == set(
        session.scalars(select(Department.code).where(Department.is_active))
    )
    # Nội dung hồ sơ có trong lời gọi; nhãn danh mục đến từ bảng
    toan_bo = json.dumps(than["messages"], ensure_ascii=False)
    assert ho_so.title in toan_bo
    for nhan in session.scalars(select(RequestType.label).where(RequestType.is_active)):
        assert nhan in toan_bo

    # Tắt một loại trong bảng: lời gọi kế tiếp không còn mã đó
    tat = sorted(loai_bat)[-1]
    session.execute(update(RequestType).where(RequestType.code == tat).values(is_active=False))
    session.flush()
    mo_hinh_gia.tra_dap_an({**dap_an_hop_le(session)})
    mo_hinh.goi_y_phan_loai(session, ho_so)
    enum_moi = mo_hinh_gia.cac_yeu_cau[-1]["response_format"]["json_schema"]["schema"][
        "properties"
    ]["request_type_code"]["enum"]
    assert tat not in enum_moi


# ---------------------------------------------------------------------------
# Tình trạng cho màn Hệ thống
# ---------------------------------------------------------------------------


def test_tinh_trang_tat_san_sang_khong_phan_hoi(monkeypatch, mo_hinh_gia):
    assert mo_hinh.tinh_trang()["status"] == mo_hinh.SAN_SANG

    mo_hinh_gia.ma_suc_khoe = 503  # llama.cpp đang nạp mô hình
    tt = mo_hinh.tinh_trang()
    assert tt["status"] == mo_hinh.KHONG_PHAN_HOI and "nạp" in tt["detail"]

    dat_cau_hinh(monkeypatch, llm_url=_cong_dong(), llm_health_timeout_seconds=1.0)
    assert mo_hinh.tinh_trang()["status"] == mo_hinh.KHONG_PHAN_HOI

    dat_cau_hinh(monkeypatch, llm_url="")
    assert mo_hinh.tinh_trang()["status"] == mo_hinh.TAT
