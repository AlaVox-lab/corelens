# ADR-0002: Nền tảng lưu trữ đối tượng cho tệp đính kèm

| Mục | Giá trị |
|---|---|
| Trạng thái | Đã chấp nhận |
| Ngày | 2026-09-06 |
| Không gian kiến trúc | `core` |
| Issue liên quan | #24 |
| Người quyết định | Navigator (`AlaVox-lab`) |

---

## Bối cảnh

Chức năng yêu cầu nội bộ cần đính kèm tệp: ảnh hiện trường sự cố thiết bị, báo giá vật tư,
tài liệu quét. Lưu tệp nhị phân trực tiếp trong PostgreSQL là lựa chọn sai — nó làm phình
cơ sở dữ liệu nghiệp vụ, làm chậm sao lưu và trộn lẫn hai loại dữ liệu có vòng đời khác nhau.

Cần một kho lưu trữ đối tượng riêng, phơi S3 API để dịch vụ ứng dụng nối vào bằng thư viện
chuẩn. Siêu dữ liệu của tệp (tên, loại, kích thước, `case_id`) vẫn nằm trong PostgreSQL cùng
hồ sơ yêu cầu; chỉ phần nội dung nhị phân đi ra kho đối tượng.

Bốn ràng buộc chi phối:

1. **Giấy phép** — bảng chấm PoF mục 2 (10 điểm) đòi giấy phép được OSI công nhận và tương
   thích MIT.
2. **Đổi được bằng cấu hình** — `ARCHITECTURE.md` mục 5. Nền tảng phải phơi S3 API chuẩn để
   điểm cuối và khóa truy cập nằm trong biến môi trường.
3. **Dựng bằng một lệnh** — bảng chấm PoF mục 4 (10 điểm).
4. **Còn được bảo trì** — tiêu chí phát triển bền vững đánh giá qua tài liệu kỹ thuật. Một
   phụ thuộc có thượng nguồn ngừng hoạt động là nợ kỹ thuật phải khai báo.

Quá trình khảo sát và số liệu đo được ghi trong
[`../object-storage-survey.md`](../object-storage-survey.md).

---

## Các phương án đã cân nhắc

### Phương án A — SeaweedFS

| Mục | Nội dung |
|---|---|
| Giấy phép | Apache-2.0 |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có, không điều kiện |
| Tương thích S3 | Có — chín trên chín phép kiểm đạt khi dựng thử |
| Tài nguyên khi chạy | 75.8 MiB, đo thật |
| Khả năng đóng gói bằng container | Ảnh chính thức 182 MB, khởi động 3.0 giây |
| Chất lượng tài liệu | Tốt |
| Mức độ hoạt động của dự án | Rất tích cực — năm bản phát hành trong tháng 8/2026, mới nhất là `4.45` ngày 31/08/2026 |
| Độ khó tích hợp | Thấp — S3 API chuẩn, dùng được với `boto3` không cần tùy chỉnh |

**Ưu điểm**

- Giấy phép Apache-2.0 dễ dãi, là ứng viên duy nhất không kèm ràng buộc copyleft
- Rất nhẹ: 75.8 MiB, gần như không ảnh hưởng tổng ngân sách bộ nhớ của hệ thống
- Presigned URL hoạt động cả chiều tải lên lẫn tải về, cho phép trình duyệt làm việc trực
  tiếp với kho lưu trữ mà không đi qua dịch vụ ứng dụng
- Chế độ `server` gộp bốn vai trò vào một tiến trình, chỉ thêm đúng một dịch vụ vào Compose
- Đang phát triển rất tích cực, rủi ro thượng nguồn ngừng hoạt động thấp

**Nhược điểm**

- Gửi thống kê cụm ẩn danh ra ngoài theo mặc định, phải chủ động tắt bằng `-master.telemetry=false`
- Cộng đồng nhỏ hơn MinIO, ít hướng dẫn sẵn hơn khi gặp trục trặc
- Chế độ gộp một tiến trình không phải cách triển khai ở quy mô sản xuất thật

### Phương án B — Garage

| Mục | Nội dung |
|---|---|
| Giấy phép | AGPL-3.0 |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có, **có điều kiện** — chỉ khi chạy như dịch vụ độc lập |
| Tương thích S3 | Có, theo tài liệu — chưa dựng thử |
| Tài nguyên khi chạy | Chưa đo. Viết bằng Rust, theo tài liệu là rất nhẹ |
| Khả năng đóng gói bằng container | Ảnh chính thức |
| Chất lượng tài liệu | Khá |
| Mức độ hoạt động của dự án | Tích cực, ảnh chứa cập nhật trong ngày tra cứu |
| Độ khó tích hợp | Thấp |

**Ưu điểm**

- Vẫn đang được bảo trì, nên nếu buộc phải sống chung lâu dài thì đây là phương án bền vững
- Rất nhẹ, phù hợp ràng buộc ngân sách bộ nhớ
- Phơi S3 API nên việc thay thế chỉ là đổi cấu hình

**Nhược điểm**

- AGPL-3.0 buộc phải chạy như dịch vụ độc lập, không được nhúng thư viện vào mã nguồn
- Cộng đồng nhỏ nhất trong ba ứng viên, khó tra cứu khi gặp sự cố

### Phương án C — MinIO

| Mục | Nội dung |
|---|---|
| Giấy phép | AGPL-3.0 |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có, **có điều kiện** — chỉ khi chạy như dịch vụ độc lập |
| Tương thích S3 | Có, là chuẩn tham chiếu thực tế của giới |
| Tài nguyên khi chạy | Chưa đo |
| Khả năng đóng gói bằng container | Ảnh chính thức, nhưng bản mới nhất đã cũ |
| Chất lượng tài liệu | Rất tốt |
| Mức độ hoạt động của dự án | **Ngừng phát hành khoảng 12 tháng** — ảnh Docker nguồn mở mới nhất ngày 07/09/2025, bản phát hành trên kho mã mới nhất ngày 16/10/2025 |
| Độ khó tích hợp | Thấp nhất, nhiều hướng dẫn nhất |

**Ưu điểm**

- Quen thuộc nhất, hệ sinh thái tài liệu và ví dụ phong phú nhất
- Là chuẩn tham chiếu thực tế cho tương thích S3

**Nhược điểm**

- Kho nguồn mở đã bị đánh dấu ngừng bảo trì và dồn về sản phẩm thương mại; bản cộng đồng bị
  cắt giao diện quản trị
- Không nhận bản vá bảo mật mới trong khoảng một năm, trong khi đây là thành phần giữ tệp
  do người dùng tải lên
- Muốn có đầy đủ chức năng thì phải ghim một phiên bản còn cũ hơn nữa, làm khoảng cách bảo
  mật rộng thêm

---

## Quyết định

Chọn **SeaweedFS** phiên bản `4.45` làm nền tảng lưu trữ đối tượng cho tệp đính kèm.

Hai phương án dự phòng được ghi nhận với điều kiện kích hoạt khác nhau:

| Phương án | Vai trò | Kích hoạt khi |
|---|---|---|
| **Garage** | Bản lùi mặc định | SeaweedFS gặp trở ngại không vượt qua được trong quá trình phát triển. Chọn vì vẫn được bảo trì, nên nếu phải dùng lâu dài thì bền vững |
| **MinIO** | Bản lùi **có điều kiện** | Chỉ dùng khi cần giải pháp gấp và cần hệ sinh thái quen thuộc, ví dụ sát ngày trình diễn. Bắt buộc kèm: ghim phiên bản cụ thể, chỉ dùng qua S3 API, ghi rõ rủi ro bảo trì vào tài liệu |

---

## Lý do

**SeaweedFS là ứng viên duy nhất đồng thời có giấy phép dễ dãi và thượng nguồn còn sống.**
Garage và MinIO đều dùng AGPL-3.0, hợp lệ nhưng buộc phải giữ ranh giới dịch vụ độc lập.
SeaweedFS dùng Apache-2.0 nên không mang theo ràng buộc nào.

**Lần dựng thử xác nhận nó đáp ứng đúng nhu cầu nghiệp vụ, không chỉ chạy được.** Chín phép
kiểm đều đạt, trong đó hai phép quan trọng nhất là presigned URL hai chiều — cho phép trình
duyệt tải tệp lên và tải về trực tiếp, giữ dịch vụ ứng dụng khỏi đường truyền tệp lớn — và
phép kiểm âm xác nhận URL hết hạn thì bị từ chối.

**Chi phí tài nguyên gần như bằng không.** 75.8 MiB là mức không đáng kể so với ngân sách
bộ nhớ toàn hệ thống, vốn đã bị Keycloak chiếm khoảng 1 GB ở ADR-0001. Đây là yếu tố quan
trọng vì bảng chấm đòi hệ thống dựng được trên máy sạch vào ngày chấm.

**MinIO bị loại khỏi vị trí chính vì lý do bảo trì, và đây là điểm cần ghi rõ để người sau
không đề xuất lại.** Nó là ứng viên quen thuộc nhất và dễ bị chọn theo quán tính. Nhưng số
liệu tra ngày 2026-09-06 cho thấy ảnh Docker nguồn mở của nó đứng im tròn mười hai tháng.
Đưa một thành phần giữ tệp người dùng vào sản phẩm mà biết trước nó không còn nhận bản vá
bảo mật là quyết định khó biện minh trước tiêu chí phát triển bền vững.

**Giữ cả hai phương án dự phòng là có chủ ý, không phải vì chưa quyết được.** Vì cả ba đều
phơi S3 API, việc thay thế chỉ là đổi biến môi trường. Hai phương án phục vụ hai tình huống
khác nhau: Garage cho trường hợp phải sống chung lâu dài, MinIO cho trường hợp cần gấp một
thứ chắc chắn chạy được ngay.

---

## Cách tích hợp

**Chạy như dịch vụ độc lập**, giao tiếp qua S3 API. Dịch vụ ứng dụng dùng thư viện khách S3
tiêu chuẩn (`boto3`), không nhúng bất kỳ mã nguồn nào của nền tảng.

| Thành phần | Vai trò |
|---|---|
| Cổng người dùng (Next.js) | Tải tệp lên và tải về trực tiếp bằng presigned URL do dịch vụ ứng dụng cấp |
| Dịch vụ ứng dụng (FastAPI) | Cấp phát presigned URL, ghi siêu dữ liệu tệp vào PostgreSQL. Không làm trung gian truyền tệp |
| SeaweedFS | Lưu nội dung nhị phân |
| PostgreSQL | Lưu siêu dữ liệu: tên tệp, loại, kích thước, `case_id`, khóa đối tượng |

### Ràng buộc bắt buộc để giữ khả năng thay thế

Lời hứa "đổi nền tảng chỉ bằng cấu hình" **chỉ đúng nếu nhóm tự giữ kỷ luật sau**:

1. Mã nguồn **chỉ được gọi S3 API chuẩn**. Tuyệt đối không dùng tính năng hay điểm cuối
   riêng của SeaweedFS. Chỉ cần một lần vi phạm là lời hứa này gãy.
2. Điểm cuối, khóa truy cập, tên bucket **phải nằm trong biến môi trường**, không mã cứng.
3. Thời hạn của presigned URL là **giá trị cấu hình**, không mã cứng.

Vi phạm bất kỳ điểm nào ở trên biến hai phương án dự phòng thành vô dụng.

---

## Hệ quả

**Điều gì trở nên dễ hơn**

- Tệp nhị phân tách khỏi cơ sở dữ liệu nghiệp vụ, giữ PostgreSQL gọn và sao lưu nhanh
- Tệp đính kèm lớn không đi qua dịch vụ ứng dụng, giảm tải cho FastAPI
- Đổi sang nền tảng khác chỉ là đổi biến môi trường, miễn là giữ đúng ba ràng buộc ở trên
- Chỉ thêm một dịch vụ vào Compose, không làm phức tạp lệnh dựng
- Tăng thêm chưa tới 80 MiB vào tổng ngân sách bộ nhớ

**Điều gì trở nên khó hơn**

- Thêm một dịch vụ nữa phải khởi động, cấu hình và sao lưu
- Nhóm phải nắm khái niệm presigned URL và vòng đời của nó
- Phải nhớ tắt `-telemetry` trong cấu hình sản phẩm
- Cần quy ước đặt tên khóa đối tượng ngay từ đầu; khảo sát dùng dạng
  `case-<mã hồ sơ>/<tên tệp>` nhưng đây chưa phải quyết định chính thức

**Việc phải làm tiếp sau quyết định này**

- [x] Cập nhật `docs/ARCHITECTURE.md` mục 3 *(đã làm trong cùng công việc này)*
- [x] Cập nhật `docs/dependencies.md` *(đã làm trong cùng công việc này)*
- [ ] Bổ sung SeaweedFS vào `infra/docker-compose.yml` khi dựng hạ tầng thật, kèm
      `-master.telemetry=false`
- [ ] Chốt quy ước đặt tên khóa đối tượng và ghi vào `ARCHITECTURE.md`
- [ ] Chốt giới hạn kích thước tệp và danh sách loại tệp được phép — thuộc lớp Poka-yoke
- [ ] Đưa `boto3` vào tệp khai báo phụ thuộc của dịch vụ ứng dụng kèm ghim phiên bản

---

## Ghi chú

Số liệu tài nguyên đo trên một máy cụ thể (24 CPU, 8.3 GB RAM cấp cho Docker) ở chế độ
`server` gộp bốn vai trò. Cấu hình tách vai trò sẽ cho con số khác.

Garage và MinIO **không được dựng thử**. Các nhận định về chúng dựa trên tài liệu chính thức
và dữ liệu phát hành công khai, không phải số đo.

Số liệu về mức độ hoạt động của các dự án được tra ngày 2026-09-06. Đây là loại thông tin
thay đổi theo thời gian, cần kiểm lại trước khi nộp bài.

**Điều kiện khiến quyết định này cần xem lại**:

- SeaweedFS đổi sang giấy phép không thuộc danh sách OSI, hoặc ngừng phát hành
- Phát hiện lỗi tương thích S3 khi hiện thực chức năng đính kèm thật
- Nhu cầu vượt quá quy mô trình diễn, đòi tách vai trò thành nhiều tiến trình
