"use server";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Thao tác ghi của hộp thư (#155). Gửi lời nhắn KHÔNG nằm ở đây: hộp thư dùng lại thao tác
// gửi của đúng buồng lái mở hồ sơ, để luật của #128 chỉ có một nơi.
//
// Nhớ: tệp mang chỉ thị "use server" chỉ được xuất hàm bất đồng bộ.

import { guiDichVu } from "@/lib/api";

/**
 * Đánh dấu đã đọc tới lời nhắn mới nhất của hồ sơ. Không đổi hồ sơ (ADR-0005), nên không
 * làm mới trang nào — thanh bên tự hỏi lại con số chưa đọc.
 */
export async function danhDauDaDoc(maHoSo: number): Promise<void> {
  await guiDichVu<void>(`/inbox/${maHoSo}/read`, {});
}
