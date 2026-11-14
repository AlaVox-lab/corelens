# ADR-0006: Nền tảng kho tri thức cho không gian H

| Mục | Giá trị |
|---|---|
| Trạng thái | Đã chấp nhận (2026-11-14); chờ giảng viên xác nhận |
| Ngày | 2026-09-25 |
| Không gian kiến trúc | `H` |
| Issue liên quan | #46 · #321 |
| Người quyết định | Navigator (`AlaVox-lab`) chấp nhận ngày 2026-11-14 để cài ở #321, theo đúng nguyên tắc giảng viên đã xác nhận cho ADR-0007 ngày 2026-11-10; đã hỏi giảng viên xác nhận riêng — xem mục Quyết định |

## Bối cảnh

Không gian `H` cần một wiki nội bộ để nhân viên tra hướng dẫn tự giải quyết trước khi gửi yêu cầu. Về sau, tầng `I` cần lấy nội dung wiki qua API để lập chỉ mục và gợi ý câu trả lời.

Đây là thành phần lắp ghép, phải chạy như dịch vụ độc lập và không được sửa mã nguồn nền tảng. Các ràng buộc chính là:

- Giấy phép của mã nguồn và ảnh Docker phải được kiểm tra tận gốc và thuộc danh sách OSI.
- Phải hỗ trợ đăng nhập một lần qua Keycloak `26.7.3`.
- Phải có API lấy nội dung cho việc lập chỉ mục.
- Phải có cách dựng bằng container và mức tài nguyên phù hợp với cụm hiện tại.
- Không được đưa mã hoặc tệp dựng thử của ứng viên vào kho DX-OS Lab.

## Các phương án đã cân nhắc

### Phương án A — Wiki.js `2.5.315`

| Mục | Nội dung |
|---|---|
| Giấy phép | AGPL-3.0 |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có, **có điều kiện** — chỉ khi chạy như dịch vụ độc lập |
| Tài nguyên khi chạy | Wiki.js `67.54 MiB`; PostgreSQL `53.02 MiB`, đo thật |
| Khả năng đóng gói bằng container | Ảnh `requarks/wiki:2.5`, dựng thật thành công |
| Chất lượng tài liệu | Có tài liệu Docker, OIDC và GraphQL API |
| Mức độ hoạt động của dự án | Bản phát hành `v2.5.315` ngày 2026-09-21 |
| Độ khó tích hợp | Thấp đến vừa; OIDC hoạt động sau khi cấu hình đúng hai địa chỉ và cấp nhóm |

**Ưu điểm**

- Đã dựng thật trong project Compose riêng `thu46` với cổng `3100`.
- Đăng nhập `an.nguyen / matkhau123` qua Keycloak thành công.
- GraphQL tạo được ba trang và đọc lại được danh sách cùng nội dung trang.
- Đã xác minh hỗ trợ tiếng Việt có dấu đầy đủ qua GraphQL (`pages.create`, `pages.single`, `pages.search` từ khóa "mật khẩu") và có gói locale `vi`.
- API và OIDC phù hợp trực tiếp với hai nhu cầu của issue.

**Nhược điểm**

- AGPL-3.0 là copyleft mạnh hơn MIT; phải giữ ranh giới dịch vụ độc lập và không nhúng mã.
- Cần cấp nhóm Wiki.js cho người dùng mới; bật tự đăng ký một mình chưa đủ quyền xem nội dung.
- Có PostgreSQL riêng trong cụm dịch vụ.

### Phương án B — BookStack `v26.09`

| Mục | Nội dung |
|---|---|
| Giấy phép | MIT ở mã nguồn BookStack; kho ảnh LinuxServer có LICENSE riêng cho lớp đóng gói |
| Được OSI công nhận | Có; MIT và giấy phép OSI của lớp đóng gói |
| Tương thích với MIT | Có |
| Tài nguyên khi chạy | Chưa đo |
| Khả năng đóng gói bằng container | Ảnh `lscr.io/linuxserver/bookstack` |
| Chất lượng tài liệu | Tốt; có hướng dẫn Docker và cấu hình ứng dụng |
| Mức độ hoạt động của dự án | Bản phát hành `v26.09` ngày 2026-09-24 |
| Độ khó tích hợp | Vừa; ảnh yêu cầu MariaDB và chưa được dựng trong issue này |

**Ưu điểm**

- Giấy phép ứng dụng dễ dãi, phù hợp với MIT của sản phẩm.
- Giao diện tài liệu và phân cấp nội dung phù hợp wiki nội bộ.

**Nhược điểm**

- Chưa có số đo tài nguyên hoặc phép kiểm SSO/API trong khảo sát này.
- Cần thêm MariaDB và phải kiểm tra chi phí bộ nhớ của cả ứng dụng lẫn cơ sở dữ liệu.
- Nguồn chính đã chuyển sang Codeberg, làm quy trình kiểm phiên bản khác với GitHub.

### Phương án C — DokuWiki `release-2026-07-14c`

| Mục | Nội dung |
|---|---|
| Giấy phép | GPL-2.0 ở mã nguồn DokuWiki; kho ảnh LinuxServer có LICENSE riêng cho lớp đóng gói |
| Được OSI công nhận | Có; GPL-2.0 và giấy phép OSI của lớp đóng gói |
| Tương thích với MIT | Có, **có điều kiện** — chỉ khi chạy như dịch vụ độc lập |
| Tài nguyên khi chạy | Chưa đo |
| Khả năng đóng gói bằng container | Ảnh `lscr.io/linuxserver/dokuwiki` |
| Chất lượng tài liệu | Tốt cho cài đặt và vận hành cơ bản |
| Mức độ hoạt động của dự án | Bản phát hành `release-2026-07-14c` ngày 2026-09-02 |
| Độ khó tích hợp | Vừa đến cao; OIDC và API phụ thuộc connector/plugin cần kiểm chứng |

**Ưu điểm**

- Mô hình đơn giản, không cần cơ sở dữ liệu riêng theo ảnh Docker.
- Có hệ thống plugin và connector phong phú.

**Nhược điểm**

- Chưa dựng thử, chưa đo bộ nhớ và chưa kiểm chứng OIDC/API trong issue này.
- Tích hợp cần thêm plugin, làm tăng rủi ro tương thích và vận hành.
- GPL-2.0 yêu cầu giữ ranh giới dịch vụ độc lập nếu có dùng mã nền tảng.

### Phương án D — Outline `v1.10.1`

| Mục | Nội dung |
|---|---|
| Giấy phép | BSL 1.1 ở mã nguồn và ảnh Docker |
| Được OSI công nhận | **Không** |
| Tương thích với MIT | Không đạt tiêu chí giấy phép của dự án |
| Tài nguyên khi chạy | Chưa đo |
| Khả năng đóng gói bằng container | Ảnh `outlinewiki/outline` |
| Chất lượng tài liệu | Tốt; có API REST chính thức |
| Mức độ hoạt động của dự án | Bản phát hành `v1.10.1` ngày 2026-09-09 |
| Độ khó tích hợp | Vừa; có API nhưng không được xem xét tiếp vì giấy phép |

**Ưu điểm**

- API REST rõ ràng và phù hợp lập chỉ mục.
- Giao diện cộng tác tốt cho kho tri thức.

**Nhược điểm**

- BSL 1.1 không nằm trong danh sách giấy phép OSI.
- Bị loại dù có khả năng kỹ thuật phù hợp; không được chọn làm thành phần của sản phẩm dự thi.

## Quyết định

Chọn **Wiki.js `2.5.315`** làm nền tảng kho tri thức cho không gian `H`, chạy như một dịch vụ độc lập và giao tiếp với DX-OS Lab qua OIDC/HTTP.

Navigator chấp nhận ngày 2026-11-14 để cài đặt ở #321. Cơ sở: ngày 2026-11-10 giảng viên đã xác nhận cho ADR-0007 rằng một thành phần AGPL-3.0 vẫn thuộc danh sách OSI nên không vi phạm yêu cầu giấy phép của cuộc thi, miễn là chạy như dịch vụ tách riêng, kho mô tả đúng mô hình nhiều giấy phép (`LICENSES.md`, `NOTICE`), và người dùng lấy được mã nguồn của dịch vụ qua mạng. Wiki.js thỏa cả ba theo cách đơn giản hơn PM4Py:

| | PM4Py (ADR-0007) | Wiki.js (bản ghi này) |
|---|---|---|
| Cách dùng | Thư viện, được `import` trong mã của nhóm | Ảnh chính thức `requarks/wiki`, chạy nguyên bản như một dịch vụ |
| Mã của nhóm phải mang AGPL | Có — cả thư mục `services/khai-pha/` | **Không** — nhóm chỉ viết cấu hình và một bước khởi tạo nói chuyện với Wiki.js qua GraphQL và OIDC, không chứa hay dẫn xuất mã Wiki.js (điều 5, *aggregate*) |
| Thư mục AGPL mới trong kho | `services/khai-pha/` kèm `LICENSE` riêng | Không có |
| Nghĩa vụ mã nguồn qua mạng (điều 13) | Mã của nhóm đã sửa đổi và kết hợp → dẫn tới mã nguồn ngay trên màn | Không sửa Wiki.js nên mã nguồn tương ứng là bản thượng nguồn công khai; cổng vẫn ghi tên, giấy phép và đường dẫn mã nguồn cạnh lối vào kho tri thức, như dòng mã nguồn của màn Quy trình thực tế |
| Ghi vào `LICENSES.md`, `NOTICE` | Có | Có, theo khuôn ClamAV (GPL-2.0, dịch vụ độc lập, #248) |

Ranh giới này hỏng nếu nhóm dựng ảnh riêng từ mã Wiki.js hay vá mã của nó — cả hai đều bị cấm. Mọi thay đổi hành vi làm bằng cấu hình và GraphQL. Giảng viên đã được hỏi xác nhận riêng; nếu giảng viên yêu cầu khác, bản ghi này được thay bằng bản mới và #321 đổi theo.

## Lý do

Wiki.js là ứng viên duy nhất đã được dựng và đo trong issue này. Cấu hình OIDC với Keycloak hoạt động sau khi tách đúng địa chỉ trình duyệt và địa chỉ container. GraphQL API tạo được ba trang, đọc lại nguyên văn tiếng Việt có dấu qua `pages.single`, và tìm kiếm tiếng Việt thành công qua `pages.search`, nên đáp ứng trực tiếp yêu cầu chuẩn bị dữ liệu cho tầng `I`.

AGPL-3.0 là giấy phép OSI có copyleft mạnh. Căn cứ pháp lý cụ thể để việc sử dụng Wiki.js không ảnh hưởng đến mã nguồn MIT của DX-OS Lab theo [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html) gồm:
- **Điều 5, đoạn cuối (*aggregate*)**: Wiki.js và sản phẩm DX-OS Lab là các tác phẩm riêng biệt, không kết hợp thành một chương trình lớn hơn, chỉ tương tác qua giao thức mạng HTTP/OIDC. Do đó, điều khoản copyleft của AGPL-3.0 không lan sang mã nguồn MIT của dự án.
- **Điều 13 (Tương tác mạng)**: Nghĩa vụ cung cấp mã nguồn cho người dùng qua mạng chỉ phát sinh khi có **sửa đổi** Wiki.js. Khi sử dụng nguyên bản ảnh chính thức `requarks/wiki:2.5` và không sửa đổi mã nền tảng, dự án chỉ cần giữ nguyên các thông báo bản quyền và giấy phép theo quy định.

BookStack là phương án lùi đáng xem xét nếu nhóm ưu tiên giấy phép MIT và chấp nhận thêm MariaDB, nhưng issue này chưa có phép đo để so sánh công bằng. DokuWiki có footprint tiềm năng nhỏ hơn nhưng cần kiểm chứng connector OIDC và API. Outline bị loại dứt khoát vì BSL 1.1 không được OSI công nhận.

## Cách tích hợp

Chạy Wiki.js như một dịch vụ độc lập trong cụm triển khai, chỉ giao tiếp qua OIDC và HTTP/GraphQL, không nhúng mã Wiki.js vào mã nguồn DX-OS Lab.

Căn cứ theo điều 5 (về tác phẩm riêng biệt *aggregate*) và điều 13 (về tương tác mạng) của [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html):
- Giữ ranh giới dịch vụ độc lập, sử dụng nguyên bản ảnh Docker chính thức `requarks/wiki:2.5` và không sửa đổi mã nguồn nền tảng.
- Người dùng đăng nhập qua client OIDC của Wiki.js trong Keycloak.
- Trình duyệt dùng địa chỉ Keycloak có thể truy cập là `http://localhost:8080` trong môi trường thử.
- Wiki.js gọi token và UserInfo từ container qua `http://host.docker.internal:8080`.
- Tầng `I` lấy nội dung qua GraphQL `/graphql` bằng API token có scope tối thiểu cần thiết.
- API token không lưu trong kho, không ghi vào tài liệu, và phải thu hồi khi kết thúc phép thử.
- Giữ nguyên thông báo bản quyền và giấy phép của Wiki.js trong dịch vụ độc lập.

## Hệ quả

**Điều gì trở nên dễ hơn**

- Có OIDC và API đã kiểm chứng để nối vào Keycloak và tầng `I`.
- Có thể thay đổi nội dung wiki mà không sửa mã ứng dụng.
- Mức đo Wiki.js cộng PostgreSQL của cụm thử là `120.56 MiB`, có thể cộng vào ngân sách hệ thống.

**Điều gì trở nên khó hơn**

- Phải duy trì dịch vụ AGPL độc lập và không nhúng mã nền tảng.
- Phải quản lý quyền nhóm Wiki.js, không chỉ ánh xạ danh tính từ Keycloak.
- Cần thiết kế lưu trữ dữ liệu, backup và giới hạn tài nguyên khi tích hợp thật.

**Việc phải làm tiếp sau quyết định này**

- [x] Navigator chấp nhận ngày 2026-11-14; chờ giảng viên xác nhận.
- [x] Cập nhật `docs/ARCHITECTURE.md` mục 3.
- [ ] Nếu chấp nhận, cập nhật `docs/dependencies.md` với Wiki.js, AGPL-3.0 và ranh giới dịch vụ.
- [x] Tạo issue riêng cho tích hợp Wiki.js vào Compose chính: #321, dưới hồ sơ Compose tùy chọn `tri-thuc` — cụm mặc định không đổi.
- [ ] Chốt chính sách cấp nhóm và quyền đọc/ghi từ dữ liệu cấu hình.
- [ ] Đo lại tổng bộ nhớ khi nền tảng được đưa vào cụm thật.

## Ghi chú

- Cụm thử nằm ngoài kho tại `D:\thu-46\`, project Compose là `thu46`.
- Wiki.js chạy thực tế phiên bản `2.5.315`; bộ nhớ đo bằng `docker stats --no-stream`.
- SSO dùng tài khoản mẫu `an.nguyen / matkhau123`, không dùng tài khoản thật.
- API token thử đã được thu hồi; cụm thử đã dọn bằng `docker compose -p thu46 ... down -v`.
- Tài liệu so sánh chi tiết và toàn bộ nguồn tham khảo nằm trong [knowledge-base-survey.md](../knowledge-base-survey.md).
