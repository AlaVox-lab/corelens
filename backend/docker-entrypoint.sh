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

# Từ #254 Alembic sở hữu cả lược đồ cấu hình của engine (bản sửa gốc 0000), nên cụm dựng
# mới đi trọn chuỗi từ cơ sở dữ liệu trống, còn cụm cũ chỉ chạy các bản sửa còn thiếu.
alembic upgrade head

echo "==> Nạp và kiểm tra cấu hình quy trình"

# Lần đầu nạp dữ liệu khởi tạo từ /seed (infra/seed/); lần nào cũng kiểm nhất quán đồ thị.
# Cấu hình hỏng thì lệnh thoát mã lỗi và dịch vụ không lên — xem app/cau_hinh/khoi_tao.py.
python -m app.cau_hinh.khoi_tao

echo "==> Khởi động máy chủ ứng dụng"

# Không dùng dòng truy cập của uvicorn: lớp giữa app/quan_sat.py ghi dòng truy cập dạng JSON, mang
# mã yêu cầu và thời gian xử lý (#247)
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --proxy-headers \
    --no-access-log
