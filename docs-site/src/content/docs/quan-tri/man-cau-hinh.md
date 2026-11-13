---
title: Màn Cấu hình quy trình
description: Xem luồng xử lý đang chạy; sửa hạn, mức ưu tiên, loại yêu cầu và phòng ban ngay trên cổng, không dựng lại cụm.
sidebar:
  order: 0
---

Quản trị viên (tài khoản mẫu `khanh.vo`) mở **Cấu hình quy trình** (`/quan-tri/cau-hinh`) trên thanh
bên. Vai khác không thấy mục này, mở thẳng đường dẫn thì bị từ chối; dịch vụ cũng tự chặn mọi lời gọi
`/admin/config` không mang vai trò quản trị viên.

## Xem

- **Luồng xử lý** của bộ quy tắc đang chạy: mỗi trạng thái, các bước đi tiếp, ai làm, ràng buộc chống
  sai nào gác bước đó, bước nào hệ thống tự đi sau bao nhiêu giờ làm việc
- **Lịch làm việc** mặc định: giờ làm theo thứ, các ngày nghỉ sắp tới
- **Nhật ký thay đổi cấu hình**: ai sửa, lúc nào, trường nào, từ giá trị nào sang giá trị nào

## Sửa

| Danh mục | Sửa được |
|---|---|
| Loại yêu cầu | Tên, mô tả, hạn chuẩn, ân hạn, ngưỡng sắp hết hạn, đang dùng hay ngưng, phòng xử lý mặc định |
| Mức ưu tiên | Tên, hệ số hạn |
| Phòng ban | Tên, mô tả, đang dùng hay ngưng |

Bấm **Sửa** trên một dòng, đổi giá trị, bấm **Xem trước**. Dịch vụ chạy thử lần sửa đó — ghi, kiểm
toàn bộ cấu hình, đếm hồ sơ đang mở bị ảnh hưởng — rồi hoàn tác, và màn hiện tóm tắt:

> Hạn chuẩn (giờ làm việc): 8 → **12**
> 3 hồ sơ đang mở sẽ tính theo hạn mới ngay khi lưu. Cấu hình sau khi sửa đã qua kiểm tra.

Bấm **Lưu** để áp dụng. Thay đổi có hiệu lực ngay cho **mọi** hồ sơ, kể cả hồ sơ đang mở: hạn của hồ
sơ tính lúc đọc từ hạn chuẩn × hệ số ưu tiên, nên không có bản sao nào giữ giá trị cũ.

Lần sửa làm hỏng cấu hình bị từ chối ngay ở bước xem trước, kèm lý do — ví dụ ngưng một phòng đang là
phòng mặc định của một loại yêu cầu:

> Cấu hình sau khi sửa không hợp lệ: Loại yêu cầu đang hoạt động có phòng ban mặc định đã ngưng: …

Đổi phòng mặc định của loại đó sang phòng khác trước, rồi mới ngưng phòng.

## Chưa sửa được trên màn

| Muốn | Làm cách |
|---|---|
| Thêm hay bớt trạng thái, bước đi, vai trò đi bước, ràng buộc | Bộ quy tắc phiên bản mới — [Tùy biến quy trình](../tuy-bien-quy-trinh/) |
| Thêm phòng ban, loại yêu cầu, trường riêng | Bản sửa dữ liệu — [Danh mục và các con số](../danh-muc-va-con-so/) |
| Lịch làm việc, ngày nghỉ | Bản sửa dữ liệu |
| Người dùng và vai trò của họ | Màn quản trị của Keycloak — [Màn Hệ thống và vận hành](../he-thong/) |

Phòng ban mới cần người trong phòng, mà người dùng nằm ở Keycloak — vì vậy thêm phòng không làm trên
màn này.
