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
  activity_code: string;
  activity_label: string;
  requires_note: boolean;
  /**
   * Trường mà cạnh này cho đặt, từ ràng buộc gắn trên cạnh (#78). Buồng lái dựng ô
   * nhập từ đây, cùng lý do nó dựng nút bấm từ danh sách cạnh. Cạnh của người gửi
   * luôn cho danh sách rỗng.
   */
  fields: string[];
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
  sla_paused: boolean;
  /** Đồng hồ đã khởi động chưa — nó chỉ khởi động khi phòng ban nhận việc. */
  sla_started: boolean;
  /**
   * Hồ sơ quá hạn vừa được giao lại hay mở lại: còn chừng này giây trước khi bị leo
   * thang lần nữa. `null` khi không áp.
   */
  sla_grace_seconds: number | null;
};

export type HoSoChiTiet = HoSoTomTat & {
  description: string | null;
  requester_id: string;
  assignee_id: string | null;
  history: SuKien[];
  allowed_transitions: CanhDiDuoc[];
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
export type NhomHangDoi = NhanCoMa & { count: number };

export type MucHangDoi = HoSoTomTat & {
  requester_label: string | null;
  priority: NhanCoMa | null;
  /** Lúc hồ sơ vào trạng thái hiện tại — mốc để tính thời gian chờ. */
  state_entered_at: string;
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
