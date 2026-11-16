---
title: Sự cố thường gặp
description: Dấu hiệu và cách xử lý các lỗi hay gặp khi dựng và chạy cụm.
sidebar:
  order: 3
---

| Dấu hiệu | Cách xử lý |
|---|---|
| `failed to connect to the docker API`, `Cannot connect to the Docker daemon` | Docker chưa chạy. Bật Docker Desktop, chờ nó báo đang chạy rồi chạy lại lệnh |
| `port is already allocated`, `address already in use` | Chương trình khác giữ cổng. Tắt chương trình đó, hoặc đổi biến cổng trong `.env`: `GATEWAY_PORT`, `SUPERSET_PORT`, `SEAWEEDFS_S3_PORT` đổi được; giữ nguyên 3000 và 8080. Cụm mặc định không giữ 5432 hay 8000 — chỉ tệp `docker-compose.phat-trien.yml` mở hai cổng đó (đổi bằng `POSTGRES_PORT`, `BACKEND_PORT`) |
| Đã giải phóng cổng và chạy lại `up` mà Keycloak khởi động lại liên tục với `UnknownHostException: postgres`, hoặc `frontend` báo `healthy` nhưng không mở được `http://localhost:3000` | Lần `up` hỏng vì trùng cổng để lại container đã tạo nhưng chưa nối mạng hay chưa gắn cổng; `up` lại không tạo lại chúng. Tạo lại đúng dịch vụ hỏng: `docker compose --env-file .env up -d --force-recreate --no-deps keycloak frontend` (trong `infra/`). Kiểm bằng `docker port dxlab-frontend`. Không cần `down -v`, dữ liệu giữ nguyên |
| Gọi `http://localhost:8000` không kết nối được | Đúng thiết kế: dịch vụ ứng dụng không mở cổng ra máy. Gọi API qua cổng API ở `http://localhost:9080` kèm access token; cần gọi thẳng khi phát triển thì thêm tệp `docker-compose.phat-trien.yml` — xem [Cài đặt](../cai-dat/) |
| Gọi API qua cổng `9080` nhận `401` dù có token | Token hết hạn (Keycloak cấp access token sống 5 phút), ký sai, hoặc Keycloak chưa sẵn sàng — `WWW-Authenticate` ghi lý do (`issuer validation unavailable` là cổng chưa đọc được Keycloak; tự hết khi Keycloak lên). `403` `mismatched audience` là token phát cho client khác, không mang `dx-api` |
| Gọi API qua cổng `9080` nhận `429` | Vượt giới hạn tốc độ chung của cổng API theo địa chỉ — chờ số giây ở `X-RateLimit-Reset`, hoặc nới `GATEWAY_RATE_LIMIT_COUNT` |
| Dựng hỏng giữa chừng với `no space left on device` hoặc `EOF` | Kiểm ổ chứa dữ liệu của Docker còn đủ chỗ (khoảng 6 GB), rồi chạy lại lệnh `up` — phần đã tải không phải tải lại |
| Bấm đăng nhập báo lỗi khi mở cổng từ máy khác qua địa chỉ IP | Realm mẫu chỉ nhận `localhost`. Mở `http://localhost:3000` trên chính máy đã cài |
| Sửa `infra/seed/` hay realm rồi dựng lại mà không thấy thay đổi | Dữ liệu khởi tạo chỉ nạp lần đầu. Xem [Nâng cấp](../nang-cap/) |
| Cụm không lên, nhật ký `postgres` báo lỗi bộ quy tắc | Bộ quy tắc quy trình khai sai — tệp kiểm tính nhất quán chặn khởi động. Đọc dòng lỗi, sửa `infra/seed/`, rồi `down -v` và dựng lại |
| Trang báo *hệ thống không phản hồi* | Dịch vụ ứng dụng chưa lên hoặc quá tải. Kiểm `docker compose --env-file .env ps` và nhật ký `backend` |
| Docker Desktop hiện hộp thoại lỗi có nút *Reset to factory defaults* | **Không bấm** — nút đó xóa mọi ảnh, container và dữ liệu, kể cả của dự án khác. Chờ một tới hai phút, thường tự lên lại |
