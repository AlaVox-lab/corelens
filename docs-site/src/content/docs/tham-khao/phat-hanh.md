---
title: Phát hành và giấy phép
description: Các bản phát hành, nhật ký thay đổi, giấy phép của dự án và các thành phần.
sidebar:
  order: 2
---

## Bản phát hành

Mỗi bản phát hành có thẻ theo **Semantic Versioning** và tệp mã nguồn `.tar.gz` ở trang
[Releases](https://github.com/AlaVox-lab/dx-os-lab/releases). Nhật ký thay đổi
[`CHANGELOG.md`](https://github.com/AlaVox-lab/dx-os-lab/blob/main/CHANGELOG.md) sinh tự động từ
lịch sử commit.

| Bản | Nội dung chính |
|---|---|
| `v0.9.0` | Khép Giai đoạn 3 — không gian Dữ liệu: lớp báo cáo trên nhật ký sự kiện, bảng điều khiển dựng từ tệp cấu hình và nhúng trong cổng theo phòng của người xem, xuất nhật ký CSV và JSON, dữ liệu trình diễn |
| `v0.8.0` | Khép đợt làm mới giao diện: phân trang và bộ lọc phía dịch vụ, ngăn xem nhanh hồ sơ, quy tắc chuyển động, kiểm tra giao diện qua đăng nhập thật, trang tài liệu; hồ sơ đang chạy giữ bộ quy tắc cũ khi đổi quy trình |
| `v0.7.0` | Cổng theo việc cần làm: trang chủ theo vai, thanh bên, hàng đợi có dải số, trường riêng theo loại yêu cầu, đăng nhập tiếng Việt, tích hợp liên tục |
| `v0.6.0` | Khép Giai đoạn 2: mở lại có giới hạn, trạng thái *Không tiếp nhận*, tệp đính kèm, rà từ ngữ |
| `v0.5.0` | Lịch làm việc, hồ sơ nằm im tự trả về hay tự đóng, hạn theo mức ưu tiên, gia hạn; bản cài đặt đầu tiên cho người ngoài |
| `v0.4.0` | Khép luồng thủ công: cổng gửi yêu cầu, buồng lái điều phối và phòng ban, lời nhắn, liên hệ người gửi |
| `v0.3.0` | Engine máy trạng thái, đồng hồ hạn và tự leo thang, tích hợp định danh |
| `v0.2.0` | Khép Giai đoạn 1: chốt kiến trúc, hạ tầng dựng bằng một lệnh |
| `v0.1.0` | Bộ khung kho mã và tài liệu chuẩn |

Xem đầy đủ ở trang Releases. Lộ trình các bản tới ở
[`docs/ROADMAP.md`](https://github.com/AlaVox-lab/dx-os-lab/blob/main/docs/ROADMAP.md): tầng Trí tuệ
từ `v0.10.0`.

## Giấy phép

Dự án phát hành theo giấy phép [MIT](https://github.com/AlaVox-lab/dx-os-lab/blob/main/LICENSE).
Mọi tệp mã nguồn mang định danh giấy phép SPDX ở đầu tệp.

Mọi phụ thuộc đều có giấy phép thuộc danh sách OSI và tương thích MIT, ghi trong
[`docs/dependencies.md`](https://github.com/AlaVox-lab/dx-os-lab/blob/main/docs/dependencies.md).
Các nền tảng lắp ghép — Keycloak, SeaweedFS, Apache Superset — đều Apache-2.0, chạy như dịch vụ
độc lập, không sửa mã nguồn.

## So sánh với sản phẩm cùng loại

[`docs/so-sanh-san-pham.md`](https://github.com/AlaVox-lab/dx-os-lab/blob/main/docs/so-sanh-san-pham.md)
đặt dự án cạnh tám sản phẩm trong nước và quốc tế, nêu điểm khác và chỗ còn kém.
