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
| Điều phối viên `binh.tran` | Trang chủ, Hàng đợi điều phối, hồ sơ vừa gửi | Số ở ô *Chờ bạn*, câu chào và số dòng *Cần bạn xử lý* khớp nhau (danh sách chạm trần 200 dòng thì dòng ghi chú nói đúng "đang hiện X trên Y"); hồ sơ vừa gửi nằm trong việc chờ với nút *Phân loại yêu cầu*, bấm vào mở đúng bước đó ở bảng thao tác; ngăn xem nhanh mở từ dòng, duyệt tới 10 hồ sơ bằng phím mũi tên, Esc đóng và trả tiêu điểm về dòng, ở 375 px chiếm toàn màn hình; mở thẳng `?xem=` thì nút chính là bước chính của hồ sơ; không hiệu ứng nào quá 300 ms trên trang chủ, hàng đợi và ngăn xem nhanh, mở trang chủ không số nào cuộn; thấy mục Điều phối, không thấy Hệ thống |
| Trưởng phòng `dung.pham` | Trang chủ, Hàng đợi phòng ban, Hộp thư | Số ở ô *Chờ bạn* khớp số dòng việc chờ |
| Quản trị viên `khanh.vo` | Trang chủ, Hệ thống | Thấy mục Hệ thống; màn báo bộ quy tắc quy trình đã nạp |

Mọi màn đều phải: mở được, không có lỗi phía trình duyệt, không có thanh cuộn ngang. Ở cấu hình giảm
chuyển động, không phần tử nào trên trang chủ, hàng đợi, ngăn xem nhanh và khung xác nhận còn hiệu ứng
chạy.

Bộ bài đã qua phép thử đột biến: cố ý làm sai con số *Chờ bạn* trên trang chủ thì hai bài kiểm số
liệu hỏng đúng chỗ; bỏ bước trả tiêu điểm khi đóng ngăn xem nhanh, hay cho nút "sau" đứng yên, thì
bài xem nhanh hỏng đúng chỗ; cho hiện trang dài 0,4 giây, hay cho số cuộn ngay lần dựng đầu, thì bài
chuyển động hỏng đúng chỗ.

## Khả năng tiếp cận

Kịch bản `e2e/kiem/kha-nang-tiep-can.spec.ts` (#435) quét các màn chính bằng
[axe-core](https://github.com/dequelabs/axe-core) qua gói `@axe-core/playwright` (MPL-2.0, chỉ dùng khi
kiểm thử) theo chuẩn **WCAG 2.1 mức A và AA**, cũng đăng nhập thật và chạy ở cả bốn cấu hình — nên tương
phản được đo ở nền sáng, nền tối và màn hẹp. Chạy riêng:

```bash
npx playwright test kiem/kha-nang-tiep-can.spec.ts
```

| Vai | Màn quét |
|---|---|
| Chưa đăng nhập | Trang chủ của cổng, trang đăng nhập Keycloak (chủ đề của dự án) |
| Người gửi | Trang chủ, Gửi yêu cầu bước 1 và bước 2, Hồ sơ của tôi, một hồ sơ |
| Điều phối viên | Trang chủ, Hàng đợi điều phối, một hồ sơ — cả khi đang mở bảng thao tác; Báo cáo: bảng điều khiển và Quy trình thực tế |
| Trưởng phòng | Trang chủ, Hàng đợi phòng ban, bảng Kanban, một hồ sơ của phòng, Hộp thư |
| Người xử lý | Hàng đợi phòng ban, Hộp thư |
| Quản trị viên | Hệ thống, Cấu hình quy trình |

Bài **hỏng khi còn vi phạm mức `critical` hoặc `serious`**, in mã luật, số phần tử và bộ chọn đầu tiên.
Vi phạm mức nhẹ hơn không làm hỏng bài; số của mọi mức ghi ở `e2e/ket-qua/kha-nang-tiep-can/<cấu hình>.jsonl`,
mỗi màn một dòng. Bài chờ mọi hiệu ứng hiện ra chạy xong rồi mới quét, vì chữ đang mờ dần cho số tương
phản thấp giả.

**Loại trừ duy nhất**: khung Superset nhúng ở màn Báo cáo (`.bao-cao-khung iframe`) — đó là trang của
Superset, nền tảng bên thứ ba, dự án không sửa mã của nó. Phần của cổng quanh khung vẫn được quét.

Cùng tệp có hai bài **chỉ dùng bàn phím**: gửi một yêu cầu từ đầu tới cuối ở *Gửi yêu cầu*, và phân loại
một hồ sơ ở trang hồ sơ của điều phối viên. Mỗi lần Tab, bài kiểm tiêu điểm đi tới theo thứ tự trên trang
(không nhảy lùi) và phần tử đang giữ tiêu điểm có viền nhìn thấy; Tab đầu tiên của mọi trang là lối
**Bỏ qua tới nội dung chính**.

Sửa giao diện mà bài này hỏng thì sửa ở mã của cổng — biến màu trong `frontend/app/globals.css`, nhãn,
thứ tự tiêu điểm — không tắt luật axe cho bài xanh.

## Khi nào chạy

Trước khi mở pull request có sửa giao diện, cùng với `npm run typecheck`, `npm run lint` và
`npm run build` trong `frontend/`. Thêm màn mới thì thêm vào `e2e/kiem/giao-dien.spec.ts`.

Trên tích hợp liên tục, quy trình `.github/workflows/e2e.yml` chạy **toàn bộ** kịch bản cho mỗi pull
request vào `main` và khi bấm *Run workflow* ở thẻ *Actions* — không chạy cho pull request vào `dev` vì
dựng trọn cụm mất khoảng nửa giờ. Quy trình dựng cụm mặc định từ `infra/.env.example` trên máy sạch,
chờ Keycloak nạp xong realm rồi chạy bằng Chromium do Playwright tải về; ô `kenh` khi chạy tay đặt biến
`KENH`. Bài hỏng thì tải tệp `bao-cao-e2e` ở trang lượt chạy: thư mục `bao-cao/` mở bằng
`npx playwright show-report bao-cao`, vết của từng bài hỏng (`trace.zip` trong `tam/`) mở ở
`https://trace.playwright.dev`.
