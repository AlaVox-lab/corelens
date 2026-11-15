# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm cổng API (#364, ADR-0010) qua mạng THẬT của cụm: Apache APISIX đứng trước dịch vụ ứng dụng.
#
# Chạy trong container dịch vụ ứng dụng như mọi bài khác — cùng mạng Compose với cổng API, Keycloak và
# chính dịch vụ (`localhost:8000` trong container). CI chạy nó ở job Cụm; thiếu cổng API thì bỏ qua khi
# chạy tay, còn trong CI bỏ qua là đỏ (DXLAB_CAM_BO_QUA=1).
#
# Lời gọi bị cổng chặn thì KHÔNG tới dịch vụ — chứng minh bằng mã yêu cầu: dịch vụ trả lại tiêu đề
# `X-Request-ID` ở MỌI phản hồi (app/quan_sat.py), còn cổng API không có plugin nào đặt tiêu đề đó. Bài
# gửi một mã riêng; phản hồi mang lại đúng mã đó nghĩa là dịch vụ đã trả lời, không mang nghĩa là cổng
# trả lời. Bài đối chứng gọi thẳng dịch vụ để chắc dấu hiệu này phân biệt được. Vì dịch vụ cũng tự trả
# 401 khi thiếu token, chỉ nhìn mã 401 thì tắt plugin kiểm token ở cổng bài vẫn xanh — nhìn mã yêu cầu
# thì đỏ (phép thử đột biến ghi ở ARCHITECTURE.md mục 7.4).

from __future__ import annotations

import base64
import datetime as dt
import http.client
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.config import get_settings

CONG_API = os.environ.get("DXLAB_CONG_API_URL", "http://cong-api:9080")
# Cổng nội bộ mà riêng cổng người dùng gọi; ở đây cổng API tin tiêu đề X-Real-IP
CONG_API_NOI_BO = os.environ.get("DXLAB_CONG_API_NOI_BO_URL", "http://cong-api:9081")
# Chính dịch vụ ứng dụng, gọi thẳng không qua cổng — chỉ để đối chứng
DICH_VU = os.environ.get("DXLAB_DICH_VU_URL", "http://localhost:8000")

MAT_KHAU_MAU = "matkhau123"
# Tài khoản quản trị của cụm mẫu (infra/.env.example), cần để tạo một client tạm phát token sống 1 giây
QUAN_TRI = os.environ.get("KEYCLOAK_ADMIN_USER", "admin")
MAT_KHAU_QUAN_TRI = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "admin")

# Đường công khai sẵn có của dịch vụ — khớp danh sách tuyến `cong-khai` ở infra/cong-api/apisix.yaml
DUONG_CONG_KHAI = ["/", "/health", "/health/live", "/health/ready", "/openapi.json", "/docs", "/redoc",
                   "/docs/oauth2-redirect"]


@dataclass
class PhanHoi:
    ma: int
    tieu_de: dict[str, str]
    than: bytes

    def json(self):
        return json.loads(self.than)


def goi(goc: str, duong: str, *, token: str | None = None, phuong_thuc: str = "GET",
        tieu_de: dict[str, str] | None = None, ket_noi: http.client.HTTPConnection | None = None) -> PhanHoi:
    """Một lời gọi HTTP, gửi đường dẫn NGUYÊN VẸN (http.client không chuẩn hóa `..`)."""
    dia_chi = urllib.parse.urlsplit(goc)
    kn = ket_noi or http.client.HTTPConnection(dia_chi.hostname, dia_chi.port, timeout=10)
    td = dict(tieu_de or {})
    if token:
        td["Authorization"] = f"Bearer {token}"
    try:
        kn.request(phuong_thuc, duong, headers=td)
        r = kn.getresponse()
        than = r.read()
        return PhanHoi(r.status, {k.lower(): v for k, v in r.getheaders()}, than)
    finally:
        if ket_noi is None:
            kn.close()


def ma_rieng() -> str:
    return f"kiem-cong-{secrets.token_hex(8)}"


def toi_dich_vu(ph: PhanHoi, ma: str) -> bool:
    """Phản hồi do dịch vụ ứng dụng trả (mang lại đúng mã yêu cầu đã gửi)?"""
    return ph.tieu_de.get("x-request-id") == ma


def lay_token(username: str, client_id: str | None = None, secret: str | None = None) -> str:
    """Access token thật của Keycloak, luồng cấp trực tiếp — như test_auth.py."""
    cs = get_settings()
    dia_chi = f"{cs.keycloak_internal_url}/realms/{cs.keycloak_realm}/protocol/openid-connect/token"
    du_lieu = urllib.parse.urlencode({
        "grant_type": "password",
        "client_id": client_id or os.environ.get("KEYCLOAK_PORTAL_CLIENT_ID", "dx-portal"),
        "client_secret": secret or os.environ.get("KEYCLOAK_PORTAL_SECRET", "doi_bi_mat_nay_truoc_khi_trien_khai"),
        "username": username,
        "password": MAT_KHAU_MAU,
        "scope": "openid",
    }).encode()
    try:
        with urllib.request.urlopen(dia_chi, data=du_lieu, timeout=10) as r:
            return json.load(r)["access_token"]
    except (urllib.error.URLError, OSError, KeyError) as loi:
        pytest.skip(f"Không lấy được token từ Keycloak ({loi}).")


def phan_claim(token: str) -> dict:
    giua = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(giua + "=" * (-len(giua) % 4)))


@pytest.fixture(scope="module", autouse=True)
def can_cong_api():
    """Cổng API phải đang chạy và đã nạp tuyến. Không có thì bỏ qua cả tệp (CI coi bỏ qua là đỏ)."""
    try:
        ph = goi(CONG_API, "/health/live")
    except OSError as loi:
        pytest.skip(f"Không tới được cổng API ở {CONG_API} ({loi}). Dựng cụm bằng docker compose up.")
    if ph.ma != 200:
        pytest.skip(f"Cổng API ở {CONG_API} chưa sẵn sàng (HTTP {ph.ma}).")


# ---------------------------------------------------------------------------
# Đối chứng: dấu hiệu "tới dịch vụ" phân biệt được
# ---------------------------------------------------------------------------


def test_doi_chung_dich_vu_tra_lai_ma_yeu_cau_ke_ca_khi_401():
    """Gọi thẳng dịch vụ không token: dịch vụ cũng trả 401 — nhưng mang lại mã yêu cầu. Nên ở các bài
    dưới, 401 KHÔNG mang mã là 401 của cổng API."""
    ma = ma_rieng()
    ph = goi(DICH_VU, "/me", tieu_de={"X-Request-ID": ma})
    assert ph.ma == 401
    assert toi_dich_vu(ph, ma)


# ---------------------------------------------------------------------------
# Đường công khai giữ nguyên hành vi
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("duong", DUONG_CONG_KHAI)
def test_duong_cong_khai_qua_cong_khong_can_token(duong):
    ma = ma_rieng()
    ph = goi(CONG_API, duong, tieu_de={"X-Request-ID": ma})
    assert ph.ma == 200, ph.than[:200]
    assert toi_dich_vu(ph, ma), "đường công khai phải được chuyển tới dịch vụ"
    assert "www-authenticate" not in ph.tieu_de


def test_health_cong_khai_van_chi_tra_trang_thai_chung():
    """#243: /health qua cổng vẫn đúng hai trường, không phiên bản, không chi tiết lỗi."""
    ph = goi(CONG_API, "/health")
    assert set(ph.json()) == {"service", "status"}


# ---------------------------------------------------------------------------
# Thiếu token, token hỏng: cổng chặn, dịch vụ không nhận được gì
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("phuong_thuc", "duong"),
    [
        ("GET", "/me"),
        ("GET", "/requests"),
        ("POST", "/requests"),
        ("GET", "/metrics"),
        ("GET", "/system/health"),
        ("POST", "/sla/scan"),
        # Đường công khai nhưng sai phương thức: rơi xuống tuyến cần token
        ("POST", "/health"),
        # Đường vòng: không đường nào lách qua tuyến công khai để tới điểm cuối cần token
        ("GET", "/health/../me"),
        ("GET", "/health/%2e%2e/me"),
        ("GET", "/health/..%2fme"),
        ("GET", "/docs/../metrics"),
        ("GET", "//me"),
        ("GET", "/health/"),
    ],
)
def test_khong_token_bi_cong_chan(phuong_thuc, duong):
    ma = ma_rieng()
    ph = goi(CONG_API, duong, phuong_thuc=phuong_thuc, tieu_de={"X-Request-ID": ma})
    assert ph.ma == 401
    assert not toi_dich_vu(ph, ma), "lời gọi thiếu token đã tới dịch vụ"
    assert ph.tieu_de.get("www-authenticate", "").startswith("Bearer")


def _khoa_rieng_la() -> bytes:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _kid_that() -> str:
    with urllib.request.urlopen(get_settings().oidc_jwks_url, timeout=10) as r:
        khoa = [k for k in json.load(r)["keys"] if k.get("alg") == "RS256" and k.get("use", "sig") == "sig"]
    return khoa[0]["kid"]


@pytest.mark.parametrize("kid_that", [False, True], ids=["kid-la", "mao-kid-cua-keycloak"])
def test_token_ky_bang_khoa_la_bi_cong_chan(kid_that):
    """Đủ claim đúng (nơi phát, người nhận, hạn dùng) nhưng ký bằng khóa của kẻ giả mạo — kể cả khi mạo
    đúng `kid` của Keycloak để cổng lấy đúng khóa thật ra so."""
    cs = get_settings()
    bay_gio = dt.datetime.now(dt.UTC)
    token = jwt.encode(
        {"sub": "ke-gian", "iss": cs.oidc_issuer, "aud": cs.oidc_audience, "iat": bay_gio,
         "exp": bay_gio + dt.timedelta(minutes=5), "realm_access": {"roles": ["administrator"]}},
        _khoa_rieng_la(),
        algorithm="RS256",
        headers={"kid": _kid_that() if kid_that else "khoa-la"},
    )
    ma = ma_rieng()
    ph = goi(CONG_API, "/me", token=token, tieu_de={"X-Request-ID": ma})
    assert ph.ma == 401
    assert not toi_dich_vu(ph, ma)
    assert "invalid_token" in ph.tieu_de.get("www-authenticate", "")


def test_token_khong_chu_ky_bi_cong_chan():
    cs = get_settings()
    bay_gio = dt.datetime.now(dt.UTC)
    token = jwt.encode(
        {"sub": "ke-gian", "iss": cs.oidc_issuer, "aud": cs.oidc_audience, "iat": bay_gio,
         "exp": bay_gio + dt.timedelta(minutes=5)},
        key=None,
        algorithm="none",
    )
    ma = ma_rieng()
    ph = goi(CONG_API, "/me", token=token, tieu_de={"X-Request-ID": ma})
    assert ph.ma == 401
    assert not toi_dich_vu(ph, ma)


def test_token_cua_client_khac_bi_cong_chan():
    """Token thật của Keycloak nhưng không phát cho dịch vụ ứng dụng (aud khác): tài khoản dịch vụ của
    danh bạ. Cổng trả 403, dịch vụ không nhận — dịch vụ gọi thẳng cũng từ chối (kiểm hai lớp)."""
    cs = get_settings()
    du_lieu = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": cs.directory_client_id,
        "client_secret": cs.directory_client_secret or "doi_bi_mat_nay_truoc_khi_trien_khai",
    }).encode()
    dia_chi = f"{cs.keycloak_internal_url}/realms/{cs.keycloak_realm}/protocol/openid-connect/token"
    try:
        with urllib.request.urlopen(dia_chi, data=du_lieu, timeout=10) as r:
            token = json.load(r)["access_token"]
    except (urllib.error.URLError, OSError, KeyError) as loi:
        pytest.skip(f"Không lấy được token của tài khoản dịch vụ danh bạ ({loi}).")
    aud = phan_claim(token).get("aud")
    assert cs.oidc_audience not in (aud if isinstance(aud, list) else [aud])

    ma = ma_rieng()
    ph = goi(CONG_API, "/me", token=token, tieu_de={"X-Request-ID": ma})
    assert ph.ma == 403
    assert not toi_dich_vu(ph, ma)
    assert goi(DICH_VU, "/me", token=token).ma == 401


# ---------------------------------------------------------------------------
# Token đúng: qua cổng, dịch vụ vẫn tự kiểm và tự phân quyền
# ---------------------------------------------------------------------------


def test_token_dung_qua_cong_toi_dich_vu():
    ma = ma_rieng()
    ph = goi(CONG_API, "/me", token=lay_token("cuong.le"), tieu_de={"X-Request-ID": ma})
    assert ph.ma == 200
    assert toi_dich_vu(ph, ma)
    assert ph.json()["username"] == "cuong.le"


def test_metrics_giu_chinh_sach_chi_quan_tri():
    """/metrics: cổng đòi token, dịch vụ đòi vai quản trị — chính sách #247 không đổi."""
    ma = ma_rieng()
    khong_quan_tri = goi(CONG_API, "/metrics", token=lay_token("cuong.le"), tieu_de={"X-Request-ID": ma})
    assert khong_quan_tri.ma == 403
    assert toi_dich_vu(khong_quan_tri, ma), "403 này phải do dịch vụ quyết, không phải cổng"

    quan_tri = goi(CONG_API, "/metrics", token=lay_token("khanh.vo"))
    assert quan_tri.ma == 200
    assert b"dxlab_http_requests_total" in quan_tri.than


# ---------------------------------------------------------------------------
# Token hết hạn: ký thật bởi Keycloak, chỉ khác ở hạn dùng
# ---------------------------------------------------------------------------


def _goi_quan_tri(url: str, token: str | None = None, *, than=None, phuong_thuc: str | None = None):
    tieu_de = {"Content-Type": "application/json"} if than is not None else {}
    if token:
        tieu_de["Authorization"] = f"Bearer {token}"
    yc = urllib.request.Request(url, data=None if than is None else json.dumps(than).encode(),
                                headers=tieu_de, method=phuong_thuc)
    with urllib.request.urlopen(yc, timeout=10) as r:
        return r.headers, r.read()


@pytest.fixture
def client_token_ngan():
    """Một client TẠM trong realm, phát access token sống 1 giây và mang aud của dịch vụ ứng dụng; gỡ
    ngay sau bài. Cần tài khoản quản trị Keycloak (mặc định của infra/.env.example)."""
    cs = get_settings()
    kc = cs.keycloak_internal_url
    try:
        du_lieu = urllib.parse.urlencode(
            {"grant_type": "password", "client_id": "admin-cli", "username": QUAN_TRI, "password": MAT_KHAU_QUAN_TRI}
        ).encode()
        with urllib.request.urlopen(f"{kc}/realms/master/protocol/openid-connect/token", data=du_lieu, timeout=10) as r:
            token_qt = json.load(r)["access_token"]
    except (urllib.error.URLError, OSError, KeyError) as loi:
        pytest.skip(f"Không đăng nhập được tài khoản quản trị Keycloak ({loi}); đặt KEYCLOAK_ADMIN_USER/PASSWORD.")

    ten = f"kiem-cong-api-{secrets.token_hex(4)}"
    bi_mat = secrets.token_urlsafe(24)
    goc = f"{kc}/admin/realms/{cs.keycloak_realm}/clients"
    tieu_de, _ = _goi_quan_tri(goc, token_qt, than={
        "clientId": ten,
        "enabled": True,
        "publicClient": False,
        "secret": bi_mat,
        "standardFlowEnabled": False,
        "directAccessGrantsEnabled": True,
        "attributes": {"access.token.lifespan": "1"},
        "protocolMappers": [{
            "name": "aud-dich-vu",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-audience-mapper",
            "config": {"included.client.audience": cs.oidc_audience, "access.token.claim": "true"},
        }],
    }, phuong_thuc="POST")
    ma_client = tieu_de["Location"].rsplit("/", 1)[-1]
    try:
        yield ten, bi_mat
    finally:
        _goi_quan_tri(f"{goc}/{ma_client}", token_qt, phuong_thuc="DELETE")


def test_token_het_han_bi_cong_chan(client_token_ngan):
    ten, bi_mat = client_token_ngan
    token = lay_token("cuong.le", client_id=ten, secret=bi_mat)
    claim = phan_claim(token)
    assert claim["exp"] - claim["iat"] <= 2, "client tạm phải phát token sống rất ngắn"

    # Cùng token, còn trong độ lệch cho phép: cổng nhận — chữ ký, nơi phát, người nhận đều đúng
    ma = ma_rieng()
    con_han = goi(CONG_API, "/me", token=token, tieu_de={"X-Request-ID": ma})
    assert con_han.ma == 200 and toi_dich_vu(con_han, ma)

    # Quá hạn cộng độ lệch: cổng chặn, dịch vụ không nhận được gì
    do_lech = int(os.environ.get("GATEWAY_TOKEN_LEEWAY_SECONDS", get_settings().oidc_leeway_seconds))
    cho = claim["exp"] + do_lech + 2 - time.time()
    if cho > 0:
        time.sleep(cho)
    ma = ma_rieng()
    het_han = goi(CONG_API, "/me", token=token, tieu_de={"X-Request-ID": ma})
    assert het_han.ma == 401
    assert not toi_dich_vu(het_han, ma)
    assert "invalid_token" in het_han.tieu_de.get("www-authenticate", "")
    # Dịch vụ gọi thẳng cũng từ chối: lớp thứ hai còn nguyên
    assert goi(DICH_VU, "/me", token=token).ma == 401


# ---------------------------------------------------------------------------
# Giới hạn tốc độ chung ở cổng
# ---------------------------------------------------------------------------


def test_vuot_nguong_bi_429_theo_tung_dia_chi():
    """Đếm theo địa chỉ người gọi. Ở cổng nội bộ (cổng người dùng gọi), địa chỉ lấy từ X-Real-IP — bài
    dùng một địa chỉ ngẫu nhiên riêng nên không chiếm hạn mức của ai. Ngưỡng đọc từ tiêu đề của cổng, nên
    bài đúng với mọi giá trị GATEWAY_RATE_LIMIT_COUNT."""
    ip = f"203.0.113.{secrets.randbelow(250) + 1}"
    dia_chi = urllib.parse.urlsplit(CONG_API_NOI_BO)
    kn = http.client.HTTPConnection(dia_chi.hostname, dia_chi.port, timeout=10)
    try:
        dau = goi(CONG_API_NOI_BO, "/health/live", tieu_de={"X-Real-IP": ip}, ket_noi=kn)
        nguong = int(dau.tieu_de["x-ratelimit-limit"])
        bi_chan: PhanHoi | None = None
        # Cửa sổ cố định: nếu cửa sổ sang lượt mới giữa chừng thì cần thêm tối đa một ngưỡng nữa
        for _ in range(2 * nguong + 5):
            ph = goi(CONG_API_NOI_BO, "/health/live", tieu_de={"X-Real-IP": ip, "X-Request-ID": "kiem-429"},
                     ket_noi=kn)
            if ph.ma == 429:
                bi_chan = ph
                break
            assert ph.ma == 200
    finally:
        kn.close()

    assert bi_chan is not None, f"không gặp 429 sau {2 * nguong + 5} lời gọi (ngưỡng {nguong})"
    assert bi_chan.tieu_de.get("x-ratelimit-remaining") == "0"
    assert "x-request-id" not in bi_chan.tieu_de, "lời gọi vượt ngưỡng đã tới dịch vụ"
    assert "error_msg" in bi_chan.json()

    # Địa chỉ khác không bị vạ lây
    assert goi(CONG_API_NOI_BO, "/health/live", tieu_de={"X-Real-IP": "198.51.100.7"}).ma == 200
    # Cổng mở ra máy KHÔNG tin X-Real-IP: cùng địa chỉ đó gửi vào đây được đếm theo địa chỉ thật của
    # container này, nên không bị chặn — người ngoài không né hay đổ được hạn mức bằng tiêu đề giả
    assert goi(CONG_API, "/health/live", tieu_de={"X-Real-IP": ip}).ma == 200
