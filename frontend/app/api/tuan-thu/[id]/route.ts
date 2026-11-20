// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Bước lệch quy trình của một hồ sơ (#448), cho khối chỉ đọc trên trang hồ sơ phía nhân viên.
//
// Trình duyệt gọi đây sau khi trang đã hiện. Đi qua máy chủ Next.js như mọi lời gọi khác — token Keycloak
// không tới trình duyệt; dịch vụ ứng dụng kiểm luật xem hồ sơ. KHÔNG BAO GIỜ trả lỗi cho khối: chưa đăng
// nhập, vai người gửi (403), hồ sơ ngoài phạm vi, dịch vụ khai phá tắt hay hỏng — đều là "không có", để
// trang hồ sơ y như khi chưa có tính năng này.
import { goiDichVu } from "@/lib/api";
import type { KetQuaTuanThu } from "@/lib/kieu";

export const dynamic = "force-dynamic";

export async function GET(_yeuCau: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const khongCo: KetQuaTuanThu = { status: "unavailable", case_id: Number(id) || 0, deviates: false, steps: [] };
  const ketQua = /^\d+$/.test(id)
    ? await goiDichVu<KetQuaTuanThu>(`/analytics/process-mining/cases/${id}`)
    : null;
  return Response.json(ketQua ?? khongCo, { headers: { "cache-control": "no-store" } });
}
