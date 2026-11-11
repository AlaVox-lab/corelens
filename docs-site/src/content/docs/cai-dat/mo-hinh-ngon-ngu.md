---
title: Mô hình ngôn ngữ (tùy chọn)
description: Bật mô hình ngôn ngữ cục bộ để gợi ý loại yêu cầu, mức ưu tiên, phòng ban cho điều phối viên — tải mô hình, biến môi trường, bộ nhớ cần, cách tắt, và kết quả đo độ chính xác.
sidebar:
  order: 5
---

Cổng có thể gợi ý **loại yêu cầu, mức ưu tiên và phòng ban** cho điều phối viên ngay khi hồ sơ được
gửi. Gợi ý do một mô hình ngôn ngữ nhỏ chạy **ngay trên máy của cụm** sinh ra — không gửi dữ liệu ra
ngoài. Phần này **tùy chọn**: cụm mặc định không có mô hình, và mọi thao tác chạy thủ công đầy đủ.

Mô hình **chỉ gợi ý**: thẻ gợi ý điền sẵn ô chọn trên màn điều phối, điều phối viên giữ hay đổi rồi
bấm đúng nút thao tác như thường. Hệ thống ghi lại họ giữ hay đổi gợi ý, để đo độ chính xác thật trên
bảng điều khiển (biểu đồ *Tỷ lệ ghi đè gợi ý*). Mô hình tắt, chậm hay trả lời sai thì đơn giản là không
có gợi ý — không thao tác nào bị chặn hay chậm đi.

## Thành phần

| Thành phần | Phiên bản | Giấy phép |
|---|---|---|
| llama.cpp server (dịch vụ `mo-hinh`) | ảnh `ghcr.io/ggml-org/llama.cpp:server-b11889` | MIT |
| Mô hình Qwen2.5-1.5B-Instruct, bản nén `q4_k_m` | tệp GGUF 1,12 GB, kho `Qwen/Qwen2.5-1.5B-Instruct-GGUF` | Apache-2.0 |

Quyết định và lý do: ADR-0008 trong `docs/adr/`.

## Cần gì

- Thêm khoảng **1,5 GB bộ nhớ** cho dịch vụ mô hình (đo: 1,08 GiB lúc đã nạp mô hình, ngữ cảnh 4096)
- Thêm khoảng **2,4 GB ổ đĩa**: ảnh llama.cpp 1,2 GB và tệp mô hình 1,1 GB
- Không cần GPU. Trên CPU Intel Core i7-13700HX, mỗi hồ sơ mất 3–7 giây (xem kết quả đo dưới)

## Bật

Ở **gốc kho mã**, tải tệp mô hình vào volume Docker của cụm:

```bash
python scripts/tai_mo_hinh.py
```

Lệnh tải từ kho chính thức của Qwen trên Hugging Face, ghim theo mã phiên bản của kho, và kiểm
SHA-256 trước khi đặt vào volume `mo-hinh` — lệch mã băm là dừng. Volume đã có tệp đúng thì không tải
lại. Cụm dựng với tên dự án Compose khác `dx-os-lab` thì thêm `--du-an <tên>`; muốn giữ tệp tải về ở
chỗ khác thư mục tạm thì thêm `--thu-muc-tam <thư mục>`.

Rồi trong `infra/.env` đặt địa chỉ mô hình, và dựng lại với hồ sơ `tri-tue` (trong `infra/`):

```bash
# infra/.env
LLM_URL=http://mo-hinh:8080
```

```bash
docker compose --env-file .env --profile tri-tue up -d
```

Màn **Hệ thống** của quản trị viên có thêm dòng **Mô hình ngôn ngữ**: *sẵn sàng*, *tắt*, hoặc *không
phản hồi* kèm lý do (ví dụ đang nạp mô hình). Cùng tình trạng có ở trường `language_model` của
`GET /system/health`. Mô hình là tùy chọn nên dòng này không làm tình trạng chung của cụm xấu đi.

## Biến môi trường

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `LLM_URL` | rỗng | Địa chỉ dịch vụ mô hình. **Rỗng là tắt** |
| `LLM_TIMEOUT_SECONDS` | `30` | Hạn chót một lần hỏi mô hình; quá hạn là không có gợi ý |
| `LLM_CONTEXT_SIZE` | `4096` | Ngữ cảnh của dịch vụ mô hình |
| `LLM_THREADS` | `4` | Số luồng CPU dịch vụ mô hình dùng |
| `SUGGEST_SCAN_INTERVAL_SECONDS` | `30` | Nhịp bộ quét bù gợi ý |
| `SUGGEST_MAX_ATTEMPTS` | `3` | Số lần thử tối đa cho một hồ sơ khi mô hình trả lời hỏng |
| `SUGGEST_RETRY_AFTER_SECONDS` | `600` | Khoảng cách tối thiểu giữa hai lần thử |
| `SUGGEST_DEPARTMENT_FROM_MODEL` | `false` | Cho gợi ý phòng ban của mô hình thay gợi ý theo bảng ánh xạ |

Gợi ý sinh theo hai đường: ngay sau khi hồ sơ được gửi (chạy nền, người gửi không phải chờ), và một
**bộ quét bù** chạy định kỳ cho hồ sơ còn chờ điều phối mà chưa có gợi ý — ví dụ hồ sơ gửi lúc mô hình
đang tắt. Bộ quét có dòng riêng *Bộ quét gợi ý phân loại* trên màn Hệ thống khi mô hình bật.

**Phòng ban.** Mặc định, gợi ý phòng ban vẫn lấy từ bảng ánh xạ loại yêu cầu → phòng
(`request_type_routing`); mô hình chỉ gợi ý loại và mức ưu tiên. Chỉ bật
`SUGGEST_DEPARTMENT_FROM_MODEL=true` khi đo trên bộ mẫu thấy mô hình đúng **từ 80 %** và hơn bảng ánh xạ.

## Tắt

Để `LLM_URL` rỗng trong `infra/.env` rồi dựng lại không kèm hồ sơ, và dừng dịch vụ mô hình:

```bash
docker compose --env-file .env up -d
docker compose --env-file .env --profile tri-tue stop mo-hinh
```

Chỉ dừng dịch vụ mô hình mà vẫn để `LLM_URL` cũng an toàn: gửi và phân loại tay chạy bình thường, màn
Hệ thống báo *không phản hồi*, gợi ý tự có lại khi mô hình lên.

> `docker compose down -v` xóa **cả volume `mo-hinh`**: muốn bật lại phải chạy lại
> `python scripts/tai_mo_hinh.py`. `down` không kèm `-v` thì giữ tệp mô hình.

## Đo độ chính xác

Bộ mẫu có nhãn: 80 hồ sơ tiếng Việt ở `backend/tests/du_lieu/bo_mau_phan_loai.json` — 20 hồ sơ mỗi loại
yêu cầu, 20 mỗi mức ưu tiên, đủ bốn phòng ban; bốn hồ sơ người gửi cố ý chọn sai loại. Trên cụm đã bật
mô hình, ở gốc kho mã:

```bash
python scripts/do_chinh_xac_goi_y.py
```

Lệnh chạy từng hồ sơ mẫu qua đúng lớp gọi mô hình của dịch vụ ứng dụng (bên trong container
`dxlab-backend`, đổi bằng `--container`), không ghi gì vào cơ sở dữ liệu, và in độ chính xác từng loại
gợi ý, các cặp nhầm, thời gian trung bình, cùng so sánh với bảng ánh xạ phòng ban.

### Kết quả đo — 11/11/2026

> Nhãn của bộ mẫu đã được nhóm duyệt ngày 11/11/2026; số đo trên là số chính thức của bản này.

Mô hình `qwen2.5-1.5b-instruct-q4_k_m`, llama.cpp server `b11889`, chỉ CPU — Intel Core i7-13700HX,
Docker Desktop trên WSL2, dịch vụ mô hình 4 luồng, ngữ cảnh 4096, nhiệt độ 0, hạn chót 30 giây.

| Gợi ý | Đúng | Ghi chú |
|---|---|---|
| Loại yêu cầu | 74/80 = **92,5 %** | Nhầm nhiều nhất: đề xuất mua vật tư → sự cố thiết bị (4) |
| Mức ưu tiên | 31/80 = **38,8 %** | Hay hạ một bậc: khẩn → cao (10), thấp → bình thường (10) |
| Phòng ban (mô hình) | 50/80 = **62,5 %** | Nhầm nhiều nhất: công nghệ thông tin → nhân sự (15) |
| Phòng ban (bảng ánh xạ, theo loại người gửi chọn) | 69/80 = **86,2 %** | |

Có gợi ý cho 80/80 hồ sơ, không mã nào ngoài danh mục. Thời gian trung bình 4,3 giây mỗi hồ sơ, dài nhất
7,2 giây. Kết luận: **giữ `SUGGEST_DEPARTMENT_FROM_MODEL=false`** — mô hình dưới ngưỡng 80 % và kém bảng
ánh xạ. Gợi ý mức ưu tiên của mô hình cỡ này còn yếu; đó là gợi ý, điều phối viên vẫn quyết định, và tỷ
lệ ghi đè trên bảng điều khiển cho biết độ chính xác thật theo thời gian. Câu lý do mô hình viết kèm gợi ý
đôi khi chỉ chép lại mô tả, hoặc viết bằng tiếng Anh.

Đã thử cho mô hình viết lý do trước khi chọn mã: loại yêu cầu tụt xuống 81,2 %, mức ưu tiên 33,8 % —
nên giữ thứ tự chọn mã trước.
