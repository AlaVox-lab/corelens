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

**Giai đoạn hiện tại**: `v0.2.0` — Giai đoạn 2, không gian `H` và `P`.

Đã cài đặt: hạ tầng sáu dịch vụ dựng bằng một lệnh, lược đồ cấu hình đầy đủ của
engine máy trạng thái, **điểm chuyển trạng thái duy nhất** và **nhật ký sự kiện**.
Chưa cài đặt: cổng gửi yêu cầu, buồng lái vận hành, toàn bộ không gian `I`. Những
mục còn ở dạng thiết kế đều ghi rõ *"chưa cài đặt"* ngay đầu mục.

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
| Lưu trữ đối tượng | SeaweedFS `4.45` | Apache-2.0 | `core`. Lưu tệp đính kèm, giao tiếp qua S3 API chuẩn. Xem [ADR-0002](adr/0002-chon-nen-tang-luu-tru-doi-tuong.md) |
| Kinh doanh thông minh | Apache Superset `6.1.0` | Apache-2.0 | Không gian `D`. Bảng điều khiển phân tích, chỉ đọc, nhúng vào cổng qua guest token. Xem [ADR-0003](adr/0003-chon-nen-tang-bi.md) |
| Quản trị CSDL | Chờ quyết định | | Hai phương án: pgAdmin 4 (chạy trong Compose) hoặc DBeaver Community |

Cả bảy thành phần đã chốt đều dùng giấy phép nhóm dễ dãi, tương thích hoàn toàn với
MIT của sản phẩm.

**Hai loại bảng điều khiển, đừng lẫn lộn.** *Buồng lái vận hành* — duyệt, phân công,
leo thang — có tương tác và ghi dữ liệu, thuộc nhóm **tự viết** trong cổng Next.js.
*Bảng điều khiển phân tích* trên nhật ký sự kiện chỉ đọc, thuộc nhóm **lắp ghép** và do
Superset đảm nhiệm. Đây là kiến trúc lai, xem ADR-0003.

Vai trò nghiệp vụ **không khai báo trong mã nguồn**. Keycloak nạp toàn bộ realm gồm
vai trò, ứng dụng khách, nhóm và người dùng từ một tệp JSON lúc khởi động, nên việc đổi
bộ vai trò khi đề thi công bố chỉ là thay dữ liệu. Đây là một trường hợp cụ thể của
khuôn mẫu ở mục 5.

**Cách hai không gian nối vào nhau.** Keycloak là nguồn sự thật về *ai mang vai trò gì
và thuộc phòng nào*; bảng `transitions` là nguồn sự thật về *vai trò nào đi được cạnh
nào*. Hàm `actor_from_claims` ở `backend/app/auth/identity.py` là chỗ duy nhất dịch
giữa hai ngôn ngữ đó. Nhờ vậy engine ở không gian `P` không biết Keycloak tồn tại, và
đổi nền tảng định danh sẽ không đụng tới một dòng nào của engine.

Phòng ban lấy từ **nhóm** chứ không từ thuộc tính người dùng: nhóm đúng ngữ nghĩa hơn,
có sẵn giao diện quản lý trong Keycloak, và cho phép một người thuộc nhiều phòng. Token
mang đường dẫn đầy đủ như `/phong-ban/it`; tiền tố là **cấu hình được**, vì doanh nghiệp
triển khai có thể tổ chức cây nhóm theo cách khác.

**Dịch vụ ứng dụng tự kiểm chữ ký token, không gọi ngược sang Keycloak ở mỗi yêu cầu.**
Khóa công khai tải một lần qua JWKS rồi giữ trong bộ nhớ; Keycloak xoay khóa thì token
mới mang `kid` lạ và thư viện tự đi lấy lại. Keycloak vì thế nằm ngoài đường đi nóng —
nó chậm hay khởi động lại cũng không làm cả hệ thống đứng.

**Một Keycloak, hai địa chỉ — và đây là chỗ dễ mất thời gian nhất.** Trình duyệt đi qua
`localhost:8080`, còn container đi qua `keycloak:8080`. Nếu không cố định `KC_HOSTNAME`,
token lấy theo hai đường sẽ mang hai giá trị `iss` khác nhau và dịch vụ từ chối một nửa
số token. Cấu hình đang dùng: `KC_HOSTNAME` cố định địa chỉ công khai, còn
`KC_HOSTNAME_BACKCHANNEL_DYNAMIC` cho phép tài liệu discovery trả địa chỉ nội bộ cho
các điểm cuối máy chủ gọi. Keycloak tự tách đúng hai chiều — `authorization_endpoint`
và `end_session_endpoint` ra địa chỉ công khai cho trình duyệt, `token_endpoint` và
`jwks_uri` ra địa chỉ nội bộ cho máy chủ.

Cùng một gốc vấn đề ở phía cổng: trong container, máy chủ Next.js nghe ở `0.0.0.0`, nên
mọi chuyển hướng dựng từ địa chỉ yêu cầu sẽ trỏ về `http://0.0.0.0:3000` và trình duyệt
đi tới đó sẽ lạc. Địa chỉ công khai của cổng vì vậy phải khai riêng bằng biến môi trường,
không được suy ra.

**Token không bao giờ tới trình duyệt.** Cổng giữ chúng trong một cookie `httpOnly` đã
mã hóa và tự gắn vào header khi gọi dịch vụ — khuôn mẫu cổng chặn trước. Mã lạ lọt vào
trang cũng không đọc được token, khác hẳn với việc để token trong `localStorage`.

**Không gian `P` không dùng nền tảng ngoài.** Engine máy trạng thái do nhóm tự viết, với
trạng thái và quy tắc chuyển lưu trong bảng dữ liệu. Quyết định này được đưa ra sau khi
khảo sát và dựng thử bốn ứng viên — xem
[ADR-0004](adr/0004-tu-viet-engine-may-trang-thai.md). Lý do cốt lõi: nhật ký sự kiện là
nơi tạo ra giá trị của đề tài, và không nền tảng nào sinh sẵn nhật ký đúng lược đồ mà
`I` cần, nên nhóm phải tự viết lớp đó dù có lắp engine hay không.

### 3.2. Chờ khảo sát

Bộ công nghệ nền mới là hạ tầng ứng dụng, chưa cấu thành hệ sinh thái DX-Lab theo
yêu cầu Open-Core. Ba nhóm thành phần sau cần khảo sát và ghi kết quả vào
`docs/adr/`:

| Không gian | Thành phần | Ghi chú khảo sát |
|---|---|---|
| `H` | Hệ thống quản trị tri thức | Vừa phục vụ người dùng, vừa là nguồn dữ liệu cho truy xuất tri thức ở `I` |
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
├── backend/                     # FastAPI — dịch vụ ứng dụng
│   ├── app/
│   │   ├── main.py              # điểm vào, điểm cuối kiểm tra sức khỏe
│   │   ├── config.py            # cấu hình từ biến môi trường
│   │   ├── db.py                # kết nối dùng chung
│   │   ├── models/              # lược đồ dữ liệu, dùng chung mọi không gian
│   │   ├── workflow/            # [P] ĐIỂM CHUYỂN TRẠNG THÁI DUY NHẤT
│   │   ├── rules/               # [P] ràng buộc Poka-yoke và đồng hồ SLA
│   │   ├── events/              # [P→D] nơi ghi nhật ký sự kiện duy nhất
│   │   ├── auth/                # [H] kiểm token OIDC, dịch claim thành Actor
│   │   ├── analytics/           # [D] chưa cài đặt
│   │   └── intelligence/        # [I] chưa cài đặt
│   ├── alembic/                 # migration cho bảng do ứng dụng sở hữu
│   ├── tests/
│   └── requirements.txt         # TỆP KHÓA PHIÊN BẢN, bắt buộc commit
├── frontend/                    # Next.js — cổng người dùng
│   ├── app/
│   │   ├── api/auth/            # [H] ba chặng của luồng đăng nhập OIDC
│   │   ├── yeu-cau/             # [H] cổng gửi yêu cầu — ba màn hình của #44
│   │   ├── globals.css          # token màu OKLCH, ba chế độ sáng/tối/in
│   │   └── layout.tsx           # phông chữ tải lúc dựng, không gọi ra ngoài
│   ├── components/              # bộ phận dùng lại giữa nhiều màn
│   ├── lib/                     # gọi dịch vụ, phiên, định dạng, siêu dữ liệu
│   └── package-lock.json        # TỆP KHÓA PHIÊN BẢN, bắt buộc commit
├── docs/
│   ├── adr/                     # năm bản ghi quyết định kiến trúc
│   ├── ARCHITECTURE.md          # tệp này
│   ├── PROJECT_STATE.md         # trạng thái hiện tại, cập nhật hàng tuần
│   ├── ROADMAP.md               # lộ trình tới tháng 12
│   ├── process-flow.md          # sơ đồ trạng thái, nguồn của dữ liệu khởi tạo
│   ├── dependencies.md          # danh mục phụ thuộc và giấy phép
│   └── *-survey.md              # bốn tài liệu khảo sát Open-Core
├── infra/                       # dựng cả cụm bằng một lệnh
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── keycloak/                # realm nạp lúc khởi động: vai trò là dữ liệu
│   ├── seaweedfs/
│   ├── superset/                # ảnh dẫn xuất, ảnh gốc thiếu trình điều khiển
│   ├── postgres/init/           # LƯỢC ĐỒ — phần thuộc kiến trúc
│   │   ├── 01-tao-cac-database.sh
│   │   ├── 02-luoc-do-quy-trinh.sql
│   │   └── 03-nap-du-lieu-khoi-tao.sh
│   └── seed/                    # DỮ LIỆU — phần doanh nghiệp triển khai sửa
│       ├── 01-quy-tac-quy-trinh.sql
│       ├── 02-co-cau-to-chuc.sql
│       └── 99-kiem-tra-tinh-nhat-quan.sql
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

Cấu trúc đầy đủ khi các không gian còn lại được xây xong. Phần đã tồn tại xem mục 4.1;
phần dưới đây ghi trước để tránh mỗi người đặt một kiểu.

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

Đây là khuôn mẫu quan trọng nhất của dự án. Ban đầu nó xuất phát từ ràng buộc đề thi
tháng 11, nhưng từ 10/09/2026 nó được nâng thành **mục tiêu sản phẩm** — xem mục 5.1.

**Quy tắc**: trạng thái, vai trò, phòng ban, loại yêu cầu, ngưỡng SLA, danh mục chỉ số —
tất cả nằm trong **cấu hình hoặc bảng dữ liệu**, tuyệt đối không mã cứng trong mã nguồn.

| Thuộc kiến trúc (giữ nguyên khi đổi đề) | Thuộc nghiệp vụ (thay được bằng dữ liệu) |
|---|---|
| Cơ chế máy trạng thái và quy tắc chuyển | Tên và số lượng trạng thái |
| Hệ phân quyền theo vai trò | Danh sách vai trò |
| Cơ chế định tuyến yêu cầu | **Danh sách phòng ban, loại yêu cầu, và bảng ánh xạ loại → phòng ban** |
| Cơ chế theo dõi SLA và cảnh báo | Ngưỡng thời gian từng loại yêu cầu |
| Quy trình truy xuất tri thức, cách lập chỉ mục | Nội dung kho tri thức |
| Khung bảng điều khiển, cách truy vấn | Danh mục chỉ số cụ thể |
| Cấu trúc nhật ký sự kiện, thuật toán khai phá | Tên các hoạt động trong quy trình |

Nếu tuân thủ, việc thích ứng với đề thi mới chỉ là thay dữ liệu khởi tạo.

### 5.1. Vì sao đây là mục tiêu sản phẩm, không chỉ là biện pháp đối phó

Buổi trao đổi với giảng viên hướng dẫn ngày 10/09/2026 đặt thêm một yêu cầu: sản phẩm phải
để **một doanh nghiệp bất kỳ tải về rồi tự tùy biến** phòng ban, loại yêu cầu và quy trình
theo đặc thù của họ, mà không cần sửa mã.

Điều này đổi bản chất của khuôn mẫu. Trước đây nó là cách giảm rủi ro khi đề thi công bố
muộn; giờ nó là **một tính năng người dùng thấy được**, và là lý do tồn tại của vai trò
`administrator` trong bộ năm vai trò.

Hệ quả cụ thể khi viết mã:

- Mọi danh mục nghiệp vụ đều có bảng riêng, không phải hằng số trong mã hay kiểu liệt kê
- Có màn hình quản trị để sửa các bảng đó, không bắt người dùng đụng vào cơ sở dữ liệu
- Dữ liệu khởi tạo chỉ là **ví dụ mẫu**, không phải phần cứng của sản phẩm

Danh sách đầy đủ các chiều cấu hình được ghi ở [`process-flow.md`](process-flow.md) mục 7.

**Kiểm tra nhanh**: nếu một chuỗi như `"Đang xử lý"` xuất hiện trong câu lệnh `if`
của mã nguồn, đó là vi phạm. Trạng thái phải tra từ bảng.

### 5.2. Lược đồ cấu hình đã hiện thực

Mười một bảng, định nghĩa ở `infra/postgres/init/02-luoc-do-quy-trinh.sql`, chia ba nhóm:

| Nhóm | Bảng | Vai trò |
|---|---|---|
| Phiên bản | `rule_sets` | Hồ sơ cũ chạy theo quy tắc cũ khi quản trị viên sửa luồng giữa chừng |
| Máy trạng thái | `states` · `transitions` · `roles` · `transition_roles` · `guards` · `transition_guards` | Trạng thái, cạnh chuyển, ma trận phân quyền, ràng buộc Poka-yoke theo cạnh |
| Cơ cấu tổ chức | `departments` · `request_types` · `request_type_routing` · `priorities` | Phần doanh nghiệp triển khai sửa đầu tiên |

**Lược đồ và dữ liệu để tách nhau có chủ ý.** Lược đồ nằm trong `infra/postgres/init/`
vì nó thuộc kiến trúc; dữ liệu khởi tạo nằm trong `infra/seed/` vì nó chỉ là ví dụ mẫu
mà công ty khác sẽ xóa đi khai lại. Lẫn hai thứ vào nhau thì người triển khai phải dò
giữa hai loại nội dung khác hẳn nhau.

**Ba lớp bảo vệ, không lớp nào nằm trong mã ứng dụng:**

1. **Khóa ngoại** chặn cạnh trỏ tới trạng thái không tồn tại. Thêm một mẹo nhỏ: cột kỹ
   thuật `transitions.from_is_terminal` luôn bằng `FALSE` và tham chiếu tới
   `states (rule_set_id, code, is_terminal)`, nên **không thể tạo cạnh rời khỏi một
   trạng thái đóng**. Dữ liệu khởi tạo không bao giờ nhắc tới cột này
2. **Chỉ mục duy nhất từng phần** bảo đảm mỗi bộ quy tắc có đúng một trạng thái bắt đầu,
   mỗi lúc có đúng một bộ quy tắc kích hoạt, mỗi loại yêu cầu có đúng một phòng ban mặc định
3. **Kiểm tra mức đồ thị** trong `infra/seed/99-kiem-tra-tinh-nhat-quan.sql` bắt những
   lỗi mà từng dòng vẫn hợp lệ nhưng cả luồng thì hỏng: ngõ cụt không phải trạng thái
   đóng, trạng thái không tới được từ điểm vào, cạnh không vai trò nào đi được. Sai một
   trong ba thì **cụm Docker dừng khởi động**, thay vì chạy với luồng hỏng rồi để một hồ
   sơ thật mắc kẹt mới lộ ra

Hai ràng buộc Poka-yoke quan trọng nhất **không có dòng dữ liệu nào** vì chúng được thực
thi bằng sự vắng mặt: *đã nhận là không trả về* và *chỉ hủy trước khi vào xử lý*. Không
phải "không nên đi", mà là "không có đường mà đi".

Cột `is_initial` đáng chú ý riêng: nhờ nó mà mã nguồn hỏi *"trạng thái bắt đầu là gì"*
thay vì viết `if state == "submitted"`. Mỗi cột kiểu này là một câu lệnh `if` không bao
giờ phải viết.

---

## 6. Khuôn mẫu: nhật ký sự kiện

**Đã cài đặt** — bảng `event_log`, mô hình ở `backend/app/models/case.py`, nơi ghi
duy nhất ở `backend/app/events/log.py`.

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
khai phá quy trình khi so sánh giữa các bản ghi. Cột dùng kiểu `TIMESTAMPTZ` và mốc
thời gian do PostgreSQL tự điền bằng `now()` — một đồng hồ duy nhất cho cả cụm, thay
vì mỗi tiến trình một đồng hồ lệch nhau vài giây.

Ba quyết định cài đặt đáng ghi lại:

**Nhật ký chỉ ghi thêm.** Một trigger PL/pgSQL chặn mọi `UPDATE` và `DELETE` trên
`event_log`. Ràng buộc đặt ở tầng cơ sở dữ liệu chứ không ở tầng ứng dụng, vì
Superset, công cụ quản trị và mọi kết nối `psql` đều đi vòng qua tầng ứng dụng. Lịch
sử sửa được thì không còn là lịch sử.

**Tạo hồ sơ không sinh sự kiện.** Tạo hồ sơ không phải một lần *chuyển* trạng thái —
không có trạng thái nào trước nó, và không có cạnh nào trong bảng `transitions` đi
vào trạng thái đầu. Mốc bắt đầu của hồ sơ là cột `requests.created_at`. Khi xuất dữ
liệu cho khai phá quy trình, tầng `D` dựng thêm một sự kiện mở đầu từ cột đó nếu công
cụ phân tích cần. Cách này tránh phải bịa một mã hoạt động không có trong dữ liệu.

**Thêm cột `note`** ngoài sáu trường bắt buộc, chứa lý do của những cạnh mang cờ
`requires_note` — từ chối vì sai chuyên môn, đóng hồ sơ khi không phòng nào nhận, mở
lại vì chưa đạt. Lý do thuộc về *lần chuyển*, không thuộc về hồ sơ: mỗi lần từ chối
có lý do riêng của nó.

### 6.1. Cơ chế bảo đảm: một cửa duy nhất

Nhật ký chỉ có giá trị nếu **không bao giờ thiếu bản ghi**. Một nhật ký thủng làm sai
lệch kết quả khai phá quy trình, và khi đó điểm sáng tạo của đề tài mất giá trị.

Cơ chế bảo đảm điều này: **mọi lần đổi trạng thái đi qua đúng một điểm trong mã**, và
điểm đó lần lượt tra bảng quy tắc chuyển, kiểm quyền theo vai trò, chạy ràng buộc
Poka-yoke, ghi nhật ký, rồi mới cập nhật trạng thái hồ sơ.

Không tồn tại đường nào khác để đổi trạng thái. Bất kỳ chỗ nào cập nhật trạng thái trực
tiếp đều là vi phạm khuôn mẫu, kể cả khi nó "chỉ sửa một trường".

**Đã cài đặt** — `backend/app/workflow/engine.py`, hàm `perform_transition`. Cách soát
lại khuôn mẫu này khi review:

```bash
grep -rn 'current_state\s*=' backend/app --include='*.py' | grep -v '=='
```

Kết quả chỉ được có hai dòng, cả hai trong `engine.py`: một ở `create_case` đặt trạng
thái đầu, một ở `perform_transition` đặt trạng thái đích. Dòng thứ ba ở bất kỳ tệp nào
khác là một lần chuyển không có bản ghi nhật ký.

Hai chi tiết cài đặt giữ cho bảo đảm này không rò rỉ:

- **Khóa dòng hồ sơ** bằng `SELECT ... FOR UPDATE` ngay đầu hàm. Không có nó, hai yêu
  cầu đồng thời cùng đọc trạng thái cũ rồi cùng ghi nhật ký
- **Danh sách trắng các trường được đặt.** Một lần chuyển chỉ đặt được bốn trường quyết
  định; `current_state` và mọi trường `suggested_*` đều nằm ngoài. Nhờ vậy không ai
  dùng lần chuyển trạng thái làm cửa sau để sửa trường bất kỳ

Quyết định tự viết engine máy trạng thái thay vì lắp ghép nền tảng có sẵn xuất phát chính
từ yêu cầu này — xem [ADR-0004](adr/0004-tu-viet-engine-may-trang-thai.md).

---

## 7. Khuôn mẫu: ràng buộc Poka-yoke

**Đã cài đặt** — `backend/app/rules/guards.py`. Nguyên tắc: chặn thao tác sai **tại
điểm chạm đầu vào**, thay vì phát hiện sau khi dữ liệu đã hỏng.

Ràng buộc chia hai loại, và loại thứ nhất mạnh hơn hẳn:

**Loại cấu trúc — thực thi bằng sự VẮNG MẶT.** Không cần dòng mã nào canh cửa, vì
không có cửa. *"Đã nhận là không trả về"* đơn giản là bảng `transitions` không có
dòng nào đi từ `in-progress` ngược về phía trước. *"Chỉ hủy trước khi vào xử lý"*
là cạnh hủy chỉ xuất phát từ bốn trạng thái đầu. Không phải *không nên đi*, mà là
**không có đường mà đi**.

**Loại kiểm tra lúc chạy — khai trong bảng, cài trong mã.** Bảng `guards` khai mã
ràng buộc, bảng `transition_guards` nối mã với từng cạnh, `guards.py` cài hàm tương
ứng. Nhờ tách như vậy, gắn thêm một ràng buộc đã có cho một cạnh khác chỉ là thêm một
dòng dữ liệu; chỉ khi cần một *loại* ràng buộc mới mới phải viết mã.

Điểm quan trọng: mã ràng buộc có trong bảng mà thiếu hàm cài đặt sẽ làm engine **từ
chối chuyển trạng thái**, không im lặng bỏ qua. Im lặng cho qua sẽ biến một ràng buộc
nghiệp vụ thành vô hiệu mà không ai biết.

Còn một cách diễn đạt thứ ba, đặt ở tầng thấp nhất: **khóa ngoại và chỉ mục duy nhất
từng phần** trong lược đồ — xem mục 5.2. Mỗi tầng bắt một loại sai khác nhau, và tầng
càng thấp thì càng khó lách.

Ví dụ dự kiến:

- Không cho đóng hồ sơ nếu thiếu ghi chú xử lý
- Không cho phân công cho người đang vượt ngưỡng tải
- Không cho chọn ngày hoàn thành trong quá khứ
- Không cho chuyển trạng thái không có trong bảng quy tắc

Ràng buộc phải cài đặt ở **cả hai phía**: giao diện chặn để trải nghiệm tốt, dịch
vụ chặn để bảo đảm toàn vẹn. Chỉ chặn ở giao diện là không đủ.

### 7.1. Đồng hồ SLA và tự leo thang

**Đã cài đặt** — `backend/app/rules/sla.py` và `backend/app/workflow/escalation.py`.

ADR-0004 ghi rõ: chọn tự viết engine đồng nghĩa nhận trách nhiệm tự làm bộ đếm thời
gian, thứ mà một nền tảng workflow có sẵn sẽ cho không. Đây là món nợ đó.

**Ba cột thay cho một mốc hạn chót.** `requests` giữ `sla_running_seconds`,
`sla_paused_seconds` và `sla_segment_since`. Lý do không tính sẵn một mốc hạn chót:
đồng hồ dừng rồi chạy lại nhiều lần trong đời một hồ sơ, nên mốc cố định sẽ sai ngay
lần đầu người dùng bị hỏi thêm thông tin.

**Trạng thái nào làm đồng hồ chạy là dữ liệu, không phải mã.** Cột `states.sla_running`
trả lời cả hai câu — đồng hồ bắt đầu từ đâu, và dừng ở đâu — nên mã nguồn không phải
viết `if state == "in-progress"`. Hiện chỉ `in-progress` và `escalated` bật cờ này.

Hệ quả nghiệp vụ có chủ đích: **thời gian ở `awaiting-info` không tính vào SLA**, vì
người xử lý không nên bị phạt khi người tạo chậm trả lời. Nhưng tổng thời gian dừng
vẫn cộng dồn vào `sla_paused_seconds`, để khai phá quy trình phát hiện ai lạm dụng
cách hỏi thêm thông tin để dừng đồng hồ. Muốn tính vào thì bật cờ cho `awaiting-info` —
sửa một giá trị trong `infra/seed/`, không đụng mã.

**Leo thang cũng đi qua điểm chuyển trạng thái duy nhất.** Bộ quét không tự đặt
`current_state`; nó gọi `perform_transition` với tác nhân hệ thống. Nếu đi tắt cho
nhanh thì nhật ký sẽ thiếu đúng những bản ghi thú vị nhất — các lần trễ hạn — và khai
phá quy trình mất khả năng chỉ ra điểm nghẽn.

**Trạng thái đích cũng không viết cứng.** Bộ quét tra bảng `transitions` tìm cạnh mang
cờ `is_system` xuất phát từ trạng thái hiện tại. Nhờ vậy hồ sơ đã leo thang không bị
nhặt lại mỗi vòng — từ `escalated` không còn cạnh hệ thống nào — mà không cần thêm một
cột *"đã leo thang chưa"*. Cơ chế tự giới hạn bằng chính cấu trúc dữ liệu.

Hai phép kiểm tra ở `infra/seed/99-kiem-tra-tinh-nhat-quan.sql` canh bộ quy tắc: phải
có ít nhất một trạng thái chạy đồng hồ, và trạng thái kết thúc không được chạy đồng hồ.
Thiếu điều kiện đầu thì cơ chế leo thang thành mã chết mà không ai biết.

### 7.2. Giao diện không giữ bản sao của bộ quy tắc

**Đã cài đặt** — `frontend/app/yeu-cau/`, từ #44.

Một cổng người dùng bình thường sẽ có đâu đó một bảng đại loại *"trạng thái nào thì
hiện nút nào"*. Cổng này **không có bảng đó**, và điều đó là cố ý.

Điểm cuối `GET /requests/{id}` trả về `allowed_transitions` — danh sách cạnh mà chính
người đang đăng nhập đi được từ trạng thái hiện tại của hồ sơ, do
`allowed_transitions()` sinh ra từ bảng `transitions` và ma trận phân quyền. Giao diện
dựng nút bấm thẳng từ danh sách đó, lấy cả nhãn chữ (`activity_label`) và cờ bắt buộc
ghi lý do (`requires_note`). Không có cạnh thì không có nút.

Đây không phải chuyện gọn mã. Bản thiết kế giao diện của #44 có một bảng như vậy, và
nó **vẽ sai hai chỗ**: đặt nút *"Hủy yêu cầu"* ở `in-progress` và `escalated`, trong
khi dữ liệu không có cạnh nào đi từ hai trạng thái đó tới `cancelled` — đúng ràng buộc
Poka-yoke *"chỉ hủy được trước khi phòng ban bắt tay vào việc"*. Chép bảng ấy vào mã
nguồn sẽ dựng ra hai cái nút bấm vào là báo lỗi. Lấy nút từ API thì hai nút sai tự
biến mất, và không có đường nào cho chúng quay lại.

Ranh giới cần giữ: giao diện **được phép** giữ siêu dữ liệu thuần thị giác — trạng
thái nào mang dấu hiệu gì, thuộc họ màu nào (`frontend/lib/trang-thai.ts`). Bảng
`states` mô tả quy trình, không mô tả cách vẽ quy trình, nên những thứ đó không có chỗ
trong cơ sở dữ liệu. Nhưng bảng ấy phải có **phương án lùi** cho mã trạng thái lạ:
doanh nghiệp thêm một trạng thái vào bộ quy tắc phải thấy nó hiện ra ngay, dù chưa ai
gán dấu hiệu cho nó. Một giao diện vỡ vì dữ liệu hợp lệ là lỗi của giao diện.

Nửa còn lại của Poka-yoke vẫn nằm ở engine: một cạnh hiện ra trên màn hình vẫn bị kiểm
lại khi yêu cầu thật gửi lên. Chặn ở giao diện thôi thì không đủ, vì ai cũng gọi thẳng
API được.

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
