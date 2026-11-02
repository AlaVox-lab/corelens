---
title: Màn Hệ thống và vận hành
description: Theo dõi tình trạng cụm, chạy bộ quét hạn ngay, quản lý người dùng qua Keycloak.
sidebar:
  order: 3
---

## Màn Hệ thống

Quản trị viên (tài khoản mẫu `khanh.vo`) mở **Hệ thống** (`/he-thong`) để xem tình trạng cụm, đọc
từ điểm kiểm tra sức khỏe của dịch vụ ứng dụng: cổng người dùng, dịch vụ ứng dụng và phiên bản, cơ sở
dữ liệu, bộ quy tắc quy trình đã nạp và có bao nhiêu trạng thái. Người dùng khác không thấy
mục này — trang chủ của họ chỉ có việc cần làm, không có chữ kỹ thuật.

![Màn Hệ thống của quản trị viên](../../../assets/anh/he-thong.png)

Quản trị viên **không đứng trong quy trình**: không đi bước nào trên hồ sơ, không mở hồ sơ ở buồng lái
nào.

## Kiểm sức khỏe không cần đăng nhập

`http://localhost:8000/health` trả tình trạng dịch vụ ứng dụng — dùng được cho công cụ giám sát.

## Bộ quét hạn

Dịch vụ ứng dụng chạy một bộ quét nền, mặc định mỗi 60 giây: leo thang hồ sơ quá hạn và đi các bước
tự động khi hồ sơ nằm im quá hạn chờ. Bật tắt và chu kỳ ở `SLA_SCAN_ENABLED`,
`SLA_SCAN_INTERVAL_SECONDS` trong `.env`. Quản trị viên chạy được một lượt ngay bằng `POST /sla/scan`.

**Thử leo thang mà không phải chờ hết hạn thật** (chỉ trên cụm thử): đẩy một hồ sơ đang xử lý sang quá
hạn — lùi cả mốc vào trạng thái, không thì hồ sơ còn nằm trong ân hạn — rồi chờ một lượt quét:

```bash
docker exec dxlab-postgres psql -U dxlab -d dxlab -c "UPDATE requests SET sla_running_seconds = 999999, sla_segment_since = now() - interval '1 day' WHERE id = <số hồ sơ>"
```

## Người dùng và phòng ban

Người dùng, vai trò và phòng ban quản lý ở Keycloak (`http://localhost:8080`, tài khoản quản trị
trong `.env`):

- **Vai trò** là vai trò của realm: `requester`, `classifier`, `approver`, `handler`, `administrator`
- **Phòng ban** là nhóm dưới đường dẫn `/phong-ban/` (đổi bằng `KEYCLOAK_DEPARTMENT_GROUP_PREFIX`)
- Khóa tài khoản người nghỉ việc thì họ không đăng nhập được và không còn trong danh sách nhận việc
  (tài khoản mẫu `tuan.ngo`)
- Gán vai qua **nhóm** cũng được, như doanh nghiệp thật hay làm — tài khoản mẫu `lan.vu` nhận vai người
  xử lý qua nhóm `/nhom-vai-tro/nguoi-xu-ly`
- Client `dx-directory` không dùng để đăng nhập: đó là tài khoản dịch vụ chỉ đọc, để dịch vụ ứng dụng
  tra tên người trong phòng cho ô chọn người xử lý

Thêm phòng ban mới phải thêm cả nhóm trong Keycloak lẫn dòng trong bảng `departments` — xem
[Danh mục và các con số](../danh-muc-va-con-so/).

## Báo cáo

Apache Superset (`http://localhost:8088`) đã có trong cụm với tài khoản chỉ đọc trên dữ liệu nghiệp
vụ. Bảng điều khiển trên nhật ký sự kiện là giai đoạn kế tiếp, phiên bản `v0.9.0`.
