# ROADMAP.md

> **Mục đích**: lộ trình từ nay tới chung kết. Đây là nơi ghi **kế hoạch tương lai**.
>
> Không ghi kế hoạch vào `ARCHITECTURE.md` — tệp đó chỉ mô tả hiện trạng. Không ghi
> tiến độ chi tiết vào đây — tiến độ thuộc `PROJECT_STATE.md`.

---

## Ràng buộc thời gian

| Mốc | Thời gian | Ghi chú |
|---|---|---|
| Công bố chủ đề | Tháng 7/2026 | Đã qua |
| **Công bố đề thi chính thức** | **Tháng 11/2026** | Chỉ trước chung kết một tháng |
| Chấm kho mã nguồn | 07–09/12/2026 | 50 điểm PoF, chấm trên `main` |
| Trình diễn và chung kết | 10/12/2026 | 50 điểm sản phẩm |
| Trao giải | 11/12/2026 | |

**Hệ quả chiến lược**: đề thi ra rất muộn. Mọi thứ xây dựng từ nay tới tháng 10 phải
là **bộ khung tái sử dụng**, không phải sản phẩm cuối. Xem mục 5 và 10 của
`ARCHITECTURE.md`.

---

## Giai đoạn 0 — Dựng nền

**Trạng thái**: Hoàn thành · **Phiên bản**: `v0.1.0`

Mục tiêu: kho mã có bộ quy chuẩn đầy đủ, cả nhóm nắm được quy trình làm việc.

- [x] Kho mã, giấy phép MIT, mô hình nhánh ba tầng
- [x] Bộ tài liệu quy chuẩn: hướng dẫn đóng góp, mẫu issue, mẫu đề nghị hợp nhất
- [x] Hệ thống nhãn theo khung H-P-D-I
- [x] Cấu hình sinh nhật ký thay đổi tự động, đã kiểm chứng
- [x] Chạy trọn ba vòng quy trình để kiểm chứng
- [x] Bản phát hành đầu tiên

---

## Giai đoạn 1 — Khảo sát và thiết kế

**Trạng thái**: Hoàn thành — cả ba khảo sát cuối đã có bản ghi *Đề xuất*, chờ giảng viên duyệt;
còn hai việc lẻ ghi dưới · **Phiên bản**: `v0.2.0`

Mục tiêu: chốt toàn bộ nền tảng Open-Core và thiết kế nghiệp vụ, đủ để bắt đầu viết
mã mà không phải quay lại bàn lại.

### 1.1. Tài liệu nền

- [x] Vẽ sơ đồ luồng nghiệp vụ bằng Mermaid, lưu vào `docs/` — `docs/process-flow.md`
- [x] Cập nhật `README.md`: mô tả đề tài, kiến trúc, phân công, hướng dẫn dựng
- [ ] `CODE_OF_CONDUCT.md`
- [x] Hoàn thiện hệ thống nhãn bằng kịch bản tự động — `scripts/setup-labels.sh`

### 1.2. Khảo sát nền tảng Open-Core

Mỗi khảo sát kết thúc bằng một bản ghi quyết định trong `docs/adr/`, có bảng so sánh
kèm **kiểm tra giấy phép** theo danh sách OSI.

- [x] `[H]` Nền tảng định danh tập trung (SSO) — Keycloak, ADR-0001
- [ ] `[H]` Hệ thống quản trị tri thức nội bộ — khảo sát xong (#46), ADR-0006 đề xuất
      Wiki.js, chờ giảng viên duyệt
- [x] `[P]` Nền tảng tự động hóa luồng công việc — so sánh với phương án tự xây
      máy trạng thái — chọn tự viết, ADR-0004
- [x] `[D]` Nền tảng kinh doanh thông minh nguồn mở — Apache Superset, ADR-0003
- [ ] `[I]` Cơ sở dữ liệu véc-tơ và khung phát triển mô hình ngôn ngữ lớn — khảo sát xong
      (#47), ADR-0008 đề xuất pgvector và llama.cpp, không dùng khung LLM, chờ giảng viên
      duyệt
- [ ] `[I]` Thư viện khai phá quy trình — khảo sát xong (#48), ADR-0007 đề xuất PM4Py
      trong dịch vụ tách riêng, chờ giảng viên duyệt

### 1.3. Thiết kế nghiệp vụ

- [x] Danh sách trạng thái và bảng quy tắc chuyển đổi — `docs/process-flow.md`
- [x] Ma trận phân quyền: vai trò nào làm được gì ở trạng thái nào
- [x] Danh sách ràng buộc Poka-yoke
- [x] Lược đồ nhật ký sự kiện — `ARCHITECTURE.md` mục 6
- [x] Danh mục chỉ số cho bảng điều khiển — bốn chỉ số, tính thử qua Superset ở #21

### 1.4. Hạ tầng phát triển

- [x] `docker-compose.yml` dựng được toàn bộ hệ thống bằng một lệnh
- [x] `.env.example` với giá trị mặc định chạy được ngay
- [x] Tích hợp liên tục: dựng ảnh chứa, kiểm thử dịch vụ trên cụm thật, kiểm kiểu giao diện
      và kiểm header giấy phép trên mỗi đề nghị hợp nhất — #241
- [x] `docs/dependencies.md` với giấy phép từng phụ thuộc

---

## Giai đoạn 2 — Không gian H và P

**Trạng thái**: Hoàn thành — luồng thủ công thông đầu-cuối, đủ các luật giảng viên chốt ngày
08/10; còn kho tri thức chờ duyệt ADR-0006 · **Phiên bản**: `v0.3.0` có cổng người gửi; `v0.4.0`
khép luồng thủ công với hai buồng lái; `v0.5.0` (15/10) — bản cài đặt đầu tiên gửi nhóm khác dùng
thử theo yêu cầu của giảng viên: hộp thư trao đổi, giao diện mới, lịch làm việc, luật hồ sơ nằm
im, hạn theo mức ưu tiên và gia hạn; **`v0.6.0` (27/10) khép giai đoạn** — mở lại có giới hạn và
trạng thái Không tiếp nhận (#102), đính kèm tệp (#80), thống nhất từ ngữ trên giao diện (#157);
`v0.7.0` (28/10) hoàn thiện trước khi sang `D` — trang chủ theo việc cần làm và nhận diện mới
(#226), cờ "cần tôi xử lý" (#227), trường thông tin riêng theo loại yêu cầu (#250), tích hợp liên
tục (#241)

Mục tiêu: luồng nghiệp vụ chạy được **hoàn toàn thủ công**, không có AI. Đây là nền
tảng bắt buộc trước khi làm bất cứ thứ gì ở `D` và `I`.

### 2.1. Không gian H — Nhân sự

- [x] Tích hợp nền tảng định danh, đăng nhập một lần
- [x] Phân quyền theo vai trò — năm vai trò từ buổi trao đổi với giảng viên ngày 10/09
- [x] Cổng tự phục vụ: gửi yêu cầu, tra cứu trạng thái — #44
- [x] Buồng lái điều phối viên và buồng lái phòng ban — #45
- [x] Thông tin liên hệ của người gửi cho nhân viên xử lý hồ sơ — #131
- [x] Hộp thư chung kiểu Messenger, mỗi cuộc trò chuyện gắn một hồ sơ — #155
- [x] Giao diện mới: khung thanh bên, trang hồ sơ hai cột, hai hàng đợi — #158, #169, #170
- [x] Trang hồ sơ đặt việc và hạn trước nhật ký, theo nhận xét của giảng viên — #189
- [x] *Hồ sơ của tôi* bỏ bảng chú giải trạng thái — #192
- [ ] Kho tri thức nội bộ — chờ duyệt ADR-0006, rồi tích hợp

### 2.2. Không gian P — Quy trình

- [x] Máy trạng thái với trạng thái và quy tắc chuyển **lưu trong cơ sở dữ liệu**
- ~~Nhánh điều kiện: yêu cầu phát sinh chi phí rẽ sang luồng phê duyệt~~ — bỏ theo giảng
  viên ngày 10/09: phát sinh chi phí thì lập một phiếu yêu cầu mới
- [x] Theo dõi SLA và tự leo thang khi quá hạn, có ân hạn sau khi phân công lại
- [x] Ràng buộc Poka-yoke ở cả giao diện lẫn dịch vụ
- [x] Sinh nhật ký sự kiện ở mọi điểm chuyển trạng thái, kèm lịch sử thay đổi trường
      quyết định
- [x] Thao tác không đổi trạng thái: nhắn, hỏi tiến độ, nhận việc, sửa nội dung — #81,
      thiết kế ở ADR-0005, làm ở #127 và #128
- [x] Trò chuyện nội bộ chỉ nhân viên thấy — #156
- [x] Đếm quay lui theo cạnh làm lại khai trong dữ liệu; cấm tự điều phối hồ sơ mình gửi —
      #153, #154
- [x] Hồ sơ nằm im ở ba trạng thái chờ: cảnh báo trước, rồi tự trả về hay tự đóng — #142,
      #143, #144, giảng viên chốt hướng ngày 08/10
- [x] Lịch làm việc: mọi đồng hồ đếm giờ làm việc — #199
- [x] Hạn theo mức ưu tiên và gia hạn từng hồ sơ — #101, giảng viên chốt ngày 08/10
- [x] Mức "sắp hết hạn" khai trong dữ liệu — #175
- [x] Mở lại có giới hạn và cấp hạn mới — #102, thay quyết định ngày 23/09
- [x] Đính kèm tệp — #80

**Tiêu chí hoàn thành giai đoạn**: một yêu cầu đi được trọn vòng từ lúc gửi tới lúc
hoàn tất, qua đủ các nhánh, hoàn toàn bằng thao tác của người.

Vòng chính đã đạt ngày 23/09: navigator chạy tay trọn một hồ sơ qua bốn vai trò trên giao
diện thật. Lượt kiểm thử tổng thể đạt 54/54 kịch bản ngày 02/10. Các luật ở trên lên đủ ngày
26/10.

---

## Giai đoạn 3 — Không gian D

**Phiên bản dự kiến**: `v0.8.0`

Mục tiêu: dữ liệu từ `P` được chuẩn hóa và trực quan hóa, đủ để cấp quản lý ra
quyết định.

- [x] Chuẩn hóa bảng nhật ký sự kiện — sáu trường bắt buộc, cộng lý do và lịch sử thay đổi
- [ ] Tích hợp nền tảng kinh doanh thông minh
- [ ] Bảng điều khiển: tồn đọng theo bộ phận, thời gian xử lý trung vị, tỷ lệ vi
      phạm SLA, phân bố loại yêu cầu
- [ ] Xuất dữ liệu mở định dạng CSV và JSON
- [ ] Dữ liệu khởi tạo đủ lớn để bảng điều khiển có ý nghĩa khi trình diễn

**Tiêu chí hoàn thành giai đoạn**: mở bảng điều khiển thấy được chỉ số thật, thay
đổi theo thao tác trên hệ thống.

---

## Giai đoạn 4 — Không gian I

**Phiên bản dự kiến**: `v0.9.0`

Mục tiêu: gắn tầng trí tuệ nhân tạo lên trên nền đã ổn định. Ba tác vụ theo thứ tự
tăng dần độ khó.

**Nguyên tắc xuyên suốt**: AI chỉ ghi vào trường gợi ý, người quyết định. Mọi tác vụ
đều phải có đường điều chỉnh thủ công.

### 4.1. Phân loại và định tuyến tự động

- [ ] Tự phân loại yêu cầu vào nhóm
- [ ] Gợi ý người xử lý phù hợp
- [ ] Giao diện cho phép điều phối viên ghi đè gợi ý
- [ ] Ghi lại tỷ lệ ghi đè để đo độ chính xác thực tế

### 4.2. Truy xuất tri thức

- [ ] Lập chỉ mục kho tri thức và các hồ sơ đã giải quyết
- [ ] Gợi ý câu trả lời ngay khi người dùng đang soạn yêu cầu
- [ ] Đo tỷ lệ yêu cầu được ngăn chặn nhờ gợi ý

### 4.3. Khai phá quy trình

- [ ] Khai phá quy trình thực tế từ nhật ký sự kiện
- [ ] Đối chiếu quy trình thực tế với quy trình thiết kế
- [ ] Chỉ ra điểm nghẽn và nhánh lệch chuẩn
- [ ] Sinh khuyến nghị cải tiến bằng ngôn ngữ tự nhiên

**Tiêu chí hoàn thành giai đoạn**: gỡ tầng `I` ra thì hệ thống suy giảm rõ rệt về
giá trị, chứ không phải không đổi gì.

---

## Giai đoạn 5 — Thích ứng đề thi

**Bắt đầu**: khi Ban tổ chức công bố đề thi, tháng 11/2026
**Phiên bản dự kiến**: `v1.0.0`

Đây là giai đoạn có rủi ro cao nhất và thời gian ngắn nhất.

- [ ] Phân tích đề thi, đối chiếu với bộ khung hiện có
- [ ] Xác định phần nào giữ nguyên, phần nào thay dữ liệu, phần nào phải viết mới
- [ ] Thay dữ liệu khởi tạo: trạng thái, vai trò, ngưỡng SLA, chỉ số
- [ ] Bổ sung tính năng đề thi yêu cầu mà bộ khung chưa có
- [ ] Cập nhật toàn bộ tài liệu cho khớp

**Chuẩn bị trước để giảm rủi ro**: tuân thủ nghiêm nguyên tắc cấu hình thay vì mã
cứng ở mục 5 của `ARCHITECTURE.md`. Nếu làm đúng, phần lớn công việc giai đoạn này
chỉ là thay dữ liệu.

---

## Giai đoạn 6 — Hoàn thiện và trình diễn

**Trước 07/12/2026**

### 6.1. Rà soát tiêu chí PoF

- [ ] Kho mã công khai, truy cập được không cần đăng nhập
- [ ] Mọi tệp mã có header giấy phép SPDX
- [ ] `LICENSE` toàn văn có mặt
- [ ] Bản phát hành `v1.0.0` với định dạng mở
- [ ] `docker compose up` chạy được trên máy sạch, kiểm chứng trên máy khác
- [ ] Hướng dẫn dựng trong `README.md` chính xác
- [ ] `docs/dependencies.md` đầy đủ, không có phụ thuộc nào bị sửa mã
- [ ] `CHANGELOG.md` đầy đủ, sinh từ lịch sử commit

### 6.2. Chuẩn bị trình diễn

- [ ] Kịch bản trình diễn tám phút, có điểm nhấn ở phần khai phá quy trình
- [ ] Dữ liệu trình diễn đủ phong phú
- [ ] Luyện tập ít nhất ba lần
- [ ] Phương án dự phòng nếu mạng chậm hoặc mô hình lỗi
- [ ] Chuẩn bị trả lời các câu hỏi dự kiến của ban giám khảo

### 6.3. Thu hút cộng đồng

- [ ] `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` đầy đủ
- [ ] Nhãn `good first issue` và `help wanted` có issue thật
- [ ] Trang tài liệu kỹ thuật dựng từ thư mục `docs/`

---

## Nguyên tắc xuyên suốt

Áp dụng ở mọi giai đoạn, không chỉ giai đoạn cuối.

| Nguyên tắc | Lý do |
|---|---|
| `main` luôn dựng được và trình diễn được | Ban giám khảo chấm trên `main` |
| Cấu hình thay vì mã cứng | Giảm chi phí thích ứng đề thi tháng 11 |
| Cắt bản phát hành thường xuyên | Cho thấy dự án phát triển liên tục |
| Cập nhật tài liệu cùng lúc với mã | Tài liệu chiếm tới 20 trên 100 điểm |
| Kiểm tra giấy phép trước khi thêm phụ thuộc | Giấy phép sai khiến dự án không được chấm |
| Xây `H` và `P` trước, `D` rồi mới `I` | Tính tuyến tính bắt buộc của khung H-P-D-I |
