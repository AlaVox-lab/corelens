-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 AlaVox-lab
--
-- Dữ liệu khởi tạo: phòng ban, loại yêu cầu, ánh xạ định tuyến, ngưỡng SLA.
--
-- ĐÂY LÀ TỆP DOANH NGHIỆP TRIỂN KHAI SẼ SỬA ĐẦU TIÊN. Bốn phòng ban và bốn loại
-- yêu cầu dưới đây chỉ là ví dụ minh họa cho bản trình diễn. Một công ty khác
-- xóa hết và khai lại theo cơ cấu của mình mà không đụng một dòng mã nào — đó
-- là mục tiêu sản phẩm ghi ở ARCHITECTURE.md mục 5.1.
--
-- Điều kiện duy nhất phải giữ: mỗi loại yêu cầu có đúng một phòng ban mặc định.
-- Ràng buộc đã đặt ở tầng dữ liệu nên sửa sai sẽ báo lỗi ngay lúc nạp.

\set ON_ERROR_STOP on


-- ---------------------------------------------------------------------------
-- Phòng ban
-- ---------------------------------------------------------------------------

INSERT INTO departments (code, label, description, display_order) VALUES
    ('it',           'Công nghệ thông tin',
     'Thiết bị, mạng, phần mềm, tài khoản hệ thống',        1),

    ('hr',           'Nhân sự',
     'Hồ sơ nhân viên, giấy tờ xác nhận, chế độ',           2),

    ('admin-office', 'Hành chính',
     'Văn phòng phẩm, vật tư, cơ sở vật chất',              3),

    ('finance',      'Tài chính kế toán',
     'Thanh toán, tạm ứng, duyệt chi',                      4);


-- ---------------------------------------------------------------------------
-- Loại yêu cầu và ngưỡng SLA
-- ---------------------------------------------------------------------------
-- Ngưỡng tính bằng giờ làm việc kể từ lúc hồ sơ vào trạng thái đang xử lý. Cạnh
-- leo thang tự động ở #42 đọc cột sla_hours, không mã cứng con số nào.

INSERT INTO request_types (code, label, description, sla_hours, display_order) VALUES
    ('device-incident', 'Sự cố thiết bị',
     'Máy tính, máy in, mạng, điện thoại bàn hỏng hoặc không dùng được',   8,  1),

    ('software-access', 'Cấp quyền phần mềm',
     'Xin tài khoản hoặc mở thêm quyền trên một hệ thống nội bộ',         24,  2),

    ('hr-certificate',  'Giấy xác nhận nhân sự',
     'Xác nhận công tác, xác nhận thu nhập, giấy giới thiệu',             48,  3),

    ('supply-purchase', 'Đề xuất mua vật tư',
     'Đề nghị mua sắm văn phòng phẩm hoặc vật tư phục vụ công việc',      72,  4);


-- ---------------------------------------------------------------------------
-- Ánh xạ loại yêu cầu sang phòng ban phụ trách
-- ---------------------------------------------------------------------------
-- Phòng mặc định là gợi ý sẵn cho người phân loại, không phải ràng buộc cứng —
-- người phân loại vẫn chọn được phòng khác, và chính những lần chọn khác đó là
-- dữ liệu quý cho khai phá quy trình: nếu một loại yêu cầu liên tục bị định
-- tuyến khác mặc định, bảng ánh xạ này đang sai.
--
-- Đề xuất mua vật tư cố ý khai hai phòng để minh họa quan hệ nhiều-nhiều:
-- Hành chính mua sắm, nhưng khoản lớn thì Tài chính đảm nhận.

INSERT INTO request_type_routing (request_type_code, department_code, is_default) VALUES
    ('device-incident', 'it',           TRUE),
    ('software-access', 'it',           TRUE),
    ('hr-certificate',  'hr',           TRUE),
    ('supply-purchase', 'admin-office', TRUE),
    ('supply-purchase', 'finance',      FALSE);
