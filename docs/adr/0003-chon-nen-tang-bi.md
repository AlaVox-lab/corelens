# ADR-0003: Nền tảng kinh doanh thông minh cho không gian D

| Mục | Giá trị |
|---|---|
| Trạng thái | Đã chấp nhận |
| Ngày | 2026-09-06 |
| Không gian kiến trúc | `D` |
| Issue liên quan | #21 |
| Người quyết định | Navigator (`AlaVox-lab`), theo định hướng đã thống nhất với giảng viên hướng dẫn |

---

## Bối cảnh

Không gian `D` cần một nền tảng trực quan hóa dữ liệu từ nhật ký sự kiện: tồn đọng theo bộ
phận, thời gian xử lý trung vị, tỷ lệ vi phạm SLA, phân bố loại yêu cầu.

Đây là thành phần **lắp ghép**. Đề bài nêu rõ yêu cầu dùng nền tảng BI nguồn mở thay vì tự
vẽ biểu đồ.

### Kiến trúc lai — hai loại bảng điều khiển

Quyết định này chỉ áp cho **bảng điều khiển phân tích** (chỉ đọc, trên nhật ký sự kiện).
**Buồng lái vận hành** (duyệt, phân công, leo thang — có tương tác và ghi dữ liệu) thuộc
nhóm tự viết theo `CLAUDE.md` mục 3.2 và sẽ do cổng Next.js đảm nhiệm.

Hệ quả quan trọng: bảng điều khiển phân tích phải **nhúng được vào cổng** và hợp nhất đăng
nhập qua Keycloak ([ADR-0001](0001-chon-nen-tang-sso.md)), để người dùng không phải đăng
nhập hai lần. Vì vậy **khả năng nhúng là tiêu chí bắt buộc**, không phải tính năng phụ.

### Ràng buộc

1. **Giấy phép** — bảng chấm PoF mục 2 (10 điểm). Copyleft mạnh vẫn hợp lệ nhưng chỉ được
   dùng như dịch vụ độc lập.
2. **Nhúng được** — xuất phát từ kiến trúc lai ở trên.
3. **Dựng bằng một lệnh trên máy sạch** — bảng chấm PoF mục 4 (10 điểm). Tổng bộ nhớ toàn
   hệ thống phải nằm trong khả năng máy chấm.
4. **Nối được PostgreSQL** — nguồn sự thật duy nhất của hệ thống.

Quá trình khảo sát và số liệu đo ghi trong [`../bi-platform-survey.md`](../bi-platform-survey.md).

---

## Các phương án đã cân nhắc

### Phương án A — Apache Superset

| Mục | Nội dung |
|---|---|
| Giấy phép | Apache-2.0 — xác minh trong ảnh chứa tại `/app/superset-core/LICENSE.txt` |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có, không điều kiện |
| Nhúng bảng điều khiển | **Có, trong bản nguồn mở** — điểm cuối guest token và embedded dashboard đều tồn tại |
| Mã khóa tính năng trả phí | **Không có** |
| Tài nguyên khi chạy | 190,1 MiB, đo thật |
| Kết nối PostgreSQL | Được, **nhưng ảnh không kèm trình điều khiển** |
| Chất lượng tài liệu | Tốt |
| Mức độ hoạt động | Rất tích cực, ~74.700 sao |

**Ưu điểm**

- Giấy phép Apache-2.0 dễ dãi, không ràng buộc copyleft
- Nhúng mở hoàn toàn: không có tính năng nào bị khóa sau giấy phép trả phí
- Rất nhẹ so với đối thủ — chênh hơn mười lần
- Đã kiểm chứng đầu cuối: đọc nhật ký sự kiện và tính đúng chỉ số vi phạm SLA

**Nhược điểm**

- Ảnh chứa thiếu trình điều khiển PostgreSQL, phải bổ sung bằng ảnh dẫn xuất hoặc một bước
  trong quy trình dựng
- Khó dùng hơn Metabase với người mới
- Con số 190 MiB đo ở chế độ máy chủ phát triển một tiến trình; bản sản phẩm sẽ tốn hơn

### Phương án B — Metabase

| Mục | Nội dung |
|---|---|
| Giấy phép | AGPL-3.0 cho ảnh nguồn mở — xác minh trong jar, phần thương mại nằm ở ảnh riêng |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có, **có điều kiện** — chỉ khi chạy như dịch vụ độc lập |
| Nhúng bảng điều khiển | **Bị khóa** — `embedding`, `embedding_sdk`, `embedding_simple` đều nằm trong nhóm trả phí |
| Tính năng bị khóa | **57 tính năng, 0 được bật** |
| Tài nguyên khi chạy | 1,98 GiB, đo thật |
| Kết nối PostgreSQL | Có sẵn trình điều khiển |
| Chất lượng tài liệu | Rất tốt |
| Mức độ hoạt động | Tích cực, ~49.100 sao |

**Ưu điểm**

- Dễ dùng nhất, người không chuyên vẫn tự tạo được biểu đồ
- Trình điều khiển PostgreSQL có sẵn, cắm vào là chạy
- Tài liệu rất tốt

**Nhược điểm**

- **Nhúng tương tác bị khóa sau giấy phép trả phí** — đúng thứ kiến trúc lai cần. Bản nguồn
  mở chỉ có nhúng tĩnh, không tương tác
- Phân quyền nâng cao và giới hạn dữ liệu theo người dùng cũng bị khóa, ảnh hưởng việc phân
  quyền theo bốn vai trò nghiệp vụ
- Tốn hơn mười lần bộ nhớ so với Superset
- AGPL-3.0 buộc giữ ranh giới dịch vụ độc lập

### Phương án C — Grafana

Không đưa vào so sánh sâu. Grafana mạnh ở dữ liệu chuỗi thời gian và giám sát hạ tầng,
không phù hợp phân tích quan hệ trên nhật ký sự kiện của quy trình nghiệp vụ. Ngoài ra
cũng dùng AGPL nên mang cùng ràng buộc như Metabase mà không bù lại được điểm nào.

---

## Quyết định

Chọn **Apache Superset** phiên bản `6.1.0` làm nền tảng kinh doanh thông minh cho không
gian `D`.

---

## Lý do

**Tiêu chí quyết định là khả năng nhúng.** Kiến trúc lai đòi bảng điều khiển phân tích phải
nhúng được vào cổng và dùng chung phiên đăng nhập Keycloak. Metabase khóa đúng tính năng
này sau giấy phép trả phí: kiểm tra thực tế cho thấy **57 tính năng bị khóa và không một
tính năng nào được bật**, trong đó có cả `embedding`, `advanced_permissions` và `sandboxes`.
Nghĩa là Metabase nguồn mở **không thể thực hiện được kiến trúc đã thiết kế**. Đây không
phải bất tiện, mà là bất khả thi.

Superset thì ngược lại: hai điểm cuối phục vụ nhúng đều có mặt trong bản Apache-2.0, và
trong toàn bộ mã nguồn không tồn tại cơ chế khóa tính năng nào.

**Tiêu chí thứ hai là giấy phép.** Superset dùng Apache-2.0 sạch, không ràng buộc. Metabase
dùng AGPL-3.0 — vẫn hợp lệ theo OSI nhưng buộc phải giữ ranh giới dịch vụ độc lập suốt vòng
đời dự án.

**Tiêu chí thứ ba là bộ nhớ, và khoảng cách lớn ngoài dự đoán.** Superset 190 MiB so với
Metabase 1,98 GiB. Chọn Metabase sẽ đẩy tổng ngân sách hệ thống từ ~1,29 GB lên ~3,08 GB,
trong khi bảng chấm đòi `docker compose up` chạy được trên máy sạch vào ngày chấm.

**Điểm Metabase thắng đã được cân nhắc và chấp nhận đánh đổi.** Nó dễ dùng hơn và có sẵn
trình điều khiển PostgreSQL, trong khi Superset cần thêm một bước cài trình điều khiển. Đây
là chi phí một lần trong quy trình dựng, không phải gánh nặng lâu dài — quá nhỏ so với việc
không nhúng được.

---

## Cách tích hợp

**Chạy như dịch vụ độc lập.** Cổng Next.js nhúng bảng điều khiển qua cơ chế guest token của
Superset; danh tính người dùng đến từ Keycloak, Superset nhận vai trò qua token.

| Thành phần | Vai trò |
|---|---|
| Cổng người dùng (Next.js) | Nhúng bảng điều khiển phân tích; tự xây buồng lái vận hành |
| Dịch vụ ứng dụng (FastAPI) | Cấp guest token cho cổng sau khi kiểm quyền theo vai trò |
| Superset | Truy vấn và vẽ biểu đồ trên nhật ký sự kiện, chỉ đọc |
| PostgreSQL | Nguồn sự thật duy nhất: bảng `event_log` và `cases` |
| Keycloak | Nguồn danh tính, xem [ADR-0001](0001-chon-nen-tang-sso.md) |

### Ràng buộc bắt buộc

1. **Superset chỉ được cấp quyền đọc** trên cơ sở dữ liệu nghiệp vụ. Bảng điều khiển phân
   tích không bao giờ ghi dữ liệu.
2. **Ảnh chứa phải là ảnh dẫn xuất** có sẵn trình điều khiển PostgreSQL, để giữ lời hứa
   dựng bằng một lệnh trên máy sạch.
3. **Chỉ dùng cho bảng điều khiển phân tích.** Mọi thao tác nghiệp vụ nằm ở buồng lái tự
   xây trong cổng.

---

## Hệ quả

**Điều gì trở nên dễ hơn**

- Không phải tự viết thư viện biểu đồ và trình khám phá dữ liệu cho phần phân tích
- Người dùng đăng nhập một lần dùng được cả cổng lẫn bảng điều khiển
- Thêm chỉ số mới là cấu hình trên giao diện Superset, không phải sửa mã và triển khai lại
- Chỉ tăng ~190 MiB vào tổng ngân sách bộ nhớ
- Ranh giới sạch giữa phần lắp ghép và phần tự viết, thuận lợi khi trình bày kiến trúc
  Open-Core trước ban giám khảo

**Điều gì trở nên khó hơn**

- Phải dựng và bảo trì một ảnh chứa dẫn xuất có trình điều khiển PostgreSQL
- Nhóm phải nắm khái niệm dataset, chart và dashboard của Superset
- Cấu hình dựng thử dùng máy chủ phát triển của Flask, **không dùng được cho sản phẩm**;
  bản thật phải chuyển sang máy chủ WSGI
- Thêm một dịch vụ nữa phải khởi động và sao lưu

**Việc phải làm tiếp sau quyết định này**

- [x] Cập nhật `docs/ARCHITECTURE.md` mục 3 *(đã làm trong cùng công việc này)*
- [x] Cập nhật `docs/dependencies.md` *(đã làm trong cùng công việc này)*
- [ ] Dựng ảnh chứa dẫn xuất bổ sung trình điều khiển PostgreSQL
- [ ] Bổ sung Superset vào `infra/docker-compose.yml` khi dựng hạ tầng thật
- [ ] Chuyển từ máy chủ phát triển sang máy chủ WSGI cho bản sản phẩm
- [ ] Nối Superset với Keycloak, cấu hình cơ chế guest token
- [ ] Chuyển bộ sinh dữ liệu ảo thành mã sản phẩm trong `infra/seed/`
- [ ] Tạo tài khoản chỉ đọc riêng cho Superset trên cơ sở dữ liệu nghiệp vụ

---

## Ghi chú

Số liệu bộ nhớ đo trên một máy cụ thể (24 CPU, 8,3 GB RAM cấp cho Docker). Superset đo ở
chế độ máy chủ phát triển một tiến trình nên là mức sàn; Metabase chạy JVM không đặt `-Xmx`
nên lấy dần bộ nhớ theo mức sẵn có, có thể ghìm bằng `JAVA_OPTS`. Dù điều chỉnh cả hai
chiều, khoảng cách vẫn rất lớn.

Grafana không được dựng thử. Nhận định về nó dựa trên tài liệu, không phải số đo.

**Điều kiện khiến quyết định này cần xem lại**:

- Superset đổi sang giấy phép không thuộc danh sách OSI
- Metabase mở khóa tính năng nhúng cho bản nguồn mở
- Nhu cầu chuyển từ bảng điều khiển phân tích sang thao tác nghiệp vụ trên nền tảng BI —
  khi đó phải xem lại ranh giới giữa buồng lái tự xây và phần lắp ghép
