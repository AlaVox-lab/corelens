# Khảo sát nền tảng lưu trữ đối tượng cho tệp đính kèm

> **Mục đích**: ghi lại quá trình và kết quả khảo sát nền tảng lưu trữ đối tượng dùng cho
> chức năng đính kèm tệp, làm căn cứ cho bản ghi quyết định
> [`adr/0002-chon-nen-tang-luu-tru-doi-tuong.md`](adr/0002-chon-nen-tang-luu-tru-doi-tuong.md).
>
> **Issue liên quan**: #24 · **Ngày thực hiện**: 2026-09-06

---

## 1. Câu hỏi cần trả lời

Chọn nền tảng lưu trữ đối tượng tương thích S3 nào để lưu tệp đính kèm của yêu cầu nội bộ —
ảnh hiện trường sự cố thiết bị, báo giá vật tư, tài liệu quét?

Đây là hạ tầng dùng chung, thuộc `space/core`. Dịch vụ ứng dụng nối qua S3 API; phần siêu
dữ liệu của tệp (tên, loại, kích thước, `case_id`) ghi vào PostgreSQL cùng hồ sơ yêu cầu.

### 1.1. Ràng buộc chi phối

| Ràng buộc | Nguồn | Hệ quả với khảo sát |
|---|---|---|
| Giấy phép được OSI công nhận, tương thích MIT | Bảng chấm PoF mục 2 (10 điểm) | Ưu tiên giấy phép dễ dãi; nếu buộc dùng copyleft mạnh thì chỉ dưới dạng dịch vụ độc lập |
| Đổi được nền tảng bằng cấu hình | `ARCHITECTURE.md` mục 5 | Phải phơi S3 API chuẩn để điểm cuối và khóa truy cập nằm trong biến môi trường |
| Dựng bằng một lệnh trên máy sạch | Bảng chấm PoF mục 4 (10 điểm) | Ảnh chứa chính thức, không đòi thao tác tay |
| Dự án còn được bảo trì | Tiêu chí phát triển bền vững | Phụ thuộc có thượng nguồn ngừng hoạt động là nợ kỹ thuật |

---

## 2. Ứng viên và kiểm tra giấy phép

| Ứng viên | Giấy phép | OSI công nhận | Tương thích MIT | Cách dùng bắt buộc |
|---|---|---|---|---|
| **SeaweedFS** | Apache-2.0 | Có | Có, không điều kiện | Tự do |
| **Garage** | AGPL-3.0 | Có | Có, **có điều kiện** | Chỉ dịch vụ độc lập qua S3 API, không nhúng mã |
| **MinIO** | AGPL-3.0 | Có | Có, **có điều kiện** | Chỉ dịch vụ độc lập qua S3 API, không nhúng mã |

Cả ba đều được OSI công nhận nên đều hợp lệ về thể lệ. Nhưng chỉ SeaweedFS dùng giấy phép
dễ dãi; hai ứng viên còn lại dùng copyleft mạnh nên bắt buộc phải chạy như dịch vụ tách
biệt, giao tiếp qua mạng, đúng quy tắc ở `dependencies.md`.

### 2.1. Mức độ hoạt động — số liệu tra ngày 2026-09-06

Đây là tiêu chí phân hóa mạnh nhất giữa ba ứng viên, nên được tra cứu bằng dữ liệu thay vì
cảm nhận:

| Ứng viên | Bản phát hành mới nhất | Ảnh Docker mới nhất | Nhận xét |
|---|---|---|---|
| **SeaweedFS** | `4.45` — 31/08/2026 | cập nhật trong ngày | Năm bản phát hành từ `4.41` tới `4.45` chỉ trong tháng 8/2026 |
| **Garage** | dùng tag theo commit | cập nhật trong ngày | Vẫn phát triển đều |
| **MinIO** | `RELEASE.2025-10-15` — 16/10/2025 | **07/09/2025** | Ảnh Docker nguồn mở **đứng im tròn 12 tháng** |

Con số của MinIO xác nhận ghi chú trong issue #24 về việc kho nguồn mở bị đánh dấu ngừng
bảo trì và dồn về sản phẩm thương mại. Ngoài ra bản cộng đồng đã bị cắt giao diện quản trị.

---

## 3. Bảng so sánh

Ô ghi *(đo thật)* là số liệu thu được khi dựng thử ở mục 4. Ô ghi *(tài liệu)* chưa dựng thử.

| Tiêu chí | SeaweedFS | Garage | MinIO |
|---|---|---|---|
| Giấy phép | Apache-2.0 | AGPL-3.0 | AGPL-3.0 |
| Được OSI công nhận | Có | Có | Có |
| Tương thích MIT | Có | Có điều kiện | Có điều kiện |
| Tương thích S3 | Có *(đo thật — 9/9 phép kiểm)* | Có *(tài liệu)* | Có *(tài liệu)* |
| Tài nguyên khi chạy | 75.8 MiB *(đo thật)* | Nhẹ, nền Rust *(tài liệu)* | Chưa đo |
| Đóng gói bằng container | Ảnh chính thức 182 MB *(đo thật)* | Ảnh chính thức | Ảnh chính thức |
| Chất lượng tài liệu | Tốt | Khá | Rất tốt |
| Mức độ hoạt động | Rất tích cực | Tích cực | **Ngừng phát hành ~12 tháng** |
| Độ khó tích hợp | Thấp — S3 API chuẩn | Thấp | Thấp, nhiều hướng dẫn nhất |

**Giới hạn của khảo sát**: chỉ dựng thử SeaweedFS. Issue yêu cầu dựng thử ứng viên dẫn đầu,
và hai ứng viên còn lại chỉ đóng vai phương án dự phòng nên không đầu tư thời gian dựng.
Số liệu tài nguyên của Garage và MinIO **chưa được đo**, không nên trích dẫn như dữ kiện.

---

## 4. Kết quả dựng thử SeaweedFS

### 4.1. Môi trường

| Mục | Giá trị |
|---|---|
| Phiên bản | `4.45`, build `79b872021` |
| Chế độ chạy | `server -s3` — một tiến trình gồm master, volume, filer và cổng S3 |
| Thư viện khách | `boto3` 1.43.89, chữ ký `s3v4` |
| Docker Engine | 29.7.2 |
| Máy thử | 24 CPU, 8.3 GB RAM cấp cho Docker |

### 4.2. Số liệu đo được

| Hạng mục | Kết quả |
|---|---|
| RAM | **75.8 MiB** |
| Thời gian khởi động tới khi cổng S3 lắng nghe | **3.0 giây** |
| Kích thước ảnh chứa | 182 MB |
| Dung lượng đĩa sau bộ kiểm | 320 KB |

Để so sánh trong cùng hệ thống: Keycloak ở ADR-0001 chiếm 969.9 MiB và khởi động trong
15.7 giây. SeaweedFS nhẹ hơn khoảng mười ba lần.

### 4.3. Các phép kiểm chứng qua S3 API

Toàn bộ chín phép kiểm đều đạt:

| # | Phép kiểm | Kết quả |
|---|---|---|
| 1 | Tạo bucket | Đạt |
| 2 | Tải lên kèm siêu dữ liệu nghiệp vụ `case-id` | Đạt |
| 3 | Liệt kê đối tượng | Đạt |
| 4 | Giữ nguyên siêu dữ liệu và `Content-Type` | Đạt |
| 5 | Toàn vẹn dữ liệu — băm SHA-256 khớp sau khi tải về | Đạt |
| 6 | Presigned URL để **tải về**, gọi bằng HTTP thuần không kèm khóa | Đạt |
| 7 | Presigned URL để **tải lên**, gọi bằng HTTP thuần không kèm khóa | Đạt |
| 8 | Kiểm tra âm: URL hết hạn bị từ chối | Đạt — trả về HTTP 403 |
| 9 | Xóa đối tượng | Đạt |

Truy cập ẩn danh vào cổng S3 bị từ chối bằng HTTP 403, xác nhận cơ chế xác thực có hiệu lực
chứ không phải mở toang.

---

## 5. Ba phát hiện ảnh hưởng tới quyết định

### 5.1. Presigned URL chạy được cả hai chiều

Đây là phát hiện có giá trị kiến trúc lớn nhất. Trình duyệt tải tệp lên và tải tệp về
**trực tiếp với kho lưu trữ, không đi qua dịch vụ ứng dụng**.

Hai hệ quả. Thứ nhất, tệp đính kèm dung lượng lớn không chiếm băng thông và bộ nhớ của
FastAPI — dịch vụ ứng dụng chỉ cấp phát URL rồi đứng ngoài. Thứ hai, URL tự hết hạn theo
thời gian cấu hình được, nên không tạo ra đường truy cập vĩnh viễn vào tệp nội bộ; phép
kiểm số 8 xác nhận điều này bằng cách để URL hết hạn rồi nhận về HTTP 403.

### 5.2. Gửi số liệu thống kê ra ngoài theo mặc định

Nhật ký khởi động ghi rõ SeaweedFS báo cáo thống kê cụm ẩn danh về
`telemetry.seaweedfs.com` mỗi 24 giờ, và có thể tắt bằng cờ `-telemetry=false`.

Không phải lỗ hổng, nhưng một sản phẩm dự thi tự gọi ra Internet khi khởi động là điều cần
biết và cần chủ động tắt. **Cấu hình sản phẩm bắt buộc thêm `-telemetry=false`.**

### 5.3. Một container chạy cả bốn vai trò

Chế độ `server` gộp master, volume, filer và cổng S3 vào một tiến trình. Điều này rất tiện
cho mục tiêu dựng toàn hệ thống bằng một lệnh: chỉ thêm đúng một dịch vụ vào tệp Compose.

Cần ghi rõ rằng đây **không phải cách triển khai ở quy mô sản xuất thật**, nơi các vai trò
được tách thành tiến trình riêng để mở rộng độc lập. Với quy mô trình diễn của dự án, chế
độ gộp là lựa chọn đúng.

---

## 6. Ngân sách bộ nhớ toàn hệ thống

Theo dõi tích lũy qua từng quyết định Open-Core, vì bảng chấm PoF mục 4 đòi `docker compose
up` chạy được trên máy sạch vào ngày chấm:

| Thành phần | Bản ghi quyết định | RAM đo được |
|---|---|---|
| Keycloak và PostgreSQL của nó | ADR-0001 | ~1.02 GB |
| SeaweedFS | ADR-0002 | ~0.08 GB |
| **Cộng dồn hiện tại** | | **~1.10 GB** |

SeaweedFS gần như không làm thay đổi ngân sách. Ẩn số nặng còn lại là nền tảng kinh doanh
thông minh đang khảo sát ở issue #21.

---

## 7. Kết luận

SeaweedFS được chọn làm phương án chính. Garage là bản lùi mặc định, MinIO là bản lùi có
điều kiện. Lập luận đầy đủ và điều kiện kích hoạt của từng phương án được ghi trong
[`adr/0002-chon-nen-tang-luu-tru-doi-tuong.md`](adr/0002-chon-nen-tang-luu-tru-doi-tuong.md).

---

## 8. Việc cần rà soát lại trước khi nộp bài

- [ ] Kiểm tra lại giấy phép SeaweedFS vẫn là Apache-2.0
- [ ] Kiểm tra phiên bản `4.45` còn được hỗ trợ, cân nhắc nâng cấp nếu có bản vá bảo mật
- [ ] Xác nhận cấu hình sản phẩm đã tắt `-telemetry`
- [ ] Xác nhận mã nguồn không dùng bất kỳ API riêng nào của SeaweedFS, chỉ dùng S3 chuẩn
