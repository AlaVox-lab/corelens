---
title: API
description: Tài liệu API của dịch vụ ứng dụng, tự sinh từ mã nguồn theo chuẩn OpenAPI.
sidebar:
  order: 1
---

Dịch vụ ứng dụng (FastAPI) tự sinh tài liệu API theo chuẩn **OpenAPI** từ chính mã nguồn, nên tài
liệu luôn khớp phiên bản đang chạy. Khi cụm đang chạy:

| Địa chỉ | Nội dung |
|---|---|
| `http://localhost:8000/docs` | Giao diện tương tác — xem và gọi thử từng điểm cuối |
| `http://localhost:8000/redoc` | Bản đọc dạng tài liệu |
| `http://localhost:8000/openapi.json` | Bản đặc tả máy đọc được, dùng sinh mã khách |
| `http://localhost:8000/health` | Tình trạng chung (`ok` / `degraded`), không cần đăng nhập, không chi tiết lỗi |
| `http://localhost:8000/system/health` | Chi tiết sức khỏe và nhịp bộ quét, chỉ quản trị viên (màn Hệ thống đọc từ đây) |

## Xác thực

Gần như mọi điểm cuối cần **token truy cập** do Keycloak cấp cho client của cổng, gửi trong header
`Authorization: Bearer <token>`. Dịch vụ tự kiểm chữ ký token theo khóa công khai của Keycloak, đọc
vai trò và phòng ban trong token. Token phải mang `dx-api` trong trường `aud`.

Cổng người dùng giữ token ở phía máy chủ và tự gắn vào lời gọi — trình duyệt không bao giờ thấy token.

## Quy tắc chung

- Tạo hồ sơ, tải tệp lên và gửi lời nhắn có **giới hạn tốc độ** theo người dùng. Vượt giới hạn trả
  `429` kèm header `Retry-After` (số giây) và `detail` dạng `{"code": "rate-limited", "message": …}`
  bằng tiếng Việt. Con số do `.env` quyết — xem [Cấu hình](../../cai-dat/cau-hinh/)
- Chuyển trạng thái hồ sơ: `POST /requests/{case_id}/transitions` (người gửi),
  `/coordination/requests/{case_id}/transitions` (điều phối), `/department/requests/{case_id}/transitions`
  (phòng ban), kèm trạng thái đích. Cả ba gọi vào **cùng một cửa** của engine, kiểm vai và ràng buộc,
  từ chối bằng thông báo tiếng Việt. Gọi thẳng API vẫn bị chặn như trên giao diện
- Chi tiết hồ sơ trả kèm **danh sách bước đi được** cho người đang gọi — giao diện dựng nút từ danh
  sách này
- Lời nhắn nội bộ không bao giờ trả cho người gửi của hồ sơ, ở bất kỳ điểm cuối nào
