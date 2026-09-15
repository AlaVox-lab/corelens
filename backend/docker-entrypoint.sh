#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Điểm vào của ảnh chứa dịch vụ ứng dụng.
#
# Chạy migration trước rồi mới khởi động máy chủ. Thứ tự này bảo đảm ứng dụng không
# bao giờ phục vụ yêu cầu trên một lược đồ cũ.

set -euo pipefail

echo "==> Áp dụng migration"

# Hiện chưa có bản sửa nào: lược đồ cấu hình của engine máy trạng thái do PostgreSQL
# tạo lúc khởi tạo thực thể, và Alembic được cấu hình bỏ qua mười một bảng đó — xem
# alembic/env.py. Lệnh dưới đây là lệnh rỗng cho tới khi #41 thêm bảng hồ sơ và bảng
# nhật ký sự kiện. Đặt sẵn để không ai quên khi tới lúc đó.
alembic upgrade head

echo "==> Khởi động máy chủ ứng dụng"

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --proxy-headers
