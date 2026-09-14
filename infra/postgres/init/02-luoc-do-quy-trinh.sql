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
    'Trạng thái đóng. Không cạnh nào được phép rời khỏi đây — ràng buộc ở bảng transitions.';

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
    display_order   SMALLINT  NOT NULL DEFAULT 0,

    -- Cột kỹ thuật, luôn bằng FALSE. Nó tồn tại chỉ để khóa ngoại ngay dưới
    -- chặn được việc tạo cạnh xuất phát từ một trạng thái kết thúc. Dữ liệu
    -- khởi tạo không bao giờ cần nhắc tới cột này — giá trị mặc định lo hết.
    from_is_terminal BOOLEAN  NOT NULL DEFAULT FALSE,

    CONSTRAINT transitions_khong_roi_trang_thai_ket_thuc
        CHECK (from_is_terminal = FALSE),

    FOREIGN KEY (rule_set_id, from_state, from_is_terminal)
        REFERENCES states (rule_set_id, code, is_terminal),

    FOREIGN KEY (rule_set_id, to_state)
        REFERENCES states (rule_set_id, code),

    -- Giữa hai trạng thái chỉ có tối đa một cạnh theo mỗi chiều
    UNIQUE (rule_set_id, from_state, to_state),

    CONSTRAINT transitions_khong_tu_tro_ve_minh
        CHECK (from_state <> to_state)
);

COMMENT ON COLUMN transitions.activity_code IS
    'Tên hoạt động đi vào trường activity của nhật ký sự kiện. Nhiều cạnh được phép dùng chung một mã khi chúng là cùng một hành vi nghiệp vụ — ví dụ hủy yêu cầu từ bốn trạng thái khác nhau.';
COMMENT ON COLUMN transitions.is_system IS
    'TRUE nghĩa là hệ thống tự đi, không vai trò người nào đi được. Hiện chỉ dùng cho cạnh leo thang khi quá hạn SLA.';
COMMENT ON COLUMN transitions.requires_note IS
    'TRUE thì bắt buộc nhập lý do. Ví dụ: từ chối vì sai chuyên môn, đóng hồ sơ khi không phòng nào nhận, mở lại vì chưa đạt.';

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
    is_active      BOOLEAN   NOT NULL DEFAULT TRUE,
    display_order  SMALLINT  NOT NULL DEFAULT 0,

    CONSTRAINT request_types_sla_duong
        CHECK (sla_hours > 0)
);

COMMENT ON COLUMN request_types.sla_hours IS
    'Ngưỡng SLA tính bằng giờ. Cạnh leo thang tự động ở #42 đọc cột này, không mã cứng ngưỡng.';

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
    display_order  SMALLINT  NOT NULL DEFAULT 0
);

CREATE UNIQUE INDEX priorities_chi_mot_mac_dinh
    ON priorities (is_default) WHERE is_default;
