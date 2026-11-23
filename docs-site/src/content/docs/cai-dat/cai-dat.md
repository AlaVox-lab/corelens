---
title: Cài đặt
description: Yêu cầu máy, hai cách cài (từ bản phát hành, từ kho mã), kiểm cụm, các dịch vụ sau khi dựng, và việc phải làm trước khi dùng thật.
sidebar:
  order: 1
---

Cả cụm tám dịch vụ dựng bằng **một lệnh** Docker Compose, không cần cài thêm gì trên máy ngoài
Docker. Mọi lời gọi API từ ngoài cụm đi qua **cổng API** (Apache APISIX) ở cổng `9080`; dịch vụ ứng dụng
và PostgreSQL không mở cổng ra máy.

## Yêu cầu môi trường

| Thành phần | Yêu cầu |
|---|---|
| Docker | Docker Desktop trên Windows và macOS, hoặc Docker Engine 24 trở lên trên Linux — kèm Docker Compose v2. Kiểm bằng `docker compose version` |
| Bộ nhớ cấp cho Docker | khoảng **2 GB** khi cả cụm chạy — đo lúc rảnh được 1,4 GB, Keycloak chiếm gần một nửa |
| Ổ đĩa trống | khoảng **6 GB** cho ảnh chứa và dữ liệu, tính trên ổ chứa dữ liệu của Docker |
| Mạng | cần Internet ở lần dựng đầu để tải ảnh chứa và thư viện; các lần sau không cần |
| Cổng cần trống | 3000 · 8080 · 8088 · 8333 · 9080 |
| Python *(tùy chọn)* | **3.10 trở lên**, chỉ để chạy các kịch bản tiện ích trong `scripts/` — nạp dữ liệu trình diễn, nâng cấp, sao lưu, tài khoản dịch vụ. Cụm không cần Python trên máy; riêng `scripts/quet_giay_phep.py` (quét giấy phép) cần 3.11 vì đọc cấu hình bằng `tomllib`. Chỉ dùng thư viện chuẩn, không phải `pip install`. Trên Ubuntu và Debian lệnh tên là `python3`: gõ `python3` ở mọi chỗ tài liệu ghi `python` |

## Cách 1 — cài từ bản phát hành

Dành cho người chỉ muốn dựng và dùng thử. Không cần Git.

1. Mở trang [Releases](https://github.com/AlaVox-lab/corelens/releases), chọn bản mang nhãn
   **Latest**, tải tệp **Source code (tar.gz)**
2. Bật Docker Desktop và chờ tới khi nó báo đang chạy
3. Mở terminal ở thư mục chứa tệp vừa tải và chạy bốn lệnh dưới. Thay `0.7.0` bằng phiên bản đã
   tải — tệp nén giải ra thư mục `corelens-<phiên bản>`, không phải `corelens`

Windows — PowerShell (Windows 10 và 11 có sẵn lệnh `tar`):

```powershell
tar -xzf corelens-0.7.0.tar.gz
cd corelens-0.7.0\infra
Copy-Item .env.example .env
docker compose --env-file .env up -d --build
```

Linux và macOS:

```bash
tar -xzf corelens-0.7.0.tar.gz
cd corelens-0.7.0/infra
cp .env.example .env
docker compose --env-file .env up -d --build
```

## Cách 2 — cài từ kho mã

Dành cho người sẽ sửa mã và gửi đóng góp. Cần thêm Git.

```bash
git clone https://github.com/AlaVox-lab/corelens.git
cd corelens/infra
cp .env.example .env
docker compose --env-file .env up -d --build
```

Lần dựng đầu mất khoảng **10–20 phút** tùy tốc độ mạng: tải ảnh chứa và dựng bốn ảnh — dịch vụ ứng
dụng, dịch vụ khai phá, cổng người dùng, và ảnh dẫn xuất cho Superset. Cổng API dùng nguyên ảnh chính thức
của Apache APISIX, không dựng.

## Kiểm cụm đã lên

```bash
docker compose --env-file .env ps
```

Chạy trong thư mục `infra`. Sáu dịch vụ `postgres`, `backend`, `cong-api`, `frontend`, `superset`,
`khai-pha` phải báo `healthy`; `keycloak` và `seaweedfs` báo `Up`. Keycloak cần thêm khoảng một phút mới
nhận đăng nhập.

Kiểm sâu hơn: đăng nhập bằng tài khoản quản trị viên `khanh.vo` rồi mở màn **Hệ thống**
(`http://localhost:3000/he-thong`) — màn báo trạng thái từng tầng, kể cả việc bộ quy tắc quy
trình đã nạp đủ hay chưa. Chưa đăng nhập thì xem `http://localhost:9080/health` (qua cổng API).

:::note
Nếu bộ quy tắc quy trình khai sai — có ngõ cụt, có trạng thái không tới được, có bước không vai
nào đi được — **cụm dừng khởi động** thay vì chạy với luồng hỏng. Xem nhật ký bằng
`docker compose --env-file .env logs postgres`.
:::

## Các dịch vụ sau khi dựng xong

| Dịch vụ | Địa chỉ | Tài khoản mặc định |
|---|---|---|
| **Cổng người dùng** | `http://localhost:3000` | tài khoản mẫu, xem [Tài khoản mẫu](../../huong-dan/tai-khoan-mau/) |
| **Cổng API** — cửa vào duy nhất của API, tài liệu API | `http://localhost:9080/docs` | access token của Keycloak, trừ `/health*` và tài liệu |
| Keycloak — định danh | `http://localhost:8080` | `admin` / `admin` |
| Apache Superset — báo cáo | `http://localhost:8088` | `admin` / `admin` |
| SeaweedFS — lưu trữ tệp, S3 API | `http://localhost:8333` | xem `.env` |

Dịch vụ ứng dụng (`8000`) và PostgreSQL (`5432`) chỉ nghe trong mạng Compose. Người phát triển cần gọi
thẳng dịch vụ hay mở cơ sở dữ liệu bằng công cụ trên máy thì thêm tệp ghi đè thứ hai — trong `infra`:

```bash
docker compose --env-file .env -f docker-compose.yml -f docker-compose.phat-trien.yml up -d
```

Hai cổng đó lấy từ `BACKEND_PORT` và `POSTGRES_PORT` trong `.env`. Đừng dùng tệp này khi triển khai thật.
Thêm hay bỏ tệp này trên cụm đang chạy thì Compose dựng lại hai container đó (dữ liệu giữ nguyên trong
volume); Keycloak mất kết nối cơ sở dữ liệu vài giây, đăng nhập có thể báo lỗi trong lúc đó rồi tự hết.
Các kịch bản trong `scripts/` (nạp dữ liệu trình diễn, sao lưu, kiểm nâng cấp…) đi qua `docker exec`, không
cần tệp này.

## Dịch vụ tùy chọn

Cụm mặc định chạy thủ công hoàn toàn và không tải mô hình nào. Mỗi phần dưới bật riêng, bằng một hồ sơ
Compose hay một lệnh, tắt đi thì phần còn lại vẫn chạy:

| Phần | Bật để làm gì | Thêm tài nguyên |
|---|---|---|
| [Mô hình ngôn ngữ](../../cai-dat/mo-hinh-ngon-ngu/) — hồ sơ `tri-tue` | Gợi ý loại, mức ưu tiên, phòng cho điều phối viên; hồ sơ đã giải quyết tương tự trên biểu mẫu gửi | khoảng 1,5 GB bộ nhớ, 2,4 GB ổ đĩa |
| [Thông báo thư và quét mã độc](../../cai-dat/thu-va-quet-tep/) — hồ sơ `thu-thu`, `quet-tep` | Gửi thư khi hồ sơ tới bước cần người nhận thao tác hay sắp tự chuyển; quét tệp đính kèm bằng ClamAV | ClamAV khoảng 1 GB bộ nhớ |
| [Kho tri thức](../../cai-dat/kho-tri-thuc/) — hồ sơ `tri-thuc` | Wiki.js đăng nhập một lần, bài hướng dẫn hiện trong gợi ý lúc soạn yêu cầu | khoảng 300 MiB bộ nhớ |
| [Xác thực hai lớp](../../cai-dat/xac-thuc-hai-lop/) — một lệnh | Mã dùng một lần (TOTP) khi đăng nhập, chỉ bằng cấu hình Keycloak | — |

Bảng điều khiển trống vì cụm mới chưa có hồ sơ: nạp vài trăm hồ sơ giả theo mục *Dữ liệu trình diễn* ở
trang [Màn Hệ thống](../../quan-tri/he-thong/). Nâng lên bản mới: [Nâng cấp](../../cai-dat/nang-cap/); sao
lưu tay cả cụm: [Sao lưu và khôi phục](../../cai-dat/sao-luu/).

## Trước khi dùng thật

Cụm dựng từ `.env.example` là cụm **trình diễn**: mật khẩu, khóa và mười ba tài khoản mẫu đều công khai.
Hệ thống không tự chặn chúng — người cài thường tạo thêm tài khoản thử của riêng mình, và không phần mềm nào
đoán đúng được tài khoản nào là mẫu. Trước khi đưa người dùng thật vào:

1. Trong `infra/.env`, đổi mọi giá trị ghi "BẮT BUỘC đổi": mật khẩu cơ sở dữ liệu, khóa kho tệp, bí mật
   của các client, khóa phiên, khóa Superset, mật khẩu quản trị Keycloak và Superset (`admin/admin`). Tệp
   `.env` thật không bao giờ được commit lên kho mã
2. Trong Keycloak (`http://localhost:8080`, realm `dx-os-lab`), xóa các tài khoản mẫu, chỉ giữ một tài khoản
   quản trị, rồi tạo tài khoản thật theo nhu cầu. Tắt (hoặc đổi bí mật) ba client tích hợp mẫu
   `dx-integration`, `dx-integration-truong-phong`, `dx-integration-duyet` nếu không dùng — hai client sau
   chỉ để chạy ví dụ quy trình thứ hai
3. Realm mẫu đã bật chống dò mật khẩu (khóa tạm sau 10 lần sai, tự mở) và chính sách mật khẩu tối thiểu
   8 ký tự; cụm dựng trước bản đó áp bằng `python scripts/xac_thuc_hai_lop.py chong-do` (xem
   [Nâng cấp](../../cai-dat/nang-cap/)). Muốn chặt hơn, sửa *Realm settings → Security defenses* và
   *Authentication → Policies*. `sslRequired` để `none` vì cụm mẫu chạy `http://localhost`; khi đưa lên tên
   miền có HTTPS, đổi thành `external` (hoặc `all`)
4. Sao lưu một lần ngay sau khi cấu hình xong — [Sao lưu và khôi phục](../../cai-dat/sao-luu/)

Báo lỗ hổng bảo mật theo
[`SECURITY.md`](https://github.com/AlaVox-lab/corelens/blob/main/SECURITY.md).
