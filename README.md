# dx-os-lab

> Cổng vận hành yêu cầu nội bộ cho doanh nghiệp, theo kiến trúc Open-Core H-P-D-I — Dự án dự thi
> Phần mềm nguồn mở, Olympic Tin học Sinh viên Việt Nam 2026.

[![Giấy phép: MIT](https://img.shields.io/badge/Gi%E1%BA%A5y%20ph%C3%A9p-MIT-blue.svg)](LICENSE)

**Tài liệu đầy đủ:** trang tài liệu trong [`docs-site/`](docs-site/) — bắt đầu nhanh, cài đặt, hướng
dẫn theo từng vai, quản trị và tùy biến, phát triển. Cách xem ở mục [Tài liệu](#tài-liệu).

---

## Giới thiệu

Ở nhiều doanh nghiệp, việc nội bộ — báo máy hỏng, xin cấp phần mềm, xin giấy xác nhận, đề xuất mua
vật tư — được gửi qua Zalo, email hay giấy tờ. Người gửi không biết yêu cầu đã tới đâu, quá hạn không
ai nhắc, và lãnh đạo không có số liệu để biết khâu nào đang chậm.

**dx-os-lab là một cổng chung cho mọi yêu cầu đó.** Một hồ sơ đi qua bốn vai — người gửi, điều phối
viên, trưởng phòng, người xử lý — và mỗi người mở cổng lên là thấy ngay việc đang chờ mình.

- **Điều phối theo từng hồ sơ** — điều phối viên phân loại, đặt mức ưu tiên và chọn phòng phù hợp;
  phòng sai chuyên môn thì trả lại kèm lý do. Không phải chuỗi người duyệt cố định
- **Quy trình là dữ liệu** — trạng thái, bước đi, vai trò, ràng buộc chống sai (Poka-yoke) và mọi con
  số nằm trong bảng. Đổi quy trình cho doanh nghiệp khác là sửa dữ liệu, không sửa mã
- **Hạn theo giờ làm việc** — nhân hệ số theo mức ưu tiên; quá hạn tự leo thang; hồ sơ nằm im thì
  hệ thống báo trước rồi tự đi
- **Vòng phản hồi tự soi quy trình** — mọi lần chuyển trạng thái ghi một dòng nhật ký sự kiện chỉ ghi
  thêm; từ nhật ký, hệ thống khai phá lại quy trình đang chạy thật và chỉ ra điểm nghẽn

So sánh với các sản phẩm cùng loại: [`docs/so-sanh-san-pham.md`](docs/so-sanh-san-pham.md).

## Kiến trúc H-P-D-I

| | Không gian | Nền tảng | Trạng thái |
|---|---|---|---|
| **H** | Nhân sự — định danh, phân quyền theo vai | Keycloak `26.7.3` (Apache-2.0) | Đã chạy |
| **P** | Quy trình — máy trạng thái, Poka-yoke, hạn xử lý | **Engine tự viết** (MIT) | Đã chạy |
| **D** | Dữ liệu — bảng điều khiển trên nhật ký sự kiện | Apache Superset `6.1.0` (Apache-2.0) | `v0.9.0` |
| **I** | Trí tuệ — khai phá quy trình, gợi ý phân loại | Đề xuất PM4Py, pgvector | `v0.10.0` |

Nền chung: Next.js, FastAPI, PostgreSQL, SeaweedFS (tệp đính kèm), Docker Compose. Nền tảng phổ thông
được lắp ghép và chạy như dịch vụ độc lập; engine quy trình — phần lõi tạo khác biệt — nhóm tự viết.
Tầng `I` chỉ ghi vào trường gợi ý, con người xác nhận mới thành quyết định. Lý do từng lựa chọn ở
[`docs/adr/`](docs/adr/).

## Cài nhanh

Cần Docker (Docker Desktop, hoặc Docker Engine 24 trở lên kèm Compose v2), khoảng 2 GB bộ nhớ, 6 GB ổ
đĩa, và các cổng 3000 · 5432 · 8000 · 8080 · 8088 · 8333 đang trống.

Tải **Source code (tar.gz)** của bản mới nhất ở trang
[Releases](https://github.com/AlaVox-lab/dx-os-lab/releases), rồi (thay `0.7.0` bằng phiên bản đã tải):

```bash
tar -xzf dx-os-lab-0.7.0.tar.gz
cd dx-os-lab-0.7.0/infra
cp .env.example .env
docker compose --env-file .env up -d --build
```

Trên PowerShell dùng `Copy-Item .env.example .env` và `cd dx-os-lab-0.7.0\infra`. Từ kho mã thì
`git clone` rồi chạy ba lệnh cuối trong `dx-os-lab/infra`. Lần đầu mất khoảng 10–20 phút.

Mở `http://localhost:3000`, bấm **Đăng nhập bằng tài khoản công ty**. Tài khoản mẫu, mật khẩu chung
`matkhau123`:

| Tài khoản | Vai |
|---|---|
| `an.nguyen` | Người gửi |
| `binh.tran` | Điều phối viên |
| `dung.pham` | Trưởng phòng Công nghệ thông tin |
| `cuong.le` | Người xử lý Công nghệ thông tin |
| `khanh.vo` | Quản trị viên — màn Hệ thống |

Bảng điều khiển phân tích ở `http://localhost:8088` (tài khoản quản trị trong `.env`). Muốn có số để
xem, nạp vài trăm hồ sơ giả vào cụm thử — chạy ở gốc kho mã:

```bash
python scripts/nap_du_lieu_trinh_dien.py --xac-nhan
```

Đủ mười ba tài khoản, kiểm cụm, cấu hình, sự cố thường gặp và nâng cấp: xem trang tài liệu, phần
*Cài đặt và vận hành*.

> **Bảo mật**: mọi mật khẩu trong `.env.example` là giá trị mẫu công khai, chỉ để dựng thử. Đổi trước
> khi triển khai thật — xem [`SECURITY.md`](SECURITY.md).

## Tài liệu

**Trang tài liệu** ([`docs-site/`](docs-site/)) chia theo người đọc, tương tự trang tài liệu của các nền
tảng nguồn mở lớn:

| Phần | Cho ai |
|---|---|
| Bắt đầu | Người mới: giới thiệu, dựng cụm và đi trọn một hồ sơ |
| Cài đặt và vận hành | Người cài đặt: yêu cầu máy, cấu hình, sự cố, nâng cấp |
| Hướng dẫn sử dụng | Nhân viên: người gửi, điều phối viên, trưởng phòng, người xử lý, hộp thư, hạn xử lý |
| Quản trị và tùy biến | Quản trị viên: đổi quy trình, danh mục, các con số, màn Hệ thống |
| Phát triển, Tham khảo | Người đóng góp: kiến trúc, quy trình đóng góp, API, phát hành |

Xem trên máy (cần Node.js 22.12 trở lên):

```bash
cd docs-site
npm ci
npm run dev
```

rồi mở `http://localhost:4321/dx-os-lab/`. Trang sẽ đăng lên GitHub Pages khi kho chuyển công khai.

Tài liệu kỹ thuật trong kho:

| Tài liệu | Trả lời |
|---|---|
| [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) | Dự án đang ở đâu, vừa làm gì, đang vướng gì |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Hệ thống tổ chức thế nào và vì sao |
| [`docs/process-flow.md`](docs/process-flow.md) | Luồng nghiệp vụ: 11 trạng thái, 32 bước, cơ sở các con số |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Việc tiếp theo |
| [`docs/adr/`](docs/adr/) | Vì sao chọn công nghệ đó |
| [`docs/dependencies.md`](docs/dependencies.md) | Phụ thuộc và giấy phép |
| [`CHANGELOG.md`](CHANGELOG.md) | Nhật ký thay đổi, sinh tự động từ lịch sử commit |

## Đóng góp

Đọc [`CONTRIBUTING.md`](CONTRIBUTING.md): mô hình nhánh, Conventional Commits, header giấy phép SPDX,
nhãn issue theo H-P-D-I, tích hợp liên tục. Tham gia dự án là đồng ý với
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Lỗ hổng bảo mật báo riêng theo [`SECURITY.md`](SECURITY.md).
Trợ lý AI lập trình đọc [`CLAUDE.md`](CLAUDE.md) (qua [`AGENTS.md`](AGENTS.md)).

## Đội ngũ

| Vai trò | Thành viên | Tài khoản |
|---|---|---|
| Giảng viên hướng dẫn | ThS. Trần Phước Đức | [`@tranphuocduc1998`](https://github.com/tranphuocduc1998) |
| Điều phối kho mã | Nguyễn Thanh Sơn | [`@AlaVox-lab`](https://github.com/AlaVox-lab) |
| Thành viên | Ngô Hoàng Đại | [`@Senning-Dd`](https://github.com/Senning-Dd) |
| Thành viên | Nguyễn Thanh Nguyên | [`@NguyentimAnh`](https://github.com/NguyentimAnh) |

Công việc chia theo từng [issue](https://github.com/AlaVox-lab/dx-os-lab/issues), không cố định ai phụ
trách không gian nào.

## Giấy phép

Dự án phát hành theo giấy phép [MIT](LICENSE). Mọi tệp mã nguồn mang định danh giấy phép SPDX ở đầu
tệp. Danh mục phụ thuộc kèm giấy phép ở [`docs/dependencies.md`](docs/dependencies.md).
