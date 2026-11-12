# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ảnh dẫn xuất của Apache Superset. Bổ sung hai thứ ảnh gốc không có:
#
#   1. Trình điều khiển PostgreSQL. Ảnh chính thức KHÔNG kèm psycopg2, nên thêm
#      cơ sở dữ liệu PostgreSQL vào giao diện sẽ thất bại với thông báo mơ hồ
#      "Connection failed, please check your connection settings".
#      Phát hiện này ghi trong docs/bi-platform-survey.md mục 5.3.
#
#   2. Bước khởi tạo lược đồ và tài khoản quản trị. Ảnh gốc chỉ chạy máy chủ,
#      không tự chạy `superset db upgrade` lẫn `fab create-admin`.
#
# Ảnh gốc dùng môi trường ảo tại /app/.venv và KHÔNG có pip trong đó, nên phải
# cài bằng uv.

ARG SUPERSET_VERSION=6.1.0
# Mã băm của chỉ mục ảnh `apache/superset:6.1.0` (bản dựng 31/08/2026) — thẻ trên Docker Hub có thể bị
# đẩy lại, mã băm thì không. Đổi SUPERSET_VERSION thì phải đổi cả mã băm này
# (`docker buildx imagetools inspect apache/superset:<thẻ>`).
ARG SUPERSET_DIGEST=sha256:59cd4af66006fe4cc98906eda42a771dbefdacb432f9ab083e02cdc6ff01f29d
FROM apache/superset:${SUPERSET_VERSION}@${SUPERSET_DIGEST}

# Ghim phiên bản bằng == để mọi lần dựng đều cho ra cùng một bộ thư viện.
# Không ghim thì mỗi người và ban giám khảo nhận một phiên bản khác nhau,
# làm hỏng khả năng dựng lại từ mã nguồn — tiêu chí PoF mục 4.
ARG PSYCOPG2_VERSION=2.9.13

USER root

RUN VIRTUAL_ENV=/app/.venv uv pip install --no-cache \
        "psycopg2-binary==${PSYCOPG2_VERSION}"

COPY superset_config.py   /app/pythonpath/superset_config.py
COPY bang-dieu-khien      /app/dxlab/bang-dieu-khien
COPY cap_quyen_khach.py   /app/dxlab/cap_quyen_khach.py
COPY docker-entrypoint.sh /usr/local/bin/dxlab-entrypoint.sh
RUN chmod +x /usr/local/bin/dxlab-entrypoint.sh

USER superset

ENV SUPERSET_CONFIG_PATH=/app/pythonpath/superset_config.py

CMD ["/usr/local/bin/dxlab-entrypoint.sh"]
