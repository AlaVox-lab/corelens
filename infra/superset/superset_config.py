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

# Miền được phép nhúng. Để rỗng nghĩa là cho phép mọi miền — chỉ chấp nhận
# được ở môi trường phát triển.
GUEST_ROLE_NAME = "Gamma"
GUEST_TOKEN_JWT_SECRET = os.environ["SUPERSET_SECRET_KEY"]
GUEST_TOKEN_JWT_EXP_SECONDS = 300

# --- Ghi chú cho bước triển khai thật ----------------------------------------
# Bản sản phẩm cần bổ sung: cấu hình bộ nhớ đệm Redis, giới hạn miền nhúng,
# và tích hợp đăng nhập một lần với Keycloak qua OAuth.
