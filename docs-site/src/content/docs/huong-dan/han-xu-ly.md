---
title: Hạn xử lý và tự động
description: Hạn đếm theo giờ làm việc và mức ưu tiên, sắp hết hạn, leo thang, gia hạn, và các bước hệ thống tự đi.
sidebar:
  order: 6
---

## Hạn đếm theo giờ làm việc

Mọi hạn đếm bằng **giờ làm việc** của một lịch: mẫu là thứ Hai tới thứ Sáu, 08:00–12:00 và
13:00–17:00 giờ Việt Nam, trừ ngày lễ. Hồ sơ nhận tối thứ Sáu chỉ bắt đầu tính hạn từ 08:00 thứ Hai.

**Hạn xử lý = hạn chuẩn của loại yêu cầu × hệ số mức ưu tiên.** Ví dụ Sự cố thiết bị 8 giờ:

| Mức ưu tiên | Hệ số | Hạn |
|---|---|---|
| Khẩn | 50% | 4 giờ |
| Cao | 75% | 6 giờ |
| Bình thường | 100% | 8 giờ |
| Thấp | 150% | 12 giờ |

Đồng hồ chỉ chạy khi **phòng ban đang giữ việc** — *Đang xử lý* và *Đã leo thang*. Thời gian chờ
người gửi bổ sung thông tin không tính vào hạn của phòng.

## Sắp hết hạn, quá hạn, leo thang

- Dùng tới **75%** hạn thì hồ sơ chuyển vàng, vào nhóm *Sắp hết hạn* của hàng đợi
- Quá hạn thì bộ quét nền **tự leo thang**: hồ sơ sang *Đã leo thang*, lên trưởng phòng
- Trưởng phòng phân công lại; người mới có **ân hạn** (mẫu một phần tư hạn) trước khi bị leo thang
  lần nữa. Hồ sơ vẫn được ghi nhận là đã quá hạn

## Gia hạn

Gia hạn kèm lý do, ghi vào dòng thời gian. Mỗi lần tối đa **50% hạn gốc**, tổng tối đa **2 lần**:
điều phối viên gia hạn lần đầu trước khi phòng nhận việc, trưởng phòng gia hạn khi hồ sơ đã leo thang.

## Hệ thống tự đi khi hồ sơ nằm im

| Hồ sơ đang ở | Không ai bấm trong | Thì | Báo trước |
|---|---|---|---|
| *Chờ phòng ban xác duyệt* | 24 giờ làm việc | Tự trả về điều phối viên | 4 giờ |
| *Chờ bổ sung thông tin* | 40 giờ làm việc | Tự đóng | 24 giờ |
| *Hoàn tất* | 24 giờ làm việc | Tự đóng | 8 giờ |

Trang chủ xếp các hồ sơ sắp tự đi lên trên. Mỗi bước tự đi ghi vào dòng thời gian là *Hệ thống*,
kèm lý do.

Mọi con số trên là dữ liệu doanh nghiệp tự đặt — cơ sở chọn từng con số ở
[Danh mục và các con số](../../quan-tri/danh-muc-va-con-so/).
