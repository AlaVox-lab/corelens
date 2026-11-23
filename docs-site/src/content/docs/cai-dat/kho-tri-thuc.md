---
title: Kho tri thức
description: Bật Wiki.js dưới hồ sơ tùy chọn tri-thuc, đăng nhập một lần qua Keycloak, nhóm theo vai trò, bài mẫu.
sidebar:
  order: 7
---

Kho tri thức là wiki nội bộ: phòng ban viết hướng dẫn tự xử lý — đặt lại mật khẩu, xin cấp quyền, máy in
không in được — để nhân viên tra trước khi gửi yêu cầu. Nền tảng là **Wiki.js `2.5.315`** (AGPL-3.0), chạy
**nguyên ảnh chính thức** như một dịch vụ độc lập. Quyết định và ranh giới giấy phép: ADR-0006 trong
`docs/adr/`, mục *Kho tri thức theo AGPL-3.0* trong `LICENSES.md`.

Cụm mặc định **không** có kho tri thức. Bật thêm khi cần, khoảng 300 MiB bộ nhớ.

## Bật

Trong `infra/`:

```bash
docker compose --env-file .env --profile tri-thuc up -d
```

Ba dịch vụ lên theo thứ tự:

| Dịch vụ | Việc |
|---|---|
| `tri-thuc-chuan-bi` | Tạo database `wiki` trên PostgreSQL của cụm; tạo hoặc cập nhật client OIDC `dx-wiki` trong Keycloak, kèm bộ ánh xạ đưa vai trò vào claim `wiki_groups`. Chạy xong thì dừng |
| `kho-tri-thuc` | Wiki.js, cổng `WIKI_PORT` (mặc định 3100) |
| `tri-thuc-khoi-tao` | Hoàn tất cài đặt lần đầu, bật đăng nhập một lần, tạo nhóm, cấp khóa API chỉ đọc cho dịch vụ ứng dụng, nạp bài mẫu từ `infra/tri-thuc/bai-mau/`. Chạy xong thì dừng |

Hai bước khởi tạo chạy lại bao nhiêu lần cũng được: thứ đã có thì để yên, bài mẫu đã có (kể cả đã sửa) không
bị ghi đè. Cụm cũ nâng lên bằng lệnh trên, không cần `down -v` — client OIDC tạo qua API quản trị của
Keycloak, nên realm đã nạp từ trước vẫn nhận.

Xem nhật ký nếu có gì không lên:

```bash
docker logs dxlab-tri-thuc-chuan-bi
docker logs dxlab-tri-thuc-khoi-tao
```

## Đăng nhập một lần

Đăng nhập cổng như thường, rồi mở `http://localhost:3100/login/keycloak`: trình duyệt đi qua Keycloak và vào
thẳng kho tri thức, không hỏi mật khẩu lần nữa. Tài khoản Wiki.js tạo tự động ở lần vào đầu.

| Vai trò trong Keycloak | Trên kho tri thức |
|---|---|
| Mọi vai trò nghiệp vụ (`WIKI_READ_ROLES`) | Đọc bài, bình luận |
| Điều phối viên, trưởng phòng, quản trị viên (`WIKI_WRITE_ROLES`) | Viết, sửa, xóa bài |

Mỗi vai trò là một nhóm Wiki.js **cùng tên với mã vai trò** — Wiki.js gán người dùng vào nhóm có tên trùng giá
trị trong claim nhóm, và đồng bộ lại ở mỗi lần đăng nhập. Đổi ai được viết thì sửa `WIKI_WRITE_ROLES` trong
`infra/.env` rồi chạy lại bước khởi tạo:

```bash
docker compose --env-file .env --profile tri-thuc up -d tri-thuc-khoi-tao
```

Trang `/login` của kho tri thức tự chuyển sang Keycloak, nên mở thẳng một bài cũng không phải chọn cách đăng
nhập. Tài khoản quản trị riêng của Wiki.js (`WIKI_ADMIN_EMAIL`, `WIKI_ADMIN_PASSWORD`) đăng nhập cục bộ ở
`http://localhost:3100/login?all=1` — chỉ để quản trị wiki. Không ai tự đăng ký tài khoản cục bộ được.

## Nối vào cổng

Đặt trong `infra/.env` rồi dựng lại dịch vụ ứng dụng (`docker compose --env-file .env up -d backend`):

```bash
WIKI_URL=http://localhost:3100
```

| Có | Cần |
|---|---|
| Lối **Kho tri thức** trên thanh bên của mọi nhân viên — mở thẻ mới, vào thẳng qua Keycloak; dưới tên ghi *Wiki.js · AGPL-3.0 · mã nguồn* | `WIKI_URL` |
| Bài hướng dẫn trong khung *Có thể đã có cách giải quyết* khi người gửi đang soạn yêu cầu, cạnh hồ sơ đã giải quyết tương tự; bấm mở bài ở thẻ mới | `WIKI_URL` **và** mô hình nhúng (`EMBEDDING_URL`, hồ sơ `tri-tue` — trang *Mô hình ngôn ngữ*) |

Bộ lập chỉ mục *Bộ lập chỉ mục kho tri thức* (màn Hệ thống) chạy mỗi `WIKI_INDEX_INTERVAL_SECONDS` giây (mặc
định 120): đọc danh sách bài bằng khóa API chỉ đọc, nhúng bài mới hay vừa sửa, bỏ bài đã xóa, thôi xuất bản
hay chuyển riêng tư. Viết bài mới thì chờ một lượt là bài vào gợi ý. Bài chỉ là gợi ý — người gửi vẫn gửi
yêu cầu bình thường.

Wiki tắt giữa chừng: bộ lập chỉ mục bỏ lượt, gợi ý vẫn dùng chỉ mục đã có, gửi yêu cầu không bị ảnh hưởng.

## Biến môi trường

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `WIKI_PORT` | `3100` | Cổng web trên máy |
| `WIKI_DB_NAME` | `wiki` | Database riêng của Wiki.js |
| `WIKI_OIDC_CLIENT_ID`, `WIKI_OIDC_SECRET` | `dx-wiki`, giá trị mẫu | Client OIDC trong Keycloak — **đổi bí mật** trước khi dùng thật |
| `WIKI_READ_ROLES`, `WIKI_WRITE_ROLES` | như bảng trên | Vai trò được đọc / được viết |
| `WIKI_ADMIN_EMAIL`, `WIKI_ADMIN_PASSWORD` | giá trị mẫu | Quản trị Wiki.js — **đổi mật khẩu** trước khi dùng thật |
| `WIKI_LOCALE` | `vi` | Ngôn ngữ giao diện. Tải gói ngôn ngữ cần mạng ra ngoài; gói chưa thật sự cài được (tải hỏng, tải không trọn, không có mạng) thì bước khởi tạo vẫn xong, giao diện và bài mẫu dùng tiếng Anh (`en`), nội dung bài vẫn tiếng Việt |

### Giao diện Wiki tiếng Anh dù đặt `vi`

Bước khởi tạo không tải được gói ngôn ngữ — nhật ký `docker logs dxlab-tri-thuc-khoi-tao` ghi
`không dùng được gói ngôn ngữ vi (…); giao diện en`. Khi máy có mạng ra ngoài, chạy lại bước khởi tạo (trong
`infra/`): `docker compose --env-file .env --profile tri-thuc up -d tri-thuc-khoi-tao`. Gói tải được thì giao
diện chuyển sang tiếng Việt; bài mẫu đã có giữ nguyên, bài mẫu bản tiếng Việt được tạo thêm cùng đường dẫn.

## Tắt

Để `WIKI_URL` rỗng rồi dựng lại dịch vụ ứng dụng (lối vào và gợi ý bài biến mất), và dừng wiki:

```bash
docker compose --env-file .env --profile tri-thuc stop kho-tri-thuc
```

Cổng yêu cầu và mọi thao tác trên hồ sơ không phụ thuộc kho tri thức. Database `wiki` và khóa API (volume
`tri-thuc-khoa`) giữ nguyên tới khi `down -v`.
