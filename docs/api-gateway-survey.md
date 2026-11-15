# Khảo sát nền tảng cổng API

> **Mục đích**: ghi lại quá trình và kết quả khảo sát nền tảng cổng API (API Gateway) đặt trước các
> dịch vụ của cụm, làm căn cứ cho bản ghi quyết định
> [`adr/0010-chon-nen-tang-cong-api.md`](adr/0010-chon-nen-tang-cong-api.md).
>
> **Issue liên quan**: #363 · **Ngày thực hiện**: 2026-11-15

---

## 1. Câu hỏi cần trả lời

Đề thi Phần mềm nguồn mở OLP 2026 yêu cầu nền tảng lõi (Tầng 1) cung cấp bốn dịch vụ bắt buộc, trong
đó có **cổng API**. Tới `v0.16.0` cụm chưa có: dịch vụ ứng dụng mở cổng 8000 thẳng ra máy chủ, và việc
giới hạn tốc độ làm bên trong ứng dụng (`ARCHITECTURE.md` mục 7.4). Chọn nền tảng cổng API nguồn mở nào
để làm cửa vào duy nhất cho mọi lời gọi API từ ngoài cụm?

### 1.1. Ràng buộc chi phối

| Ràng buộc | Nguồn | Hệ quả với khảo sát |
|---|---|---|
| Giấy phép được OSI công nhận | Thể lệ, tiêu chí PoF 2 (10 điểm) | Kiểm tệp `LICENSE` của từng ứng viên, không dựa vào nhãn |
| Kiểm token của Keycloak ngay tại biên | Đề thi mục 4, nguyên lý bảo mật không tín nhiệm | Phải kiểm được chữ ký JWT theo khóa công khai lấy từ điểm cuối khám phá OIDC, vì Keycloak xoay khóa |
| Cấu hình bằng tệp trong kho | Đề thi mục 4 (hạ tầng bằng mã); PoF 4 | Không đòi cơ sở dữ liệu riêng hay thao tác tay sau khi dựng |
| Không sửa, không dựng lại ảnh nền tảng | PoF 5 | Tính năng cần dùng phải có sẵn trong ảnh chính thức |
| Bộ nhớ nhỏ | Cụm mặc định đang 1,66 GiB | Đo thật, không lấy số quảng cáo |

---

## 2. Ứng viên và kiểm tra giấy phép

Dòng đầu của tệp giấy phép đọc trực tiếp từ kho của từng dự án ngày 15/11/2026.

| Ứng viên | Bản thử | Tệp giấy phép | Dòng đầu | OSI | Tương thích MIT |
|---|---|---|---|---|---|
| **Apache APISIX** | `3.20.0` (13/11/2026) | [`LICENSE`](https://github.com/apache/apisix/blob/master/LICENSE) | `Apache License Version 2.0, January 2004` | Có | Có |
| **Traefik Proxy** | `v3.7.19` (13/11/2026) | [`LICENSE.md`](https://github.com/traefik/traefik/blob/master/LICENSE.md) | `The MIT License (MIT)` | Có | Có |
| **Kong Gateway** (bản nguồn mở) | `3.9.4` | [`LICENSE`](https://github.com/Kong/kong/blob/master/LICENSE) | `Apache License Version 2.0, January 2004` | Có | Có |

Ứng viên xem qua nhưng không dựng thử:

| Ứng viên | Giấy phép | Lý do không đi tiếp |
|---|---|---|
| Caddy | Apache-2.0 ([`LICENSE`](https://github.com/caddyserver/caddy/blob/master/LICENSE)) | Kiểm JWT cần mô-đun ngoài, tức phải tự dựng ảnh riêng — trái ràng buộc dùng ảnh chính thức |

**Lưu ý về giấy phép khi đọc bảng công nghệ tham chiếu của đề thi.** Bảng đó chỉ là ví dụ và không phải
mục nào cũng thuộc danh sách OSI. Tệp [`LICENSE`](https://github.com/hashicorp/vault/blob/main/LICENSE)
của HashiCorp Vault mở đầu bằng *"License text copyright (c) 2020 MariaDB Corporation Ab… Business Source
License"* — BSL không được OSI công nhận, nên Vault **không dùng được** trong dự án này. Mọi nền tảng lấy
từ bảng đó đều phải qua quy trình kiểm giấy phép ở `dependencies.md` trước khi đưa vào.

---

## 3. Dựng thử và số đo

Cụm thử dựng **ngoài kho mã**, tên dự án Compose riêng `thu363`, cổng 21080–21082, đã gỡ sau khi đo.
Phía sau mỗi cổng API là một máy chủ HTTP tĩnh đóng vai dịch vụ; máy chủ đó cũng phát tệp khám phá OIDC
và bộ khóa công khai (JWKS) như Keycloak. Ba token RS256 ký bằng `pyjwt`: một token đúng, một token hết
hạn, một token ký bằng khóa lạ.

### 3.1. Kiểm token tại biên *(đo thật)*

Mã HTTP trả về khi gọi `GET /api/ping` qua từng cổng:

| Lời gọi | APISIX | Traefik | Kong | Mong đợi |
|---|---|---|---|---|
| Không token | 401 | **200** | 401 | 401 |
| Token đúng | 200 | 200 | 200 | 200 |
| Token hết hạn | 401 | **200** | 401 | 401 |
| Token ký bằng khóa lạ | 401 | **200** | 401 | 401 |

- **APISIX** dùng plugin `openid-connect` có sẵn, chế độ `bearer_only` và `use_jwks`: tự đọc điểm cuối
  khám phá, tải bộ khóa công khai và kiểm chữ ký. Keycloak xoay khóa thì cổng tự theo.
- **Kong** dùng plugin `jwt` có sẵn, nhưng khóa công khai phải **chép tay vào tệp cấu hình** theo từng
  nơi phát. Keycloak xoay khóa là mọi lời gọi bị từ chối cho tới khi sửa tệp. Plugin OpenID Connect đọc
  điểm cuối khám phá thuộc bản thương mại theo tài liệu của Kong — chưa kiểm lại trong lần thử này.
- **Traefik** bản nguồn mở không có bộ kiểm JWT; cách làm là `ForwardAuth` chuyển sang một dịch vụ xác
  thực tự viết, hoặc plugin bên thứ ba tải lúc chạy. Cả hai đều thêm một thành phần phải bảo trì.

### 3.2. Giới hạn tốc độ *(đo thật)*

Ngưỡng 300 lời gọi mỗi phút, gửi 350 lời gọi liên tiếp, mỗi cổng chạy một tiến trình làm việc:

| | APISIX (`limit-count`) | Kong (`rate-limiting`) | Traefik (`rateLimit`) |
|---|---|---|---|
| Kết quả | 300 lần 200, 50 lần 429 | 300 lần 200, 50 lần 429 | Có sẵn, kiểu thùng rò; không thử cùng ngưỡng |

Ở cấu hình mặc định (tiến trình làm việc theo số nhân máy), bộ đếm cục bộ của Kong tính **riêng từng
tiến trình**: 400 lời gọi qua ngưỡng 300 mà không lần nào bị chặn. APISIX đếm chung trong bộ nhớ dùng
chung, chặn đúng ở lời gọi thứ 300.

### 3.3. Bộ nhớ và kích thước ảnh *(đo thật, `docker stats --no-stream`, máy 24 nhân)*

| | APISIX `3.20.0-debian` | Traefik `v3.7.19` | Kong `3.9.4` |
|---|---|---|---|
| Mặc định, sau 400 lời gọi | 525 MiB | 28 MiB | 1,59 GiB |
| Một tiến trình làm việc, sau 350 lời gọi | **57 MiB** | 25 MiB | 121 MiB |
| Kích thước ảnh đã giải nén | 638 MB | 251 MB | 546 MB |

APISIX và Kong sinh tiến trình làm việc theo số nhân, nên trên máy nhiều nhân **phải** đặt số tiến trình
trong cấu hình; với quy mô trình diễn một tiến trình là đủ.

### 3.4. Cấu hình bằng tệp

| | APISIX | Traefik | Kong |
|---|---|---|---|
| Chạy không cần kho cấu hình ngoài | Có — chế độ `standalone`, đọc `apisix.yaml` | Có — `providers.file` | Có — chế độ không cơ sở dữ liệu |
| Nạp lại khi tệp đổi | Có | Có | Phải khởi động lại hoặc gọi API quản trị |

---

## 4. Kết luận

| Tiêu chí | APISIX | Traefik | Kong |
|---|---|---|---|
| Giấy phép | Apache-2.0 | MIT | Apache-2.0 |
| Kiểm token Keycloak tại biên bằng tính năng có sẵn | **Có, theo điểm cuối khám phá** | Không | Có, khóa chép tay |
| Giới hạn tốc độ đúng ở mặc định | Có | Có | Không khi nhiều tiến trình |
| Bộ nhớ (một tiến trình) | 57 MiB | 25 MiB | 121 MiB |
| Cấu hình bằng tệp trong kho | Có | Có | Có |

**Đề xuất: Apache APISIX `3.20.0`**, chạy chế độ `standalone` với một tiến trình làm việc. Đây là ứng
viên duy nhất kiểm được token của Keycloak tại biên mà không thêm thành phần tự viết và không phải chép
khóa tay. Traefik nhẹ nhất nhưng thiếu đúng tính năng đề thi cần ở lớp biên. Chi tiết quyết định ở
ADR-0010.

**Chưa kiểm:** chạy với Keycloak thật của cụm (chỉ thử với bộ khóa giả lập); hành vi khi Keycloak chưa
sẵn sàng lúc cổng khởi động; chuyển tiếp tải tệp lớn và luồng sự kiện. Các mục này kiểm ở #364.
