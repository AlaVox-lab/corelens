-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 AlaVox-lab
--
-- Dữ liệu khởi tạo: bộ quy tắc quy trình v1.
--
-- Nội dung tệp này là bản sao chạy được của docs/process-flow.md mục 2 tới 5 —
-- mười trạng thái, mười chín cạnh, năm vai trò, các ràng buộc Poka-yoke. Sửa
-- luồng nghiệp vụ nghĩa là sửa tệp này, không phải sửa mã nguồn.
--
-- Hai tệp phải khớp nhau. Khi đổi một bên, đổi cả bên kia trong cùng công việc.

\set ON_ERROR_STOP on


-- ---------------------------------------------------------------------------
-- Bộ quy tắc
-- ---------------------------------------------------------------------------

INSERT INTO rule_sets (id, version, label, effective_from, is_active, note) VALUES
    (1, 'v1', 'Bộ quy tắc ban đầu — mười trạng thái, mười chín cạnh',
     TIMESTAMPTZ '2026-09-10 00:00:00+00', TRUE,
     'Chốt trong buổi trao đổi với giảng viên hướng dẫn ngày 10/09/2026: năm vai trò, thêm chặng định tuyến phòng ban, bỏ cổng phê duyệt chi phí.');


-- ---------------------------------------------------------------------------
-- Năm vai trò
-- ---------------------------------------------------------------------------
-- Mã phải trùng tên vai trò realm trong infra/keycloak/realm-dx-os-lab.json.

INSERT INTO roles (code, label, description, display_order) VALUES
    ('requester',     'Người tạo yêu cầu',
     'Gửi yêu cầu, bổ sung thông tin, hủy khi được phép, xác nhận hoặc mở lại', 1),

    ('classifier',    'Người phân loại yêu cầu',
     'Phân loại, chọn phòng ban phụ trách, đặt mức ưu tiên, định tuyến lại khi bị từ chối', 2),

    ('approver',      'Người xét duyệt yêu cầu',
     'Quyết định phòng ban nhận hay không nhận, phân công lại khi leo thang', 3),

    ('handler',       'Người xử lý yêu cầu',
     'Thực hiện công việc, hỏi thêm thông tin khi cần, báo hoàn thành', 4),

    ('administrator', 'Quản trị viên',
     'Không đi cạnh nào. Quản lý phòng ban, loại yêu cầu, ngưỡng SLA, bảng ánh xạ loại sang phòng', 5);


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
     'Sai chuyên môn, cần định tuyến lại',                            FALSE, FALSE, FALSE, 8),

    (1, 'escalated',              'Đã leo thang',
     'Quá hạn SLA, đẩy lên cấp trên trong cùng phòng ban',            FALSE, FALSE, TRUE,  9),

    (1, 'cancelled',              'Đã hủy',
     'Người tạo rút yêu cầu',                                         FALSE, TRUE,  FALSE, 10);


-- ---------------------------------------------------------------------------
-- Mười chín cạnh chuyển trạng thái
-- ---------------------------------------------------------------------------
-- Cột activity_code đi thẳng vào trường activity của nhật ký sự kiện. Nhiều
-- cạnh dùng chung một mã khi chúng là cùng một hành vi nghiệp vụ — ví dụ bốn
-- cạnh hủy. Khai phá quy trình vẫn tách được chúng nhờ cặp from_state, to_state.
--
-- Hai cạnh đánh dấu [CHỜ XÁC NHẬN] là suy luận của nhóm, chưa được giảng viên
-- duyệt. Xem docs/process-flow.md mục 8. Nếu thầy bác thì xóa đúng một dòng ở
-- đây và một dòng ma trận phân quyền tương ứng — không đụng tới mã nguồn.

INSERT INTO transitions
    (rule_set_id, from_state, to_state, activity_code, activity_label, is_system, requires_note, display_order)
VALUES
    (1, 'submitted',           'classified',             'classify',            'Phân loại yêu cầu',                             FALSE, FALSE,  1),
    (1, 'submitted',           'awaiting-info',          'request-info',        'Yêu cầu bổ sung thông tin',                     FALSE, TRUE,   2),
    (1, 'submitted',           'cancelled',              'cancel',              'Hủy yêu cầu',                                   FALSE, FALSE,  3),

    (1, 'classified',          'awaiting-acceptance',    'route-to-department', 'Chuyển về phòng ban',                           FALSE, FALSE,  4),
    (1, 'classified',          'cancelled',              'cancel',              'Hủy yêu cầu',                                   FALSE, FALSE,  5),
    -- [CHỜ XÁC NHẬN] lối thoát khi không phòng nào nhận, tránh luẩn quẩn vô hạn
    (1, 'classified',          'closed',                 'close-unrouted',      'Đóng hồ sơ, không phòng nào nhận',              FALSE, TRUE,   6),

    (1, 'awaiting-acceptance', 'in-progress',            'accept',              'Xác duyệt và giao xử lý',                       FALSE, FALSE,  7),
    (1, 'awaiting-acceptance', 'rejected-by-department', 'reject',              'Từ chối vì sai chuyên môn',                     FALSE, TRUE,   8),
    (1, 'awaiting-acceptance', 'cancelled',              'cancel',              'Hủy yêu cầu',                                   FALSE, FALSE,  9),

    (1, 'rejected-by-department', 'classified',          'reroute',             'Định tuyến lại phòng khác',                     FALSE, FALSE, 10),

    (1, 'in-progress',         'awaiting-info',          'request-info',        'Yêu cầu bổ sung thông tin',                     FALSE, TRUE,  11),
    (1, 'in-progress',         'escalated',              'escalate',            'Leo thang do quá hạn',                          TRUE,  FALSE, 12),
    (1, 'in-progress',         'completed',              'complete',            'Hoàn thành xử lý',                              FALSE, FALSE, 13),

    (1, 'escalated',           'in-progress',            'reassign',            'Phân công lại trong cùng phòng',                FALSE, FALSE, 14),

    (1, 'awaiting-info',       'classified',             'provide-info',        'Bổ sung thông tin — người phân loại đã hỏi',    FALSE, FALSE, 15),
    (1, 'awaiting-info',       'in-progress',            'provide-info',        'Bổ sung thông tin — người xử lý đã hỏi',        FALSE, FALSE, 16),
    (1, 'awaiting-info',       'cancelled',              'cancel',              'Hủy yêu cầu',                                   FALSE, FALSE, 17),

    (1, 'completed',           'closed',                 'confirm',             'Xác nhận đạt',                                  FALSE, FALSE, 18),
    -- [CHỜ XÁC NHẬN] mở lại khi chưa đạt; hồ sơ ở lại đúng phòng ban đã nhận
    (1, 'completed',           'in-progress',            'reopen',              'Mở lại, chưa đạt',                              FALSE, TRUE,  19);


-- ---------------------------------------------------------------------------
-- Ma trận phân quyền
-- ---------------------------------------------------------------------------
-- Cạnh leo thang không có mặt ở đây vì nó đã đánh dấu is_system — hệ thống tự
-- đi, không vai trò người nào đi được. Vai trò administrator cũng không có mặt:
-- quản trị viên sửa cấu hình chứ không đẩy hồ sơ.

INSERT INTO transition_roles (transition_id, role_code)
SELECT t.id, v.role_code
FROM (VALUES
    ('submitted',              'classified',             'classifier'),
    ('submitted',              'awaiting-info',          'classifier'),
    ('submitted',              'cancelled',              'requester'),

    ('classified',             'awaiting-acceptance',    'classifier'),
    ('classified',             'cancelled',              'requester'),
    ('classified',             'closed',                 'classifier'),

    ('awaiting-acceptance',    'in-progress',            'approver'),
    ('awaiting-acceptance',    'rejected-by-department', 'approver'),
    ('awaiting-acceptance',    'cancelled',              'requester'),

    ('rejected-by-department', 'classified',             'classifier'),

    ('in-progress',            'awaiting-info',          'handler'),
    ('in-progress',            'completed',              'handler'),

    ('escalated',              'in-progress',            'approver'),

    ('awaiting-info',          'classified',             'requester'),
    ('awaiting-info',          'in-progress',            'requester'),
    ('awaiting-info',          'cancelled',              'requester'),

    ('completed',              'closed',                 'requester'),
    ('completed',              'in-progress',            'requester')
) AS v (from_state, to_state, role_code)
JOIN transitions t
  ON t.rule_set_id = 1
 AND t.from_state  = v.from_state
 AND t.to_state    = v.to_state;


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
-- báo thành dòng, cùng ba ràng buộc bổ trợ.

INSERT INTO guards (code, label, description) VALUES
    ('requester-owns-case',
     'Phải là người tạo hồ sơ',
     'Người thao tác phải chính là người đã gửi yêu cầu. Không có ràng buộc này thì bất kỳ ai mang vai trò requester cũng hủy được hồ sơ của người khác.'),

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
     'Cạnh này giữ nguyên phòng ban của hồ sơ, chỉ đổi người phụ trách. Leo thang là chuyện nội bộ một phòng.');

INSERT INTO transition_guards (transition_id, guard_code)
SELECT t.id, v.guard_code
FROM (VALUES
    -- Người tạo chỉ thao tác được trên hồ sơ của chính mình
    ('submitted',           'cancelled',              'requester-owns-case'),
    ('classified',          'cancelled',              'requester-owns-case'),
    ('awaiting-acceptance', 'cancelled',              'requester-owns-case'),
    ('awaiting-info',       'cancelled',              'requester-owns-case'),
    ('awaiting-info',       'classified',             'requester-owns-case'),
    ('awaiting-info',       'in-progress',            'requester-owns-case'),
    ('completed',           'closed',                 'requester-owns-case'),
    ('completed',           'in-progress',            'requester-owns-case'),

    -- Phòng ban chỉ thao tác được trên hồ sơ của phòng mình
    ('awaiting-acceptance', 'in-progress',            'actor-in-case-department'),
    ('awaiting-acceptance', 'rejected-by-department', 'actor-in-case-department'),
    ('in-progress',         'awaiting-info',          'actor-in-case-department'),
    ('in-progress',         'completed',              'actor-in-case-department'),
    ('escalated',           'in-progress',            'actor-in-case-department'),

    -- Mức ưu tiên đặt đúng một lần, ở tay người phân loại
    ('submitted',           'classified',             'set-priority'),

    -- Phòng ban phụ trách chọn ở chặng chuyển về phòng
    ('classified',          'awaiting-acceptance',    'select-department'),

    -- Leo thang không đổi phòng
    ('escalated',           'in-progress',            'department-unchanged')
) AS v (from_state, to_state, guard_code)
JOIN transitions t
  ON t.rule_set_id = 1
 AND t.from_state  = v.from_state
 AND t.to_state    = v.to_state;


-- ---------------------------------------------------------------------------
-- Mức ưu tiên
-- ---------------------------------------------------------------------------

INSERT INTO priorities (code, label, is_default, display_order) VALUES
    ('low',    'Thấp',        FALSE, 1),
    ('normal', 'Bình thường', TRUE,  2),
    ('high',   'Cao',         FALSE, 3),
    ('urgent', 'Khẩn',        FALSE, 4);
