---
title: Nâng cấp
description: Lên bản mới — khi nào chỉ cần dựng lại, khi nào phải xóa dữ liệu khởi tạo, và cách tự kiểm.
sidebar:
  order: 4
---

## Hai loại thay đổi

| Thay đổi | Cách nạp | Phải làm khi nâng cấp |
|---|---|---|
| **Migration** trong `backend/alembic/versions/` | Tự chạy lúc dịch vụ ứng dụng khởi động | Chỉ `up -d --build` |
| **Lược đồ và dữ liệu khởi tạo** — `infra/postgres/init/`, `infra/seed/`, realm `infra/keycloak/` | Chỉ nạp **một lần**, lúc PostgreSQL tạo thực thể lần đầu | `down -v` rồi `up -d --build` — **mất dữ liệu trong cụm** |

## Tự kiểm sau khi kéo mã mới

Đứng ở gốc kho mã, sau `git pull`:

```bash
git diff --name-only "HEAD@{1}" HEAD -- infra
```

| Thấy tệp nào | Phải làm |
|---|---|
| `infra/postgres/init/…`, `infra/seed/…`, `infra/keycloak/…` | `down -v` rồi `up -d --build` |
| `infra/.env.example` | Mở tệp, chép những dòng mới sang `infra/.env` |
| `infra/docker-compose.yml` | `up -d --build` |
| Không có gì | `up -d --build` nếu muốn chạy bản mới; migration tự chạy |

Lệnh đầy đủ, chạy trong `infra/`:

```bash
docker compose --env-file .env down -v
docker compose --env-file .env up -d --build
```

:::caution
`down -v` xóa sạch hồ sơ, người dùng tạo tay trong Keycloak và bảng điều khiển tạo tay trong
Superset. Realm và dữ liệu khởi tạo tự nạp lại.
:::

## Các bản cần `down -v`

Ghi chú phát hành của từng bản ([Releases](https://github.com/AlaVox-lab/dx-os-lab/releases))
nêu thay đổi lược đồ. Gần đây nhất, `v0.7.0` có ba lần: cột bước chính trên bảng cạnh, bảng
trường riêng theo loại yêu cầu, và chủ đề đăng nhập trong realm.

Chuyển dữ liệu thật qua các bản mà không xóa là việc đang làm — đưa lược đồ cấu hình vào
migration (issue #254).
