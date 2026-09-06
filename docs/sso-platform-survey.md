# Khảo sát nền tảng định danh tập trung (SSO) — Không gian H

> **Mục đích**: ghi lại quá trình và kết quả khảo sát nền tảng định danh tập trung
> cho không gian `H`, làm căn cứ cho bản ghi quyết định
> [`adr/0001-chon-nen-tang-sso.md`](adr/0001-chon-nen-tang-sso.md).
>
> **Issue liên quan**: #19 · **Ngày thực hiện**: 2026-09-06

---

## 1. Câu hỏi cần trả lời

Chọn nền tảng định danh tập trung nào để cung cấp đăng nhập một lần, quản lý danh tính
và phân quyền theo vai trò cho toàn hệ thống, đáp ứng bốn vai trò nghiệp vụ: người gửi
yêu cầu, điều phối viên, người xử lý, trưởng bộ phận?

Đây là thành phần **lắp ghép**, không tự viết. `CLAUDE.md` mục 3.2 xếp SSO vào nhóm nền
tảng nguồn mở có sẵn cần tích hợp, không phải nhóm tự phát triển.

### 1.1. Ràng buộc chi phối

| Ràng buộc | Nguồn | Hệ quả với khảo sát |
|---|---|---|
| Giấy phép phải được OSI công nhận và tương thích MIT | Bảng chấm PoF mục 2 (10 điểm) | Loại ngay mọi ứng viên dùng BSL, SSPL, Elastic, Commons Clause, fair-code |
| Danh sách vai trò phải nằm trong dữ liệu, không mã cứng | `ARCHITECTURE.md` mục 5 | Nền tảng phải nạp được vai trò từ tệp cấu hình, không phải khai báo bằng tay |
| Toàn hệ thống dựng bằng một lệnh trên máy sạch | Bảng chấm PoF mục 4 (10 điểm) | Phải có ảnh chứa chính thức, cấu hình được bằng biến môi trường |
| Không sửa mã nguồn thư viện bên thứ ba | Bảng chấm PoF mục 5 (10 điểm) | Phải tích hợp qua giao thức chuẩn, không vá mã nền tảng |

---

## 2. Ứng viên và kiểm tra giấy phép

Ba ứng viên được đưa vào so sánh. Kết quả đối chiếu với danh sách chính thức tại
`https://opensource.org/licenses`:

| Ứng viên | Giấy phép | OSI công nhận | Tương thích MIT | Ghi chú |
|---|---|---|---|---|
| **Keycloak** | Apache-2.0 | Có | Có | Sạch, không điều kiện |
| **Zitadel** | Apache-2.0 | Có | Có | Sạch, không điều kiện |
| **Authentik** | MIT ở phần lõi | Có | Có, **có điều kiện** | Thư mục `enterprise/` tách sang giấy phép thương mại riêng. Chỉ hợp lệ nếu dùng đúng phần lõi MIT và tránh tính năng Enterprise |

**Không ứng viên nào dùng AGPL**, nên không phát sinh ràng buộc copyleft mạnh về cách
tích hợp. Cả ba đều dùng PostgreSQL làm kho dữ liệu và phơi OIDC theo chuẩn, nghĩa là
tích hợp không đòi hỏi sửa mã nền tảng.

Ory (Kratos + Hydra) được nêu trong issue nhưng không đưa vào so sánh sâu: đây là bộ
thành phần rời cần tự lắp thành một hệ hoàn chỉnh, chi phí tích hợp cao hơn hẳn ba ứng
viên trên trong khi nhóm chỉ cần một nền tảng trọn gói.

---

## 3. Bảng so sánh

Ô ghi *(tài liệu)* là thông tin lấy từ tài liệu chính thức, **chưa dựng thử kiểm chứng**.
Ô ghi *(đo thật)* là số liệu thu được từ lần dựng thử ở mục 4.

| Tiêu chí | Keycloak | Zitadel | Authentik |
|---|---|---|---|
| Giấy phép | Apache-2.0 | Apache-2.0 | MIT (lõi) |
| Được OSI công nhận | Có | Có | Có |
| Tương thích với MIT | Có | Có | Có điều kiện |
| Hỗ trợ OIDC | Có *(đo thật)* | Có *(tài liệu)* | Có *(tài liệu)* |
| Hỗ trợ SAML | Có | Có *(tài liệu)* | Có *(tài liệu)* |
| Phân quyền theo vai trò | Realm role và client role, đưa được vào token *(đo thật)* | Có *(tài liệu)* | Có *(tài liệu)* |
| Kho dữ liệu | PostgreSQL | PostgreSQL | PostgreSQL |
| Nạp cấu hình từ tệp | Có — nhập realm từ JSON *(đo thật)* | Có *(tài liệu)* | Có — blueprint *(tài liệu)* |
| Tài nguyên khi chạy | 970 MiB *(đo thật)* | Chưa đo — nền Go, dự kiến nhẹ hơn | Chưa đo — nền Python |
| Đóng gói bằng container | Ảnh chính thức *(đo thật)* | Ảnh chính thức | Ảnh chính thức |
| Chất lượng tài liệu | Rất đầy đủ | Tốt | Tốt |
| Mức độ hoạt động | Dự án của CNCF, cộng đồng lớn nhất trong ba ứng viên | Tích cực | Tích cực |
| Độ khó tích hợp | Thấp — OIDC chuẩn, nhiều ví dụ sẵn | Thấp | Thấp |

**Giới hạn của khảo sát**: chỉ dựng thử Keycloak. Issue #19 yêu cầu dựng thử ít nhất một
ứng viên, và Keycloak là ứng viên dẫn đầu sau bước sàng lọc giấy phép nên được ưu tiên
kiểm chứng. Số liệu tài nguyên của Zitadel và Authentik **chưa được đo**, không nên trích
dẫn như dữ kiện.

---

## 4. Kết quả dựng thử Keycloak

### 4.1. Môi trường

| Mục | Giá trị |
|---|---|
| Phiên bản Keycloak | `26.7.3` trên JVM (Quarkus 3.33.3.1) |
| Kho dữ liệu | PostgreSQL `16-alpine` |
| Docker Engine | 29.7.2 |
| Máy thử | 24 CPU, 8.3 GB RAM cấp cho Docker |
| Chế độ chạy | `start-dev` — chỉ dùng cho dựng thử, không phải cấu hình sản phẩm |

### 4.2. Số liệu đo được

| Hạng mục | Kết quả |
|---|---|
| RAM Keycloak | **969.9 MiB** |
| RAM PostgreSQL | 54.2 MiB |
| **Tổng cụm** | **~1.02 GB** |
| Thời gian khởi động | 15.7 giây |
| Vòng đời access token | 300 giây (mặc định) |
| Thuật toán ký token | RS256, khóa công khai phơi qua JWKS |

### 4.3. Các phép kiểm chứng và kết quả

| Phép kiểm | Kết quả |
|---|---|
| Nạp realm từ tệp JSON lúc khởi động | Đạt — nhật ký ghi realm đã được nhập và tiến trình nhập kết thúc thành công |
| Bốn vai trò nghiệp vụ xuất hiện trong token | Đạt — mỗi tài khoản mang đúng một vai trong claim `realm_access.roles` |
| Lấy token qua điểm cuối OIDC | Đạt — cả bốn tài khoản mẫu |
| Điểm cuối phát hiện cấu hình OIDC | Đạt — đủ `issuer`, `authorization_endpoint`, `token_endpoint`, `jwks_uri`, `end_session_endpoint`, `userinfo_endpoint` |
| Khóa công khai để xác thực token | Đạt — JWKS trả về khóa ký RS256 |
| Kiểm tra âm: sai mật khẩu | Đạt — trả về `invalid_grant`, từ chối đúng |

Bốn vai trò được khai báo bằng định danh tiếng Anh (`requester`, `coordinator`, `handler`,
`department-head`), phần tiếng Việt đặt ở trường mô tả. Lý do: tên vai trò đi vào token và
vào mã phân quyền nên nó là **định danh**, phải theo quy ước tiếng Anh của
`ARCHITECTURE.md` mục 8.3; còn "Điều phối viên" là chuỗi hiển thị cho người dùng.

### 4.4. Cách tái hiện

Cụm dựng thử gồm hai tệp: một tệp Compose khai báo Keycloak và PostgreSQL, một tệp JSON
mô tả realm. Keycloak được chạy với `start-dev --import-realm`, tệp realm gắn vào thư mục
`/opt/keycloak/data/import/`.

Các tệp này **cố ý không đưa vào kho mã**. Chúng dùng chế độ `start-dev` và mật khẩu mẫu,
không phải cấu hình sản phẩm; đưa vào kho sẽ tạo ấn tượng sai rằng hệ thống đã có hạ tầng
định danh chạy được. Hạ tầng thật sẽ do một công việc riêng dựng, kèm `.env.example` và
hướng dẫn trong `README.md`.

---

## 5. Ba phát hiện ảnh hưởng tới quyết định

### 5.1. Vai trò nạp được từ dữ liệu — phát hiện quan trọng nhất

Toàn bộ realm gồm bốn vai trò, hai ứng dụng khách và bốn người dùng được nạp từ **một tệp
JSON duy nhất** lúc khởi động, không cần thao tác tay nào trên giao diện quản trị.

Đây là kết quả có giá trị nhất của lần khảo sát, vì nó trả lời trực tiếp ràng buộc khó nhất
của dự án: `ARCHITECTURE.md` mục 5 bắt buộc danh sách vai trò phải là dữ liệu thay được, do
đề thi tháng 11/2026 có thể quy định bộ vai trò khác. Với cơ chế nhập realm, việc thích ứng
là **sửa một tệp dữ liệu**, không phải sửa mã.

### 5.2. Xác thực token cục bộ, không phụ thuộc thời gian chạy

Keycloak ký token bằng RS256 và phơi khóa công khai qua JWKS. Dịch vụ FastAPI tải khóa một
lần rồi **tự kiểm chữ ký cho từng yêu cầu**, không phải gọi ngược sang Keycloak.

Hai hệ quả: Keycloak không nằm trên đường đi nóng của mỗi yêu cầu; và nếu Keycloak tạm dừng,
các token còn hạn vẫn dùng được. Ranh giới giữa nền tảng lắp ghép và mã tự viết vì thế rất
sạch — đúng tinh thần kiến trúc Open-Core.

### 5.3. Chi phí bộ nhớ là có thật và cần theo dõi ở cấp toàn hệ thống

Con số 970 MiB xác nhận nhược điểm đã dự đoán của Keycloak. Xét riêng cho không gian `H`,
mức này chấp nhận được ở quy mô trình diễn.

Nhưng nó **không đứng một mình**. Các khảo sát #21 (nền tảng BI) và #24 (lưu trữ đối tượng)
sẽ cộng thêm dịch vụ vào cùng một tệp Compose, bên cạnh PostgreSQL chính, FastAPI và Next.js.
Bảng chấm PoF mục 4 đòi `docker compose up` chạy được **trên máy sạch** vào ngày chấm, mà
máy đó không chắc mạnh bằng máy phát triển.

Đây không phải lý do bác Keycloak, nhưng là lý do phải **theo dõi tổng ngân sách bộ nhớ**
khi chốt hai khảo sát còn lại, và cân nhắc cấu hình giới hạn bộ nhớ JVM cho Keycloak ở
bước tích hợp thật.

---

## 6. Kết luận

Keycloak được chọn. Lập luận đầy đủ, các phương án bị loại và hệ quả của quyết định được
ghi trong [`adr/0001-chon-nen-tang-sso.md`](adr/0001-chon-nen-tang-sso.md).

---

## 7. Việc cần rà soát lại trước khi nộp bài

Theo cảnh báo ở cuối `dependencies.md`, thông tin giấy phép của dự án nguồn mở có thể thay
đổi theo thời gian.

- [ ] Kiểm tra lại giấy phép của Keycloak vẫn là Apache-2.0
- [ ] Kiểm tra phiên bản `26.7.3` còn được hỗ trợ, cân nhắc nâng cấp nếu có bản vá bảo mật
- [ ] Đo lại tổng bộ nhớ toàn cụm sau khi tích hợp đủ các nền tảng của #21 và #24
