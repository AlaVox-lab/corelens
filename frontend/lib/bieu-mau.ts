// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Đọc biểu mẫu thao tác ở buồng lái thành dữ liệu gửi cho dịch vụ.
//
// Dùng chung giữa thao tác của buồng lái điều phối (#82), buồng lái phòng ban (#83) và
// cổng người gửi (#127). Tệp thường, KHÔNG mang chỉ thị "use server": tệp mang chỉ thị
// đó chỉ được xuất hàm bất đồng bộ, và xuất thứ khác thì trang vỡ lúc chạy dù bước dựng
// vẫn xanh (#44).

import { kieuTruong } from "@/lib/truong";

/** Tiền tố tên ô nhập mang giá trị một trường quyết định, ví dụ `truong:priority_code`. */
export const TIEN_TO_TRUONG = "truong:";

export function chuoi(gia_tri: FormDataEntryValue | null): string {
  return typeof gia_tri === "string" ? gia_tri.trim() : "";
}

/**
 * Gom các ô `truong:*` thành `changes`. Ô CHỌN để trống thì BỎ QUA; ô CHỮ để trống thì
 * gửi `null`.
 *
 * Bỏ ô chọn trống thay vì gửi chuỗi rỗng là cố ý. Gửi `request_type_code: ""` thì ràng
 * buộc trên cạnh hiểu là muốn xóa loại, và báo "không được xóa loại yêu cầu" — sai câu,
 * vì người dùng chỉ quên chọn. Bỏ hẳn trường đi thì ràng buộc báo đúng "phải chọn loại".
 * Với người xử lý cũng vậy: để trống nghĩa là chưa giao cho ai, không phải xóa người.
 *
 * Ô chữ thì ngược lại (#127): người gửi xóa hết mô tả là muốn hồ sơ không còn mô tả. Bỏ
 * qua thì mô tả cũ ở lại, và ràng buộc báo "chưa có gì thay đổi" ngay sau khi người
 * dùng vừa xóa cả một đoạn. Ô nào là ô chọn thì hỏi lib/truong.ts — cùng chỗ quyết định
 * dựng ô chọn hay ô chữ, nên cách đọc ô luôn khớp với cách vẽ ô.
 */
/** Đọc chuỗi JSON của ô ẩn; hỏng thì gửi bộ rỗng để dịch vụ báo thiếu trường bằng lời. */
export function docJson(v: string): Record<string, unknown> {
  try {
    const kq = JSON.parse(v || "{}");
    return kq && typeof kq === "object" && !Array.isArray(kq) ? kq : {};
  } catch {
    return {};
  }
}

export function gomThayDoi(duLieu: FormData): Record<string, unknown> {
  const thayDoi: Record<string, unknown> = {};
  for (const [ten, gia_tri] of duLieu.entries()) {
    if (!ten.startsWith(TIEN_TO_TRUONG)) continue;
    const truong = ten.slice(TIEN_TO_TRUONG.length);
    const v = chuoi(gia_tri);
    // Bộ trường riêng (#250) đi dưới dạng JSON trong một ô ẩn
    if (kieuTruong(truong).rieng) {
      thayDoi[truong] = docJson(v);
      continue;
    }
    if (v) thayDoi[truong] = v;
    else if (!kieuTruong(truong).nguon) thayDoi[truong] = null;
  }
  return thayDoi;
}

/**
 * Đọc biểu mẫu lời nhắn (#128) thành phần thân gửi cho dịch vụ. `null` khi thiếu thông
 * tin. Loại lời nhắn là giá trị của nút đã bấm, mà nút dựng từ `message_kinds` của dịch
 * vụ — không có mã loại nào viết ở giao diện.
 */
export function docLoiNhan(
  duLieu: FormData,
): { maHoSo: string; than: { kind: string; body: string | null } } | null {
  const maHoSo = chuoi(duLieu.get("case_id"));
  const kind = chuoi(duLieu.get("kind"));
  if (!maHoSo || !kind) return null;
  return { maHoSo, than: { kind, body: chuoi(duLieu.get("body")) || null } };
}
