# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử khuyến nghị cải tiến bằng câu chữ (#320).
#
#   1. Con số bịa bị loại: câu có số không tra được trong bảng dữ kiện (dựng từ kết quả khai phá) bị bỏ;
#      câu dẫn đúng số — viết kiểu Việt Nam: dấu chấm nghìn, dấu phẩy thập phân, %, giờ/phút — được giữ.
#   2. Mô hình tắt: điểm cuối báo `disabled` ngay, kết quả khai phá (nguồn của câu kết luận tất định)
#      vẫn trả đủ. Mô hình không tới được: `unavailable`, không lỗi.
#   3. Không chờ và không hỏi lại: lần đầu `pending`, sinh ở nền; cùng dữ liệu thì lấy bộ nhớ đệm, dữ
#      liệu đổi thì sinh lại.
#
# Mô hình được thay bằng máy chủ HTTP nhỏ kiểu OpenAI dựng ngay trong bài; dịch vụ khai phá bằng bản giả.

from __future__ import annotations

import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient

from app.analytics.khai_pha import khai_pha_client
from app.auth.dependencies import current_actor, current_claims
from app.config import Settings
from app.db import get_session
from app.intelligence import khuyen_nghi, mo_hinh
from app.main import app
from app.workflow.context import Actor

TU, DEN = "2026-10-01", "2026-10-31"

# Kết quả khai phá mẫu theo hợp đồng mục 6.4 — mã và nhãn đặt riêng cho bài, không phải của bộ quy tắc
KET_QUA = {
    "range": {"from": TU, "to": DEN},
    "departments": None,
    "engine": "gia",
    "cases_count": 1234,
    "events_count": 9000,
    "groups": {"request_types": [{"code": "loai-a", "cases_count": 800}],
               "departments": [{"code": "phong-a", "cases_count": 700}, {"code": "phong-b", "cases_count": 534}]},
    "states": [
        {"code": "tt-cho", "label": "Chờ bộ phận A", "is_initial": False, "is_terminal": False,
         "visits": 900, "cases": 850, "median_wait_seconds": 32700, "is_bottleneck": True,
         "longest_waits": [], "by_request_type": [],
         "by_department": [{"code": "phong-b", "visits": 400, "median_wait_seconds": 54000}]},
    ],
    "edges": [],
    "designed_main_flow": [],
    "deviations": [
        {"kind": "rework", "cases_count": 52, "ratio": 0.042, "cases": [],
         "by_request_type": [{"code": "loai-a", "cases_count": 40, "ratio": 0.05}], "by_department": []},
        {"kind": "escalation", "cases_count": 0, "ratio": 0.0, "cases": [], "by_request_type": [],
         "by_department": []},
    ],
    "bottlenecks": {"overall_median_wait_seconds": 9600, "factor": 2.0, "threshold_seconds": 19200,
                    "ranking": [{"code": "tt-cho", "label": "Chờ bộ phận A", "median_wait_seconds": 32700,
                                 "visits": 900, "is_bottleneck": True}]},
    "variants": [{"sequence": ["a", "b"], "cases_count": 700, "ratio": 0.567, "cases": []}],
    "other_variants_cases": 0,
}


# ---------------------------------------------------------------------------
# Bảng dữ kiện và phép kiểm số
# ---------------------------------------------------------------------------


def _kq(**them) -> dict:
    return {**json.loads(json.dumps(KET_QUA)), "scope": {"all": True, "departments": []},
            "labels": {"request_types": {"loai-a": "Loại A"},
                       "departments": {"phong-a": "Phòng A", "phong-b": "Phòng B"}},
            "case_codes": {}, **them}


def test_bang_du_kien_viet_so_kieu_viet_nam_va_nhan_tu_ket_qua():
    dong = "\n".join(khuyen_nghi.bang_du_kien(_kq()))
    assert "1.234 hồ sơ được gửi" in dong
    assert "“Chờ bộ phận A”: chờ trung vị 9 giờ 5 phút làm việc" in dong
    assert "gấp 3,4 lần mức chung" in dong
    assert "chậm nhất ở phòng Phòng B (trung vị 15 giờ làm việc)" in dong
    assert "“Trả về làm lại”: 4,2 % hồ sơ (52 hồ sơ)" in dong
    assert "loại Loại A (40 hồ sơ, 5 % hồ sơ của loại đó)" in dong
    # Nhánh không hồ sơ nào không vào bảng
    assert "Leo thang" not in dong


@pytest.mark.parametrize(
    ("chu", "so"),
    [
        ("1.234 hồ sơ", [1234.0]),
        ("4,2 % hồ sơ", [4.2]),
        ("9 giờ 5 phút", [9.0, 5.0]),
        ("gấp 3,4 lần", [3.4]),
        ("tỷ lệ 3.4 lần", [3.4]),
        ("từ 01/10/2026", [1.0, 10.0, 2026.0]),
    ],
)
def test_tach_so_viet_nam(chu, so):
    assert khuyen_nghi.cac_so(chu) == so


def test_so_bia_bi_loai_so_that_duoc_giu():
    du_kien = khuyen_nghi.bang_du_kien(_kq())
    cau = [
        "Nên bổ sung người cho Phòng B vì “Chờ bộ phận A” chờ trung vị 9 giờ 5 phút, gấp 3,4 lần mức chung.",
        "Nên rà lại biểu mẫu Loại A, nơi có 40 hồ sơ bị trả về làm lại.",
        # Số bịa: 27 % không có trong kết quả
        "Có 27 % hồ sơ bị trả về, cần đào tạo lại người xử lý.",
        # Số tự tính: 52 + 40
        "Tổng cộng 92 hồ sơ có vấn đề.",
        # Không dẫn số nào — khuyến nghị không có căn cứ
        "Nên cải tiến quy trình nói chung.",
    ]
    kq = khuyen_nghi.kiem_cau(cau, du_kien, khuyen_nghi.ten_trong_ket_qua(_kq()))
    assert kq.giu == cau[:2]
    assert kq.sai_so == cau[2:4]
    assert kq.khong_so == cau[4:]


def test_so_that_gan_sai_doi_tuong_hay_ghep_hai_dong_bi_loai():
    # Gặp thật trên dữ liệu trình diễn: số có trong kết quả nhưng là của phòng khác, hay ghép số của hai
    # dòng dữ kiện thành một câu "từ … lên …"
    kq_mau = _kq()
    cau = [
        "Phòng A chậm nhất, trung vị 15 giờ làm việc ở “Chờ bộ phận A”.",  # 15 giờ là của Phòng B
        "Nên giảm 52 hồ sơ trả về làm lại xuống còn 57 %.",  # 52 và 57 ở hai dòng khác nhau
        "Trạng thái “Chờ bộ phận A” có 9 hồ sơ chờ lâu.",  # 9 là "9 giờ", không phải 9 hồ sơ
        "Phòng B chậm nhất ở “Chờ bộ phận A”, trung vị 15 giờ làm việc, nên bổ sung người.",
    ]
    kq = khuyen_nghi.kiem_cau(cau, khuyen_nghi.bang_du_kien(kq_mau), khuyen_nghi.ten_trong_ket_qua(kq_mau))
    assert kq.sai_so == cau[:3]
    assert kq.giu == cau[3:]


def test_so_thu_tu_dau_muc_khong_thanh_cau_khong_thanh_so():
    assert khuyen_nghi.tach_cau("1. Nên rà lại biểu mẫu, 40 hồ sơ bị trả về. 2. Nên bổ sung người. 3.") == [
        "Nên rà lại biểu mẫu, 40 hồ sơ bị trả về.",
        "Nên bổ sung người.",
    ]


def test_gan_trang_thai_thanh_phong_hay_nhac_sai_vai_bi_loai():
    # Hai câu mô hình thật viết trên cụm trình diễn (#557): số đúng, đối tượng sai — trạng thái gọi là "phòng",
    # và nhắc người gửi ở trạng thái không chờ người gửi. Vai đi bước tiếp đọc từ `turns` (bộ quy tắc)
    kq_mau = _kq(turns={"tt-cho": ["approver"]}, role_labels={"approver": "Người xét duyệt yêu cầu"})
    du_kien = khuyen_nghi.bang_du_kien(kq_mau)
    tho = [
        {"dong": 1, "viec": "Nên bổ sung người xử lý cho phòng 'Chờ bộ phận A'."},
        {"dong": 1, "viec": "Nên nhắc người gửi bổ sung thông tin sớm."},
        {"dong": 1, "viec": "Nên nhắc trưởng phòng xét duyệt hồ sơ ở 'Chờ bộ phận A' trong ngày."},
    ]
    kiem = khuyen_nghi.dung_cau(tho, du_kien, khuyen_nghi.ten_trong_ket_qua(kq_mau), kq_mau)
    assert kiem.sai_so == [tho[0]["viec"], tho[1]["viec"]]
    assert len(kiem.giu) == 1
    # Ngoặc đơn thẳng thành ngoặc kép như dòng căn cứ
    assert kiem.giu[0].startswith("Nên nhắc trưởng phòng xét duyệt hồ sơ ở “Chờ bộ phận A” trong ngày — căn cứ:")

    # Không có thông tin lượt (trạng thái không có bước chính): không kiểm vai, vẫn bắt trạng thái gọi là phòng
    kiem = khuyen_nghi.dung_cau(tho, du_kien, khuyen_nghi.ten_trong_ket_qua(_kq()), _kq())
    assert kiem.sai_so == [tho[0]["viec"]]


def test_loi_dan_ghi_ai_di_buoc_tiep():
    kq_mau = _kq(turns={"tt-cho": ["approver"]}, role_labels={})
    van_de = [d for d in khuyen_nghi.bang_du_kien(kq_mau) if d.startswith(khuyen_nghi.TIEN_TO_VAN_DE)]
    assert khuyen_nghi.ai_di_tiep(van_de, kq_mau) == ["Trạng thái “Chờ bộ phận A”: trưởng phòng."]
    assert khuyen_nghi.ai_di_tiep(van_de, _kq()) == []


# ---------------------------------------------------------------------------
# Điểm cuối, mô hình giả
# ---------------------------------------------------------------------------


class MoHinhGia:
    """Máy chủ `/v1/chat/completions` kiểu OpenAI trả đúng đối tượng `tra_loi`."""

    def __init__(self) -> None:
        self.tra_loi: dict = {"khuyen_nghi": []}
        self.so_lan = 0
        self.da_hoi: list[dict] = []
        gia = self

        class XuLy(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                than = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                gia.so_lan += 1
                gia.da_hoi.append(than)
                ra = json.dumps({"choices": [{"message": {"content": json.dumps(gia.tra_loi)}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(ra)))
                self.end_headers()
                self.wfile.write(ra)

            def log_message(self, *a):
                pass

        self.may_chu = HTTPServer(("127.0.0.1", 0), XuLy)
        self.url = f"http://127.0.0.1:{self.may_chu.server_address[1]}"


class KhaiPhaGia:
    def __init__(self) -> None:
        self.ket_qua = json.loads(json.dumps(KET_QUA))

    def khai_pha(self, tu, den, phong):
        return self.ket_qua


def dat_cau_hinh(monkeypatch, **gia_tri) -> Settings:
    cau_hinh = Settings(**{"recommendation_timeout_seconds": 3.0, **gia_tri})
    for tep in (mo_hinh, khuyen_nghi):
        monkeypatch.setattr(tep, "get_settings", lambda: cau_hinh)
    return cau_hinh


@pytest.fixture
def mo_hinh_gia(monkeypatch):
    gia = MoHinhGia()
    luong = threading.Thread(target=gia.may_chu.serve_forever, daemon=True)
    luong.start()
    dat_cau_hinh(monkeypatch, llm_url=gia.url)
    try:
        yield gia
    finally:
        gia.may_chu.shutdown()
        gia.may_chu.server_close()


@pytest.fixture
def client(session):
    khuyen_nghi.xoa_dem()
    gia = KhaiPhaGia()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: Actor(id="dp-320", roles=frozenset({"classifier"}))
    app.dependency_overrides[current_claims] = lambda: {}
    app.dependency_overrides[khai_pha_client] = lambda: gia
    with TestClient(app) as c:
        c.gia = gia
        yield c
    app.dependency_overrides.clear()
    khuyen_nghi.xoa_dem()


def _hoi(client):
    return client.get("/analytics/process-mining/recommendation", params={"from": TU, "to": DEN})


def _cho_xong(client, han: float = 5.0) -> dict:
    het = time.monotonic() + han
    while True:
        tra = _hoi(client)
        assert tra.status_code == 200, tra.text
        if tra.json()["status"] != khuyen_nghi.DANG_SINH or time.monotonic() > het:
            return tra.json()
        time.sleep(0.05)


def test_mo_hinh_tat_thi_disabled_va_ket_qua_khai_pha_van_du(client, monkeypatch):
    dat_cau_hinh(monkeypatch, llm_url="")
    tra = _hoi(client)
    assert tra.status_code == 200
    assert tra.json()["status"] == khuyen_nghi.TAT and tra.json()["sentences"] == []
    # Câu kết luận tất định dựng từ kết quả khai phá — nguồn đó không phụ thuộc mô hình
    kp = client.get("/analytics/process-mining", params={"from": TU, "to": DEN})
    assert kp.status_code == 200 and kp.json()["cases_count"] == 1234


def test_cong_dong_thi_unavailable_khong_loi(client, monkeypatch):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        cong = s.getsockname()[1]
    dat_cau_hinh(monkeypatch, llm_url=f"http://127.0.0.1:{cong}")
    assert _cho_xong(client)["status"] == khuyen_nghi.KHONG_PHAN_HOI


def test_sinh_o_nen_loai_cau_sai_so_va_dung_bo_nho_dem(client, mo_hinh_gia):
    # Vấn đề [1] là trạng thái “Chờ bộ phận A”, [2] là nhánh trả về làm lại
    mo_hinh_gia.tra_loi = {"khuyen_nghi": [
        {"dong": 1, "viec": "1. Nên bổ sung người xử lý cho Phòng B."},
        {"dong": 2, "viec": "Nên rà lại biểu mẫu vì 27 % hồ sơ bị trả về."},  # số bịa
        {"dong": 2, "viec": "Nên giảm hồ sơ Leo thang do quá hạn."},  # nhánh không thuộc dòng 2
        {"dong": 9, "viec": "Nên làm gì đó."},  # không có vấn đề số 9
    ]}
    dau = _hoi(client).json()
    assert dau["status"] == khuyen_nghi.DANG_SINH  # không chờ mô hình

    xong = _cho_xong(client)
    assert xong["status"] == khuyen_nghi.SAN_SANG
    assert len(xong["sentences"]) == 1
    cau = xong["sentences"][0]
    # Việc do mô hình viết, căn cứ kèm số là dòng dữ kiện của hệ thống
    assert cau.startswith("Nên bổ sung người xử lý cho Phòng B — căn cứ: trạng thái “Chờ bộ phận A”")
    assert "9 giờ 5 phút làm việc, gấp 3,4 lần mức chung" in cau
    assert xong["dropped_wrong_number"] == 2
    assert xong["dropped_no_number"] == 1
    # Mô hình chỉ thấy bảng dữ kiện dựng từ kết quả khai phá, có lược đồ ràng buộc
    hoi = mo_hinh_gia.da_hoi[0]
    assert "1.234 hồ sơ" in hoi["messages"][1]["content"]
    assert hoi["response_format"]["json_schema"]["name"] == "khuyen_nghi"

    # Mở lại màn với cùng dữ liệu: bộ nhớ đệm, không hỏi mô hình lần nữa
    lai = _hoi(client).json()
    assert lai["cached"] is True and lai["sentences"] == xong["sentences"]
    assert mo_hinh_gia.so_lan == 1

    # Có hồ sơ mới làm số đổi: sinh lại, không nói số cũ
    client.gia.ket_qua["cases_count"] = 1300
    assert _hoi(client).json()["status"] == khuyen_nghi.DANG_SINH
    _cho_xong(client)
    assert mo_hinh_gia.so_lan == 2


def test_khong_co_ho_so_thi_khong_hoi_mo_hinh(client, mo_hinh_gia):
    client.gia.ket_qua["cases_count"] = 0
    assert _hoi(client).json()["status"] == khuyen_nghi.KHONG_DU_LIEU
    assert mo_hinh_gia.so_lan == 0


def test_nguoi_gui_khong_hoi_duoc(client):
    app.dependency_overrides[current_actor] = lambda: Actor(id="ng-320", roles=frozenset({"requester"}))
    assert _hoi(client).status_code == 403
