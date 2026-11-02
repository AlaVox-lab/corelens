---
title: Điều phối viên
description: Phân loại, đặt mức ưu tiên, chọn phòng ban cho từng hồ sơ, chuyển lại khi bị từ chối.
sidebar:
  order: 3
---

Điều phối viên là người đọc từng hồ sơ và quyết định **phòng nào làm**. Ví dụ dùng `binh.tran`.

## Trang chủ và hàng đợi

Trang chủ gom các hồ sơ đang chờ bạn, nút mang tên bước kế tiếp — *Phân loại yêu cầu*, *Chuyển về
phòng ban*. Mặc định xếp theo độ gấp; đổi được và trình duyệt nhớ.

![Trang chủ của điều phối viên](../../../assets/anh/trang-chu-dieu-phoi.png)

Mục **Điều phối** (`/dieu-phoi`) là hàng đợi đầy đủ. Dải số trên đầu bấm để lọc theo trạng thái;
cột *Việc tiếp theo* cho biết bước kế của từng hồ sơ. Ô tìm khớp mã, tiêu đề, người gửi, gõ không
dấu vẫn ra; ba ô chọn lọc theo loại yêu cầu, mức ưu tiên, phòng. Bộ lọc đang bật hiện thành chip
bấm để bỏ. Mỗi trang 50 hồ sơ, dòng cuối ghi đang xem bao nhiêu trên tổng số; địa chỉ trang giữ
bộ lọc và trang đang xem, nên gửi đường dẫn cho đồng nghiệp là họ thấy đúng danh sách đó.

![Hàng đợi điều phối](../../../assets/anh/hang-doi-dieu-phoi.png)

## Một hồ sơ qua tay điều phối

1. **Phân loại yêu cầu** — xác nhận hay sửa loại người gửi chọn, và **đặt mức ưu tiên** (Khẩn,
   Cao, Bình thường, Thấp). Mức ưu tiên quyết định hạn xử lý
2. **Chuyển về phòng ban** — chọn phòng phụ trách. Hệ thống gợi ý theo loại yêu cầu, bạn chọn khác
   được
3. Thiếu thông tin thì **Yêu cầu bổ sung thông tin** trước khi phân loại — người gửi trả lời xong,
   hồ sơ quay về đúng chỗ bạn hỏi

## Khi phòng ban trả hồ sơ

Phòng nhận sai chuyên môn thì **từ chối kèm lý do**, hồ sơ sang *Bị phòng ban từ chối*. Bạn **chuyển
lại sang phòng khác**. Không phòng nào nhận thì kết thúc bằng **Không tiếp nhận, không phòng nào
nhận** — bắt buộc ghi lý do; người gửi có thể tạo hồ sơ mới rõ hơn.

Phòng giữ hồ sơ quá lâu mà chưa xác duyệt: bạn **Rút hồ sơ về điều phối** kèm lý do, hoặc hệ thống
tự trả về sau **24 giờ làm việc**.

## Gia hạn

Trước khi phòng nhận việc, bạn **gia hạn xử lý** được một lần, kèm lý do — tối đa nửa hạn gốc. Các
lần sau do trưởng phòng làm khi hồ sơ đã leo thang.

## Những điều hệ thống chặn

- Bạn **không tự điều phối hồ sơ do chính mình gửi** — người khác phải phân loại. Hàng đợi ghi
  *Bạn gửi — người khác điều phối* ở các hồ sơ đó
- Phân loại mà thiếu mức ưu tiên hay loại yêu cầu, chuyển phòng mà chưa chọn phòng — bị chặn
