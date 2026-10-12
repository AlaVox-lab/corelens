-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 AlaVox-lab
--
-- Dữ liệu khởi tạo: lịch làm việc (#199).
--
-- Mọi khoảng thời gian của quy trình — hạn xử lý SLA, ân hạn, các hạn chờ — đo bằng giờ
-- làm việc theo lịch mặc định dưới đây. Doanh nghiệp triển khai sửa giờ làm và ngày nghỉ
-- ở đây, không sửa mã.
--
-- Lịch mẫu: thứ Hai – thứ Sáu, 08:00–12:00 và 13:00–17:00 (8 giờ một ngày), nghỉ trưa
-- 12:00–13:00, giờ Việt Nam.
--
-- Ngày nghỉ năm 2026 theo các ngày nghỉ lễ, Tết hưởng nguyên lương của Bộ luật Lao động
-- và phương án nghỉ năm 2026 đã công bố. Chỉ ghi ngày làm việc bị nghỉ — ngày lễ rơi vào
-- thứ Bảy, Chủ nhật thì lịch đã không có giờ làm. Ngày hoán đổi làm bù vào thứ Bảy chưa
-- khai được ở đây (lịch chưa có ngày làm thêm), nên chỉ ghi ngày nghỉ chính và nghỉ bù.
-- Nguồn, mở ngày 12/10/2026:
--   Tết Nguyên đán: https://vov.vn/xa-hoi/thu-tuong-chinh-phu-dong-y-phuong-an-nghi-tet-binh-ngo-9-ngay-lien-tuc-post1237646.vov
--   Giỗ Tổ, 30/4, 1/5, 2/9: https://tapchitoaan.vn/lich-nghi-le-gio-to-hung-vuong-304-15-va-quoc-khanh-29-nam-202615074.html
--   Ngày Văn hóa Việt Nam 24/11: https://hatinh.gov.vn/vi/bai-viet/ngay-van-hoa-viet-nam---2411-nguoi-lao-dong-duoc-nghi-huong-nguyen-luong
-- Thêm ngày nghỉ của năm sau khi có thông báo chính thức.

\set ON_ERROR_STOP on


INSERT INTO work_calendars (code, label, time_zone, is_default) VALUES
    ('mac-dinh', 'Giờ hành chính', 'Asia/Ho_Chi_Minh', TRUE);

INSERT INTO work_hours (calendar_code, iso_weekday, start_time, end_time)
SELECT 'mac-dinh', thu, khung.bat, khung.ket
FROM generate_series(1, 5) AS thu,
     (VALUES (TIME '08:00', TIME '12:00'),
             (TIME '13:00', TIME '17:00')) AS khung (bat, ket);

INSERT INTO holidays (calendar_code, day, label) VALUES
    ('mac-dinh', DATE '2026-01-01', 'Tết Dương lịch'),
    ('mac-dinh', DATE '2026-02-16', 'Tết Nguyên đán'),
    ('mac-dinh', DATE '2026-02-17', 'Tết Nguyên đán'),
    ('mac-dinh', DATE '2026-02-18', 'Tết Nguyên đán'),
    ('mac-dinh', DATE '2026-02-19', 'Tết Nguyên đán'),
    ('mac-dinh', DATE '2026-02-20', 'Tết Nguyên đán'),
    ('mac-dinh', DATE '2026-04-27', 'Nghỉ bù Giỗ Tổ Hùng Vương (26/4 là Chủ nhật)'),
    ('mac-dinh', DATE '2026-04-30', 'Ngày Chiến thắng'),
    ('mac-dinh', DATE '2026-05-01', 'Quốc tế Lao động'),
    ('mac-dinh', DATE '2026-09-01', 'Quốc khánh'),
    ('mac-dinh', DATE '2026-09-02', 'Quốc khánh'),
    ('mac-dinh', DATE '2026-11-24', 'Ngày Văn hóa Việt Nam'),
    ('mac-dinh', DATE '2027-01-01', 'Tết Dương lịch');
