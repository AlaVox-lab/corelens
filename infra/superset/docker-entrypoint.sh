#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Khởi tạo Superset rồi bàn giao cho tiến trình phục vụ gốc của ảnh chứa.
#
# Ảnh chính thức chỉ chạy máy chủ, KHÔNG tự tạo lược đồ cơ sở dữ liệu và cũng
# không tạo tài khoản quản trị. Thiếu bước này thì Superset vẫn trả HTTP 200 ở
# điểm cuối sức khoẻ nhưng không ai đăng nhập được, và nhật ký chỉ ghi một dòng
# "Pending database migrations" rất dễ bỏ sót.

set -euo pipefail

echo "==> Nâng cấp lược đồ cơ sở dữ liệu của Superset"
superset db upgrade

echo "==> Bảo đảm có tài khoản quản trị"
# Lệnh này báo lỗi nếu tài khoản đã tồn tại, nên nuốt lỗi để container khởi
# động lại được nhiều lần mà không hỏng.
superset fab create-admin \
    --username "${SUPERSET_ADMIN_USER}" \
    --password "${SUPERSET_ADMIN_PASSWORD}" \
    --firstname "Quan" \
    --lastname "Tri" \
    --email "admin@dx-os-lab.test" || echo "    (tài khoản đã tồn tại, bỏ qua)"

echo "==> Khởi tạo vai trò và quyền mặc định"
superset init

echo "==> Bàn giao cho máy chủ"
exec /app/docker/entrypoints/run-server.sh
