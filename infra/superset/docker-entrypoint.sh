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

# Bảng điều khiển phân tích (#304) nằm trong kho dưới dạng tệp YAML — kết nối dữ liệu, dataset,
# biểu đồ, dashboard — để cụm dựng mới có sẵn bảng điều khiển, không ai phải tạo tay. Nạp đè
# mỗi lần khởi động theo uuid: tệp trong kho là nguồn sự thật, sửa trên giao diện mà không xuất
# lại thì lần khởi động sau mất. Chuỗi kết nối chỉ ghi chỗ giữ chỗ, mật khẩu thật lấy từ biến
# môi trường lúc chạy.
echo "==> Nạp bảng điều khiển từ tệp cấu hình"
rm -rf /tmp/bang-dieu-khien
cp -r /app/dxlab/bang-dieu-khien /tmp/bang-dieu-khien
python - <<'PY'
import os, pathlib
tep = pathlib.Path("/tmp/bang-dieu-khien/databases/du-lieu-nghiep-vu.yaml")
tep.write_text(
    tep.read_text(encoding="utf-8").replace("__SUPERSET_READONLY_URI__", os.environ["SUPERSET_READONLY_URI"]),
    encoding="utf-8",
)
PY
superset import-directory --overwrite /tmp/bang-dieu-khien
rm -rf /tmp/bang-dieu-khien

# Bảng điều khiển nhúng trong cổng (#305) vẽ bằng token khách: vai khách cần quyền đọc kết nối
# dữ liệu vừa nạp, ảnh gốc không cấp. Chạy sau bước nạp vì quyền gắn theo tên kết nối.
echo "==> Cấp quyền đọc cho vai khách của bảng điều khiển nhúng"
python /app/dxlab/cap_quyen_khach.py

echo "==> Bàn giao cho máy chủ"
exec /app/docker/entrypoints/run-server.sh
