// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Lối vào của từng không gian làm việc.
//
// Dịch vụ quyết người dùng vào được không gian nào — trường `workspaces` của `/me` —
// còn tệp này chỉ trả lời: không gian đó có những trang nào, gọi chúng là gì. Thanh
// điều hướng và trang chủ cùng đọc từ đây, để hai nơi không bao giờ liệt kê khác nhau.
//
// Không gian lạ thì bỏ qua, không vỡ trang: dịch vụ thêm không gian mới trước khi giao
// diện kịp có trang cho nó là chuyện bình thường.

/** Tên icon của mục trên thanh bên. Thanh bên tra icon theo tên này (#158). */
export type TenIcon =
  | "trang-chu"
  | "gui"
  | "ho-so"
  | "dieu-phoi"
  | "phong-ban"
  | "bao-cao"
  | "hop-thu"
  | "he-thong"
  | "cau-hinh"
  | "uy-quyen"
  | "tri-thuc";

export type LoiVao = {
  duongDan: string;
  nhan: string;
  /** Một câu giải thích, hiện ở trang chủ. */
  moTa: string;
  icon: TenIcon;
  /**
   * Nhóm trên thanh bên: `chung` là việc của mọi nhân viên, `lam-viec` là buồng lái
   * theo vai trò — thanh bên đặt tiêu đề nhóm "Làm việc" trước nhóm này.
   */
  nhom: "chung" | "lam-viec";
};

const LOI_VAO: Record<string, LoiVao[]> = {
  portal: [
    {
      duongDan: "/yeu-cau/moi",
      nhan: "Gửi yêu cầu",
      moTa: "Một biểu mẫu cho mọi loại yêu cầu: sự cố thiết bị, cấp quyền phần mềm, giấy xác nhận nhân sự, đề xuất mua vật tư.",
      icon: "gui",
      nhom: "chung",
    },
    {
      duongDan: "/yeu-cau",
      nhan: "Hồ sơ của tôi",
      moTa: "Theo dõi từng bước hồ sơ đi qua, kể cả những lần bị trả lại hay quay lui.",
      icon: "ho-so",
      nhom: "chung",
    },
  ],
  coordination: [
    {
      duongDan: "/dieu-phoi",
      nhan: "Điều phối",
      moTa: "Phân loại hồ sơ mới gửi lên và chuyển về đúng phòng ban phụ trách.",
      icon: "dieu-phoi",
      nhom: "lam-viec",
    },
  ],
  department: [
    {
      duongDan: "/phong-ban",
      nhan: "Phòng ban",
      moTa: "Nhận hồ sơ về phòng, giao người xử lý, theo dõi hạn xử lý và hồ sơ bị leo thang.",
      icon: "phong-ban",
      nhom: "lam-viec",
    },
    {
      duongDan: "/uy-quyen",
      nhan: "Ủy quyền",
      moTa: "Nhờ người cùng phòng làm thay trong những ngày vắng mặt; trưởng phòng khai thay cho người xử lý.",
      icon: "uy-quyen",
      nhom: "lam-viec",
    },
  ],
  reports: [
    {
      duongDan: "/bao-cao",
      nhan: "Báo cáo",
      moTa: "Tồn đọng, thời gian xử lý, tỷ lệ trễ hạn và các loại yêu cầu — trong phạm vi bạn phụ trách.",
      icon: "bao-cao",
      nhom: "lam-viec",
    },
  ],
  system: [
    {
      duongDan: "/he-thong",
      nhan: "Hệ thống",
      moTa: "Tình trạng các dịch vụ của cụm: định danh, cơ sở dữ liệu, bộ quy tắc quy trình.",
      icon: "he-thong",
      nhom: "lam-viec",
    },
    {
      duongDan: "/quan-tri/cau-hinh",
      nhan: "Cấu hình quy trình",
      moTa: "Xem luồng xử lý đang chạy; sửa hạn, mức ưu tiên, loại yêu cầu và phòng ban mà không dựng lại cụm.",
      icon: "cau-hinh",
      nhom: "lam-viec",
    },
  ],
};

export function loiVaoCua(khongGian: string[]): LoiVao[] {
  return khongGian.flatMap((k) => LOI_VAO[k] ?? []);
}

/**
 * Trang hồ sơ mà người có các không gian này mở được, cho một mã hồ sơ cho trước (#315): buồng
 * lái điều phối nếu có, không thì buồng lái phòng ban. Không có cả hai thì không có trang nào để
 * dẫn tới — phía gọi hiện mã hồ sơ dạng chữ thường thay vì liên kết gãy.
 */
export function duongDanHoSo(ma: number, khongGian: string[]): string | null {
  if (khongGian.includes("coordination")) return `/dieu-phoi/${ma}`;
  if (khongGian.includes("department")) return `/phong-ban/${ma}`;
  return null;
}
