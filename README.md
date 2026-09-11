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
| Giao diện | Next.js (React) | MIT |
| Dịch vụ ứng dụng | FastAPI (Python) | MIT |
| Cơ sở dữ liệu | PostgreSQL | PostgreSQL License |
| Đóng gói | Docker + Docker Compose | Apache-2.0 |

Các nền tảng Open-Core cho từng không gian đang trong giai đoạn khảo sát. Kết quả
được ghi thành bản ghi quyết định trong [`docs/adr/`](docs/adr/).

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

**Phiên bản `v0.1.0` — Giai đoạn 0: Dựng nền**

Kho mã hiện có bộ quy chuẩn làm việc và hệ thống tài liệu đầy đủ. **Chưa có mã nguồn
ứng dụng.** Xem [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) để biết chi tiết
tiến độ và việc tiếp theo.

---

## Cài đặt và dựng từ mã nguồn

> Hiện đã dựng được tầng hạ tầng gồm bốn dịch vụ nền. Tầng ứng dụng (cổng người dùng và
> dịch vụ nghiệp vụ) đang trong quá trình phát triển.

### Yêu cầu môi trường

| Thành phần | Yêu cầu |
|---|---|
| Docker Engine | 24 trở lên, kèm Docker Compose v2 |
| Git | bất kỳ phiên bản nào còn được hỗ trợ |
| Bộ nhớ trống | khoảng **2 GB** cho toàn cụm |
| Cổng cần trống | 5432 · 8080 · 8088 · 8333 |

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
| Keycloak — định danh | `http://localhost:8080` | `admin` / `admin` |
| Apache Superset — báo cáo | `http://localhost:8088` | `admin` / `admin` |
| SeaweedFS — lưu trữ tệp, S3 API | `http://localhost:8333` | xem `.env` |
| PostgreSQL | `localhost:5432` | xem `.env` |

Realm `dx-os-lab` trong Keycloak tự nạp lúc khởi động, gồm **năm vai trò nghiệp vụ** và
năm người dùng mẫu (mật khẩu `matkhau123`). Xem `infra/keycloak/realm-dx-os-lab.json`.

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

| Vai trò | Thành viên | Phạm vi trách nhiệm |
|---|---|---|
| Giảng viên hướng dẫn | *chờ điền* | |
| Điều phối kho mã và kiến trúc | *chờ điền* | Không gian `P`, lắp ghép kiến trúc, quản trị quy trình |
| Phát triển giao diện và trải nghiệm | *chờ điền* | Không gian `H`, cổng người dùng, bảng điều khiển |
| Dữ liệu và trí tuệ nhân tạo | *chờ điền* | Không gian `D` và `I` |

---

## Giấy phép

Dự án phát hành theo giấy phép [MIT](LICENSE).

Mọi tệp mã nguồn đều mang định danh giấy phép SPDX ở đầu tệp. Danh mục phụ thuộc kèm
giấy phép của từng thành phần được ghi tại
[`docs/dependencies.md`](docs/dependencies.md).
