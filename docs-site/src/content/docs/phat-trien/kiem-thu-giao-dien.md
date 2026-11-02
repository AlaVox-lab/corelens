---
title: Kiểm thử giao diện
description: Kịch bản kiểm tra giao diện qua đăng nhập thật — bốn vai, bốn cấu hình hiển thị, một lệnh.
sidebar:
  order: 3
---

Thư mục `e2e/` chứa kịch bản kiểm tra giao diện chạy bằng
[Playwright](https://playwright.dev) (Apache-2.0). Kịch bản **đăng nhập thật** qua trang của
Keycloak cho từng vai, không tự đúc cookie phiên — một lỗi đăng nhập từng bị che đúng vì kiểm thử tự
đúc cookie.

## Chạy

Cần cụm đang chạy (xem [Cài đặt](../../cai-dat/cai-dat/)) và Node.js 22 trở lên. Đứng ở thư mục
`e2e/`:

```bash
npm ci
npm run cai-trinh-duyet   # tải Chromium cho Playwright, chỉ lần đầu
npm run kiem
```

Một lượt khoảng hai phút. Kết quả:

| Ở đâu | Nội dung |
|---|---|
| Màn hình terminal | Từng bài đạt hay hỏng |
| `e2e/ket-qua/anh/<cấu hình>/` | Ảnh chụp từng màn của từng vai |
| `e2e/ket-qua/bao-cao/` | Báo cáo HTML, mở bằng `npm run bao-cao`; bài hỏng kèm bản ghi thao tác |

Thư mục `ket-qua/` chứa cả trạng thái đăng nhập của các tài khoản thử, đã nằm trong `.gitignore`.

| Biến | Mặc định | Dùng khi |
|---|---|---|
| `CONG` | `http://localhost:3000` | Cổng chạy ở địa chỉ khác |
| `KENH` | trống | Đặt `chrome` để dùng Chrome cài sẵn trên máy, khỏi tải Chromium |
| `MAT_KHAU` | `matkhau123` | Realm thử dùng mật khẩu khác |

:::caution
Kịch bản **gửi một hồ sơ thật** để có việc chờ cho điều phối viên. Chạy trên cụm thử, không chạy trên
hệ thống đang dùng thật.
:::

## Kịch bản kiểm gì

Bước chuẩn bị: bốn tài khoản đăng nhập thật; `an.nguyen` gửi một yêu cầu *Sự cố thiết bị* qua biểu
mẫu, điền cả trường riêng bắt buộc.

Rồi chạy cùng một bộ bài ở **bốn cấu hình**: rộng 1440 px nền sáng, rộng nền tối, hẹp 375 px, và bật
*giảm chuyển động*.

| Vai | Màn | Điều kiện |
|---|---|---|
| Người gửi `an.nguyen` | Trang chủ, Gửi yêu cầu, Hồ sơ của tôi, hồ sơ vừa gửi, Hộp thư | Hồ sơ vừa gửi có trong danh sách; không thấy mục Hệ thống, mở thẳng `/he-thong` thì bị từ chối |
| Điều phối viên `binh.tran` | Trang chủ, Hàng đợi điều phối, hồ sơ vừa gửi | Số ở ô *Chờ bạn*, câu chào và số dòng *Cần bạn xử lý* khớp nhau; hồ sơ vừa gửi nằm trong việc chờ với nút *Phân loại yêu cầu*, bấm vào mở đúng bước đó ở bảng thao tác; ngăn xem nhanh mở từ dòng, duyệt tới 10 hồ sơ bằng phím mũi tên, Esc đóng và trả tiêu điểm về dòng, ở 375 px chiếm toàn màn hình; mở thẳng `?xem=` thì nút chính là bước chính của hồ sơ; thấy mục Điều phối, không thấy Hệ thống |
| Trưởng phòng `dung.pham` | Trang chủ, Hàng đợi phòng ban, Hộp thư | Số ở ô *Chờ bạn* khớp số dòng việc chờ |
| Quản trị viên `khanh.vo` | Trang chủ, Hệ thống | Thấy mục Hệ thống; màn báo bộ quy tắc quy trình đã nạp |

Mọi màn đều phải: mở được, không có lỗi phía trình duyệt, không có thanh cuộn ngang. Ở cấu hình giảm
chuyển động, không phần tử nào trên trang chủ còn hiệu ứng chạy.

Bộ bài đã qua phép thử đột biến: cố ý làm sai con số *Chờ bạn* trên trang chủ thì hai bài kiểm số
liệu hỏng đúng chỗ; bỏ bước trả tiêu điểm khi đóng ngăn xem nhanh, hay cho nút "sau" đứng yên, thì
bài xem nhanh hỏng đúng chỗ.

## Khi nào chạy

Trước khi mở pull request có sửa giao diện, cùng với `npm run typecheck` và `npm run build` trong
`frontend/`. Thêm màn mới thì thêm vào `e2e/kiem/giao-dien.spec.ts`.
