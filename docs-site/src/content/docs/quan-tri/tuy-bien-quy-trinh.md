---
title: Tùy biến quy trình
description: Đổi trạng thái, bước đi, vai trò và ràng buộc chống sai bằng cách sửa dữ liệu khởi tạo — không sửa mã.
sidebar:
  order: 1
---

Toàn bộ quy trình là **dữ liệu** trong tệp
[`infra/seed/01-quy-tac-quy-trinh.sql`](https://github.com/AlaVox-lab/corelens/blob/main/infra/seed/01-quy-tac-quy-trinh.sql).
Engine không biết tên trạng thái nào: nó tra bảng rồi làm theo. Giao diện cũng không giữ bảng
"trạng thái nào hiện nút nào" — nút dựng từ danh sách bước đi mà dịch vụ trả về.

## Các bảng của bộ quy tắc

| Bảng | Chứa gì | Ví dụ trong bộ mẫu |
|---|---|---|
| `states` | Trạng thái: nhãn, có phải trạng thái đầu hay kết thúc, đồng hồ hạn có chạy không | 11 trạng thái; đồng hồ chỉ chạy ở *Đang xử lý*, *Đã leo thang* |
| `transitions` | Bước đi từ trạng thái này sang trạng thái kia: nhãn, có bắt buộc ghi chú không, có phải bước hệ thống tự đi không, có phải bước làm lại không, hạn chờ, bước chính | 32 bước, trong đó 5 bước giữ nguyên trạng thái |
| `roles`, `transition_roles` | Vai trò, và vai nào đi được bước nào | Chỉ điều phối viên phân loại |
| `guards`, `transition_guards` | Ràng buộc chống sai gắn trên từng bước | *Phải thuộc phòng đang giữ hồ sơ*, *Bắt buộc đặt mức ưu tiên*, *Quay về đúng chỗ đã hỏi* |
| `message_kinds` | Loại lời nhắn và ai gửi được | Lời nhắn, Hỏi tiến độ, Nhắn nội bộ |

Toàn văn từng trạng thái, từng bước và ai bấm được ở
[`docs/process-flow.md`](https://github.com/AlaVox-lab/corelens/blob/main/docs/process-flow.md).

## Ví dụ: thêm một bước đi

Bộ mẫu không cho hủy hồ sơ khi đang xử lý — không có bước *Đang xử lý → Đã hủy*, nên nút Hủy không
bao giờ hiện ở đó. Muốn cho phép:

1. Thêm một dòng vào `transitions` (từ `in-progress` sang `cancelled`, nhãn, thứ tự)
2. Thêm dòng vào `transition_roles` cho vai `requester`
3. Gắn ràng buộc `requester-owns-case` để chỉ chính người gửi hủy được
4. Dựng lại cụm với `down -v` (xem [Nâng cấp](../../cai-dat/nang-cap/))

Nút **Hủy yêu cầu** tự hiện ở hồ sơ đang xử lý của người gửi — không sửa dòng mã nào.

## Hai lớp chống sai

1. **Không có đường đi sai.** Bước không có trong bảng thì không có nút, và dịch vụ từ chối nếu ai
   đó gọi thẳng API
2. **Có đường nhưng phải đủ điều kiện.** Ràng buộc trên bước — thiếu lý do, sai phòng, tự điều phối
   hồ sơ mình gửi, hết lượt mở lại — bị chặn với thông báo bằng nhãn tiếng Việt

Mọi lần chuyển trạng thái, dù người bấm hay hệ thống tự đi, đi qua **một cửa duy nhất** trong mã:
tra bảng quy tắc → kiểm vai trò → chạy ràng buộc → ghi nhật ký → cập nhật hồ sơ, trong một giao
dịch.

## Khai sai thì cụm không lên

Hàm `kiem_tra_cau_hinh()` trong cơ sở dữ liệu kiểm cả đồ thị mỗi lần dịch vụ khởi động: trạng thái
không tới được, ngõ cụt không phải trạng thái kết thúc, bước không vai nào đi được, nơi hỏi thêm mà
thiếu đường quay về… Sai thì **dịch vụ ứng dụng dừng khởi động** và nhật ký `backend` chỉ ra lỗi — tốt
hơn để một hồ sơ thật mắc kẹt giữa chừng. Lần đầu dựng cụm, dữ liệu trong `infra/seed/` được nạp rồi
kiểm ngay; sửa `infra/seed/` sau đó chỉ có tác dụng với cụm dựng mới.

## Đổi quy trình khi hệ thống đang chạy

Mỗi hồ sơ ghi lại bộ quy tắc nó dùng lúc tạo (`requests.rule_set_id`) và đi tiếp theo đúng bộ đó
tới khi kết thúc: nút, nhật ký sự kiện và đồng hồ hạn của hồ sơ cũ theo bộ cũ, hồ sơ tạo sau theo
bộ đang bật. Hàng đợi, Hồ sơ của tôi và hộp thư giữ hồ sơ của mọi bộ còn hồ sơ đang mở. Bài kiểm
thử chạy hai bộ song song nằm ở `backend/tests/test_hai_bo_quy_tac.py` (#278, #299); chi tiết ở
`docs/ARCHITECTURE.md` mục 6.1.

Bật bộ mới trên cụm đang chạy là một **bản sửa dữ liệu** của Alembic (#254): chép bộ đang bật thành
phiên bản mới, sửa phiên bản đó, rồi kích hoạt — bước kích hoạt chạy `kiem_tra_cau_hinh()` trước, bộ
mới hỏng thì cả bản sửa hoàn tác. Hồ sơ cũ không mất, không cần dựng lại cụm. Mẫu mã ở
`docs/ARCHITECTURE.md` mục 5.4. Màn quản trị để đổi quy trình ngay trên giao diện (#255) là việc sau.
