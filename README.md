# dx-os-lab

> Trạm thực hành số (DX-Lab) mô phỏng Hệ điều hành Doanh nghiệp số theo kiến trúc
> Open-Core — Dự án dự thi Phần mềm nguồn mở, Olympic Tin học Sinh viên Việt Nam 2026.

[![Giấy phép: MIT](https://img.shields.io/badge/Gi%E1%BA%A5y%20ph%C3%A9p-MIT-blue.svg)](LICENSE)

---

## Giới thiệu

Phần lớn chương trình chuyển đổi số hiện nay rơi vào cái bẫy "ảo tưởng công nghệ":
doanh nghiệp mua nhiều phần mềm nhưng nhân sự vẫn làm việc theo thói quen cũ, dữ
liệu bị giam trong các ốc đảo thông tin rời rạc.

**dx-os-lab** giải quyết một lát cắt cụ thể của vấn đề đó: **cổng vận hành yêu cầu
nội bộ**. Hệ thống tiếp nhận và điều phối tập trung mọi loại yêu cầu trong doanh
nghiệp — sự cố thiết bị, cấp quyền phần mềm, giấy xác nhận nhân sự, đề xuất mua vật
tư — thay cho tình trạng nhân viên gửi yêu cầu rải rác qua nhiều kênh, không có luồng
xử lý thống nhất, không ai biết yêu cầu đang ở đâu.

### Điểm khác biệt: vòng phản hồi tự soi quy trình

Doanh nghiệp thiết kế quy trình trên giấy, nhưng quy trình thực sự vận hành luôn khác
với thiết kế. Nhân sự bỏ bước, quay ngược trạng thái, đi đường tắt. Không tổ chức nào
biết chính xác điều này vì không ai đo lường.

Mọi lần chuyển trạng thái trong hệ thống đều ghi một bản ghi vào nhật ký sự kiện có
cấu trúc. Từ nhật ký này, hệ thống **tự khai phá lại quy trình thực tế đang diễn ra**
và đối chiếu với quy trình đã thiết kế, chỉ ra điểm nghẽn, nhánh lệch chuẩn và các
bước tiêu tốn nhiều thời gian nhất.

---

## Kiến trúc H-P-D-I

Hệ thống tổ chức theo bốn không gian chức năng do đề bài quy định. Bốn không gian
này phải xây dựng **theo thứ tự** — không thể tự động hóa ở `I` khi `P` chưa có ràng
buộc và `D` chưa chuẩn hóa.

| | Không gian | Trách nhiệm |
|---|---|---|
| **H** | Nhân sự | Định danh tập trung, phân quyền theo vai trò, cổng tự phục vụ, kho tri thức |
| **P** | Quy trình | Máy trạng thái, luồng phê duyệt, ràng buộc Poka-yoke, theo dõi SLA |
| **D** | Dữ liệu | Nguồn sự thật duy nhất, nhật ký sự kiện, bảng điều khiển, xuất dữ liệu mở |
| **I** | Trí tuệ nhân tạo | Phân loại tự động, truy xuất tri thức, khai phá quy trình |

**Nguyên tắc bất di dịch**: tầng `I` chỉ ghi vào các trường gợi ý, con người giữ toàn
quyền quyết định. Mọi kết quả từ AI đều phải qua một bước xác nhận, và luôn có đường
điều chỉnh thủ công.

---

## Bộ công nghệ

| Tầng | Công nghệ | Giấy phép |
|---|---|---|
| Giao diện | Next.js `16.3.5` (React `19.3.0`) | MIT |
| Dịch vụ ứng dụng | FastAPI `0.141.1` (Python `3.13`) | MIT |
| Cơ sở dữ liệu | PostgreSQL `16` | PostgreSQL License |
| Đóng gói | Docker + Docker Compose | Apache-2.0 |

Bốn nền tảng Open-Core đã chốt, mỗi quyết định có một bản ghi trong
[`docs/adr/`](docs/adr/):

| Không gian | Nền tảng | Giấy phép | Cách tích hợp |
|---|---|---|---|
| `H` | Keycloak `26.7.3` | Apache-2.0 | Dịch vụ độc lập qua OIDC |
| `P` | **Tự viết engine máy trạng thái** | MIT | Trạng thái và quy tắc chuyển nằm trong bảng dữ liệu |
| `D` | Apache Superset `6.1.0` | Apache-2.0 | Dịch vụ độc lập, chỉ đọc, nhúng qua guest token |
| `core` | SeaweedFS `4.45` | Apache-2.0 | Dịch vụ độc lập qua S3 API |

Ba mảng còn đang khảo sát: quản trị tri thức cho `H`, cơ sở dữ liệu véc-tơ và khung
LLM cho `I`, thư viện khai phá quy trình cho `I`.

---

## Bản đồ tài liệu

Đọc theo thứ tự này khi bắt đầu làm việc với dự án:

| Thứ tự | Tài liệu | Trả lời câu hỏi |
|---|---|---|
| 1 | [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) | Dự án đang ở đâu? Vừa làm gì? Đang vướng gì? |
| 2 | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Hệ thống được tổ chức thế nào và vì sao? |
| 3 | [`docs/ROADMAP.md`](docs/ROADMAP.md) | Việc tiếp theo là gì? |
| 4 | [`docs/adr/`](docs/adr/) | Vì sao chọn công nghệ đó? |
| 5 | [`CONTRIBUTING.md`](CONTRIBUTING.md) | Quy trình làm việc và quy ước mã nguồn |
| 6 | [`CLAUDE.md`](CLAUDE.md) | Ràng buộc dành cho tác nhân AI |

Ngoài ra: [`docs/dependencies.md`](docs/dependencies.md) — danh mục phụ thuộc kèm
giấy phép · [`CHANGELOG.md`](CHANGELOG.md) — nhật ký thay đổi, sinh tự động từ lịch
sử commit.

---

## Trạng thái hiện tại

**Phiên bản `v0.2.0` — Giai đoạn 2: Không gian `H` và `P`**

Giai đoạn khảo sát và thiết kế đã khép. Kho mã có bộ quy chuẩn, hệ thống tài liệu,
bốn bản ghi quyết định kiến trúc, hạ tầng dựng được bằng một lệnh, và **lược đồ cấu
hình đầy đủ của engine máy trạng thái**. Xem
[`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) để biết tiến độ và việc tiếp theo.

---

## Cài đặt và dựng từ mã nguồn

> Cụm sáu dịch vụ dựng được bằng một lệnh. Cổng gửi yêu cầu đã chạy được; buồng lái
> cho điều phối viên và người xử lý đang được xây dựng.

### Yêu cầu môi trường

| Thành phần | Yêu cầu |
|---|---|
| Docker Engine | 24 trở lên, kèm Docker Compose v2 |
| Git | bất kỳ phiên bản nào còn được hỗ trợ |
| Bộ nhớ trống | khoảng **2 GB** cho toàn cụm |
| Cổng cần trống | 3000 · 5432 · 8000 · 8080 · 8088 · 8333 |

### Ba bước

```bash
git clone https://github.com/AlaVox-lab/dx-os-lab.git
cd dx-os-lab/infra
cp .env.example .env
docker compose --env-file .env up -d --build
```

Mọi giá trị trong `.env.example` **chạy được ngay**, không cần sửa gì để dựng thử. Lần
đầu chạy mất vài phút vì phải tải ảnh chứa và dựng ảnh dẫn xuất cho Superset.

### Các dịch vụ sau khi dựng xong

| Dịch vụ | Địa chỉ | Tài khoản mặc định |
|---|---|---|
| **Cổng người dùng** | `http://localhost:3000` | chưa cần đăng nhập |
| **Dịch vụ ứng dụng** — tài liệu API | `http://localhost:8000/docs` | chưa cần đăng nhập |
| Keycloak — định danh | `http://localhost:8080` | `admin` / `admin` |
| Apache Superset — báo cáo | `http://localhost:8088` | `admin` / `admin` |
| SeaweedFS — lưu trữ tệp, S3 API | `http://localhost:8333` | xem `.env` |
| PostgreSQL | `localhost:5432` | xem `.env` |

Mở `http://localhost:3000` là biết ngay cụm có khỏe không: trang chủ báo trạng thái
từng tầng, kể cả việc bộ quy tắc quy trình đã nạp đủ mười trạng thái hay chưa. Cổng gửi
yêu cầu nằm ở `http://localhost:3000/yeu-cau`.

Lược đồ và dữ liệu khởi tạo của engine máy trạng thái nạp tự động lúc PostgreSQL khởi
tạo lần đầu. Nếu bộ quy tắc sai — có ngõ cụt, có trạng thái không tới được, có cạnh
không vai trò nào đi được — **cụm sẽ dừng khởi động** thay vì chạy với luồng hỏng.
Xem `infra/seed/`.

### Đăng nhập thử

Bấm **Đăng nhập bằng Keycloak** trên trang chủ. Realm `dx-os-lab` tự nạp lúc khởi động,
gồm năm vai trò nghiệp vụ, bốn nhóm phòng ban và sáu tài khoản mẫu — tất cả dùng mật
khẩu `matkhau123`:

| Tài khoản | Vai trò | Phòng ban |
|---|---|---|
| `an.nguyen` | Người tạo yêu cầu | — |
| `binh.tran` | Người phân loại | — |
| `dung.pham` | Người xét duyệt | Công nghệ thông tin |
| `cuong.le` | Người xử lý | Công nghệ thông tin |
| `ha.do` | Người xử lý | Nhân sự |
| `khanh.vo` | Quản trị viên | — |

Hai người xử lý ở hai phòng khác nhau là cố ý: nó cho thấy ràng buộc *chỉ người thuộc
phòng đang giữ hồ sơ mới thao tác được*. Ba vai trò còn lại không cần phòng ban.

Toàn bộ khai trong `infra/keycloak/realm-dx-os-lab.json` — thêm phòng ban hay đổi vai
trò là sửa tệp đó rồi dựng lại cụm, không đụng mã nguồn.

### Cổng gửi yêu cầu

Đăng nhập bằng `an.nguyen` rồi mở `http://localhost:3000/yeu-cau`. Ba màn hình:

| Màn | Địa chỉ | Việc làm được |
|---|---|---|
| Gửi yêu cầu | `/yeu-cau/moi` | Biểu mẫu ba bước: chọn loại, viết nội dung, xem lại rồi gửi |
| Hồ sơ của tôi | `/yeu-cau` | Danh sách hồ sơ đã gửi, kèm chú giải mười trạng thái |
| Chi tiết hồ sơ | `/yeu-cau/{số}` | Dòng thời gian đầy đủ và những thao tác làm được lúc này |

Ba điều đáng thử, vì chúng cho thấy bộ quy tắc đang thật sự điều khiển giao diện:

**Nút bấm đến từ dữ liệu, không từ mã nguồn.** Mở một hồ sơ ở trạng thái `Đang xử lý`
sẽ thấy dòng chữ *"Không có thao tác nào dành cho bạn"* — vì bảng `transitions` không
có cạnh nào đi từ đó tới `Đã hủy`. Thêm một dòng vào `infra/seed/01-quy-tac-quy-trinh.sql`
rồi dựng lại cụm là nút hiện ra, không sửa một dòng TypeScript nào.

**Người gửi không tự đặt mức ưu tiên.** Biểu mẫu không có ô đó, và lược đồ dữ liệu vào
cũng không nhận trường đó — gọi thẳng API kèm `priority_code` thì giá trị bị bỏ qua.
Ràng buộc Poka-yoke thực thi bằng sự vắng mặt, không bằng một câu cảnh báo.

**In thử bằng Ctrl+P.** Mười trạng thái phân biệt nhau bằng màu, nhưng mỗi trạng thái
còn mang một dấu hiệu riêng đặt trước nhãn (`○ ◐ ◌ ● ! ✓ ✕ ▲ ■ –`). Khi in, toàn bộ
màu rút về đen trắng và dấu hiệu vẫn phân biệt được từng trạng thái — cũng là thứ giúp
người không phân biệt được màu đọc được giao diện này.

### Theo dõi SLA

Dịch vụ ứng dụng chạy một bộ quét nền, mặc định mỗi 60 giây, tìm hồ sơ vượt ngưỡng SLA
rồi **tự leo thang** chúng. Ngưỡng khai theo từng loại yêu cầu trong
`infra/seed/02-co-cau-to-chuc.sql`; trạng thái nào làm đồng hồ chạy khai ở cột
`sla_running` trong `infra/seed/01-quy-tac-quy-trinh.sql`.

Muốn xem cơ chế hoạt động mà không phải chờ, hạ chu kỳ quét trong `.env`:

```bash
SLA_SCAN_INTERVAL_SECONDS=5
```

Quản trị viên cũng chạy được một lượt quét ngay bằng `POST /sla/scan`.

Thời gian hồ sơ nằm ở *Chờ bổ sung thông tin* **không** tính vào SLA — người xử lý
không bị phạt khi người tạo chậm trả lời — nhưng tổng thời gian dừng vẫn được ghi lại.

> **Cảnh báo bảo mật**: toàn bộ mật khẩu trong `.env.example` là giá trị mẫu công khai,
> chỉ dùng cho môi trường phát triển. Bắt buộc thay trước khi triển khai thật. Tệp `.env`
> thật không bao giờ được commit lên kho mã.

### Dừng và dọn

```bash
docker compose --env-file .env down        # dừng, giữ dữ liệu
docker compose --env-file .env down -v     # dừng và xóa sạch dữ liệu
```

---

## Đóng góp

Đọc [`CONTRIBUTING.md`](CONTRIBUTING.md) trước khi gửi đóng góp. Tài liệu này mô tả:

- Mô hình nhánh ba tầng và quy trình làm việc
- Quy ước đặt tên nhánh và quy ước commit theo chuẩn Conventional Commits
- Yêu cầu header giấy phép trên mọi tệp mã nguồn
- Hệ thống nhãn issue theo khung kiến trúc H-P-D-I

Các issue gắn nhãn `good first issue` phù hợp cho người mới tham gia dự án.

---

## Đội ngũ

| Vai trò | Thành viên | Tài khoản |
|---|---|---|
| Giảng viên hướng dẫn | ThS. Trần Phước Đức | [`@tranphuocduc1998`](https://github.com/tranphuocduc1998) |
| Điều phối kho mã | Nguyễn Thanh Sơn | [`@AlaVox-lab`](https://github.com/AlaVox-lab) |
| Thành viên | Ngô Hoàng Đại | [`@Senning-Dd`](https://github.com/Senning-Dd) |
| Thành viên | Nguyễn Thanh Nguyên | [`@NguyentimAnh`](https://github.com/NguyentimAnh) |

Công việc được chia theo từng [issue](https://github.com/AlaVox-lab/dx-os-lab/issues) chứ
không cố định người nào phụ trách không gian nào — các thành viên hỗ trợ lẫn nhau tùy việc.

---

## Giấy phép

Dự án phát hành theo giấy phép [MIT](LICENSE).

Mọi tệp mã nguồn đều mang định danh giấy phép SPDX ở đầu tệp. Danh mục phụ thuộc kèm
giấy phép của từng thành phần được ghi tại
[`docs/dependencies.md`](docs/dependencies.md).
