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

## Quy tắc chung

- Cổng API giới hạn tốc độ **chung** theo địa chỉ người gọi, cho mọi đường: vượt ngưỡng trả `429` với
  `{"error_msg": …}` và các header `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- Tạo hồ sơ, tải tệp lên và gửi lời nhắn còn có **giới hạn tốc độ** theo người dùng ở dịch vụ. Vượt giới
  hạn trả `429` kèm header `Retry-After` (số giây) và `detail` dạng `{"code": "rate-limited", "message": …}`
  bằng tiếng Việt. Con số của cả hai giới hạn do `.env` quyết — xem [Cấu hình](../../cai-dat/cau-hinh/)
- Chuyển trạng thái hồ sơ: `POST /requests/{case_id}/transitions` (người gửi),
  `/coordination/requests/{case_id}/transitions` (điều phối), `/department/requests/{case_id}/transitions`
  (phòng ban), kèm trạng thái đích. Cả ba gọi vào **cùng một cửa** của engine, kiểm vai và ràng buộc,
  từ chối bằng thông báo tiếng Việt. Gọi thẳng API vẫn bị chặn như trên giao diện
- Chi tiết hồ sơ trả kèm **danh sách bước đi được** cho người đang gọi — giao diện dựng nút từ danh
  sách này
- Lời nhắn nội bộ không bao giờ trả cho người gửi của hồ sơ, ở bất kỳ điểm cuối nào
