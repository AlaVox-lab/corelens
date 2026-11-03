---
title: Đóng góp
description: Quy trình nhánh và commit, kiểm thử, tích hợp liên tục, và cách dựng trang tài liệu này.
sidebar:
  order: 2
---

Quy ước đầy đủ ở
[`CONTRIBUTING.md`](https://github.com/AlaVox-lab/dx-os-lab/blob/main/CONTRIBUTING.md). Tóm tắt:

## Quy trình

- Mỗi việc là một **issue** có nhãn `type/`, `space/`, `priority/`
- Nhánh công việc tạo từ `dev`, tên `<loại>/<số-issue>-<mô-tả>` — ví dụ `fix/274-khung-chat`
- Commit theo **Conventional Commits**, tiếng Việt có dấu: `<loại>(<phạm vi>): <mô tả>`, kèm
  `Closes #N`. Nhật ký thay đổi sinh tự động từ commit, nên commit sai chuẩn sẽ biến mất khỏi nhật ký
- Pull request vào `dev` (squash), rồi `dev` lên `main` (merge commit)
- Mọi tệp mã mới có header giấy phép:

```python
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
```

## Kiểm thử và tích hợp liên tục

Mỗi pull request tự chạy năm kiểm tra:

| Kiểm tra | Chạy tay ở máy |
|---|---|
| Header giấy phép | `python scripts/kiem_header.py` |
| Giao diện — dựng và kiểm kiểu | `npm ci`, `npm run build`, `npm run typecheck` trong `frontend/` |
| Trang tài liệu — dựng | `npm ci`, `npm run build` trong `docs-site/` |
| Cụm — toàn bộ kiểm thử dịch vụ trên PostgreSQL và Keycloak thật | `docker exec dxlab-backend python -m pytest -p no:cacheprovider -q` khi cụm đang chạy |
| Bảng điều khiển — Superset tự nạp dashboard từ tệp cấu hình, đọc được view báo cáo | mở `http://localhost:8088` sau khi dựng cụm |

Tính năng ở dịch vụ còn được thử bằng **phép thử đột biến**: cố ý cài lỗi vào mã, bài kiểm thử phải
bắt được.

## Dựng trang tài liệu này

Trang nằm ở thư mục `docs-site/`, dựng bằng [Starlight](https://starlight.astro.build) (MIT). Cần
Node.js:

```bash
cd docs-site
npm ci
npm run dev      # xem trực tiếp ở http://localhost:4321/dx-os-lab/
npm run build    # dựng ra docs-site/dist
```

Mỗi trang là một tệp Markdown trong `docs-site/src/content/docs/`. Nút **Sửa trang này** ở cuối mỗi
trang mở đúng tệp trên GitHub. Nội dung kỹ thuật sâu giữ ở `docs/` của kho — trang này dẫn sang,
không chép lại.
