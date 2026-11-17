-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 AlaVox-lab
--
-- Dữ liệu khởi tạo: quy trình mẫu thứ hai — đề xuất mua sắm duyệt hai cấp (#376, nền tảng lõi Mức 2).
--
-- Chứng minh động cơ luồng công việc phục vụ được một ứng dụng khác chỉ bằng DỮ LIỆU: không một dòng mã nào
-- biết quy trình này tồn tại. Một ứng dụng ngoài cổng người dùng chạy trọn nó qua API của lõi `/core/v1`
-- (examples/goi-loi/quy_trinh_mua_sam.py). Mọi luật sẵn có đọc từ bộ quy tắc của hồ sơ nên chạy luôn cho
-- quy trình này: ràng buộc Poka-yoke trên cạnh, ghi chú bắt buộc, hạn tính bằng giờ làm việc, trường riêng
-- theo loại, đính kèm, nhật ký sự kiện chỉ ghi thêm.
--
--   Đã gửi đề xuất ──Gửi trưởng phòng duyệt──▶ Chờ trưởng phòng duyệt ──Duyệt cấp một──▶ Chờ duyệt cấp hai
--        │  ▲                                    │            │                         │      │      │
--        │  └──────Gửi lại── Trả lại bổ sung ◀───┘ (trả lại)  └──▶ Từ chối ◀─(từ chối)──┘      │      │
--        └──▶ Đã rút ◀──────────────┘                                    Đã duyệt ◀──Duyệt cấp hai┘      │
--                                     Trả lại bổ sung ◀──────────────(trả lại)──────────────────────┘
--
-- Chỉ dùng vai sẵn có: người đề xuất là `requester`, trưởng phòng là `approver` (chỉ hồ sơ phòng mình — ràng
-- buộc actor-in-case-department), duyệt cấp hai là `classifier` (không tự duyệt đề xuất của chính mình —
-- actor-not-requester). "Phòng đề xuất" là trường quyết định `department_code`, người đề xuất chọn ở cạnh Gửi
-- trưởng phòng duyệt (ràng buộc select-department): đó là cột mà phạm vi trưởng phòng đọc. Từ chối và trả lại
-- bắt buộc ghi lý do. Engine không có điều kiện trên cạnh, nên mọi đề xuất qua đủ hai cấp, kể cả khoản nhỏ.
--
-- Hạn từng bước: hai trạng thái chờ duyệt bật `sla_running`, cạnh vào mỗi bước chờ duyệt mang `restarts_sla`
-- — mỗi cấp duyệt có hạn riêng bằng `sla_hours` của loại yêu cầu (nhân hệ số mức ưu tiên nếu có).
--
-- Không gắn mã bộ quy tắc: bộ nhận mã kế tiếp, mọi dòng sau tra bộ theo version. Nên tệp chạy được cả lúc dựng
-- cụm mới (sau 00…05) lẫn trong bản sửa Alembic 0028 trên cụm đã có dữ liệu. Ứng dụng minh họa không hiện quy
-- trình này: các màn của nó chỉ dùng quy trình mang cờ `processes.is_app_default`.

\set ON_ERROR_STOP on


-- ---------------------------------------------------------------------------
-- Bộ quy tắc
-- ---------------------------------------------------------------------------

INSERT INTO rule_sets (id, process_code, version, label, effective_from, is_active, note)
SELECT COALESCE(max(id), 0) + 1, 'purchase-approval', 'purchase-v1',
       'Đề xuất mua sắm — bảy trạng thái, mười hai cạnh',
       TIMESTAMPTZ '2026-11-16 00:00:00+00', TRUE,
       'Quy trình mẫu thứ hai của nền tảng lõi Mức 2 (#376): duyệt hai cấp, chỉ dùng vai sẵn có.'
FROM rule_sets;


-- ---------------------------------------------------------------------------
-- Bảy trạng thái
-- ---------------------------------------------------------------------------

INSERT INTO states (rule_set_id, code, label, description, is_initial, is_terminal, sla_running, display_order)
SELECT b.id, v.code, v.label, v.description, v.is_initial, v.is_terminal, v.sla_running, v.display_order
FROM (SELECT id FROM rule_sets WHERE version = 'purchase-v1') b
CROSS JOIN (VALUES
    ('proposal-submitted',       'Đã gửi đề xuất',
     'Người đề xuất vừa tạo, chưa gửi trưởng phòng — còn sửa được',          TRUE,  FALSE, FALSE, 1),
    ('awaiting-head-approval',   'Chờ trưởng phòng duyệt',
     'Trưởng phòng đề xuất duyệt cấp một, có hạn riêng',                     FALSE, FALSE, TRUE,  2),
    ('awaiting-second-approval', 'Chờ duyệt cấp hai',
     'Điều phối viên duyệt cấp hai, có hạn riêng',                           FALSE, FALSE, TRUE,  3),
    ('returned-for-revision',    'Trả lại bổ sung',
     'Người duyệt trả lại, người đề xuất sửa rồi gửi lại',                   FALSE, FALSE, FALSE, 4),
    ('proposal-approved',        'Đã duyệt',
     'Đề xuất được duyệt đủ hai cấp',                                        FALSE, TRUE,  FALSE, 5),
    ('proposal-declined',        'Từ chối',
     'Một cấp duyệt từ chối, đã ghi lý do',                                  FALSE, TRUE,  FALSE, 6),
    ('proposal-withdrawn',       'Đã rút',
     'Người đề xuất rút đề xuất trước khi duyệt xong',                       FALSE, TRUE,  FALSE, 7)
) AS v (code, label, description, is_initial, is_terminal, sla_running, display_order);


-- ---------------------------------------------------------------------------
-- Mười hai cạnh
-- ---------------------------------------------------------------------------
-- Đứng đầu theo display_order là đường xuôi. Cạnh tự trỏ Sửa nội dung (ADR-0005) giữ trạng thái mà vẫn ghi
-- nhật ký. Trả lại là cạnh làm lại (is_rework).

INSERT INTO transitions
    (rule_set_id, from_state, to_state, activity_code, activity_label, is_system, requires_note, note_label,
     display_order, is_rework, restarts_sla, accepts_attachments, primary_scope)
SELECT b.id, v.*
FROM (SELECT id FROM rule_sets WHERE version = 'purchase-v1') b
CROSS JOIN (VALUES
    ('proposal-submitted',       'awaiting-head-approval',   'submit-proposal',     'Gửi trưởng phòng duyệt',
     FALSE, FALSE, NULL::text,          1, FALSE, TRUE,  TRUE,  'role'::text),
    ('proposal-submitted',       'proposal-submitted',       'edit-content',        'Sửa nội dung',
     FALSE, FALSE, NULL,                2, FALSE, FALSE, TRUE,  NULL),
    ('proposal-submitted',       'proposal-withdrawn',       'withdraw-proposal',   'Rút đề xuất',
     FALSE, FALSE, NULL,                3, FALSE, FALSE, FALSE, NULL),

    ('awaiting-head-approval',   'awaiting-second-approval', 'approve-first-level', 'Duyệt cấp một',
     FALSE, FALSE, NULL,                4, FALSE, TRUE,  FALSE, 'role'),
    ('awaiting-head-approval',   'returned-for-revision',    'return-for-revision', 'Trả lại để bổ sung',
     FALSE, TRUE,  'Cần bổ sung gì',    5, TRUE,  FALSE, FALSE, NULL),
    ('awaiting-head-approval',   'proposal-declined',        'decline-proposal',    'Từ chối đề xuất',
     FALSE, TRUE,  'Lý do từ chối',     6, FALSE, FALSE, FALSE, NULL),

    ('awaiting-second-approval', 'proposal-approved',        'approve-second-level', 'Duyệt cấp hai',
     FALSE, FALSE, NULL,                7, FALSE, FALSE, FALSE, 'role'),
    ('awaiting-second-approval', 'returned-for-revision',    'return-for-revision', 'Trả lại để bổ sung',
     FALSE, TRUE,  'Cần bổ sung gì',    8, TRUE,  FALSE, FALSE, NULL),
    ('awaiting-second-approval', 'proposal-declined',        'decline-proposal',    'Từ chối đề xuất',
     FALSE, TRUE,  'Lý do từ chối',     9, FALSE, FALSE, FALSE, NULL),

    ('returned-for-revision',    'awaiting-head-approval',   'resubmit-proposal',   'Gửi lại',
     FALSE, FALSE, NULL,               10, FALSE, TRUE,  TRUE,  'role'),
    ('returned-for-revision',    'returned-for-revision',    'edit-content',        'Sửa nội dung',
     FALSE, FALSE, NULL,               11, FALSE, FALSE, TRUE,  NULL),
    ('returned-for-revision',    'proposal-withdrawn',       'withdraw-proposal',   'Rút đề xuất',
     FALSE, FALSE, NULL,               12, FALSE, FALSE, FALSE, NULL)
) AS v (from_state, to_state, activity_code, activity_label, is_system, requires_note, note_label,
        display_order, is_rework, restarts_sla, accepts_attachments, primary_scope);


-- ---------------------------------------------------------------------------
-- Ma trận phân quyền — chỉ vai sẵn có
-- ---------------------------------------------------------------------------

INSERT INTO transition_roles (transition_id, role_code)
SELECT t.id, v.role_code
FROM (VALUES
    ('proposal-submitted',       'awaiting-head-approval',   'requester'),
    ('proposal-submitted',       'proposal-submitted',       'requester'),
    ('proposal-submitted',       'proposal-withdrawn',       'requester'),
    ('awaiting-head-approval',   'awaiting-second-approval', 'approver'),
    ('awaiting-head-approval',   'returned-for-revision',    'approver'),
    ('awaiting-head-approval',   'proposal-declined',        'approver'),
    ('awaiting-second-approval', 'proposal-approved',        'classifier'),
    ('awaiting-second-approval', 'returned-for-revision',    'classifier'),
    ('awaiting-second-approval', 'proposal-declined',        'classifier'),
    ('returned-for-revision',    'awaiting-head-approval',   'requester'),
    ('returned-for-revision',    'returned-for-revision',    'requester'),
    ('returned-for-revision',    'proposal-withdrawn',       'requester')
) AS v (from_state, to_state, role_code)
JOIN transitions t
  ON t.rule_set_id = (SELECT id FROM rule_sets WHERE version = 'purchase-v1')
 AND t.from_state  = v.from_state
 AND t.to_state    = v.to_state
 AND NOT t.is_system;


-- ---------------------------------------------------------------------------
-- Ràng buộc Poka-yoke trên cạnh — chỉ ràng buộc sẵn có (01-quy-tac-quy-trinh.sql)
-- ---------------------------------------------------------------------------

INSERT INTO transition_guards (transition_id, guard_code)
SELECT t.id, v.guard_code
FROM (VALUES
    -- Người đề xuất chỉ thao tác trên đề xuất của chính mình
    ('proposal-submitted',       'awaiting-head-approval',   'requester-owns-case'),
    ('proposal-submitted',       'proposal-submitted',       'requester-owns-case'),
    ('proposal-submitted',       'proposal-withdrawn',       'requester-owns-case'),
    ('returned-for-revision',    'awaiting-head-approval',   'requester-owns-case'),
    ('returned-for-revision',    'returned-for-revision',    'requester-owns-case'),
    ('returned-for-revision',    'proposal-withdrawn',       'requester-owns-case'),

    -- Phòng đề xuất chọn lúc gửi trưởng phòng: chính phòng đó duyệt cấp một
    ('proposal-submitted',       'awaiting-head-approval',   'select-department'),

    -- Sửa nội dung và trường riêng khi chưa gửi, hay khi bị trả lại
    ('proposal-submitted',       'proposal-submitted',       'edit-content'),
    ('returned-for-revision',    'returned-for-revision',    'edit-content'),

    -- Trưởng phòng chỉ duyệt đề xuất của phòng mình
    ('awaiting-head-approval',   'awaiting-second-approval', 'actor-in-case-department'),
    ('awaiting-head-approval',   'returned-for-revision',    'actor-in-case-department'),
    ('awaiting-head-approval',   'proposal-declined',        'actor-in-case-department'),

    -- Người duyệt cấp hai không tự duyệt đề xuất do chính mình gửi
    ('awaiting-second-approval', 'proposal-approved',        'actor-not-requester'),
    ('awaiting-second-approval', 'returned-for-revision',    'actor-not-requester'),
    ('awaiting-second-approval', 'proposal-declined',        'actor-not-requester')
) AS v (from_state, to_state, guard_code)
JOIN transitions t
  ON t.rule_set_id = (SELECT id FROM rule_sets WHERE version = 'purchase-v1')
 AND t.from_state  = v.from_state
 AND t.to_state    = v.to_state
 AND NOT t.is_system;


-- ---------------------------------------------------------------------------
-- Loại yêu cầu và trường riêng
-- ---------------------------------------------------------------------------
-- 16 giờ làm việc cho MỖI cấp duyệt (hai ngày làm việc với lịch mẫu). Không mở lại: đề xuất đã kết thúc thì
-- người đề xuất tạo đề xuất mới.

INSERT INTO request_types (code, process_code, label, description, sla_hours, sla_grace_hours, sla_warn_percent,
                           sla_extension_max_percent, sla_extension_max_count, reopen_max_count, display_order)
VALUES
    ('purchase-request', 'purchase-approval', 'Đề xuất mua sắm',
     'Đề xuất mua sắm cần trưởng phòng và điều phối viên duyệt', 16, 4, 75, 50, 0, 0, 10);

INSERT INTO request_type_fields
    (request_type_code, code, label, kind, required, help_text, unit, options, display_order)
VALUES
    ('purchase-request', 'so-tien', 'Số tiền', 'number', TRUE,
     'Tổng số tiền đề xuất, số nguyên dương', 'đồng', NULL, 1),
    ('purchase-request', 'ly-do', 'Lý do', 'text', TRUE,
     'Mua gì, phục vụ việc gì', NULL, NULL, 2);

-- kiem_tra_cau_hinh() đòi mỗi loại đang dùng có một phòng mặc định. Với quy trình này đó chỉ là gợi ý ban đầu
-- cho ô chọn phòng đề xuất. Chọn Hành chính nếu có, không thì phòng đang hoạt động đứng đầu — cụm cũ đã khai
-- lại cơ cấu tổ chức vẫn nhận được tệp này.
INSERT INTO request_type_routing (request_type_code, department_code, is_default)
SELECT 'purchase-request', code, TRUE
FROM departments
WHERE is_active
ORDER BY (code = 'admin-office') DESC, display_order, code
LIMIT 1;
