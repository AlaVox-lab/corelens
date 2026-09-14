#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Nạp dữ liệu khởi tạo từ thư mục infra/seed/ vào database nghiệp vụ.
#
# Vì sao cần kịch bản này thay vì để thẳng các tệp .sql vào thư mục khởi tạo:
# PostgreSQL chỉ quét tầng trên cùng của /docker-entrypoint-initdb.d/. Dữ liệu
# khởi tạo được tách sang infra/seed/ vì đó là phần doanh nghiệp khác sẽ sửa khi
# tùy biến sản phẩm — để lẫn với lược đồ thì họ phải dò giữa hai loại nội dung
# hoàn toàn khác nhau. Kịch bản này bắc cầu giữa hai nơi.
#
# Thêm một tệp dữ liệu khởi tạo mới KHÔNG cần sửa docker-compose.yml: cứ thả vào
# infra/seed/ với tiền tố số để định thứ tự nạp.

set -euo pipefail

SEED_DIR=/seed

if [ ! -d "$SEED_DIR" ]; then
    echo "==> Không thấy $SEED_DIR, bỏ qua bước nạp dữ liệu khởi tạo"
    exit 0
fi

echo "==> Nạp dữ liệu khởi tạo từ $SEED_DIR"

shopt -s nullglob
for tep in "$SEED_DIR"/*.sql; do
    echo "    - $(basename "$tep")"
    psql -v ON_ERROR_STOP=1 \
        --username "$POSTGRES_USER" \
        --dbname "$POSTGRES_DB" \
        --quiet \
        -f "$tep"
done

echo "==> Nạp dữ liệu khởi tạo hoàn tất"
