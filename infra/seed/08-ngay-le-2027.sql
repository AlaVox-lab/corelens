-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 AlaVox-lab
--
-- Dữ liệu khởi tạo: ngày nghỉ lễ năm 2027 của lịch mặc định (#439).
--
-- Cùng cách ghi với 03-lich-lam-viec.sql: chỉ ghi NGÀY LÀM VIỆC bị nghỉ — lễ rơi vào thứ Bảy, Chủ nhật
-- thì lịch đã không có giờ làm; ngày nghỉ bù thì ghi. Cụm dựng mới nạp tệp này sau tệp 03; cụm đang
-- chạy nhận nó qua bản sửa 0033_ngay_le_2027. ON CONFLICT để chạy lại, hay chạy trên cụm đã thêm tay
-- qua màn cấu hình, đều không lỗi.
--
-- Lịch nghỉ 2027 theo báo chí ngày 15–17/11/2026, mở ngày 18/11/2026:
--   https://xaydungchinhsach.chinhphu.vn/lich-nghi-tet-nghi-le-2027-119261115134738791.htm
--   https://vnexpress.net/du-kien-cac-ngay-nghi-le-tet-nam-2027-5105651.html
-- Tết Nguyên đán: nghỉ từ thứ Năm 4/2 tới hết thứ Tư 10/2 (năm ngày lễ cộng hai ngày cuối tuần) —
-- hai phương án Bộ Nội vụ trình đều cho cùng năm ngày làm việc bị nghỉ dưới đây. Giỗ Tổ (10/3 âm lịch)
-- là thứ Sáu 16/4; 1/5 là thứ Bảy nên nghỉ bù thứ Hai 3/5; Quốc khánh nghỉ 2/9 và 3/9. Có văn bản
-- chính thức khác lịch này thì sửa ở đây và ở màn cấu hình.

\set ON_ERROR_STOP on

INSERT INTO holidays (calendar_code, day, label) VALUES
    ('mac-dinh', DATE '2027-01-01', 'Tết Dương lịch'),
    ('mac-dinh', DATE '2027-02-04', 'Tết Nguyên đán'),
    ('mac-dinh', DATE '2027-02-05', 'Tết Nguyên đán'),
    ('mac-dinh', DATE '2027-02-08', 'Tết Nguyên đán'),
    ('mac-dinh', DATE '2027-02-09', 'Tết Nguyên đán'),
    ('mac-dinh', DATE '2027-02-10', 'Tết Nguyên đán'),
    ('mac-dinh', DATE '2027-04-16', 'Giỗ Tổ Hùng Vương'),
    ('mac-dinh', DATE '2027-04-30', 'Ngày Chiến thắng'),
    ('mac-dinh', DATE '2027-05-03', 'Nghỉ bù Quốc tế Lao động (1/5 là thứ Bảy)'),
    ('mac-dinh', DATE '2027-09-02', 'Quốc khánh'),
    ('mac-dinh', DATE '2027-09-03', 'Quốc khánh'),
    ('mac-dinh', DATE '2027-11-24', 'Ngày Văn hóa Việt Nam')
ON CONFLICT (calendar_code, day) DO NOTHING;
