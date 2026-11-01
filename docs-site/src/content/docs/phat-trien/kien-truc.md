---
title: Kiến trúc
description: Bức tranh tổng — các dịch vụ trong cụm, engine máy trạng thái, nhật ký sự kiện — và nơi đọc tài liệu kỹ thuật đầy đủ.
sidebar:
  order: 1
---

Trang này là bản đồ. Tài liệu kỹ thuật đầy đủ nằm trong kho mã, ở thư mục `docs/`, và luôn đi cùng
mã nguồn.

## Các dịch vụ trong cụm

| Dịch vụ | Công nghệ | Giấy phép | Vai trò |
|---|---|---|---|
| Cổng người dùng | Next.js (React) | MIT | Giao diện cho bốn vai, giữ phiên đăng nhập phía máy chủ |
| Dịch vụ ứng dụng | FastAPI (Python) | MIT | Engine quy trình, ràng buộc, đồng hồ hạn, bộ quét nền, API |
| Cơ sở dữ liệu | PostgreSQL 16 | PostgreSQL License | Bộ quy tắc, hồ sơ, nhật ký sự kiện, lịch làm việc |
| Định danh | Keycloak 26.7 | Apache-2.0 | Đăng nhập một lần qua OIDC, vai trò, nhóm phòng ban |
| Kho tệp | SeaweedFS 4.45 | Apache-2.0 | Tệp đính kèm qua S3 API |
| Báo cáo | Apache Superset 6.1 | Apache-2.0 | Bảng điều khiển trên dữ liệu nghiệp vụ, chỉ đọc |

Ba nền tảng cuối chạy như **dịch vụ độc lập**, nói chuyện qua giao thức chuẩn; không nhúng thư viện,
không sửa mã nền tảng. Vì sao chọn từng nền tảng — và vì sao **tự viết** engine quy trình thay vì
dùng Camunda hay Flowable — ghi trong các bản ghi quyết định ở
[`docs/adr/`](https://github.com/AlaVox-lab/dx-os-lab/tree/main/docs/adr).

## Engine máy trạng thái

- Bộ quy tắc là dữ liệu: trạng thái, bước đi, vai trò, ràng buộc. Không có tên trạng thái nào trong
  câu lệnh điều kiện của mã nguồn
- **Một cửa duy nhất** — hàm `perform_transition` trong `backend/app/workflow/engine.py`: tra bảng
  quy tắc → kiểm vai trò → chạy ràng buộc → ghi nhật ký → cập nhật hồ sơ, trong một giao dịch, khóa
  dòng hồ sơ để hai người bấm cùng lúc không tạo hai lần chuyển
- Bước của hệ thống (leo thang, tự trả về, tự đóng) cũng đi qua cửa đó, nên nhật ký không bao giờ
  thiếu bản ghi
- Thao tác không đổi hồ sơ (lời nhắn) **không** là bước đi — ranh giới ở ADR-0005

## Nhật ký sự kiện

Mỗi lần chuyển trạng thái ghi một dòng vào `event_log`: mã hồ sơ, hoạt động, thời điểm (UTC), người
thực hiện, trạng thái trước và sau, giá trị cũ và mới của trường đã đổi. Trigger ở cơ sở dữ liệu
chặn sửa và xóa. Định dạng này dùng thẳng được cho khai phá quy trình ở tầng `I`.

## Đọc tiếp trong kho mã

| Tài liệu | Trả lời |
|---|---|
| [`docs/ARCHITECTURE.md`](https://github.com/AlaVox-lab/dx-os-lab/blob/main/docs/ARCHITECTURE.md) | Hệ thống tổ chức thế nào; các khuôn mẫu: cấu hình thay vì mã cứng, nhật ký sự kiện, Poka-yoke; quy ước đặt tên |
| [`docs/process-flow.md`](https://github.com/AlaVox-lab/dx-os-lab/blob/main/docs/process-flow.md) | Sơ đồ 11 trạng thái, 32 bước, ai bấm được, cơ sở các con số |
| [`docs/adr/`](https://github.com/AlaVox-lab/dx-os-lab/tree/main/docs/adr) | Tám bản ghi quyết định kiến trúc |
| [`docs/ROADMAP.md`](https://github.com/AlaVox-lab/dx-os-lab/blob/main/docs/ROADMAP.md) | Lộ trình các giai đoạn |
| [`docs/PROJECT_STATE.md`](https://github.com/AlaVox-lab/dx-os-lab/blob/main/docs/PROJECT_STATE.md) | Dự án đang ở đâu, cập nhật hằng tuần |
| [`docs/dependencies.md`](https://github.com/AlaVox-lab/dx-os-lab/blob/main/docs/dependencies.md) | Mọi phụ thuộc và giấy phép |
