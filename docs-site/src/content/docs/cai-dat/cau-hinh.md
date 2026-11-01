---
title: Cấu hình
description: Các biến trong infra/.env — cổng, mật khẩu, giới hạn tệp đính kèm, bộ quét hạn — và phần nào phải đổi trước khi triển khai thật.
sidebar:
  order: 2
---

Cấu hình **vận hành** nằm trong `infra/.env`, chép từ `infra/.env.example`. Cấu hình **nghiệp vụ**
— trạng thái, vai trò, hạn xử lý, phòng ban, loại yêu cầu — không nằm ở đây mà trong dữ liệu khởi
tạo, xem [Tùy biến quy trình](../../quan-tri/tuy-bien-quy-trinh/).

Đổi `.env` thì khởi động lại dịch vụ liên quan bằng `docker compose --env-file .env up -d`; không
cần xóa dữ liệu.

## Phải đổi trước khi triển khai thật

| Biến | Vì sao |
|---|---|
| `DXLAB_DB_PASSWORD`, `SUPERSET_READONLY_PASSWORD` | Mật khẩu cơ sở dữ liệu |
| `KEYCLOAK_ADMIN_PASSWORD`, `SUPERSET_ADMIN_PASSWORD` | Tài khoản quản trị Keycloak, Superset (mẫu là `admin`) |
| `SEAWEEDFS_SECRET_KEY` | Khóa S3 của kho tệp — phải khớp `infra/seaweedfs/s3-config.json` |
| `KEYCLOAK_PORTAL_SECRET`, `KEYCLOAK_DIRECTORY_SECRET` | Bí mật hai client — phải khớp `infra/keycloak/realm-dx-os-lab.json` |
| `PORTAL_SESSION_SECRET` | Khóa mã hóa cookie phiên của cổng — sinh bằng `openssl rand -base64 32` |
| `SUPERSET_SECRET_KEY` | Khóa ký phiên của Superset — sinh bằng `openssl rand -base64 42` |

## Cổng

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `FRONTEND_PORT` | `3000` | Cổng người dùng. Giữ nguyên khi dùng realm mẫu — địa chỉ chuyển hướng đăng nhập gắn với cổng này |
| `KEYCLOAK_PORT` | `8080` | Giữ nguyên khi dùng realm mẫu, cùng lý do |
| `BACKEND_PORT` | `8000` | Dịch vụ ứng dụng, tài liệu API ở `/docs` |
| `POSTGRES_PORT` | `5432` | Đổi nếu máy đã có PostgreSQL giữ cổng này |
| `SUPERSET_PORT` | `8088` | |
| `SEAWEEDFS_S3_PORT` | `8333` | |

## Tệp đính kèm

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `ATTACHMENT_ALLOWED_EXTENSIONS` | ảnh, PDF, Word, Excel, văn bản, CSV | Cố ý không có `zip`, `exe`, `bat`, `js`, `sh`. Dịch vụ còn kiểm nội dung khớp đuôi |
| `ATTACHMENT_MAX_MB` | `10` | Mỗi tệp |
| `ATTACHMENT_MAX_FILES` | `5` | Mỗi lần tải |
| `ATTACHMENT_MAX_FILES_PER_CASE` | `20` | Mỗi hồ sơ |
| `SEAWEEDFS_BUCKET` | `dxlab-attachments` | Đổi tên thùng thì đổi cả quyền trong `infra/seaweedfs/s3-config.json` |

Giao diện hỏi dịch vụ các giới hạn này, nên đổi một chỗ là hai lớp chặn cùng đổi.

## Định danh

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `KEYCLOAK_REALM` | `dx-os-lab` | Realm nạp từ `infra/keycloak/realm-dx-os-lab.json` |
| `KEYCLOAK_DEPARTMENT_GROUP_PREFIX` | `/phong-ban/` | Phòng ban là nhóm Keycloak dưới đường dẫn này. Tổ chức cây nhóm khác thì đổi ở đây |
| `KEYCLOAK_MAX_HEAP` | `768m` | Keycloak là dịch vụ nặng nhất cụm; dưới `512m` khởi động chậm hẳn |

## Bộ quét hạn

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `SLA_SCAN_ENABLED` | `true` | Bộ quét nền tự leo thang hồ sơ quá hạn và đi các bước tự động khi hồ sơ nằm im |
| `SLA_SCAN_INTERVAL_SECONDS` | `60` | Hạ xuống `5` khi cần trình diễn leo thang mà không phải chờ |

Ngưỡng hạn của từng loại yêu cầu **không** nằm ở đây — xem
[Danh mục và các con số](../../quan-tri/danh-muc-va-con-so/).
