# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm chữ ký token OIDC.
#
# Nguyên tắc từ ADR-0001: dịch vụ ứng dụng **tự kiểm chữ ký cục bộ**, không gọi ngược
# sang Keycloak ở mỗi yêu cầu. Keycloak nằm ngoài đường đi nóng, nên nó chậm hay khởi
# động lại cũng không làm cả hệ thống đứng.
#
# Khóa công khai tải một lần qua JWKS rồi giữ trong bộ nhớ. Khi Keycloak xoay khóa,
# token mới mang `kid` lạ và thư viện tự đi lấy lại bộ khóa — không cần khởi động lại
# dịch vụ, cũng không cần hẹn giờ làm mới.

from __future__ import annotations

from functools import lru_cache

import jwt
from jwt import PyJWKClient

from app.config import get_settings


class TokenInvalid(Exception):
    """Token không hợp lệ: sai chữ ký, hết hạn, sai người nhận, hoặc sai nơi phát."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@lru_cache
def _jwks_client() -> PyJWKClient:
    """Máy khách JWKS dùng chung cho cả vòng đời tiến trình.

    `lru_cache` giữ đúng một thực thể, nhờ đó bộ nhớ đệm khóa không bị dựng lại ở mỗi
    yêu cầu — nếu không thì mỗi yêu cầu lại là một lần gọi mạng sang Keycloak, đúng
    thứ mà ADR-0001 muốn tránh.
    """
    cau_hinh = get_settings()
    return PyJWKClient(
        cau_hinh.oidc_jwks_url,
        cache_keys=True,
        max_cached_keys=16,
    )


def verify_token(token: str) -> dict:
    """Kiểm một access token và trả về phần claim đã được xác thực.

    Kiểm đủ bốn thứ: chữ ký, hạn dùng, nơi phát (`iss`) và người nhận (`aud`). Bỏ sót
    `aud` là lỗi hay gặp — khi đó một token phát cho dịch vụ khác trong cùng realm vẫn
    lọt qua.
    """
    cau_hinh = get_settings()

    try:
        khoa = _jwks_client().get_signing_key_from_jwt(token)
    except Exception as loi:  # noqa: BLE001 — mọi trục trặc lấy khóa đều là token hỏng
        raise TokenInvalid(f"Không lấy được khóa công khai để kiểm token: {loi}") from loi

    try:
        return jwt.decode(
            token,
            khoa.key,
            algorithms=["RS256"],
            issuer=cau_hinh.oidc_issuer,
            audience=cau_hinh.oidc_audience,
            leeway=cau_hinh.oidc_leeway_seconds,
            options={
                "require": ["exp", "iat", "iss", "aud", "sub"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )
    except jwt.ExpiredSignatureError as loi:
        raise TokenInvalid("Token đã hết hạn.") from loi
    except jwt.InvalidAudienceError as loi:
        raise TokenInvalid(
            f"Token không dành cho dịch vụ này (cần aud = '{cau_hinh.oidc_audience}')."
        ) from loi
    except jwt.InvalidIssuerError as loi:
        raise TokenInvalid(
            f"Token do nơi khác phát (cần iss = '{cau_hinh.oidc_issuer}')."
        ) from loi
    except jwt.InvalidTokenError as loi:
        raise TokenInvalid(f"Token không hợp lệ: {loi}") from loi
