-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 AlaVox-lab
--
-- Dữ liệu khởi tạo: bộ quy tắc quy trình v1.
--
-- Nội dung tệp này là bản sao chạy được của docs/process-flow.md mục 2 tới 5 —
-- mười trạng thái, hai mươi bốn cạnh, năm vai trò, các ràng buộc Poka-yoke. Sửa
-- luồng nghiệp vụ nghĩa là sửa tệp này, không phải sửa mã nguồn.
--
-- Hai tệp phải khớp nhau. Khi đổi một bên, đổi cả bên kia trong cùng công việc.

\set ON_ERROR_STOP on


-- ---------------------------------------------------------------------------
-- Bộ quy tắc
-- ---------------------------------------------------------------------------

INSERT INTO rule_sets (id, version, label, effective_from, is_active, note) VALUES
    (1, 'v1', 'Bộ quy tắc ban đầu — mười trạng thái, hai mươi bốn cạnh',
     TIMESTAMPTZ '2026-09-10 00:00:00+00', TRUE,
     'Chốt trong buổi trao đổi với giảng viên hướng dẫn ngày 10/09/2026: năm vai trò, thêm chặng định tuyến phòng ban, bỏ cổng phê duyệt chi phí. Bổ sung ngày 24/09/2026 (#79): chờ bổ sung thông tin quay về đúng chỗ đã hỏi, trưởng phòng hỏi thêm được trước khi nhận việc. Bổ sung ngày 24/09/2026 (#127, ADR-0005): người gửi sửa nội dung khi hồ sơ chưa tới phòng ban, người xử lý tự nhận hồ sơ chưa giao ai.');


-- ---------------------------------------------------------------------------
-- Năm vai trò
-- ---------------------------------------------------------------------------
-- Mã phải trùng tên vai trò realm trong infra/keycloak/realm-dx-os-lab.json.

INSERT INTO roles (code, label, description, display_order, report_scope) VALUES
    ('requester',     'Người tạo yêu cầu',
     'Gửi yêu cầu, sửa nội dung trước khi tới phòng ban, bổ sung thông tin, hủy khi được phép, xác nhận hoặc mở lại', 1, NULL),

    ('classifier',    'Người phân loại yêu cầu',
     'Phân loại, chọn phòng ban phụ trách, đặt mức ưu tiên, hỏi thêm thông tin, chuyển lại phòng khác khi bị từ chối', 2, 'all'),

    ('approver',      'Người xét duyệt yêu cầu',
     'Quyết định phòng ban nhận hay không nhận, hỏi thêm thông tin trước khi nhận, phân công lại khi leo thang', 3, 'department'),

    ('handler',       'Người xử lý yêu cầu',
     'Nhận việc về mình khi hồ sơ chưa giao ai, thực hiện công việc, hỏi thêm thông tin khi cần, báo hoàn thành', 4, NULL),

    ('administrator', 'Quản trị viên',
     'Không đi cạnh nào. Quản lý phòng ban, loại yêu cầu, ngưỡng SLA, bảng ánh xạ loại sang phòng', 5, 'all');


-- ---------------------------------------------------------------------------
-- Mười trạng thái
-- ---------------------------------------------------------------------------
-- Cột `sla_running` quyết định đồng hồ SLA chạy ở trạng thái nào. Chỉ hai trạng
-- thái bật: `in-progress` và `escalated` — tức đồng hồ chỉ chạy khi phòng ban đang
-- thực sự giữ việc.
--
-- Hệ quả có chủ đích: thời gian hồ sơ nằm ở `awaiting-info` KHÔNG tính vào SLA, vì
-- người xử lý không nên bị phạt khi người tạo chậm trả lời. Nhưng tổng thời gian
-- dừng vẫn được cộng dồn vào cột `requests.sla_paused_seconds`, để khai phá quy
-- trình phát hiện ai lạm dụng cách hỏi thêm thông tin để dừng đồng hồ.
--
-- Muốn tính cả thời gian chờ bổ sung vào SLA thì bật `sla_running` cho
-- `awaiting-info` — sửa một giá trị ở đây, không đụng dòng mã nào.

INSERT INTO states (rule_set_id, code, label, description, is_initial, is_terminal, sla_running, display_order) VALUES
    (1, 'submitted',              'Đã gửi',
     'Người tạo vừa gửi, chờ phân loại',                              TRUE, FALSE, FALSE, 1),

    (1, 'classified',             'Đã phân loại',
     'Đã xác định loại yêu cầu và phòng ban phụ trách',               FALSE, FALSE, FALSE, 2),

    (1, 'awaiting-acceptance',    'Chờ phòng ban xác duyệt',
     'Đã chuyển về phòng, chờ họ nhận hoặc từ chối',                  FALSE, FALSE, FALSE, 3),

    (1, 'in-progress',            'Đang xử lý',
     'Phòng ban đã nhận và giao người xử lý',                         FALSE, FALSE, TRUE,  4),

    (1, 'completed',              'Hoàn tất',
     'Người xử lý báo xong, chờ người tạo xác nhận',                  FALSE, FALSE, FALSE, 5),

    (1, 'closed',                 'Đã đóng',
     'Hồ sơ kết thúc',                                                FALSE, TRUE,  FALSE, 6),

    (1, 'awaiting-info',          'Chờ bổ sung thông tin',
     'Hỏi ngược người tạo, không phải trả về phòng ban',              FALSE, FALSE, FALSE, 7),

    (1, 'rejected-by-department', 'Bị phòng ban từ chối',
     'Sai chuyên môn, cần chuyển lại sang phòng khác',                            FALSE, FALSE, FALSE, 8),

    (1, 'escalated',              'Đã leo thang',
     'Quá hạn SLA, đẩy lên cấp trên trong cùng phòng ban',            FALSE, FALSE, TRUE,  9),

    (1, 'cancelled',              'Đã hủy',
     'Người tạo rút yêu cầu',                                         FALSE, TRUE,  FALSE, 10),

    -- Giảng viên (08/10, #102): không gọi việc điều phối viên đóng hồ sơ không phòng nào nhận là
    -- "đóng" như một yêu cầu đã xử lý xong. Trạng thái kết thúc riêng để tầng D tách khỏi số hồ sơ
    -- đã xử lý; không có cạnh mở lại — người gửi tạo hồ sơ mới liên kết hồ sơ này.
    (1, 'rejected-unrouted',      'Không tiếp nhận',
     'Không phòng nào tiếp nhận, điều phối viên đã ghi lý do',        FALSE, TRUE,  FALSE, 11);


-- ---------------------------------------------------------------------------
-- Hai mươi bốn cạnh chuyển trạng thái
-- ---------------------------------------------------------------------------
-- Cột activity_code đi thẳng vào trường activity của nhật ký sự kiện. Nhiều
-- cạnh dùng chung một mã khi chúng là cùng một hành vi nghiệp vụ — ví dụ bốn
-- cạnh hủy. Khai phá quy trình vẫn tách được chúng nhờ cặp from_state, to_state.
--
-- Cạnh đứng đầu theo display_order là hành động chính khi một người thấy từ hai
-- nút trở lên — cổng người gửi tô màu nút đó. Đặt đường xuôi lên trước.
--
-- Chờ bổ sung thông tin (#79): ba nơi hỏi được — điều phối ở Đã gửi, trưởng phòng
-- ở Chờ phòng ban xác duyệt, người xử lý ở Đang xử lý — và ba cạnh trả lời quay về
-- đúng ba nơi đó. Ràng buộc return-to-previous-state chỉ cho đi cạnh về đúng chỗ
-- đã hỏi, nên người gửi chỉ thấy MỘT nút "Bổ sung thông tin". Thêm một nơi hỏi mới
-- thì phải thêm cạnh quay về tương ứng — tệp 99 chặn khởi động nếu thiếu.
--
-- Cạnh tự trỏ (#127, ADR-0005) là thao tác đổi hồ sơ mà giữ nguyên trạng thái: vẫn đi
-- qua cửa chuyển trạng thái để có dòng nhật ký. Mỗi trạng thái tối đa một cạnh tự trỏ.
--
-- Hai cạnh nhóm tự thêm — không phòng nào nhận, và mở lại khi chưa đạt — giảng viên đã đồng
-- ý ngày 08/10 với điều kiện đổi tên trạng thái và thêm giới hạn (#102). Xem
-- docs/process-flow.md mục 8.

INSERT INTO transitions
    (rule_set_id, from_state, to_state, activity_code, activity_label, is_system, requires_note, note_label, display_order)
VALUES
    (1, 'submitted',           'classified',             'classify',            'Phân loại yêu cầu',                   FALSE, FALSE, NULL,                     1),
    (1, 'submitted',           'awaiting-info',          'request-info',        'Yêu cầu bổ sung thông tin',           FALSE, TRUE,  'Thông tin cần bổ sung',  2),
    -- Sửa nội dung trước khi tới phòng ban (#127, ADR-0005). Ở Đã gửi là cạnh tự trỏ;
    -- ở Đã phân loại thì hồ sơ về Đã gửi, vì phân loại cũ dựa trên nội dung cũ.
    (1, 'submitted',           'submitted',              'edit-content',        'Sửa nội dung',                        FALSE, FALSE, NULL,                     3),
    (1, 'submitted',           'cancelled',              'cancel',              'Hủy yêu cầu',                         FALSE, FALSE, NULL,                     4),

    (1, 'classified',          'awaiting-acceptance',    'route-to-department', 'Chuyển về phòng ban',                 FALSE, FALSE, NULL,                     5),
    (1, 'classified',          'submitted',              'edit-content',        'Sửa nội dung',                        FALSE, FALSE, NULL,                     6),
    (1, 'classified',          'cancelled',              'cancel',              'Hủy yêu cầu',                         FALSE, FALSE, NULL,                     7),
    -- Lối thoát khi không phòng nào nhận, tránh luẩn quẩn vô hạn (#102, giảng viên đồng ý
    -- 08/10): đích là Không tiếp nhận chứ không phải Đã đóng, lý do bắt buộc. Người gửi tạo lại
    -- hồ sơ với thông tin rõ hơn — hồ sơ mới liên kết hồ sơ này bằng parent_request_id.
    (1, 'classified',          'rejected-unrouted',      'decline-unrouted',    'Không tiếp nhận, không phòng nào nhận', FALSE, TRUE, 'Lý do không tiếp nhận',   8),

    (1, 'awaiting-acceptance', 'in-progress',            'accept',              'Xác duyệt và giao xử lý',             FALSE, FALSE, NULL,                     9),
    (1, 'awaiting-acceptance', 'awaiting-info',          'request-info',        'Yêu cầu bổ sung thông tin',           FALSE, TRUE,  'Thông tin cần bổ sung', 10),
    (1, 'awaiting-acceptance', 'rejected-by-department', 'reject',              'Từ chối vì sai chuyên môn',           FALSE, TRUE,  NULL,                    11),
    (1, 'awaiting-acceptance', 'cancelled',              'cancel',              'Hủy yêu cầu',                         FALSE, FALSE, NULL,                    12),
    -- Hồ sơ nằm im ở Chờ phòng ban xác duyệt (#142, giảng viên chốt 08/10): điều phối viên
    -- rút về trước hạn, hay hệ thống tự trả về khi hết hạn chờ. Hai cạnh cùng cặp trạng
    -- thái, một của người, một của hệ thống — hạn chờ khai ở ngay dưới.
    (1, 'awaiting-acceptance', 'classified',             'withdraw',            'Rút hồ sơ về điều phối',              FALSE, TRUE,  'Lý do rút hồ sơ',      25),
    (1, 'awaiting-acceptance', 'classified',             'auto-return',         'Tự trả về điều phối',                 TRUE,  FALSE, NULL,                    26),

    (1, 'rejected-by-department', 'classified',          'reroute',             'Chuyển lại sang phòng khác',          FALSE, FALSE, NULL,                    13),

    -- Nhận việc về mình (#127, ADR-0005): cạnh tự trỏ, đổi người xử lý mà không đổi
    -- trạng thái. Chỉ đi được khi hồ sơ chưa giao ai.
    (1, 'in-progress',         'in-progress',            'claim',               'Nhận việc về mình',                   FALSE, FALSE, NULL,                    14),
    (1, 'in-progress',         'awaiting-info',          'request-info',        'Yêu cầu bổ sung thông tin',           FALSE, TRUE,  'Thông tin cần bổ sung', 15),
    (1, 'in-progress',         'escalated',              'escalate',            'Leo thang do quá hạn',                TRUE,  FALSE, NULL,                    16),
    (1, 'in-progress',         'completed',              'complete',            'Hoàn thành xử lý',                    FALSE, FALSE, NULL,                    17),

    (1, 'escalated',           'in-progress',            'reassign',            'Phân công lại trong cùng phòng',      FALSE, FALSE, NULL,                    18),

    -- Ba cạnh trả lời, cùng một hoạt động. Người gửi chỉ thấy một trong ba — cạnh về
    -- đúng chỗ đã hỏi — nên cả ba mang chung một nhãn.
    (1, 'awaiting-info',       'submitted',              'provide-info',        'Bổ sung thông tin',                   FALSE, TRUE,  'Thông tin bổ sung',     19),
    (1, 'awaiting-info',       'awaiting-acceptance',    'provide-info',        'Bổ sung thông tin',                   FALSE, TRUE,  'Thông tin bổ sung',     20),
    (1, 'awaiting-info',       'in-progress',            'provide-info',        'Bổ sung thông tin',                   FALSE, TRUE,  'Thông tin bổ sung',     21),
    (1, 'awaiting-info',       'cancelled',              'cancel',              'Hủy yêu cầu',                         FALSE, FALSE, NULL,                    22),
    -- Người gửi không bổ sung thì hồ sơ tự đóng (#143, giảng viên chốt 08/10): nhắc trước,
    -- vẫn im lặng thì đóng và ghi lý do. Đích là Đã đóng chứ không phải Đã hủy — người gửi
    -- không chủ động bỏ yêu cầu. Mã hoạt động riêng để nhật ký tách được với tự đóng Hoàn tất.
    (1, 'awaiting-info',       'closed',                 'auto-close-no-info',  'Tự đóng vì chưa bổ sung thông tin',   TRUE,  FALSE, NULL,                    28),

    -- Gia hạn xử lý (#101, giảng viên chốt 08/10): cạnh tự trỏ (ADR-0005), lý do bắt buộc,
    -- giá trị cũ và mới vào nhật ký. Điều phối viên gia hạn lần đầu trước khi phòng nhận
    -- việc; lần sau chỉ trưởng phòng, khi hồ sơ đã leo thang — Đang xử lý đã có cạnh tự
    -- trỏ "Nhận việc về mình" (navigator chốt 15/10). Đã đóng chỉ có cạnh mở lại: hết hồ sơ là
    -- hết gia hạn. Giới hạn số giờ và số lần khai ở loại yêu cầu.
    (1, 'classified',          'classified',             'extend-deadline',     'Gia hạn xử lý',                       FALSE, TRUE,  'Lý do gia hạn',        29),
    (1, 'awaiting-acceptance', 'awaiting-acceptance',    'extend-deadline',     'Gia hạn xử lý',                       FALSE, TRUE,  'Lý do gia hạn',        30),
    (1, 'escalated',           'escalated',              'extend-deadline',     'Gia hạn xử lý',                       FALSE, TRUE,  'Lý do gia hạn',        31),

    (1, 'completed',           'closed',                 'confirm',             'Xác nhận đạt',                        FALSE, FALSE, NULL,                    23),
    -- Mở lại khi chưa đạt; hồ sơ ở lại đúng phòng ban đã nhận. Mỗi hồ sơ mở lại tối đa
    -- request_types.reopen_max_count lần, mở lại là mở chu kỳ xử lý mới (#102).
    (1, 'completed',           'in-progress',            'reopen',              'Mở lại, chưa đạt',                    FALSE, TRUE,  NULL,                    24),
    -- Người gửi không xác nhận thì hồ sơ Hoàn tất tự đóng (#144, giảng viên chốt 08/10):
    -- Hoàn tất đã là xử lý xong nghiệp vụ, Đã đóng mới hết chu kỳ hồ sơ. Cùng cặp trạng thái
    -- với Xác nhận đạt của người gửi — hạn chờ khai ở ngay dưới.
    (1, 'completed',           'closed',                 'auto-close',          'Tự đóng hồ sơ',                       TRUE,  FALSE, NULL,                    27);

-- Hạn chờ của cạnh tự đi (#142), tính bằng giờ làm việc (#199): hết hạn thì bộ quét đi
-- cạnh thay người; còn `warn_before_hours` thì màn hình báo trước. Tự trả về không phải cạnh
-- làm lại — phòng ban không từ chối nội dung, chỉ để quá hạn (navigator chốt 12/10).
UPDATE transitions
   SET auto_after_hours = 24, warn_before_hours = 4
 WHERE rule_set_id = 1 AND activity_code = 'auto-return';

-- "3 ngày làm việc" của giảng viên = 24 giờ làm việc với lịch mẫu 8 giờ một ngày; báo
-- trước một ngày làm việc (navigator chốt 12/10, #144). Đổi lịch thì xem lại con số này.
UPDATE transitions
   SET auto_after_hours = 24, warn_before_hours = 8
 WHERE rule_set_id = 1 AND activity_code = 'auto-close';

-- Chờ bổ sung thông tin (#143): giảng viên chốt "nhắc sau 2 ngày"; navigator chốt 15/10 tự
-- đóng sau 5 ngày làm việc. Với lịch mẫu 8 giờ một ngày: đóng sau 40 giờ làm việc, dấu nhắc
-- hiện từ giờ thứ 16 — tức báo trước 24 giờ. Đồng hồ SLA của phòng ban vẫn dừng ở trạng thái
-- này (cột sla_running), hạn chờ là đồng hồ riêng của người gửi.
UPDATE transitions
   SET auto_after_hours = 40, warn_before_hours = 24
 WHERE rule_set_id = 1 AND activity_code = 'auto-close-no-info';

-- Đính kèm tệp (#80, navigator chốt 26/10): người gửi đính kèm được khi họ đang có một cạnh
-- Sửa nội dung hay Bổ sung thông tin — lúc vừa gửi, lúc sửa nội dung, lúc trả lời câu hỏi.
-- Tới phòng ban thì không cạnh nào mang cờ, việc đính kèm khóa lại. Muốn mở thêm chỗ đính
-- kèm thì bật cờ cho cạnh khác ở đây, không sửa mã.
UPDATE transitions
   SET accepts_attachments = TRUE
 WHERE rule_set_id = 1
   AND NOT is_system
   AND activity_code IN ('edit-content', 'provide-info');

-- Bước chính của từng trạng thái (#227): hồ sơ đứng ở đó là đang chờ người đi được cạnh này,
-- và cờ needs_my_action trên danh sách hồ sơ bật cho họ. Sửa, hủy, gia hạn, hỏi thêm, rút về,
-- nhận việc không phải bước chính: bấm được nhưng hồ sơ không chờ họ. Hoàn thành xử lý chờ
-- người được giao, chưa giao ai thì chờ cả phòng. Đổi bước chính thì sửa ở đây, không sửa mã.
UPDATE transitions
   SET primary_scope = 'role'
 WHERE rule_set_id = 1
   AND NOT is_system
   AND activity_code IN ('classify', 'route-to-department', 'accept', 'reroute',
                         'reassign', 'provide-info', 'confirm');

UPDATE transitions
   SET primary_scope = 'assignee'
 WHERE rule_set_id = 1
   AND NOT is_system
   AND activity_code = 'complete';

-- Mở lại sau khi đã đóng (#102, giảng viên chốt 08/10): trong 7 ngày làm việc kể từ lúc hồ sơ vào
-- Đã đóng — 56 giờ làm việc với lịch mẫu 8 giờ một ngày, đổi lịch thì xem lại con số này. Đây là
-- cạnh DUY NHẤT rời khỏi một trạng thái kết thúc, nên khai cột from_is_terminal và cửa sổ thời gian
-- mà lược đồ đòi. Chỉ hồ sơ đã từng làm xong mới mở lại được (ràng buộc reopen-from-rework): hồ sơ tự
-- đóng vì chưa bổ sung thông tin chưa có gì để "chưa đạt". Quá cửa sổ hay hết lượt thì người gửi tạo
-- hồ sơ mới liên kết hồ sơ cũ.
INSERT INTO transitions
    (rule_set_id, from_state, to_state, activity_code, activity_label, is_system, requires_note,
     note_label, display_order, is_rework, from_is_terminal, reopen_window_hours, restarts_sla)
VALUES
    (1, 'closed', 'in-progress', 'reopen-after-close', 'Mở lại sau khi đóng', FALSE, TRUE,
     NULL, 32, TRUE, TRUE, 56, TRUE);

-- Mở lại từ Hoàn tất cũng là chu kỳ xử lý mới: đồng hồ SLA đếm lại, gia hạn cũ không kế thừa
UPDATE transitions
   SET restarts_sla = TRUE
 WHERE rule_set_id = 1 AND activity_code = 'reopen';

-- Cạnh làm lại (#153): hồ sơ bị đẩy ngược để làm lại. Dòng thời gian đếm "quay lui" theo
-- đúng các cạnh này — hỏi đáp bổ sung thông tin, phân công lại sau leo thang không tính.
-- Doanh nghiệp đổi cạnh nào là làm lại thì sửa danh sách này, không sửa mã.
UPDATE transitions t
   SET is_rework = TRUE
  FROM (VALUES
    ('awaiting-acceptance', 'rejected-by-department'),   -- phòng từ chối vì sai chuyên môn
    ('completed',           'in-progress'),              -- người gửi mở lại vì chưa đạt
    ('classified',          'submitted')                 -- sửa nội dung sau khi đã phân loại
  ) AS v (from_state, to_state)
 WHERE t.rule_set_id = 1
   AND t.from_state  = v.from_state
   AND t.to_state    = v.to_state;


-- ---------------------------------------------------------------------------
-- Ma trận phân quyền
-- ---------------------------------------------------------------------------
-- Cạnh leo thang không có mặt ở đây vì nó đã đánh dấu is_system — hệ thống tự
-- đi, không vai trò người nào đi được. Một cặp trạng thái có thể có cả cạnh người lẫn
-- cạnh hệ thống (#142), nên phép nối dưới đây chỉ nhận cạnh của người. Vai trò administrator cũng không có mặt:
-- quản trị viên sửa cấu hình chứ không đẩy hồ sơ.

INSERT INTO transition_roles (transition_id, role_code)
SELECT t.id, v.role_code
FROM (VALUES
    ('submitted',              'classified',             'classifier'),
    ('submitted',              'awaiting-info',          'classifier'),
    ('submitted',              'submitted',              'requester'),
    ('submitted',              'cancelled',              'requester'),

    ('classified',             'awaiting-acceptance',    'classifier'),
    ('classified',             'submitted',              'requester'),
    ('classified',             'cancelled',              'requester'),
    ('classified',             'rejected-unrouted',      'classifier'),

    ('awaiting-acceptance',    'in-progress',            'approver'),
    ('awaiting-acceptance',    'awaiting-info',          'approver'),
    ('awaiting-acceptance',    'rejected-by-department', 'approver'),
    ('awaiting-acceptance',    'cancelled',              'requester'),
    ('awaiting-acceptance',    'classified',             'classifier'),

    ('rejected-by-department', 'classified',             'classifier'),

    ('in-progress',            'in-progress',            'handler'),
    ('in-progress',            'awaiting-info',          'handler'),
    ('in-progress',            'completed',              'handler'),

    ('escalated',              'in-progress',            'approver'),

    -- Gia hạn xử lý (#101): điều phối trước khi phòng nhận, trưởng phòng sau leo thang
    ('classified',             'classified',             'classifier'),
    ('awaiting-acceptance',    'awaiting-acceptance',    'classifier'),
    ('escalated',              'escalated',              'approver'),

    ('awaiting-info',          'submitted',              'requester'),
    ('awaiting-info',          'awaiting-acceptance',    'requester'),
    ('awaiting-info',          'in-progress',            'requester'),
    ('awaiting-info',          'cancelled',              'requester'),

    ('completed',              'closed',                 'requester'),
    ('completed',              'in-progress',            'requester'),
    ('closed',                 'in-progress',            'requester')
) AS v (from_state, to_state, role_code)
JOIN transitions t
  ON t.rule_set_id = 1
 AND t.from_state  = v.from_state
 AND t.to_state    = v.to_state
 AND NOT t.is_system;


-- ---------------------------------------------------------------------------
-- Ràng buộc Poka-yoke kiểm tra lúc chạy
-- ---------------------------------------------------------------------------
-- Hai trong bốn ràng buộc ở docs/process-flow.md mục 5 KHÔNG xuất hiện ở đây vì
-- chúng đã được thực thi bằng cấu trúc:
--
--   "Đã nhận là không trả về"   — không tồn tại cạnh nào từ in-progress ngược về
--                                 awaiting-acceptance hay classified
--   "Chỉ hủy trước khi vào xử lý" — cạnh cancel chỉ xuất phát từ bốn trạng thái
--                                 trước khi nhận việc
--
-- Hai ràng buộc còn lại cần đối chiếu người thao tác với hồ sơ nên phải khai
-- báo thành dòng, cùng năm ràng buộc bổ trợ.
--
-- Ràng buộc còn quyết định TRƯỜNG NÀO ĐẶT ĐƯỢC Ở CẠNH NÀO. Một lần chuyển chỉ kèm
-- được trường mà ràng buộc trên cạnh đó quản — bản đồ nằm ở GUARD_REGISTRY trong
-- backend/app/rules/guards.py. Gỡ set-priority khỏi một cạnh là cạnh đó hết đặt được
-- mức ưu tiên, không cần sửa mã.

INSERT INTO guards (code, label, description) VALUES
    ('requester-owns-case',
     'Phải là người tạo hồ sơ',
     'Người thao tác phải chính là người đã gửi yêu cầu. Không có ràng buộc này thì bất kỳ ai mang vai trò requester cũng hủy được hồ sơ của người khác.'),

    ('actor-not-requester',
     'Không tự điều phối hồ sơ của mình',
     'Người thao tác không được là người đã gửi hồ sơ. Gắn vào các cạnh của vai điều phối: một người vừa gửi yêu cầu vừa là điều phối viên thì không tự phân loại, tự đặt mức ưu tiên, tự chuyển phòng hay tự đóng hồ sơ của chính mình. Phòng ban không gắn — nhân viên tự làm việc của chính mình là bình thường.'),

    ('actor-in-case-department',
     'Phải thuộc phòng ban đang giữ hồ sơ',
     'Người thao tác phải thuộc phòng ban mà hồ sơ đang được giao. Chặn việc phòng này can thiệp vào hồ sơ của phòng khác.'),

    ('set-priority',
     'Bắt buộc đặt mức ưu tiên',
     'Cạnh này bắt buộc ghi mức ưu tiên. Ưu tiên do người phân loại đặt — người tạo yêu cầu không bao giờ tự đặt được, vì không có cạnh nào của vai trò requester mang ràng buộc này.'),

    ('select-department',
     'Bắt buộc chọn phòng ban phụ trách',
     'Cạnh này bắt buộc chọn phòng ban. Danh sách gợi ý lấy từ bảng request_type_routing, nhưng người phân loại được chọn khác.'),

    ('department-unchanged',
     'Không được đổi phòng ban',
     'Cạnh này giữ nguyên phòng ban của hồ sơ, chỉ đổi người phụ trách. Leo thang là chuyện nội bộ một phòng.'),

    ('set-request-type',
     'Bắt buộc có loại yêu cầu',
     'Hồ sơ phải có loại yêu cầu khi rời khỏi tay người phân loại. Giữ loại người gửi đã chọn, hoặc đặt mới nếu người gửi bỏ trống. Không có loại thì không có ngưỡng SLA, và bộ quét quá hạn sẽ bỏ qua hồ sơ đó mà không báo gì.'),

    ('assign-handler',
     'Cho phép giao người xử lý',
     'Cạnh này cho phép giao hồ sơ cho một người xử lý cụ thể trong phòng ban. Chưa bắt buộc: hồ sơ vẫn thuộc cả phòng, và mọi người xử lý trong phòng đều thao tác được.'),

    ('return-to-previous-state',
     'Quay về đúng chỗ đã hỏi',
     'Cạnh này chỉ đi được khi đích chính là trạng thái hồ sơ đã ở ngay trước trạng thái hiện tại, đọc từ nhật ký sự kiện. Gắn vào mọi cạnh trả lời ra khỏi Chờ bổ sung thông tin: ai hỏi thì hồ sơ về đúng người đó, và người gửi chỉ thấy một nút thay vì phải đoán.'),

    ('edit-content',
     'Cho sửa nội dung',
     'Cạnh này cho người gửi sửa tiêu đề, mô tả, loại yêu cầu. Chỉ gắn vào cạnh xuất phát từ trạng thái hồ sơ chưa tới phòng ban — tới phòng ban rồi thì không còn cạnh sửa nào. Nội dung cũ không mất: cột changes của nhật ký giữ giá trị cũ. Phải thật sự đổi một thứ gì đó, và giữ cùng giới hạn độ dài với lúc gửi.'),

    ('assign-self',
     'Tự nhận việc',
     'Cạnh này chỉ đi được khi hồ sơ chưa giao cho ai, và tự đặt người xử lý là chính người thao tác — không có ô chọn người. Hồ sơ đã có người giữ thì phải nhờ trưởng phòng phân công lại.'),

    ('extend-deadline',
     'Gia hạn xử lý',
     'Cạnh này cho nhập số giờ làm việc gia hạn thêm: từ 1 tới request_types.sla_extension_max_percent phần trăm hạn gốc — hạn của loại yêu cầu nhân hệ số của mức ưu tiên. Tự cộng vào tổng giờ gia hạn và đếm số lần; nhật ký giữ giá trị cũ và mới (#101).'),

    ('first-extension',
     'Chỉ gia hạn lần đầu',
     'Cạnh này chỉ đi được khi hồ sơ chưa gia hạn lần nào. Gắn vào cạnh gia hạn của điều phối viên: lần gia hạn thứ hai chỉ trưởng phòng được làm (#101).'),

    ('extension-limit',
     'Chưa hết lượt gia hạn',
     'Cạnh này chỉ đi được khi hồ sơ gia hạn chưa tới request_types.sla_extension_max_count lần (#101).'),

    ('reopen-limit',
     'Chưa hết lượt mở lại',
     'Cạnh này chỉ đi được khi hồ sơ mở lại chưa tới request_types.reopen_max_count lần (#102). Gắn vào cả hai cạnh mở lại — từ Hoàn tất và từ Đã đóng — nên số lần tính chung. Đi qua cạnh thì đếm thêm một lần và đưa gia hạn về 0: chu kỳ xử lý mới có hạn mới.'),

    ('reopen-window',
     'Còn trong cửa sổ mở lại',
     'Cạnh này chỉ đi được khi hồ sơ vào trạng thái kết thúc chưa quá transitions.reopen_window_hours giờ làm việc (#102). Quá cửa sổ thì hồ sơ kết thúc hẳn.'),

    ('reopen-from-rework',
     'Chỉ mở lại hồ sơ đã từng làm xong',
     'Cạnh này chỉ đi được khi trạng thái hồ sơ đứng ngay trước khi kết thúc có một cạnh làm lại về cùng đích (#102): hồ sơ Hoàn tất rồi đóng thì mở lại được, hồ sơ tự đóng vì chưa bổ sung thông tin thì không.');

INSERT INTO transition_guards (transition_id, guard_code)
SELECT t.id, v.guard_code
FROM (VALUES
    -- Người tạo chỉ thao tác được trên hồ sơ của chính mình
    ('submitted',           'cancelled',              'requester-owns-case'),
    ('classified',          'cancelled',              'requester-owns-case'),
    ('awaiting-acceptance', 'cancelled',              'requester-owns-case'),
    ('awaiting-info',       'cancelled',              'requester-owns-case'),
    ('awaiting-info',       'submitted',              'requester-owns-case'),
    ('awaiting-info',       'awaiting-acceptance',    'requester-owns-case'),
    ('awaiting-info',       'in-progress',            'requester-owns-case'),
    ('submitted',           'submitted',              'requester-owns-case'),
    ('classified',          'submitted',              'requester-owns-case'),
    ('completed',           'closed',                 'requester-owns-case'),
    ('completed',           'in-progress',            'requester-owns-case'),
    ('closed',              'in-progress',            'requester-owns-case'),

    -- Mở lại có giới hạn (#102): tối đa reopen_max_count lần cho cả hai cạnh; từ Đã đóng thì
    -- thêm cửa sổ 7 ngày làm việc và chỉ hồ sơ từng làm xong
    ('completed',           'in-progress',            'reopen-limit'),
    ('closed',              'in-progress',            'reopen-limit'),
    ('closed',              'in-progress',            'reopen-window'),
    ('closed',              'in-progress',            'reopen-from-rework'),

    -- Bổ sung thông tin xong thì về đúng chỗ đã hỏi (#79)
    ('awaiting-info',       'submitted',              'return-to-previous-state'),
    ('awaiting-info',       'awaiting-acceptance',    'return-to-previous-state'),
    ('awaiting-info',       'in-progress',            'return-to-previous-state'),

    -- Sửa nội dung chỉ trước khi tới phòng ban (#127). Khóa sau đó bằng sự vắng mặt:
    -- không cạnh sửa nào xuất phát từ trạng thái của phòng ban
    ('submitted',           'submitted',              'edit-content'),
    ('classified',          'submitted',              'edit-content'),

    -- Điều phối viên không tự điều phối hồ sơ do chính mình gửi (#154): mọi cạnh của vai
    -- điều phối. Cạnh của phòng ban không gắn — tự làm việc của mình là bình thường
    ('submitted',           'classified',             'actor-not-requester'),
    ('submitted',           'awaiting-info',          'actor-not-requester'),
    ('classified',          'awaiting-acceptance',    'actor-not-requester'),
    ('classified',          'rejected-unrouted',      'actor-not-requester'),
    ('rejected-by-department', 'classified',          'actor-not-requester'),
    ('awaiting-acceptance', 'classified',             'actor-not-requester'),

    -- Phòng ban chỉ thao tác được trên hồ sơ của phòng mình
    ('awaiting-acceptance', 'in-progress',            'actor-in-case-department'),
    ('awaiting-acceptance', 'awaiting-info',          'actor-in-case-department'),
    ('awaiting-acceptance', 'rejected-by-department', 'actor-in-case-department'),
    ('in-progress',         'in-progress',            'actor-in-case-department'),
    ('in-progress',         'awaiting-info',          'actor-in-case-department'),
    ('in-progress',         'completed',              'actor-in-case-department'),
    ('escalated',           'in-progress',            'actor-in-case-department'),

    -- Mức ưu tiên đặt đúng một lần, ở tay người phân loại. Cùng lúc đó hồ sơ phải có
    -- loại yêu cầu, vì loại quyết định ngưỡng SLA.
    ('submitted',           'classified',             'set-priority'),
    ('submitted',           'classified',             'set-request-type'),

    -- Phòng ban phụ trách chọn ở chặng chuyển về phòng. Loại yêu cầu kiểm thêm một lần
    -- ở đây vì đây là cửa DUY NHẤT dẫn tới phòng ban — lưới an toàn cho mọi đường vào
    -- classified không qua cạnh submitted -> classified. Trước #79 đường vòng qua
    -- awaiting-info là một đường như vậy; nay nó quay về submitted.
    ('classified',          'awaiting-acceptance',    'select-department'),
    ('classified',          'awaiting-acceptance',    'set-request-type'),

    -- Người xử lý giao ở hai chặng: lúc phòng nhận việc, và lúc phân công lại sau leo thang
    ('awaiting-acceptance', 'in-progress',            'assign-handler'),
    ('escalated',           'in-progress',            'assign-handler'),

    -- Người xử lý tự nhận hồ sơ chưa giao ai (#127): người được giao là chính họ, nên
    -- không có ô chọn người, và họ không thành vai trò giao việc
    ('in-progress',         'in-progress',            'assign-self'),

    -- Leo thang không đổi phòng
    ('escalated',           'in-progress',            'department-unchanged'),

    -- Gia hạn xử lý (#101). Điều phối viên chỉ gia hạn lần đầu, và không gia hạn hồ sơ
    -- mình gửi; trưởng phòng gia hạn hồ sơ của phòng mình tới khi hết lượt.
    ('classified',          'classified',             'extend-deadline'),
    ('classified',          'classified',             'first-extension'),
    ('classified',          'classified',             'actor-not-requester'),
    ('awaiting-acceptance', 'awaiting-acceptance',    'extend-deadline'),
    ('awaiting-acceptance', 'awaiting-acceptance',    'first-extension'),
    ('awaiting-acceptance', 'awaiting-acceptance',    'actor-not-requester'),
    ('escalated',           'escalated',              'extend-deadline'),
    ('escalated',           'escalated',              'extension-limit'),
    ('escalated',           'escalated',              'actor-in-case-department')
) AS v (from_state, to_state, guard_code)
JOIN transitions t
  ON t.rule_set_id = 1
 AND t.from_state  = v.from_state
 AND t.to_state    = v.to_state
 AND NOT t.is_system;


-- ---------------------------------------------------------------------------
-- Mức ưu tiên
-- ---------------------------------------------------------------------------

-- Hạn theo mức ưu tiên (#101, giảng viên chốt 08/10): hạn = hạn chuẩn của loại yêu cầu ×
-- sla_factor_percent / 100. Ân hạn nhân cùng hệ số (navigator chốt 15/10). Sự cố thiết bị
-- 8 giờ: Khẩn 4 giờ, Cao 6, Bình thường 8, Thấp 12.
INSERT INTO priorities (code, label, is_default, display_order, sla_factor_percent) VALUES
    ('low',    'Thấp',        FALSE, 1, 150),
    ('normal', 'Bình thường', TRUE,  2, 100),
    ('high',   'Cao',         FALSE, 3,  75),
    ('urgent', 'Khẩn',        FALSE, 4,  50);


-- ---------------------------------------------------------------------------
-- Loại lời nhắn trên hồ sơ (#128, ADR-0005)
-- ---------------------------------------------------------------------------
-- Lời nhắn không đổi hồ sơ nên không phải cạnh: không đổi trạng thái, không dừng
-- đồng hồ, không bắt ai phải trả lời. Hỏi chính thức — dừng đồng hồ, bắt buộc trả lời
-- — vẫn là cạnh "Yêu cầu bổ sung thông tin" ở trên.
--
-- Chốt với navigator ngày 24/09/2026: lời nhắn hai chiều, ai mở được hồ sơ thì nhắn
-- được; hồ sơ kết thúc thì chỉ đọc. "Hỏi tiến độ" là loại riêng của người gửi, chỉ khi
-- hồ sơ ở phòng ban, và hỏi lại chỉ khi phòng ban đã trả lời hoặc đã quá bốn giờ — để
-- số lần phòng ban bị hối mà tầng I đếm không bị thổi phồng.

--
-- Chốt ngày 04/10 và 06/10/2026 (#156): mỗi hồ sơ có thêm một cuộc trò chuyện NỘI BỘ chỉ
-- nhân viên đang mở được hồ sơ thấy — ví dụ điều phối viên hỏi trưởng phòng "phòng chị
-- nhận vụ này không?" trước khi trả qua lại. Người gửi của hồ sơ không thấy, kể cả khi họ
-- cũng là nhân viên. Không tính vào "người gửi đang chờ trả lời", không mở khóa luật hỏi
-- lại của "Hỏi tiến độ"; hồ sơ kết thúc thì chỉ đọc như mọi lời nhắn.

INSERT INTO message_kinds
    (code, label, description, owner_only, department_stage_only,
     reask_after_hours, body_required, hidden_from_requester, display_order) VALUES
    ('message',          'Gửi lời nhắn',
     'Trao đổi thêm trên hồ sơ, hai chiều giữa người gửi và nhân viên đang giữ hồ sơ.',
     FALSE, FALSE, NULL, TRUE,  FALSE, 1),

    ('progress-inquiry', 'Hỏi tiến độ',
     'Người gửi hỏi phòng ban đang giữ hồ sơ việc đã tới đâu. Hỏi lại được khi phòng ban đã trả lời, hoặc đã quá bốn giờ mà chưa ai trả lời.',
     TRUE,  TRUE,  4,    FALSE, FALSE, 2),

    ('internal-note',    'Nhắn nội bộ',
     'Trao đổi giữa nhân viên đang giữ hồ sơ. Người gửi hồ sơ không thấy.',
     FALSE, FALSE, NULL, TRUE,  TRUE,  3);

-- Quản trị viên không có mặt: họ không mở hồ sơ nào ở buồng lái nào
INSERT INTO message_kind_roles (kind_code, role_code) VALUES
    ('message',          'requester'),
    ('message',          'classifier'),
    ('message',          'approver'),
    ('message',          'handler'),
    ('progress-inquiry', 'requester'),
    ('internal-note',    'classifier'),
    ('internal-note',    'approver'),
    ('internal-note',    'handler');
