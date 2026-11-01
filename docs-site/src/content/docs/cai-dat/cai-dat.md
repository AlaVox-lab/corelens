---
title: Cài đặt
description: Yêu cầu máy, hai cách cài (từ bản phát hành, từ kho mã), kiểm cụm và các dịch vụ sau khi dựng.
sidebar:
  order: 1
---

Cả cụm sáu dịch vụ dựng bằng **một lệnh** Docker Compose, không cần cài thêm gì trên máy ngoài
Docker.

## Yêu cầu môi trường

| Thành phần | Yêu cầu |
|---|---|
| Docker | Docker Desktop trên Windows và macOS, hoặc Docker Engine 24 trở lên trên Linux — kèm Docker Compose v2. Kiểm bằng `docker compose version` |
| Bộ nhớ cấp cho Docker | khoảng **2 GB** khi cả cụm chạy — đo lúc rảnh được 1,4 GB, Keycloak chiếm gần một nửa |
| Ổ đĩa trống | khoảng **6 GB** cho ảnh chứa và dữ liệu, tính trên ổ chứa dữ liệu của Docker |
| Mạng | cần Internet ở lần dựng đầu để tải ảnh chứa và thư viện; các lần sau không cần |
| Cổng cần trống | 3000 · 5432 · 8000 · 8080 · 8088 · 8333 |

## Cách 1 — cài từ bản phát hành

Dành cho người chỉ muốn dựng và dùng thử. Không cần Git.

1. Mở trang [Releases](https://github.com/AlaVox-lab/dx-os-lab/releases), chọn bản mang nhãn
   **Latest**, tải tệp **Source code (tar.gz)**
2. Bật Docker Desktop và chờ tới khi nó báo đang chạy
3. Mở terminal ở thư mục chứa tệp vừa tải và chạy bốn lệnh dưới. Thay `0.7.0` bằng phiên bản đã
   tải — tệp nén giải ra thư mục `dx-os-lab-<phiên bản>`, không phải `dx-os-lab`

Windows — PowerShell (Windows 10 và 11 có sẵn lệnh `tar`):

```powershell
tar -xzf dx-os-lab-0.7.0.tar.gz
cd dx-os-lab-0.7.0\infra
Copy-Item .env.example .env
docker compose --env-file .env up -d --build
```

Linux và macOS:

```bash
tar -xzf dx-os-lab-0.7.0.tar.gz
cd dx-os-lab-0.7.0/infra
cp .env.example .env
docker compose --env-file .env up -d --build
```

## Cách 2 — cài từ kho mã

Dành cho người sẽ sửa mã và gửi đóng góp. Cần thêm Git.

```bash
git clone https://github.com/AlaVox-lab/dx-os-lab.git
cd dx-os-lab/infra
cp .env.example .env
docker compose --env-file .env up -d --build
```

Lần dựng đầu mất khoảng **10–20 phút** tùy tốc độ mạng: tải ảnh chứa và dựng ba ảnh — dịch vụ ứng
dụng, cổng người dùng, và ảnh dẫn xuất cho Superset.

## Kiểm cụm đã lên

```bash
docker compose --env-file .env ps
```

Chạy trong thư mục `infra`. Bốn dịch vụ `postgres`, `backend`, `frontend`, `superset` phải báo
`healthy`; `keycloak` và `seaweedfs` báo `Up`. Keycloak cần thêm khoảng một phút mới nhận đăng
nhập.

Kiểm sâu hơn: đăng nhập bằng tài khoản quản trị viên `khanh.vo` rồi mở màn **Hệ thống**
(`http://localhost:3000/he-thong`) — màn báo trạng thái từng tầng, kể cả việc bộ quy tắc quy
trình đã nạp đủ hay chưa. Chưa đăng nhập thì xem `http://localhost:8000/health`.

:::note
Nếu bộ quy tắc quy trình khai sai — có ngõ cụt, có trạng thái không tới được, có bước không vai
nào đi được — **cụm dừng khởi động** thay vì chạy với luồng hỏng. Xem nhật ký bằng
`docker compose --env-file .env logs postgres`.
:::

## Các dịch vụ sau khi dựng xong

| Dịch vụ | Địa chỉ | Tài khoản mặc định |
|---|---|---|
| **Cổng người dùng** | `http://localhost:3000` | tài khoản mẫu, xem [Tài khoản mẫu](../../huong-dan/tai-khoan-mau/) |
| **Dịch vụ ứng dụng** — tài liệu API | `http://localhost:8000/docs` | — |
| Keycloak — định danh | `http://localhost:8080` | `admin` / `admin` |
| Apache Superset — báo cáo | `http://localhost:8088` | `admin` / `admin` |
| SeaweedFS — lưu trữ tệp, S3 API | `http://localhost:8333` | xem `.env` |
| PostgreSQL | `localhost:5432` | xem `.env` |

:::caution[Bảo mật]
Mọi mật khẩu trong `.env.example` là giá trị mẫu công khai, chỉ dùng để thử. Bắt buộc thay trước
khi triển khai thật. Tệp `.env` thật không bao giờ được commit lên kho mã.
:::
