// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Đọc biểu mẫu thao tác ở buồng lái thành dữ liệu gửi cho dịch vụ.
//
// Dùng chung giữa thao tác của buồng lái điều phối (#82) và buồng lái phòng ban (#83).
// Tệp thường, KHÔNG mang chỉ thị "use server": tệp mang chỉ thị đó chỉ được xuất hàm
// bất đồng bộ, và xuất thứ khác thì trang vỡ lúc chạy dù bước dựng vẫn xanh (#44).

/** Tiền tố tên ô nhập mang giá trị một trường quyết định, ví dụ `truong:priority_code`. */
export const TIEN_TO_TRUONG = "truong:";

export function chuoi(gia_tri: FormDataEntryValue | null): string {
  return typeof gia_tri === "string" ? gia_tri.trim() : "";
}

/**
 * Gom các ô `truong:*` thành `changes`, BỎ QUA ô để trống.
 *
 * Bỏ ô trống thay vì gửi chuỗi rỗng là cố ý. Gửi `request_type_code: ""` thì ràng buộc
 * trên cạnh hiểu là muốn xóa loại, và báo "không được xóa loại yêu cầu" — sai câu, vì
 * người dùng chỉ quên chọn. Bỏ hẳn trường đi thì ràng buộc báo đúng "phải chọn loại".
 * Với người xử lý cũng vậy: để trống nghĩa là chưa giao cho ai, không phải xóa người.
 */
export function gomThayDoi(duLieu: FormData): Record<string, string> {
  const thayDoi: Record<string, string> = {};
  for (const [ten, gia_tri] of duLieu.entries()) {
    if (!ten.startsWith(TIEN_TO_TRUONG)) continue;
    const v = chuoi(gia_tri);
    if (v) thayDoi[ten.slice(TIEN_TO_TRUONG.length)] = v;
  }
  return thayDoi;
}
