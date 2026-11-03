// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Token khách cho bảng điều khiển nhúng ở mục Báo cáo (#305).
//
// Thư viện nhúng gọi đây lúc mở trang và mỗi lần token sắp hết hạn. Đi qua máy chủ Next.js như
// mọi lời gọi khác: token Keycloak không tới trình duyệt, còn token khách thì phải tới — nó chỉ
// mở đúng một dashboard, trong phạm vi dịch vụ ứng dụng đã gắn, và hết hạn sau vài phút.

import { guiDichVu } from "@/lib/api";
import type { TokenBaoCao } from "@/lib/kieu";

export const dynamic = "force-dynamic";

export async function POST() {
  const ketQua = await guiDichVu<TokenBaoCao>("/analytics/dashboard/guest-token", {});
  if (ketQua.ok) {
    return Response.json(ketQua.duLieu, { headers: { "cache-control": "no-store" } });
  }
  const ma =
    ketQua.ma === "chua-dang-nhap" ? 401 : ketQua.ma === "reports-forbidden" ? 403 : 503;
  return Response.json({ ma: ketQua.ma, thongDiep: ketQua.thongDiep }, { status: ma });
}
