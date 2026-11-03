# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Bảng điều khiển phân tích nhúng trong cổng (#305): ai được xin token khách, và token đó mang
# điều kiện lọc nào.
#
# Superset được thay bằng bản giả ghi lại điều kiện lọc dịch vụ gửi đi — thứ cần kiểm là quyết
# định của dịch vụ, không phải Superset. Việc Superset áp điều kiện đó lên từng biểu đồ đã thử
# trên cụm thật, và có kịch bản giao diện qua đăng nhập thật ở e2e/.
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.analytics.bang_dieu_khien import (
    COT_PHONG,
    PhamVi,
    SupersetKhongPhanHoi,
    dieu_kien_loc,
    superset_client,
)
from app.auth.dependencies import current_actor, current_claims
from app.db import get_session
from app.main import app
from app.models.workflow_config import Department, Role
from app.workflow.context import Actor

TRUONG_PHONG_IT = Actor(id="tp-305", name="Anh Dũng", roles=frozenset({"approver"}), departments=frozenset({"it"}))
DIEU_PHOI = Actor(id="dp-305", roles=frozenset({"classifier"}))
QUAN_TRI = Actor(id="qt-305", roles=frozenset({"administrator"}))
NGUOI_GUI = Actor(id="ng-305", roles=frozenset({"requester"}))
XU_LY_IT = Actor(id="xl-305", roles=frozenset({"handler"}), departments=frozenset({"it"}))


class SupersetGia:
    """Ghi lại mỗi lần xin token; `hong` thì giả như Superset tắt."""

    def __init__(self) -> None:
        self.lan_xin: list[tuple[Actor, list[dict[str, str]]]] = []
        self.hong = False

    def xin_token(self, actor, loc):
        if self.hong:
            raise SupersetKhongPhanHoi("tắt")
        self.lan_xin.append((actor, loc))
        return "token-gia", "ma-nhung-gia"


@pytest.fixture
def client(session):
    gia = SupersetGia()
    dang_goi = {"actor": TRUONG_PHONG_IT}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: dang_goi["actor"]
    app.dependency_overrides[current_claims] = lambda: {}
    app.dependency_overrides[superset_client] = lambda: gia
    with TestClient(app) as c:
        c.dang_goi, c.superset = dang_goi, gia
        yield c
    app.dependency_overrides.clear()


def _xin(client, actor):
    client.dang_goi["actor"] = actor
    return client.post("/analytics/dashboard/guest-token")


def test_truong_phong_chi_thay_phong_minh(client):
    tra_ve = _xin(client, TRUONG_PHONG_IT)
    assert tra_ve.status_code == 200
    than = tra_ve.json()
    assert (than["token"], than["dashboard_id"]) == ("token-gia", "ma-nhung-gia")
    assert than["scope"]["all"] is False
    assert [p["code"] for p in than["scope"]["departments"]] == ["it"]
    assert than["scope"]["departments"][0]["label"]  # tên phòng tra từ bảng, để cổng hiện
    [(actor, loc)] = client.superset.lan_xin
    assert actor.id == TRUONG_PHONG_IT.id
    assert loc == [{"clause": f"{COT_PHONG} IN ('it')"}]


@pytest.mark.parametrize("actor", [DIEU_PHOI, QUAN_TRI], ids=["dieu-phoi", "quan-tri"])
def test_dieu_phoi_va_quan_tri_thay_toan_cong_ty(client, actor):
    tra_ve = _xin(client, actor)
    assert tra_ve.status_code == 200
    assert tra_ve.json()["scope"] == {"all": True, "departments": []}
    assert client.superset.lan_xin[-1][1] == []


@pytest.mark.parametrize("actor", [NGUOI_GUI, XU_LY_IT], ids=["nguoi-gui", "xu-ly"])
def test_vai_khac_nhan_403_va_khong_xin_superset(client, actor):
    tra_ve = _xin(client, actor)
    assert tra_ve.status_code == 403
    assert tra_ve.json()["detail"]["code"] == "reports-forbidden"
    assert client.superset.lan_xin == []


def test_truong_phong_chua_thuoc_phong_nao_bi_tu_choi(client):
    chua_co_phong = Actor(id="tp-305b", roles=frozenset({"approver"}))
    assert _xin(client, chua_co_phong).status_code == 403
    assert client.superset.lan_xin == []


def test_ma_phong_la_trong_token_bi_bo(client):
    """Chỉ mã có trong bảng phòng ban đi vào điều kiện lọc — không chuỗi nào từ token đi thẳng."""
    la = Actor(id="tp-305c", roles=frozenset({"approver"}),
               departments=frozenset({"it", "x') OR (1=1"}))
    assert _xin(client, la).status_code == 200
    assert client.superset.lan_xin[-1][1] == [{"clause": f"{COT_PHONG} IN ('it')"}]


def test_nhieu_phong_loc_du_moi_phong(client, session):
    hai_phong = Actor(id="tp-305d", roles=frozenset({"approver"}), departments=frozenset({"it", "hr"}))
    assert _xin(client, hai_phong).status_code == 200
    menh_de = client.superset.lan_xin[-1][1][0]["clause"]
    assert menh_de.startswith(f"{COT_PHONG} IN (")
    assert "'it'" in menh_de and "'hr'" in menh_de


def test_nhieu_vai_tro_lay_pham_vi_rong_nhat(client):
    kiem = Actor(id="tp-305e", roles=frozenset({"approver", "classifier"}), departments=frozenset({"it"}))
    assert _xin(client, kiem).json()["scope"]["all"] is True
    assert client.superset.lan_xin[-1][1] == []


def test_pham_vi_la_du_lieu_khong_phai_ma(client, session):
    """Đổi cột `report_scope` trong bảng là đổi ai xem được — không sửa dòng mã nào."""
    session.execute(update(Role).where(Role.code == "handler").values(report_scope="department"))
    session.execute(update(Role).where(Role.code == "approver").values(report_scope=None))
    session.flush()
    assert _xin(client, XU_LY_IT).status_code == 200
    assert client.superset.lan_xin[-1][1] == [{"clause": f"{COT_PHONG} IN ('it')"}]
    assert _xin(client, TRUONG_PHONG_IT).status_code == 403


def test_superset_tat_thi_503(client):
    client.superset.hong = True
    tra_ve = _xin(client, TRUONG_PHONG_IT)
    assert tra_ve.status_code == 503
    assert tra_ve.json()["detail"]["code"] == "reports-unavailable"


def test_me_chi_hien_bao_cao_cho_vai_duoc_xem(client):
    def khong_gian(actor):
        client.dang_goi["actor"] = actor
        return client.get("/me").json()["workspaces"]

    for duoc in (TRUONG_PHONG_IT, DIEU_PHOI, QUAN_TRI):
        assert "reports" in khong_gian(duoc), duoc.id
    for khong in (NGUOI_GUI, XU_LY_IT):
        assert "reports" not in khong_gian(khong), khong.id
    # Báo cáo đứng trước Hệ thống trên thanh bên
    cua_qt = khong_gian(QUAN_TRI)
    assert cua_qt.index("reports") < cua_qt.index("system")


def test_du_lieu_khoi_tao_khop_pham_vi_da_chot(session):
    pham_vi = dict(session.execute(select(Role.code, Role.report_scope)).all())
    assert pham_vi == {
        "requester": None, "classifier": "all", "approver": "department",
        "handler": None, "administrator": "all",
    }


def test_dieu_kien_loc_nhan_doi_dau_nhay():
    phong = Department(code="o'k", label="Thử")
    assert dieu_kien_loc(PhamVi(toan_cong_ty=False, phong=(phong,))) == [
        {"clause": f"{COT_PHONG} IN ('o''k')"}
    ]
    assert dieu_kien_loc(PhamVi(toan_cong_ty=True)) == []


class _MayChuGia:
    """Superset giả qua HTTP thật: đòi Bearer, cookie phiên và mã CSRF như bản thật."""

    def __init__(self) -> None:
        import http.server
        import json
        import threading

        cha = self
        self.duong_da_goi: list[str] = []
        self.guest_hong = False
        self.lan_xin_token: list[dict] = []

        class XuLy(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _tra(self, ma, than, cookie=None):
                du_lieu = json.dumps(than).encode()
                self.send_response(ma)
                self.send_header("Content-Type", "application/json")
                if cookie:
                    self.send_header("Set-Cookie", cookie)
                self.send_header("Content-Length", str(len(du_lieu)))
                self.end_headers()
                self.wfile.write(du_lieu)

            def _than(self):
                n = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(n) or b"null")

            def do_GET(self):
                cha.duong_da_goi.append("GET " + self.path)
                if self.path == "/api/v1/security/csrf_token/" and self.headers.get("Authorization") == "Bearer tk":
                    return self._tra(200, {"result": "csrf-1"}, cookie="session=s1; Path=/")
                self._tra(401, {})

            def do_POST(self):
                cha.duong_da_goi.append("POST " + self.path)
                than = self._than()
                if self.path == "/api/v1/security/login":
                    return self._tra(200, {"access_token": "tk"})
                du_phien = (self.headers.get("Authorization") == "Bearer tk"
                            and self.headers.get("X-CSRFToken") == "csrf-1"
                            and "session=s1" in (self.headers.get("Cookie") or ""))
                if not du_phien:
                    return self._tra(400, {"message": "The CSRF token is missing."})
                if self.path == "/api/v1/dashboard/van-hanh-yeu-cau/embedded":
                    return self._tra(200, {"result": {"uuid": "uuid-nhung", "allowed_domains": than["allowed_domains"]}})
                if self.path == "/api/v1/security/guest_token/":
                    if cha.guest_hong:
                        return self._tra(400, {"message": "resource not found"})
                    cha.lan_xin_token.append(than)
                    return self._tra(200, {"token": "khach-1"})
                self._tra(404, {})

        self.may_chu = http.server.ThreadingHTTPServer(("127.0.0.1", 0), XuLy)
        threading.Thread(target=self.may_chu.serve_forever, daemon=True).start()
        self.goc = f"http://127.0.0.1:{self.may_chu.server_address[1]}"


def test_superset_client_di_dung_luong_dang_nhap_csrf_va_nho_ma_nhung():
    from app.analytics.bang_dieu_khien import SupersetClient

    gia = _MayChuGia()
    try:
        may = SupersetClient()
        may._goc, may._slug, may._mien_nhung = gia.goc, "van-hanh-yeu-cau", "http://cong.test"
        loc = [{"clause": f"{COT_PHONG} IN ('it')"}]

        assert may.xin_token(TRUONG_PHONG_IT, loc) == ("khach-1", "uuid-nhung")
        assert may.xin_token(TRUONG_PHONG_IT, loc) == ("khach-1", "uuid-nhung")
        # Cấu hình nhúng bật một lần rồi nhớ, không gửi lại mỗi lần làm mới token
        assert gia.duong_da_goi.count("POST /api/v1/dashboard/van-hanh-yeu-cau/embedded") == 1
        yeu_cau = gia.lan_xin_token[0]
        assert yeu_cau["resources"] == [{"type": "dashboard", "id": "uuid-nhung"}]
        assert yeu_cau["rls"] == loc
        assert yeu_cau["user"]["username"] == TRUONG_PHONG_IT.id

        # Xin token hỏng (cấu hình nhúng bị xóa) thì lần sau bật lại cấu hình nhúng
        gia.guest_hong = True
        with pytest.raises(SupersetKhongPhanHoi):
            may.xin_token(TRUONG_PHONG_IT, loc)
        gia.guest_hong = False
        may.xin_token(TRUONG_PHONG_IT, loc)
        assert gia.duong_da_goi.count("POST /api/v1/dashboard/van-hanh-yeu-cau/embedded") == 2
    finally:
        gia.may_chu.shutdown()


def test_superset_client_bao_khong_phan_hoi_khi_superset_tat():
    from app.analytics.bang_dieu_khien import SupersetClient

    may = SupersetClient()
    may._goc, may._tran_giay = "http://127.0.0.1:9", 1.0
    with pytest.raises(SupersetKhongPhanHoi):
        may.xin_token(TRUONG_PHONG_IT, [])
