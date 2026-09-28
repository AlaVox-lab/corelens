# ADR-0007: Thư viện khai phá quy trình cho không gian I

| Mục | Giá trị |
|---|---|
| Trạng thái | Đề xuất |
| Ngày | 2026-09-28 |
| Không gian kiến trúc | `I` |
| Issue liên quan | #48 |
| Người quyết định | Navigator (`AlaVox-lab`) và giảng viên hướng dẫn — chưa chốt |

---

## Bối cảnh

Điểm sáng tạo chịu lực của đề tài là **vòng phản hồi tự soi quy trình** (`CLAUDE.md` mục
4.1): từ nhật ký sự kiện, hệ thống vẽ lại quy trình đang thật sự chạy, đối chiếu với quy
trình thiết kế, chỉ ra cạnh lệch chuẩn, vòng lặp định tuyến sai và điểm nghẽn. Gỡ thành
phần này ra thì sản phẩm tụt xuống mức helpdesk thông thường.

Khai phá quy trình thuộc nhóm **lắp ghép** (`CLAUDE.md` mục 3.2): dùng thư viện nguồn mở có
sẵn, không tự cài đặt lại thuật toán.

Ràng buộc:

1. **Giấy phép** — bảng chấm PoF mục Giấy phép (10 điểm), trừ 5 điểm nếu mã nguồn chứa sự
   không tương thích giấy phép. Mảng này có thư viện copyleft mạnh
2. **Đọc được nhật ký hiện có** — lược đồ `event_log` ở `ARCHITECTURE.md` mục 6, không đổi
   lược đồ chỉ để chiều thư viện
3. **Dựng bằng một lệnh trên máy sạch** — bảng chấm PoF mục Dựng từ mã nguồn (10 điểm);
   tài nguyên cộng vào ngân sách toàn hệ thống
4. **Thứ tự H → P → D → I** (`CLAUDE.md` mục 3.1) — bản ghi này chọn thư viện, chưa tích hợp

Quá trình khảo sát, số liệu đo và nguồn ghi trong
[`../process-mining-survey.md`](../process-mining-survey.md).

---

## Các phương án đã cân nhắc

### Phương án A — PM4Py `2.7.23.8`

| Mục | Nội dung |
|---|---|
| Giấy phép | AGPL-3.0-or-later — xác minh ở `LICENSE` của kho và tệp giấy phép trong gói đã cài; nhà phát triển bán thêm giấy phép thương mại riêng |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có, **có điều kiện** — chỉ khi nằm trong dịch vụ khai phá tách riêng |
| Tài nguyên khi chạy | 174 MiB bộ nhớ tiến trình cho 1.000 hồ sơ; phân tích 1,5 giây, đo thật |
| Khả năng đóng gói bằng container | Gói Python cài từ PyPI; chạy được trong một container Python riêng |
| Chất lượng tài liệu | Tốt; có hàm cấp cao cho khám phá, đối chiếu, thời gian |
| Mức độ hoạt động của dự án | Tích cực — bản `2.7.23.8` phát hành 2026-09-01 |
| Độ khó tích hợp | Vừa — phải dựng thêm một dịch vụ, vì giấy phép |

**Ưu điểm**

- Đã chạy đủ bốn việc của #48: vẽ sơ đồ 24 cạnh, đối chiếu thiết kế, đếm vòng lặp định
  tuyến sai, đo thời gian nằm ở mỗi trạng thái
- Phép cài lệch 8 hồ sơ: bắt **đúng 8**, không báo nhầm, bằng phát lại token trên lưới thiết
  kế
- Cùng Python với dịch vụ ứng dụng — nhóm không phải thêm ngôn ngữ để bảo trì
- Nhiều thuật toán có sẵn nhất trong các ứng viên

**Nhược điểm**

- AGPL buộc giữ ranh giới dịch vụ riêng suốt vòng đời dự án
- Kéo theo bộ thư viện số học lớn — numpy, scipy, pandas, matplotlib và các gói khác: tốn
  bộ nhớ gấp đôi rưỡi pm4js, ảnh chứa nặng hơn
- Lần nạp đầu sau khi cài mất 95 giây vì biên dịch mã — phải biên dịch sẵn trong ảnh

### Phương án B — pm4js `0.0.38`

| Mục | Nội dung |
|---|---|
| Giấy phép | BSD-3-Clause — xác minh ở `LICENSE` của kho và của gói đã cài; gói kèm tệp `heapq.js` theo **CC BY-SA 2.5** |
| Được OSI công nhận | Có cho BSD-3-Clause; CC BY-SA 2.5 thì không |
| Tương thích với MIT | Có, nhưng phải ghi chú riêng tệp CC BY-SA |
| Tài nguyên khi chạy | 69 MiB bộ nhớ tiến trình cho 1.000 hồ sơ; phân tích dưới 0,1 giây, đo thật |
| Khả năng đóng gói bằng container | Gói npm; chạy được trong container Node riêng |
| Chất lượng tài liệu | Vừa — một tệp `DOCS.md` liệt kê hàm |
| Mức độ hoạt động của dự án | Thấp — bản npm gần nhất 2023-10-20; kho còn nhận commit tới 2026-08 |
| Độ khó tích hợp | Vừa — thêm Node vào tầng `I` |

**Ưu điểm**

- Giấy phép dễ dãi, nhúng được mà không cần ranh giới dịch vụ
- Nhẹ và nhanh nhất; cho cùng 24 cạnh, cùng tần suất như PM4Py
- Gióng hàng trên đồ thị thiết kế bắt **đúng 8/8** hồ sơ cài lệch

**Nhược điểm**

- Bản `0.0.x`, ít thuật toán hơn
- Phát lại token trên lưới Petri có chuyển tiếp trùng nhãn báo sai cả 989 hồ sơ
- Tệp CC BY-SA 2.5 đi kèm là một điểm giấy phép phải giải trình

### Phương án C — bupaR `1.0.1`

| Mục | Nội dung |
|---|---|
| Giấy phép | MIT — xác minh ở `DESCRIPTION` trên CRAN của `bupaR`, `processmapR`, `processcheckR` và `LICENSE` của kho |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có |
| Tài nguyên khi chạy | Chưa đo |
| Khả năng đóng gói bằng container | Cần ảnh chứa có môi trường R |
| Chất lượng tài liệu | Chưa đánh giá |
| Mức độ hoạt động của dự án | `1.0.1` trên CRAN ngày 2026-01-27 |
| Độ khó tích hợp | Cao — thêm cả ngôn ngữ R vào bộ công nghệ |

**Ưu điểm**

- Giấy phép MIT, không ràng buộc
- Có gói vẽ sơ đồ (`processmapR`) và kiểm theo luật (`processcheckR`)

**Nhược điểm**

- Chưa dựng thử, chưa đo
- Nhóm không dùng R ở đâu khác; chưa kiểm giấy phép các gói R kéo theo

### Phương án D — ProM `6.15`

| Mục | Nội dung |
|---|---|
| Giấy phép | Lõi GPL, phần lớn plug-in L-GPL — theo trang `promtools.org`; kho `ProM-Framework` không có tệp `LICENSE` |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có điều kiện |
| Tài nguyên khi chạy | Chưa đo |
| Khả năng đóng gói bằng container | Không phù hợp — ứng dụng máy tính có giao diện |
| Chất lượng tài liệu | Chưa đánh giá |
| Mức độ hoạt động của dự án | Lâu đời; kho lõi cập nhật gần nhất 2023-11 |
| Độ khó tích hợp | Không tích hợp được như dịch vụ |

**Ưu điểm**

- Công cụ tham chiếu của giới nghiên cứu khai phá quy trình

**Nhược điểm**

- Không chạy được như dịch vụ trong cụm — chỉ dùng được thủ công trên máy người phân tích
- Căn cứ giấy phép nằm trên trang web, không nằm trong kho mã

---

## Quyết định

Đề xuất chọn **PM4Py `2.7.23.8`** làm thư viện khai phá quy trình cho không gian `I`, chạy
trong **một dịch vụ khai phá tách riêng**, giao tiếp với phần còn lại qua HTTP.

Đây chưa phải quyết định đã chấp nhận. Navigator và giảng viên cần xem xét trước khi đổi
trạng thái.

---

## Lý do

**Tiêu chí quyết định là năng lực đã kiểm chứng.** PM4Py là ứng viên duy nhất vừa có nhiều
thuật toán, vừa đã chạy đủ bốn việc của issue trên nhật ký của dự án, kể cả đối chiếu thiết
kế bằng phát lại token trên chính lưới mà pm4js xử lý sai. Nó cùng Python với dịch vụ ứng
dụng và đang được phát triển tích cực.

**Giấy phép là cái giá, và trả được.** AGPL buộc ranh giới dịch vụ riêng — cùng cách dự án
đã tính cho Metabase, Garage và MinIO. Bộ nhớ 174 MiB nằm trong ngân sách, cỡ Superset.

**pm4js là phương án lùi**, dùng nếu giảng viên muốn tránh hẳn copyleft: nhẹ, giấy phép dễ
dãi, bắt lệch đúng bằng gióng hàng trên DFG. Nó không được chọn vì bản `0.0.x`, ít thuật
toán, đưa Node vào tầng `I`, và vẫn có tệp CC BY-SA phải giải trình.

**bupaR** không được chọn vì thêm cả ngôn ngữ R mà chưa đo được gì. **ProM** không dùng được
như dịch vụ.

**Bị loại vì giấy phép**: Celonis và Disco (Fluxicon) — phần mềm thương mại mã đóng, không
phải nguồn mở. Ghi lại để người sau không đề xuất.

---

## Cách tích hợp

**Chạy như dịch vụ độc lập.** Ranh giới:

| Thành phần | Vai trò |
|---|---|
| Dịch vụ khai phá (container riêng, thư mục riêng) | **Nơi duy nhất** `import pm4py`. Đọc nhật ký, trả sơ đồ và chỉ số qua HTTP |
| Dịch vụ ứng dụng (FastAPI, MIT) | Không `import pm4py`. Gọi dịch vụ khai phá qua HTTP khi cần |
| PostgreSQL | Dịch vụ khai phá chỉ được quyền **đọc**, bằng tài khoản riêng — như Superset ở ADR-0003 |
| Tầng `D` | Xuất nhật ký cho khai phá: dựng sự kiện mở đầu từ `requests.created_at` (`ARCHITECTURE.md` mục 6) |

### Ranh giới giấy phép

- **Chiều MIT sang AGPL là tương thích.** Danh sách giấy phép của GNU ghi giấy phép MIT
  (Expat) *"compatible with the GNU GPL"*. Các tệp nhóm viết trong dịch vụ khai phá vẫn
  giữ header MIT; khi chạy, cả dịch vụ đó là một chương trình dùng thư viện AGPL
- **Điều 13 của AGPL**: dịch vụ khai phá phục vụ người dùng qua mạng thì phải cho họ lấy
  được mã nguồn tương ứng. Kho mã của dự án công khai nên đáp ứng sẵn. Không sửa mã PM4Py
  nên không có phần sửa nào phải công bố thêm
- **Dịch vụ ứng dụng và cổng không bao giờ `import pm4py`** — chỉ trao đổi dữ liệu qua HTTP,
  nên AGPL không lan sang phần còn lại (điều 5, tác phẩm riêng biệt gộp chung — *aggregate*)
- Cài từ PyPI, ghim phiên bản bằng `==`; không chép mã thư viện vào kho, không sửa mã thư
  viện

**Tầng `I` chỉ gợi ý** (`CLAUDE.md` mục 4.3): dịch vụ khai phá chỉ đọc và phân tích, không
ghi vào bất kỳ trường quyết định nào của hồ sơ.

---

## Hệ quả

**Điều gì trở nên dễ hơn**

- Có sẵn khám phá quy trình, đối chiếu thiết kế, phân tích thời gian — không tự viết thuật
  toán
- Nhật ký hiện tại dùng được ngay, **không cần thêm trường**. Hai việc ở bước xuất: dựng sự
  kiện mở đầu từ `requests.created_at`; lấy `to_state` làm hoạt động khi đối chiếu thiết kế,
  vì một mã hoạt động có thể đi nhiều cạnh (`provide-info` ba cạnh, `cancel` bốn cạnh)
- Đếm vòng lặp định tuyến sai theo cạnh từ chối; cột `changes` tách được hồ sơ định tuyến
  lại mà vẫn về phòng cũ
- Ranh giới lắp ghép rõ, thuận lợi khi trình bày kiến trúc Open-Core

**Điều gì trở nên khó hơn**

- Thêm một dịch vụ phải dựng, khởi động, giám sát; ảnh chứa nặng vì bộ thư viện số học —
  kích thước ảnh chưa đo
- Phải giữ ranh giới AGPL mãi: không ai được `import pm4py` trong dịch vụ ứng dụng
- Doanh nghiệp dùng DX-OS mà sửa dịch vụ khai phá thì phải công khai phần sửa
- Câu *"không nhúng thư viện vào mã nguồn dự án"* ở `CLAUDE.md` mục 5.2, `ARCHITECTURE.md`
  mục 3.3 và `docs/dependencies.md` không còn đúng nguyên văn — phải sửa thành "chỉ trong
  dịch vụ tách riêng", nếu không tài liệu mâu thuẫn với mã

**Việc phải làm tiếp sau quyết định này**

- [ ] Navigator và giảng viên chấp nhận hoặc yêu cầu sửa bản ghi
- [ ] Nếu chấp nhận, cập nhật `docs/ARCHITECTURE.md` mục 3 và câu quy tắc AGPL ở mục 3.3
- [ ] Nếu chấp nhận, cập nhật `docs/dependencies.md` với PM4Py, AGPL-3.0-or-later và ranh
      giới dịch vụ; sửa câu tương ứng ở `CLAUDE.md` mục 5.2
- [ ] Tạo issue riêng cho dịch vụ khai phá và bước xuất nhật ký của tầng `D` — làm sau khi
      `P` và `D` ổn định
- [ ] Chạy lại phân tích trên nhật ký thật khi hệ thống có dữ liệu vận hành
- [ ] Đo kích thước ảnh chứa và bộ nhớ khi dịch vụ vào cụm thật

---

## Ghi chú

- Chạy thử ngoài kho trong thư mục `thu-48\`, mỗi thư viện một môi trường riêng; không cài
  gì vào container của dự án, không ghi gì vào cơ sở dữ liệu
- Dữ liệu: bộ sinh `scripts/sinh_nhat_ky_ao.py` (#124), tham số mặc định, hạt giống
  `20260924` — 1.000 hồ sơ, 6.736 sự kiện, bộ quy tắc 10 trạng thái, 24 cạnh
- Máy đo: Intel Core i7-13700HX, 15,6 GB RAM, Windows 11 Pro; Python `3.13.7`, Node.js
  `24.11.1`. Bộ nhớ đo bằng `psutil` và `process.memoryUsage`
- Toàn bộ số liệu chạy trên nhật ký **ảo**: chứng minh thư viện đọc lại đúng giả định của bộ
  sinh, chưa phải phát hiện nghiệp vụ
- Nguồn tham khảo đầy đủ ở mục 6.2 của tài liệu khảo sát

**Điều kiện khiến quyết định này cần xem lại**:

- PM4Py đổi sang giấy phép không thuộc danh sách OSI, hoặc tách bản cộng đồng khỏi các
  thuật toán cần dùng
- Giảng viên không chấp nhận ranh giới AGPL — khi đó chuyển sang pm4js
- pm4js ra bản ổn định và bỏ tệp CC BY-SA
