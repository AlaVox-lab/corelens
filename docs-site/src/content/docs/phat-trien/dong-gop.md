---
title: Đóng góp
description: Quy trình nhánh và commit, kiểm thử, tích hợp liên tục, và cách dựng trang tài liệu này.
sidebar:
  order: 2
---

Quy ước đầy đủ ở
[`CONTRIBUTING.md`](https://github.com/AlaVox-lab/corelens/blob/main/CONTRIBUTING.md). Tóm tắt:

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
  ([bảng giấy phép theo thư mục](https://github.com/AlaVox-lab/corelens/blob/main/LICENSES.md)):

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

### Kiểm thử dựa trên tính chất cho máy trạng thái

Bài theo ví dụ chỉ đi những đường người viết nghĩ ra. `backend/tests/test_tinh_chat_may_trang_thai.py`
để [Hypothesis](https://hypothesis.readthedocs.io) (MPL-2.0) tự sinh chuỗi thao tác: tạo hồ sơ ở mọi quy
trình đang bật, rồi cho một tác nhân bất kỳ — kể cả người không có vai nào và tác nhân hệ thống — thử
đi một cạnh bất kỳ của bảng `transitions`, kèm nhập liệu đúng lẫn sai. Sau **mỗi** bước bài kiểm bốn bất
biến của cửa chuyển trạng thái duy nhất:

- chuyển thành công thì có đúng một dòng nhật ký mới, của đúng hồ sơ đó, với trạng thái trước và sau
  khớp hồ sơ, theo một cạnh có thật trong bộ quy tắc của hồ sơ mà tác nhân có vai; rời trạng thái kết
  thúc chỉ bằng cạnh mở lại mà dữ liệu khai `from_is_terminal`;
- bị từ chối thì không có dòng nhật ký nào và hồ sơ giữ nguyên trạng thái lẫn mọi trường;
- trạng thái của mọi hồ sơ luôn thuộc bộ quy tắc hồ sơ ghim;
- `allowed_transitions` chỉ chào cạnh đi ra từ trạng thái hiện tại mà tác nhân có vai.

Bản mặc định (80 ví dụ, mỗi ví dụ tới 50 bước, khoảng nửa phút) chạy trong bộ kiểm thử của cụm, cả CI. Bài
tự kiểm nó không rỗng: mọi bộ quy tắc đang bật phải có lần chuyển thành công. Bản dài gấp mười số ví dụ (vài
phút), chọn seed để lặp lại đúng một lượt, và `-s` để in thống kê — số lần thành công theo mã hoạt động, số
lần bị từ chối theo mã lỗi:

```bash
docker exec -e DXLAB_TINH_CHAT_DAI=1 dxlab-backend python -m pytest -p no:cacheprovider -q -s \
  tests/test_tinh_chat_may_trang_thai.py --hypothesis-seed=12345
```

Bài đỏ thì Hypothesis thu gọn phản ví dụ (việc này mất vài phút) rồi in nó dưới dòng
`Failing test case: <state machine>`: các lời gọi `state.tao_ho_so_dau(...)`, `state.chuyen_trang_thai(...)`
theo đúng thứ tự, trước mỗi lời gọi là các giá trị đã rút có nhãn — `Draw 9 (canh): Canh(...)` là cạnh,
`(vai)`, `(phong)`, `(ma_tac_nhan)` là tác nhân, rồi trường gửi kèm và ghi chú — và trên cùng là câu khẳng
định bị phá, ví dụ `một lần chuyển phải ghi đúng một dòng nhật ký`. Đó là lỗi của engine cần issue riêng:
chép phản ví dụ vào issue và dựng lại nó thành một bài theo ví dụ, đừng nới bài cho xanh. Cơ sở dữ liệu ví
dụ của Hypothesis tắt, nên lượt sau không tự phát lại phản ví dụ cũ — đầu ra của pytest là bản ghi duy nhất.

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
