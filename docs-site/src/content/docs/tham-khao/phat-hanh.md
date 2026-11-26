---
title: Phát hành và giấy phép
description: Các bản phát hành, nhật ký thay đổi, giấy phép của dự án và các thành phần.
sidebar:
  order: 2
---

## Bản phát hành

Mỗi bản phát hành có thẻ theo **Semantic Versioning** và tệp mã nguồn `.tar.gz` ở trang
[Releases](https://github.com/AlaVox-lab/corelens/releases). Nhật ký thay đổi
[`CHANGELOG.md`](https://github.com/AlaVox-lab/corelens/blob/main/CHANGELOG.md) sinh tự động từ
lịch sử commit.

| Bản | Nội dung chính |
|---|---|
| `v1.8.1` | Logo Corelens ở cổng, trang tài liệu và màn đăng nhập; số phiên bản đọc từ một nguồn; biểu mẫu gửi không cho qua bước 2 khi thiếu trường bắt buộc; gợi ý hồ sơ tương tự gộp trùng, có ô *Cách giải quyết* mà người xử lý ghi khi hoàn thành; trang hồ sơ đã đóng nói đúng; nút chính theo bước chính trong dữ liệu; khuyến nghị cải tiến nhắc đúng vai và luôn có câu cho điểm nghẽn lớn |
| `v1.8.0` | Lệnh tạo hồ sơ và chuyển trạng thái của lõi nhận khóa `Idempotency-Key`, gửi lại cùng khóa nhận đúng kết quả cũ; nhật ký kiểm toán chỉ ghi thêm cho mỗi lần xem hồ sơ, liên hệ, tệp của người khác và xuất nhật ký; ngăn xem nhanh không che bảng hồ sơ; trang *Mã nguồn và giấy phép* ở chân thanh bên thay các dòng AGPL chen giữa nội dung; dữ liệu trình diễn đọc như doanh nghiệp thật, có số cho hai biểu đồ đo gợi ý; mọi chữ người dùng thấy mang tên Corelens; README gọn, kho tri thức chịu được gói ngôn ngữ hỏng |
| `v1.7.0` | Điều phối viên chọn nhiều hồ sơ để phân loại hay chuyển phòng cả lô, mỗi hồ sơ vẫn một lần chuyển và một dòng nhật ký riêng, hồ sơ bị chặn báo riêng; người gửi chấm mức hài lòng 1–5 kèm nhận xét khi xác nhận đạt, bảng điều khiển thêm điểm trung bình, tỷ lệ được chấm theo phòng và phân bố điểm; dòng thời gian ghi đúng nhãn bước khi một cặp trạng thái có cả bước người lẫn bước hệ thống |
| `v1.6.0` | Trang hồ sơ của điều phối viên và phòng ban hiện các bước đi lệch quy trình thiết kế, chỉ để đọc; cổng đạt WCAG 2.1 AA trên màn chính của từng vai, có kịch bản quét axe và bài thao tác bằng bàn phím; API lõi trả mọi cạnh của hồ sơ kèm lý do không đi được và trường cần nhập; kiểm thử dựa trên tính chất cho máy trạng thái bằng Hypothesis |
| `v1.5.1` | Bản vá sau khi đổi tên dự án thành Corelens: kho chuyển sang `AlaVox-lab/corelens`, hướng dẫn cài khớp tên tệp nén mới `corelens-<phiên bản>`, đường gốc trang tài liệu `/corelens` |
| `v1.5.0` | Webhook không bỏ sót sự kiện: lần gửi sinh bằng trigger trong giao dịch ghi nhật ký, gửi ngoài giao dịch; xuất nhật ký sự kiện chuẩn XES; bảng điều khiển thêm vi phạm hạn theo loại, ghi đè gợi ý theo tuần, thời gian chờ theo trạng thái; từ điển dữ liệu sinh tự động; tìm cả trong mô tả; mở biểu mẫu với loại chọn sẵn; thẻ gợi ý của điều phối viên kèm hồ sơ đã giải quyết tương tự; kịch bản giao diện cho Kanban, webhook, thời gian thực; action lên bản chạy Node 24 |
| `v1.4.0` | Đặc tả OpenAPI của nền tảng lõi `/core/v1` nằm trong kho, tích hợp liên tục báo khi lệch mã; quét giấy phép mọi gói phụ thuộc kể cả gián tiếp, báo cáo đính kèm bản phát hành; đối soát tài liệu phụ thuộc, kiểm liên kết hỏng, kiểm tệp Compose từng hồ sơ; pre-commit tùy chọn; kịch bản in tiếng Việt trên Windows, kiểm nâng cấp trên cụm thử; yêu cầu Python cho kịch bản tiện ích |
| `v1.3.0` | Tích hợp liên tục kiểm chuẩn tiêu đề pull request và lịch sử commit, kiểm header giấy phép cả trên tệp cấu hình, mọi biến cấu hình có dòng giải thích; mẫu issue dạng biểu mẫu; ngày nghỉ lễ năm 2027 trong lịch làm việc mẫu; kiểm thử độc lập với dữ liệu trình diễn; bước nâng cấp từ `v1.0.0` theo thứ tự |
| `v1.2.0` | Điều kiện trên cạnh: quy trình rẽ nhánh theo trường của hồ sơ, khai trong dữ liệu — đề xuất mua vật tư dưới ngưỡng chỉ cần một cấp duyệt; xuất quy trình ra BPMN 2.0 qua API lõi; quản lý webhook trên màn Hệ thống; bảng Kanban cho buồng lái phòng ban; kịch bản trình diễn chung kết |
| `v1.1.0` | Nền tảng lõi Mức 2: động cơ luồng công việc chạy nhiều quy trình, quy trình mẫu thứ hai *đề xuất mua vật tư* thuần dữ liệu; lưu trữ lạnh theo tháng ra kho đối tượng và trang phả hệ dữ liệu; cổng người dùng cập nhật thời gian thực; webhook có chữ ký; siết realm mẫu; README tiếng Anh, linter và kịch bản giao diện trong tích hợp liên tục |
| `v1.0.0` | Bản dự thi OLP 2026 theo mô hình của đề: cổng API Apache APISIX làm cửa vào duy nhất, kiểm token tại biên; nền tảng lõi không giao diện phơi qua API `/core/v1` kèm tài khoản dịch vụ và ví dụ gọi lõi; xác thực hai lớp tùy chọn; khóa phiên bản cả gói Python kéo theo |
| `v0.16.0` | Kho tri thức Wiki.js (tùy chọn, hồ sơ `tri-thuc`): đăng nhập một lần qua Keycloak, quyền theo vai trò, bài hướng dẫn hiện trong gợi ý khi đang soạn yêu cầu; khép nhóm nền tảng vận hành |
| `v0.15.0` | Màn quản trị cấu hình: xem luồng xử lý, sửa hạn, hệ số ưu tiên, loại yêu cầu, phòng ban ngay trên cổng, có xem trước và nhật ký sửa; ủy quyền khi vắng mặt cho người cùng phòng theo khoảng ngày, ghi "thay mặt"; sao lưu tay và khôi phục có đối soát; chính sách dữ liệu cá nhân (ADR-0009) |
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
[`docs/ROADMAP.md`](https://github.com/AlaVox-lab/corelens/blob/main/docs/ROADMAP.md): tầng Trí tuệ
từ `v0.10.0`.

## Giấy phép

Kho theo mô hình nhiều giấy phép, bảng đầy đủ ở
[`LICENSES.md`](https://github.com/AlaVox-lab/corelens/blob/main/LICENSES.md):

| Phần | Giấy phép |
|---|---|
| Dịch vụ ứng dụng, cổng, kiểm thử giao diện, kịch bản, hạ tầng, tài liệu | [MIT](https://github.com/AlaVox-lab/corelens/blob/main/LICENSE) |
| Dịch vụ khai phá quy trình `services/khai-pha/` | [AGPL-3.0-or-later](https://github.com/AlaVox-lab/corelens/blob/main/services/khai-pha/LICENSE) |

Dịch vụ khai phá dùng thư viện PM4Py (AGPL-3.0-or-later) nên cả thư mục theo AGPL; phần còn lại chỉ
trao đổi JSON với nó qua HTTP. Mọi tệp mã nguồn mang định danh giấy phép SPDX đúng thư mục ở đầu
tệp. Trang *Mã nguồn và giấy phép* ở chân thanh bên của cổng dẫn tới mã nguồn của dịch vụ khai phá (điều 13
của AGPL).

Mọi phụ thuộc đều có giấy phép thuộc danh sách OSI và tương thích với giấy phép của phần dùng nó, ghi
trong [`docs/dependencies.md`](https://github.com/AlaVox-lab/corelens/blob/main/docs/dependencies.md);
thông báo bên thứ ba ở [`NOTICE`](https://github.com/AlaVox-lab/corelens/blob/main/NOTICE).
Các nền tảng lắp ghép — Keycloak, SeaweedFS, Apache Superset — đều Apache-2.0, chạy như dịch vụ
độc lập, không sửa mã nguồn.

## So sánh với sản phẩm cùng loại

[`docs/so-sanh-san-pham.md`](https://github.com/AlaVox-lab/corelens/blob/main/docs/so-sanh-san-pham.md)
đặt dự án cạnh tám sản phẩm trong nước và quốc tế, nêu điểm khác và chỗ còn kém.
