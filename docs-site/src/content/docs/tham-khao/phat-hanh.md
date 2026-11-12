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
| `v0.14.0` | Nền tảng vận hành: thông báo thư điện tử qua hàng đợi có thử lại, kiểm chữ ký và quét mã độc tệp đính kèm (tùy chọn), nhật ký có cấu trúc với mã yêu cầu, điểm cuối sống/sẵn sàng và số đo; khép Giai đoạn 4 |
| `v0.13.0` | Gợi ý người xử lý cho trưởng phòng theo tải việc và kinh nghiệm; hồ sơ đã giải quyết tương tự khi người gửi đang soạn (pgvector); khuyến nghị cải tiến trên màn quy trình thực tế, mọi con số tra được từ kết quả khai phá |
| `v0.12.0` | Mô hình ngôn ngữ chạy trong cụm, bật theo lựa chọn: gợi ý loại yêu cầu, mức ưu tiên, phòng ban cho điều phối viên, người giữ hay đổi bằng thao tác cũ; kho ghi rõ mô hình nhiều giấy phép (dịch vụ khai phá theo AGPL-3.0) |
| `v0.11.0` | Khai phá quy trình thực tế từ nhật ký sự kiện trong dịch vụ riêng, có bộ máy dự phòng; màn Quy trình thực tế trong mục Báo cáo: sơ đồ tương tác, câu kết luận dựng từ số liệu, điểm nghẽn và nhánh lệch bấm ra đúng hồ sơ |
| `v0.10.0` | Nền tảng vận hành: nâng cấp từ `v0.9.1` không mất dữ liệu (lược đồ cấu hình trong migration, bộ quy tắc phiên bản mới), tiêu đề bảo mật và giới hạn tốc độ, bộ quét có khóa và nhịp sức khỏe, công cụ kiểm chứng chạy lại được; thẻ gợi ý có xác nhận và đo tỷ lệ ghi đè — mảnh đầu của không gian Trí tuệ |
| `v0.9.1` | Bản vá: nâng khung giao diện của cổng lên bản đã sửa các cảnh báo bảo mật, không đổi hành vi |
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

Kho theo mô hình nhiều giấy phép, bảng đầy đủ ở
[`LICENSES.md`](https://github.com/AlaVox-lab/dx-os-lab/blob/main/LICENSES.md):

| Phần | Giấy phép |
|---|---|
| Dịch vụ ứng dụng, cổng, kiểm thử giao diện, kịch bản, hạ tầng, tài liệu | [MIT](https://github.com/AlaVox-lab/dx-os-lab/blob/main/LICENSE) |
| Dịch vụ khai phá quy trình `services/khai-pha/` | [AGPL-3.0-or-later](https://github.com/AlaVox-lab/dx-os-lab/blob/main/services/khai-pha/LICENSE) |

Dịch vụ khai phá dùng thư viện PM4Py (AGPL-3.0-or-later) nên cả thư mục theo AGPL; phần còn lại chỉ
trao đổi JSON với nó qua HTTP. Mọi tệp mã nguồn mang định danh giấy phép SPDX đúng thư mục ở đầu
tệp. Màn Quy trình thực tế có dòng dẫn tới mã nguồn của dịch vụ khai phá (điều 13 của AGPL).

Mọi phụ thuộc đều có giấy phép thuộc danh sách OSI và tương thích với giấy phép của phần dùng nó, ghi
trong [`docs/dependencies.md`](https://github.com/AlaVox-lab/dx-os-lab/blob/main/docs/dependencies.md);
thông báo bên thứ ba ở [`NOTICE`](https://github.com/AlaVox-lab/dx-os-lab/blob/main/NOTICE).
Các nền tảng lắp ghép — Keycloak, SeaweedFS, Apache Superset — đều Apache-2.0, chạy như dịch vụ
độc lập, không sửa mã nguồn.

## So sánh với sản phẩm cùng loại

[`docs/so-sanh-san-pham.md`](https://github.com/AlaVox-lab/dx-os-lab/blob/main/docs/so-sanh-san-pham.md)
đặt dự án cạnh tám sản phẩm trong nước và quốc tế, nêu điểm khác và chỗ còn kém.
