# ADR-0001: Nền tảng định danh tập trung cho không gian H

| Mục | Giá trị |
|---|---|
| Trạng thái | Đã chấp nhận |
| Ngày | 2026-09-06 |
| Không gian kiến trúc | `H` |
| Issue liên quan | #19 |
| Người quyết định | Navigator (`AlaVox-lab`), theo định hướng của giảng viên hướng dẫn |

---

## Bối cảnh

Không gian `H` cần một nền tảng định danh tập trung cung cấp đăng nhập một lần, quản lý
danh tính và phân quyền theo vai trò cho toàn hệ thống. Bốn vai trò nghiệp vụ phải biểu
diễn được: người gửi yêu cầu, điều phối viên, người xử lý, trưởng bộ phận.

Đây là thành phần **lắp ghép**. `CLAUDE.md` mục 3.2 xếp SSO vào nhóm nền tảng nguồn mở có
sẵn phải tích hợp, không phải nhóm tự phát triển. Tự viết phần này vừa tốn nhiều tuần công,
vừa đi ngược tiêu chí chấm điểm về *tính nguyên gốc của kiến trúc lắp ghép*.

Bốn ràng buộc chi phối quyết định:

1. **Giấy phép** — bảng chấm PoF mục 2 (10 điểm) đòi giấy phép được OSI công nhận và tương
   thích MIT. Một giấy phép sai khiến toàn dự án không đủ điều kiện chấm.
2. **Cấu hình thay vì mã cứng** — `ARCHITECTURE.md` mục 5 bắt buộc danh sách vai trò nằm
   trong dữ liệu. Đề thi chính thức chỉ công bố tháng 11/2026 và có thể quy định bộ vai trò
   khác, nên nền tảng phải cho phép thay vai trò bằng cách sửa dữ liệu.
3. **Dựng bằng một lệnh** — bảng chấm PoF mục 4 (10 điểm) đòi hệ thống dựng được trên máy
   sạch, nên nền tảng phải có ảnh chứa chính thức và cấu hình được bằng biến môi trường.
4. **Không sửa mã thư viện bên thứ ba** — bảng chấm PoF mục 5 (10 điểm). Việc tích hợp phải
   đi qua giao thức chuẩn.

Quá trình khảo sát và số liệu đo được ghi đầy đủ trong
[`../sso-platform-survey.md`](../sso-platform-survey.md).

---

## Các phương án đã cân nhắc

### Phương án A — Keycloak

| Mục | Nội dung |
|---|---|
| Giấy phép | Apache-2.0 |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có, không điều kiện |
| Tài nguyên khi chạy | 969.9 MiB, đo thật khi dựng thử |
| Khả năng đóng gói bằng container | Ảnh chính thức, đã dựng thử thành công |
| Chất lượng tài liệu | Rất đầy đủ |
| Mức độ hoạt động của dự án | Dự án của CNCF, cộng đồng lớn nhất trong ba ứng viên |
| Độ khó tích hợp | Thấp — OIDC chuẩn, nhiều ví dụ sẵn cho cả React lẫn Python |

**Ưu điểm**

- Giấy phép Apache-2.0 sạch, không kèm điều kiện nào
- Nạp toàn bộ realm gồm vai trò, ứng dụng khách và người dùng từ một tệp JSON lúc khởi
  động — đáp ứng trực tiếp ràng buộc cấu hình thay vì mã cứng
- Ký token bằng RS256 và phơi khóa công khai qua JWKS, cho phép dịch vụ ứng dụng tự xác
  thực token mà không gọi ngược
- Hỗ trợ đầy đủ cả OIDC lẫn SAML, phòng khi đề thi yêu cầu tích hợp hệ thống khác
- Cộng đồng lớn nhất, giảm rủi ro tắc khi tích hợp — yếu tố quan trọng với nhóm có quỹ
  thời gian hạn chế trước tháng 12
- Được CNCF bảo trợ, là điểm cộng cho tiêu chí phát triển bền vững

**Nhược điểm**

- Tốn bộ nhớ nhất trong ba ứng viên: gần 1 GB cho riêng dịch vụ này
- Chạy trên JVM, thời gian khởi động 15.7 giây, chậm hơn các nền tảng biên dịch sẵn

### Phương án B — Zitadel

| Mục | Nội dung |
|---|---|
| Giấy phép | Apache-2.0 |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có, không điều kiện |
| Tài nguyên khi chạy | Chưa đo — viết bằng Go, dự kiến nhẹ hơn Keycloak |
| Khả năng đóng gói bằng container | Ảnh chính thức |
| Chất lượng tài liệu | Tốt |
| Mức độ hoạt động của dự án | Tích cực |
| Độ khó tích hợp | Thấp |

**Ưu điểm**

- Giấy phép sạch ngang Keycloak
- Viết bằng Go nên nhẹ hơn đáng kể, khởi động nhanh hơn
- Dùng PostgreSQL làm kho dữ liệu, không thêm loại cơ sở dữ liệu mới vào hệ thống

**Nhược điểm**

- Cộng đồng nhỏ hơn Keycloak, ít ví dụ tích hợp sẵn hơn khi gặp trục trặc
- Chưa được dựng thử trong khảo sát này, nên các ưu điểm về tài nguyên vẫn là dự kiến
  theo tài liệu chứ chưa phải số đo

### Phương án C — Authentik

| Mục | Nội dung |
|---|---|
| Giấy phép | MIT ở phần lõi; thư mục `enterprise/` theo giấy phép thương mại riêng |
| Được OSI công nhận | Có, với phần lõi |
| Tương thích với MIT | Có, **có điều kiện** — phải tránh tính năng Enterprise |
| Tài nguyên khi chạy | Chưa đo — nền Python |
| Khả năng đóng gói bằng container | Ảnh chính thức |
| Chất lượng tài liệu | Tốt |
| Mức độ hoạt động của dự án | Tích cực |
| Độ khó tích hợp | Thấp |

**Ưu điểm**

- Phần lõi dùng MIT, trùng đúng giấy phép của sản phẩm
- Nền Python, cùng ngôn ngữ với tầng dịch vụ ứng dụng và tầng `I` của dự án

**Nhược điểm**

- Giấy phép **tách đôi**: phải liên tục canh chừng ranh giới giữa phần lõi MIT và phần
  Enterprise thương mại. Lỡ dùng một tính năng thuộc phần Enterprise là tạo ra sự không
  tương thích giấy phép ngay trong sản phẩm, đúng thứ bảng chấm PoF mục 2 trừ điểm
- Rủi ro này phải gánh suốt vòng đời dự án, trong khi hai phương án còn lại không có

### Phương án D — Ory (Kratos + Hydra)

Được nêu trong issue nhưng không đưa vào so sánh sâu. Đây là bộ thành phần rời cần tự lắp
thành một hệ hoàn chỉnh; chi phí tích hợp cao hơn hẳn ba phương án trên, trong khi nhóm chỉ
cần một nền tảng trọn gói và đang bị giới hạn thời gian.

---

## Quyết định

Chọn **Keycloak** làm nền tảng định danh tập trung cho không gian `H`, ghim phiên bản
`26.7.3`.

---

## Lý do

**Tiêu chí quyết định chính là khả năng khai báo vai trò bằng dữ liệu.** Lần dựng thử xác
nhận Keycloak nạp trọn realm — bốn vai trò, hai ứng dụng khách, bốn người dùng — từ một tệp
JSON lúc khởi động, không cần thao tác tay nào. Điều này trả lời trực tiếp ràng buộc khó
nhất của dự án: khi đề thi tháng 11/2026 công bố và có thể đổi bộ vai trò, việc thích ứng
chỉ là sửa một tệp dữ liệu chứ không phải sửa mã.

**Tiêu chí thứ hai là rủi ro tích hợp.** Nhóm còn rất ít thời gian sau khi đề thi công bố,
nên khả năng tìm được lời giải khi gặp trục trặc quan trọng hơn vài trăm MiB bộ nhớ. Keycloak
có cộng đồng lớn nhất trong ba ứng viên, tài liệu đầy đủ nhất, và được CNCF bảo trợ.

**Zitadel bị loại dù không có nhược điểm nào rõ rệt.** Giấy phép sạch ngang Keycloak và nhẹ
hơn về tài nguyên. Nó thua ở chỗ cộng đồng nhỏ hơn, và ưu thế tài nguyên của nó vẫn chưa
được đo trong khảo sát này. Đây là phương án lùi hợp lý nếu tổng ngân sách bộ nhớ của hệ
thống về sau trở thành vấn đề thật.

**Authentik bị loại vì lý do giấy phép, và đây là điểm cần ghi rõ để người sau không đề xuất
lại.** Phần lõi dùng MIT nên hợp lệ, nhưng giấy phép bị tách đôi với thư mục `enterprise/`
theo giấy phép thương mại. Chọn nó nghĩa là nhóm phải canh ranh giới ấy suốt vòng đời dự án,
và một lần lỡ tay là tạo ra sự không tương thích giấy phép ngay trong sản phẩm. Hai phương án
còn lại không bắt nhóm gánh rủi ro đó, nên không có lý do gì để nhận nó.

**Nhược điểm bộ nhớ được chấp nhận có ý thức.** Gần 1 GB là cái giá thật, nhưng ở quy mô
trình diễn thì chấp nhận được, và nó được bù lại bằng rủi ro tích hợp thấp nhất.

---

## Cách tích hợp

**Chạy như dịch vụ độc lập**, giao tiếp qua giao thức OIDC. Không nhúng bất kỳ thư viện nào
của Keycloak vào mã nguồn dự án, không sửa mã nguồn của nền tảng.

Ranh giới kiến trúc:

| Thành phần | Vai trò | Cách nói chuyện với Keycloak |
|---|---|---|
| Cổng người dùng (Next.js) | Ứng dụng khách công khai `dx-portal` | Chuyển hướng người dùng sang Keycloak để đăng nhập, nhận lại token |
| Dịch vụ ứng dụng (FastAPI) | Ứng dụng khách bí mật `dx-api` | Tải khóa công khai qua JWKS một lần, tự kiểm chữ ký token cho từng yêu cầu |
| Keycloak | Nguồn sự thật về danh tính và vai trò | Nạp realm từ tệp JSON lúc khởi động |
| PostgreSQL của Keycloak | Kho dữ liệu của nền tảng | Tách riêng, không dùng chung với cơ sở dữ liệu nghiệp vụ |

Vì token ký bằng RS256 và khóa công khai lấy được qua JWKS, dịch vụ ứng dụng **không gọi
ngược sang Keycloak ở mỗi yêu cầu**. Keycloak nằm ngoài đường đi nóng.

Bốn vai trò khai báo bằng định danh tiếng Anh, phần tiếng Việt đặt ở trường mô tả, theo quy
ước ngôn ngữ của `ARCHITECTURE.md` mục 8.3:

| Định danh | Vai trò nghiệp vụ |
|---|---|
| `requester` | Người gửi yêu cầu |
| `coordinator` | Điều phối viên |
| `handler` | Người xử lý |
| `department-head` | Trưởng bộ phận |

---

## Hệ quả

**Điều gì trở nên dễ hơn**

- Nhóm không phải viết bảng người dùng, băm mật khẩu, phiên đăng nhập, hay trang quản trị
  người dùng — tiết kiệm nhiều tuần công và tránh tự cài đặt lại một thành phần bảo mật
- Thay đổi bộ vai trò khi đề thi công bố chỉ là sửa tệp dữ liệu realm
- Thêm người dùng và đổi vai trò làm được bằng giao diện, không cần lập trình viên
- Về sau, nền tảng kinh doanh thông minh được chốt ở #21 dùng chung một lần đăng nhập với
  cổng người dùng, không bắt người dùng đăng nhập hai lần
- Ranh giới sạch giữa nền tảng lắp ghép và mã tự viết, thuận lợi khi trình bày kiến trúc
  Open-Core trước ban giám khảo

**Điều gì trở nên khó hơn**

- Thêm gần 1 GB bộ nhớ và một dịch vụ PostgreSQL riêng vào tổng cụm. Cần theo dõi tổng ngân
  sách bộ nhớ khi chốt #21 và #24, vì bảng chấm PoF mục 4 đòi hệ thống dựng được trên máy
  sạch mà máy chấm không chắc mạnh bằng máy phát triển
- Cấu hình dựng thử dùng chế độ `start-dev`, **không dùng được cho sản phẩm**. Bước tích hợp
  thật phải chuyển sang chế độ sản phẩm, cấu hình tên miền và chứng chỉ cho đúng
- Nhóm phải nắm thêm khái niệm của Keycloak: realm, client, realm role, ánh xạ claim
- Phụ thuộc vào một dịch vụ ngoài khi khởi động: hệ thống cần Keycloak sẵn sàng trước khi
  người dùng đăng nhập được

**Việc phải làm tiếp sau quyết định này**

- [x] Cập nhật `docs/ARCHITECTURE.md` mục 3 — chuyển SSO từ nhóm chờ khảo sát sang nhóm đã chốt
      *(đã làm trong cùng công việc này, theo mục 12 của tệp đó)*
- [x] Cập nhật `docs/dependencies.md` — ghi Keycloak vào bảng nền tảng Open-Core
      *(đã làm trong cùng công việc này)*
- [ ] Tạo công việc riêng dựng `infra/docker-compose.yml` thật, kèm `.env.example`
- [ ] Tạo công việc riêng tích hợp Keycloak vào cổng Next.js và dịch vụ FastAPI
- [ ] Chuyển cấu hình từ chế độ `start-dev` sang chế độ sản phẩm
- [ ] Cân nhắc đặt giới hạn bộ nhớ cho JVM của Keycloak trong tệp Compose

---

## Ghi chú

Số liệu tài nguyên trong bản ghi này đo trên một máy cụ thể (24 CPU, 8.3 GB RAM cấp cho
Docker) ở chế độ `start-dev`. Cấu hình sản phẩm có thể cho con số khác.

Zitadel và Authentik **không được dựng thử** trong khảo sát này. Các nhận định về tài nguyên
của hai nền tảng đó dựa trên tài liệu chính thức, không phải số đo, và không nên trích dẫn
như dữ kiện đã kiểm chứng.

**Điều kiện khiến quyết định này cần xem lại**:

- Keycloak đổi sang giấy phép không thuộc danh sách OSI
- Tổng bộ nhớ toàn cụm sau khi tích hợp #21 và #24 vượt quá khả năng của máy trình diễn —
  khi đó cân nhắc phương án lùi Zitadel
- Đề thi tháng 11/2026 yêu cầu một cơ chế định danh mà Keycloak không đáp ứng được
