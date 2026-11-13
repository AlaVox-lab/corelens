# Chính sách bảo mật

## Phiên bản được hỗ trợ

Dự án đang phát triển nhanh; bản vá bảo mật chỉ làm trên bản phát hành **mới nhất** và nhánh `dev`.

| Phiên bản | Nhận bản vá bảo mật |
|---|---|
| Bản mới nhất ở trang [Releases](https://github.com/AlaVox-lab/dx-os-lab/releases) | Có |
| Các bản cũ hơn | Không — nâng cấp lên bản mới nhất |

## Báo lỗ hổng

**Đừng mở issue công khai cho lỗ hổng bảo mật.** Issue công khai để lộ lỗ hổng trước khi có bản vá.

Báo riêng bằng một trong hai cách:

1. Tính năng **Report a vulnerability** của GitHub ở tab *Security* của kho — báo cáo chỉ người duy
   trì xem được
2. Nhắn riêng cho người điều phối kho mã [@AlaVox-lab](https://github.com/AlaVox-lab)

Nêu càng rõ càng tốt: thành phần bị ảnh hưởng (cổng người dùng, dịch vụ ứng dụng, cấu hình cụm),
phiên bản, các bước tái hiện, mức ảnh hưởng bạn đánh giá.

## Chúng tôi làm gì

- Xác nhận đã nhận báo cáo trong vòng **3 ngày làm việc**
- Đánh giá, báo lại hướng xử lý và thời gian dự kiến
- Phát hành bản vá, ghi công người báo cáo trong ghi chú phát hành nếu người đó đồng ý

## Lưu ý khi triển khai

Tệp `infra/.env.example` chứa **mật khẩu và khóa mẫu công khai**, chỉ dùng để dựng thử. Trước khi
triển khai thật bắt buộc đổi mọi mật khẩu, bí mật và khóa ký — danh sách ở trang tài liệu *Cấu hình*
(`docs-site/src/content/docs/cai-dat/cau-hinh.md`). Realm mẫu có mười ba tài khoản dùng chung một mật
khẩu, chỉ để trình diễn; môi trường thật xóa các tài khoản này, chỉ giữ một tài khoản quản trị rồi tạo
tài khoản thật. Hệ thống không tự chặn tài khoản hay mật khẩu mẫu lúc khởi động — giảng viên hướng dẫn
chốt không làm (#242), vì người cài thường tạo tài khoản thử riêng và phần mềm không phân biệt được.
Các bước ở mục *Trước khi dùng thật* của `README.md`.
