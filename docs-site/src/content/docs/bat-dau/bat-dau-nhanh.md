---
title: Bắt đầu nhanh
description: Dựng cả cụm bằng một lệnh, đăng nhập bằng tài khoản mẫu và đi trọn một hồ sơ.
sidebar:
  order: 2
---

Khoảng 20 phút, phần lớn là chờ tải ảnh chứa ở lần đầu.

## 1. Chuẩn bị

- **Docker Desktop** (Windows, macOS) hoặc Docker Engine 24 trở lên kèm Docker Compose v2 (Linux)
- Khoảng **2 GB** bộ nhớ và **6 GB** ổ đĩa trống cho Docker
- Các cổng 3000, 8080, 8088, 8333, 9080 đang trống

Chi tiết ở [Cài đặt](../../cai-dat/cai-dat/).

## 2. Dựng cụm

Tải tệp **Source code (tar.gz)** của bản mới nhất ở trang
[Releases](https://github.com/AlaVox-lab/dx-os-lab/releases), bật Docker, rồi chạy (thay `0.7.0`
bằng phiên bản đã tải):

```bash
tar -xzf dx-os-lab-0.7.0.tar.gz
cd dx-os-lab-0.7.0/infra
cp .env.example .env
docker compose --env-file .env up -d --build
```

Trên PowerShell thay `cp` bằng `Copy-Item` và dùng dấu `\` trong đường dẫn. Mọi giá trị trong
`.env.example` chạy được ngay.

Kiểm cụm đã lên: `docker compose --env-file .env ps` — `postgres`, `backend`, `cong-api`, `frontend`,
`superset`, `khai-pha` báo `healthy`; `keycloak`, `seaweedfs` báo `Up`. Chờ thêm khoảng một phút cho
Keycloak.

## 3. Đi trọn một hồ sơ

Mở `http://localhost:3000`, bấm **Đăng nhập bằng tài khoản công ty**. Mọi tài khoản mẫu dùng mật
khẩu `matkhau123`. Mỗi tài khoản dùng một cửa sổ ẩn danh riêng.

1. **`an.nguyen`** (người gửi) — *Gửi yêu cầu* → chọn **Sự cố thiết bị** → điền tiêu đề, mô tả, mã
   tài sản, vị trí → xem lại → gửi
2. **`binh.tran`** (điều phối viên) — trang chủ thấy hồ sơ mới ở *Cần bạn xử lý* → **Phân loại yêu
   cầu**, đặt mức ưu tiên → **Chuyển về phòng ban**, chọn *Công nghệ thông tin*
3. **`dung.pham`** (trưởng phòng CNTT) — **Xác duyệt và giao xử lý**, chọn `cuong.le`. Đồng hồ hạn
   bắt đầu chạy từ đây
4. **`cuong.le`** (người xử lý) — **Hoàn thành xử lý**
5. **`an.nguyen`** — **Xác nhận đạt**. Hồ sơ sang *Đã đóng*

Mở **dòng thời gian** của hồ sơ để xem từng bước: ai bấm, lúc nào, giá trị nào đổi.

## Tiếp theo

- Thử các nhánh: hỏi thêm thông tin, phòng từ chối, quá hạn, mở lại — [Hướng dẫn sử dụng](../../huong-dan/nguoi-gui/)
- Đổi quy trình cho doanh nghiệp của bạn — [Tùy biến quy trình](../../quan-tri/tuy-bien-quy-trinh/)
- Dừng cụm: `docker compose --env-file .env down` (giữ dữ liệu) hoặc thêm `-v` (xóa sạch)
