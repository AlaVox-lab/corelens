# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử phần định danh.
#
# Hai tầng:
#
#   Đơn vị — tự sinh cặp khóa RSA rồi đúc token, nên chạy được mà không cần Keycloak.
#            Đây là nơi các phép thử ÂM sống: chữ ký giả, token hết hạn, sai người
#            nhận, sai nơi phát, và token không chữ ký.
#   Tích hợp — lấy token thật từ Keycloak đang chạy. Tự bỏ qua nếu không có cụm.
#
# Tầng đơn vị mới là tầng quan trọng: một kẻ tấn công không gửi token hợp lệ, và
# những đường tấn công kinh điển đều nằm ở đây.

from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth.identity import actor_from_claims
from app.auth.tokens import TokenInvalid, verify_token
from app.config import get_settings

TIEN_TO = "/phong-ban/"


# ---------------------------------------------------------------------------
# Dựng khóa và token giả
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def cap_khoa():
    """Một cặp khóa RSA dùng chung cho cả phiên kiểm thử."""
    rieng = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem_rieng = rieng.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return rieng, rieng.public_key(), pem_rieng


@pytest.fixture
def jwks_gia(monkeypatch, cap_khoa):
    """Thay máy khách JWKS bằng một bộ khóa cục bộ.

    Nhờ vậy phần kiểm chữ ký được kiểm thử độc lập với mạng và với Keycloak.
    """
    _, cong_khai, _ = cap_khoa

    class KhoaGia:
        key = cong_khai

    class MayKhachGia:
        def get_signing_key_from_jwt(self, token):  # noqa: ARG002
            return KhoaGia()

    monkeypatch.setattr("app.auth.tokens._jwks_client", lambda: MayKhachGia())


def _duc_token(pem_rieng, **ghi_de) -> str:
    """Đúc một access token giống hệt token thật của Keycloak."""
    cau_hinh = get_settings()
    bay_gio = dt.datetime.now(dt.UTC)

    claims = {
        "sub": "0f9c1f6a-0000-4000-8000-000000000001",
        "iss": cau_hinh.oidc_issuer,
        "aud": cau_hinh.oidc_audience,
        "iat": bay_gio,
        "exp": bay_gio + dt.timedelta(minutes=5),
        "preferred_username": "cuong.le",
        "name": "Cường Lê",
        "email": "cuong.le@dx-os-lab.test",
        "realm_access": {"roles": ["handler", "offline_access"]},
        "groups": ["/phong-ban/it"],
    }
    claims.update(ghi_de)
    return jwt.encode(claims, pem_rieng, algorithm="RS256")


# ---------------------------------------------------------------------------
# Dịch claim sang tác nhân nghiệp vụ
# ---------------------------------------------------------------------------


def test_lay_dung_vai_tro_va_phong_ban():
    actor = actor_from_claims(
        {
            "sub": "nd-001",
            "realm_access": {"roles": ["handler", "requester"]},
            "groups": ["/phong-ban/it", "/phong-ban/hr"],
        },
        department_prefix=TIEN_TO,
    )

    assert actor.id == "nd-001"
    assert actor.roles == frozenset({"handler", "requester"})
    assert actor.departments == frozenset({"it", "hr"})
    assert actor.is_system is False


def test_group_khong_dung_tien_to_bi_bo_qua():
    """Doanh nghiệp dùng cây group cho nhiều mục đích, không chỉ phòng ban."""
    actor = actor_from_claims(
        {
            "sub": "nd-001",
            "realm_access": {"roles": []},
            "groups": [
                "/phong-ban/it",
                "/du-an/dx-os",
                "/phong-ban/",
                "phong-ban/khong-co-gach-dau",
            ],
        },
        department_prefix=TIEN_TO,
    )

    assert actor.departments == frozenset({"it"})


def test_thieu_claim_vai_tro_va_group_van_dung_duoc_tac_nhan():
    """Người dùng chưa gán vai trò nào vẫn đăng nhập được, chỉ là không đi được cạnh nào."""
    actor = actor_from_claims({"sub": "nd-002"}, department_prefix=TIEN_TO)

    assert actor.id == "nd-002"
    assert actor.roles == frozenset()
    assert actor.departments == frozenset()


# ---------------------------------------------------------------------------
# Kiểm chữ ký — đường hợp lệ
# ---------------------------------------------------------------------------


def test_token_hop_le_qua_duoc(jwks_gia, cap_khoa):
    _, _, pem_rieng = cap_khoa
    claims = verify_token(_duc_token(pem_rieng))

    assert claims["preferred_username"] == "cuong.le"
    assert claims["groups"] == ["/phong-ban/it"]

    actor = actor_from_claims(claims, department_prefix=TIEN_TO)
    assert actor.roles == frozenset({"handler", "offline_access"})
    assert actor.departments == frozenset({"it"})


# ---------------------------------------------------------------------------
# Kiểm chữ ký — đường bị chặn
# ---------------------------------------------------------------------------


def test_token_sai_chu_ky_bi_tu_choi(jwks_gia):
    """Token ký bằng khóa khác hoàn toàn — đúng thứ kẻ giả mạo sẽ gửi."""
    khoa_ke_gian = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem_ke_gian = khoa_ke_gian.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    with pytest.raises(TokenInvalid):
        verify_token(_duc_token(pem_ke_gian))


def test_token_het_han_bi_tu_choi(jwks_gia, cap_khoa):
    _, _, pem_rieng = cap_khoa
    qua_khu = dt.datetime.now(dt.UTC) - dt.timedelta(hours=1)

    with pytest.raises(TokenInvalid, match="hết hạn"):
        verify_token(
            _duc_token(
                pem_rieng, iat=qua_khu, exp=qua_khu + dt.timedelta(minutes=5)
            )
        )


def test_token_sai_nguoi_nhan_bi_tu_choi(jwks_gia, cap_khoa):
    """Không kiểm `aud` thì token phát cho dịch vụ khác trong cùng realm vẫn lọt."""
    _, _, pem_rieng = cap_khoa

    with pytest.raises(TokenInvalid, match="không dành cho dịch vụ này"):
        verify_token(_duc_token(pem_rieng, aud="dich-vu-khac"))


def test_token_sai_noi_phat_bi_tu_choi(jwks_gia, cap_khoa):
    _, _, pem_rieng = cap_khoa

    with pytest.raises(TokenInvalid, match="nơi khác phát"):
        verify_token(_duc_token(pem_rieng, iss="http://keycloak-gia/realms/x"))


def test_token_thieu_claim_bat_buoc_bi_tu_choi(jwks_gia, cap_khoa):
    """Thiếu `sub` thì không biết ghi ai vào nhật ký sự kiện."""
    _, _, pem_rieng = cap_khoa
    cau_hinh = get_settings()
    bay_gio = dt.datetime.now(dt.UTC)

    thieu_sub = jwt.encode(
        {
            "iss": cau_hinh.oidc_issuer,
            "aud": cau_hinh.oidc_audience,
            "iat": bay_gio,
            "exp": bay_gio + dt.timedelta(minutes=5),
        },
        pem_rieng,
        algorithm="RS256",
    )

    with pytest.raises(TokenInvalid):
        verify_token(thieu_sub)


def test_token_khong_chu_ky_bi_tu_choi(jwks_gia):
    """Đòn kinh điển: đổi thuật toán sang `none` để bỏ hẳn phần chữ ký.

    Hàm kiểm chỉ chấp nhận RS256, nên token không chữ ký bị loại ngay.
    """
    cau_hinh = get_settings()
    bay_gio = dt.datetime.now(dt.UTC)

    khong_chu_ky = jwt.encode(
        {
            "sub": "ke-gian",
            "iss": cau_hinh.oidc_issuer,
            "aud": cau_hinh.oidc_audience,
            "iat": bay_gio,
            "exp": bay_gio + dt.timedelta(minutes=5),
            "realm_access": {"roles": ["administrator"]},
        },
        key=None,
        algorithm="none",
    )

    with pytest.raises(TokenInvalid):
        verify_token(khong_chu_ky)


# ---------------------------------------------------------------------------
# Tích hợp với Keycloak thật
# ---------------------------------------------------------------------------


def _lay_token_that(username: str, password: str = "matkhau123") -> str | None:
    """Lấy access token thật bằng luồng cấp trực tiếp.

    Luồng này bật trên `dx-portal` chỉ để bộ kiểm thử lấy được token mà không cần
    trình duyệt. Bản triển khai thật phải tắt nó đi.
    """
    cau_hinh = get_settings()
    dia_chi = os.environ.get(
        "DXLAB_OIDC_TOKEN_URL",
        cau_hinh.oidc_jwks_url.replace("/protocol/openid-connect/certs", "")
        + "/protocol/openid-connect/token",
    )

    du_lieu = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": os.environ.get("KEYCLOAK_PORTAL_CLIENT_ID", "dx-portal"),
            "client_secret": os.environ.get(
                "KEYCLOAK_PORTAL_SECRET", "doi_bi_mat_nay_truoc_khi_trien_khai"
            ),
            "username": username,
            "password": password,
            "scope": "openid",
        }
    ).encode()

    try:
        with urllib.request.urlopen(dia_chi, data=du_lieu, timeout=5) as phan_hoi:
            return json.load(phan_hoi)["access_token"]
    except (urllib.error.URLError, OSError, KeyError):
        return None


@pytest.mark.parametrize(
    ("username", "vai_tro", "phong_ban"),
    [
        ("cuong.le", "handler", {"it"}),
        ("dung.pham", "approver", {"it"}),
        ("ha.do", "handler", {"hr"}),
        ("binh.tran", "classifier", set()),
    ],
)
def test_token_that_tu_keycloak(username, vai_tro, phong_ban):
    """Token thật từ Keycloak qua được toàn bộ chuỗi kiểm và cho đúng tác nhân.

    Bài này kiểm cả những thứ mà token tự đúc không kiểm được: protocol mapper có
    đưa group vào token không, `aud` có mang tên dịch vụ không, và `iss` có khớp
    địa chỉ công khai không.
    """
    token = _lay_token_that(username)
    if token is None:
        pytest.skip(
            "Không lấy được token từ Keycloak. Dựng cụm bằng: "
            "cd infra && docker compose --env-file .env up -d keycloak"
        )

    claims = verify_token(token)
    actor = actor_from_claims(claims)

    assert claims["preferred_username"] == username
    assert vai_tro in actor.roles
    assert actor.departments == phong_ban
