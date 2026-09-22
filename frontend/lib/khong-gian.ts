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

export type LoiVao = {
  duongDan: string;
  nhan: string;
  /** Một câu giải thích, hiện ở trang chủ. */
  moTa: string;
};

const LOI_VAO: Record<string, LoiVao[]> = {
  portal: [
    {
      duongDan: "/yeu-cau/moi",
      nhan: "Gửi yêu cầu",
      moTa: "Một biểu mẫu cho mọi loại yêu cầu: sự cố thiết bị, cấp quyền phần mềm, giấy tờ nhân sự, đề xuất mua sắm.",
    },
    {
      duongDan: "/yeu-cau",
      nhan: "Hồ sơ của tôi",
      moTa: "Theo dõi từng bước hồ sơ đi qua, kể cả những lần bị trả lại hay quay lui.",
    },
  ],
  coordination: [
    {
      duongDan: "/dieu-phoi",
      nhan: "Điều phối",
      moTa: "Phân loại hồ sơ mới gửi lên và chuyển về đúng phòng ban phụ trách.",
    },
  ],
};

export function loiVaoCua(khongGian: string[]): LoiVao[] {
  return khongGian.flatMap((k) => LOI_VAO[k] ?? []);
}
