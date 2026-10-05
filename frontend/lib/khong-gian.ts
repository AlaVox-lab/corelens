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
export type TenIcon = "trang-chu" | "gui" | "ho-so" | "dieu-phoi" | "phong-ban";

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
      moTa: "Một biểu mẫu cho mọi loại yêu cầu: sự cố thiết bị, cấp quyền phần mềm, giấy tờ nhân sự, đề xuất mua sắm.",
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
  ],
};

export function loiVaoCua(khongGian: string[]): LoiVao[] {
  return khongGian.flatMap((k) => LOI_VAO[k] ?? []);
}
