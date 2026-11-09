# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Cấu hình quy trình sống được qua nâng cấp (#254).
#
# Lược đồ cấu hình do Alembic quản lý từ bản sửa gốc 0000. Gói này lo phần dữ liệu:
#
#   khoi_tao   — nạp dữ liệu khởi tạo từ infra/seed/ lần đầu, và kiểm nhất quán mỗi lần khởi động
#   bo_quy_tac — chép một bộ quy tắc thành phiên bản mới rồi kích hoạt, dùng trong bản sửa dữ liệu
