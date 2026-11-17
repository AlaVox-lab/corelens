-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 AlaVox-lab
--
-- Dữ liệu khởi tạo: điều kiện trên cạnh cho quy trình mua sắm mẫu (#397).
--
-- Trước tệp này mọi đề xuất qua đủ hai cấp duyệt, kể cả khoản nhỏ. Giờ ở "Chờ trưởng phòng duyệt" có hai cạnh
-- duyệt, điều kiện bù nhau trên trường riêng `so-tien`:
--
--   Chờ trưởng phòng duyệt ──Duyệt (dưới ngưỡng)  [so-tien <  5.000.000]──▶ Đã duyệt
--                          ──Duyệt cấp một         [so-tien >= 5.000.000]──▶ Chờ duyệt cấp hai
--
-- Trưởng phòng chỉ thấy MỘT nút duyệt — cạnh không thỏa điều kiện không hiện. Ngưỡng là dữ liệu: đổi bằng
--   UPDATE transition_conditions SET value = '10000000' WHERE field_code = 'so-tien';
-- (cập nhật cả hai dòng để hai điều kiện vẫn bù nhau).
--
-- Không mã nào biết quy trình này hay trường `so-tien`. Chạy sau tệp 06 lúc dựng cụm mới, và trong bản sửa
-- Alembic 0032 trên cụm đã có quy trình mua sắm. Chạy lại không sinh trùng.

\set ON_ERROR_STOP on


-- ---------------------------------------------------------------------------
-- Cạnh mới: trưởng phòng duyệt xong luôn khi dưới ngưỡng
-- ---------------------------------------------------------------------------

INSERT INTO transitions
    (rule_set_id, from_state, to_state, activity_code, activity_label, is_system, requires_note, note_label,
     display_order, is_rework, restarts_sla, accepts_attachments, primary_scope)
SELECT b.id, 'awaiting-head-approval', 'proposal-approved', 'approve-under-threshold', 'Duyệt (dưới ngưỡng)',
       FALSE, FALSE, NULL, 4, FALSE, FALSE, FALSE, 'role'
FROM rule_sets b
WHERE b.version = 'purchase-v1'
  AND NOT EXISTS (
      SELECT 1 FROM transitions t
      WHERE t.rule_set_id = b.id AND t.activity_code = 'approve-under-threshold'
  );

-- Cùng vai và cùng ràng buộc với cạnh "Duyệt cấp một": trưởng phòng của chính phòng đề xuất
INSERT INTO transition_roles (transition_id, role_code)
SELECT t.id, 'approver'
FROM transitions t
JOIN rule_sets b ON b.id = t.rule_set_id AND b.version = 'purchase-v1'
WHERE t.activity_code = 'approve-under-threshold'
ON CONFLICT DO NOTHING;

INSERT INTO transition_guards (transition_id, guard_code)
SELECT t.id, 'actor-in-case-department'
FROM transitions t
JOIN rule_sets b ON b.id = t.rule_set_id AND b.version = 'purchase-v1'
WHERE t.activity_code = 'approve-under-threshold'
ON CONFLICT DO NOTHING;


-- ---------------------------------------------------------------------------
-- Hai điều kiện bù nhau
-- ---------------------------------------------------------------------------

INSERT INTO transition_conditions (transition_id, field_code, operator, value, description)
SELECT t.id, 'so-tien', v.operator, '5000000'::jsonb, v.description
FROM (VALUES
    ('approve-under-threshold', '<',  'Số tiền dưới 5.000.000 đồng — trưởng phòng duyệt là xong'),
    ('approve-first-level',     '>=', 'Số tiền từ 5.000.000 đồng — cần thêm duyệt cấp hai')
) AS v (activity_code, operator, description)
JOIN transitions t ON t.activity_code = v.activity_code
                  AND t.from_state = 'awaiting-head-approval'
JOIN rule_sets b ON b.id = t.rule_set_id AND b.version = 'purchase-v1'
ON CONFLICT (transition_id, field_code, operator) DO NOTHING;
