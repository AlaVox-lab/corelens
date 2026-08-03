---
name: Khảo sát kỹ thuật
about: Khảo sát, so sánh và đề xuất lựa chọn một nền tảng hoặc kỹ thuật
title: "[Research] "
labels: ["type/research"]
assignees: []
---

## Câu hỏi cần trả lời

Nêu chính xác điều cần quyết định sau khi khảo sát xong.

## Bối cảnh kiến trúc

Khảo sát này phục vụ không gian nào trong khung H-P-D-I? Kết quả sẽ ảnh hưởng
tới thành phần nào của hệ thống?

## Việc cần làm

- [ ] Liệt kê ít nhất ba ứng viên
- [ ] Kiểm tra giấy phép từng ứng viên có nằm trong danh sách được OSI công nhận
- [ ] Kiểm tra tính tương thích giấy phép với MIT
- [ ] So sánh theo bảng tiêu chí bên dưới
- [ ] Dựng thử ít nhất một ứng viên bằng Docker
- [ ] Viết kết quả vào `docs/`
- [ ] Ghi quyết định thành một bản ghi quyết định kiến trúc trong `docs/adr/`

## Bảng so sánh

| Tiêu chí | Ứng viên A | Ứng viên B | Ứng viên C |
|----------|-----------|-----------|-----------|
| Giấy phép | | | |
| Được OSI công nhận | | | |
| Tương thích với MIT | | | |
| Tài nguyên khi chạy | | | |
| Khả năng đóng gói bằng container | | | |
| Chất lượng tài liệu | | | |
| Mức độ hoạt động của dự án | | | |
| Độ khó tích hợp | | | |

## Định nghĩa hoàn thành

- Có tài liệu so sánh trong `docs/`
- Có bản ghi quyết định kiến trúc nêu rõ phương án chọn và lý do
- Cả nhóm đã đọc và thống nhất

## Lưu ý về giấy phép

Một số nền tảng tự nhận là nguồn mở nhưng dùng giấy phép không nằm trong danh
sách được OSI công nhận. Cần đối chiếu tên giấy phép với danh sách chính thức
tại https://opensource.org/licenses trước khi đánh giá tính năng.

Với các giấy phép copyleft mạnh, ghi rõ phương án tích hợp dự kiến để tránh
xung đột với giấy phép của dự án.
