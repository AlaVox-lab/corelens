# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử liên hệ người gửi trên hai buồng lái (#131).
#
# Ba lớp, theo thứ tự:
#
#   1. Cửa: chỉ người mở được hồ sơ mới tra được liên hệ, và cửa chặn TRƯỚC khi hỏi
#      danh bạ — người phòng khác không làm Keycloak lộ ra điều gì, kể cả hồ sơ có thật.
#   2. Đọc thuộc tính: phần dịch hồ sơ người dùng của Keycloak thành email và số điện
#      thoại, kiểm bằng cách thay lớp gọi mạng.
#   3. Keycloak thật: tài khoản dịch vụ đọc được thuộc tính khai trong user profile.

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.dependencies import current_actor
from app.auth.directory import Contact, DirectoryUnavailable, KeycloakDirectory, get_directory
from app.db import get_session
from app.main import app
from app.models.case import Request
from app.models.workflow_config import Department, Priority, RequestType
from app.workflow.context import Actor
from app.workflow.coordination import VAI_TRO_DIEU_PHOI
from app.workflow.engine import create_case, perform_transition

NGUOI_GUI = Actor(id="kc-gui-131", name="An Nguyễn", roles=frozenset({"requester"}))
NGUOI_GUI_KHAC = Actor(id="kc-gui-132", name="Người Gửi Khác", roles=frozenset({"requester"}))
DIEU_PHOI = Actor(id="kc-dp-131", name="Bình Trần", roles=frozenset({VAI_TRO_DIEU_PHOI}))

LIEN_HE = Contact(email="an.nguyen@dx-os-lab.test", phone="0900 000 001")


def _truong_phong(phong: str) -> Actor:
    return Actor(id="kc-tp-131", name="Dung Phạm", roles=frozenset({"approver"}),
                 departments=frozenset({phong}))


def _xu_ly(phong: str) -> Actor:
    return Actor(id="kc-xl-131", name="Cường Lê", roles=frozenset({"handler"}),
                 departments=frozenset({phong}))


class DanhBaGia:
    """Thay Keycloak. Ghi lại đã bị hỏi ai, để kiểm cửa chặn TRƯỚC khi hỏi."""

    def __init__(self, lien_he: Contact | None = LIEN_HE, loi: str | None = None):
        self.lien_he = lien_he
        self.loi = loi
        self.da_hoi: list[str] = []

    def contact(self, user_id: str) -> Contact | None:
        self.da_hoi.append(user_id)
        if self.loi:
            raise DirectoryUnavailable(self.loi)
        return self.lien_he

    def department_members(self, department_code: str) -> list:
        return []


@pytest.fixture
def phong_khac(session, phong_ban) -> str:
    ma = session.scalars(
        select(Department.code)
        .where(Department.is_active, Department.code != phong_ban)
        .order_by(Department.display_order)
    ).first()
    if ma is None:
        pytest.skip("Cần ít nhất hai phòng ban đang hoạt động.")
    return ma


@pytest.fixture
def client(session):
    """Máy khách HTTP đổi được người gọi và danh bạ.

    Phần dựng cảnh phải `commit`, không dừng ở `flush` — lý do ở fixture cùng tên trong
    test_routes.py.
    """
    trang_thai = {"actor": DIEU_PHOI, "danh_ba": DanhBaGia()}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: trang_thai["actor"]
    app.dependency_overrides[get_directory] = lambda: trang_thai["danh_ba"]
    with TestClient(app) as c:
        c.trang_thai = trang_thai
        yield c
    app.dependency_overrides.clear()


def _goi_bang(client, actor: Actor, danh_ba: DanhBaGia | None = None) -> DanhBaGia:
    client.trang_thai["actor"] = actor
    if danh_ba is not None:
        client.trang_thai["danh_ba"] = danh_ba
    return client.trang_thai["danh_ba"]


def _cho_phong_nhan(session, phong: str) -> Request:
    """Hồ sơ của An Nguyễn đang nằm ở phòng `phong`, chờ phòng nhận — qua đúng các cạnh."""
    loai = session.scalars(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    ho_so = create_case(
        session, title="Máy in tầng ba kẹt giấy", requester_id=NGUOI_GUI.id,
        requester_label=NGUOI_GUI.label, request_type_code=loai,
    )
    uu_tien = session.scalars(select(Priority.code).order_by(Priority.display_order)).first()
    perform_transition(session, case_id=ho_so.id, to_state="classified", actor=DIEU_PHOI,
                       changes={"priority_code": uu_tien})
    perform_transition(session, case_id=ho_so.id, to_state="awaiting-acceptance",
                       actor=DIEU_PHOI, changes={"department_code": phong})
    session.commit()
    return ho_so


def _dieu_phoi(ho_so: Request) -> str:
    return f"/coordination/requests/{ho_so.id}/requester-contact"


def _phong_ban(ho_so: Request) -> str:
    return f"/department/requests/{ho_so.id}/requester-contact"


# ---------------------------------------------------------------------------
# Cửa
# ---------------------------------------------------------------------------


def test_dieu_phoi_thay_lien_he_nguoi_gui(client, session, phong_ban):
    ho_so = _cho_phong_nhan(session, phong_ban)
    danh_ba = _goi_bang(client, DIEU_PHOI)

    r = client.get(_dieu_phoi(ho_so))

    assert r.status_code == 200
    assert r.json() == {
        "name": "An Nguyễn",
        "email": "an.nguyen@dx-os-lab.test",
        "phone": "0900 000 001",
        "found": True,
    }
    assert danh_ba.da_hoi == [NGUOI_GUI.id], "tra đúng người gửi, theo sub"


@pytest.mark.parametrize("nguoi", [_truong_phong, _xu_ly], ids=["truong-phong", "xu-ly"])
def test_phong_dang_giu_ho_so_thay_lien_he(client, session, phong_ban, nguoi):
    ho_so = _cho_phong_nhan(session, phong_ban)
    _goi_bang(client, nguoi(phong_ban))

    r = client.get(_phong_ban(ho_so))

    assert r.status_code == 200
    assert r.json()["phone"] == "0900 000 001"


def test_phong_khac_nhan_404_va_danh_ba_khong_bi_hoi(client, session, phong_ban, phong_khac):
    ho_so = _cho_phong_nhan(session, phong_ban)
    danh_ba = _goi_bang(client, _truong_phong(phong_khac))

    r = client.get(_phong_ban(ho_so))

    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "case-not-found"
    assert danh_ba.da_hoi == []


@pytest.mark.parametrize(
    "nguoi", [NGUOI_GUI, NGUOI_GUI_KHAC], ids=["chinh-nguoi-gui", "nguoi-gui-khac"]
)
def test_nguoi_gui_khong_vao_duoc_hai_diem_cuoi(client, session, phong_ban, nguoi):
    ho_so = _cho_phong_nhan(session, phong_ban)
    danh_ba = _goi_bang(client, nguoi)

    assert client.get(_dieu_phoi(ho_so)).status_code == 403
    assert client.get(_phong_ban(ho_so)).status_code == 403
    assert danh_ba.da_hoi == []


def test_cong_nguoi_gui_khong_lo_lien_he(client, session, phong_ban):
    """Cổng người gửi không có điểm cuối liên hệ, và trang chi tiết không mang theo nó."""
    ho_so = _cho_phong_nhan(session, phong_ban)
    danh_ba = _goi_bang(client, NGUOI_GUI)

    assert client.get(f"/requests/{ho_so.id}/requester-contact").status_code == 404
    chi_tiet = client.get(f"/requests/{ho_so.id}")
    assert chi_tiet.status_code == 200
    assert "phone" not in chi_tiet.text and "0900" not in chi_tiet.text
    assert danh_ba.da_hoi == []


def test_ho_so_khong_ton_tai_thi_404(client):
    danh_ba = _goi_bang(client, DIEU_PHOI)

    r = client.get("/coordination/requests/999999999/requester-contact")

    assert r.status_code == 404
    assert danh_ba.da_hoi == []


# ---------------------------------------------------------------------------
# Danh bạ trả gì
# ---------------------------------------------------------------------------


def test_danh_ba_hong_thi_503_ma_trang_chi_tiet_van_mo(client, session, phong_ban):
    ho_so = _cho_phong_nhan(session, phong_ban)
    _goi_bang(client, DIEU_PHOI, DanhBaGia(loi="Không gọi được Keycloak: Connection refused"))

    r = client.get(_dieu_phoi(ho_so))
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "directory-unavailable"
    assert "Connection refused" in r.json()["detail"]["message"]
    assert client.get(f"/coordination/requests/{ho_so.id}").status_code == 200

    _goi_bang(client, _truong_phong(phong_ban))
    assert client.get(_phong_ban(ho_so)).status_code == 503
    assert client.get(f"/department/requests/{ho_so.id}").status_code == 200


def test_chua_dien_so_dien_thoai_thi_tra_trong(client, session, phong_ban):
    ho_so = _cho_phong_nhan(session, phong_ban)
    _goi_bang(client, DIEU_PHOI, DanhBaGia(Contact(email="an.nguyen@dx-os-lab.test", phone=None)))

    r = client.get(_dieu_phoi(ho_so))

    assert r.status_code == 200
    assert r.json()["phone"] is None
    assert r.json()["found"] is True, "chưa điền số khác với không còn tài khoản"


def test_tai_khoan_khong_con_thi_van_co_ten(client, session, phong_ban):
    ho_so = _cho_phong_nhan(session, phong_ban)
    _goi_bang(client, DIEU_PHOI, DanhBaGia(lien_he=None))

    r = client.get(_dieu_phoi(ho_so))

    assert r.status_code == 200
    assert r.json() == {"name": "An Nguyễn", "email": None, "phone": None, "found": False}


# ---------------------------------------------------------------------------
# Đọc hồ sơ người dùng của Keycloak
# ---------------------------------------------------------------------------


def _danh_ba(*, thuoc_tinh: str = "phoneNumber", tran: float = 3.0) -> KeycloakDirectory:
    return KeycloakDirectory(
        base_url="http://keycloak:8080",
        realm="dx-os-lab",
        client_id="dx-directory",
        client_secret="bi-mat",
        department_prefix="/phong-ban/",
        timeout_seconds=tran,
        phone_attribute=thuoc_tinh,
    )


def _thay_goi(danh_ba: KeycloakDirectory, tra_ve) -> list[str]:
    """Thay lớp gọi mạng bằng một kết quả định sẵn; trả về các đường dẫn đã gọi."""
    da_goi: list[str] = []

    def goi(duong_dan, thoi_han, **_):
        da_goi.append(duong_dan)
        return tra_ve

    danh_ba._goi = goi
    return da_goi


def test_doc_email_va_so_dien_thoai():
    danh_ba = _danh_ba()
    da_goi = _thay_goi(danh_ba, {
        "email": "an.nguyen@dx-os-lab.test",
        "attributes": {"phoneNumber": ["  ", " 0900 000 001 "]},
    })

    assert danh_ba.contact("kc-gui-131") == Contact(
        email="an.nguyen@dx-os-lab.test", phone="0900 000 001"
    ), "bỏ giá trị trống, cắt khoảng trắng"
    assert da_goi == ["/users/kc-gui-131"]


def test_ten_thuoc_tinh_doc_tu_cau_hinh():
    danh_ba = _danh_ba(thuoc_tinh="mobile")
    _thay_goi(danh_ba, {
        "attributes": {"phoneNumber": ["0900 000 001"], "mobile": ["0912 345 678"]},
    })

    assert danh_ba.contact("x").phone == "0912 345 678"


def test_khong_co_thuoc_tinh_thi_tra_trong():
    danh_ba = _danh_ba()
    _thay_goi(danh_ba, {"username": "an.nguyen", "email": ""})

    assert danh_ba.contact("x") == Contact(email=None, phone=None)


def test_khong_con_tai_khoan_thi_none():
    danh_ba = _danh_ba()
    _thay_goi(danh_ba, None)

    assert danh_ba.contact("x") is None


def test_tra_lien_he_giu_tran_thoi_gian():
    """Cùng trần thời gian với ô chọn người xử lý: Keycloak treo không giữ trang lại."""
    danh_ba = _danh_ba(tran=0.3)
    danh_ba._tra_lien_he = lambda user_id: time.sleep(2)

    bat_dau = time.monotonic()
    with pytest.raises(DirectoryUnavailable, match="không trả lời xong"):
        danh_ba.contact("x")
    assert time.monotonic() - bat_dau < 1.0


# ---------------------------------------------------------------------------
# Keycloak thật
# ---------------------------------------------------------------------------


def test_keycloak_that_tra_dung_lien_he_tai_khoan_mau(danh_ba_that):
    """Kiểm thứ danh bạ giả không kiểm được: user profile của realm khai thuộc tính số
    điện thoại, và tài khoản dịch vụ chỉ mang `view-users` vẫn đọc được nó."""
    tim = danh_ba_that._goi("/users?username=an.nguyen&exact=true", time.monotonic() + 5)
    assert len(tim) == 1

    lien_he = danh_ba_that.contact(tim[0]["id"])

    assert lien_he == Contact(email="an.nguyen@dx-os-lab.test", phone="0900 000 001")
    assert danh_ba_that.contact("00000000-0000-0000-0000-000000000000") is None
