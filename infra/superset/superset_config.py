# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Cấu hình Apache Superset cho DX-OS Lab.
#
# Superset KHÔNG đọc biến môi trường tuỳ ý — nó nạp cấu hình từ tệp Python trỏ bởi
# SUPERSET_CONFIG_PATH. Đặt SQLALCHEMY_DATABASE_URI trực tiếp bằng biến môi trường
# sẽ bị bỏ qua âm thầm và Superset lặng lẽ quay về SQLite.

import os

# --- Kho siêu dữ liệu của chính Superset -------------------------------------
# Trỏ vào database `superset` trên thực thể PostgreSQL dùng chung.
SQLALCHEMY_DATABASE_URI = os.environ["SUPERSET_DATABASE_URI"]

# --- Khoá ký phiên -----------------------------------------------------------
SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

# --- Nhúng bảng điều khiển vào cổng người dùng -------------------------------
# Đây là lý do chọn Superset thay vì Metabase: khả năng nhúng nằm trong bản
# nguồn mở, không bị khoá sau giấy phép trả phí. Xem ADR-0003.
FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,
}

# Người xem trong cổng nhận token khách do dịch vụ ứng dụng xin thay (#305), không đăng nhập
# Superset. Vai khách được đọc kết nối dữ liệu nghiệp vụ — điểm vào cấp quyền đó sau khi nạp
# bảng điều khiển (cap_quyen_khach.py); phạm vi phòng ban do dịch vụ gắn vào từng token.
# Token sống 5 phút, thư viện nhúng phía cổng tự xin lại trước khi hết hạn.
GUEST_ROLE_NAME = "Gamma"
GUEST_TOKEN_JWT_SECRET = os.environ["SUPERSET_SECRET_KEY"]
GUEST_TOKEN_JWT_EXP_SECONDS = 300

# Chỉ cổng người dùng được đặt Superset trong khung. Mặc định Superset trả
# `X-Frame-Options: SAMEORIGIN`, khung nhúng ở cổng 3000 bị trình duyệt chặn. `frame-ancestors`
# của CSP thay chỗ tiêu đề đó ở mọi trình duyệt hiện hành; tiêu đề cũ vẫn giữ cho trình duyệt
# không hiểu CSP. Phần còn lại chép từ cấu hình mặc định của Superset 6.1, bỏ các máy chủ bản đồ
# và ảnh bên ngoài mà bảng điều khiển này không dùng; giữ các máy chủ phông chữ của chủ đề.
_PHONG_CHU = [
    "https://fonts.googleapis.com",
    "https://fonts.gstatic.com",
    "https://use.typekit.net",
    "https://use.typekit.com",
]
TALISMAN_CONFIG = {
    "content_security_policy": {
        "base-uri": ["'self'"],
        "default-src": ["'self'"],
        "img-src": ["'self'", "blob:", "data:"],
        "worker-src": ["'self'", "blob:"],
        "connect-src": ["'self'"],
        "object-src": "'none'",
        "style-src": ["'self'", "'unsafe-inline'", *_PHONG_CHU],
        "font-src": ["'self'", *_PHONG_CHU],
        "script-src": ["'self'", "'strict-dynamic'"],
        "frame-ancestors": ["'self'", os.environ["PORTAL_PUBLIC_URL"]],
    },
    "content_security_policy_nonce_in": ["script-src"],
    "force_https": False,
    "session_cookie_secure": False,
}

# --- Ghi chú cho bước triển khai thật ----------------------------------------
# Bản sản phẩm cần bổ sung: cấu hình bộ nhớ đệm Redis, giới hạn miền nhúng,
# và tích hợp đăng nhập một lần với Keycloak qua OAuth.
