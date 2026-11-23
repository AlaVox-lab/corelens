---
title: Giới thiệu
description: Corelens là gì, giải quyết vấn đề nào, và khác các phần mềm cùng loại ở đâu.
sidebar:
  order: 1
---

## Vấn đề

Ở nhiều doanh nghiệp, việc nội bộ — báo máy hỏng, xin cấp phần mềm, xin giấy xác nhận, đề xuất
mua vật tư — được gửi qua Zalo, email hay giấy tờ. Người gửi không biết yêu cầu đã tới đâu, quá
hạn không ai nhắc, và lãnh đạo không có số liệu để biết khâu nào đang chậm.

## Corelens làm gì

**Một cổng chung cho mọi yêu cầu nội bộ.** Một hồ sơ đi qua bốn vai:

| Vai | Việc chính |
|---|---|
| **Người gửi** | Gửi yêu cầu, trả lời khi được hỏi thêm, xác nhận đạt hay mở lại |
| **Điều phối viên** | Phân loại, đặt mức ưu tiên, chọn phòng ban phù hợp cho từng hồ sơ |
| **Trưởng phòng** | Nhận hồ sơ về phòng và giao người, hoặc từ chối nếu sai chuyên môn |
| **Người xử lý** | Làm việc, hỏi thêm người gửi khi cần, báo hoàn thành |

Mở cổng lên, mỗi người thấy ngay **việc đang chờ chính mình**, xếp theo độ gấp. Mỗi vai chỉ thấy
những nút mình được bấm ở bước đó.

Điểm khác với một phần mềm phê duyệt thông thường: hồ sơ **không đi theo một chuỗi người duyệt cố
định**. Điều phối viên đọc từng hồ sơ và chọn phòng phù hợp; phòng nhận sai thì trả lại kèm lý do,
hồ sơ được chuyển sang phòng khác.

## Ba ý tưởng nền

1. **Quy trình là dữ liệu.** Mười một trạng thái, ba mươi hai bước đi, vai trò được bấm, ràng buộc
   chống sai và mọi con số (hạn, số lần gia hạn, số lần mở lại) nằm trong bảng. Doanh nghiệp khác
   đổi quy trình bằng cách sửa dữ liệu, không sửa mã — xem
   [Tùy biến quy trình](../../quan-tri/tuy-bien-quy-trinh/).
2. **Chống sai từ gốc** (Poka-yoke — nguyên lý chống sai lỗi của hệ thống sản xuất Toyota). Thao
   tác sai thì hoặc không có nút để bấm, hoặc bấm vào bị dịch vụ chặn kèm lý do bằng tiếng Việt.
3. **Mọi bước để lại dấu vết.** Mỗi lần hồ sơ đổi trạng thái ghi một dòng nhật ký chỉ ghi thêm.
   Từ nhật ký này, hệ thống khai phá lại quy trình đang chạy thật và chỉ ra điểm nghẽn — xem
   [Quy trình thực tế](../../huong-dan/quy-trinh-thuc-te/).

## Kiến trúc H-P-D-I

Theo đề bài, hệ thống chia bốn không gian, xây theo đúng thứ tự:

| | Không gian | Trạng thái |
|---|---|---|
| **H** | Nhân sự — đăng nhập một lần, phân quyền theo vai (Keycloak) | Đã chạy |
| **P** | Quy trình — engine máy trạng thái tự viết, ràng buộc, hạn xử lý | Đã chạy |
| **D** | Dữ liệu — bảng điều khiển trên nhật ký sự kiện (Apache Superset) | Đã chạy |
| **I** | Trí tuệ — khai phá quy trình, gợi ý phân loại có người xác nhận | Đã chạy; gợi ý bằng mô hình ngôn ngữ là tùy chọn |

Nền tảng phổ thông được **lắp ghép** từ phần mềm nguồn mở có sẵn (Keycloak, Apache APISIX làm cổng
API, SeaweedFS, Superset); engine quy trình, phần tạo khác biệt, nhóm **tự viết**. AI ở tầng `I` chỉ ghi
vào trường gợi ý, con người xác nhận mới thành quyết định. Bốn không gian này là tầng ứng dụng minh họa; bên
dưới là nền tảng lõi chỉ có API, cho ứng dụng khác dùng lại — xem [Kiến trúc](../../phat-trien/kien-truc/).

So sánh với tám sản phẩm cùng loại trong nước và quốc tế:
[docs/so-sanh-san-pham.md](https://github.com/AlaVox-lab/corelens/blob/main/docs/so-sanh-san-pham.md).

## Tên gọi

Tên cũ của dự án là `dx-os-lab`. Tên đó còn nằm trong các định danh kỹ thuật — realm Keycloak `dx-os-lab`, dự
án Compose, container `dxlab-*`, biến `DXLAB_*` — và được giữ nguyên để cụm đang chạy không phải dựng lại.
