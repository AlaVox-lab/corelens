-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 AlaVox-lab
--
-- Dữ liệu khởi tạo: danh mục quy trình (#376, nền tảng lõi Mức 2).
--
-- Động cơ luồng công việc chạy nhiều quy trình cùng lúc. Mỗi quy trình có đúng một bộ quy tắc đang bật
-- (`rule_sets.process_code`), mỗi loại yêu cầu thuộc một quy trình (`request_types.process_code`) — loại
-- yêu cầu quyết định hồ sơ chạy theo quy trình nào. Vai trò, phòng ban, mức ưu tiên, lịch làm việc dùng
-- chung mọi quy trình.
--
-- `is_app_default` đánh dấu quy trình mà các màn của ứng dụng minh họa — cổng người gửi, hai buồng lái,
-- trang chủ, báo cáo, khai phá — dùng. Đúng một dòng mang cờ này; kiem_tra_cau_hinh() chặn khởi động nếu
-- khác. Mã nguồn hỏi cờ này, không viết tên quy trình nào.
--
-- Tệp chạy trước mọi tệp khác (thứ tự tên tệp): 01 và 02 gắn bộ quy tắc và loại yêu cầu vào quy trình đầu,
-- 06 khai quy trình thứ hai. Cụm dựng trước #376 nhận tệp này qua bản sửa Alembic 0028.

\set ON_ERROR_STOP on

INSERT INTO processes (code, label, description, display_order, is_app_default) VALUES
    ('internal-requests', 'Cổng yêu cầu nội bộ',
     'Tiếp nhận và điều phối mọi yêu cầu nội bộ: phân loại, chuyển phòng ban, nhận việc, xử lý, xác nhận.',
     1, TRUE),

    ('purchase-approval', 'Đề xuất mua sắm duyệt hai cấp',
     'Quy trình mẫu thứ hai, chạy hoàn toàn qua API của lõi: người đề xuất gửi, trưởng phòng duyệt cấp một, '
     'điều phối viên duyệt cấp hai.',
     2, FALSE);
