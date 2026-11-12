"use server";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Bật/tắt một loại thông báo thư của chính người dùng (#251). Dịch vụ lấy định danh từ token,
// không nhận từ đây — không ai đổi được tùy chọn của người khác.
//
// Nhớ: tệp mang chỉ thị "use server" chỉ được xuất hàm bất đồng bộ.

import { guiDichVu } from "@/lib/api";

export async function doiThongBao(
  ma: string,
  bat: boolean,
): Promise<{ ok: boolean; thongDiep?: string }> {
  const ketQua = await guiDichVu<unknown>(`/me/notifications/${encodeURIComponent(ma)}`, { enabled: bat });
  return ketQua.ok ? { ok: true } : { ok: false, thongDiep: ketQua.thongDiep };
}
