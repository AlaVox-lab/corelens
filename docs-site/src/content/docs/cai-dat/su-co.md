---
title: Sự cố thường gặp
description: Dấu hiệu và cách xử lý các lỗi hay gặp khi dựng và chạy cụm.
sidebar:
  order: 3
---

| Dấu hiệu | Cách xử lý |
|---|---|
| `failed to connect to the docker API`, `Cannot connect to the Docker daemon` | Docker chưa chạy. Bật Docker Desktop, chờ nó báo đang chạy rồi chạy lại lệnh |
| `port is already allocated`, `address already in use` | Chương trình khác giữ cổng — thường là PostgreSQL cài sẵn giữ 5432. Tắt chương trình đó, hoặc đổi `POSTGRES_PORT` trong `.env`. Đổi được tương tự `BACKEND_PORT`, `SUPERSET_PORT`, `SEAWEEDFS_S3_PORT`; giữ nguyên 3000 và 8080 |
| Dựng hỏng giữa chừng với `no space left on device` hoặc `EOF` | Kiểm ổ chứa dữ liệu của Docker còn đủ chỗ (khoảng 6 GB), rồi chạy lại lệnh `up` — phần đã tải không phải tải lại |
| Bấm đăng nhập báo lỗi khi mở cổng từ máy khác qua địa chỉ IP | Realm mẫu chỉ nhận `localhost`. Mở `http://localhost:3000` trên chính máy đã cài |
| Sửa `infra/seed/` hay realm rồi dựng lại mà không thấy thay đổi | Dữ liệu khởi tạo chỉ nạp lần đầu. Xem [Nâng cấp](../nang-cap/) |
| Cụm không lên, nhật ký `postgres` báo lỗi bộ quy tắc | Bộ quy tắc quy trình khai sai — tệp kiểm tính nhất quán chặn khởi động. Đọc dòng lỗi, sửa `infra/seed/`, rồi `down -v` và dựng lại |
| Trang báo *hệ thống không phản hồi* | Dịch vụ ứng dụng chưa lên hoặc quá tải. Kiểm `docker compose --env-file .env ps` và nhật ký `backend` |
| Docker Desktop hiện hộp thoại lỗi có nút *Reset to factory defaults* | **Không bấm** — nút đó xóa mọi ảnh, container và dữ liệu, kể cả của dự án khác. Chờ một tới hai phút, thường tự lên lại |
