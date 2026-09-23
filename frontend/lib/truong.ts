// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Siêu dữ liệu TRÌNH BÀY của các trường quyết định trên hồ sơ.
//
// Cùng ranh giới với lib/trang-thai.ts. Tệp này KHÔNG quyết định cạnh nào có ô nhập
// nào — điều đó đến từ `fields` của từng cạnh, mà dịch vụ suy từ ràng buộc gắn trên
// cạnh (#78). Tệp này chỉ trả lời: một trường đã được phép thì gọi nó là gì, và lấy
// lựa chọn từ danh mục nào.
//
// Vì sao chấp nhận một bảng nhỏ ở đây: bốn trường quyết định là LƯỢC ĐỒ của hồ sơ —
// cột trong bảng `requests` — chứ không phải cấu hình nghiệp vụ. Doanh nghiệp khai lại
// trạng thái, vai trò, phòng ban mà không đụng tới chúng. Đổi chúng là đổi lược đồ, và
// khi đó `lib/kieu.ts` cũng phải đổi theo.
//
// Gặp trường lạ thì hiện ô nhập chữ kèm tên trường, không vỡ trang.

export type NguonDanhMuc = "priorities" | "departments" | "request-types" | "assignees";

export type KieuTruong = {
  nhan: string;
  /** Danh mục để dựng ô chọn. Không có thì hiện ô nhập chữ. */
  nguon?: NguonDanhMuc;
};

const BANG: Record<string, KieuTruong> = {
  request_type_code: { nhan: "Loại yêu cầu", nguon: "request-types" },
  priority_code: { nhan: "Mức ưu tiên", nguon: "priorities" },
  department_code: { nhan: "Phòng ban phụ trách", nguon: "departments" },
  // Danh mục tra từ danh bạ Keycloak (#84), theo phòng đang giữ hồ sơ. Giá trị gửi đi
  // là định danh, nhãn hiển thị là tên thật.
  assignee_id: { nhan: "Người xử lý", nguon: "assignees" },
};

export function kieuTruong(ma: string): KieuTruong {
  return BANG[ma] ?? { nhan: ma };
}
