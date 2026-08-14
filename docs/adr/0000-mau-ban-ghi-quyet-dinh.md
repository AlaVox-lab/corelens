# ADR-NNNN: <Tiêu đề quyết định, dạng danh từ>

| Mục | Giá trị |
|---|---|
| Trạng thái | Đề xuất · Đã chấp nhận · Đã thay thế bởi ADR-NNNN |
| Ngày | YYYY-MM-DD |
| Không gian kiến trúc | `H` · `P` · `D` · `I` · `core` |
| Issue liên quan | #N |
| Người quyết định | |

---

## Bối cảnh

<Vấn đề cần giải quyết là gì. Ràng buộc nào đang chi phối quyết định này — kỹ thuật,
thời gian, tiêu chí chấm điểm, năng lực nhóm.>

<Nếu quyết định này liên quan tới tiêu chí chấm điểm, nêu rõ tiêu chí và số điểm.>

---

## Các phương án đã cân nhắc

Với mỗi phương án là một nền tảng hoặc thư viện, **bắt buộc** ghi giấy phép và kết
quả đối chiếu với danh sách OSI.

### Phương án A — <tên>

| Mục | Nội dung |
|---|---|
| Giấy phép | |
| Được OSI công nhận | Có · Không |
| Tương thích với MIT | Có · Không · Có điều kiện |
| Tài nguyên khi chạy | |
| Khả năng đóng gói bằng container | |
| Chất lượng tài liệu | |
| Mức độ hoạt động của dự án | |
| Độ khó tích hợp | |

**Ưu điểm**

-

**Nhược điểm**

-

### Phương án B — <tên>

<Cùng cấu trúc như trên>

### Phương án C — <tên>

<Cùng cấu trúc như trên>

---

## Quyết định

<Chọn phương án nào. Viết một câu dứt khoát, không mơ hồ.>

---

## Lý do

<Vì sao chọn phương án đó thay vì các phương án còn lại. Nêu tiêu chí quyết định
chính, không liệt kê lại toàn bộ bảng so sánh.>

<Nếu có phương án bị loại vì giấy phép, nêu rõ — đây là thông tin quan trọng để
người sau không đề xuất lại.>

---

## Cách tích hợp

<Nhúng thư viện vào mã nguồn, hay chạy như dịch vụ độc lập giao tiếp qua mạng.>

<Nếu nền tảng dùng giấy phép copyleft mạnh, bắt buộc là phương án dịch vụ độc lập,
và ghi rõ ranh giới kiến trúc ở đây.>

---

## Hệ quả

**Điều gì trở nên dễ hơn**

-

**Điều gì trở nên khó hơn**

-

**Việc phải làm tiếp sau quyết định này**

- [ ] Cập nhật `docs/ARCHITECTURE.md` mục 3
- [ ] Cập nhật `docs/dependencies.md`
- [ ] Bổ sung vào `docker-compose.yml` nếu là dịch vụ độc lập
- [ ]

---

## Ghi chú

<Thông tin bổ sung: liên kết tới tài liệu chính thức, kết quả dựng thử, số liệu đo
được, hoặc điều kiện có thể khiến quyết định này cần xem lại.>
