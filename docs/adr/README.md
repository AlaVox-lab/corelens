# Bản ghi quyết định kiến trúc

Thư mục này lưu các Architecture Decision Record (ADR) — mỗi tệp ghi lại một
quyết định kiến trúc quan trọng của dự án.

## Vì sao cần

Tiêu chí chấm điểm số 10 của cuộc thi đánh giá mức độ phát triển bền vững của
sản phẩm, căn cứ trên tài liệu kỹ thuật kèm theo. ADR là cách chuẩn hóa để
ghi lại không chỉ *quyết định gì* mà còn *vì sao quyết định như vậy*.

## Quy ước đặt tên

`NNNN-mo-ta-ngan.md`, trong đó `NNNN` là số thứ tự bốn chữ số tăng dần.

Ví dụ: `0001-chon-nen-tang-sso.md`

## Cấu trúc một bản ghi

- **Bối cảnh** — vấn đề cần giải quyết, ràng buộc hiện có
- **Các phương án** — những lựa chọn đã cân nhắc, kèm giấy phép nếu là phần mềm
- **Quyết định** — chọn gì
- **Lý do** — vì sao chọn phương án đó
- **Hệ quả** — điều gì trở nên dễ hơn, điều gì trở nên khó hơn

## Trạng thái

Mỗi bản ghi mang một trạng thái: `Đề xuất`, `Đã chấp nhận`, `Đã thay thế bởi NNNN`.
Bản ghi đã ban hành thì không sửa nội dung — nếu quyết định thay đổi, tạo bản ghi
mới và đánh dấu bản cũ là đã bị thay thế.