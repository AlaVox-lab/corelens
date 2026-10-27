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

**Giai đoạn 2: Không gian `H` và `P`** — phiên bản phát hành mới nhất xem ở trang
[Releases](https://github.com/AlaVox-lab/dx-os-lab/releases).

Luồng thủ công đã chạy đầu-cuối cho cả bốn vai trò trên giao diện thật: người gửi gửi
và theo dõi yêu cầu, điều phối viên phân loại và định tuyến, trưởng phòng nhận việc và
giao người, người xử lý làm và hỏi thêm khi cần. Người gửi sửa được nội dung khi hồ sơ
chưa tới phòng ban, người xử lý tự nhận việc về mình. Mọi lời nhắn gom về một hộp thư
chung, mỗi cuộc trò chuyện gắn một hồ sơ, và nhân viên trao đổi nội bộ được mà người gửi
không thấy. Engine máy trạng thái tự viết chạy ràng buộc Poka-yoke, đếm hạn SLA theo giờ
làm việc và tự leo thang, tự trả hồ sơ về điều phối hay tự đóng khi người phải bấm im lặng
quá hạn, và ghi nhật ký sự kiện cho mọi lần chuyển trạng thái. Tầng `D` và `I` chưa cài
đặt. Xem
[`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) để biết tiến độ và việc tiếp theo.

---

## Cài đặt và dựng từ mã nguồn

> Cụm sáu dịch vụ dựng được bằng một lệnh. Cổng gửi yêu cầu, buồng lái điều phối và
> buồng lái phòng ban đều chạy được với các tài khoản mẫu bên dưới.

### Yêu cầu môi trường

| Thành phần | Yêu cầu |
|---|---|
| Docker | Docker Desktop trên Windows và macOS, hoặc Docker Engine 24 trở lên trên Linux — kèm Docker Compose v2. Kiểm bằng `docker compose version` |
| Bộ nhớ cấp cho Docker | khoảng **2 GB** khi cả cụm chạy — đo lúc rảnh được 1,4 GB, Keycloak chiếm gần một nửa |
| Ổ đĩa trống | khoảng **6 GB** cho ảnh chứa và dữ liệu, tính trên ổ chứa dữ liệu của Docker |
| Mạng | cần Internet ở lần dựng đầu để tải ảnh chứa và thư viện; các lần sau không cần |
| Cổng cần trống | 3000 · 5432 · 8000 · 8080 · 8088 · 8333 |

Cài từ bản phát hành thì không cần Git.

### Cách 1 — cài từ bản phát hành

Đây là cách dành cho người chỉ muốn dựng và dùng thử hệ thống.

1. Mở trang [Releases](https://github.com/AlaVox-lab/dx-os-lab/releases), chọn bản mang
   nhãn **Latest**, tải tệp **Source code (tar.gz)** ở mục *Assets*. Tệp tải về tên
   `dx-os-lab-<phiên bản>.tar.gz`, ví dụ `dx-os-lab-0.5.0.tar.gz`
2. Bật Docker Desktop và chờ tới khi nó báo đang chạy
3. Mở terminal ở thư mục chứa tệp vừa tải, chạy bốn lệnh dưới đây. Thay `0.5.0` bằng số
   phiên bản bạn đã tải — tệp nén giải ra thư mục `dx-os-lab-<phiên bản>`, không phải
   `dx-os-lab`

Windows — PowerShell (Windows 10 và 11 có sẵn lệnh `tar`):

```powershell
tar -xzf dx-os-lab-0.5.0.tar.gz
cd dx-os-lab-0.5.0\infra
Copy-Item .env.example .env
docker compose --env-file .env up -d --build
```

Linux và macOS:

```bash
tar -xzf dx-os-lab-0.5.0.tar.gz
cd dx-os-lab-0.5.0/infra
cp .env.example .env
docker compose --env-file .env up -d --build
```

### Cách 2 — cài từ kho mã

Dành cho người sẽ sửa mã và gửi đóng góp. Cần thêm Git.

```bash
git clone https://github.com/AlaVox-lab/dx-os-lab.git
cd dx-os-lab/infra
cp .env.example .env
docker compose --env-file .env up -d --build
```

Mọi giá trị trong `.env.example` **chạy được ngay**, không cần sửa gì để dựng thử. Lần
dựng đầu mất khoảng **10–20 phút**, tùy tốc độ mạng, vì phải tải ảnh chứa và dựng ba ảnh: dịch vụ ứng
dụng, cổng người dùng và ảnh dẫn xuất cho Superset.

### Kiểm cụm đã lên

```bash
docker compose --env-file .env ps
```

Chạy trong thư mục `infra`. Bốn dịch vụ `postgres`, `backend`, `frontend`, `superset` phải
báo `healthy`; `keycloak` và `seaweedfs` báo `Up`. Keycloak cần thêm khoảng một phút sau
khi lên mới nhận đăng nhập. Rồi mở `http://localhost:3000`.

### Sự cố thường gặp

| Dấu hiệu | Cách xử lý |
|---|---|
| `failed to connect to the docker API`, `Cannot connect to the Docker daemon` | Docker chưa chạy. Bật Docker Desktop, chờ nó báo đang chạy rồi chạy lại lệnh |
| `port is already allocated`, `address already in use` | Một chương trình khác giữ cổng — thường là PostgreSQL cài sẵn trên máy, giữ cổng 5432. Tắt chương trình đó, hoặc đổi `POSTGRES_PORT` trong `.env`. Đổi được tương tự `BACKEND_PORT`, `SUPERSET_PORT`, `SEAWEEDFS_S3_PORT`; giữ nguyên 3000 và 8080 vì cấu hình đăng nhập mẫu gắn với hai cổng đó |
| Dựng hỏng giữa chừng với `no space left on device` hoặc `EOF` | Kiểm ổ chứa dữ liệu của Docker còn đủ chỗ như bảng yêu cầu, rồi chạy lại lệnh `up` — phần đã tải không phải tải lại |
| Bấm đăng nhập báo lỗi khi mở cổng từ máy khác qua địa chỉ IP | Cấu hình đăng nhập mẫu chỉ nhận `localhost`. Mở `http://localhost:3000` trên chính máy đã cài |
| Sửa tệp trong `infra/seed/` hoặc realm rồi dựng lại mà không thấy thay đổi | Dữ liệu khởi tạo chỉ nạp lần đầu. Chạy `down -v` ở mục *Dừng và dọn* rồi dựng lại |

### Các dịch vụ sau khi dựng xong

| Dịch vụ | Địa chỉ | Tài khoản mặc định |
|---|---|---|
| **Cổng người dùng** | `http://localhost:3000` | chưa cần đăng nhập |
| **Dịch vụ ứng dụng** — tài liệu API | `http://localhost:8000/docs` | chưa cần đăng nhập |
| Keycloak — định danh | `http://localhost:8080` | `admin` / `admin` |
| Apache Superset — báo cáo | `http://localhost:8088` | `admin` / `admin` |
| SeaweedFS — lưu trữ tệp, S3 API | `http://localhost:8333` | xem `.env` |
| PostgreSQL | `localhost:5432` | xem `.env` |

Kiểm cụm có khỏe không: đăng nhập bằng tài khoản quản trị viên `khanh.vo` rồi mở màn
**Hệ thống** (`http://localhost:3000/he-thong`) — màn báo trạng thái từng tầng, kể cả việc bộ
quy tắc quy trình đã nạp đủ các trạng thái hay chưa. Chưa đăng nhập thì xem thẳng
`http://localhost:8000/health`. Người dùng khác mở trang chủ thấy danh sách việc đang chờ họ,
không thấy chữ kỹ thuật. Cổng gửi yêu cầu nằm ở `http://localhost:3000/yeu-cau`.

Lược đồ và dữ liệu khởi tạo của engine máy trạng thái nạp tự động lúc PostgreSQL khởi
tạo lần đầu. Nếu bộ quy tắc sai — có ngõ cụt, có trạng thái không tới được, có cạnh
không vai trò nào đi được — **cụm sẽ dừng khởi động** thay vì chạy với luồng hỏng.
Xem `infra/seed/`.

### Đăng nhập thử

Bấm **Đăng nhập bằng tài khoản công ty** trên trang chủ. Realm `dx-os-lab` tự nạp lúc khởi động,
gồm năm vai trò nghiệp vụ, bốn nhóm phòng ban và mười ba tài khoản mẫu — tất cả dùng mật
khẩu `matkhau123`:

| Tài khoản | Vai trò | Phòng ban | Số điện thoại |
|---|---|---|---|
| `an.nguyen` | Người tạo yêu cầu | — | `0900 000 001` |
| `binh.tran` | Người phân loại | — | `0900 000 002` |
| `dung.pham` | Người xét duyệt | Công nghệ thông tin | `0900 000 004` |
| `cuong.le` | Người xử lý | Công nghệ thông tin | `0900 000 003` |
| `lan.vu` | Người xử lý, nhận qua nhóm | Công nghệ thông tin | `0900 000 006` |
| `tuan.ngo` | Người xử lý — **đã khóa** | Công nghệ thông tin | `0900 000 007` |
| `ha.do` | Người xử lý | Nhân sự | `0900 000 008` |
| `giang.hoang` | Người xét duyệt | Nhân sự | `0900 000 009` |
| `minh.dang` | Người xét duyệt | Hành chính | `0900 000 010` |
| `nam.bui` | Người xử lý | Hành chính | `0900 000 011` |
| `phuong.ly` | Người xét duyệt | Tài chính kế toán | `0900 000 012` |
| `quang.trinh` | Người xử lý | Tài chính kế toán | `0900 000 013` |
| `khanh.vo` | Quản trị viên | — | `0900 000 005` |

Số điện thoại là số giả, theo một dãy dễ nhận ra. Điều phối viên và nhân viên phòng ban thấy
email và số của người gửi ngay dưới tên họ trên trang chi tiết hồ sơ (#131). Mỗi người tự
sửa số của mình ở trang tài khoản `http://localhost:8080/realms/dx-os-lab/account`.

Mỗi phòng có ít nhất một người xét duyệt và một người xử lý (#145), nên hồ sơ chuyển về
phòng nào cũng có người nhận. Người ở các phòng khác nhau cũng cho thấy ràng buộc *chỉ
người thuộc phòng đang giữ hồ sơ mới thao tác được*. Ba vai trò còn lại không cần phòng ban.

Hai tài khoản cuối của phòng Công nghệ thông tin cũng cố ý. `lan.vu` nhận vai trò người
xử lý qua nhóm `/nhom-vai-tro/nguoi-xu-ly` chứ không gán thẳng — cách doanh nghiệp thật
hay dùng. `tuan.ngo` đóng vai người đã nghỉ việc: tài khoản bị khóa nên không đăng nhập
được, và không bao giờ hiện trong danh sách người nhận việc.

Realm còn một client `dx-directory` không dùng để đăng nhập: đó là tài khoản dịch vụ chỉ
đọc, để dịch vụ ứng dụng tra tên người trong phòng cho ô chọn người xử lý.

Toàn bộ khai trong `infra/keycloak/realm-dx-os-lab.json` — thêm phòng ban hay đổi vai
trò là sửa tệp đó rồi dựng lại cụm, không đụng mã nguồn.

### Cổng gửi yêu cầu

Đăng nhập bằng `an.nguyen` rồi mở `http://localhost:3000/yeu-cau`. Ba màn hình:

| Màn | Địa chỉ | Việc làm được |
|---|---|---|
| Gửi yêu cầu | `/yeu-cau/moi` | Biểu mẫu ba bước: chọn loại, viết nội dung, xem lại rồi gửi |
| Hồ sơ của tôi | `/yeu-cau` | Danh sách hồ sơ đã gửi; rê chuột hoặc chạm vào nhãn trạng thái để xem hồ sơ đang ở bước nào |
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

### Buồng lái điều phối viên

Đăng nhập bằng `binh.tran` rồi mở mục **Điều phối** trên thanh điều hướng, hoặc thẳng
`http://localhost:3000/dieu-phoi`. Mục đó chỉ hiện với tài khoản mang vai trò điều phối —
đăng nhập bằng `an.nguyen` sẽ không thấy.

| Màn | Địa chỉ | Việc làm được |
|---|---|---|
| Hàng đợi | `/dieu-phoi` | Hồ sơ đang chờ phân loại hoặc định tuyến, chờ lâu nhất lên đầu |
| Chi tiết | `/dieu-phoi/{số}` | Phân loại, chuyển về phòng ban, hỏi thêm thông tin, chuyển lại phòng khác cho hồ sơ bị trả |

Thử một vòng trọn vẹn với hai cửa sổ: `an.nguyen` gửi yêu cầu ở cổng người gửi,
`binh.tran` phân loại rồi chuyển về phòng ban ở buồng lái — cửa sổ của người gửi thấy
ngay trạng thái mới cùng tên người vừa thao tác trên dòng thời gian.

**Ô nhập cũng đến từ dữ liệu, như nút bấm.** Mở bảng *Phân loại yêu cầu* sẽ thấy hai ô —
mức ưu tiên và loại yêu cầu — vì ràng buộc gắn trên cạnh đó quản đúng hai trường ấy. Gỡ
dòng `set-priority` của cạnh này trong `infra/seed/01-quy-tac-quy-trinh.sql` rồi dựng lại
cụm là ô mức ưu tiên biến mất, không sửa dòng TypeScript nào.

### Buồng lái phòng ban

Đăng nhập bằng `dung.pham` (trưởng phòng) hoặc `cuong.le` (người xử lý) rồi mở mục
**Phòng ban**, hoặc thẳng `http://localhost:3000/phong-ban`. Cả phòng nhìn chung một hàng
đợi; nút bấm của mỗi người khác nhau vì chúng đến từ bộ quy tắc.

| Màn | Địa chỉ | Việc làm được |
|---|---|---|
| Hàng đợi | `/phong-ban` | Hồ sơ của phòng mình, quá hạn lên đầu rồi tới gần hạn nhất; nút *Giao cho tôi* thu về phần việc của mình |
| Chi tiết | `/phong-ban/{số}` | Trưởng phòng nhận hồ sơ và giao người xử lý, từ chối, phân công lại hồ sơ bị leo thang; người xử lý hỏi thêm thông tin hoặc báo hoàn thành |

Thử trọn vòng đời một hồ sơ với ba cửa sổ: `an.nguyen` gửi, `binh.tran` phân loại và
chuyển về phòng Công nghệ thông tin, `dung.pham` nhận rồi giao cho `cuong.le`, `cuong.le`
báo hoàn thành, và `an.nguyen` xác nhận đạt để đóng hồ sơ.

**Ô chọn người xử lý đọc từ Keycloak.** Danh sách chỉ gồm người của đúng phòng đó và
nhận được việc — không có trưởng phòng, không có `tuan.ngo` vì tài khoản đã khóa. Tắt
Keycloak rồi mở lại hồ sơ: trang vẫn mở được, ô chọn người báo không nạp được danh sách,
và trưởng phòng vẫn nhận được hồ sơ mà chưa giao cho ai.

**Xem hồ sơ tự leo thang.** Hạ `SLA_SCAN_INTERVAL_SECONDS` như ở mục dưới, để một hồ sơ
đang xử lý quá hạn: nó chuyển sang *Đã leo thang*, nổi lên đầu hàng đợi, và trưởng phòng
phân công lại được ngay từ màn chi tiết. Sau khi phân công lại, người mới có một khoảng
**ân hạn** trước khi hồ sơ bị leo thang lần nữa — màn hình ghi "Quá hạn … · ân hạn còn …".

### Theo dõi SLA

Dịch vụ ứng dụng chạy một bộ quét nền, mặc định mỗi 60 giây, tìm hồ sơ vượt ngưỡng SLA
rồi **tự leo thang** chúng. Ngưỡng khai theo từng loại yêu cầu trong
`infra/seed/02-co-cau-to-chuc.sql`; trạng thái nào làm đồng hồ chạy khai ở cột
`sla_running` trong `infra/seed/01-quy-tac-quy-trinh.sql`.

Ngưỡng ở `02-co-cau-to-chuc.sql` là hạn chuẩn của mức ưu tiên Bình thường; mức Khẩn, Cao,
Thấp nhân hệ số 50%, 75%, 150% khai trong bảng `priorities`. Điều phối viên gia hạn được một
lần trước khi phòng ban nhận việc, trưởng phòng gia hạn khi hồ sơ đã leo thang — mỗi lần tối đa
nửa hạn gốc, tổng tối đa hai lần, luôn kèm lý do.

Hạn đếm bằng **giờ làm việc**, không phải giờ đồng hồ: mẫu là Thứ Hai tới Thứ Sáu, 8:00–12:00
và 13:00–17:00 giờ Việt Nam, trừ ngày lễ năm 2026, khai trong
`infra/seed/03-lich-lam-viec.sql`. Hồ sơ gửi tối Thứ Sáu chỉ bắt đầu tính hạn từ 8:00 Thứ
Hai. Các hạn chờ tự trả về, tự đóng cũng đếm theo lịch này.

Muốn xem cơ chế hoạt động mà không phải chờ, hạ chu kỳ quét trong `.env`:

```bash
SLA_SCAN_INTERVAL_SECONDS=5
```

Quản trị viên cũng chạy được một lượt quét ngay bằng `POST /sla/scan`.

Thời gian hồ sơ nằm ở *Chờ bổ sung thông tin* **không** tính vào SLA — người xử lý
không bị phạt khi người tạo chậm trả lời — nhưng tổng thời gian dừng vẫn được ghi lại.

Hồ sơ đã quá hạn mà được phân công lại, được mở lại, hay vừa bổ sung thông tin xong thì
có **ân hạn** trước khi bị leo thang lần nữa: mẫu là một phần tư hạn xử lý, khai ở cột
`sla_grace_hours` cạnh `sla_hours`. Đồng hồ tổng không đặt lại — hồ sơ vẫn được ghi nhận
là quá hạn.

Muốn thử leo thang bằng tay mà không phải chờ hết hạn thật, đẩy một hồ sơ đang xử lý sang
quá hạn — phải lùi cả mốc vào trạng thái, nếu không hồ sơ còn nằm trong ân hạn:

```bash
docker exec dxlab-postgres psql -U dxlab -d dxlab -c "UPDATE requests SET sla_running_seconds = 999999, sla_segment_since = now() - interval '1 day' WHERE id = <số hồ sơ>"
```

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
