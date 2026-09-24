# ADR-0005: Ranh giới của máy trạng thái với thao tác không đổi trạng thái

| Mục | Giá trị |
|---|---|
| Trạng thái | **Đề xuất** — chờ giảng viên hướng dẫn |
| Ngày | 2026-09-24 |
| Không gian kiến trúc | `P` — ranh giới máy trạng thái; chạm `D` ở nhật ký sự kiện |
| Issue liên quan | #81 |
| Người quyết định | **Giảng viên hướng dẫn** (chờ); navigator (`AlaVox-lab`) đề xuất và ghi bản ghi |

---

## Bối cảnh

Cổng người gửi và hai buồng lái dựng nút bấm hoàn toàn từ `allowed_transitions` —
[`ARCHITECTURE.md`](../ARCHITECTURE.md) mục 7.2. Không có cạnh thì không có nút. Bốn thao
tác người dùng cần lại không ứng với cạnh nào, vì chúng không đổi trạng thái hồ sơ:

| Thao tác | Ai làm | Đổi gì trên hồ sơ |
|---|---|---|
| Nhắn điều phối viên | Người gửi | Không đổi gì |
| Hỏi tiến độ | Người gửi | Không đổi gì |
| Nhận việc về mình | Người xử lý, khi hồ sơ chưa giao cho ai | Trường quyết định `assignee_id` |
| Sửa nội dung | Người gửi | Tiêu đề, mô tả — không phải trường quyết định |

Ô gõ thông tin bổ sung từng nằm trong danh sách này. #79 đã giải nó bằng ô ghi chú bắt
buộc của cạnh *Bổ sung thông tin*, nên nó không còn thuộc bản ghi này.

Đây không phải nhu cầu tưởng tượng. *Hỏi tiến độ* hiện là một cuộc gọi điện — công việc ẩn
không để lại dấu vết, đúng loại dữ liệu tầng `I` cần để chỉ ra điểm nghẽn thật. *Nhận việc
về mình* đến từ quyết định ngày 23/09 giữ việc giao người là tùy chọn: hồ sơ chưa giao ai
thì bộ lọc "Giao cho tôi" không bắt được, hai người có thể làm trùng, và khi leo thang
không biết hỏi ai.

### Ràng buộc chi phối

1. **Một cửa duy nhất** — mọi thay đổi trên hồ sơ đi qua `perform_transition`, để nhật ký
   sự kiện không bao giờ thủng. `ARCHITECTURE.md` mục 6.1, ADR-0004
2. **Lịch sử trường quyết định nằm trong nhật ký** — cột `event_log.changes` (#100). Một
   trường quyết định đổi mà không có dòng nhật ký là lịch sử thủng
3. **Cấu hình thay vì mã cứng** — `CLAUDE.md` mục 1.2
4. **Đồ thị quy trình phải đọc được** — khai phá quy trình ở tầng `I` dựng sơ đồ từ nhật ký

### Dữ kiện từ mã nguồn hiện tại (kiểm ngày 24/09/2026)

- Bảng `transitions` có hai ràng buộc cố ý, trong
  `infra/postgres/init/02-luoc-do-quy-trinh.sql`: `CHECK (from_state <> to_state)` cấm cạnh
  tự trỏ, và `UNIQUE (rule_set_id, from_state, to_state)` — giữa hai trạng thái chỉ có một
  cạnh mỗi chiều
- Engine, API và giao diện đều nhận diện một cạnh bằng cặp *(trạng thái nguồn, trạng thái
  đích)*: điểm cuối chuyển trạng thái nhận `to_state`, nút bấm khóa theo `to_state`
- Mọi lần chuyển, kể cả tự trỏ nếu có, đặt lại mốc `requests.sla_segment_since`
  (`cap_nhat_dong_ho` trong `backend/app/rules/sla.py`). Mốc đó là gốc đo **ân hạn leo
  thang** của #94
- Ràng buộc `return-to-previous-state` (#79) đọc `from_state` của dòng nhật ký mới nhất để
  biết hồ sơ vào trạng thái chờ từ đâu
- Vai trò "giao việc" (#84) suy từ những cạnh cho đặt `assignee_id`
- Dòng thời gian gắn nhãn "Quay lui" cho mốc nào đưa hồ sơ vào lại trạng thái đã từng vào

---

## Các phương án đã cân nhắc

Không phương án nào thêm phụ thuộc bên ngoài, nên không có mục giấy phép.

### Phương án A — Mọi thao tác là cạnh tự trỏ (hướng 1 của #81)

Mỗi thao tác là một dòng `transitions` có `from_state = to_state`, cho mỗi trạng thái nó
áp dụng.

**Ưu điểm**

- Một cửa cho mọi thứ; mọi thao tác đều có dòng nhật ký

**Nhược điểm**

- **Phải gỡ cả hai ràng buộc lược đồ.** *Đang xử lý* cần ít nhất hai cạnh tự trỏ — hỏi tiến
  độ và nhận việc — nên `UNIQUE` phải đi. Mất nó thì cặp *(nguồn, đích)* không còn chỉ ra
  một cạnh: API phải nhận thêm mã hoạt động, giao diện phải đổi khóa nút. Đổi hợp đồng API
  mà #44, #82, #83 đang dùng
- **Mở một lỗ Poka-yoke.** Hỏi tiến độ thành một lần chuyển, nên đặt lại mốc ân hạn. Người
  gửi hỏi tiến độ trên một hồ sơ đã quá hạn là đẩy lùi lần leo thang thêm một khoảng ân
  hạn; hỏi đều tay thì hồ sơ **không bao giờ leo thang** — ngược hẳn mục đích của việc hỏi
- **Va vào #79.** Một lời nhắn gửi lúc hồ sơ đang *Chờ bổ sung thông tin* sinh dòng nhật ký
  từ trạng thái chờ về chính nó. "Chỗ cũ" thành chính trạng thái chờ, và người gửi mất
  đường trả lời
- Bảng `transitions` phình theo số thao tác nhân số trạng thái; sơ đồ khai phá đầy vòng tự
  lặp; dòng thời gian gắn nhãn "Quay lui" cho từng lời nhắn
- *Sửa nội dung* vẫn không vừa: tiêu đề và mô tả không phải trường quyết định

### Phương án B — Mọi thao tác nằm ngoài máy trạng thái (hướng 2 của #81)

Một bảng lời nhắn riêng, không đi qua `perform_transition`. Nhận việc và sửa nội dung cũng
đi đường riêng.

**Ưu điểm**

- Đồ thị quy trình sạch; engine không đổi

**Nhược điểm**

- **Nhận việc ghi `assignee_id` mà không có dòng nhật ký.** Lịch sử người xử lý mà #100 vừa
  dựng bị thủng, và khai phá quy trình không thấy thời điểm hồ sơ có người nhận. Đây đúng
  loại đường vòng mà #81 cảnh báo — và là tiền lệ cho mọi thao tác sửa trường quyết định
  sau này

### Phương án C — Chia theo câu hỏi "thao tác có đổi hồ sơ không" (đề xuất)

| Thao tác | Đi đường nào |
|---|---|
| Nhắn điều phối viên, hỏi tiến độ | **Bảng lời nhắn riêng.** Chỉ thêm dòng; không bao giờ ghi vào `requests`, không chạm đồng hồ SLA |
| Nhận việc về mình | **Cạnh tự trỏ** `in-progress → in-progress`, đi qua `perform_transition`, vào nhật ký kèm `changes` của `assignee_id` |
| Sửa nội dung | **Không sửa bản gốc.** Người gửi bổ sung bằng lời nhắn |

Ranh giới gói trong một câu:

> Thứ gì đổi hồ sơ — trạng thái hay trường quyết định — đi qua cửa chuyển trạng thái và vào
> nhật ký. Thứ gì không đổi hồ sơ thì vào bảng lời nhắn, và bảng đó không bao giờ được ghi
> vào `requests`.

**Ưu điểm**

- Mọi thay đổi trường quyết định vẫn có dòng nhật ký — một cửa và lịch sử của #100 còn
  nguyên
- Lời nhắn không chạm đồng hồ, nên không lách được ân hạn leo thang
- Chỉ gỡ ràng buộc cấm tự trỏ, **giữ `UNIQUE`**: mỗi trạng thái tối đa một cạnh tự trỏ, cặp
  *(nguồn, đích)* vẫn chỉ ra đúng một cạnh, hợp đồng API và giao diện không đổi
- Sơ đồ khai phá chỉ thêm đúng một hoạt động có nghĩa — lúc hồ sơ có người nhận

**Nhược điểm**

- Mở một đường ghi thứ hai (bảng lời nhắn). Phải khai rõ ranh giới trong
  `ARCHITECTURE.md` để nó không thành cớ cho đường vòng khác
- Cạnh nhận việc cần một **loại ràng buộc mới**: engine tự đặt `assignee_id` bằng chính người
  thao tác, không phải ô chọn. Dùng lại `assign-handler` thì người xử lý thành "vai trò giao
  việc" (#84) và thấy ô chọn cả phòng
- Cạnh nhận việc đặt lại mốc ân hạn. Chấp nhận được: người vừa nhận việc có ân hạn như sau
  phân công lại (#94), và chỉ làm được khi hồ sơ chưa ai giữ — tức một lần, không lặp được
  như hỏi tiến độ ở phương án A

---

## Quyết định

**Đề xuất phương án C**, chờ giảng viên hướng dẫn chấp thuận.

---

## Lý do

Tiêu chí quyết định là **dòng nhật ký có đang kể đúng lịch sử hồ sơ không**. Phương án A
kể quá nhiều — mỗi lời nhắn thành một lần chuyển, và điều đó mở hai lỗi thật: lách ân hạn
leo thang, và làm hỏng luồng bổ sung thông tin vừa làm ở #79. Phương án B kể quá ít — mất
lúc hồ sơ đổi người giữ. Phương án C kể đúng: đổi hồ sơ thì có dòng, không đổi thì không.

*Sửa nội dung* bị loại vì một lý do riêng: văn bản người gửi viết lúc gửi là dữ liệu cho
phân loại tự động ở tầng `I`. Cặp *"văn bản → loại mà điều phối viên chốt"* chỉ đúng khi
văn bản là bản điều phối viên đã đọc. Sửa sau khi phân loại làm lệch cặp đó, và xóa dấu
kiểm toán của những gì người gửi đã thực sự viết.

---

## Hệ quả

**Điều gì trở nên dễ hơn**

- Người gửi có chỗ nhắn và hỏi tiến độ ngay trên hồ sơ, không phải gọi điện
- Tầng `D` xuất được số lần hỏi tiến độ trên từng hồ sơ — chỉ số điểm nghẽn mà hiện không
  đo được
- Hồ sơ chưa giao ai có cách để người xử lý nhận, mà vẫn giữ việc giao người là tùy chọn

**Điều gì trở nên khó hơn**

- Dòng thời gian phải trộn hai nguồn — nhật ký và lời nhắn — theo thời gian, nhưng phân
  biệt rõ bằng hình thức, và số lần đổi trạng thái vẫn chỉ đếm từ nhật ký
- Có hai nơi ghi dữ liệu hồ sơ; ranh giới phải được canh bằng kiểm thử, không chỉ bằng
  tài liệu

**Việc phải làm tiếp nếu phương án C được chấp thuận**

- [ ] Gỡ `CHECK (from_state <> to_state)`, giữ `UNIQUE` — đổi lược đồ khởi tạo, cả nhóm
      `down -v`
- [ ] Bảng lời nhắn do Alembic sở hữu, chỉ thêm như `event_log`; loại lời nhắn và vai trò
      gửi được khai trong dữ liệu
- [ ] Loại ràng buộc tự đặt người xử lý bằng người thao tác, chỉ đi được khi hồ sơ chưa
      giao ai; không biến người xử lý thành vai trò giao việc
- [ ] `return-to-previous-state` bỏ qua dòng nhật ký tự trỏ; phép kiểm đồ thị cấm cạnh tự trỏ
      ở trạng thái chờ
- [ ] Dòng thời gian không gắn nhãn "Quay lui" cho mốc tự trỏ
- [ ] Bổ sung mục ranh giới vào `docs/ARCHITECTURE.md`, cập nhật `docs/process-flow.md`
- [ ] Đổi trạng thái bản ghi này thành *Đã chấp nhận*, ghi người quyết định

---

## Câu hỏi cho giảng viên

1. Chấp thuận ranh giới của phương án C không?
2. Không cho sửa nội dung đã gửi, chỉ cho bổ sung bằng lời nhắn — có được không?
3. *Nhận việc về mình* chỉ làm được khi hồ sơ chưa giao ai. Hồ sơ đã giao người khác thì
   phải nhờ trưởng phòng phân công lại — đúng ý không?

---

## Ghi chú

- Hai hướng gốc được nêu trong thân #81, cùng lời nhắc rằng đây là quyết định kiến trúc cần
  giảng viên và cả nhóm đồng ý. Dữ kiện lược đồ bổ sung ở bình luận ngày 24/09 trên #81
- Nếu giảng viên chọn A hoặc B, bản ghi này được sửa theo lựa chọn đó trước khi chuyển sang
  *Đã chấp nhận* — bản ghi còn ở trạng thái *Đề xuất* thì chưa ban hành
