#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Tạo hai database còn lại bên cạnh database nghiệp vụ, và cấp cho Superset
# một tài khoản CHỈ ĐỌC trên dữ liệu nghiệp vụ.
#
# PostgreSQL tự chạy mọi tệp trong /docker-entrypoint-initdb.d/ đúng một lần,
# lúc khởi tạo thực thể lần đầu. Xóa volume thì nó chạy lại.

set -euo pipefail

echo "==> Tạo database cho Keycloak và Superset"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE "${KEYCLOAK_DB_NAME}";
    CREATE DATABASE "${SUPERSET_DB_NAME}";
EOSQL

echo "==> Tạo tài khoản chỉ đọc cho Superset trên database nghiệp vụ"

# Superset chỉ được đọc. Bảng điều khiển phân tích không bao giờ ghi dữ liệu
# nghiệp vụ — ràng buộc bắt buộc trong ADR-0003.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER "${SUPERSET_READONLY_USER}"
        WITH PASSWORD '${SUPERSET_READONLY_PASSWORD}';

    GRANT CONNECT ON DATABASE "${POSTGRES_DB}"
        TO "${SUPERSET_READONLY_USER}";

    GRANT USAGE ON SCHEMA public
        TO "${SUPERSET_READONLY_USER}";

    -- Cấp quyền đọc trên các bảng đã có
    GRANT SELECT ON ALL TABLES IN SCHEMA public
        TO "${SUPERSET_READONLY_USER}";

    -- Và trên mọi bảng tạo về sau, để khỏi phải cấp lại sau mỗi lần migration
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT ON TABLES TO "${SUPERSET_READONLY_USER}";
EOSQL

echo "==> Khởi tạo cơ sở dữ liệu hoàn tất"
