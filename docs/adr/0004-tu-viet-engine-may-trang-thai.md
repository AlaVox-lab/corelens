# ADR-0004: Tự viết engine máy trạng thái cho không gian P

| Mục | Giá trị |
|---|---|
| Trạng thái | Đã chấp nhận |
| Ngày | 2026-09-07 |
| Không gian kiến trúc | `P` |
| Issue liên quan | #20 |
| Người quyết định | **Giảng viên hướng dẫn**; navigator (`AlaVox-lab`) thực hiện khảo sát và ghi bản ghi |

---

## Bối cảnh

Không gian `P` cần một máy trạng thái điều khiển vòng đời của yêu cầu nội bộ: mười trạng
thái, các nhánh phê duyệt, chờ bổ sung thông tin, leo thang khi quá hạn SLA, và ràng buộc
Poka-yoke. Thiết kế đầy đủ nằm ở [`../process-flow.md`](../process-flow.md).

Câu hỏi ban đầu của issue #20 là: lắp ghép một nền tảng workflow có sẵn, hay tự xây engine
máy trạng thái cấu hình được?

`CLAUDE.md` mục 3.2 đã xếp *"engine máy trạng thái cấu hình được"* vào nhóm **tự viết**.
Khảo sát được thực hiện để kiểm chứng lập trường đó bằng dữ liệu thay vì mặc định chấp nhận,
vì nếu có một nền tảng thực sự phù hợp thì việc lắp ghép sẽ tiết kiệm nhiều tuần công.

Quá trình khảo sát, số liệu dựng thử bốn ứng viên và phân tích đầy đủ nằm ở
[`../workflow-engine-survey.md`](../workflow-engine-survey.md).

### Ràng buộc chi phối

1. **Trạng thái và quy tắc chuyển phải nằm trong dữ liệu** — `ARCHITECTURE.md` mục 5. Đề
   thi chính thức chỉ công bố tháng 11/2026 và có thể quy định bộ trạng thái khác.
2. **Mọi lần chuyển trạng thái phải sinh nhật ký sự kiện** với lược đồ sáu trường —
   `ARCHITECTURE.md` mục 6. Đây là nguồn dữ liệu cho khai phá quy trình ở không gian `I`.
3. **Giấy phép được OSI công nhận** — bảng chấm PoF mục 2 (10 điểm).
4. **Quỹ thời gian và năng lực nhóm** — ba sinh viên, còn khoảng ba tháng, phải làm cả bốn
   không gian.

---

## Các phương án đã cân nhắc

### Bị loại ở bước sàng lọc giấy phép

Hai ứng viên bị loại trước khi bàn tới tính năng. Giấy phép được kiểm **bên trong ảnh chứa
được phát hành**, vì đó mới là thứ đi kèm sản phẩm.

| Ứng viên | Kết quả kiểm | Kết luận |
|---|---|---|
| **n8n** `2.38.3` | Gói khai báo `LicenseRef-n8n-sustainable-use`; ảnh phát hành mang **122 tệp `.ee.`** là bản cài đặt thương mại | **Không thuộc OSI.** Dùng sẽ mất điểm cấp phép |
| **Camunda 8** `8.9.19` | Ảnh mang hai tệp giấy phép; `CAMUNDA-LICENSE-1.0.txt` chỉ cho dùng ở môi trường phi sản xuất, ứng dụng tự đòi `CAMUNDA_LICENSE_KEY` lúc chạy | **Không thuộc OSI.** Cấm dùng cho sản phẩm thật nếu không trả phí |

**Ghi rõ để người sau không đề xuất lại**: n8n có hơn 200.000 sao và là cái tên dễ nghĩ tới
nhất khi nhắc tự động hóa luồng công việc nguồn mở; Camunda là tên tuổi lâu đời nhất mảng
BPM. Chính vì nổi tiếng nên khả năng bị đề xuất lại rất cao.

### Phương án A — Tự viết engine máy trạng thái

| Mục | Nội dung |
|---|---|
| Giấy phép | MIT — là mã của chính dự án |
| Trạng thái và quy tắc lưu trong dữ liệu | Có, theo thiết kế: bảng trong PostgreSQL |
| Nhật ký sự kiện | **Đúng lược đồ sáu trường**, do nhóm tự định nghĩa |
| Tài nguyên khi chạy | Không thêm dịch vụ nào |
| Độ khó tích hợp | Thấp — cùng ngôn ngữ, cùng cơ sở dữ liệu với phần còn lại |
| Chi phí bảo trì | Bảo trì mã của mình |

**Ưu điểm**

- Toàn quyền kiểm soát lược đồ nhật ký sự kiện — thứ nuôi cả không gian `D` lẫn `I`
- Không thêm dịch vụ, không thêm bộ nhớ vào tổng ngân sách
- Không phải học mô hình tư duy mới, giảm rủi ro cho nhóm có quỹ thời gian hạn chế
- Là phần **tự viết** mà đề bài mong đợi, đóng góp trực tiếp vào tiêu chí *tính nguyên gốc
  của kiến trúc lắp ghép*

**Nhược điểm**

- Phải tự làm ba việc mà một engine có sẵn sẽ cho không: **thực thi bền bỉ**, **bộ đếm thời
  gian cho SLA**, **đánh phiên bản quy trình**
- Chất lượng phụ thuộc hoàn toàn vào nhóm; lỗi trong engine là lỗi của mình

### Phương án B — Flowable `8.0.0`

Ứng viên lắp ghép mạnh nhất, được dựng thử kỹ nhất.

| Mục | Nội dung |
|---|---|
| Giấy phép | Apache-2.0 — sạch |
| Trạng thái và quy tắc lưu trong dữ liệu | **Có** — BPMN 2.0 XML, triển khai được lúc chạy, đã kiểm chứng |
| Nhật ký sự kiện | **Chỉ khớp 4 trên 6 trường**; thiếu `from_state` và `to_state` |
| Tài nguyên khi chạy | 461,3 MiB (Flowable 374,5 + PostgreSQL 86,8), đo thật |
| Cho sẵn | Thực thi bền bỉ, bộ đếm thời gian, đánh phiên bản quy trình |
| Độ khó tích hợp | Trung bình — phải học BPMN |

**Ưu điểm**

- Cho sẵn đúng ba thứ mà phương án tự viết phải tự làm
- Quy trình định nghĩa bằng dữ liệu, đáp ứng ràng buộc quan trọng nhất
- Phân quyền theo vai trò qua `candidateGroups`, ánh xạ được bốn vai trò nghiệp vụ

**Nhược điểm**

- **Nhật ký sự kiện lệch lược đồ.** BPMN ghi *"hoạt động nào đã chạy"*, không ghi *"đi từ
  trạng thái nào sang trạng thái nào"*. Nhóm **vẫn phải tự viết lớp sinh nhật ký sự kiện**
- Sinh 11 bản ghi cho một hồ sơ chỉ có ba bước nghiệp vụ; phần dư là bản ghi kỹ thuật của
  BPMN, phải lọc bỏ trước khi khai phá quy trình
- **Lệch mô hình**: thiết kế của dự án là máy trạng thái, BPMN là luồng hoạt động. Diễn đạt
  lẫn nhau được nhưng đó là phép dịch, không phải phép khớp
- Thêm 461 MiB và một dịch vụ JVM phải vận hành

### Phương án C — Temporal `1.31.2`

| Mục | Nội dung |
|---|---|
| Giấy phép | MIT — sạch |
| Trạng thái và quy tắc lưu trong dữ liệu | **Không** — quy trình là mã nguồn |
| Tài nguyên khi chạy | 62,1 MiB ở chế độ dev; bản thật cần cụm riêng |

**Bị loại bằng thực nghiệm, không bằng suy luận từ tài liệu.** Phép thử: tạo một hồ sơ mang
tên quy trình mà Temporal chưa biết định nghĩa. Temporal **vẫn nhận** và tạo lần chạy, nhưng
hồ sơ treo vĩnh viễn vì không Worker nào biết quy trình đó là gì. Giao diện dòng lệnh cũng
không có lệnh nạp định nghĩa dạng dữ liệu.

Kết luận: Temporal không lưu định nghĩa quy trình, nó chỉ điều phối việc thực thi. Đổi một
trạng thái khi đề thi công bố nghĩa là sửa mã và triển khai lại Worker — ngược thẳng ràng
buộc số 1.

### Phương án D — Conductor

Không dựng thử. Ảnh chứa nặng nhất trong nhóm sạch giấy phép (415 MB), bản phát hành mới
nhất còn là bản ứng viên (`rc5`), và về mô hình không khác Flowable đủ nhiều để thay đổi kết
luận.

---

## Quyết định

**Tự viết engine máy trạng thái cấu hình được.** Không lắp ghép nền tảng workflow nào.

---

## Lý do

Quyết định do giảng viên hướng dẫn đưa ra sau khi xem kết quả khảo sát. Điểm cốt lõi trong
nhận xét của giảng viên là **dời trọng tâm câu hỏi**: vấn đề không phải *"dùng Flowable hay
tự viết"* mà là *"điểm sáng tạo của đề tài nằm ở đâu"*.

**Thứ nhất, engine không phải nơi tạo ra giá trị của đề tài.** Giá trị nằm ở vòng phản hồi
tự soi quy trình — khai phá quy trình thực tế từ nhật ký sự kiện rồi đối chiếu với quy trình
thiết kế. Chọn engine nào không làm phần đó hay hơn hay dở đi. Nhóm nên dồn sức vào khai phá
quy trình thay vì vào việc chọn công cụ.

**Thứ hai, Flowable không giải quyết được vấn đề cốt lõi.** Khảo sát đo được rằng nhật ký của
Flowable chỉ khớp bốn trên sáu trường, thiếu đúng hai trường `from_state` và `to_state` mà
khai phá quy trình cần. Nghĩa là dù lắp Flowable vào, nhóm **vẫn phải tự viết lớp sinh nhật
ký sự kiện**. Phần khó nhất không được giảm đi, trong khi vẫn phải trả giá bằng 461 MiB, một
dịch vụ JVM và một mô hình tư duy mới.

**Thứ ba, tự viết cho toàn quyền kiểm soát dữ liệu.** Nhóm quyết định lưu gì và xử lý thế
nào, thay vì nhận mô hình sự kiện của bên khác rồi hậu xử lý về lược đồ của mình.

**Thứ tư, rủi ro thấp hơn.** Áp dụng một khung làm việc mà nhóm chưa vững làm tăng khả năng
mắc lỗi, trong khi quỹ thời gian còn khoảng ba tháng cho cả bốn không gian. Engine máy trạng
thái cho bài toán này không quá khó — nó nhận sự kiện từ người dùng chứ không phải điều phối
tiến trình dài hạn giữa nhiều dịch vụ.

**Điều nhóm chấp nhận đánh đổi**: chọn tự viết đồng nghĩa nhận trách nhiệm tự làm **thực thi
bền bỉ**, **bộ đếm thời gian cho SLA** và **đánh phiên bản quy trình** — ba thứ Flowable cho
sẵn. Xem mục Hệ quả để biết vì sao chi phí này nhỏ hơn vẻ ngoài.

---

## Thiết kế

Đây không phải quyết định tích hợp nền tảng ngoài, nên mục này mô tả hướng thiết kế thay cho
ranh giới tích hợp.

### Trạng thái và quy tắc chuyển nằm trong bảng dữ liệu

| Bảng | Vai trò |
|---|---|
| `states` | Danh sách trạng thái: mã định danh, nhãn hiển thị, có phải trạng thái kết thúc không |
| `transitions` | Các cạnh hợp lệ: `from_state`, `to_state`, tên hoạt động, vai trò được phép thực hiện, điều kiện kèm theo |

Đổi quy trình khi đề thi công bố là **sửa dữ liệu khởi tạo**, không sửa mã. Đây là hiện thực
cụ thể của khuôn mẫu ở `ARCHITECTURE.md` mục 5.

**Kiểm tra nhanh**: nếu một chuỗi như `"Đang xử lý"` xuất hiện trong câu lệnh `if` của mã
nguồn, đó là vi phạm. Trạng thái phải tra từ bảng.

### Một cửa duy nhất cho mọi lần chuyển trạng thái

Mọi thao tác đổi trạng thái đi qua **đúng một điểm** trong mã. Điểm đó lần lượt:

1. Tra bảng `transitions` xem cạnh `from_state → to_state` có hợp lệ không
2. Kiểm vai trò người thực hiện có nằm trong danh sách được phép không
3. Chạy các ràng buộc Poka-yoke áp cho cạnh đó
4. **Ghi một bản ghi vào `event_log`** với đủ sáu trường, mốc thời gian theo UTC
5. Cập nhật trạng thái của hồ sơ

Không tồn tại đường nào khác để đổi trạng thái. Đây là điều kiện bảo đảm nhật ký sự kiện
**không bao giờ thiếu bản ghi** — mà một nhật ký thiếu thì kết quả khai phá quy trình sai
lệch, và toàn bộ điểm sáng tạo của đề tài mất giá trị.

### Ba việc phải tự làm và cách tiếp cận

| Việc | Cách làm | Vì sao nhẹ hơn vẻ ngoài |
|---|---|---|
| **Thực thi bền bỉ** | Trạng thái hồ sơ lưu trong PostgreSQL | Quy trình của ta **do người đẩy**, không phải tiến trình chạy dài hạn giữa nhiều dịch vụ. Hồ sơ nằm yên chờ người thao tác, nên trạng thái trong cơ sở dữ liệu vốn đã bền vững. Đây là lý do bài toán này không cần tới Temporal |
| **Bộ đếm thời gian cho SLA** | Một tác vụ định kỳ quét hồ sơ quá ngưỡng rồi chuyển sang trạng thái leo thang | Ngưỡng SLA nằm trong dữ liệu theo từng loại yêu cầu. Việc leo thang cũng là một lần chuyển trạng thái, nên đi qua đúng một cửa ở trên và tự sinh nhật ký |
| **Đánh phiên bản quy trình** | Ghi phiên bản của bảng quy tắc vào từng hồ sơ lúc tạo | Hồ sơ cũ tiếp tục chạy theo bộ quy tắc cũ, hồ sơ mới theo bộ mới |

---

## Hệ quả

**Điều gì trở nên dễ hơn**

- Nhật ký sự kiện đúng lược đồ ngay từ đầu, không phải hậu xử lý từ mô hình của bên khác
- Không thêm dịch vụ nào vào tệp Compose, giữ nguyên ngân sách bộ nhớ ~1,29 GB
- Nhóm không phải học BPMN, dồn được thời gian vào khai phá quy trình
- Toàn bộ logic nghiệp vụ nằm cùng một ngôn ngữ, cùng một cơ sở dữ liệu với phần còn lại
- Đây là phần **tự viết** để trình bày trước ban giám khảo như đóng góp nguyên gốc của nhóm

**Điều gì trở nên khó hơn**

- Ba việc ở bảng trên là trách nhiệm của nhóm, không ai làm hộ
- Lỗi trong engine là lỗi của nhóm, cần kiểm thử kỹ vì đây là phần lõi
- Phải giữ kỷ luật **một cửa duy nhất**; chỉ cần một chỗ đổi trạng thái đi tắt là nhật ký
  thủng và khai phá quy trình cho kết quả sai
- Không có giao diện quản trị quy trình sẵn như Flowable; muốn xem quy trình phải tự dựng

**Việc phải làm tiếp sau quyết định này**

- [x] Cập nhật `docs/ARCHITECTURE.md` *(đã làm trong cùng công việc này)*
- [x] Cập nhật `docs/dependencies.md` *(đã làm trong cùng công việc này)*
- [ ] Thiết kế bảng `states` và `transitions`, đưa mười trạng thái của `process-flow.md`
      thành dữ liệu khởi tạo
- [ ] Lập ma trận phân quyền: vai trò nào được thực hiện cạnh nào
- [ ] Lập danh sách ràng buộc Poka-yoke theo từng cạnh
- [ ] Hiện thực điểm chuyển trạng thái duy nhất, kèm sinh nhật ký sự kiện
- [ ] Hiện thực tác vụ định kỳ theo dõi SLA và tự leo thang
- [ ] Kiểm thử: một yêu cầu đi trọn vòng qua đủ các nhánh, nhật ký sinh đủ và đúng

---

## Ghi chú

Số liệu tài nguyên trong bản ghi này đo trên một máy cụ thể (24 CPU, 8,3 GB RAM cấp cho
Docker). Conductor không được dựng thử; nhận định về nó dựa trên tài liệu.

**Về ba thứ Flowable cho sẵn**: khảo sát xác nhận Flowable **có** thực thi bền bỉ, bộ đếm
thời gian và đánh phiên bản quy trình. Việc chọn tự viết nghĩa là nhóm chủ động nhận lại ba
trách nhiệm đó, đổi lấy quyền kiểm soát nhật ký sự kiện và việc không phải học một mô hình
mới. Ghi rõ điều này để tránh hiểu nhầm rằng Flowable thiếu chúng.

**Điều kiện khiến quyết định này cần xem lại**:

- Đề thi tháng 11/2026 yêu cầu một năng lực điều phối vượt quá máy trạng thái đơn giản, ví
  dụ giao dịch phân tán giữa nhiều hệ thống ngoài
- Engine tự viết bộc lộ lỗi nghiêm trọng mà nhóm không đủ thời gian sửa trước ngày chấm; khi
  đó Flowable là phương án lùi đã được khảo sát sẵn
