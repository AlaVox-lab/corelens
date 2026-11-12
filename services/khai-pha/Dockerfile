# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 AlaVox-lab
#
# Ảnh chứa của dịch vụ khai phá quy trình (#314, ADR-0007). Dịch vụ riêng, thư mục riêng, ảnh riêng:
# ranh giới để thư viện AGPL pm4py không bao giờ nằm trong ảnh của dịch vụ ứng dụng hay cổng.

FROM python:3.13.17-slim@sha256:d98cc29d3266e535dd9da1099688d9cb3ca4753813571e071763d17725460962

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt

# Lần nạp pm4py đầu tiên biên dịch mã mất cả phút (đo ở #48: 95 giây). Biên dịch sẵn lúc dựng ảnh để
# dịch vụ khởi động trong vài giây.
RUN python -c "import pm4py" 2>/dev/null || true

COPY . ./

RUN useradd --create-home --shell /bin/bash khaipha \
    && chown --recursive khaipha:khaipha /app
USER khaipha

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
