# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ảnh chứa cho dịch vụ ứng dụng.
#
# Ghim phiên bản ảnh nền bằng thẻ cụ thể, không dùng `latest`. Ban giám khảo dựng lại
# sau nhiều tháng phải nhận đúng bộ phiên bản mà nhóm đã kiểm chứng.

FROM python:3.13.17-slim@sha256:d98cc29d3266e535dd9da1099688d9cb3ca4753813571e071763d17725460962

# Không sinh tệp .pyc, không đệm đầu ra — nhật ký hiện ngay trong docker logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Chép riêng tệp phụ thuộc trước mã nguồn để Docker tái dùng được lớp cài đặt khi
# chỉ mã nguồn thay đổi. Sửa một dòng mã mà phải cài lại toàn bộ thư viện thì mỗi
# lần dựng mất vài phút.
COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt

COPY . ./

# Git trên Windows không giữ được bit cho phép chạy, nên đặt lại ngay trong ảnh chứa.
# Cùng cách mà infra/superset/Dockerfile đang dùng.
RUN chmod +x /app/docker-entrypoint.sh

# Chạy bằng tài khoản thường, không phải root. Một tiến trình bị chiếm quyền thì
# thiệt hại giới hạn trong phạm vi tài khoản đó.
RUN useradd --create-home --shell /bin/bash dxlab \
    && chown --recursive dxlab:dxlab /app
USER dxlab

EXPOSE 8000

# Dùng chính Python để kiểm tra sức khỏe, khỏi cài thêm curl vào ảnh. Điểm cuối "sẵn sàng" (#247)
# trả 503 khi cơ sở dữ liệu hỏng hay bộ quy tắc chưa nạp, nên container báo unhealthy đúng lúc — khác
# với bẫy đã gặp ở Superset — và cổng, Superset chờ `service_healthy` là chờ dịch vụ làm được việc.
# `/health/live` (không chạm cơ sở dữ liệu) dành cho bộ điều phối có tách hai khái niệm, như Kubernetes.
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health/ready', timeout=4).status == 200 else 1)"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
