// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Người gửi bấm "Đã giải quyết được, không gửi nữa" sau khi xem hồ sơ tương tự (#319) — một yêu cầu
// được ngăn chặn. Ghi hỏng thì thôi: người gửi vẫn rời biểu mẫu như họ muốn, bộ quét sẽ tính phiên đó
// là bỏ không gửi khi quá hạn chờ.

import { guiDichVu } from "@/lib/api";

export const dynamic = "force-dynamic";

const MA_PHIEN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(yeuCau: Request) {
  const than = (await yeuCau.json().catch(() => null)) as { session_id?: unknown } | null;
  if (typeof than?.session_id === "string" && MA_PHIEN.test(than.session_id)) {
    await guiDichVu<undefined>("/similar-cases/abandon", { session_id: than.session_id });
  }
  return new Response(null, { status: 204 });
}
