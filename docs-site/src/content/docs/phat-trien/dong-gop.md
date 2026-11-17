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
- Mọi tệp mã mới có header giấy phép theo thư mục chứa nó — MIT ở mọi nơi:

```python
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
```

- Riêng thư mục dịch vụ khai phá `services/khai-pha/` theo AGPL-3.0-or-later
  ([bảng giấy phép theo thư mục](https://github.com/AlaVox-lab/dx-os-lab/blob/main/LICENSES.md)):

```python
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 AlaVox-lab
```

## Kiểm thử và tích hợp liên tục

Mỗi pull request tự chạy sáu kiểm tra:

| Kiểm tra | Chạy tay ở máy |
|---|---|
| Header giấy phép | `python scripts/kiem_header.py` |
| Linter — ruff cho Python, eslint cho cổng | `ruff check .` ở gốc kho (ruff `0.17.3`); `npm run lint` trong `frontend/` |
| Giao diện — dựng và kiểm kiểu | `npm ci`, `npm run build`, `npm run typecheck` trong `frontend/` |
| Trang tài liệu — dựng | `npm ci`, `npm run build` trong `docs-site/` |
| Cụm — toàn bộ kiểm thử dịch vụ trên PostgreSQL và Keycloak thật, kể cả các đường qua cổng API | `docker exec dxlab-backend python -m pytest -p no:cacheprovider -q` khi cụm đang chạy |
| Bảng điều khiển — Superset tự nạp dashboard từ tệp cấu hình, đọc được view báo cáo | mở `http://localhost:8088` sau khi dựng cụm |

Pull request vào `main` chạy thêm **toàn bộ kịch bản giao diện** trên một cụm dựng sạch (quy trình
`e2e.yml`, cũng bấm chạy tay được ở thẻ *Actions*); hỏng thì báo cáo HTML và vết của bài hỏng được lưu
lại ở trang lượt chạy — xem [Kiểm thử giao diện](../kiem-thu-giao-dien/).

Tính năng ở dịch vụ còn được thử bằng **phép thử đột biến**: cố ý cài lỗi vào mã, bài kiểm thử phải
bắt được.

## Dựng trang tài liệu này

Trang nằm ở thư mục `docs-site/`, dựng bằng [Starlight](https://starlight.astro.build) (MIT). Cần
Node.js:

```bash
cd docs-site
npm ci
npm run dev      # xem trực tiếp ở http://localhost:4321/
npm run build    # dựng ra docs-site/dist
```

Mỗi trang là một tệp Markdown trong `docs-site/src/content/docs/`. Nút **Sửa trang này** ở cuối mỗi
trang mở đúng tệp trên GitHub. Nội dung kỹ thuật sâu giữ ở `docs/` của kho — trang này dẫn sang,
không chép lại.
