# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm ranh giới nền tảng lõi và ứng dụng minh họa (#365, ARCHITECTURE.md mục 2.3).
#
# API của lõi được gắn THÊM một lần dưới `/core/v1` — cùng router, cùng hàm, cùng phụ thuộc với đường cũ.
# Ba lớp kiểm:
#
#   Trong tiến trình — TestClient với tác nhân giả như test_routes.py: mỗi đường /core/v1 trả cùng kết quả
#     với đường cũ, đọc lẫn ghi; điểm cuối của ứng dụng minh họa không có dưới /core/v1; không token thì 401;
#     OpenAPI có năm nhóm "Lõi — …", không trùng mã thao tác.
#   Tài khoản dịch vụ — token client credentials THẬT của Keycloak (client dx-integration của realm mẫu) tạo
#     được hồ sơ và đi một bước chuyển chỉ bằng /core/v1; hồ sơ mang nhãn người gửi là tên client.
#   Qua cổng API thật — /core/v1 không token bị cổng chặn; token của tài khoản dịch vụ qua được.
#
# Phần ghi chạy trong phiên được hoàn tác ở cuối bài (conftest.py), kể cả khi đi bằng token thật.

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.dependencies import current_actor, current_claims
from app.auth.identity import actor_from_claims
from app.auth.tokens import verify_token
from app.config import get_settings
from app.db import get_session
from app.main import NHOM_LOI, TIEN_TO_LOI, app
from app.models.case import EventLog, Request
from app.models.thong_bao import NotificationType
from app.workflow.context import Actor
from app.workflow.engine import create_case
from tests.test_cong_api import CONG_API, goi, ma_rieng, phan_claim, toi_dich_vu
from tests.test_tep_dinh_kem import PNG, kho_that  # noqa: F401 — fixture dùng lại
from tests.truong_mau import chi_tiet_mau

NGUOI_GUI = Actor(id="loi-gui-365", name="Người gửi 365", roles=frozenset({"requester"}))
QUAN_TRI = Actor(id="loi-qt-365", name="Quản trị 365", roles=frozenset({"administrator"}))

# Bảng ánh xạ đường cũ → đường của lõi. Nguồn sự thật cho bài, khớp bảng ở ARCHITECTURE.md mục 2.3: thêm một
# điểm cuối vào lõi mà không thêm vào đây (hay ngược lại) thì bài đỏ.
ANH_XA: dict[tuple[str, str], str] = {
    ("GET", "/processes"): "/core/v1/workflow/processes",
    ("GET", "/request-types"): "/core/v1/workflow/request-types",
    ("GET", "/states"): "/core/v1/workflow/states",
    ("GET", "/priorities"): "/core/v1/workflow/priorities",
    ("GET", "/departments"): "/core/v1/workflow/departments",
    ("POST", "/requests"): "/core/v1/workflow/requests",
    ("GET", "/requests"): "/core/v1/workflow/requests",
    ("GET", "/requests/{case_id}"): "/core/v1/workflow/requests/{case_id}",
    ("POST", "/requests/{case_id}/transitions"): "/core/v1/workflow/requests/{case_id}/transitions",
    ("GET", "/attachments/policy"): "/core/v1/files/policy",
    ("POST", "/requests/{case_id}/attachments"): "/core/v1/files/requests/{case_id}/attachments",
    ("GET", "/attachments/{attachment_id}"): "/core/v1/files/{attachment_id}",
    ("GET", "/analytics/event-log"): "/core/v1/events",
    ("GET", "/me/notifications"): "/core/v1/notifications/preferences",
    ("POST", "/me/notifications/{code}"): "/core/v1/notifications/preferences/{code}",
    ("GET", "/me"): "/core/v1/identity/me",
}


def _cac_thao_tac() -> list[tuple[str, str, dict]]:
    return [
        (phuong_thuc.upper(), duong, thao_tac)
        for duong, cac_cach in app.openapi()["paths"].items()
        for phuong_thuc, thao_tac in cac_cach.items()
    ]


def _dien(duong: str, **gia_tri) -> str:
    for khoa, v in gia_tri.items():
        duong = duong.replace("{" + khoa + "}", str(v))
    return duong


@pytest.fixture
def client(session):
    """Máy khách dùng chung phiên của bài; đổi tác nhân bằng `client.tac_nhan["actor"] = …`."""
    tac_nhan = {"actor": NGUOI_GUI}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: tac_nhan["actor"]
    app.dependency_overrides[current_claims] = lambda: {
        "sub": tac_nhan["actor"].id, "preferred_username": "nguoi.gui.365", "name": tac_nhan["actor"].name,
    }
    with TestClient(app) as c:
        c.tac_nhan = tac_nhan
        yield c
    app.dependency_overrides.clear()


def _ho_so_cua(session, actor: Actor = NGUOI_GUI) -> Request:
    """Một hồ sơ của `actor` ở trạng thái đầu, dựng qua engine. Commit như test_routes.py dặn."""
    ho_so = create_case(session, title="Máy chiếu phòng họp không lên hình", description="Thử #365.",
                        requester_id=actor.id, requester_label=actor.label)
    session.commit()
    return ho_so


# ---------------------------------------------------------------------------
# OpenAPI: đúng bảng ánh xạ, đúng nhãn, không trùng mã thao tác
# ---------------------------------------------------------------------------


def test_openapi_loi_dung_bang_anh_xa():
    """Mọi thao tác dưới /core/v1 là một dòng của bảng ánh xạ, và ngược lại — không điểm cuối nào của ứng
    dụng minh họa lọt vào lõi, không điểm cuối lõi nào thiếu."""
    co = {(p, d) for p, d, _ in _cac_thao_tac()}
    duoi_loi = {(p, d) for p, d in co if d.startswith(TIEN_TO_LOI + "/")}
    assert duoi_loi == {(p, moi) for (p, _), moi in ANH_XA.items()}
    # Đường cũ còn nguyên cho cổng người dùng
    assert set(ANH_XA) <= co


def test_openapi_nhan_loi_va_ma_thao_tac_khong_trung():
    nhan_loi = {n["name"] for n in NHOM_LOI.values()}
    for phuong_thuc, duong, thao_tac in _cac_thao_tac():
        nhan = thao_tac.get("tags", [])
        if duong.startswith(TIEN_TO_LOI + "/"):
            assert nhan and all(n.startswith("Lõi — ") for n in nhan), (phuong_thuc, duong, nhan)
            assert set(nhan) <= nhan_loi
        else:
            assert not any(n.startswith("Lõi — ") for n in nhan), (phuong_thuc, duong, nhan)

    ma = [t["operationId"] for _, _, t in _cac_thao_tac()]
    assert len(ma) == len(set(ma)), "trùng operationId"

    # Năm nhóm lõi có mô tả và đứng đầu trang tài liệu
    dau = [n["name"] for n in app.openapi()["tags"]][: len(NHOM_LOI)]
    assert dau == [n["name"] for n in NHOM_LOI.values()]
    assert all(n.get("description") for n in app.openapi()["tags"][: len(NHOM_LOI)])


# ---------------------------------------------------------------------------
# Cùng kết quả với đường cũ
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("cu", "moi"),
    [
        ("/request-types", "/core/v1/workflow/request-types"),
        ("/states", "/core/v1/workflow/states"),
        ("/priorities", "/core/v1/workflow/priorities"),
        ("/departments", "/core/v1/workflow/departments"),
        ("/requests", "/core/v1/workflow/requests"),
        ("/requests?q=YC&needs_action=true", "/core/v1/workflow/requests?q=YC&needs_action=true"),
        ("/requests/{case_id}", "/core/v1/workflow/requests/{case_id}"),
        ("/attachments/policy", "/core/v1/files/policy"),
        ("/me/notifications", "/core/v1/notifications/preferences"),
        ("/me", "/core/v1/identity/me"),
    ],
)
def test_doc_qua_loi_cung_ket_qua_duong_cu(client, session, rule_set, cu, moi):
    ho_so = _ho_so_cua(session)
    tra_cu = client.get(_dien(cu, case_id=ho_so.id))
    tra_moi = client.get(_dien(moi, case_id=ho_so.id))
    assert tra_cu.status_code == 200, tra_cu.text
    assert tra_moi.status_code == tra_cu.status_code
    assert tra_moi.json() == tra_cu.json()


def test_hoso_nguoi_khac_qua_loi_van_404(client, session, rule_set):
    """Cùng cửa nhìn thấy như đường cũ: hồ sơ của người khác trả 404, không 403."""
    cua_nguoi_khac = _ho_so_cua(session, Actor(id="loi-khac-365", roles=frozenset({"requester"})))
    assert client.get(f"/core/v1/workflow/requests/{cua_nguoi_khac.id}").status_code == 404
    assert client.get(f"/requests/{cua_nguoi_khac.id}").status_code == 404


def test_xuat_nhat_ky_qua_loi_cung_noi_dung_va_cung_quyen(client, session, rule_set):
    _ho_so_cua(session)
    for dinh_dang in ("json", "csv"):
        client.tac_nhan["actor"] = QUAN_TRI
        cu = client.get(f"/analytics/event-log?format={dinh_dang}")
        moi = client.get(f"/core/v1/events?format={dinh_dang}")
        assert cu.status_code == moi.status_code == 200
        assert moi.content == cu.content
        assert moi.headers["content-type"] == cu.headers["content-type"]
        assert moi.headers["content-disposition"] == cu.headers["content-disposition"]
    # Cùng phụ thuộc phân quyền: người không phải quản trị nhận 403 ở cả hai
    client.tac_nhan["actor"] = NGUOI_GUI
    assert client.get("/core/v1/events").status_code == client.get("/analytics/event-log").status_code == 403


def test_tao_ho_so_va_di_buoc_qua_loi_nhu_duong_cu(client, session, rule_set):
    loai = client.get("/core/v1/workflow/request-types").json()[0]
    tao = client.post("/core/v1/workflow/requests", json={
        "title": "Cấp quyền phần mềm kế toán", "description": "Tạo qua lõi.",
        "request_type_code": loai["code"], "details": chi_tiet_mau(loai),
    })
    assert tao.status_code == 201, tao.text
    ho_so = tao.json()
    assert ho_so["history"] == []
    # Đọc lại ở đường cũ: đúng hồ sơ đó, cùng nội dung
    assert client.get(f"/requests/{ho_so['id']}").json() == client.get(
        f"/core/v1/workflow/requests/{ho_so['id']}").json()

    cac_buoc = ho_so["allowed_transitions"]
    assert cac_buoc, "người gửi phải đi được ít nhất một bước ở trạng thái đầu"
    buoc = next((b for b in cac_buoc if not b["keeps_state"]), cac_buoc[0])
    di = client.post(f"/core/v1/workflow/requests/{ho_so['id']}/transitions",
                     json={"to_state": buoc["to_state"], "note": "Đi qua lõi." if buoc["requires_note"] else None})
    assert di.status_code == 200, di.text
    assert di.json()["state"]["code"] == buoc["to_state"]
    assert di.json() == client.get(f"/requests/{ho_so['id']}").json()

    # Cùng một cửa chuyển trạng thái: một dòng nhật ký, tác nhân là người gọi
    nhat_ky = session.scalars(select(EventLog).where(EventLog.case_id == ho_so["id"])).all()
    assert [(e.actor, e.to_state) for e in nhat_ky] == [(NGUOI_GUI.id, buoc["to_state"])]


def test_buoc_sai_qua_loi_bi_tu_choi_nhu_duong_cu(client, session, rule_set):
    """Lõi không mở thêm cửa nào: bước không có trong bảng cạnh bị engine từ chối, cùng mã lỗi."""
    ho_so = _ho_so_cua(session)
    trang_thai = [s["code"] for s in client.get("/core/v1/workflow/states").json()]
    di_duoc = {b["to_state"] for b in client.get(f"/requests/{ho_so.id}").json()["allowed_transitions"]}
    cam = next(s for s in trang_thai if s not in di_duoc)
    moi = client.post(f"/core/v1/workflow/requests/{ho_so.id}/transitions", json={"to_state": cam})
    cu = client.post(f"/requests/{ho_so.id}/transitions", json={"to_state": cam})
    assert moi.status_code == cu.status_code
    assert moi.status_code in (403, 409)
    assert moi.json() == cu.json()


def test_tuy_chon_thong_bao_qua_loi_doi_duoc_doc_o_duong_cu(client, session, rule_set):
    loai = session.scalars(select(NotificationType.code).where(NotificationType.is_active)).first()
    if loai is None:
        pytest.skip("Dữ liệu khởi tạo chưa khai loại thông báo nào.")
    hien = {t["code"]: t["enabled"] for t in client.get("/me/notifications").json()["types"]}
    doi = client.post(f"/core/v1/notifications/preferences/{loai}", json={"enabled": not hien[loai]})
    assert doi.status_code == 200, doi.text
    assert doi.json() == client.get("/me/notifications").json()
    assert {t["code"]: t["enabled"] for t in doi.json()["types"]}[loai] is (not hien[loai])


def test_tai_tep_qua_loi_doc_duoc_o_ca_hai_duong(client, session, rule_set, kho_that):  # noqa: F811
    ho_so = _ho_so_cua(session)
    tai_len = client.post(f"/core/v1/files/requests/{ho_so.id}/attachments",
                          files=[("files", ("anh-man-hinh.png", PNG, "application/octet-stream"))])
    assert tai_len.status_code == 201, tai_len.text
    ma_tep = tai_len.json()[0]["id"]
    moi = client.get(f"/core/v1/files/{ma_tep}")
    cu = client.get(f"/attachments/{ma_tep}")
    assert moi.status_code == cu.status_code == 200
    assert moi.content == cu.content == PNG
    assert moi.headers["content-disposition"] == cu.headers["content-disposition"]
    # Người không mở được hồ sơ nhận 404 ở cả hai đường — cùng một luật quyền
    client.tac_nhan["actor"] = Actor(id="loi-khac-365", roles=frozenset({"requester"}))
    assert client.get(f"/core/v1/files/{ma_tep}").status_code == client.get(f"/attachments/{ma_tep}").status_code == 404


# ---------------------------------------------------------------------------
# Ứng dụng minh họa không có dưới /core/v1; lõi vẫn cần token
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("phuong_thuc", "duong"),
    [
        ("GET", "/core/v1/coordination/queue"),
        ("GET", "/core/v1/workflow/coordination/queue"),
        ("POST", "/core/v1/coordination/requests/1/transitions"),
        ("GET", "/core/v1/department/queue"),
        ("POST", "/core/v1/department/requests/1/transitions"),
        ("GET", "/core/v1/inbox"),
        ("POST", "/core/v1/workflow/requests/1/messages"),
        ("GET", "/core/v1/delegations"),
        ("GET", "/core/v1/workflow/departments/it/assignees"),
        ("POST", "/core/v1/analytics/dashboard/guest-token"),
        ("GET", "/core/v1/analytics/process-mining"),
        ("POST", "/core/v1/similar-cases/search"),
        ("GET", "/core/v1/admin/config"),
        ("GET", "/core/v1/system/health"),
        ("POST", "/core/v1/sla/scan"),
        ("GET", "/core/v1/metrics"),
        ("GET", "/core/v1/health"),
    ],
)
def test_diem_cuoi_ung_dung_khong_co_duoi_loi(phuong_thuc, duong):
    """404 vì không có tuyến — không phải vì thiếu quyền (thiếu quyền là 401/403, xem bài dưới). Không cần
    vòng đời ứng dụng nên không mở TestClient bằng `with`."""
    assert TestClient(app).request(phuong_thuc, duong).status_code == 404


@pytest.mark.parametrize(("phuong_thuc", "duong"), sorted({(p, m) for (p, _), m in ANH_XA.items()}))
def test_loi_khong_token_401(phuong_thuc, duong):
    tra = TestClient(app).request(phuong_thuc, _dien(duong, case_id=1, attachment_id=1, code="x"))
    assert tra.status_code == 401, tra.text
    assert tra.headers.get("www-authenticate") == "Bearer"


# ---------------------------------------------------------------------------
# Tài khoản dịch vụ: token client credentials thật của Keycloak
# ---------------------------------------------------------------------------

CLIENT_TICH_HOP = os.environ.get("KEYCLOAK_INTEGRATION_CLIENT_ID", "dx-integration")
VAI_TICH_HOP = [v.strip() for v in os.environ.get("KEYCLOAK_INTEGRATION_ROLES", "requester").split(",") if v.strip()]


@pytest.fixture(scope="module")
def token_dich_vu() -> str:
    """Access token của tài khoản dịch vụ, luồng client credentials — client khai trong realm mẫu (#365)."""
    cs = get_settings()
    du_lieu = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": CLIENT_TICH_HOP,
        "client_secret": os.environ.get("KEYCLOAK_INTEGRATION_SECRET", "doi_bi_mat_nay_truoc_khi_trien_khai"),
    }).encode()
    dia_chi = f"{cs.keycloak_internal_url}/realms/{cs.keycloak_realm}/protocol/openid-connect/token"
    try:
        with urllib.request.urlopen(dia_chi, data=du_lieu, timeout=10) as r:
            return json.load(r)["access_token"]
    except (urllib.error.URLError, OSError, KeyError) as loi:
        pytest.skip(f"Không lấy được token của tài khoản dịch vụ {CLIENT_TICH_HOP} ({loi}). Cụm dựng trước "
                    "#365 thì chạy scripts/tai_khoan_dich_vu.py.")


def test_token_dich_vu_qua_kiem_va_thanh_tac_nhan_doc_duoc(token_dich_vu):
    """Token thiếu `name` và `groups` của người dùng vẫn qua đủ bốn phép kiểm, và tác nhân mang nhãn là tên
    client chứ không phải `service-account-…`."""
    claims = verify_token(token_dich_vu)
    assert "name" not in claims
    tac_nhan = actor_from_claims(claims)
    assert tac_nhan.label == CLIENT_TICH_HOP
    assert set(VAI_TICH_HOP) <= tac_nhan.roles
    assert tac_nhan.departments == frozenset()


def test_nguoi_dung_thuong_khong_muon_duoc_nhan_cua_ung_dung():
    """Chỉ tên người dùng ĐÚNG là tài khoản dịch vụ của client phát token mới đổi thành tên client."""
    gia = actor_from_claims({"sub": "x", "preferred_username": "service-account-dx-portal", "azp": "dx-integration"})
    assert gia.label == "service-account-dx-portal"
    thuong = actor_from_claims({"sub": "y", "preferred_username": "an.nguyen", "azp": "dx-portal"})
    assert thuong.label == "an.nguyen"
    co_ten = actor_from_claims({"sub": "z", "name": "Ứng dụng nhân sự", "preferred_username": "service-account-hr",
                                "azp": "hr"})
    assert co_ten.label == "Ứng dụng nhân sự"


def test_tai_khoan_dich_vu_tao_ho_so_va_di_mot_buoc_chi_bang_loi(session, rule_set, token_dich_vu):
    """Định nghĩa hoàn thành của #365, trong tiến trình: token thật, kiểm token thật, chỉ /core/v1."""
    claims = phan_claim(token_dich_vu)
    app.dependency_overrides[get_session] = lambda: session
    try:
        with TestClient(app, headers={"Authorization": f"Bearer {token_dich_vu}"}) as c:
            loai = c.get("/core/v1/workflow/request-types").json()[0]
            tao = c.post("/core/v1/workflow/requests", json={
                "title": "Yêu cầu từ ứng dụng nhân sự", "request_type_code": loai["code"],
                "details": chi_tiet_mau(loai),
            })
            assert tao.status_code == 201, tao.text
            ho_so = tao.json()
            assert ho_so["requester_id"] == claims["sub"]

            cac_buoc = c.get(f"/core/v1/workflow/requests/{ho_so['id']}").json()["allowed_transitions"]
            assert cac_buoc, f"vai {VAI_TICH_HOP} phải đi được ít nhất một bước ở trạng thái đầu"
            buoc = next((b for b in cac_buoc if not b["keeps_state"]), cac_buoc[0])
            di = c.post(f"/core/v1/workflow/requests/{ho_so['id']}/transitions",
                        json={"to_state": buoc["to_state"], "note": "Thử." if buoc["requires_note"] else None})
            assert di.status_code == 200, di.text
            lich_su = c.get(f"/core/v1/workflow/requests/{ho_so['id']}").json()["history"]
    finally:
        app.dependency_overrides.clear()

    assert [(s["actor"], s["actor_label"], s["to_state"]) for s in lich_su] == [
        (claims["sub"], CLIENT_TICH_HOP, buoc["to_state"])
    ]
    # Nhãn người gửi ghi vào hồ sơ đọc được: tên ứng dụng, không phải mã định danh
    assert session.get(Request, ho_so["id"]).requester_label == CLIENT_TICH_HOP


# ---------------------------------------------------------------------------
# Qua cổng API thật
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def cong_api():
    try:
        ph = goi(CONG_API, "/health/live")
    except OSError as loi:
        pytest.skip(f"Không tới được cổng API ở {CONG_API} ({loi}).")
    if ph.ma != 200:
        pytest.skip(f"Cổng API ở {CONG_API} chưa sẵn sàng (HTTP {ph.ma}).")


@pytest.mark.parametrize(
    ("phuong_thuc", "duong"),
    [("GET", "/core/v1/workflow/request-types"), ("POST", "/core/v1/workflow/requests"),
     ("GET", "/core/v1/identity/me"), ("GET", "/core/v1/events"), ("GET", "/core/v1/nhom-chua-co")],
)
def test_cong_api_chan_loi_khong_token(cong_api, phuong_thuc, duong):
    """`/core/v1/*` rơi vào tuyến cần token của cổng: không token thì 401 ngay tại cổng, không tới dịch vụ."""
    ma = ma_rieng()
    ph = goi(CONG_API, duong, phuong_thuc=phuong_thuc, tieu_de={"X-Request-ID": ma})
    assert ph.ma == 401
    assert not toi_dich_vu(ph, ma)


def test_cong_api_cho_tai_khoan_dich_vu_vao_loi(cong_api, token_dich_vu):
    ma = ma_rieng()
    ph = goi(CONG_API, "/core/v1/identity/me", token=token_dich_vu, tieu_de={"X-Request-ID": ma})
    assert ph.ma == 200, ph.than[:200]
    assert toi_dich_vu(ph, ma)
    assert ph.json()["username"] == f"service-account-{CLIENT_TICH_HOP}".lower()
    assert set(VAI_TICH_HOP) <= set(ph.json()["roles"])

    danh_muc = goi(CONG_API, "/core/v1/workflow/request-types", token=token_dich_vu)
    assert danh_muc.ma == 200 and danh_muc.json()
    # Vai requester không mở được điểm cuối chỉ quản trị của lõi: 403 do dịch vụ quyết, không phải cổng
    ma = ma_rieng()
    xuat = goi(CONG_API, "/core/v1/events", token=token_dich_vu, tieu_de={"X-Request-ID": ma})
    if "administrator" not in VAI_TICH_HOP:
        assert xuat.ma == 403 and toi_dich_vu(xuat, ma)
