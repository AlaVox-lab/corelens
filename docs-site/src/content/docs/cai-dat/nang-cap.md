---
title: Nâng cấp
description: Lên bản mới mà không mất dữ liệu, cách tự kiểm, và những bản cũ vẫn phải dựng lại.
sidebar:
  order: 4
---

## Từ v0.9.1 trở đi: dựng lại là xong

Cụm dựng từ `v0.9.1` trở đi lên bản mới **giữ nguyên hồ sơ, nhật ký sự kiện, lời nhắn và tệp đính
kèm**. Lý do:

| Phần | Nạp thế nào |
|---|---|
| **Lược đồ** — mọi bảng, kể cả bảng cấu hình quy trình | Migration trong `backend/alembic/versions/`, tự chạy lúc dịch vụ ứng dụng khởi động; chỉ bản còn thiếu được chạy |
| **Dữ liệu khởi tạo** — `infra/seed/` | Dịch vụ ứng dụng nạp **lần đầu**, khi cơ sở dữ liệu chưa có bộ quy tắc nào; lần sau không nạp lại |
| **Đổi quy trình** của một bản mới | Bản sửa dữ liệu tạo bộ quy tắc phiên bản mới: hồ sơ đang chạy giữ luật cũ, hồ sơ mới theo luật mới |
| **Realm Keycloak** — `infra/keycloak/` | Chỉ nạp lần đầu Keycloak khởi động — xem cuối trang |

Mỗi lần khởi động, dịch vụ còn kiểm tính nhất quán của quy trình (ngõ cụt, trạng thái không tới
được, cạnh không ai đi được…). Cấu hình hỏng thì dịch vụ không lên, thay vì chạy với luồng hỏng.

Các bước, trong `infra/`:

1. Giải nén bản mới đè lên (hoặc `git pull` nếu dùng kho mã)
2. Mở `.env.example`, chép những dòng mới sang `.env` — biến mới thường có giá trị mặc định nên bỏ
   qua vẫn chạy, nhưng muốn đổi thì phải chép
3. Dựng lại:

```bash
docker compose --env-file .env up -d --build
```

## Tự kiểm không mất dữ liệu

Chụp số liệu trước khi nâng, so sau khi nâng — đứng ở gốc kho mã:

```bash
python scripts/kiem_nang_cap.py chup truoc-nang-cap.json
# … nâng cấp như trên …
python scripts/kiem_nang_cap.py so truoc-nang-cap.json
```

Lệnh chỉ đọc. Nó so số dòng và mã băm các cột không bao giờ đổi của hồ sơ, nhật ký, lời nhắn, tệp
đính kèm, và hỏi kho tệp xem từng tệp còn đủ kích thước không. Dòng mới sinh trong lúc nâng — bộ quét
tự leo thang một hồ sơ quá hạn chẳng hạn — chỉ được báo thêm, không tính là lệch. Cụm đổi tên container
thì thêm `--container` và `--backend`.

## Bản cũ hơn v0.9.1: phải dựng lại

Trước `v0.9.1`, lược đồ cấu hình và dữ liệu khởi tạo do PostgreSQL nạp đúng một lần lúc tạo thực thể,
nên đổi cấu hình là phải xóa dữ liệu:

```bash
docker compose --env-file .env down -v
docker compose --env-file .env up -d --build
```

:::caution
`down -v` xóa sạch hồ sơ, người dùng tạo tay trong Keycloak và bảng điều khiển tạo tay trong
Superset. Realm và dữ liệu khởi tạo tự nạp lại.
:::

## Realm Keycloak

Keycloak chỉ nạp `infra/keycloak/realm-dx-os-lab.json` khi realm chưa có. Bản mới đổi realm (vai trò,
client, chủ đề đăng nhập) thì ghi chú phát hành ([Releases](https://github.com/AlaVox-lab/dx-os-lab/releases))
nêu rõ; khi đó sửa tay trong trang quản trị Keycloak, hoặc dựng lại cụm.

### Tài khoản dịch vụ gọi API của lõi

Bản có API của nền tảng lõi (`/core/v1`) thêm client `dx-integration` vào realm — tài khoản dịch vụ để ứng
dụng khác gọi lõi, xem [API](../../tham-khao/api/). Cụm dựng từ bản cũ hơn không có client này. Tạo nó mà
không cần `down -v`, đứng ở gốc kho mã, sau bước 2 ở trên (đã chép ba dòng `KEYCLOAK_INTEGRATION_*` sang
`.env`) và khi cụm đang chạy:

```bash
python scripts/tai_khoan_dich_vu.py
```

Kịch bản kiểm client, thiếu thì tạo, có rồi thì đặt lại cấu hình và bí mật theo `.env`, gán vai còn thiếu,
rồi xin thử một token để chắc mọi thứ khớp. Chạy lại bao nhiêu lần cũng được. Cụm khác địa chỉ hay tệp env
thì thêm `--env-file` và `--keycloak`. Đổi `KEYCLOAK_INTEGRATION_SECRET` về sau cũng chạy lại lệnh này.
