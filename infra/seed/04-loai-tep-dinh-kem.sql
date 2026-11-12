-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 AlaVox-lab
--
-- Dữ liệu khởi tạo: cách kiểm nội dung từng loại tệp đính kèm (#248).
--
-- Đuôi nào ĐƯỢC NHẬN vẫn do biến môi trường `ATTACHMENT_ALLOWED_EXTENSIONS` quyết (#80). Bảng này
-- chỉ trả lời "tệp mang đuôi này thì nội dung phải trông thế nào": chữ ký đầu tệp, loại nội dung trả
-- khi tải về, và cách dò macro. Thêm một đuôi mới là thêm một dòng ở đây rồi thêm đuôi vào biến
-- môi trường — không sửa mã.
--
-- `signatures`   mẫu chữ ký dạng hex, `??` là một byte bất kỳ; khớp MỘT mẫu là đạt. Rỗng và
--                `text_only` sai thì không kiểm nội dung.
-- `search_bytes` 0: mẫu phải nằm ngay đầu tệp. Lớn hơn 0: mẫu nằm đâu đó trong chừng ấy byte đầu
--                (PDF cho phép rác trước `%PDF-`, trình đọc PDF vẫn mở).
-- `text_only`    tệp văn bản thuần: không có byte 0 trong 8 KB đầu.
-- `macro_check`  `ooxml`: gói ZIP của Office có `vbaProject.bin`; `ole`: tệp Office đời cũ có kho
--                `_VBA_PROJECT`. Tệp có macro vẫn được NHẬN nhưng gắn cờ để giao diện cảnh báo.
-- `always_macro` định dạng sinh ra để mang macro (.docm, .xlsm, .pptm) — luôn gắn cờ.
--
-- Chữ ký theo đặc tả của từng định dạng: PNG (ISO/IEC 15948), JPEG (ISO/IEC 10918-1, SOI + mã
-- đánh dấu), GIF87a/89a, WebP (RIFF … WEBP), PDF (ISO 32000), ZIP (PKWARE APPNOTE — gói Office
-- Open XML, ISO/IEC 29500), Compound File Binary (MS-CFB — Word, Excel, PowerPoint đời cũ).
--
-- `ON CONFLICT DO NOTHING`: cụm dựng trước #248 nhận các dòng này qua migration 0023, chạy chính
-- tệp này; doanh nghiệp đã sửa một dòng thì dòng đó được giữ.

\set ON_ERROR_STOP on


INSERT INTO attachment_file_types
    (extension, content_type, signatures, search_bytes, text_only, macro_check, always_macro, note)
VALUES
    ('png',  'image/png',  ARRAY['89504e470d0a1a0a'], 0, FALSE, NULL, FALSE, 'Ảnh PNG'),
    ('jpg',  'image/jpeg', ARRAY['ffd8ff'], 0, FALSE, NULL, FALSE, 'Ảnh JPEG'),
    ('jpeg', 'image/jpeg', ARRAY['ffd8ff'], 0, FALSE, NULL, FALSE, 'Ảnh JPEG'),
    ('gif',  'image/gif',  ARRAY['474946383761', '474946383961'], 0, FALSE, NULL, FALSE, 'Ảnh GIF'),
    ('webp', 'image/webp', ARRAY['52494646????????57454250'], 0, FALSE, NULL, FALSE, 'Ảnh WebP'),
    ('pdf',  'application/pdf', ARRAY['255044462d'], 1024, FALSE, NULL, FALSE, 'Tài liệu PDF'),
    ('txt',  'text/plain', ARRAY[]::text[], 0, TRUE, NULL, FALSE, 'Văn bản thuần'),
    ('csv',  'text/csv',   ARRAY[]::text[], 0, TRUE, NULL, FALSE, 'Bảng tính dạng CSV'),
    ('doc',  'application/msword', ARRAY['d0cf11e0a1b11ae1'], 0, FALSE, 'ole', FALSE,
     'Word đời cũ — có thể mang macro'),
    ('xls',  'application/vnd.ms-excel', ARRAY['d0cf11e0a1b11ae1'], 0, FALSE, 'ole', FALSE,
     'Excel đời cũ — có thể mang macro'),
    ('ppt',  'application/vnd.ms-powerpoint', ARRAY['d0cf11e0a1b11ae1'], 0, FALSE, 'ole', FALSE,
     'PowerPoint đời cũ — có thể mang macro'),
    ('docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
     ARRAY['504b0304'], 0, FALSE, 'ooxml', FALSE, 'Word'),
    ('xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
     ARRAY['504b0304'], 0, FALSE, 'ooxml', FALSE, 'Excel'),
    ('pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
     ARRAY['504b0304'], 0, FALSE, 'ooxml', FALSE, 'PowerPoint'),
    ('docm', 'application/vnd.ms-word.document.macroEnabled.12',
     ARRAY['504b0304'], 0, FALSE, 'ooxml', TRUE, 'Word có macro'),
    ('xlsm', 'application/vnd.ms-excel.sheet.macroEnabled.12',
     ARRAY['504b0304'], 0, FALSE, 'ooxml', TRUE, 'Excel có macro'),
    ('pptm', 'application/vnd.ms-powerpoint.presentation.macroEnabled.12',
     ARRAY['504b0304'], 0, FALSE, 'ooxml', TRUE, 'PowerPoint có macro')
ON CONFLICT (extension) DO NOTHING;
