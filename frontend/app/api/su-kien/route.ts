// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Luồng tín hiệu "hồ sơ vừa đổi" cho trình duyệt (#387) — chuyển tiếp `GET /me/stream` của dịch vụ ứng dụng.
//
// Đi qua máy chủ Next.js như mọi lời gọi khác: token không bao giờ tới trình duyệt, trình duyệt chỉ mở
// `EventSource` tới chính cổng. Dịch vụ từ chối hay không tới được thì trả 204: theo chuẩn SSE, trình duyệt
// thấy 204 là thôi không nối lại — cổng chạy tiếp bằng hỏi định kỳ như trước.

import { moLuongDichVu } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(yeuCau: Request) {
  const luong = await moLuongDichVu("/me/stream", yeuCau.signal);
  if (!luong?.body) return new Response(null, { status: 204 });

  return new Response(luong.body, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      // Reverse proxy đứng trước cổng (nginx…) không gom luồng vào bộ đệm
      "X-Accel-Buffering": "no",
    },
  });
}
