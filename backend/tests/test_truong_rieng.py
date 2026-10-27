# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Trường thông tin riêng theo loại yêu cầu (#250).
#
# Khai báo nằm trong bảng `request_type_fields`; các bài dưới dùng bộ mẫu của dữ liệu khởi tạo
# (Sự cố thiết bị: Mã tài sản*, Vị trí*, Mức ảnh hưởng; Đề xuất mua vật tư: Tên vật tư*, Số
# lượng*, Dự toán, Nhà cung cấp gợi ý). Bài "đổi khai báo" thêm một dòng ngay trong giao dịch
# của bài để chứng minh biểu mẫu, phép kiểm và trang hồ sơ đi theo dữ liệu, không theo mã.

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.dependencies import current_actor
from app.db import get_session
from app.main import app
from app.models.case import EventLog, Request
from app.models.workflow_config import Priority, RequestTypeField
from app.workflow.context import Actor
from app.workflow.engine import create_case, perform_transition
from app.workflow.errors import GuardViolation, InvalidFieldValue

NGUOI_GUI = Actor(id="tr-gui-01", name="An Nguyễn", roles=frozenset({"requester"}))
DIEU_PHOI = Actor(id="tr-dp-01", name="Bình Trần", roles=frozenset({"classifier"}))

THIET_BI = "device-incident"
VAT_TU = "supply-purchase"
DU_THIET_BI = {"ma-tai-san": "LT-0042", "vi-tri": "Tầng 3"}


def _tao(session, loai: str = THIET_BI, chi_tiet: dict | None = None) -> Request:
    return create_case(
        session, title="Máy in tầng ba kẹt giấy", requester_id=NGUOI_GUI.id,
        requester_label=NGUOI_GUI.label, request_type_code=loai,
        details=DU_THIET_BI if chi_tiet is None else chi_tiet,
    )


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: NGUOI_GUI
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# --- Kiểm theo khai báo ---------------------------------------------------------------


def test_luu_ban_chuan_hoa(session, rule_set):
    ho_so = _tao(session, VAT_TU, {"ten-vat-tu": "  Giấy A4  ", "so-luong": "20", "du-toan": "1500000",
                                   "nha-cung-cap": ""})
    assert ho_so.details == {"ten-vat-tu": "Giấy A4", "so-luong": 20, "du-toan": 1500000}


def test_thieu_truong_bat_buoc_bi_tu_choi(session, rule_set):
    with pytest.raises(InvalidFieldValue, match="Chưa điền Vị trí"):
        _tao(session, chi_tiet={"ma-tai-san": "LT-0042"})


@pytest.mark.parametrize(
    ("chi_tiet", "cau"),
    [
        ({"ten-vat-tu": "Giấy", "so-luong": "hai mươi"}, "Số lượng phải là một số"),
        ({"ten-vat-tu": "Giấy", "so-luong": -3}, "không âm"),
        ({"ten-vat-tu": "Giấy", "so-luong": 2, "khong-co": "x"}, "không có trường"),
    ],
)
def test_sai_kieu_hay_truong_la_bi_tu_choi(session, rule_set, chi_tiet, cau):
    with pytest.raises(InvalidFieldValue, match=cau):
        _tao(session, VAT_TU, chi_tiet)


def test_lua_chon_ngoai_danh_sach_bi_tu_choi(session, rule_set):
    with pytest.raises(InvalidFieldValue, match="Mức ảnh hưởng chỉ nhận một trong"):
        _tao(session, chi_tiet={**DU_THIET_BI, "muc-anh-huong": "Cả tòa nhà"})


# --- Đi theo dữ liệu, không theo mã ----------------------------------------------------


def test_them_truong_bang_du_lieu_thi_kiem_va_hien_theo(session, rule_set, client):
    session.add(RequestTypeField(request_type_code=THIET_BI, code="so-may", label="Số máy",
                                 kind="number", required=True, display_order=9))
    session.flush()

    with pytest.raises(InvalidFieldValue, match="Chưa điền Số máy"):
        _tao(session)
    ho_so = _tao(session, chi_tiet={**DU_THIET_BI, "so-may": 3})

    cac_loai = {l["code"]: l for l in client.get("/request-types").json()}
    assert "so-may" in [t["code"] for t in cac_loai[THIET_BI]["fields"]], "biểu mẫu có trường mới"
    chi_tiet = client.get(f"/requests/{ho_so.id}").json()
    assert chi_tiet["details"]["so-may"] == 3
    assert "Số máy" in [t["label"] for t in chi_tiet["detail_fields"]], "trang hồ sơ có nhãn mới"


# --- Sửa nội dung: nhật ký giữ giá trị cũ và mới ----------------------------------------


def test_sua_truong_rieng_ghi_nhat_ky(session, rule_set):
    ho_so = _tao(session)
    moi = {**DU_THIET_BI, "vi-tri": "Tầng 5, phòng họp lớn"}
    perform_transition(session, case_id=ho_so.id, to_state="submitted", actor=NGUOI_GUI,
                       changes={"details": moi})

    assert ho_so.details["vi-tri"] == "Tầng 5, phòng họp lớn"
    dong = session.scalars(
        select(EventLog).where(EventLog.case_id == ho_so.id).order_by(EventLog.id.desc())
    ).first()
    assert "details" in dong.changes, "nhật ký ghi phần từ → sang của trường riêng"
    assert dong.changes["details"]["from"]["vi-tri"] == "Tầng 3"


def test_sua_sai_kieu_bi_tu_choi_bang_tieng_viet(session, rule_set):
    ho_so = _tao(session)
    with pytest.raises(GuardViolation, match="Chưa điền Mã tài sản"):
        perform_transition(session, case_id=ho_so.id, to_state="submitted", actor=NGUOI_GUI,
                           changes={"details": {"vi-tri": "Tầng 3"}})


def test_nguoi_gui_doi_loai_phai_dien_truong_cua_loai_moi(session, rule_set):
    ho_so = _tao(session)
    with pytest.raises(GuardViolation, match="Chưa điền Tên vật tư"):
        perform_transition(session, case_id=ho_so.id, to_state="submitted", actor=NGUOI_GUI,
                           changes={"request_type_code": VAT_TU})


def test_dieu_phoi_doi_loai_khong_bi_chan(session, rule_set):
    """Điều phối đổi loại lúc phân loại: không chặn, trang hồ sơ hiện trường thiếu là chưa có."""
    ho_so = _tao(session)
    uu_tien = session.scalars(select(Priority.code).order_by(Priority.display_order)).first()
    perform_transition(session, case_id=ho_so.id, to_state="classified", actor=DIEU_PHOI,
                       changes={"priority_code": uu_tien, "request_type_code": VAT_TU})
    assert ho_so.request_type_code == VAT_TU


# --- Qua điểm cuối ----------------------------------------------------------------------


def test_gui_yeu_cau_thieu_truong_tra_422_tieng_viet(client, rule_set):
    phan_hoi = client.post("/requests", json={"title": "Máy in tầng ba kẹt giấy",
                                              "request_type_code": THIET_BI,
                                              "details": {"ma-tai-san": "LT-0042"}})
    assert phan_hoi.status_code == 422
    assert "Chưa điền Vị trí" in phan_hoi.json()["detail"]["message"]

    phan_hoi = client.post("/requests", json={"title": "Máy in tầng ba kẹt giấy",
                                              "request_type_code": THIET_BI, "details": DU_THIET_BI})
    assert phan_hoi.status_code in (200, 201)
    assert phan_hoi.json()["details"] == DU_THIET_BI


def test_dong_thoi_gian_ke_truong_rieng_bang_nhan(client, session, rule_set):
    ho_so = _tao(session)
    perform_transition(session, case_id=ho_so.id, to_state="submitted", actor=NGUOI_GUI,
                       changes={"details": {**DU_THIET_BI, "vi-tri": "Tầng 5"}})
    lich_su = client.get(f"/requests/{ho_so.id}").json()["history"]
    thay = [t for e in lich_su for t in e["changes"] if t["field"] == "details"]
    assert thay and "Vị trí: Tầng 5" in thay[0]["after"]["label"]
    assert "Vị trí: Tầng 3" in thay[0]["before"]["label"]
