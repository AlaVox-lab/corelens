---
title: Danh mục và các con số
description: Phòng ban, loại yêu cầu, trường riêng, mức ưu tiên, lịch làm việc, vai trò — và cơ sở của từng con số trong bộ mẫu.
sidebar:
  order: 2
---

## Đổi ở đâu

Cột "Cụm đang chạy" là cách đổi mà không mất dữ liệu; cột "Dữ liệu mẫu" chỉ có tác dụng với cụm dựng
mới (dữ liệu khởi tạo nạp một lần — [Nâng cấp](../../cai-dat/nang-cap/)).

| Muốn đổi | Cụm đang chạy | Dữ liệu mẫu |
|---|---|---|
| Tên, mô tả, ngưng hay dùng lại một phòng ban | [Màn Cấu hình quy trình](../man-cau-hinh/) | `departments` trong `infra/seed/02-co-cau-to-chuc.sql` |
| Thêm phòng ban | Bản sửa dữ liệu, **và** nhóm phòng ban trong Keycloak | Như trên, **và** nhóm trong realm |
| Loại yêu cầu: tên, mô tả, hạn chuẩn, ân hạn, ngưỡng sắp hạn, ngưng hay dùng | Màn Cấu hình quy trình | `request_types` (cùng tệp) |
| Phòng mặc định của loại yêu cầu | Màn Cấu hình quy trình | `request_type_routing` |
| Giới hạn gia hạn và mở lại, trường riêng của từng loại | Bản sửa dữ liệu | `request_types`, `request_type_fields` |
| Mức ưu tiên: tên, hệ số hạn | Màn Cấu hình quy trình | `priorities` trong `infra/seed/01-quy-tac-quy-trinh.sql` |
| Lịch làm việc, ngày lễ | Bản sửa dữ liệu | `work_calendars`, `work_hours`, `holidays` trong `infra/seed/03-lich-lam-viec.sql`; ngày lễ năm 2027 ở `infra/seed/08-ngay-le-2027.sql` (bản sửa 0033 thêm vào cụm đang chạy) |
| Hạn chờ để hệ thống tự đi | Bộ quy tắc phiên bản mới | cột `auto_after_hours`, `warn_before_hours` trong `01-quy-tac-quy-trinh.sql` |
| Người dùng, vai trò, nhóm phòng ban | Màn quản trị của Keycloak | `infra/keycloak/realm-dx-os-lab.json` |
| Giới hạn tệp đính kèm | `infra/.env` — xem [Cấu hình](../../cai-dat/cau-hinh/) | — |

Bản sửa dữ liệu và bộ quy tắc phiên bản mới: khuôn mẫu ở `docs/ARCHITECTURE.md` mục 5.4.

## Trường riêng theo loại yêu cầu

Mỗi dòng trong `request_type_fields` là một ô trên biểu mẫu: mã, nhãn, kiểu (`text`, `number`,
`date`, `choice`), bắt buộc hay không, lời gợi ý, đơn vị, các lựa chọn. Bộ mẫu:

| Loại | Trường |
|---|---|
| Sự cố thiết bị | Mã tài sản\*, Vị trí\*, Mức ảnh hưởng |
| Cấp quyền phần mềm | Hệ thống cần quyền\*, Mức quyền, Cần trước ngày |
| Giấy xác nhận nhân sự | Loại giấy\*, Số bản\*, Ngôn ngữ |
| Đề xuất mua vật tư | Tên vật tư\*, Số lượng\*, Dự toán, Nhà cung cấp gợi ý |

Dấu \* là trường bắt buộc.

Thêm một dòng là biểu mẫu gửi tự có ô mới, dịch vụ tự kiểm bắt buộc và kiểu, trang hồ sơ và dòng
thời gian tự hiện nhãn và giá trị. Giá trị lưu ở cột `requests.details`.

## Bộ mẫu dùng những con số nào, và vì sao

| Con số | Giá trị mẫu |
|---|---|
| Lịch làm việc | Thứ Hai–Sáu, 08:00–12:00 và 13:00–17:00 — theo Bộ luật Lao động 2019, Điều 105 |
| Hạn chuẩn theo loại | Sự cố thiết bị 8 giờ, Cấp quyền phần mềm 24, Giấy xác nhận nhân sự 48, Đề xuất mua vật tư 72 |
| Hệ số mức ưu tiên | Khẩn 50%, Cao 75%, Bình thường 100%, Thấp 150% |
| Ngưỡng sắp hết hạn | 75% hạn |
| Gia hạn | Mỗi lần tối đa 50% hạn gốc, tối đa 2 lần |
| Mở lại | Tối đa 2 lần; sau khi đóng thì trong 7 ngày làm việc |
| Tự trả về điều phối / tự đóng khi chưa bổ sung / tự đóng *Hoàn tất* | 24 / 40 / 24 giờ làm việc |

Cơ sở và nguồn của từng con số — giá trị mặc định của các nền tảng bàn dịch vụ phổ biến, quy định
pháp luật, hoặc ghi rõ là giá trị mẫu để doanh nghiệp tự đặt — ở
[`docs/process-flow.md` mục 9](https://github.com/AlaVox-lab/dx-os-lab/blob/main/docs/process-flow.md#9-cơ-sở-các-con-số-trong-bộ-quy-tắc-mẫu).
