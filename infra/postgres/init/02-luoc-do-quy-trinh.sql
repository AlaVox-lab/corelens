-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 AlaVox-lab
--
-- Lược đồ cấu hình cho engine máy trạng thái của không gian P.
--
-- Tệp này chỉ định nghĩa CẤU TRÚC. Toàn bộ nội dung nghiệp vụ — trạng thái nào,
-- cạnh nào, phòng ban nào — nằm trong infra/seed/, vì đó là phần doanh nghiệp
-- khác sẽ sửa khi tùy biến sản phẩm theo đặc thù của họ. Xem ADR-0004 và
-- docs/process-flow.md.
--
-- Nguyên tắc chi phối mọi bảng dưới đây: KHÔNG có dòng nghĩa là KHÔNG đi được.
-- Ràng buộc Poka-yoke được diễn đạt bằng việc thiếu vắng dữ liệu và bằng khóa
-- ngoại, chứ không bằng câu lệnh if trong mã nguồn.
--
-- PostgreSQL chạy tệp này đúng một lần, lúc khởi tạo thực thể, trên database
-- nghiệp vụ (biến POSTGRES_DB). Xóa volume thì nó chạy lại.

\set ON_ERROR_STOP on


-- ===========================================================================
-- 1. PHIÊN BẢN BỘ QUY TẮC
-- ===========================================================================
-- Hồ sơ cũ phải chạy theo quy tắc có hiệu lực lúc nó được tạo. Nếu quản trị
-- viên sửa luồng giữa chừng mà không có cột này, hồ sơ đang dở sẽ đột ngột đổi
-- luật giữa đường — và nhật ký sự kiện mất ý nghĩa để khai phá quy trình.
--
-- Cách dùng: mỗi hồ sơ ghi lại rule_set_id lúc tạo và giữ nguyên tới khi đóng.

CREATE TABLE rule_sets (
    id              SMALLINT     PRIMARY KEY,
    version         TEXT         NOT NULL UNIQUE,
    label           TEXT         NOT NULL,
    effective_from  TIMESTAMPTZ  NOT NULL,
    is_active       BOOLEAN      NOT NULL DEFAULT FALSE,
    note            TEXT
);

COMMENT ON TABLE  rule_sets IS 'Phiên bản bộ quy tắc quy trình. Hồ sơ cũ chạy theo quy tắc cũ.';
COMMENT ON COLUMN rule_sets.effective_from IS 'Luôn lưu theo UTC, như mọi mốc thời gian trong hệ thống.';

-- Đúng một bộ quy tắc được kích hoạt tại một thời điểm. Hồ sơ mới luôn nhận
-- bộ này. Ràng buộc đặt ở tầng dữ liệu để không phụ thuộc kỷ luật của mã gọi.
CREATE UNIQUE INDEX rule_sets_chi_mot_bo_kich_hoat
    ON rule_sets (is_active) WHERE is_active;


-- ===========================================================================
-- 2. VAI TRÒ
-- ===========================================================================
-- Mã vai trò phải TRÙNG KHỚP tên vai trò trong realm Keycloak
-- (infra/keycloak/realm-dx-os-lab.json). Keycloak là nguồn sự thật về việc ai
-- mang vai trò nào; bảng này là nguồn sự thật về vai trò nào đi được cạnh nào.
-- Lệch tên giữa hai nơi sẽ khiến người dùng đăng nhập được nhưng không thao
-- tác được gì — xem #43.

CREATE TABLE roles (
    code           TEXT      PRIMARY KEY,
    label          TEXT      NOT NULL,
    description    TEXT,
    display_order  SMALLINT  NOT NULL DEFAULT 0
);

COMMENT ON TABLE roles IS 'Năm vai trò nghiệp vụ. Mã phải trùng tên vai trò realm trong Keycloak.';


-- ===========================================================================
-- 3. TRẠNG THÁI
-- ===========================================================================
-- Cột code là giá trị thật đi vào hai trường from_state và to_state của nhật ký
-- sự kiện. Viết tiếng Anh vì mã nguồn so sánh với chúng; cột label là chuỗi
-- hiển thị tiếng Việt. Quy ước ở ARCHITECTURE.md mục 8.3.

CREATE TABLE states (
    rule_set_id    SMALLINT  NOT NULL REFERENCES rule_sets (id) ON DELETE CASCADE,
    code           TEXT      NOT NULL,
    label          TEXT      NOT NULL,
    description    TEXT,
    is_initial     BOOLEAN   NOT NULL DEFAULT FALSE,
    is_terminal    BOOLEAN   NOT NULL DEFAULT FALSE,
    sla_running    BOOLEAN   NOT NULL DEFAULT FALSE,
    display_order  SMALLINT  NOT NULL DEFAULT 0,

    PRIMARY KEY (rule_set_id, code),

    -- Khóa phụ này tồn tại để bảng transitions tham chiếu tới, xem mục 4
    UNIQUE (rule_set_id, code, is_terminal),

    -- Trạng thái kết thúc thì không thể đồng thời là trạng thái bắt đầu
    CONSTRAINT states_bat_dau_khong_the_ket_thuc
        CHECK (NOT (is_initial AND is_terminal))
);

COMMENT ON COLUMN states.is_initial IS
    'Điểm vào của luồng. Có cột này thì mã nguồn không phải viết if state = ''submitted''.';
COMMENT ON COLUMN states.is_terminal IS
    'Trạng thái kết thúc chu kỳ hồ sơ. Cạnh rời khỏi đây chỉ được là cạnh MỞ LẠI có cửa sổ thời gian (transitions.reopen_window_hours, #102) — ràng buộc ở bảng transitions.';
COMMENT ON COLUMN states.sla_running IS
    'Đồng hồ SLA có chạy khi hồ sơ nằm ở trạng thái này không. Một cột này trả lời cả hai câu: đồng hồ bắt đầu từ đâu, và dừng ở đâu. Nhờ nó mà mã nguồn không phải viết if state = ''in-progress''.';

-- Đúng một trạng thái bắt đầu cho mỗi bộ quy tắc. Nếu không có ràng buộc này,
-- quản trị viên tùy biến sai sẽ tạo ra luồng có hai điểm vào hoặc không có
-- điểm vào nào, và lỗi chỉ lộ ra lúc chạy.
CREATE UNIQUE INDEX states_chi_mot_trang_thai_bat_dau
    ON states (rule_set_id) WHERE is_initial;


-- ===========================================================================
-- 4. CẠNH CHUYỂN TRẠNG THÁI
-- ===========================================================================
-- Mỗi dòng là một cạnh hợp lệ. Không có dòng nghĩa là không đi được.
--
-- Đây là chỗ ràng buộc Poka-yoke "đã nhận là không trả về" được thực thi: đơn
-- giản là không tồn tại dòng nào đi từ in-progress ngược về awaiting-acceptance
-- hay classified. Không phải "không nên đi", mà là "không có đường mà đi".

CREATE TABLE transitions (
    id              INTEGER   GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rule_set_id     SMALLINT  NOT NULL REFERENCES rule_sets (id) ON DELETE CASCADE,
    from_state      TEXT      NOT NULL,
    to_state        TEXT      NOT NULL,
    activity_code   TEXT      NOT NULL,
    activity_label  TEXT      NOT NULL,
    is_system       BOOLEAN   NOT NULL DEFAULT FALSE,
    requires_note   BOOLEAN   NOT NULL DEFAULT FALSE,
    note_label      TEXT,
    display_order   SMALLINT  NOT NULL DEFAULT 0,

    -- Cạnh làm lại (#153): đi qua nó là hồ sơ bị đẩy ngược để làm lại — từ chối vì sai
    -- chuyên môn, mở lại vì chưa đạt. Số lần quay lui trên dòng thời gian đếm số lần đi qua
    -- cạnh mang cờ này, không đếm mọi lần vào lại một trạng thái cũ: hỏi đáp bổ sung
    -- thông tin hay phân công lại sau leo thang là đi vòng rồi về, không phải làm lại.
    is_rework       BOOLEAN   NOT NULL DEFAULT FALSE,

    -- Trạng thái nguồn có phải trạng thái kết thúc không. Khóa ngoại ngay dưới buộc cột này
    -- khớp với `states.is_terminal` của trạng thái nguồn. Từ #102 cạnh rời khỏi trạng thái kết
    -- thúc được phép, nhưng chỉ cạnh mở lại có cửa sổ thời gian — xem CHECK bên dưới. Dữ liệu
    -- khởi tạo chỉ nhắc tới cột này ở cạnh mở lại sau khi đóng.
    from_is_terminal BOOLEAN  NOT NULL DEFAULT FALSE,

    -- Cạnh mở lại sau khi hồ sơ đã kết thúc (#102, giảng viên chốt 08/10): đi được khi hồ sơ
    -- nằm ở trạng thái kết thúc chưa quá chừng này GIỜ LÀM VIỆC kể từ lúc vào đó (7 ngày làm
    -- việc = 56 giờ với lịch mẫu 8 giờ một ngày). NULL là cạnh bình thường. Quá cửa sổ thì
    -- cạnh không hiện nữa — hồ sơ kết thúc hẳn, người gửi tạo hồ sơ mới.
    reopen_window_hours SMALLINT,

    -- Đi qua cạnh này là mở chu kỳ xử lý mới (#102): đồng hồ SLA đếm lại từ 0, không kế thừa
    -- hạn đã hết của chu kỳ cũ. Bật cho hai cạnh mở lại. Thời gian dừng (chờ bổ sung) vẫn giữ.
    restarts_sla      BOOLEAN   NOT NULL DEFAULT FALSE,

    -- Người đang đứng ở cạnh này đính kèm được tệp vào hồ sơ (#80): cạnh Sửa nội dung và Bổ sung
    -- thông tin, tức những lúc người gửi còn chuyện để nói với người nhận. Hồ sơ tới phòng ban
    -- thì không còn cạnh nào mang cờ này và việc đính kèm khóa lại, như cách Sửa nội dung khóa.
    accepts_attachments BOOLEAN NOT NULL DEFAULT FALSE,

    -- Cạnh hệ thống tự đi khi hồ sơ nằm ở trạng thái nguồn đủ chừng này GIỜ LÀM VIỆC
    -- (#142): hồ sơ nằm im vì người phải bấm không bấm thì hệ thống đi thay, có ghi nhật
    -- ký. NULL là cạnh không tự đi theo thời gian chờ — cạnh leo thang do bộ quét SLA đi.
    auto_after_hours  SMALLINT,
    -- Báo trước trên màn hình khi còn chừng này giờ làm việc tới lúc tự đi. NULL là
    -- không báo trước.
    warn_before_hours SMALLINT,

    -- Bước chính của quy trình ở trạng thái nguồn (#227): hồ sơ đang ở đây là đang chờ người
    -- đi được cạnh này. Cờ `needs_my_action` trên danh sách hồ sơ suy từ cột này, không từ
    -- "bấm được gì" — người gửi sửa hay hủy được ở Đã gửi nhưng hồ sơ không chờ họ.
    --   NULL       không phải bước chính (sửa, hủy, gia hạn, hỏi thêm, nhận việc…)
    --   'role'     chờ mọi người có vai đi được cạnh
    --   'assignee' chờ người đang được giao hồ sơ; hồ sơ chưa giao ai thì như 'role'
    primary_scope TEXT,

    CONSTRAINT transitions_buoc_chinh_hop_le
        CHECK (primary_scope IS NULL
               OR (primary_scope IN ('role', 'assignee') AND NOT is_system)),

    -- Rời khỏi trạng thái kết thúc chỉ được bằng cạnh mở lại có cửa sổ thời gian của người
    CONSTRAINT transitions_roi_ket_thuc_phai_co_cua_so
        CHECK (from_is_terminal = FALSE OR reopen_window_hours IS NOT NULL),
    CONSTRAINT transitions_cua_so_mo_lai_hop_le
        CHECK (reopen_window_hours IS NULL
               OR (from_is_terminal AND NOT is_system AND reopen_window_hours > 0)),

    CONSTRAINT transitions_tu_di_chi_canh_he_thong
        CHECK (auto_after_hours IS NULL OR (is_system AND auto_after_hours > 0)),
    CONSTRAINT transitions_bao_truoc_hop_le
        CHECK (warn_before_hours IS NULL
               OR (auto_after_hours IS NOT NULL
                   AND warn_before_hours > 0 AND warn_before_hours < auto_after_hours)),

    FOREIGN KEY (rule_set_id, from_state, from_is_terminal)
        REFERENCES states (rule_set_id, code, is_terminal),

    FOREIGN KEY (rule_set_id, to_state)
        REFERENCES states (rule_set_id, code),

    -- Giữa hai trạng thái chỉ có tối đa một cạnh của NGƯỜI và một cạnh của HỆ THỐNG theo
    -- mỗi chiều, và mỗi trạng thái tối đa một cạnh tự trỏ mỗi loại. Hai loại tác nhân
    -- không bao giờ đi được cạnh của nhau, nên engine nhận diện một cạnh bằng cặp (trạng
    -- thái nguồn, trạng thái đích) cộng loại tác nhân; API và giao diện chỉ thấy cạnh của
    -- người nên vẫn nhận diện bằng cặp. Thêm `is_system` từ #142: "Chờ phòng ban xác duyệt
    -- → Đã phân loại" có cả cạnh điều phối viên rút hồ sơ lẫn cạnh hệ thống tự trả về.
    UNIQUE (rule_set_id, from_state, to_state, is_system)

    -- Cạnh tự trỏ (from_state = to_state) ĐƯỢC PHÉP từ ADR-0005: thao tác đổi hồ sơ mà
    -- không đổi trạng thái — nhận việc về mình, sửa nội dung — vẫn phải đi qua cửa
    -- chuyển trạng thái để có dòng nhật ký. Tệp 99 cấm cạnh tự trỏ ở trạng thái chờ.
);

COMMENT ON COLUMN transitions.activity_code IS
    'Tên hoạt động đi vào trường activity của nhật ký sự kiện. Nhiều cạnh được phép dùng chung một mã khi chúng là cùng một hành vi nghiệp vụ — ví dụ hủy yêu cầu từ bốn trạng thái khác nhau.';
COMMENT ON COLUMN transitions.is_system IS
    'TRUE nghĩa là hệ thống tự đi, không vai trò người nào đi được. Hiện chỉ dùng cho cạnh leo thang khi quá hạn SLA.';
COMMENT ON COLUMN transitions.reopen_window_hours IS
    'Cạnh mở lại sau khi hồ sơ kết thúc (#102): đi được khi hồ sơ mới vào trạng thái kết thúc chưa quá chừng này giờ làm việc. NULL là cạnh thường.';
COMMENT ON COLUMN transitions.accepts_attachments IS
    'Người có cạnh này đính kèm được tệp vào hồ sơ (#80). Cờ nằm ở cạnh chứ không ở trạng thái, vì quyền đính kèm đi theo vai và việc người đó đang làm — người gửi ở Chờ bổ sung thông tin đính kèm được, nhân viên phòng ban ở Đang xử lý thì không.';
COMMENT ON COLUMN transitions.restarts_sla IS
    'Đi qua cạnh này là mở chu kỳ xử lý mới (#102): đồng hồ SLA đếm lại từ 0.';
COMMENT ON COLUMN transitions.requires_note IS
    'TRUE thì bắt buộc nhập lý do. Ví dụ: từ chối vì sai chuyên môn, đóng hồ sơ khi không phòng nào nhận, mở lại vì chưa đạt.';
COMMENT ON COLUMN transitions.note_label IS
    'Tên ô ghi chú của cạnh này trên giao diện. NULL thì gọi là lý do. Đặt khi ghi chú không phải lời giải thích mà là nội dung chính — ví dụ câu hỏi khi yêu cầu bổ sung, câu trả lời khi bổ sung thông tin.';

-- Mỗi trạng thái tối đa một cạnh tự đi theo thời gian chờ: hai đồng hồ chờ trên cùng một
-- trạng thái thì không biết cái nào thắng.
CREATE UNIQUE INDEX transitions_mot_canh_tu_di
    ON transitions (rule_set_id, from_state) WHERE auto_after_hours IS NOT NULL;

CREATE INDEX transitions_tra_theo_trang_thai_nguon
    ON transitions (rule_set_id, from_state);


-- ===========================================================================
-- 5. MA TRẬN PHÂN QUYỀN — VAI TRÒ NÀO ĐI ĐƯỢC CẠNH NÀO
-- ===========================================================================
-- Quan hệ nhiều-nhiều chứ không phải một cột trên transitions. Lý do: doanh
-- nghiệp tùy biến có thể muốn hai vai trò cùng đi được một cạnh, và với cột đơn
-- thì họ buộc phải nhân đôi dòng cạnh — làm hỏng ràng buộc duy nhất ở mục 4.
--
-- Cạnh không có dòng nào ở đây và cũng không đánh dấu is_system là cạnh chết.
-- Kiểm tra điều đó ở cuối tệp dữ liệu khởi tạo.

CREATE TABLE transition_roles (
    transition_id  INTEGER  NOT NULL REFERENCES transitions (id) ON DELETE CASCADE,
    role_code      TEXT     NOT NULL REFERENCES roles (code)     ON DELETE RESTRICT,

    PRIMARY KEY (transition_id, role_code)
);

COMMENT ON TABLE transition_roles IS 'Ma trận phân quyền theo cạnh. Không có dòng nghĩa là vai trò đó không đi được cạnh đó.';


-- ===========================================================================
-- 6. RÀNG BUỘC POKA-YOKE THEO TỪNG CẠNH
-- ===========================================================================
-- Bốn ràng buộc ở docs/process-flow.md mục 5 chia làm hai nhóm:
--
--   Nhóm cấu trúc — thực thi bằng sự VẮNG MẶT của cạnh, không cần dòng nào ở
--   đây: "đã nhận là không trả về" và "chỉ hủy trước khi vào xử lý".
--
--   Nhóm kiểm tra lúc chạy — cần đối chiếu người thao tác với hồ sơ, nên phải
--   khai báo thành dòng: các mã dưới đây.
--
-- Mã guard là hợp đồng giữa dữ liệu và mã nguồn: engine ở #41 tra bảng này rồi
-- gọi hàm kiểm tra tương ứng. Thêm ràng buộc mới cho một cạnh có sẵn chỉ là
-- thêm một dòng; thêm LOẠI ràng buộc mới thì cần viết hàm kiểm tra mới.

CREATE TABLE guards (
    code         TEXT  PRIMARY KEY,
    label        TEXT  NOT NULL,
    description  TEXT  NOT NULL
);

CREATE TABLE transition_guards (
    transition_id  INTEGER  NOT NULL REFERENCES transitions (id) ON DELETE CASCADE,
    guard_code     TEXT     NOT NULL REFERENCES guards (code)    ON DELETE RESTRICT,

    PRIMARY KEY (transition_id, guard_code)
);


-- ===========================================================================
-- 7. CƠ CẤU TỔ CHỨC — PHẦN DOANH NGHIỆP KHÁC SỬA NHIỀU NHẤT
-- ===========================================================================
-- Ba bảng dưới đây là lý do tồn tại của vai trò administrator. Mục tiêu sản
-- phẩm: doanh nghiệp tải về rồi tự khai phòng ban và loại yêu cầu của mình mà
-- không đụng một dòng mã nào. Xem ARCHITECTURE.md mục 5.1.

CREATE TABLE departments (
    code           TEXT      PRIMARY KEY,
    label          TEXT      NOT NULL,
    description    TEXT,
    is_active      BOOLEAN   NOT NULL DEFAULT TRUE,
    display_order  SMALLINT  NOT NULL DEFAULT 0
);

CREATE TABLE request_types (
    code           TEXT      PRIMARY KEY,
    label          TEXT      NOT NULL,
    description    TEXT,
    sla_hours      INTEGER   NOT NULL,
    sla_grace_hours INTEGER  NOT NULL DEFAULT 0,
    sla_warn_percent SMALLINT NOT NULL DEFAULT 75,
    sla_extension_max_percent SMALLINT NOT NULL DEFAULT 50,
    sla_extension_max_count   SMALLINT NOT NULL DEFAULT 2,
    reopen_max_count          SMALLINT NOT NULL DEFAULT 2,
    is_active      BOOLEAN   NOT NULL DEFAULT TRUE,
    display_order  SMALLINT  NOT NULL DEFAULT 0,

    CONSTRAINT request_types_sla_duong
        CHECK (sla_hours > 0),
    -- Ân hạn dài hơn chính hạn xử lý thì lần leo thang ĐẦU TIÊN cũng bị hoãn — sai
    CONSTRAINT request_types_an_han_hop_le
        CHECK (sla_grace_hours >= 0 AND sla_grace_hours <= sla_hours),
    -- 0 thì mọi hồ sơ vừa nhận việc đã "sắp hết hạn"; 100 thì mức vàng không bao giờ hiện
    CONSTRAINT request_types_nguong_sap_het_hop_le
        CHECK (sla_warn_percent > 0 AND sla_warn_percent < 100),
    CONSTRAINT request_types_gia_han_hop_le
        CHECK (sla_extension_max_percent > 0 AND sla_extension_max_count >= 0),
    CONSTRAINT request_types_mo_lai_hop_le
        CHECK (reopen_max_count >= 0)
);

-- Trường thông tin riêng của từng loại yêu cầu (#250): mã tài sản cho sự cố thiết bị, số tiền
-- cho đề xuất mua vật tư... Biểu mẫu gửi, phép kiểm ở dịch vụ và trang hồ sơ đều dựng từ bảng
-- này; thêm một trường là thêm một dòng, không sửa mã. Giá trị lưu ở requests.details (JSONB,
-- khóa là `code` dưới đây).
CREATE TABLE request_type_fields (
    request_type_code TEXT     NOT NULL REFERENCES request_types (code) ON DELETE CASCADE,
    code              TEXT     NOT NULL,
    label             TEXT     NOT NULL,
    -- text: chữ một dòng; number: số không âm; date: ngày YYYY-MM-DD; choice: chọn một trong options
    kind              TEXT     NOT NULL,
    required          BOOLEAN  NOT NULL DEFAULT FALSE,
    -- Câu hướng dẫn dưới ô nhập, ví dụ "Số in trên tem dán ở mặt dưới máy"
    help_text         TEXT,
    -- Đơn vị hiện cạnh ô số, ví dụ "đồng", "bản"
    unit              TEXT,
    options           TEXT[],
    display_order     SMALLINT NOT NULL DEFAULT 0,

    PRIMARY KEY (request_type_code, code),
    CONSTRAINT request_type_fields_kieu_hop_le
        CHECK (kind IN ('text', 'number', 'date', 'choice')),
    -- Ô chọn phải có ít nhất hai lựa chọn; kiểu khác không mang danh sách lựa chọn
    CONSTRAINT request_type_fields_lua_chon_hop_le
        CHECK ((kind = 'choice') = (options IS NOT NULL)
               AND (options IS NULL OR cardinality(options) >= 2)),
    -- Mã là khóa trong JSONB: chữ thường, số, gạch ngang — giống mã trạng thái
    CONSTRAINT request_type_fields_ma_hop_le
        CHECK (code ~ '^[a-z][a-z0-9-]*$')
);

COMMENT ON COLUMN request_types.sla_hours IS
    'Ngưỡng SLA tính bằng giờ làm việc theo lịch mặc định (#199). Cạnh leo thang tự động ở #42 đọc cột này, không mã cứng ngưỡng.';

COMMENT ON COLUMN request_types.sla_grace_hours IS
    'Ân hạn tính bằng giờ làm việc (#94, #199): mỗi lần hồ sơ vào lại trạng thái đếm giờ — phân công lại, mở lại, bổ sung thông tin xong — người nhận có ít nhất chừng này trước khi bộ quét được leo thang lại, dù hồ sơ đã quá hạn. Đồng hồ tổng không đặt lại. 0 là không có ân hạn.';

COMMENT ON COLUMN request_types.sla_warn_percent IS
    'Ngưỡng "sắp hết hạn" (#175): hồ sơ đã dùng từ chừng này phần trăm cam kết trở lên mà chưa quá hạn thì dịch vụ trả cờ sla_due_soon, giao diện tô vàng. Tính trên hạn của chính hồ sơ nên tự co giãn theo hạn.';

COMMENT ON COLUMN request_types.sla_extension_max_percent IS
    'Gia hạn (#101): mỗi lần gia hạn tối đa chừng này phần trăm hạn gốc của hồ sơ — hạn của loại nhân hệ số ưu tiên. Giảng viên để ngỏ con số; navigator chốt 50 ngày 15/10.';

COMMENT ON COLUMN request_types.sla_extension_max_count IS
    'Gia hạn (#101): tổng số lần gia hạn tối đa của một hồ sơ. Ai gia hạn lần nào là chuyện của ràng buộc gắn trên từng cạnh gia hạn.';

COMMENT ON COLUMN request_types.reopen_max_count IS
    'Mở lại (#102, giảng viên chốt 08/10): tổng số lần người gửi mở lại một hồ sơ, tính cả mở lại từ Hoàn tất lẫn từ Đã đóng. Quá số này thì phải tạo hồ sơ mới liên kết hồ sơ cũ (requests.parent_request_id). 0 là không cho mở lại.';

-- Ánh xạ loại yêu cầu sang phòng ban phụ trách. Nhiều-nhiều có đánh dấu mặc
-- định: một loại yêu cầu có thể do vài phòng đảm nhận, nhưng chỉ một phòng được
-- gợi ý sẵn cho người phân loại. Đây cũng là nơi tầng I về sau đọc để gợi ý
-- định tuyến — và theo nguyên tắc bất di dịch, gợi ý vẫn phải qua tay người.
CREATE TABLE request_type_routing (
    request_type_code  TEXT     NOT NULL REFERENCES request_types (code) ON DELETE CASCADE,
    department_code    TEXT     NOT NULL REFERENCES departments (code)   ON DELETE RESTRICT,
    is_default         BOOLEAN  NOT NULL DEFAULT FALSE,

    PRIMARY KEY (request_type_code, department_code)
);

CREATE UNIQUE INDEX request_type_routing_chi_mot_mac_dinh
    ON request_type_routing (request_type_code) WHERE is_default;


-- ===========================================================================
-- 8. MỨC ƯU TIÊN
-- ===========================================================================
-- Cũng là dữ liệu, vì cùng một lý do với trạng thái: nếu chuỗi "Khẩn" lọt vào
-- câu lệnh if thì đã vi phạm nguyên tắc cấu-hình-thay-vì-mã-cứng.
--
-- Ai đặt mức ưu tiên là chuyện của ràng buộc Poka-yoke, không phải của bảng
-- này: người tạo yêu cầu không bao giờ tự đặt được.

CREATE TABLE priorities (
    code           TEXT      PRIMARY KEY,
    label          TEXT      NOT NULL,
    is_default     BOOLEAN   NOT NULL DEFAULT FALSE,
    display_order  SMALLINT  NOT NULL DEFAULT 0,
    -- Hạn theo mức ưu tiên (#101): hạn = hạn chuẩn của loại yêu cầu × hệ số / 100
    sla_factor_percent SMALLINT NOT NULL DEFAULT 100,

    CONSTRAINT priorities_he_so_duong CHECK (sla_factor_percent > 0)
);

CREATE UNIQUE INDEX priorities_chi_mot_mac_dinh
    ON priorities (is_default) WHERE is_default;


-- ===========================================================================
-- 9. LOẠI LỜI NHẮN TRÊN HỒ SƠ (#128, ADR-0005)
-- ===========================================================================
-- Lời nhắn là thao tác KHÔNG đổi hồ sơ: không đổi trạng thái, không đổi trường nào,
-- không chạm đồng hồ SLA. Vì vậy nó không đi qua cửa chuyển trạng thái và không vào
-- nhật ký sự kiện. Bản thân lời nhắn nằm ở bảng `case_messages` do Alembic sở hữu,
-- chỉ ghi thêm như `event_log`. Hai bảng dưới đây khai LOẠI lời nhắn và vai trò gửi
-- được từng loại — cấu hình, không phải dữ liệu vận hành.
--
-- Ai nhắn được trên hồ sơ nào thì KHÔNG khai ở đây: ai mở được hồ sơ thì nhắn được,
-- theo đúng cửa nhìn thấy của từng buồng lái. Hai bảng này chỉ thu hẹp thêm — theo vai
-- trò, và theo các cờ của từng loại.

CREATE TABLE message_kinds (
    code                   TEXT      PRIMARY KEY,
    label                  TEXT      NOT NULL,
    description            TEXT,
    -- Chỉ người gửi của CHÍNH hồ sơ gửi được loại này, như ràng buộc
    -- requester-owns-case trên các cạnh của người gửi
    owner_only             BOOLEAN   NOT NULL DEFAULT FALSE,
    -- Chỉ gửi được khi hồ sơ nằm trong hàng đợi phòng ban. Tập trạng thái đó SUY từ
    -- bộ quy tắc — trạng thái mà vai trò phòng ban có cạnh đi ra — không liệt kê ở đây
    department_stage_only  BOOLEAN   NOT NULL DEFAULT FALSE,
    -- Gửi lại loại này chỉ được khi phía bên kia đã trả lời lần gửi trước, hoặc đã quá
    -- chừng này giờ. NULL là không giới hạn.
    reask_after_hours      SMALLINT,
    body_required          BOOLEAN   NOT NULL DEFAULT TRUE,
    -- Người gửi của hồ sơ KHÔNG thấy và không gửi được loại này, kể cả khi họ cũng có vai
    -- trò nhân viên — trò chuyện nội bộ giữa nhân viên (#156). Ràng buộc theo hồ sơ, không
    -- theo vai trò. Dịch vụ lọc ở mọi điểm cuối trả lời nhắn.
    hidden_from_requester  BOOLEAN   NOT NULL DEFAULT FALSE,
    display_order          SMALLINT  NOT NULL DEFAULT 0,

    CONSTRAINT message_kinds_hoi_lai_duong
        CHECK (reask_after_hours IS NULL OR reask_after_hours > 0),
    -- Loại chỉ người gửi hồ sơ gửi được mà lại ẩn với chính người đó là cấu hình chết
    CONSTRAINT message_kinds_noi_bo_khong_cua_chu_ho_so
        CHECK (NOT (owner_only AND hidden_from_requester))
);

CREATE TABLE message_kind_roles (
    kind_code  TEXT  NOT NULL REFERENCES message_kinds (code) ON DELETE CASCADE,
    role_code  TEXT  NOT NULL REFERENCES roles (code)         ON DELETE RESTRICT,

    PRIMARY KEY (kind_code, role_code)
);

COMMENT ON TABLE message_kinds IS
    'Loại lời nhắn trên hồ sơ (#128). Lời nhắn không đổi hồ sơ nên không phải cạnh chuyển trạng thái — xem ADR-0005.';


-- ===========================================================================
-- 10. LỊCH LÀM VIỆC (#199)
-- ===========================================================================
-- Mọi khoảng thời gian của quy trình — đồng hồ SLA, ân hạn (#94), các hạn chờ — đo
-- bằng GIỜ LÀM VIỆC: hồ sơ cam kết 8 giờ, phòng ban nhận lúc 15:00 thứ Sáu thì hạn là
-- 15:00 thứ Hai, không phải 23:00 thứ Sáu. Giờ làm, ngày nghỉ, múi giờ đều là dữ liệu
-- trong infra/seed/ — doanh nghiệp đổi lịch không sửa mã.
--
-- Một lịch chung cho cả công ty (`is_default`). Bảng vẫn có khóa lịch để sau này gắn
-- lịch riêng cho phòng ban mà không phải đổi lược đồ.
--
-- Mốc thời gian vẫn lưu theo UTC như mọi nơi khác; lịch chỉ dùng để ĐO KHOẢNG giữa hai
-- mốc. Không chỗ nào trong mã được tự trừ hai mốc để ra thời gian xử lý — mọi phép đo
-- đi qua hai hàm ở cuối mục này.

CREATE TABLE work_calendars (
    code        TEXT     PRIMARY KEY,
    label       TEXT     NOT NULL,
    -- Tên múi giờ IANA, ví dụ Asia/Ho_Chi_Minh. Giờ làm và ngày nghỉ hiểu theo múi này.
    -- Tên sai thì tệp 99 chặn ngay lúc nạp.
    time_zone   TEXT     NOT NULL,
    is_default  BOOLEAN  NOT NULL DEFAULT FALSE
);

CREATE UNIQUE INDEX work_calendars_chi_mot_mac_dinh
    ON work_calendars (is_default) WHERE is_default;

-- Khung giờ làm theo thứ trong tuần. Một ngày có nhiều khung — nghỉ trưa là khoảng
-- trống giữa hai khung. `end_time` nhận '24:00' cho khung chạy tới hết ngày.
CREATE TABLE work_hours (
    calendar_code  TEXT      NOT NULL REFERENCES work_calendars (code) ON DELETE CASCADE,
    -- 1 = thứ Hai … 7 = Chủ nhật, theo ISODOW của PostgreSQL
    iso_weekday    SMALLINT  NOT NULL,
    start_time     TIME      NOT NULL,
    end_time       TIME      NOT NULL,

    PRIMARY KEY (calendar_code, iso_weekday, start_time),

    CONSTRAINT work_hours_thu_hop_le
        CHECK (iso_weekday BETWEEN 1 AND 7),
    CONSTRAINT work_hours_khung_hop_le
        CHECK (start_time < end_time)
);

-- Ngày nghỉ trọn ngày (lễ, Tết, nghỉ bù). Ngày nằm ở đây thì không có giờ làm nào,
-- kể cả khi rơi vào thứ có khung giờ.
CREATE TABLE holidays (
    calendar_code  TEXT  NOT NULL REFERENCES work_calendars (code) ON DELETE CASCADE,
    day            DATE  NOT NULL,
    label          TEXT  NOT NULL,

    PRIMARY KEY (calendar_code, day)
);

COMMENT ON TABLE work_calendars IS
    'Lịch làm việc (#199). Mọi khoảng thời gian của quy trình đo bằng giờ làm việc theo lịch mặc định.';

-- Số giây làm việc giữa hai mốc, theo lịch `p_lich` (bỏ trống là lịch mặc định).
-- Đi từng ngày theo giờ địa phương, bỏ ngày nghỉ, cộng phần giao của [p_tu, p_den) với
-- từng khung giờ làm của ngày đó. Mốc đảo ngược hay trùng nhau thì ra 0.
CREATE FUNCTION so_giay_lam_viec(p_tu TIMESTAMPTZ, p_den TIMESTAMPTZ, p_lich TEXT DEFAULT NULL)
RETURNS BIGINT
LANGUAGE sql STABLE
AS $$
    WITH lich AS (
        SELECT code, time_zone
        FROM work_calendars
        WHERE code = COALESCE(p_lich, (SELECT code FROM work_calendars WHERE is_default))
    ),
    ngay AS (
        SELECT l.code, l.time_zone, d::date AS ngay
        FROM lich l,
             generate_series((p_tu AT TIME ZONE l.time_zone)::date,
                             (p_den AT TIME ZONE l.time_zone)::date,
                             INTERVAL '1 day') AS d
        WHERE p_den > p_tu
          AND NOT EXISTS (
              SELECT 1 FROM holidays h WHERE h.calendar_code = l.code AND h.day = d::date
          )
    )
    SELECT COALESCE(FLOOR(SUM(GREATEST(0, EXTRACT(EPOCH FROM
               LEAST(p_den, (n.ngay + w.end_time) AT TIME ZONE n.time_zone)
             - GREATEST(p_tu, (n.ngay + w.start_time) AT TIME ZONE n.time_zone))))), 0)::BIGINT
    FROM ngay n
    JOIN work_hours w
      ON w.calendar_code = n.code AND w.iso_weekday = EXTRACT(ISODOW FROM n.ngay)
$$;

-- Mốc thời gian sau `p_giay` giây làm việc kể từ `p_tu` — hạn chót để hiển thị ("hạn
-- 15:00 thứ Hai"). Phép ngược của hàm trên: so_giay_lam_viec(p_tu, kết quả) = p_giay.
-- Trả NULL khi không có lịch, hoặc khi mười năm tới không đủ giờ làm (lịch trống).
CREATE FUNCTION moc_sau_giay_lam_viec(p_tu TIMESTAMPTZ, p_giay BIGINT, p_lich TEXT DEFAULT NULL)
RETURNS TIMESTAMPTZ
LANGUAGE plpgsql STABLE
AS $$
DECLARE
    v_lich  TEXT;
    v_tz    TEXT;
    v_ngay  DATE;
    v_con   NUMERIC;
    v_bat   TIMESTAMPTZ;
    v_ket   TIMESTAMPTZ;
    v_khung RECORD;
BEGIN
    SELECT code, time_zone INTO v_lich, v_tz
    FROM work_calendars
    WHERE code = COALESCE(p_lich, (SELECT code FROM work_calendars WHERE is_default));

    IF v_lich IS NULL OR p_tu IS NULL OR p_giay IS NULL THEN
        RETURN NULL;
    END IF;
    IF p_giay <= 0 THEN
        RETURN p_tu;
    END IF;

    v_con  := p_giay;
    v_ngay := (p_tu AT TIME ZONE v_tz)::date;

    FOR i IN 1 .. 3660 LOOP
        IF NOT EXISTS (SELECT 1 FROM holidays WHERE calendar_code = v_lich AND day = v_ngay) THEN
            FOR v_khung IN
                SELECT start_time, end_time
                FROM work_hours
                WHERE calendar_code = v_lich AND iso_weekday = EXTRACT(ISODOW FROM v_ngay)
                ORDER BY start_time
            LOOP
                v_bat := GREATEST(p_tu, (v_ngay + v_khung.start_time) AT TIME ZONE v_tz);
                v_ket := (v_ngay + v_khung.end_time) AT TIME ZONE v_tz;
                CONTINUE WHEN v_ket <= v_bat;

                IF EXTRACT(EPOCH FROM v_ket - v_bat) >= v_con THEN
                    RETURN v_bat + make_interval(secs => v_con::double precision);
                END IF;
                v_con := v_con - EXTRACT(EPOCH FROM v_ket - v_bat);
            END LOOP;
        END IF;
        v_ngay := v_ngay + 1;
    END LOOP;

    RETURN NULL;
END;
$$;
