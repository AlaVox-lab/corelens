---
title: API
description: Tài liệu API của dịch vụ ứng dụng, tự sinh từ mã nguồn theo chuẩn OpenAPI.
sidebar:
  order: 1
---

Dịch vụ ứng dụng (FastAPI) tự sinh tài liệu API theo chuẩn **OpenAPI** từ chính mã nguồn, nên tài
liệu luôn khớp phiên bản đang chạy. Mọi lời gọi API từ ngoài cụm đi qua **cổng API** (Apache APISIX) ở
cổng `9080` — đường dẫn giữ nguyên như của dịch vụ. Khi cụm đang chạy:

| Địa chỉ | Nội dung |
|---|---|
| `http://localhost:9080/docs` | Giao diện tương tác — xem và gọi thử từng điểm cuối (nút **Authorize** để dán token) |
| `http://localhost:9080/redoc` | Bản đọc dạng tài liệu |
| `http://localhost:9080/openapi.json` | Bản đặc tả máy đọc được, dùng sinh mã khách |
| `http://localhost:9080/health` | Tình trạng chung (`ok` / `degraded`), không cần đăng nhập, không chi tiết lỗi |
| `http://localhost:9080/system/health` | Chi tiết sức khỏe và nhịp bộ quét, chỉ quản trị viên (màn Hệ thống đọc từ đây) |

Dịch vụ ứng dụng không mở cổng `8000` ra máy ở cấu hình mặc định; gọi thẳng nó chỉ được khi thêm tệp
`docker-compose.phat-trien.yml` — xem [Cài đặt](../../cai-dat/cai-dat/).

## Xác thực

Mọi điểm cuối, trừ `/`, `/health`, `/health/live`, `/health/ready` và bốn đường tài liệu ở trên, cần
**token truy cập** do Keycloak cấp, gửi trong header `Authorization: Bearer <token>`. Token được kiểm
**hai lần**:

1. **Tại cổng API** — chữ ký theo khóa công khai của Keycloak, nơi phát, hạn dùng, và `dx-api` trong
   trường `aud`. Hỏng thì lời gọi không tới dịch vụ: thiếu token, hết hạn, ký sai nhận `401` kèm
   `WWW-Authenticate`; token phát cho client khác nhận `403`
2. **Tại dịch vụ** — kiểm lại đủ bốn thứ trên, rồi đọc vai trò và phòng ban trong token để phân quyền

Cổng người dùng giữ token ở phía máy chủ và tự gắn vào lời gọi — trình duyệt không bao giờ thấy token.
Lời gọi của cổng người dùng cũng đi qua cổng API.

## API của nền tảng lõi — `/core/v1`

Đề thi tách **nền tảng lõi không giao diện** (Tầng 1) khỏi **ứng dụng minh họa** (Tầng 2). Phần API dành
cho mọi ứng dụng tầng trên nằm dưới tiền tố có phiên bản `/core/v1`, nhóm theo dịch vụ lõi; trong `/docs`
năm nhóm này đứng đầu, nhãn bắt đầu bằng **"Lõi — "**. Các đường còn lại thuộc ứng dụng minh họa — cổng vận
hành yêu cầu nội bộ — và có thể đổi theo giao diện của nó.

| Nhóm | Điểm cuối |
|---|---|
| Luồng công việc | `GET /core/v1/workflow/request-types`, `/states`, `/priorities`, `/departments` — danh mục cấu hình · `POST /core/v1/workflow/requests` — tạo hồ sơ · `GET /core/v1/workflow/requests`, `/requests/{case_id}` — danh sách, chi tiết kèm **bước đi được** (`allowed_transitions`) và **lịch sử** (`history`) · `POST /core/v1/workflow/requests/{case_id}/transitions` — đi một bước |
| Tệp | `GET /core/v1/files/policy` · `POST /core/v1/files/requests/{case_id}/attachments` · `GET /core/v1/files/{attachment_id}` |
| Nhật ký sự kiện | `GET /core/v1/events?format=csv\|json&from=…&to=…` — chỉ quản trị viên |
| Thông báo | `GET /core/v1/notifications/preferences` · `POST /core/v1/notifications/preferences/{code}` |
| Định danh | `GET /core/v1/identity/me` |

Mỗi đường của lõi là **cùng một điểm cuối** với một đường cũ mà cổng người dùng đang dùng (ví dụ
`/core/v1/workflow/requests` và `/requests`): cùng kết quả, cùng phân quyền, cùng giới hạn tốc độ. Bảng ánh
xạ đầy đủ và danh sách điểm cuối thuộc ứng dụng minh họa ở `docs/ARCHITECTURE.md` mục 2.3.

Bước chuyển qua lõi là cửa của người gửi: chỉ trên hồ sơ do chính người gọi tạo, và chỉ những bước mà vai
của người gọi đi được theo quy trình đang chạy. Phân loại, nhận việc… là việc của hai buồng lái trong ứng
dụng minh họa.

### Token cho ứng dụng khác: tài khoản dịch vụ

Một ứng dụng không có người dùng đăng nhập (phần mềm nhân sự, ứng dụng di động, kịch bản tích hợp) xin token
bằng **luồng client credentials** của Keycloak, với client `dx-integration` — biến `KEYCLOAK_INTEGRATION_*`
trong `.env`, xem [Cấu hình](../../cai-dat/cau-hinh/):

```bash
curl -s http://localhost:8080/realms/dx-os-lab/protocol/openid-connect/token \
  -d grant_type=client_credentials \
  -d client_id=dx-integration \
  -d client_secret=<KEYCLOAK_INTEGRATION_SECRET>
```

Token mang `dx-api` trong `aud` và vai `requester`, nên qua được cổng API và dịch vụ như token của người dùng
— không phép kiểm nào được nới. Hồ sơ tài khoản dịch vụ tạo mang nhãn người gửi là tên client
(`dx-integration`). Rồi gọi lõi qua cổng API:

```bash
curl -s http://localhost:9080/core/v1/workflow/request-types -H "Authorization: Bearer <token>"
```

Ví dụ đầy đủ, chỉ dùng thư viện chuẩn của Python: `examples/goi-loi/` — tạo một hồ sơ, đi một bước, in lịch
sử, toàn bộ qua `/core/v1`. Cụm dựng trước bản có `/core/v1` thì tạo client trước bằng
`python scripts/tai_khoan_dich_vu.py` — xem [Nâng cấp](../../cai-dat/nang-cap/).

## Quy tắc chung

- Cổng API giới hạn tốc độ **chung** theo địa chỉ người gọi, cho mọi đường: vượt ngưỡng trả `429` với
  `{"error_msg": …}` và các header `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- Tạo hồ sơ, tải tệp lên và gửi lời nhắn còn có **giới hạn tốc độ** theo người dùng ở dịch vụ. Vượt giới
  hạn trả `429` kèm header `Retry-After` (số giây) và `detail` dạng `{"code": "rate-limited", "message": …}`
  bằng tiếng Việt. Con số của cả hai giới hạn do `.env` quyết — xem [Cấu hình](../../cai-dat/cau-hinh/)
- Chuyển trạng thái hồ sơ: `POST /requests/{case_id}/transitions` (người gửi, cũng là
  `/core/v1/workflow/requests/{case_id}/transitions` của lõi), `/coordination/requests/{case_id}/transitions`
  (điều phối), `/department/requests/{case_id}/transitions` (phòng ban), kèm trạng thái đích. Cả ba gọi vào
  **cùng một cửa** của engine, kiểm vai và ràng buộc, từ chối bằng thông báo tiếng Việt. Gọi thẳng API vẫn
  bị chặn như trên giao diện
- Chi tiết hồ sơ trả kèm **danh sách bước đi được** cho người đang gọi — giao diện dựng nút từ danh
  sách này
- Lời nhắn nội bộ không bao giờ trả cho người gửi của hồ sơ, ở bất kỳ điểm cuối nào
