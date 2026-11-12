-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 AlaVox-lab
--
-- Dữ liệu khởi tạo: loại thông báo thư điện tử (#251).
--
-- Thư chỉ được gửi khi máy chủ thư được cấu hình (`SMTP_HOST`, infra/.env.example); không cấu hình
-- thì bảng này nằm yên, không sự kiện nào được xếp hàng. Mỗi dòng là một loại người dùng bật/tắt
-- được ở trang Thông báo của cổng. Thêm loại, đổi lời thư, tắt hẳn một loại — sửa ở đây, không sửa mã.
--
-- `trigger`     cơ chế kích hoạt, mã biết ba giá trị:
--                 state-entered  hồ sơ vừa đổi trạng thái hay đổi người được giao (mọi lần chuyển
--                                đi qua cổng chuyển trạng thái duy nhất)
--                 auto-warning   hồ sơ vừa vào khoảng báo trước của cạnh tự đi — theo
--                                `transitions.auto_after_hours` và `warn_before_hours` đã có (#142);
--                                mỗi lần hồ sơ vào trạng thái chỉ báo một lần
--                 auto-done      hệ thống vừa tự đi cạnh đó vì hết hạn chờ
-- `recipients`  ai nhận:
--                 primary-step   người đang có bước chính trên hồ sơ — cùng phép tính với cờ "cần
--                                tôi xử lý" (#227, cột `transitions.primary_scope`), tính lúc gửi
--                 requester      người gửi hồ sơ
--               Người vừa làm thao tác không bao giờ nhận thư về chính thao tác đó.
-- Mẫu tiêu đề và nội dung theo cú pháp `string.Template` của Python. Biến có sẵn:
--   $ten_nguoi_nhan  tên người nhận trong danh bạ        $ma_ho_so     mã hồ sơ, dạng YC-2026-0123
--   $tieu_de         tiêu đề hồ sơ                       $trang_thai   tên trạng thái hiện tại
--   $tu_trang_thai   tên trạng thái trước (auto-done)    $buoc         nhãn bước chính đang chờ
--   $han_tu_dong     lúc hệ thống sẽ tự đi (giờ Việt Nam) $canh_tu_dong nhãn cạnh tự đi
--   $lien_ket        địa chỉ cổng
-- Biến viết sai thì để nguyên trong thư (không làm hỏng việc gửi).
--
-- `ON CONFLICT DO NOTHING`: cụm dựng trước #251 nhận các dòng này qua migration 0024; doanh nghiệp
-- đã sửa một dòng thì dòng đó được giữ.

\set ON_ERROR_STOP on


INSERT INTO notification_types
    (code, label, description, trigger, recipients, subject_template, body_template,
     default_enabled, is_active, display_order)
VALUES
    ('viec-cho-toi',
     'Có việc chờ tôi',
     'Khi một hồ sơ chuyển tới bước cần bạn thao tác.',
     'state-entered', 'primary-step',
     '[DX-OS Lab] $ma_ho_so chờ bạn: $buoc',
     E'Chào $ten_nguoi_nhan,\n\n'
     'Hồ sơ $ma_ho_so "$tieu_de" đang ở trạng thái "$trang_thai" và chờ bạn: $buoc.\n\n'
     'Mở cổng để xử lý: $lien_ket\n\n'
     '— Thư tự động từ DX-OS Lab. Tắt loại thư này ở trang Thông báo của cổng.',
     TRUE, TRUE, 10),
    ('sap-tu-dong',
     'Hồ sơ sắp tự chuyển',
     'Khi một hồ sơ đang chờ bạn sắp bị hệ thống tự đóng hoặc tự trả về vì không ai thao tác.',
     'auto-warning', 'primary-step',
     '[DX-OS Lab] $ma_ho_so sẽ $canh_tu_dong lúc $han_tu_dong',
     E'Chào $ten_nguoi_nhan,\n\n'
     'Hồ sơ $ma_ho_so "$tieu_de" đang chờ bạn ở trạng thái "$trang_thai" ($buoc). '
     'Nếu không ai thao tác, hệ thống sẽ $canh_tu_dong lúc $han_tu_dong.\n\n'
     'Mở cổng để xử lý: $lien_ket\n\n'
     '— Thư tự động từ DX-OS Lab. Tắt loại thư này ở trang Thông báo của cổng.',
     TRUE, TRUE, 20),
    ('da-tu-dong',
     'Hồ sơ đã tự chuyển',
     'Khi hệ thống vừa tự đóng hoặc tự trả về hồ sơ của bạn vì hết hạn chờ.',
     'auto-done', 'requester',
     '[DX-OS Lab] $ma_ho_so: $canh_tu_dong',
     E'Chào $ten_nguoi_nhan,\n\n'
     'Hồ sơ $ma_ho_so "$tieu_de" của bạn vừa được hệ thống chuyển từ "$tu_trang_thai" sang '
     '"$trang_thai" ($canh_tu_dong) vì hết hạn chờ mà chưa ai thao tác.\n\n'
     'Xem hồ sơ: $lien_ket\n\n'
     '— Thư tự động từ DX-OS Lab. Tắt loại thư này ở trang Thông báo của cổng.',
     TRUE, TRUE, 30)
ON CONFLICT (code) DO NOTHING;
