---
title: Thông báo thư và quét mã độc (tùy chọn)
description: Bật thông báo thư điện tử (kèm hộp thư thử Mailpit) và quét mã độc tệp đính kèm bằng ClamAV — hai dịch vụ tùy chọn, tắt mặc định, cách bật, cách tắt, và hệ thống làm gì khi chúng hỏng.
sidebar:
  order: 6
---

Hai thành phần dưới đây **tắt mặc định**. Cụm dựng bằng `docker compose up` không có chúng, không tải
thêm gì, và chạy đầy đủ. Bật thành phần nào thì thêm hồ sơ Compose (`--profile`) của nó và đặt một biến
trong `infra/.env`. Thành phần tùy chọn hỏng chỉ làm mất phần của nó — không bao giờ chặn chuyển trạng
thái hay tải tệp của người dùng.

## Thông báo thư điện tử

Hệ thống gửi thư khi:

| Loại | Khi nào | Ai nhận |
|---|---|---|
| Có việc chờ tôi | Hồ sơ chuyển tới bước cần bạn thao tác | Người đang có bước chính — cùng cờ "Cần bạn xử lý" trên trang chủ |
| Hồ sơ sắp tự chuyển | Hồ sơ đang chờ bạn vào khoảng báo trước của hạn chờ (sắp tự đóng, tự trả về) | Như trên |
| Hồ sơ đã tự chuyển | Hệ thống vừa tự đóng hay tự trả về hồ sơ vì hết hạn chờ | Người gửi hồ sơ |

Danh sách loại, tiêu đề và lời thư nằm trong dữ liệu `infra/seed/05-loai-thong-bao.sql` — sửa lời thư,
thêm hay tắt một loại là sửa tệp đó. Mỗi người bật/tắt từng loại ở trang **Thông báo thư** (biểu tượng
chuông cạnh tên ở thanh bên). Địa chỉ thư là địa chỉ trong tài khoản Keycloak, tra lúc gửi.

### Bật với hộp thư thử Mailpit (trình diễn)

[Mailpit](https://github.com/axllent/mailpit) (MIT) nhận mọi thư qua SMTP và giữ lại để xem trên web, không
chuyển đi đâu. Trong `infra/.env`:

```bash
SMTP_HOST=thu-thu
SMTP_PORT=1025
```

rồi trong `infra/`:

```bash
docker compose --env-file .env --profile thu-thu up -d
```

Xem thư ở <http://localhost:8025> (đổi cổng bằng `MAILPIT_UI_PORT`). Màn **Hệ thống** có dòng *Thông báo
thư* (sẵn sàng / không phản hồi, số thư chờ gửi, số thư hỏng) và dòng *Bộ gửi thư thông báo*.

### Máy chủ thư thật

Bỏ hồ sơ `thu-thu`, điền `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_SECURITY`
(`none`, `starttls` cho cổng 587, `ssl` cho cổng 465) và `SMTP_FROM` trong `infra/.env`, rồi
`docker compose --env-file .env up -d backend`.

### Khi máy chủ thư hỏng

Mọi thao tác trên hồ sơ vẫn chạy. Thư nằm trong hàng đợi và được thử lại sau `NOTIFY_RETRY_AFTER_SECONDS`
giây, chờ nhân đôi mỗi lần, tối đa `NOTIFY_MAX_ATTEMPTS` lần; quá số lần thì thư được đánh dấu hỏng. Mỗi
thư có một dòng trong bảng `notification_deliveries` — người nhận, tiêu đề, nội dung, số lần thử, lỗi cuối,
lúc gửi — để đối soát.

**Tắt:** để `SMTP_HOST` rỗng rồi `docker compose --env-file .env up -d backend`; dừng Mailpit bằng
`docker compose --profile thu-thu stop thu-thu`.

## Quét mã độc tệp đính kèm

Không bật gì thì mỗi tệp vẫn được kiểm ba lớp: đuôi nằm trong danh sách cho phép, **nội dung khớp chữ ký
của định dạng** (tệp đổi đuôi thành `.pdf` bị từ chối), và **dò macro** — tệp Word, Excel, PowerPoint có
macro vẫn được nhận nhưng mang nhãn *"có macro — cẩn thận khi mở"* ở mọi nơi liệt kê tệp. Chữ ký từng
định dạng nằm trong dữ liệu `infra/seed/04-loai-tep-dinh-kem.sql`.

Lớp thứ tư là quét mã độc bằng [ClamAV](https://github.com/Cisco-Talos/clamav) (GPL-2.0, chạy như dịch
vụ riêng; dịch vụ ứng dụng chỉ gửi tệp qua mạng — xem `LICENSES.md`). Cần thêm khoảng 1 GB bộ nhớ.
Trong `infra/.env`:

```bash
CLAMAV_HOST=quet-tep
```

rồi trong `infra/`:

```bash
docker compose --env-file .env --profile quet-tep up -d
```

ClamAV nạp bộ mẫu nhận diện mất một đến vài phút lúc khởi động. Màn **Hệ thống** có dòng *Quét mã độc
tệp đính kèm*: tắt / sẵn sàng / không phản hồi.

- Tệp bị báo có mã độc: cả lần tải bị từ chối, người gửi thấy tên mẫu mã độc.
- ClamAV không phản hồi: theo `CLAMAV_ON_UNAVAILABLE` — `accept` (mặc định) nhận tệp và gắn nhãn
  *"chưa quét mã độc"*, ghi nhật ký; `reject` từ chối lần tải để người gửi thử lại sau.
- Không có mạng: ảnh ClamAV đã kèm bộ mẫu, quét được ngay; đặt `CLAMAV_NO_FRESHCLAMD=true` để nó không
  thử tải bản cập nhật.

**Tắt:** để `CLAMAV_HOST` rỗng rồi `docker compose --env-file .env up -d backend`; dừng ClamAV bằng
`docker compose --profile quet-tep stop quet-tep`.
