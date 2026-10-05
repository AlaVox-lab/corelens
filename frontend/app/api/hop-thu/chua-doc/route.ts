// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Số lời nhắn chưa đọc, cho thanh bên tự hỏi lại khoảng 12 giây một lần (#155).
//
// Đi qua máy chủ Next.js như mọi lời gọi khác: token không bao giờ tới trình duyệt. Chỉ
// trả đúng một con số — thanh bên hỏi định kỳ ở mọi trang, nên lần hỏi phải nhẹ.

import { goiDichVu } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET() {
  const ketQua = await goiDichVu<{ unread: number }>("/inbox/unread");
  // Phiên hết hạn hay dịch vụ không trả lời: `null`, thanh bên giữ con số đang hiện
  return Response.json({ unread: ketQua?.unread ?? null });
}
