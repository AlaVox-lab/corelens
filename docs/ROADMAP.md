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
| **Công bố đề thi chính thức** | **Tháng 11/2026** | Đã công bố — đối chiếu ở [`doi-chieu-de-thi.md`](doi-chieu-de-thi.md) |
| **Hạn gửi bài** | **17:00 ngày 06/12/2026** | Gửi đường dẫn kho mã qua thư điện tử; kho phải công khai |
| Chấm kho mã nguồn | 07–09/12/2026 | 50 điểm PoF, chấm trên `main` |
| Trình diễn và chung kết | 10/12/2026 | 50 điểm sản phẩm, mỗi đội trình bày 15 phút |
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

**Trạng thái**: Hoàn thành — ADR-0007 và ADR-0008 đã chấp nhận (08/11, giảng viên xác nhận ADR-0007
ngày 10/11); ADR-0006 navigator chấp nhận 14/11 (chờ giảng viên xác nhận), cài ở #321; còn `CODE_OF_CONDUCT.md` ·
**Phiên bản**: `v0.2.0`

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
- [x] `[H]` Hệ thống quản trị tri thức nội bộ — khảo sát xong (#46), ADR-0006 chọn Wiki.js, navigator
      chấp nhận 14/11 (chờ giảng viên xác nhận); cài ở #321 dưới hồ sơ Compose tùy chọn `tri-thuc`, đăng nhập
      một lần, bài viết làm nguồn gợi ý thứ hai
- [x] `[P]` Nền tảng tự động hóa luồng công việc — so sánh với phương án tự xây
      máy trạng thái — chọn tự viết, ADR-0004
- [x] `[D]` Nền tảng kinh doanh thông minh nguồn mở — Apache Superset, ADR-0003
- [x] `[I]` Cơ sở dữ liệu véc-tơ và khung phát triển mô hình ngôn ngữ lớn — pgvector và llama.cpp,
      không dùng khung LLM, ADR-0008 (chấp nhận 08/11, cài ở #316, #317, #319)
- [x] `[I]` Thư viện khai phá quy trình — PM4Py trong dịch vụ tách riêng, ADR-0007 (chấp nhận
      08/11, giảng viên xác nhận 10/11 kèm mô hình nhiều giấy phép #340)

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
tục (#241); `v0.8.0` (02/11) khép đợt làm mới giao diện — phân trang và bộ lọc phía dịch vụ
(#232), ngăn xem nhanh hồ sơ (#233), quy tắc chuyển động (#237), kịch bản kiểm tra giao diện qua
đăng nhập thật (#238), trang tài liệu (#279) — và hồ sơ đang chạy giữ bộ quy tắc cũ khi đổi quy
trình (#278, #299)

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
- [x] Kho tri thức nội bộ — ADR-0006 chấp nhận 14/11, cài ở #321 (hồ sơ tùy chọn `tri-thuc`)

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

**Trạng thái**: Hoàn thành · **Phiên bản**: `v0.9.0` (03/11) — lớp báo cáo trên nhật ký sự kiện và
bảng điều khiển dựng từ tệp cấu hình (#304), nhúng trong cổng lọc theo phòng của người xem (#305),
xuất nhật ký CSV và JSON cùng lệnh nạp dữ liệu trình diễn (#306). Bản vá `v0.9.1` (08/11) nâng khung
giao diện của cổng để vá cảnh báo bảo mật (#313)

Mục tiêu: dữ liệu từ `P` được chuẩn hóa và trực quan hóa, đủ để cấp quản lý ra
quyết định.

- [x] Chuẩn hóa bảng nhật ký sự kiện — sáu trường bắt buộc, cộng lý do và lịch sử thay đổi
- [x] Tích hợp nền tảng kinh doanh thông minh
- [x] Bảng điều khiển: tồn đọng theo bộ phận, thời gian xử lý trung vị, tỷ lệ vi
      phạm SLA, phân bố loại yêu cầu
- [x] Xuất dữ liệu mở định dạng CSV và JSON
- [x] Dữ liệu khởi tạo đủ lớn để bảng điều khiển có ý nghĩa khi trình diễn

**Tiêu chí hoàn thành giai đoạn**: mở bảng điều khiển thấy được chỉ số thật, thay
đổi theo thao tác trên hệ thống.

---

## Giai đoạn 4 — Không gian I

**Trạng thái**: Hoàn thành về chức năng — còn kho tri thức (#321) để ngoài phạm vi thi · **Phiên bản**:
`v0.10.0` (09/11) đưa trước thẻ gợi ý có xác nhận (#239) cùng đợt nền tảng vận hành (#243, #249, #253,
#254); `v0.11.0` (10/11) khai phá quy trình thực tế và màn Quy trình thực tế trong cổng (#314, #315);
`v0.12.0` (11/11) mô hình ngôn ngữ cục bộ tùy chọn và gợi ý loại, mức ưu tiên, phòng (#316, #317), mô
hình nhiều giấy phép (#340); `v0.13.0` (11/11) gợi ý người xử lý, hồ sơ tương tự, khuyến nghị cải tiến
(#318, #319, #320) · **Mốc**: *Giai đoạn 4 — Không gian I*, hạn 29/11 · **Issue gốc**: #322

Mục tiêu: gắn tầng trí tuệ nhân tạo lên trên nền đã ổn định. **Khai phá quy trình làm trước**
(navigator chốt 04/11): đó là điểm sáng tạo của đề tài. Phân loại và truy xuất làm sau, trên ADR-0008.

**Nguyên tắc xuyên suốt**: AI chỉ ghi vào trường gợi ý, người quyết định. Mọi tác vụ
đều phải có đường điều chỉnh thủ công.

### 4.1. Khai phá quy trình

- [x] Khai phá quy trình thực tế từ nhật ký sự kiện (#314)
- [x] Đối chiếu quy trình thực tế với luồng chính của quy trình thiết kế (#314)
- [x] Chỉ ra điểm nghẽn và nhánh lệch chuẩn trên màn quy trình thực tế trong cổng (#315)
- [x] Sinh khuyến nghị cải tiến bằng ngôn ngữ tự nhiên (#320)

### 4.2. Phân loại và định tuyến tự động

- [x] Giao diện cho phép điều phối viên giữ hoặc ghi đè gợi ý, ghi lại tỷ lệ ghi đè để đo độ chính
      xác thực tế (#239, `v0.10.0`)
- [x] Dịch vụ mô hình ngôn ngữ cục bộ, bật theo lựa chọn (#316)
- [x] Tự gợi ý loại yêu cầu, mức ưu tiên và phòng ban (#317)
- [x] Gợi ý người xử lý phù hợp (#318)

### 4.3. Truy xuất tri thức

- [x] Lập chỉ mục các hồ sơ đã giải quyết, gợi ý hồ sơ tương tự ngay khi người dùng đang soạn yêu cầu
      (#319)
- [x] Đo tỷ lệ yêu cầu được ngăn chặn nhờ gợi ý (#319)
- [ ] Kho tri thức — nhóm đề xuất để ngoài phạm vi thi, làm khi còn thời gian (#321)

**Tiêu chí hoàn thành giai đoạn**: gỡ tầng `I` ra thì hệ thống suy giảm rõ rệt về
giá trị, chứ không phải không đổi gì.

Đạt ngày 11/11 về chức năng: gỡ tầng `I` thì mất màn Quy trình thực tế, thẻ gợi ý và hồ sơ tương tự;
tắt riêng mô hình thì luồng thủ công vẫn chạy đủ. Giới hạn đã biết: mô hình 1,5B gợi ý mức ưu tiên còn
yếu và gợi ý phòng dưới ngưỡng 80 % nên giữ bảng ánh xạ — số đo ở `PROJECT_STATE.md`.

---

## Giai đoạn 5 — Thích ứng đề thi

**Bắt đầu**: 15/11/2026, sau khi Ban tổ chức công bố đề thi · issue gốc #369
**Phiên bản dự kiến**: `v1.0.0`

Đây là giai đoạn có rủi ro cao nhất và thời gian ngắn nhất.

Đề yêu cầu một nền tảng lõi không giao diện cung cấp định danh, cổng API, quản trị dữ liệu và động cơ
luồng công việc, cùng ít nhất một ứng dụng minh họa trong H-P-D-I. Bộ khung đã có ứng dụng minh họa và
ba trong bốn dịch vụ lõi; còn thiếu cổng API và ranh giới rõ giữa lõi với ứng dụng.

- [x] Phân tích đề thi, đối chiếu với bộ khung hiện có — [`doi-chieu-de-thi.md`](doi-chieu-de-thi.md) (#363)
- [x] Khảo sát nền tảng cổng API — ADR-0010, đã chấp nhận 15/11 (#363)
- [ ] Cổng API làm cửa vào duy nhất của cụm (#364)
- [ ] Tách nền tảng lõi không giao diện khỏi ứng dụng minh họa (#365) — giảng viên chốt 15/11: làm Mức 1 (vẽ lại ranh giới API) trước, xong mới xét Mức 2 (nhiều quy trình)
- [ ] Xác thực hai lớp tùy chọn (#366)
- [ ] Viết lại tài liệu theo mô hình ba tầng của đề (#367)
- [ ] Phát hành `v1.0.0`, kiểm dựng từ tệp phát hành (#368)

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
