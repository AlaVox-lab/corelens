# ADR-0010: Nền tảng cổng API cho lớp biên của cụm

| Mục | Giá trị |
|---|---|
| Trạng thái | Đã chấp nhận (2026-11-15) |
| Ngày | 2026-11-15 |
| Không gian kiến trúc | `core` |
| Issue liên quan | #363 · #364 |
| Người quyết định | Navigator (`AlaVox-lab`) chấp nhận ngày 2026-11-15 để cài ở #364 |

---

## Bối cảnh

Đề thi Phần mềm nguồn mở OLP 2026 yêu cầu nền tảng lõi không giao diện (Tầng 1) cung cấp bắt buộc bốn
dịch vụ: định danh/SSO, **cổng API**, quản trị dữ liệu cấu trúc và phi cấu trúc, động cơ luồng công việc.
Đề cũng nêu nguyên lý bảo mật không tín nhiệm thực thi ngay tại cửa ngõ biên mạng.

Tới `v0.16.0` cụm có ba trong bốn dịch vụ đó nhưng chưa có cổng API: dịch vụ ứng dụng và PostgreSQL mở
cổng thẳng ra máy chủ; giới hạn tốc độ và tiêu đề bảo mật làm trong dịch vụ ứng dụng và cổng người dùng
(`ARCHITECTURE.md` mục 7.4). Thiếu một dịch vụ lõi bắt buộc ảnh hưởng trực tiếp tới tiêu chí *mức độ hoàn
thiện* và *tính nguyên gốc của giải pháp* (mỗi tiêu chí 10 điểm), và ghi chú của tiêu chí PoF 2 đòi sản
phẩm *giải quyết đúng đầu bài*.

Kết quả khảo sát đầy đủ: [`../api-gateway-survey.md`](../api-gateway-survey.md).

---

## Các phương án đã cân nhắc

### Phương án A — Apache APISIX `3.20.0`

| Mục | Nội dung |
|---|---|
| Giấy phép | Apache-2.0 |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có |
| Tài nguyên khi chạy | 57 MiB với một tiến trình làm việc; 525 MiB ở mặc định trên máy 24 nhân, đo thật |
| Khả năng đóng gói bằng container | Ảnh chính thức `apache/apisix:3.20.0-debian`, chế độ `standalone` đọc tệp YAML, không cần etcd |
| Chất lượng tài liệu | Tài liệu plugin đầy đủ, có ví dụ cho Keycloak |
| Mức độ hoạt động của dự án | Dự án cấp cao nhất của Quỹ Apache; bản `3.20.0` ngày 13/11/2026 |
| Độ khó tích hợp | Thấp đến vừa |

**Ưu điểm**

- Plugin `openid-connect` có sẵn kiểm token theo điểm cuối khám phá và bộ khóa công khai của Keycloak —
  đo thật: token thiếu, hết hạn, ký bằng khóa lạ đều nhận 401
- Giới hạn tốc độ đếm chung giữa các tiến trình, chặn đúng ngưỡng
- Cấu hình là một tệp trong kho, nạp lại khi tệp đổi

**Nhược điểm**

- Ảnh lớn (638 MB)
- Phải đặt số tiến trình làm việc, không thì tốn bộ nhớ theo số nhân của máy

### Phương án B — Traefik Proxy `v3.7.19`

| Mục | Nội dung |
|---|---|
| Giấy phép | MIT |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có |
| Tài nguyên khi chạy | 25–28 MiB, đo thật |
| Khả năng đóng gói bằng container | Ảnh chính thức, cấu hình bằng tệp |
| Chất lượng tài liệu | Tốt |
| Mức độ hoạt động của dự án | Phát hành hằng tuần |
| Độ khó tích hợp | Thấp cho định tuyến; **cao cho kiểm token** |

**Ưu điểm**

- Nhẹ nhất, cấu hình gọn

**Nhược điểm**

- Bản nguồn mở không kiểm JWT — đo thật: lời gọi không token vẫn qua. Phải thêm dịch vụ xác thực tự viết
  hoặc plugin bên thứ ba tải lúc chạy

### Phương án C — Kong Gateway `3.9.4` (bản nguồn mở)

| Mục | Nội dung |
|---|---|
| Giấy phép | Apache-2.0 |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có |
| Tài nguyên khi chạy | 121 MiB với một tiến trình; 1,59 GiB ở mặc định trên máy 24 nhân, đo thật |
| Khả năng đóng gói bằng container | Ảnh chính thức, chế độ không cơ sở dữ liệu |
| Chất lượng tài liệu | Tốt |
| Mức độ hoạt động của dự án | Còn phát hành; nhiều tính năng định danh nằm ở bản thương mại |
| Độ khó tích hợp | Vừa |

**Ưu điểm**

- Kiểm JWT bằng plugin có sẵn

**Nhược điểm**

- Khóa công khai phải chép tay vào cấu hình; Keycloak xoay khóa thì hỏng cho tới khi sửa tệp
- Bộ đếm giới hạn tốc độ cục bộ tính riêng từng tiến trình — đo thật: 400 lời gọi qua ngưỡng 300 không
  bị chặn ở mặc định

---

## Quyết định

Dùng Apache APISIX `3.20.0`, chạy chế độ `standalone` với một tiến trình làm việc, làm cửa
vào duy nhất cho mọi lời gọi API từ ngoài cụm.

---

## Lý do

Tiêu chí quyết định là **kiểm token của Keycloak ngay tại biên bằng tính năng có sẵn**. Chỉ APISIX làm
được mà không thêm thành phần tự viết (Traefik) và không buộc chép khóa tay (Kong). Cả ba đều đạt về
giấy phép, nên không ứng viên nào bị loại vì giấy phép. APISIX cũng là ví dụ được nêu trong bảng công
nghệ tham chiếu của đề thi, nên giám khảo quen với nó.

Không chọn tự viết lớp biên trong dịch vụ ứng dụng — như hiện có ở mục 7.4 của `ARCHITECTURE.md` — làm
câu trả lời cho đề: đề gọi tên cổng API là một dịch vụ của lõi, và tiêu chí PoF 5 trừ điểm khi không dùng
thành phần sẵn có.

---

## Cách tích hợp

Dịch vụ độc lập trong Docker Compose, ảnh chính thức ghim mã băm, không sửa, không dựng lại. Cấu hình
tuyến và plugin nằm trong `infra/`.

- Cổng API là thành phần duy nhất mở cổng API ra máy chủ. Dịch vụ ứng dụng và PostgreSQL chỉ nghe trong
  mạng Compose ở cấu hình mặc định
- Cổng kiểm chữ ký, nơi phát và hạn dùng của token. **Dịch vụ ứng dụng vẫn kiểm lại** đủ bốn thứ kể cả
  người nhận (`aud`) như hiện nay: phòng thủ hai lớp, và phân quyền theo vai trò vẫn là việc của dịch vụ
- Giới hạn tốc độ chung đặt tại cổng; bộ đếm trong PostgreSQL của dịch vụ ứng dụng (mục 7.4) giữ cho các
  thao tác cần đếm theo người dùng
- Trang đăng nhập Keycloak, Superset và kho tri thức là giao diện của nền tảng, không phải API của lõi;
  có đưa chúng ra sau cổng hay không quyết ở #364

---

## Hệ quả

**Điều gì trở nên dễ hơn**

- Trả lời trực tiếp yêu cầu "cổng API" của đề; có một chỗ duy nhất để xem và đổi chính sách biên
- Thêm ứng dụng thứ hai dùng lõi chỉ cần thêm tuyến, không đụng dịch vụ ứng dụng

**Điều gì trở nên khó hơn**

- Thêm một dịch vụ vào cụm mặc định (khoảng 57 MiB) và một chặng mạng cho mỗi lời gọi
- Cổng phụ thuộc Keycloak lúc tải khóa: thứ tự khởi động và hành vi khi Keycloak chưa sẵn sàng phải kiểm
- Kiểm thử và CI đang gọi thẳng cổng 8000 phải đổi sang đi qua cổng API

**Việc phải làm tiếp sau quyết định này**

- [x] Navigator chấp nhận, đổi trạng thái bản ghi (15/11/2026)
- [x] Cập nhật `docs/ARCHITECTURE.md` mục 3 và mục 7.4
- [x] Cập nhật `docs/dependencies.md` và `NOTICE`
- [x] Bổ sung vào `docker-compose.yml` (#364)

---

## Ghi chú

- Số đo lấy ngày 15/11/2026 trên cụm thử ngoài kho mã (`thu363`), máy 24 nhân, Docker 29.7.2; cách đo ở
  mục 3 của bản khảo sát
- Ảnh đã thử: `apache/apisix:3.20.0-debian@sha256:013de62a9dfba7d8e6006b3e85b524c28c9f1c3549fca3b91d5b258b0b9e759a`
- Chưa thử với Keycloak thật của cụm — chỉ với bộ khóa giả lập cùng định dạng
- Xem lại quyết định nếu: APISIX đổi giấy phép; plugin `openid-connect` không chạy được ở chế độ
  `standalone` với Keycloak `26.7.3`; hoặc giảng viên muốn giữ cụm mặc định không thêm dịch vụ
