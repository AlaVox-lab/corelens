# Khảo sát nền tảng kinh doanh thông minh (BI) — Không gian D

> **Mục đích**: ghi lại quá trình và kết quả khảo sát nền tảng BI cho không gian `D`, làm
> căn cứ cho bản ghi quyết định
> [`adr/0003-chon-nen-tang-bi.md`](adr/0003-chon-nen-tang-bi.md).
>
> **Issue liên quan**: #21 · **Ngày thực hiện**: 2026-09-06

---

## 1. Câu hỏi cần trả lời

Chọn nền tảng BI nào để xây bảng điều khiển trực quan hóa dữ liệu từ nhật ký sự kiện: tồn
đọng theo bộ phận, thời gian xử lý trung vị, tỷ lệ vi phạm SLA, phân bố loại yêu cầu?

### 1.1. Hai loại bảng điều khiển — kiến trúc lai

Trước khi so sánh nền tảng, cần tách bạch hai thứ hay bị gọi chung là "dashboard":

| Loại | Bản chất | Ai làm |
|---|---|---|
| **Buồng lái vận hành** — duyệt, phân công, leo thang | Tương tác, ghi dữ liệu | **Tự xây** trong cổng Next.js |
| **Bảng điều khiển phân tích** — trên nhật ký sự kiện | Chỉ đọc, khám phá dữ liệu | **Lắp ghép** nền tảng BI |

Khảo sát này chỉ giải quyết vế thứ hai. Vế thứ nhất thuộc nhóm tự viết theo `CLAUDE.md`
mục 3.2 và sẽ có công việc riêng.

Hệ quả kiến trúc: phương án **lai**. Bảng điều khiển phân tích được nhúng vào cổng và hợp
nhất đăng nhập qua Keycloak (xem [ADR-0001](adr/0001-chon-nen-tang-sso.md)), nên **khả năng
nhúng là tiêu chí bắt buộc**, không phải tính năng có thì tốt.

### 1.2. Ràng buộc chi phối

| Ràng buộc | Nguồn | Hệ quả |
|---|---|---|
| Giấy phép được OSI công nhận, tương thích MIT | Bảng chấm PoF mục 2 (10 điểm) | Copyleft mạnh chỉ dùng như dịch vụ độc lập |
| Nhúng được vào cổng người dùng | Kiến trúc lai ở mục 1.1 | Tính năng nhúng phải nằm trong bản nguồn mở, không sau tường trả phí |
| Dựng bằng một lệnh trên máy sạch | Bảng chấm PoF mục 4 (10 điểm) | Tổng bộ nhớ phải nằm trong khả năng máy chấm |
| Nối được PostgreSQL | Nguồn sự thật duy nhất | Phải có trình điều khiển PostgreSQL |

---

## 2. Dữ liệu thử — điều kiện tiên quyết

Không thể so sánh hai nền tảng BI trên cơ sở dữ liệu rỗng: cả hai đều đẹp như nhau khi
không có gì để vẽ. Nên bước đầu tiên là sinh dữ liệu.

### 2.1. Cách sinh

Bộ sinh bám theo [`process-flow.md`](process-flow.md): mười trạng thái, bốn vai trò, các
nhánh phê duyệt, chờ bổ sung, leo thang, hủy và từ chối. Lược đồ đúng như
`ARCHITECTURE.md` mục 6 quy định.

| Bảng | Nội dung |
|---|---|
| `event_log` | `case_id`, `activity`, `timestamp` (UTC), `actor`, `from_state`, `to_state` |
| `cases` | `case_id`, `request_type`, `department`, `sla_hours`, `created_at`, `closed_at`, `final_state` |

**Quy ước đặt tên trong nhật ký**: `from_state` và `to_state` dùng định danh tiếng Anh vì
mã nguồn so sánh với chúng; `activity` dùng nhãn tiếng Việt vì đó là thứ hiện trên sơ đồ
khai phá quy trình cho người đọc. Theo `ARCHITECTURE.md` mục 8.3, và khớp với ví dụ hoạt
động tiếng Việt nêu ở mục 6 của tệp đó.

### 2.2. Quy mô và tính thực tế

| Chỉ số | Giá trị |
|---|---|
| Số hồ sơ | 1.000 |
| Số sự kiện | 5.496 (trung bình 5,5 mỗi hồ sơ) |
| Khoảng thời gian | 180 ngày |
| Trạng thái cuối | 837 đã đóng · 106 đang xử lý · 57 đã hủy |
| Tỷ lệ vi phạm SLA | **19,2 %** |

**Một lỗi đã phát hiện và sửa**: bản sinh đầu tiên cho tỷ lệ vi phạm SLA **80,3 %** vì thời
gian được cộng dồn ngẫu nhiên qua từng bước, khiến tổng luôn vượt ngưỡng. Bảng điều khiển
hiện 80 % vi phạm trông như hệ thống hỏng, và chỉ số đó mất hết biến thiên để so sánh. Bản
sửa quyết định trước mỗi hồ sơ có vi phạm hay không, rồi co giãn toàn bộ chuỗi sự kiện cho
khớp tổng thời gian mục tiêu.

Kết quả sau khi sửa, trung vị nằm dưới ngưỡng ở mọi loại yêu cầu:

| Loại yêu cầu | Trung vị (giờ) | Ngưỡng SLA | Tỷ lệ vi phạm |
|---|---|---|---|
| Đề xuất mua vật tư | 40,9 | 72 | 17,7 % |
| Giấy xác nhận nhân sự | 27,2 | 48 | 14,5 % |
| Cấp quyền phần mềm | 15,9 | 24 | 21,0 % |
| Hỗ trợ khác | 13,8 | 24 | 17,2 % |
| Sự cố thiết bị | 5,2 | 8 | 21,6 % |

Bộ sinh dữ liệu **không đưa vào kho mã** ở công việc này vì đây là công cụ khảo sát. Nhưng
nó nên được nâng thành mã sản phẩm trong `infra/seed/` về sau, vì giai đoạn 3 của lộ trình
yêu cầu *"dữ liệu khởi tạo đủ lớn để bảng điều khiển có ý nghĩa khi trình diễn"*.

---

## 3. Kiểm tra giấy phép — xác minh trong ảnh chứa được phát hành

Giấy phép được kiểm bên trong ảnh chứa thật, vì đó mới là thứ đi kèm sản phẩm.

### 3.1. Apache Superset — Apache-2.0, sạch không điều kiện

| Điểm kiểm | Kết quả |
|---|---|
| Tệp giấy phép trong ảnh | `/app/superset-core/LICENSE.txt` — Apache License 2.0 |
| Mã khóa tính năng trả phí | **Không có** — không tìm thấy `premium_features`, `license_key` hay `enterprise_license` |

### 3.2. Metabase — AGPL-3.0 cho ảnh nguồn mở, đã kiểm chứng

Kho mã Metabase báo `NOASSERTION`, dấu hiệu ban đầu giống n8n nên cần soi kỹ.

`LICENSE.txt` của Metabase phân định: mã ngoài thư mục `enterprise/` theo AGPL, mã bên trong
theo giấy phép thương mại; và **hai bản phát hành tách riêng** — ảnh `metabase/metabase`
theo AGPL, ảnh `metabase/metabase-enterprise` theo giấy phép thương mại.

Kiểm chứng trong ảnh `metabase/metabase:v0.62.19`: tệp jar chứa 71 mục khớp chữ
"enterprise", **nhưng toàn bộ đều nằm trong `metabase/premium_features/defenterprise*`** —
đó là cơ chế điều phối (`defenterprise`, `in-ee?`, `dynamic-ee-oss-fn`, `check-feature`),
tức phần mã AGPL quyết định có bản cài đặt thương mại hay không rồi lùi về hành vi nguồn mở.
**Không phải mã tính năng Enterprise.**

Kết luận: ảnh nguồn mở của Metabase **đúng là AGPL-3.0**, hợp lệ theo OSI. Vì là copyleft
mạnh nên chỉ được dùng như dịch vụ độc lập giao tiếp qua HTTP, không nhúng thư viện.

*So sánh để thấy khác biệt*: n8n ở khảo sát #20 nhét 122 tệp `.ee.` là **bản cài đặt thật**
vào ảnh chính. Metabase tách sạch. Hai tình huống khác hẳn nhau dù cùng bị báo `NOASSERTION`.

---

## 4. Bảng so sánh

| Tiêu chí | Apache Superset | Metabase |
|---|---|---|
| Phiên bản thử | `6.1.0` | `v0.62.19` |
| Giấy phép | **Apache-2.0** | AGPL-3.0 (ảnh nguồn mở) |
| Được OSI công nhận | Có | Có |
| Tương thích với MIT | Có, không điều kiện | Có, **có điều kiện** — chỉ dịch vụ độc lập |
| Kết nối PostgreSQL | Được, **nhưng thiếu trình điều khiển sẵn** | Có sẵn |
| **Nhúng vào cổng** | **Có, trong bản nguồn mở** | **Bị khóa sau giấy phép trả phí** |
| Phân quyền nâng cao | Có | Bị khóa |
| Tài nguyên khi chạy | **190 MiB** | **1,98 GiB** |
| Kích thước ảnh | 301 MB | 709 MB |
| Chất lượng tài liệu | Tốt | Rất tốt |
| Mức độ hoạt động | Rất tích cực, ~74.700 sao | Tích cực, ~49.100 sao |
| Độ khó tích hợp | Trung bình | Thấp |

---

## 5. Kết quả dựng thử

Cả hai nối vào **cùng một** PostgreSQL chứa nhật ký sự kiện ảo, để so sánh trên cùng bộ dữ
liệu. Máy thử: 24 CPU, 8,3 GB RAM cấp cho Docker.

### 5.1. Tài nguyên — chênh lệch hơn mười lần

| Thành phần | RAM đo được |
|---|---|
| Superset | **190,1 MiB** |
| Metabase | **1,98 GiB** |
| PostgreSQL chứa dữ liệu | 24,9 MiB |

**Hai lưu ý để không hiểu sai con số:**

Metabase chạy trên JVM **không đặt `-Xmx`**, nên nó lấy dần bộ nhớ theo mức sẵn có: trong
cùng một phiên đo, mức dùng tăng từ 1,56 GiB lên 1,98 GiB. Có thể ghìm lại bằng `JAVA_OPTS`,
nhưng hành vi mặc định mới là thứ xảy ra khi chạy `docker compose up` trên máy sạch — đúng
tình huống của ngày chấm.

Superset trong lần thử chạy bằng máy chủ phát triển của Flask, một tiến trình. Bản sản phẩm
dùng máy chủ WSGI nhiều tiến trình nên sẽ tốn hơn. Con số 190 MiB là **mức sàn**.

Dù tính cả hai chiều điều chỉnh, khoảng cách vẫn rất lớn.

### 5.2. Khả năng nhúng — tiêu chí quyết định

**Metabase**: điểm cuối `/api/session/properties` cho thấy **57 tính năng bị khóa, 0 tính
năng được bật**. Trong danh sách bị khóa có đúng những thứ kiến trúc lai cần:

| Tính năng bị khóa | Vì sao dự án cần |
|---|---|
| `embedding`, `embedding_sdk`, `embedding_simple` | Nhúng bảng điều khiển vào cổng |
| `advanced_permissions` | Phân quyền theo bốn vai trò nghiệp vụ |
| `sandboxes` | Giới hạn dữ liệu theo người dùng |
| `database_auth_providers` | Hợp nhất đăng nhập với Keycloak |

Metabase nguồn mở vẫn có **nhúng tĩnh** (iframe ký bằng JWT, không tương tác). Nhưng nhúng
tương tác — thứ kiến trúc lai cần — nằm sau tường trả phí.

**Superset**: hai điểm cuối `POST /api/v1/security/guest_token/` và
`POST /api/v1/dashboard/{id}/embedded` đều trả HTTP 400 khi gọi với dữ liệu rỗng, **không
phải 404**, nghĩa là chúng tồn tại trong bản Apache-2.0. Cộng với việc không có bất kỳ mã
khóa tính năng nào, năng lực nhúng của Superset là mở hoàn toàn.

### 5.3. Kết nối PostgreSQL — một chi phí tích hợp chỉ lộ ra khi chạy thử

Lần thêm cơ sở dữ liệu đầu tiên vào Superset **thất bại**. Chẩn đoán cho thấy mạng thông
suốt nhưng ảnh `apache/superset:6.1.0` **không kèm trình điều khiển PostgreSQL**.

Khắc phục: cài `psycopg2-binary` vào môi trường ảo của Superset (`/app/.venv`, dùng `uv` vì
ảnh không có `pip` trong môi trường đó), rồi khởi động lại. Sau đó kết nối thành công.

Hệ quả thực tế: bước tích hợp thật cần **một ảnh chứa dẫn xuất** bổ sung trình điều khiển,
hoặc một bước cài đặt trong quy trình dựng. Đây là chi phí có thật, phải ghi vào hướng dẫn
dựng, và là điểm Metabase thuận hơn vì có sẵn.

**Bổ sung sau khi dựng hạ tầng thật (issue #38)**: chi phí tích hợp còn lớn hơn con số ở
trên. Hai điều nữa lộ ra khi ghép Superset vào cụm:

- **Superset không đọc biến môi trường tuỳ ý.** Đặt `SQLALCHEMY_DATABASE_URI` như một biến
  môi trường bị **bỏ qua âm thầm**, và Superset lặng lẽ quay về SQLite. Dấu hiệu duy nhất
  là một dòng `Context impl SQLiteImpl` lẫn trong nhật ký khởi động. Phải nạp cấu hình từ
  tệp Python trỏ bởi `SUPERSET_CONFIG_PATH`
- **Ảnh gốc không tự khởi tạo.** Nó chỉ chạy máy chủ, không chạy `superset db upgrade` lẫn
  `fab create-admin`. Hậu quả rất dễ bỏ sót: điểm cuối sức khoẻ vẫn trả HTTP 200 và
  container vẫn báo `healthy`, nhưng **không ai đăng nhập được**

Cả hai đều đã xử lý trong `infra/superset/`. Ghi lại ở đây vì chúng làm chi phí tích hợp
Superset cao hơn đánh giá ban đầu — dù kết luận chọn Superset vẫn không đổi, do khả năng
nhúng vẫn là tiêu chí quyết định và Metabase khoá đúng tính năng đó.

### 5.4. Kiểm chứng đầu cuối

Sau khi có trình điều khiển, một truy vấn chỉ số được chạy **qua chính Superset** trên nhật
ký sự kiện, cho kết quả đúng:

| Loại yêu cầu | Số hồ sơ | Tỷ lệ vi phạm SLA |
|---|---|---|
| Sự cố thiết bị | 324 | 21,6 % |
| Cấp quyền phần mềm | 210 | 21,0 % |
| Giấy xác nhận nhân sự | 166 | 14,5 % |
| Đề xuất mua vật tư | 130 | 17,7 % |
| Hỗ trợ khác | 64 | 17,2 % |

Vòng dữ liệu khép kín: nhật ký sự kiện → PostgreSQL → Superset → chỉ số.

---

## 6. Ngân sách bộ nhớ toàn hệ thống

| Thành phần | Bản ghi quyết định | RAM |
|---|---|---|
| Keycloak và PostgreSQL của nó | ADR-0001 | ~1,02 GB |
| SeaweedFS | ADR-0002 | ~0,08 GB |
| **Superset** | **ADR-0003** | **~0,19 GB** |
| **Cộng dồn** | | **~1,29 GB** |

Nếu chọn Metabase, con số này sẽ là **~3,08 GB** — gấp hơn hai lần, chưa kể PostgreSQL
nghiệp vụ, FastAPI và Next.js. Với yêu cầu `docker compose up` chạy được trên máy sạch của
bảng chấm PoF mục 4, đây là khác biệt đáng kể.

Không gian `P` vẫn còn để ngỏ ở issue #20: nếu quyết định lắp Flowable thì cộng thêm
~0,45 GB nữa.

---

## 7. Kết luận

Apache Superset được chọn. Lập luận đầy đủ và hệ quả ghi trong
[`adr/0003-chon-nen-tang-bi.md`](adr/0003-chon-nen-tang-bi.md).

---

## 8. Việc cần rà soát lại trước khi nộp bài

- [ ] Kiểm tra lại giấy phép Superset vẫn là Apache-2.0
- [ ] Kiểm tra phiên bản `6.1.0` còn được hỗ trợ
- [ ] Xác nhận ảnh chứa dẫn xuất đã có trình điều khiển PostgreSQL
- [ ] Đo lại tổng bộ nhớ toàn cụm sau khi có quyết định của #20
- [ ] Chuyển bộ sinh dữ liệu ảo thành mã sản phẩm trong `infra/seed/`
