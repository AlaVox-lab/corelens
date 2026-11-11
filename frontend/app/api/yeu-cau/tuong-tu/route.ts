// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Hồ sơ đã giải quyết tương tự cho biểu mẫu Gửi yêu cầu (#319).
//
// Trình duyệt gọi đây khi người gửi ngừng gõ tiêu đề và mô tả. Đi qua máy chủ Next.js như mọi lời gọi
// khác — token Keycloak không tới trình duyệt. KHÔNG BAO GIỜ trả lỗi cho biểu mẫu: chưa đăng nhập, dịch
// vụ tắt, mô hình nhúng tắt hay chậm — đều là danh sách rỗng, để biểu mẫu không hiện gì lạ và không chờ.

import { guiDichVu } from "@/lib/api";
import type { KetQuaTuongTu } from "@/lib/kieu";

export const dynamic = "force-dynamic";

const KHONG_LUU = { "cache-control": "no-store" };
const RONG: KetQuaTuongTu = { items: [], enabled: true };

const MA_PHIEN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(yeuCau: Request) {
  const than = (await yeuCau.json().catch(() => null)) as {
    title?: unknown;
    description?: unknown;
    session_id?: unknown;
  } | null;
  const tieuDe = typeof than?.title === "string" ? than.title.slice(0, 300) : "";
  const moTa = typeof than?.description === "string" ? than.description.slice(0, 5000) : "";
  const phien = typeof than?.session_id === "string" && MA_PHIEN.test(than.session_id) ? than.session_id : null;

  const ketQua = await guiDichVu<KetQuaTuongTu>("/similar-cases/search", {
    title: tieuDe,
    description: moTa || null,
    session_id: phien,
  });
  return Response.json(ketQua.ok ? ketQua.duLieu : RONG, { headers: KHONG_LUU });
}
