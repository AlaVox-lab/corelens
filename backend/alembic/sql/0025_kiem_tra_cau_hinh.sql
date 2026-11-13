-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 AlaVox-lab
--
-- Hàm kiểm tra tính nhất quán của cấu hình quy trình — nội dung bản sửa 0025 (#255).
--
-- Thay hàm của bản sửa 0018 (#254, lý do tồn tại của hàm đọc ở tệp đó) bằng CREATE OR REPLACE,
-- giữ nguyên mười phép kiểm cũ và thêm hai phép kiểm cho cơ cấu tổ chức. Từ #255 quản trị viên sửa
-- phòng ban và loại yêu cầu ngay trên màn quản trị cấu hình (app/cau_hinh/quan_tri.py); mỗi lần sửa
-- gọi hàm này trong cùng giao dịch, hỏng thì lần sửa bị từ chối kèm câu lỗi của hàm:
--
--   - 8b: loại yêu cầu đang hoạt động mà phòng ban mặc định đã ngưng — hồ sơ mới sẽ được gợi ý về
--     một phòng không còn trong ô chọn của điều phối viên;
--   - 8c: không còn loại yêu cầu nào đang hoạt động — biểu mẫu Gửi yêu cầu không còn lựa chọn nào.
--
-- Hàm ném lỗi ở phép kiểm đầu tiên không đạt, đạt hết thì trả về bình thường. Thêm phép kiểm mới
-- là một bản sửa mới dùng CREATE OR REPLACE, không sửa tệp này.

CREATE OR REPLACE FUNCTION kiem_tra_cau_hinh() RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    bo         RECORD;
    toi_duoc   TEXT[];
    danh_sach  TEXT;
    so_trang_thai INTEGER;
    so_canh       INTEGER;
BEGIN
    FOR bo IN SELECT id, version FROM rule_sets ORDER BY id LOOP

        -- Phép kiểm tra 1 — ngõ cụt
        -- Trạng thái không phải kết thúc thì bắt buộc phải có đường đi tiếp.
        SELECT string_agg(s.code, ', ' ORDER BY s.code) INTO danh_sach
        FROM states s
        WHERE s.rule_set_id = bo.id
          AND NOT s.is_terminal
          AND NOT EXISTS (
              SELECT 1 FROM transitions t
              WHERE t.rule_set_id = bo.id AND t.from_state = s.code
          );

        IF danh_sach IS NOT NULL THEN
            RAISE EXCEPTION
                'Bộ quy tắc %: trạng thái không phải kết thúc nhưng không có cạnh nào đi ra — hồ sơ vào đây sẽ mắc kẹt: %',
                bo.version, danh_sach;
        END IF;

        -- Phép kiểm tra 2 — trạng thái không tới được
        -- Đi từ điểm vào theo mọi cạnh, thu thập những trạng thái chạm tới được.
        WITH RECURSIVE lan_toa AS (
            SELECT s0.code
            FROM states s0
            WHERE s0.rule_set_id = bo.id AND s0.is_initial

            UNION

            SELECT t.to_state
            FROM transitions t
            JOIN lan_toa r ON t.from_state = r.code
            WHERE t.rule_set_id = bo.id
        )
        SELECT array_agg(code) INTO toi_duoc FROM lan_toa;

        SELECT string_agg(s.code, ', ' ORDER BY s.code) INTO danh_sach
        FROM states s
        WHERE s.rule_set_id = bo.id
          AND NOT (s.code = ANY (COALESCE(toi_duoc, ARRAY[]::TEXT[])));

        IF danh_sach IS NOT NULL THEN
            RAISE EXCEPTION
                'Bộ quy tắc %: trạng thái không tới được từ điểm vào — khai báo thừa hoặc thiếu cạnh: %',
                bo.version, danh_sach;
        END IF;

        -- Phép kiểm tra 3 — cạnh chết
        -- Cạnh phải hoặc có ít nhất một vai trò đi được, hoặc là cạnh hệ thống.
        SELECT string_agg(t.from_state || ' → ' || t.to_state, ', ' ORDER BY t.display_order)
        INTO danh_sach
        FROM transitions t
        WHERE t.rule_set_id = bo.id
          AND NOT t.is_system
          AND NOT EXISTS (
              SELECT 1 FROM transition_roles tr WHERE tr.transition_id = t.id
          );

        IF danh_sach IS NOT NULL THEN
            RAISE EXCEPTION
                'Bộ quy tắc %: cạnh không vai trò nào đi được và cũng không đánh dấu là cạnh hệ thống: %',
                bo.version, danh_sach;
        END IF;

        -- Phép kiểm tra 4 — đồng hồ SLA không bao giờ chạy
        -- Không trạng thái nào bật `sla_running` thì không hồ sơ nào quá hạn được,
        -- và cơ chế tự leo thang trở thành mã chết mà không ai biết.
        IF NOT EXISTS (
            SELECT 1 FROM states s WHERE s.rule_set_id = bo.id AND s.sla_running
        ) THEN
            RAISE EXCEPTION
                'Bộ quy tắc %: không trạng thái nào bật sla_running — đồng hồ SLA sẽ không bao giờ chạy và cơ chế leo thang thành vô hiệu',
                bo.version;
        END IF;

        -- Phép kiểm tra 5 — trạng thái kết thúc mà vẫn chạy đồng hồ
        -- Mâu thuẫn: hồ sơ đã đóng thì không còn gì để trễ, và đồng hồ sẽ chạy mãi.
        SELECT string_agg(s.code, ', ' ORDER BY s.code) INTO danh_sach
        FROM states s
        WHERE s.rule_set_id = bo.id AND s.is_terminal AND s.sla_running;

        IF danh_sach IS NOT NULL THEN
            RAISE EXCEPTION
                'Bộ quy tắc %: trạng thái kết thúc nhưng vẫn bật sla_running: %',
                bo.version, danh_sach;
        END IF;

        -- Phép kiểm tra 6 — hỏi ở đâu thì phải có đường quay về đó (#79)
        -- Trạng thái chờ nào có cạnh ra mang `return-to-previous-state` thì hồ sơ chỉ
        -- rời được bằng cạnh về đúng chỗ đã vào. Một cạnh DẪN VÀO trạng thái đó mà
        -- thiếu cạnh quay về tương ứng thì hồ sơ vào bằng đường ấy sẽ mắc kẹt — chỉ
        -- còn hủy được. Ví dụ: thêm cạnh "hỏi thêm" ở Đã leo thang mà quên cạnh về.
        SELECT string_agg(vao.from_state || ' → ' || vao.to_state, ', ' ORDER BY vao.display_order)
        INTO danh_sach
        FROM transitions vao
        WHERE vao.rule_set_id = bo.id
          -- Cạnh tự trỏ không đưa hồ sơ VÀO trạng thái nào, nên không cần đường về.
          -- Cạnh tự trỏ ở trạng thái chờ là việc của phép kiểm tra 7.
          AND vao.from_state <> vao.to_state
          AND EXISTS (
              SELECT 1
              FROM transitions ra
              JOIN transition_guards g ON g.transition_id = ra.id
              WHERE ra.rule_set_id = bo.id
                AND ra.from_state = vao.to_state
                AND g.guard_code = 'return-to-previous-state'
          )
          AND NOT EXISTS (
              SELECT 1
              FROM transitions ve
              JOIN transition_guards g ON g.transition_id = ve.id
              WHERE ve.rule_set_id = bo.id
                AND ve.from_state = vao.to_state
                AND ve.to_state = vao.from_state
                AND g.guard_code = 'return-to-previous-state'
          );

        IF danh_sach IS NOT NULL THEN
            RAISE EXCEPTION
                'Bộ quy tắc %: cạnh dẫn vào trạng thái chờ nhưng không có cạnh quay về đúng chỗ — hồ sơ vào bằng đường này sẽ mắc kẹt: %',
                bo.version, danh_sach;
        END IF;

        -- Phép kiểm tra 7 — không có cạnh tự trỏ ở trạng thái chờ (#127)
        -- Cạnh tự trỏ (ADR-0005) ghi một dòng nhật ký mà không đổi trạng thái. Engine bỏ
        -- qua dòng đó khi tìm "chỗ cũ", nhưng một thao tác đổi hồ sơ trong lúc hồ sơ
        -- đang chờ người khác trả lời là dấu hiệu bộ quy tắc khai sai chỗ — chặn từ đầu.
        SELECT string_agg(t.from_state || ' → ' || t.to_state, ', ' ORDER BY t.display_order)
        INTO danh_sach
        FROM transitions t
        WHERE t.rule_set_id = bo.id
          AND t.from_state = t.to_state
          AND EXISTS (
              SELECT 1
              FROM transitions ra
              JOIN transition_guards g ON g.transition_id = ra.id
              WHERE ra.rule_set_id = bo.id
                AND ra.from_state = t.from_state
                AND g.guard_code = 'return-to-previous-state'
          );

        IF danh_sach IS NOT NULL THEN
            RAISE EXCEPTION
                'Bộ quy tắc %: cạnh tự trỏ ở trạng thái chờ — thao tác này phải đặt ở trạng thái khác: %',
                bo.version, danh_sach;
        END IF;

        SELECT count(*) INTO so_trang_thai FROM states      WHERE rule_set_id = bo.id;
        SELECT count(*) INTO so_canh       FROM transitions WHERE rule_set_id = bo.id;

        RAISE NOTICE 'Bộ quy tắc % hợp lệ: % trạng thái, % cạnh chuyển',
            bo.version, so_trang_thai, so_canh;

    END LOOP;

    -- Phép kiểm tra 8 — loại yêu cầu không có phòng ban mặc định
    -- Ràng buộc duy nhất từng phần đã bảo đảm KHÔNG QUÁ một phòng mặc định.
    -- Còn thiếu hẳn thì phải bắt ở đây, nếu không người phân loại mở hồ sơ ra
    -- sẽ không thấy gợi ý nào.
    SELECT string_agg(rt.code, ', ' ORDER BY rt.code) INTO danh_sach
    FROM request_types rt
    WHERE rt.is_active
      AND NOT EXISTS (
          SELECT 1 FROM request_type_routing r
          WHERE r.request_type_code = rt.code AND r.is_default
      );

    IF danh_sach IS NOT NULL THEN
        RAISE EXCEPTION
            'Loại yêu cầu đang hoạt động nhưng chưa khai phòng ban mặc định: %',
            danh_sach;
    END IF;

    -- Phép kiểm tra 8b — phòng ban mặc định của loại yêu cầu đang hoạt động đã ngưng (#255)
    SELECT string_agg(rt.code || ' → ' || d.code, ', ' ORDER BY rt.code) INTO danh_sach
    FROM request_types rt
    JOIN request_type_routing r ON r.request_type_code = rt.code AND r.is_default
    JOIN departments d ON d.code = r.department_code
    WHERE rt.is_active AND NOT d.is_active;

    IF danh_sach IS NOT NULL THEN
        RAISE EXCEPTION
            'Loại yêu cầu đang hoạt động có phòng ban mặc định đã ngưng: %', danh_sach;
    END IF;

    -- Phép kiểm tra 8c — không còn loại yêu cầu nào đang hoạt động (#255)
    IF NOT EXISTS (SELECT 1 FROM request_types WHERE is_active) THEN
        RAISE EXCEPTION 'Phải còn ít nhất một loại yêu cầu đang hoạt động';
    END IF;

    RAISE NOTICE 'Cơ cấu tổ chức hợp lệ: mọi loại yêu cầu đều có phòng ban mặc định đang hoạt động';

    -- Phép kiểm tra 9 — loại lời nhắn không vai trò nào gửi được (#128)
    -- Cùng lý do với phép kiểm tra 3: một loại không ai gửi được là cấu hình chết,
    -- không bao giờ hiện nút nào, và không ai biết vì sao.
    SELECT string_agg(k.code, ', ' ORDER BY k.code) INTO danh_sach
    FROM message_kinds k
    WHERE NOT EXISTS (SELECT 1 FROM message_kind_roles r WHERE r.kind_code = k.code);

    IF danh_sach IS NOT NULL THEN
        RAISE EXCEPTION
            'Loại lời nhắn không vai trò nào gửi được: %', danh_sach;
    END IF;

    RAISE NOTICE 'Loại lời nhắn hợp lệ: mọi loại đều có vai trò gửi được';

    -- Phép kiểm tra 10 — lịch làm việc (#199)
    -- Mọi đồng hồ đo bằng giờ làm việc của lịch mặc định. Thiếu lịch, hay lịch không có
    -- giờ làm nào, thì đồng hồ SLA đứng yên mãi và không hồ sơ nào bao giờ quá hạn — lỗi
    -- im lặng, nên phải chặn lúc nạp.
    IF (SELECT count(*) FROM work_calendars WHERE is_default) <> 1 THEN
        RAISE EXCEPTION 'Phải có đúng một lịch làm việc mặc định (work_calendars.is_default)';
    END IF;

    SELECT string_agg(c.code || ' (' || c.time_zone || ')', ', ' ORDER BY c.code) INTO danh_sach
    FROM work_calendars c
    WHERE NOT EXISTS (SELECT 1 FROM pg_timezone_names z WHERE z.name = c.time_zone);

    IF danh_sach IS NOT NULL THEN
        RAISE EXCEPTION 'Lịch làm việc mang tên múi giờ không tồn tại: %', danh_sach;
    END IF;

    SELECT string_agg(c.code, ', ' ORDER BY c.code) INTO danh_sach
    FROM work_calendars c
    WHERE NOT EXISTS (SELECT 1 FROM work_hours w WHERE w.calendar_code = c.code);

    IF danh_sach IS NOT NULL THEN
        RAISE EXCEPTION 'Lịch làm việc không có khung giờ làm nào: %', danh_sach;
    END IF;

    -- Hai khung chồng nhau trong cùng một ngày thì phần chồng bị đếm hai lần
    SELECT string_agg(a.calendar_code || ' thứ ' || a.iso_weekday || ' '
                      || a.start_time || '–' || a.end_time || ' chồng ' || b.start_time || '–' || b.end_time,
                      ', ') INTO danh_sach
    FROM work_hours a
    JOIN work_hours b
      ON b.calendar_code = a.calendar_code
     AND b.iso_weekday = a.iso_weekday
     AND b.start_time > a.start_time
     AND b.start_time < a.end_time;

    IF danh_sach IS NOT NULL THEN
        RAISE EXCEPTION 'Khung giờ làm chồng nhau: %', danh_sach;
    END IF;

    RAISE NOTICE 'Lịch làm việc hợp lệ: một lịch mặc định, có giờ làm, không khung nào chồng nhau';
END $$;

COMMENT ON FUNCTION kiem_tra_cau_hinh() IS
    'Kiểm tính nhất quán mức đồ thị của mọi bộ quy tắc, cơ cấu tổ chức, loại lời nhắn và lịch làm việc. Ném lỗi ở phép kiểm đầu tiên không đạt (#254, #255).';
