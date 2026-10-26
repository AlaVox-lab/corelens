// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Hình dạng dữ liệu mà dịch vụ ứng dụng trả về.
//
// Đây là bản dịch thủ công của `backend/app/workflow/schemas.py` sang TypeScript. Hai
// tệp phải khớp nhau, và không có gì tự động bắt được lúc chúng lệch — TypeScript
// không nhìn thấy mã Python.
//
// Vì sao không sinh tự động từ lược đồ OpenAPI: thêm một bước sinh mã vào chuỗi dựng
// là thêm một chỗ hỏng cho ban giám khảo khi họ dựng lại từ mã nguồn, mà đổi lại chỉ
// tiết kiệm được vài chục dòng. Khi số điểm cuối tăng lên đủ nhiều thì tính lại.
//
// KHI SỬA `schemas.py`, SỬA LUÔN TỆP NÀY. Bộ kiểm thử `backend/tests/test_routes.py`
// khẳng định hình dạng phía máy chủ, nên nó sẽ bắt được thay đổi ở đó — nhưng nó
// không biết gì về tệp này.

/** Một giá trị danh mục: mã để mã nguồn so sánh, nhãn để người đọc. */
export type NhanCoMa = {
  code: string;
  label: string;
};

export type LoaiYeuCau = NhanCoMa & {
  description: string | null;
  sla_hours: number;
};

export type TrangThai = NhanCoMa & {
  is_terminal: boolean;
};

/**
 * Một thao tác người dùng thực hiện được từ trạng thái hiện tại.
 *
 * Danh sách này do engine sinh ra từ bảng `transitions` và ma trận phân quyền. Giao
 * diện dựng nút bấm **chỉ** từ đây, không bao giờ từ một bảng ánh xạ viết trong mã
 * nguồn giao diện — xem chú thích đầu `app/yeu-cau/[id]/page.tsx`.
 */
export type CanhDiDuoc = {
  to_state: string;
  to_state_label: string;
  /**
   * Trạng thái đích là trạng thái kết thúc: đi rồi không quay lại được. Giao diện hỏi
   * lại trước khi gửi, kèm ô lý do tùy chọn (#98).
   */
  to_state_is_terminal: boolean;
  /**
   * Trạng thái kết thúc đích còn cạnh mở lại: số giờ làm việc kể từ lúc vào đó mà người gửi
   * còn mở lại được (#102). `null` là kết thúc hẳn — chỉ còn cách tạo hồ sơ mới.
   */
  to_state_reopen_hours: number | null;
  activity_code: string;
  activity_label: string;
  requires_note: boolean;
  /**
   * Tên ô ghi chú của cạnh (#79). `null` thì gọi là "Lý do". Ở cạnh bổ sung thông tin,
   * ô ghi chú là chính câu trả lời của người gửi chứ không phải lời giải thích.
   */
  note_label: string | null;
  /**
   * Cạnh tự trỏ: đổi hồ sơ mà giữ nguyên trạng thái — nhận việc về mình, sửa nội dung
   * (ADR-0005). Giao diện nói "giữ nguyên trạng thái" thay cho "chuyển sang".
   */
  keeps_state: boolean;
  /**
   * Trường mà cạnh này cho đặt, từ ràng buộc gắn trên cạnh (#78). Giao diện dựng ô
   * nhập từ đây, cùng lý do nó dựng nút bấm từ danh sách cạnh. Cạnh của người gửi chỉ
   * có trường ở thao tác sửa nội dung (#127).
   */
  fields: string[];
};

/**
 * Một trường quyết định mà lần chuyển đã đổi giá trị (#100). `before` rỗng khi trường
 * chưa có giá trị trước đó. Nhãn do dịch vụ tra, kể cả mục đã ngừng dùng.
 */
export type ThayDoiTruong = {
  field: string;
  before: NhanCoMa | null;
  after: NhanCoMa | null;
};

/** Một mốc trong dòng thời gian, dựng thẳng từ bảng `event_log`. */
export type SuKien = {
  /** Chuỗi ISO 8601 theo UTC. Đổi sang giờ Việt Nam lúc hiển thị, xem lib/dinh-dang.ts. */
  timestamp: string;
  activity: string;
  activity_label: string | null;
  actor: string;
  actor_label: string;
  is_system: boolean;
  from_state: string;
  from_state_label: string;
  to_state: string;
  to_state_label: string;
  note: string | null;
  /** Tên của ghi chú, cùng tên với ô nhập lúc ghi (#79). `null` thì gọi là "Lý do". */
  note_label: string | null;
  /** Trường quyết định mà lần chuyển này đổi — nhật ký giữ trọn lịch sử thay đổi. */
  changes: ThayDoiTruong[];
  /** Mốc đi qua cạnh làm lại, khai trong dữ liệu (#153). */
  is_rework: boolean;
};

/** Cạnh hệ thống tự đi khi hồ sơ nằm im quá hạn chờ (#142). Nhãn lấy từ dữ liệu. */
export type TuDong = {
  activity_label: string;
  at: string | null;
  warn: boolean;
};

export type HoSoTomTat = {
  id: number;
  code: string;
  title: string;
  request_type: NhanCoMa | null;
  department: NhanCoMa | null;
  state: TrangThai;
  created_at: string;
  updated_at: string;

  sla_running_seconds: number;
  sla_paused_seconds: number;
  /** `null` khi hồ sơ chưa có loại yêu cầu, nên chưa biết áp ngưỡng nào. */
  sla_limit_seconds: number | null;
  sla_overdue: boolean;
  /** Đã dùng tới ngưỡng "sắp hết hạn" khai theo loại yêu cầu mà chưa quá hạn (#175). */
  sla_due_soon: boolean;
  /** Gia hạn xử lý (#101): `sla_limit_seconds` đã gồm số giờ này. */
  sla_extension_total_hours: number;
  sla_extension_count: number;
  sla_paused: boolean;
  /** Đồng hồ đã khởi động chưa — nó chỉ khởi động khi phòng ban nhận việc. */
  sla_started: boolean;
  /**
   * Hồ sơ quá hạn vừa được giao lại hay mở lại: còn chừng này giây trước khi bị leo
   * thang lần nữa. `null` khi không áp.
   */
  sla_grace_seconds: number | null;
  /**
   * Mốc hết hạn xử lý theo lịch làm việc, khi đồng hồ đang chạy (#199). `null` khi đồng hồ
   * đang dừng hay chưa chạy — lúc đó chưa biết hạn rơi vào đâu.
   */
  sla_due_at: string | null;
  /**
   * Hồ sơ đang ở trạng thái có hạn chờ: hết hạn thì hệ thống tự đi cạnh này (#142). `warn`
   * là đã vào khoảng báo trước. `null` khi trạng thái hiện tại không có hạn chờ.
   */
  auto_transition: TuDong | null;
  /**
   * Lời nhắn sau cùng là của người gửi hồ sơ (`true`), của nhân viên (`false`), hay chưa
   * có lời nhắn nào (`null`) — nguồn của dấu hiệu "đang chờ trả lời" trên danh sách (#128).
   */
  last_message_from_requester: boolean | null;
};

/**
 * Một lời nhắn trên hồ sơ (#128). Không phải mốc chuyển trạng thái: dòng thời gian trộn
 * nó với `history`, nhưng số lần đổi trạng thái chỉ đếm `history`.
 */
export type LoiNhan = {
  id: number;
  kind: string;
  kind_label: string;
  author: string;
  author_label: string;
  /** Tác giả là người gửi của chính hồ sơ. */
  from_requester: boolean;
  /** Của chính người đang xem. */
  mine: boolean;
  /** Lời nhắn nội bộ giữa nhân viên (#156) — người gửi hồ sơ không bao giờ nhận được. */
  internal: boolean;
  /** Trống được ở loại không bắt buộc nội dung, như "Hỏi tiến độ". */
  body: string | null;
  /** Chuỗi ISO 8601 theo UTC. */
  created_at: string;
};

/**
 * Một loại lời nhắn người đang xem gửi được lúc này. Giao diện dựng nút từ đây, cùng lý
 * do nó dựng nút chuyển trạng thái từ `allowed_transitions`.
 */
export type LoaiLoiNhan = NhanCoMa & {
  description: string | null;
  body_required: boolean;
  /** Loại nội bộ (#156): nút gửi nằm ở cuộc nội bộ, không ở cuộc với người gửi. */
  internal: boolean;
  /** Có giá trị thì loại này đang chờ luật hỏi lại: nút mờ tới mốc đó, hoặc tới khi có trả lời. */
  retry_at: string | null;
};

/** Hồ sơ nối với hồ sơ đang xem bằng `parent_request_id`: bản gốc hay bản tạo lại (#102). */
export type HoSoLienQuan = {
  id: number;
  code: string;
  title: string;
  state: TrangThai;
};

/** Một tệp đính kèm trên hồ sơ (#80). Tải về bằng `/api/tep/<id>`, không có khóa kho. */
export type TepDinhKem = {
  id: number;
  filename: string;
  content_type: string;
  size_bytes: number;
  uploaded_by_label: string;
  /** Chuỗi ISO 8601 theo UTC. */
  created_at: string;
};

/** Giới hạn tệp đính kèm. Giao diện hỏi dịch vụ thay vì tự giữ bản sao (#80). */
export type ChinhSachTep = {
  allowed_extensions: string[];
  max_mb: number;
  max_files: number;
  max_files_per_case: number;
};

export type HoSoChiTiet = HoSoTomTat & {
  /** Tệp đính kèm, và người đang xem đính kèm thêm được lúc này không (#80). */
  attachments: TepDinhKem[];
  can_attach: boolean;
  /** Hồ sơ này được tạo lại từ hồ sơ nào (#102). */
  parent: HoSoLienQuan | null;
  /** Các hồ sơ đã tạo lại từ hồ sơ này (#102). */
  children: HoSoLienQuan[];
  /** Đã mở lại mấy lần, và loại yêu cầu cho mở lại tối đa mấy lần (#102). */
  reopen_count: number;
  reopen_max_count: number | null;
  description: string | null;
  requester_id: string;
  assignee_id: string | null;
  history: SuKien[];
  allowed_transitions: CanhDiDuoc[];
  messages: LoiNhan[];
  message_kinds: LoaiLoiNhan[];
  /** Người đang xem đọc được cuộc nội bộ của hồ sơ này (#156). */
  sees_internal: boolean;
};

// ---------------------------------------------------------------------------
// Danh mục cho ô chọn
// ---------------------------------------------------------------------------

export type MucUuTien = NhanCoMa & { is_default: boolean };

export type PhongBan = NhanCoMa & { description: string | null };

// ---------------------------------------------------------------------------
// Buồng lái điều phối viên (#82)
// ---------------------------------------------------------------------------

/** Một trạng thái trong hàng đợi, kèm số hồ sơ. Danh sách suy từ bộ quy tắc. */
export type NhomHangDoi = NhanCoMa & {
  count: number;
  /**
   * Nhóm chỉ để theo dõi: hồ sơ của phòng đang ở lượt người gửi và sẽ quay về (#99).
   * Dịch vụ suy từ bộ quy tắc; hàng đợi điều phối luôn `false`.
   */
  watch_only: boolean;
};

export type MucHangDoi = HoSoTomTat & {
  requester_label: string | null;
  priority: NhanCoMa | null;
  /** Lúc hồ sơ vào trạng thái hiện tại — mốc để tính thời gian chờ. */
  state_entered_at: string;
  /** Hồ sơ do chính người đang xem gửi — chỉ hàng đợi điều phối đặt (#154). */
  requested_by_me?: boolean;
};

export type HangDoi = {
  groups: NhomHangDoi[];
  items: MucHangDoi[];
};

export type HoSoDieuPhoi = HoSoChiTiet & {
  requester_label: string | null;
  priority: NhanCoMa | null;
  state_entered_at: string;
  /** Phòng mặc định cho loại yêu cầu, để ô chọn điền sẵn. Chỉ là gợi ý. */
  suggested_department: NhanCoMa | null;
  /** Hồ sơ do chính người đang xem gửi: người khác phải điều phối nó (#154). */
  requested_by_me: boolean;
};

// ---------------------------------------------------------------------------
// Buồng lái phòng ban (#83)
// ---------------------------------------------------------------------------

export type MucHangDoiPhongBan = MucHangDoi & {
  /** Định danh Keycloak — để so. Tên bên dưới ghi lúc giao việc — để đọc. */
  assignee_id: string | null;
  assignee_label: string | null;
  assigned_to_me: boolean;
};

export type HangDoiPhongBan = {
  /** Phòng của người đang xem. */
  departments: NhanCoMa[];
  groups: NhomHangDoi[];
  items: MucHangDoiPhongBan[];
};

export type HoSoPhongBan = HoSoChiTiet & {
  requester_label: string | null;
  priority: NhanCoMa | null;
  state_entered_at: string;
  assignee_label: string | null;
  assigned_to_me: boolean;
};

/** Một người nhận được việc trong phòng, tra từ danh bạ Keycloak (#84). */
export type NguoiNhanViec = {
  /** `sub` của Keycloak — đúng giá trị gửi lên trong `assignee_id`. */
  id: string;
  name: string;
  username: string;
};

export type NguoiNhanViecTrongPhong = {
  department: PhongBan;
  people: NguoiNhanViec[];
};

/**
 * Cách liên hệ người gửi, tra từ danh bạ Keycloak lúc mở trang (#131). Hai trường liên
 * hệ trống nghĩa là người gửi chưa điền; `found` sai nghĩa là tài khoản không còn.
 */
export type LienHeNguoiGui = {
  name: string | null;
  email: string | null;
  phone: string | null;
  found: boolean;
};

// ---------------------------------------------------------------------------
// Hộp thư chung (#155)
// ---------------------------------------------------------------------------

/** Cửa người đang xem mở hồ sơ — quyết điểm cuối đọc chi tiết và gửi lời nhắn. */
export type CuaMoHoSo = "portal" | "department" | "coordination";

export type LoiNhanCuoi = {
  author_label: string;
  kind_label: string;
  body: string | null;
  created_at: string;
  /** Của chính người đang xem. */
  mine: boolean;
  from_requester: boolean;
};

/** Một cuộc trò chuyện: lời nhắn của MỘT hồ sơ, với người gửi hoặc nội bộ (#156). */
export type CuocTroChuyen = {
  case_id: number;
  code: string;
  title: string;
  state: TrangThai;
  requester_id: string;
  requester_label: string | null;
  workspace: CuaMoHoSo;
  /** Cuộc nội bộ giữa nhân viên — một hồ sơ có thể có cả hai cuộc. */
  internal: boolean;
  last_message: LoiNhanCuoi;
  unread: number;
  /** Phía bên kia nhắn sau cùng: đang chờ người đang xem trả lời. */
  waiting_on_me: boolean;
};

export type HopThu = {
  items: CuocTroChuyen[];
  unread: number;
};
