-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 AlaVox-lab
--
-- Kiểm tra tính nhất quán của bộ quy tắc sau khi nạp dữ liệu khởi tạo.
--
-- Vì sao cần tệp này: khóa ngoại và ràng buộc duy nhất bắt được lỗi ở mức từng
-- dòng, nhưng không bắt được lỗi ở mức ĐỒ THỊ. Một quản trị viên tùy biến sản
-- phẩm cho doanh nghiệp của họ có thể tạo ra bộ quy tắc mà mọi dòng đều hợp lệ
-- nhưng cả luồng thì hỏng — có trạng thái không ai tới được, có ngõ cụt không
-- phải trạng thái đóng, có cạnh không vai trò nào đi được.
--
-- Những lỗi đó nếu không chặn ở đây thì chỉ lộ ra khi một hồ sơ thật mắc kẹt
-- giữa chừng. Tệp này làm cụm Docker DỪNG KHỞI ĐỘNG thay vì chạy với luồng hỏng.
--
-- Tệp đánh số 99 để luôn chạy sau cùng. Engine ở #41 sẽ gọi lại đúng ba phép
-- kiểm tra này mỗi khi quản trị viên sửa bộ quy tắc lúc hệ thống đang chạy.

\set ON_ERROR_STOP on

DO $$
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

        SELECT count(*) INTO so_trang_thai FROM states      WHERE rule_set_id = bo.id;
        SELECT count(*) INTO so_canh       FROM transitions WHERE rule_set_id = bo.id;

        RAISE NOTICE 'Bộ quy tắc % hợp lệ: % trạng thái, % cạnh chuyển',
            bo.version, so_trang_thai, so_canh;

    END LOOP;

    -- Phép kiểm tra 4 — loại yêu cầu không có phòng ban mặc định
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

    RAISE NOTICE 'Cơ cấu tổ chức hợp lệ: mọi loại yêu cầu đều có phòng ban mặc định';
END $$;
