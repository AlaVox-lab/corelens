# Khảo sát nền tảng tự động hóa luồng công việc — Không gian P

> **Mục đích**: cung cấp dữ liệu để nhóm và giảng viên hướng dẫn quyết định: lắp ghép một
> nền tảng workflow có sẵn, hay tự xây engine máy trạng thái cấu hình được?
>
> **Issue liên quan**: #20 · **Ngày thực hiện**: 2026-09-06
>
> **Tài liệu này cố ý KHÔNG đưa ra kết luận.** Lý do nêu ở mục 1.2.

---

## 1. Câu hỏi cần trả lời

Chọn nền tảng tự động hóa luồng công việc nào để hiện thực máy trạng thái của yêu cầu nội
bộ, hay tự xây engine máy trạng thái cấu hình được?

### 1.1. Vì sao issue này khác ba khảo sát trước

Ba khảo sát kia — định danh tập trung (#19), lưu trữ đối tượng (#24), kinh doanh thông minh
(#21) — đều hỏi *"lắp nền tảng nào vào?"*. Đó là câu hỏi có đáp án đo được.

Issue này hỏi một câu khác về bản chất: *"có lắp gì vào không, hay tự viết?"* Đây là quyết
định về **phạm vi và bản sắc sản phẩm**, không phải so sánh kỹ thuật thuần túy.

`CLAUDE.md` mục 3.2 đã có lập trường: *"engine máy trạng thái cấu hình được"* nằm trong nhóm
**tự viết**. Nếu khảo sát này kết luận ngược lại thì đó là sửa một quyết định kiến trúc gốc.

### 1.2. Vì sao tài liệu này không kết luận

1. **Nó chạm vào điểm sáng tạo của cả dự án.** Vòng phản hồi tự soi quy trình sống nhờ nhật
   ký sự kiện do chính nhóm định nghĩa. Nhận engine ngoài là nhận luôn mô hình sự kiện của họ.
2. **Nó phụ thuộc năng lực và quỹ thời gian của nhóm** — yếu tố không đo được bằng dựng thử.
3. **Đây là quyết định kiến trúc lớn nhất còn lại**, nên ô *Người quyết định* trong bản ghi
   quyết định cần có giảng viên hướng dẫn.

### 1.3. Ràng buộc chi phối

| Ràng buộc | Nguồn | Hệ quả |
|---|---|---|
| Giấy phép được OSI công nhận, tương thích MIT | Bảng chấm PoF mục 2 (10 điểm) | Loại thẳng ứng viên không thuộc OSI |
| Trạng thái và quy tắc chuyển nằm trong **dữ liệu** | `ARCHITECTURE.md` mục 5 | Engine phải cho định nghĩa quy trình bằng dữ liệu, đổi được lúc chạy |
| Sinh nhật ký sự kiện ở **mọi** lần chuyển trạng thái | `ARCHITECTURE.md` mục 6 | Lược đồ tối thiểu: `case_id`, `activity`, `timestamp` (UTC), `actor`, `from_state`, `to_state` |
| Dựng bằng một lệnh trên máy sạch | Bảng chấm PoF mục 4 (10 điểm) | Ảnh chứa chính thức, tổng bộ nhớ nằm trong khả năng máy chấm |

---

## 2. Kiểm tra giấy phép — xác minh trong chính ảnh chứa được phát hành

Khảo sát này không dừng ở việc đọc siêu dữ liệu trên kho mã. Với hai ứng viên đáng ngờ, giấy
phép được kiểm **bên trong ảnh chứa thật**, vì đó mới là thứ sẽ được phát hành kèm sản phẩm.

### 2.1. n8n — loại

| Điểm kiểm | Kết quả |
|---|---|
| Khai báo trong `package.json` của gói `n8n@2.38.3` | `"license": "LicenseRef-n8n-sustainable-use"` |
| Ý nghĩa | Theo quy ước SPDX, tiền tố `LicenseRef-` dành cho **giấy phép tự định nghĩa, không nằm trong danh sách chuẩn** |
| Tệp giấy phép dạng văn bản trong gói | Không có. Chỉ có `dist/license.js` — mã kiểm tra quyền dùng tính năng trả phí |
| Tệp `.ee.` trong ảnh phát hành | **122 tệp** |

Kết luận: **không thuộc danh sách OSI**. Phát hành sản phẩm kèm n8n đồng nghĩa phát hành lại
122 tệp thuộc điều khoản thương mại riêng.

### 2.2. Camunda 8 — loại

| Điểm kiểm | Kết quả |
|---|---|
| Tệp giấy phép trong ảnh `camunda/camunda:8.9.19` | Có **hai** tệp cùng lúc: `APACHE-2.0.txt` **và** `CAMUNDA-LICENSE-1.0.txt` |
| Phạm vi cho phép của Camunda License 1.0 | Chỉ cho dùng trong môi trường **"Non-Production Environment"**; dùng cho sản phẩm thật phải mua giấy phép thương mại |
| Điều khoản kèm theo | Cấm di chuyển, thay đổi, vô hiệu hóa hoặc lách cơ chế kiểm tra license key |
| Hành vi lúc chạy | Nhật ký khởi động ghi cảnh báo `CamundaLicense — No license detected when one is expected`, yêu cầu cung cấp biến `CAMUNDA_LICENSE_KEY` |

Kết luận: **không thuộc danh sách OSI**. Đây không phải giấy phép "hơi khó chịu" mà là giấy
phép **cấm dùng cho sản phẩm thật** nếu không trả tiền.

**Ghi lại để người sau không đề xuất lại**: n8n có hơn 200.000 sao trên GitHub và là cái tên
dễ nghĩ tới nhất khi nhắc "tự động hóa luồng công việc nguồn mở"; Camunda là tên tuổi lâu đời
nhất trong mảng BPM. Chính vì nổi tiếng nên khả năng bị đề xuất lại rất cao. Cả hai **dùng
được về mặt kỹ thuật nhưng khiến dự án mất điểm về mặt thể lệ**.

*Ghi chú lịch sử*: Camunda 7 từng dùng Apache-2.0 nhưng đã hết vòng đời. Camunda 8 hiện tại
không còn là nguồn mở theo chuẩn OSI.

### 2.3. Ứng viên đạt

| Ứng viên | Giấy phép | Bản phát hành mới nhất | Hoạt động |
|---|---|---|---|
| **Temporal** | `MIT` | `v1.31.2` — 08/07/2026 | Rất tích cực, ~22.900 sao |
| **Flowable** | `Apache-2.0` | `flowable-8.0.0` — 27/02/2026 | Tích cực, ~9.500 sao |
| **Conductor** | `Apache-2.0` | `v3.32.2.rc5` — 02/09/2026 | Tích cực, ~32.200 sao |

*Lưu ý về Conductor*: bản mới nhất là bản ứng viên (`rc5`), và dự án đã chuyển quyền bảo trì
từ Netflix sang cộng đồng `conductor-oss`.

---

## 3. Bảng so sánh

Ô ghi *(đo thật)* là số liệu thu được ở mục 4.

| Tiêu chí | Temporal | Flowable | Conductor | n8n | Camunda 8 | Tự xây |
|---|---|---|---|---|---|---|
| Giấy phép | MIT | Apache-2.0 | Apache-2.0 | `LicenseRef` riêng | Camunda License 1.0 | MIT |
| Được OSI công nhận | Có | Có | Có | **Không** | **Không** | — |
| Dùng được cho sản phẩm thật | Có | Có | Có | Hạn chế | **Không, nếu không trả phí** | Có |
| Định nghĩa quy trình là gì | **Mã nguồn** *(đo thật)* | BPMN 2.0 XML — dữ liệu *(đo thật)* | JSON — dữ liệu | JSON — dữ liệu | BPMN — dữ liệu | Bảng trong CSDL |
| Trạng thái/quy tắc lưu trong dữ liệu | **Không** *(đo thật)* | Có, triển khai lúc chạy *(đo thật)* | Có | Có | Có | Có, theo thiết kế |
| Nhật ký khớp lược đồ dự án | Mô hình riêng | **4/6 trường** *(đo thật)* | Chưa đo | Chưa đo | Chưa đo | Đúng 6/6 |
| RAM đo được | 62 MiB *(chế độ dev)* | **461 MiB** | Chưa đo | **750 MiB** | **802 MiB** *(chưa có Elasticsearch)* | 0 |
| Phụ thuộc thêm | Cụm CSDL khi chạy thật | PostgreSQL | Chưa đo | — | **Cần Elasticsearch** | Không |
| Độ khó tích hợp | Cao — mô hình mới | Trung bình — phải học BPMN | Trung bình | Thấp | Trung bình | Thấp |

Conductor **chưa được dựng thử**; mọi ô của nó là thông tin tài liệu, không phải số đo.

---

## 4. Kết quả dựng thử

Bốn ứng viên được dựng bằng Docker và đo lần lượt để số liệu bộ nhớ không nhiễu lẫn nhau.
Máy thử: 24 CPU, 8.3 GB RAM cấp cho Docker.

### 4.1. Flowable 8.0.0 — ứng viên được kiểm kỹ nhất

Được chọn kiểm sâu vì đây là **đối thủ mạnh nhất của phương án tự xây**: nó định nghĩa quy
trình bằng BPMN 2.0 XML, tức đúng nghĩa là dữ liệu, và là engine dành cho quy trình nghiệp vụ
chứ không phải điều phối hệ phân tán.

Một phần luồng yêu cầu nội bộ được mô hình hóa bằng BPMN: tiếp nhận → cổng điều kiện phát
sinh chi phí → phê duyệt → xử lý → hoàn tất.

| Phép kiểm | Kết quả |
|---|---|
| Triển khai định nghĩa quy trình **lúc chạy** qua REST, không sửa mã, không dựng lại ảnh | Đạt |
| Phân quyền theo vai trò bằng `candidateGroups` | Đạt — nhận đúng `coordinator`, `department-head`, `handler` |
| Rẽ nhánh điều kiện theo biến của hồ sơ | Đạt — đặt `phatSinhChiPhi = true` thì hồ sơ đi qua bước phê duyệt |
| Tự sinh nhật ký hoạt động | Đạt — 11 bản ghi cho một hồ sơ |
| Mốc thời gian theo UTC | Đạt |
| Đánh phiên bản định nghĩa quy trình | Có sẵn |

| Số liệu | Giá trị |
|---|---|
| RAM Flowable | 374.5 MiB |
| RAM PostgreSQL | 86.8 MiB |
| **Tổng cụm** | **461.3 MiB** |
| Thời gian khởi động | 5.2 giây |

**Nhưng lược đồ nhật ký lệch.** Đối chiếu với lược đồ `ARCHITECTURE.md` mục 6 quy định:

| Trường dự án cần | Flowable có tương ứng không |
|---|---|
| `case_id` | Có — `processInstanceId` hoặc `businessKey` |
| `activity` | Có — `activityName` |
| `timestamp` | Có — `startTime`, đã theo UTC |
| `actor` | Có — `assignee` |
| `from_state` | **Không có** |
| `to_state` | **Không có** |

Bốn trên sáu. Hai trường thiếu không phải khiếm khuyết của Flowable mà là hệ quả của mô hình:
BPMN ghi *"hoạt động nào đã chạy"*, không ghi *"đi từ trạng thái nào sang trạng thái nào"*.

Ngoài ra, 11 bản ghi sinh ra cho một hồ sơ chỉ có ba bước nghiệp vụ. Phần dư là bản ghi kỹ
thuật của BPMN: năm bản `sequenceFlow`, một bản `exclusiveGateway`, hai bản sự kiện đầu cuối.
Muốn dùng cho khai phá quy trình thì phải lọc bỏ.

### 4.2. Temporal — định nghĩa quy trình nằm trong mã, đã kiểm chứng

Ban đầu Temporal bị nghi là không hợp vì triết lý *workflow-as-code*. Nghi ngờ này được kiểm
chứng bằng thực nghiệm thay vì chỉ dựa vào tài liệu.

Phép thử: tạo một hồ sơ mang tên quy trình `YeuCauNoiBo` mà Temporal chưa hề biết định nghĩa.

| Quan sát | Kết quả |
|---|---|
| Temporal có nhận lệnh không | **Có** — tạo ra một lần chạy với mã định danh đầy đủ |
| Hồ sơ có chạy được không | **Không** — đứng ở trạng thái `RUNNING` với một tác vụ treo vĩnh viễn |
| Nguyên nhân | Không có Worker nào biết `YeuCauNoiBo` là gì. Định nghĩa nằm trong mã Worker, không nằm trong Temporal |
| Có lệnh nạp định nghĩa dạng dữ liệu không | **Không có** — giao diện dòng lệnh chỉ có `start` và `execute`, không có `deploy`, `register` hay `import` |

**Kết luận đã kiểm chứng**: Temporal không lưu định nghĩa quy trình. Nó điều phối việc thực
thi, còn quy trình là mã nguồn do nhóm viết và biên dịch. Điều này **ngược thẳng** với ràng
buộc "trạng thái và quy tắc chuyển nằm trong dữ liệu" của `ARCHITECTURE.md` mục 5. Muốn đổi
một trạng thái khi đề thi công bố, nhóm phải sửa mã và triển khai lại Worker.

| Số liệu | Giá trị |
|---|---|
| Phiên bản | CLI 1.8.3, Server 1.31.2 |
| RAM | 62.1 MiB |

**Cảnh báo về con số 62 MiB**: đây là chế độ `server start-dev`, lưu trữ trong bộ nhớ, một
tiến trình. Bản chạy thật cần cụm riêng với cơ sở dữ liệu bền vững, nên con số này là **mức
sàn**, không phải chi phí thực tế.

### 4.3. n8n — dựng thử để xác nhận kết luận loại

Dựng thử không nhằm cân nhắc lại n8n, vì giấy phép đã loại nó. Mục đích là biến kết luận từ
"đọc siêu dữ liệu thấy vậy" thành "đã chạy và kiểm trong ảnh phát hành".

| Số liệu | Giá trị |
|---|---|
| Phiên bản | 2.38.3 |
| RAM | **749.6 MiB** |
| Giấy phép khai báo trong gói | `LicenseRef-n8n-sustainable-use` |
| Số tệp `.ee.` trong ảnh | 122 |

### 4.4. Camunda 8 — dựng thử để xác nhận kết luận loại

| Số liệu | Giá trị |
|---|---|
| Phiên bản | 8.9.19 |
| RAM | **801.6 MiB** — và đây là **chưa kèm Elasticsearch** mà tài liệu đi kèm nói là cần |
| Hành vi lúc chạy | Ghi cảnh báo thiếu license key, yêu cầu biến `CAMUNDA_LICENSE_KEY` |

Chạy được ở chế độ cấu hình nhẹ, nhưng cả giấy phép lẫn tài nguyên đều là lý do loại.

### 4.5. Conductor — không dựng thử

Không đầu tư dựng thử vì ảnh chứa nặng nhất trong nhóm sạch giấy phép (415 MB), bản phát hành
mới nhất còn là bản ứng viên, và về mô hình nó không khác Flowable đủ nhiều để thay đổi kết
luận. Nếu quyết định nghiêng về lắp ghép thì nên dựng thử Conductor trước khi chốt.

---

## 5. Đối chiếu sòng phẳng: lắp ghép và tự xây

### 5.1. Lắp ghép engine mang lại gì

Không nhỏ, không nên coi nhẹ:

- **Thực thi bền bỉ** — hồ sơ không mất trạng thái khi dịch vụ khởi động lại
- **Bộ đếm thời gian sẵn có** — phục vụ theo dõi SLA và tự leo thang, thứ nhóm sẽ phải tự
  viết nếu không dùng engine
- **Đánh phiên bản quy trình** — hồ sơ cũ chạy theo định nghĩa cũ, hồ sơ mới theo định nghĩa mới
- **Truy vấn tác vụ theo vai trò** có sẵn
- **Uy tín khi trình bày** — cho thấy nhóm biết dùng nền tảng công nghiệp

### 5.2. Cái giá phải trả

- **Thêm 461 MiB** nếu chọn Flowable, cộng một dịch vụ JVM phải vận hành và sao lưu
- **Một mô hình tư duy mới phải học** — BPMN không nắm được trong một buổi
- **Vẫn phải tự viết lớp nhật ký sự kiện** vì lược đồ lệch (mục 4.1)
- **Mất quyền kiểm soát hình dạng nhật ký** — thứ nuôi cả không gian `D` lẫn `I`
- Đề bài xếp engine máy trạng thái vào nhóm **tự viết**, nên lắp ghép ở đây **không cộng
  điểm** cho tiêu chí kiến trúc lắp ghép như khi lắp SSO hay BI

### 5.3. Lệch mô hình — phát hiện quan trọng nhất

**Thiết kế của dự án là một máy trạng thái.** `docs/process-flow.md` mô tả mười trạng thái,
mỗi lần chuyển là một cạnh có điều kiện về vai trò. Một số trạng thái đi vào từ nhiều phía —
"Chờ bổ sung thông tin" vào được từ cả điều phối viên lẫn người xử lý. Câu hỏi trung tâm là
*"hồ sơ đang ở trạng thái nào, và từ đây được đi đâu?"*

**Mô hình của BPMN là một luồng hoạt động.** Câu hỏi trung tâm là *"tác vụ nào đang mở?"*
Trạng thái không phải khái niệm hạng nhất; nó suy ra từ vị trí hiện tại trong luồng.

**Mô hình của Temporal còn xa hơn nữa**: quy trình là một hàm trong mã nguồn, được thực thi
bền bỉ. Không có khái niệm "định nghĩa quy trình dưới dạng dữ liệu" nào cả.

Hai mô hình đầu diễn đạt lẫn nhau được, nhưng đó là một **phép dịch**, không phải phép khớp.
Hệ quả thực tế: nhật ký lấy ra mang hình dạng của BPMN, trong khi khai phá quy trình của dự
án cần hình dạng chuyển trạng thái. Nghĩa là **dù dùng Flowable, nhóm vẫn phải tự viết lớp
sinh nhật ký sự kiện** — hoặc hậu xử lý lịch sử của Flowable về lược đồ của mình, hoặc phát
sinh nhật ký riêng song song.

### 5.4. Ngân sách bộ nhớ

Theo dõi tích lũy, vì bảng chấm PoF mục 4 đòi hệ thống dựng được trên máy sạch ngày chấm:

| Thành phần | Bản ghi quyết định | RAM |
|---|---|---|
| Keycloak và PostgreSQL của nó | ADR-0001 | ~1.02 GB |
| SeaweedFS | ADR-0002 | ~0.08 GB |
| **Đang dùng** | | **~1.10 GB** |
| Nếu thêm Flowable | *chưa quyết* | +0.45 GB → **~1.55 GB** |
| Nền tảng BI của #21 | *chưa khảo sát* | chưa rõ, dự kiến đáng kể |

Chưa kể PostgreSQL nghiệp vụ, FastAPI và Next.js.

---

## 6. Câu hỏi để nhóm và giảng viên quyết

Khảo sát dừng ở đây. Bốn câu hỏi cần người quyết định trả lời:

1. **Bộ đếm thời gian và thực thi bền bỉ có đáng đổi lấy 461 MiB cùng một mô hình tư duy mới
   không?** Đây là thứ có giá trị thật mà engine mang lại.
2. **Việc vẫn phải tự viết lớp nhật ký sự kiện dù đã lắp engine có làm mất phần lớn lợi ích
   không?** Nếu phần khó nhất vẫn phải tự làm, engine còn tiết kiệm được bao nhiêu?
3. **Nếu nghiêng về lắp ghép, có nên dựng thử Conductor trước khi chốt không?** Đây là ứng
   viên sạch giấy phép duy nhất chưa được đo.
4. **Có nên giữ nguyên lập trường của `CLAUDE.md` mục 3.2 — engine máy trạng thái thuộc nhóm
   tự viết — hay khảo sát này đủ căn cứ để sửa lại?**

Sau khi có quyết định, ghi thành `docs/adr/0004-...` theo mẫu `0000`, với ô *Người quyết định*
có tên giảng viên hướng dẫn.

---

## 7. Việc còn lại của issue #20

- [x] Liệt kê ứng viên, kèm phương án tự xây làm mốc
- [x] Kiểm tra giấy phép OSI — loại được n8n và Camunda 8, xác minh trong ảnh chứa phát hành
- [x] Kiểm tra tương thích MIT
- [x] Đánh giá khả năng lưu trạng thái và quy tắc chuyển trong dữ liệu
- [x] Đánh giá khả năng sinh nhật ký sự kiện ở mỗi lần chuyển trạng thái
- [x] So sánh theo bảng tiêu chí
- [x] Dựng thử — bốn ứng viên: Flowable, Temporal, n8n, Camunda 8
- [x] Viết kết quả vào `docs/`
- [ ] **Ghi bản ghi quyết định** — chờ quyết định của nhóm và giảng viên
