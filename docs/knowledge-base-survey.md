# Khảo sát nền tảng kho tri thức cho không gian H

> **Issue**: #46  
> **Ngày khảo sát**: 2026-09-25  
> **Phạm vi**: khảo sát và dựng thử, chưa tích hợp vào hệ thống chính

## 1. Mục tiêu và tiêu chí

Không gian `H` cần một wiki nội bộ để nhân viên tự tra hướng dẫn trước khi gửi yêu cầu. Về sau, tầng `I` cần lấy nội dung wiki qua API để lập chỉ mục và gợi ý câu trả lời.

Các tiêu chí được dùng:

1. Giấy phép của mã nguồn ứng viên và ảnh Docker phải được kiểm tra riêng; giấy phép phải thuộc danh sách OSI.
2. Có đăng nhập một lần qua OIDC, để hợp nhất với Keycloak `26.7.3` của hệ thống.
3. Có API lấy nội dung trang cho công việc lập chỉ mục.
4. Chạy được như dịch vụ độc lập bằng Docker, không sửa mã nguồn nền tảng.
5. Tài nguyên và độ khó vận hành phù hợp với ngân sách bộ nhớ toàn cụm.
6. Có khả năng quản lý nội dung, phân quyền và cấu trúc trang đủ cho wiki nội bộ.
7. Hỗ trợ tiếng Việt có dấu trong lưu trữ, đọc lại nguyên văn qua API, tìm kiếm nội dung và giao diện quản trị hệ thống.

Giấy phép AGPL vẫn được xem xét ở dạng dịch vụ độc lập. Không nhúng mã AGPL vào mã MIT của dự án và không sửa mã nền tảng.

## 2. Ứng viên và giấy phép

Phiên bản mới nhất được đọc từ GitHub Releases ngày 2026-09-25. Các URL trong cột nguồn là nơi đã kiểm tra, không chỉ là nhãn giấy phép trong siêu dữ liệu.

| Ứng viên | Phiên bản mới nhất | Giấy phép mã nguồn | Kiểm trong kho mã | Kiểm trong ảnh Docker | OSI | Kết luận giấy phép |
|---|---|---|---|---|---|---|
| **Wiki.js** | `v2.5.315` | AGPL-3.0 | [LICENSE của Wiki.js](https://github.com/requarks/wiki/blob/main/LICENSE) (Dòng 1: `GNU AFFERO GENERAL PUBLIC LICENSE`) | [Ảnh `requarks/wiki`](https://hub.docker.com/r/requarks/wiki) ghi AGPLv3 và chứa tệp `/wiki/LICENSE` | Có, [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html) | Đạt khi chạy độc lập qua HTTP/OIDC |
| **BookStack** | `v26.09` | MIT | [LICENSE của BookStack](https://codeberg.org/bookstack/bookstack/src/branch/development/LICENSE) (Dòng 1: `The MIT License (MIT)`) | [Kho ảnh LinuxServer](https://github.com/linuxserver/docker-bookstack) có tệp LICENSE; ảnh `lscr.io/linuxserver/bookstack` đóng gói ứng dụng và được phát hành như OSS | Có; MIT và GPL-3.0 của kho đóng gói đều nằm trong [danh sách OSI](https://opensource.org/licenses) | Đạt; cần ghi rõ ranh giới giữa ứng dụng và ảnh đóng gói |
| **DokuWiki** | `release-2026-07-14c` | GPL-2.0 | [COPYING của DokuWiki](https://github.com/dokuwiki/dokuwiki/blob/master/COPYING) (Dòng 1: `GNU GENERAL PUBLIC LICENSE`) | [Kho ảnh LinuxServer](https://github.com/linuxserver/docker-dokuwiki) có tệp LICENSE; ảnh `lscr.io/linuxserver/dokuwiki` dẫn về kho đóng gói | Có; GPL-2.0 và GPL-3.0 đều nằm trong [danh sách OSI](https://opensource.org/licenses) | Đạt về giấy phép; tính năng OIDC/API cần plugin hoặc cấu hình thêm |
| **Outline** | `v1.10.1` | BSL 1.1 | [LICENSE của Outline](https://github.com/outline/outline/blob/main/LICENSE) (Dòng 1: `Business Source License 1.1`) | [Ảnh `outlinewiki/outline`](https://hub.docker.com/r/outlinewiki/outline) ghi lại giấy phép BSL 1.1 | **Không** | **Loại**: BSL 1.1 không nằm trong danh sách OSI, không đạt tiêu chí giấy phép của dự án |

Outline vẫn giữ trong bảng để ghi lại phương án bị loại, tránh đề xuất lại sau này. Không coi một nhãn “open source” trên trang sản phẩm là đủ nếu tệp LICENSE của mã nguồn hoặc ảnh Docker không đạt.

### 2.1. Kiểm tra giấy phép bên trong ảnh Docker của Wiki.js

Đã kiểm tra trực tiếp tệp giấy phép và nhãn (label) bên trong ảnh Docker `requarks/wiki:2.5`:

1. Đọc tệp `/wiki/LICENSE` bên trong container:
   ```bash
   docker run --rm --entrypoint sh requarks/wiki:2.5 -c "ls /wiki; head -3 /wiki/LICENSE"
   ```
   Kết quả: tệp `/wiki/LICENSE` tồn tại trong thư mục ứng dụng; 3 dòng đầu của tệp là:
   ```text
                       GNU AFFERO GENERAL PUBLIC LICENSE
                          Version 3, 19 November 2007
   ```

2. Kiểm tra nhãn siêu dữ liệu của ảnh Docker:
   ```bash
   docker inspect --format "{{json .Config.Labels}}" requarks/wiki:2.5
   ```
   Kết quả: `{"maintainer":"requarks.io"}`.

## 3. Kết quả dựng thử Wiki.js

### 3.1. Môi trường và lệnh

Cụm thử được đặt ngoài kho tại `D:\thu-46\`, dùng Compose project riêng `thu46` và cổng web `3100`.

```powershell
docker compose -p thu46 -f D:\thu-46\compose.yml up -d
```

Ảnh đã dùng:

- `requarks/wiki:2.5`, chạy thực tế phiên bản `2.5.315`
- `postgres:16-alpine`

Cụm có hai container: `thu46-wiki-1` và `thu46-db-1`. Trang `http://localhost:3100` trả HTTP 200 sau khi khởi động.

### 3.2. SSO với Keycloak

Đã tạo client OIDC `wiki-thu` trong realm `dx-os-lab` bằng giao diện quản trị Keycloak.

Cấu hình có hai địa chỉ vì Wiki.js chạy trong container:

| Thành phần | Địa chỉ |
|---|---|
| Authorization endpoint, do trình duyệt mở | `http://localhost:8080/realms/dx-os-lab/protocol/openid-connect/auth` |
| Token endpoint, do Wiki.js gọi từ container | `http://host.docker.internal:8080/realms/dx-os-lab/protocol/openid-connect/token` |
| UserInfo endpoint, do Wiki.js gọi từ container | `http://host.docker.internal:8080/realms/dx-os-lab/protocol/openid-connect/userinfo` |
| Issuer | `http://localhost:8080/realms/dx-os-lab` |
| Callback | `http://localhost:3100/login/cecb5570-e200-4e9d-a30b-4a90d7028ed8/callback` |
| Logout endpoint, do trình duyệt mở | `http://localhost:8080/realms/dx-os-lab/protocol/openid-connect/logout` |

Kết quả:

- Trình duyệt được chuyển tới Keycloak bằng `localhost`, không dùng `host.docker.internal`.
- Đăng nhập bằng tài khoản mẫu `an.nguyen / matkhau123` thành công.
- Wiki.js tạo người dùng `an.nguyen@dx-os-lab.test`; gán người dùng vào nhóm `Guests` để có quyền xem wiki.
- Callback quay về Wiki.js và mở được trang chào mừng.
- Lỗi đầu tiên là dùng sai `host.docker.internal` cho Authorization endpoint; lỗi này được sửa theo ghi chú “Một Keycloak, hai địa chỉ”.

### 3.3. API lấy nội dung

Wiki.js cung cấp GraphQL tại `/graphql`. Đã bật API Access và tạo một API token tạm thời với quyền Full Access trong cụm thử.

Đã tạo ba trang bằng mutation `pages.create`:

| ID | Path | Kết quả |
|---:|---|---|
| 1 | `huong-dan-api-1` | `Page created successfully.` |
| 2 | `huong-dan-api-2` | `Page created successfully.` |
| 3 | `huong-dan-api-3` | `Page created successfully.` |

Lệnh kiểm tra danh sách tương đương:

```http
POST http://localhost:3100/graphql
Authorization: Bearer <API_TOKEN>
Content-Type: application/json

{"query":"{ pages { list(orderBy: TITLE) { id path title } } }"}
```

Kết quả trả đủ ba trang. Truy vấn `pages.single(id: 1)` trả cả `id`, `path`, `title` và trường `content`, trong đó nội dung trang thứ nhất là:

```text
# Huong dan thu 1

Noi dung kiem thu Wiki.js cho khao sat #46.
```

API token đã được thu hồi trước khi dọn cụm thử. Token, dữ liệu thử và tệp Compose không nằm trong kho mã.

### 3.4. Tài nguyên

Đo bằng `docker stats --no-stream` khi Wiki.js đã chạy:

| Container | Bộ nhớ sử dụng | CPU tại thời điểm đo |
|---|---:|---:|
| `thu46-wiki-1` | `67.54 MiB` | `0.02%` |
| `thu46-db-1` | `53.02 MiB` | `13.78%` |
| **Tổng** | **`120.56 MiB`** | Không cộng CPU giữa các container |

Đây là một ảnh chụp đo trên máy phát triển, không phải giới hạn cố định của nền tảng.

### 3.5. Kiểm thử hỗ trợ Tiếng Việt

Phép thử kiểm tra khả năng lưu trữ, đọc lại nguyên văn có dấu qua GraphQL API và tìm kiếm tiếng Việt:

1. **Tạo trang có dấu qua GraphQL API**: Gửi yêu cầu `pages.create` với tiêu đề `"Hướng dẫn đổi mật khẩu"` và nội dung:
   ```markdown
   # Hướng dẫn đổi mật khẩu

   Đây là nội dung hướng dẫn đổi mật khẩu cho người dùng hệ thống DX-OS Lab.
   Quy trình thực hiện gồm các bước xác thực qua Keycloak và cập nhật mật khẩu mới.
   ```
   Trong PowerShell, thân yêu cầu JSON phải gửi dạng mảng byte UTF-8 (`[System.Text.Encoding]::UTF8.GetBytes($json)`) kèm header `Content-Type: application/json; charset=utf-8` để tránh ký tự bị hỏng trước khi tới Wiki.js.

2. **Đọc lại bằng `pages.single`**: Truy vấn `pages.single(id: 2)` trả về tiêu đề và nội dung có dấu khớp **NGUYÊN VĂN** với dữ liệu đã gửi, không bị lỗi font hay mất dấu:
   ```json
   {
     "id": 2,
     "path": "huong-dan-doi-mat-khau",
     "title": "Hướng dẫn đổi mật khẩu",
     "content": "# Hướng dẫn đổi mật khẩu\n\nĐây là nội dung hướng dẫn đổi mật khẩu cho người dùng hệ thống DX-OS Lab.\nQuy trình thực hiện gồm các bước xác thực qua Keycloak và cập nhật mật khẩu mới."
   }
   ```

3. **Tìm kiếm tiếng Việt có dấu**: Thử tìm kiếm từ khóa `"mật khẩu"` qua GraphQL API `pages.search(query: "mật khẩu")`. Kết quả tìm kiếm tìm thấy trang `"Hướng dẫn đổi mật khẩu"` (`path: huong-dan-doi-mat-khau`) với `totalHits: 2`.

4. **Kiểm tra ngôn ngữ hệ thống**: Truy vấn GraphQL `localization.locales` cho thấy hệ thống có sẵn gói ngôn ngữ Tiếng Việt (`code: "vi"`, `name: "Vietnamese"`, `nativeName: "Tiếng Việt"`, độ sẵn sàng 100%).

## 4. So sánh

| Tiêu chí | Wiki.js | BookStack | DokuWiki | Outline |
|---|---|---|---|---|
| Giấy phép | AGPL-3.0, đạt OSI khi chạy độc lập | MIT, ảnh đóng gói OSS | GPL-2.0, ảnh đóng gói OSS | BSL 1.1, **không đạt OSI** |
| Phiên bản đã xác định | `2.5.315` | `26.09` | `release-2026-07-14c` | `1.10.1` |
| Docker | Ảnh chính thức `requarks/wiki` | `lscr.io/linuxserver/bookstack` | `lscr.io/linuxserver/dokuwiki` | `outlinewiki/outline` |
| SSO/OIDC | Có Generic OpenID Connect; đã thử với Keycloak | Có cơ chế OIDC theo tài liệu; chưa dựng thử | Có connector/plugin xác thực; chưa dựng thử OIDC | Có tích hợp đăng nhập, nhưng không xét tiếp vì giấy phép |
| API nội dung | GraphQL; đã tạo và đọc ba trang | Có API/khả năng tích hợp theo tài liệu; chưa đo | Có thể mở rộng qua plugin/API; chưa đo | REST API chính thức; chưa đo |
| Hỗ trợ tiếng Việt | Đạt: Tạo/đọc lại nguyên văn có dấu qua GraphQL, tìm kiếm "mật khẩu" thành công, Locale có Tiếng Việt (`vi`, 100%) | Chưa kiểm | Chưa kiểm | Chưa kiểm |
| Bộ nhớ | Wiki `67.54 MiB`, PostgreSQL `53.02 MiB` đo thật | Chưa đo | Chưa đo | Chưa đo |
| Dựng thử | Đạt, project `thu46`, cổng `3100` | Chưa dựng | Chưa dựng | Chưa dựng |
| Rủi ro tích hợp | AGPL yêu cầu giữ dịch vụ độc lập; OIDC và GraphQL rõ ràng | Cần MariaDB và thêm dịch vụ lưu trữ dữ liệu | Không có database mặc định nhưng phụ thuộc plugin cho OIDC/API | Không đạt giấy phép, loại khỏi lựa chọn |

Các ô “chưa đo” và “chưa kiểm” không phải ước lượng. Chưa dựng ứng viên thì không ghi số liệu tài nguyên hay kết quả kiểm thử như dữ kiện.

## 5. Đề xuất và nguồn

Đề xuất chọn **Wiki.js `2.5.315`** cho kho tri thức, triển khai như một dịch vụ độc lập và giao tiếp với hệ thống qua OIDC/HTTP. Đây là ứng viên duy nhất đã được dựng thật trong khảo sát, có kết quả SSO với Keycloak, hỗ trợ tiếng Việt có dấu đầy đủ và có API GraphQL đọc được nội dung trang.

Lý do chọn:

- Wiki.js đáp ứng trực tiếp cả hai luồng cần khảo sát: nhân viên đăng nhập qua Keycloak và tầng `I` lấy nội dung qua API.
- Dữ liệu đo được nhỏ hơn đáng kể so với ngân sách toàn cụm hiện tại; số đo cũng minh bạch và tái hiện được.
- AGPL-3.0 được OSI công nhận. Ranh giới dịch vụ độc lập giữ mã AGPL ngoài mã MIT của DX-OS Lab.
- BookStack là phương án lùi hợp lý nếu nhóm ưu tiên giấy phép dễ dãi hơn, nhưng chưa được dựng và đo trong issue này.
- DokuWiki nhẹ về mô hình triển khai, nhưng OIDC/API cần kiểm chứng thêm qua plugin.
- Outline bị loại vì BSL 1.1 không thuộc danh sách OSI, dù có API và ảnh Docker chính thức.

Nguồn chính:

- [Issue #46](https://github.com/AlaVox-lab/dx-os-lab/issues/46)
- [Wiki.js LICENSE](https://github.com/requarks/wiki/blob/main/LICENSE)
- [Wiki.js Docker Hub](https://hub.docker.com/r/requarks/wiki)
- [Wiki.js API](https://docs.requarks.io/dev/api)
- [BookStack LICENSE](https://codeberg.org/bookstack/bookstack/src/branch/development/LICENSE)
- [BookStack Docker image repository](https://github.com/linuxserver/docker-bookstack)
- [DokuWiki COPYING](https://github.com/dokuwiki/dokuwiki/blob/master/COPYING)
- [DokuWiki Docker image repository](https://github.com/linuxserver/docker-dokuwiki)
- [Outline LICENSE](https://github.com/outline/outline/blob/main/LICENSE)
- [Outline Docker Hub](https://hub.docker.com/r/outlinewiki/outline)
- [Outline API](https://www.getoutline.com/developers)
- [Danh sách giấy phép OSI](https://opensource.org/licenses)
- [Giấy phép GNU AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html)

## Dọn dẹp

Đã thu hồi API token thử và dọn cụm thử bằng project riêng:

```powershell
docker compose -p thu46 -f D:\thu-46\compose.yml down -v
```

Cụm chính `dx-os-lab` không bị dừng hoặc xóa dữ liệu trong quá trình khảo sát.

