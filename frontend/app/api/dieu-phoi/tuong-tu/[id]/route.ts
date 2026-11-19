// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Hồ sơ đã giải quyết tương tự làm căn cứ cho thẻ gợi ý của điều phối viên (#450).
//
// Trình duyệt gọi đây khi thẻ gợi ý hiện. Đi qua máy chủ Next.js như mọi lời gọi khác — token Keycloak không
// tới trình duyệt; dịch vụ ứng dụng kiểm vai điều phối. KHÔNG BAO GIỜ trả lỗi cho thẻ: chưa đăng nhập, không
// đủ vai, dịch vụ hay mô hình nhúng tắt — đều là "tắt", để màn điều phối y như khi chưa có tính năng này.
import { goiDichVu } from "@/lib/api";
import type { KetQuaCanCu } from "@/lib/kieu";

export const dynamic = "force-dynamic";

const TAT: KetQuaCanCu = { items: [], enabled: false };

export async function GET(_yeuCau: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const ketQua = /^\d+$/.test(id) ? await goiDichVu<KetQuaCanCu>(`/similar-cases/for-case/${id}`) : null;
  return Response.json(ketQua ?? TAT, { headers: { "cache-control": "no-store" } });
}
