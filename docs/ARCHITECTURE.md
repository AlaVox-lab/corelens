# ARCHITECTURE.md

> **Mục đích của tệp này**: đây là nguồn thông tin duy nhất về cách kho mã được tổ
> chức và vì sao. Bất kỳ ai — người hay công cụ AI — khi bắt đầu làm việc với dự án
> đều phải đọc tệp này **trước khi** khám phá mã nguồn, trước khi viết mã mới.
>
> **Tệp này mô tả HIỆN TRẠNG của mã nguồn, không phải nhật ký thay đổi và không
> phải kế hoạch.** Kế hoạch tương lai thuộc về `ROADMAP.md`. Tiến độ tuần thuộc về
> `PROJECT_STATE.md`. Khi thay đổi một khuôn mẫu thiết kế (không phải sửa lỗi bên
> trong khuôn mẫu đã có), **bắt buộc** cập nhật mục tương ứng ngay trong cùng công
> việc đó. Xem mục 12.

---

## 1. Tóm tắt dự án

**dx-os-lab** — Trạm thực hành số (DX-Lab) mô phỏng một Hệ điều hành Doanh nghiệp
số, xây dựng theo kiến trúc Open-Core cho cuộc thi Phần mềm nguồn mở, Olympic Tin
học Sinh viên Việt Nam 2026.

**Bài toán nghiệp vụ**: Cổng vận hành yêu cầu nội bộ — tiếp nhận và điều phối tập
trung mọi loại yêu cầu trong doanh nghiệp (sự cố thiết bị, cấp quyền phần mềm, giấy
xác nhận nhân sự, đề xuất mua vật tư).

**Điểm khác biệt**: vòng phản hồi tự soi quy trình. Mọi chuyển trạng thái ghi vào
nhật ký sự kiện có cấu trúc; từ đó hệ thống tự khai phá lại quy trình thực tế đang
chạy và đối chiếu với quy trình đã thiết kế, chỉ ra điểm nghẽn và nhánh lệch chuẩn.

**Giai đoạn hiện tại**: `v0.1.0` — mới có bộ khung kho mã và tài liệu chuẩn.
**Chưa có mã nguồn ứng dụng.** Các mục 4 đến 9 dưới đây mô tả thiết kế đã thống
nhất nhưng **chưa được cài đặt**; chúng sẽ chuyển thành mô tả hiện trạng khi mã
nguồn tương ứng xuất hiện.

**Ràng buộc quan trọng**: đề thi chính thức chỉ được công bố tháng 11/2026. Mọi thứ
xây dựng trước thời điểm đó là **bộ khung tái sử dụng**, không phải sản phẩm cuối.
Xem mục 10 về nguyên tắc thiết kế xuất phát từ ràng buộc này.

---

## 2. Khung kiến trúc H-P-D-I

Toàn bộ hệ thống tổ chức theo bốn không gian chức năng do đề bài quy định. Ký hiệu
này được dùng nhất quán trong nhãn issue, phạm vi commit, cấu trúc thư mục và tên
biến.

| Ký hiệu | Không gian | Trách nhiệm |
|---|---|---|
| **H** | Human — Nhân sự | Định danh tập trung, phân quyền theo vai trò, cổng tự phục vụ, kho tri thức nội bộ |
| **P** | Process — Quy trình | Máy trạng thái, luồng phê duyệt, ràng buộc Poka-yoke, theo dõi SLA, sinh nhật ký sự kiện |
| **D** | Data — Dữ liệu | Nguồn sự thật duy nhất, nhật ký sự kiện chuẩn hóa, bảng điều khiển, xuất dữ liệu mở |
| **I** | Intelligence — Trí tuệ nhân tạo | Phân loại tự động, truy xuất tri thức, khai phá quy trình |

### 2.1. Tính tuyến tính bắt buộc

Bốn không gian phải xây dựng **theo thứ tự H → P → D → I**. Không thể đạt năng lực
tự động hóa ở `I` khi `P` chưa có ràng buộc và `D` chưa chuẩn hóa. Tích hợp AI vào
quy trình chưa chuẩn hóa sẽ sinh ảo giác dữ liệu.

**Hệ quả thực hành**: nếu một công việc yêu cầu xây dựng thành phần thuộc `I` trong
khi `P` và `D` chưa ổn định, hãy nêu vấn đề trước khi thực hiện.

### 2.2. Nguyên tắc bất di dịch: AI chỉ gợi ý, con người quyết định

Tầng `I` **chỉ được ghi vào các trường mang tính gợi ý**, không bao giờ ghi trực
tiếp vào trường quyết định. Mọi kết quả từ AI phải đi qua một bước xác nhận của
người có thẩm quyền, dù chỉ là một cú nhấn chuột.

Trong lược đồ dữ liệu, tách rõ hai nhóm trường:

| Trường gợi ý (AI ghi) | Trường quyết định (người ghi) |
|---|---|
| `suggested_category` | `category` |
| `suggested_assignee_id` | `assignee_id` |
| `suggested_priority` | `priority` |

Đồng thời ghi lại việc con người có ghi đè gợi ý của AI hay không, phục vụ đo lường
độ chính xác thực tế của mô hình.

Ba lý do: đúng nguyên lý Human-in-the-loop mà đề bài nêu; nếu AI phân luồng sai thì
người dùng vẫn điều chỉnh được; và nếu mô hình lỗi vào ngày trình diễn, hệ thống
vẫn vận hành ở chế độ thủ công.

**Thứ tự xây dựng bắt buộc**: hoàn thiện luồng thủ công chạy đúng trước, sau đó mới
gắn AI vào như một lớp hỗ trợ.

---

## 3. Bộ công nghệ

Không đưa vào công nghệ thay thế mà không cập nhật mục này và tạo một bản ghi quyết
định kiến trúc trong `docs/adr/`.

### 3.1. Đã chốt

| Tầng | Công nghệ | Giấy phép | Ghi chú |
|---|---|---|---|
| Giao diện | Next.js (React) | MIT | Cổng người dùng và bảng điều khiển |
| Dịch vụ ứng dụng | FastAPI (Python) | MIT | Cùng ngôn ngữ với toàn bộ tầng `I`, không phải bắc cầu sang dịch vụ khác |
| Cơ sở dữ liệu | PostgreSQL | PostgreSQL License | Được OSI công nhận. Hỗ trợ phần mở rộng tìm kiếm véc-tơ phục vụ `I` |
| Đóng gói | Docker + Docker Compose | Apache-2.0 | Dựng toàn hệ thống bằng một lệnh |
| Định danh tập trung | Keycloak `26.7.3` | Apache-2.0 | Không gian `H`. Chạy như dịch vụ độc lập, giao tiếp qua OIDC. Xem [ADR-0001](adr/0001-chon-nen-tang-sso.md) |
| Quản trị CSDL | Chờ quyết định | | Hai phương án: pgAdmin 4 (chạy trong Compose) hoặc DBeaver Community |

Cả năm thành phần đã chốt đều dùng giấy phép nhóm dễ dãi, tương thích hoàn toàn với
MIT của sản phẩm.

Vai trò nghiệp vụ **không khai báo trong mã nguồn**. Keycloak nạp toàn bộ realm gồm
vai trò, ứng dụng khách và người dùng từ một tệp JSON lúc khởi động, nên việc đổi bộ
vai trò khi đề thi công bố chỉ là thay dữ liệu. Đây là một trường hợp cụ thể của khuôn
mẫu ở mục 5.

### 3.2. Chờ khảo sát

Bộ công nghệ nền mới là hạ tầng ứng dụng, chưa cấu thành hệ sinh thái DX-Lab theo
yêu cầu Open-Core. Bốn nhóm thành phần sau cần khảo sát và ghi kết quả vào
`docs/adr/`:

| Không gian | Thành phần | Ghi chú khảo sát |
|---|---|---|
| `H` | Hệ thống quản trị tri thức | Vừa phục vụ người dùng, vừa là nguồn dữ liệu cho truy xuất tri thức ở `I` |
| `D` | Nền tảng kinh doanh thông minh | Đề bài nêu rõ yêu cầu BI nguồn mở. Dùng nền tảng chuyên dụng thay vì tự vẽ biểu đồ |
| `I` | Cơ sở dữ liệu véc-tơ và khung LLM | Ưu tiên phần mở rộng véc-tơ ngay trên PostgreSQL để giảm số dịch vụ |
| `I` | Thư viện khai phá quy trình | Kiểm tra kỹ giấy phép, mảng này có thư viện dùng copyleft mạnh |

### 3.3. Quy tắc kiểm tra giấy phép

Trước khi thêm bất kỳ phụ thuộc nào:

1. Đối chiếu tên giấy phép với danh sách chính thức tại `opensource.org/licenses`
2. Kiểm tra tương thích với MIT
3. Ghi kết quả vào `docs/dependencies.md`

Cảnh giác với các giấy phép **không** thuộc danh sách OSI: BSL, SSPL, Elastic
License, Commons Clause, fair-code. Dùng chúng khiến dự án không được chấm điểm.

Với giấy phép copyleft mạnh (AGPL): hợp lệ vì được OSI công nhận, nhưng chỉ dùng
dưới dạng dịch vụ độc lập giao tiếp qua HTTP, không nhúng thư viện vào mã nguồn.
Ghi rõ ranh giới này trong bản ghi quyết định.

---

## 4. Cấu trúc thư mục

### 4.1. Hiện trạng

```
dx-os-lab/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── config.yml
│   │   ├── feature_request.md
│   │   └── research.md
│   └── pull_request_template.md
├── docs/
│   ├── adr/
│   │   └── README.md            # quy ước ghi bản ghi quyết định kiến trúc
│   ├── ARCHITECTURE.md          # tệp này
│   ├── PROJECT_STATE.md         # trạng thái hiện tại, cập nhật hàng tuần
│   ├── ROADMAP.md               # lộ trình tới tháng 12
│   └── dependencies.md          # danh mục phụ thuộc và giấy phép
├── scripts/
│   └── setup-labels.sh          # khởi tạo hệ thống nhãn
├── .gitattributes               # chuẩn hóa ký tự kết thúc dòng
├── .gitignore
├── CHANGELOG.md                 # sinh tự động bằng git-cliff
├── CONTRIBUTING.md              # quy trình làm việc và quy ước mã nguồn
├── LICENSE                      # MIT toàn văn
├── README.md
└── cliff.toml                   # cấu hình sinh nhật ký thay đổi
```

### 4.2. Cấu trúc dự kiến khi có mã nguồn

Chưa cài đặt. Ghi ở đây để thống nhất trước, tránh mỗi người đặt một kiểu.

```
dx-os-lab/
├── frontend/                    # Next.js
│   ├── app/
│   │   ├── (portal)/            # [H] cổng người dùng, tự phục vụ
│   │   ├── (admin)/             # [H] quản trị, phân quyền
│   │   └── (dashboard)/         # [D] bảng điều khiển vận hành
│   ├── components/
│   ├── lib/
│   └── types/                   # kiểu dữ liệu dùng chung, nguồn duy nhất
│
├── backend/                     # FastAPI
│   ├── app/
│   │   ├── auth/                # [H] định danh, phân quyền
│   │   ├── workflow/            # [P] máy trạng thái, quy tắc chuyển
│   │   ├── rules/               # [P] ràng buộc Poka-yoke, SLA
│   │   ├── events/              # [P→D] sinh và lưu nhật ký sự kiện
│   │   ├── analytics/           # [D] truy vấn chỉ số, xuất dữ liệu mở
│   │   ├── intelligence/        # [I] phân loại, RAG, khai phá quy trình
│   │   └── models/              # lược đồ dữ liệu
│   ├── alembic/                 # migration
│   └── tests/
│
├── infra/
│   ├── docker-compose.yml       # dựng toàn hệ thống bằng một lệnh
│   ├── .env.example             # biến môi trường mẫu, giá trị chạy được ngay
│   └── seed/                    # dữ liệu khởi tạo, tự nạp khi khởi động
│
└── docs/
```

**Nguyên tắc đặt tên thư mục backend**: theo không gian kiến trúc, không theo tầng
kỹ thuật. Nghĩa là `workflow/` chứa cả model, service, router liên quan tới quy
trình — thay vì tách thành `models/`, `services/`, `routers/` rồi rải logic khắp nơi.

---

## 5. Khuôn mẫu: cấu hình thay vì mã cứng

Đây là khuôn mẫu quan trọng nhất của dự án, xuất phát từ ràng buộc đề thi tháng 11.

**Quy tắc**: trạng thái, vai trò, ngưỡng SLA, danh mục chỉ số — tất cả nằm trong
**cấu hình hoặc bảng dữ liệu**, tuyệt đối không mã cứng trong mã nguồn.

| Thuộc kiến trúc (giữ nguyên khi đổi đề) | Thuộc nghiệp vụ (thay được bằng dữ liệu) |
|---|---|
| Cơ chế máy trạng thái và quy tắc chuyển | Tên và số lượng trạng thái |
| Hệ phân quyền theo vai trò | Danh sách vai trò |
| Cơ chế theo dõi SLA và cảnh báo | Ngưỡng thời gian từng loại yêu cầu |
| Quy trình truy xuất tri thức, cách lập chỉ mục | Nội dung kho tri thức |
| Khung bảng điều khiển, cách truy vấn | Danh mục chỉ số cụ thể |
| Cấu trúc nhật ký sự kiện, thuật toán khai phá | Tên các hoạt động trong quy trình |

Nếu tuân thủ, việc thích ứng với đề thi mới chỉ là thay dữ liệu khởi tạo.

**Kiểm tra nhanh**: nếu một chuỗi như `"Đang xử lý"` xuất hiện trong câu lệnh `if`
của mã nguồn, đó là vi phạm. Trạng thái phải tra từ bảng.

---

## 6. Khuôn mẫu: nhật ký sự kiện

Chưa cài đặt. Thiết kế đã thống nhất:

Mọi lần chuyển trạng thái trong không gian `P` **bắt buộc** phát sinh một bản ghi
vào nhật ký sự kiện, với cấu trúc tối thiểu:

| Trường | Ý nghĩa |
|---|---|
| `case_id` | Định danh hồ sơ, nối các sự kiện thuộc cùng một yêu cầu |
| `activity` | Tên hoạt động, ví dụ `Tiếp nhận`, `Phân công`, `Phê duyệt` |
| `timestamp` | Mốc thời gian, **luôn lưu theo UTC** |
| `actor` | Người hoặc hệ thống thực hiện |
| `from_state` / `to_state` | Trạng thái trước và sau |

Nhật ký này là tài sản quý nhất của hệ thống: nó nuôi bảng điều khiển ở `D` và
thuật toán khai phá quy trình ở `I`.

**Lưu ý về múi giờ**: lưu UTC là bắt buộc. Lưu giờ cục bộ sẽ làm sai lệch kết quả
khai phá quy trình khi so sánh giữa các bản ghi.

---

## 7. Khuôn mẫu: ràng buộc Poka-yoke

Chưa cài đặt. Nguyên tắc: chặn thao tác sai **tại điểm chạm đầu vào**, thay vì phát
hiện sau khi dữ liệu đã hỏng.

Ví dụ dự kiến:

- Không cho đóng hồ sơ nếu thiếu ghi chú xử lý
- Không cho phân công cho người đang vượt ngưỡng tải
- Không cho chọn ngày hoàn thành trong quá khứ
- Không cho chuyển trạng thái không có trong bảng quy tắc

Ràng buộc phải cài đặt ở **cả hai phía**: giao diện chặn để trải nghiệm tốt, dịch
vụ chặn để bảo đảm toàn vẹn. Chỉ chặn ở giao diện là không đủ.

---

## 8. Quy ước đặt tên và mã nguồn

### 8.1. Header giấy phép

Mọi tệp mã nguồn mới **bắt buộc** bắt đầu bằng:

```python
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
```

```typescript
// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
```

Thiếu header này bị trừ 5 điểm theo bảng chấm.

### 8.2. Thư viện bên thứ ba

- Khai báo qua trình quản lý gói, kèm tệp khóa phiên bản
- **Không** sao chép mã thư viện vào kho mã
- **Không** chỉnh sửa mã thư viện bên thứ ba. Cần đổi hành vi thì dùng cấu hình,
  plugin, hoặc lớp bọc
- Tệp khóa phiên bản (`package-lock.json`, `requirements.txt` ghim bằng `==`)
  **bắt buộc commit**, không đưa vào `.gitignore`

### 8.3. Ngôn ngữ

| Nội dung | Ngôn ngữ |
|---|---|
| Tên biến, hàm, lớp, tệp | Tiếng Anh |
| Chú thích trong mã | Tiếng Việt có dấu |
| Commit message | Tiếng Việt có dấu |
| Tài liệu | Tiếng Việt có dấu |
| Chuỗi hiển thị cho người dùng | Tiếng Việt có dấu |

---

## 9. Ngoài phạm vi

Không xây dựng những thứ sau vào mã nguồn ở giai đoạn hiện tại:

- Triển khai lên máy chủ thật hoặc dịch vụ đám mây
- Xác thực hai lớp, khôi phục mật khẩu qua thư điện tử
- Ứng dụng di động
- Đa ngôn ngữ giao diện
- Thanh toán, tích hợp hệ thống tài chính
- Tối ưu hiệu năng cho quy mô lớn — hệ thống chỉ cần chạy tốt ở quy mô trình diễn

Nếu một yêu cầu chạm vào danh sách này, dừng lại và trao đổi trước khi thực hiện.

---

## 10. Chiến lược đối phó với đề thi tháng 11

Đề thi chính thức công bố tháng 11/2026, chấm kho mã ngày 7–9/12, chung kết 10/12.

**Nguyên tắc**: mọi thứ xây dựng trước tháng 11 phải tái sử dụng được. Tách bạch
phần kiến trúc giữ nguyên và phần nghiệp vụ thay được — xem bảng ở mục 5.

**Hệ quả với `main`**: nhánh `main` luôn phải ở trạng thái dựng được và trình diễn
được, vì đó là thứ ban giám khảo nhìn thấy khi chấm kho mã. Đây là lý do tồn tại
của nhánh tích hợp `dev`.

---

## 11. Quy trình làm việc của tác nhân AI

Áp dụng cho mọi công việc trong kho mã này, bất kể công cụ nào đang chạy.

**Thứ tự đọc bắt buộc trước khi làm gì:**

1. `docs/PROJECT_STATE.md` — biết dự án đang ở đâu, vừa làm gì, đang vướng gì
2. `docs/ARCHITECTURE.md` (tệp này) — biết hệ thống hoạt động thế nào
3. `docs/ROADMAP.md` — biết việc tiếp theo là gì
4. `docs/adr/` — biết vì sao chọn công nghệ đó, tránh đề xuất lại thứ đã bác bỏ
5. `CLAUDE.md` — các ràng buộc vận hành, đặc biệt là quy tắc cấm tự chạy lệnh Git

**Sau đó:**

6. **Phân tích** yêu cầu — xác định chính xác tệp và khuôn mẫu nào bị ảnh hưởng.
   Nếu yêu cầu mâu thuẫn với một khuôn mẫu đã ghi hoặc chạm vào mục 9, **dừng lại
   và hỏi** thay vì tự quyết định.

7. **Thực hiện** — bám theo khuôn mẫu đã có. Ưu tiên mở rộng khuôn mẫu hiện tại hơn
   là phát minh khuôn mẫu mới.

8. **Không tự chạy** kiểm thử, máy chủ phát triển, hoặc lệnh triển khai trừ khi
   được yêu cầu rõ ràng. Sinh ra mã không đồng nghĩa với đã kiểm chứng mã chạy được.

9. **Không tự chạy bất kỳ lệnh Git nào ghi vào lịch sử** — commit, push, merge,
   tag, tạo nhánh. Soạn sẵn lệnh và nội dung để người dùng tự chạy. Lịch sử commit
   phải mang danh tính thật của con người. Xem `CLAUDE.md`.

10. **Trả về kết quả để rà soát** — tóm tắt tệp đã đổi và vì sao. Không coi công
    việc là xong chỉ vì mã biên dịch được.

11. **Cập nhật tệp này** nếu thay đổi vừa rồi tạo ra hoặc sửa đổi một khuôn mẫu —
    ngay trong cùng công việc, không để lại sau.

---

## 12. Khi nào cập nhật tệp này

| Tình huống | Cập nhật? |
|---|---|
| Sửa lỗi bên trong một khuôn mẫu đã có | **Không** — mô tả khuôn mẫu vẫn đúng |
| Thêm trường mới vào lược đồ mà mã khác cần biết | **Có** — cập nhật mục tương ứng |
| Đưa vào một cơ chế mới, hoặc đổi cách hai thành phần giao tiếp | **Có** |
| Chốt một nền tảng nguồn mở sau khảo sát | **Có** — cập nhật mục 3, đồng thời tạo bản ghi quyết định trong `docs/adr/` |
| Thêm một trang hoặc một điểm cuối API mới | **Có** — bổ sung vào mục 4 |
| Thay đổi thuần túy về giao diện hoặc câu chữ | **Không** |
| Thêm kế hoạch cho giai đoạn sau | **Không** — kế hoạch thuộc về `ROADMAP.md` |
| Cập nhật tiến độ tuần | **Không** — tiến độ thuộc về `PROJECT_STATE.md` |

**Tự kiểm tra trước khi kết thúc mỗi công việc**: nếu một người hoặc một tác nhân AI
mở phiên làm việc mới ngay bây giờ và chỉ đọc tệp này, họ có hiểu đúng hành vi hiện
tại của hệ thống không, hay sẽ tưởng nhầm một khuôn mẫu đã không còn tồn tại?

Nếu là vế sau, cập nhật tệp trước khi kết thúc công việc.
