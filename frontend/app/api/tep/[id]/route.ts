// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Tải một tệp đính kèm về (#80).
//
// Đi qua máy chủ Next.js như mọi lời gọi khác: token không tới trình duyệt, và kho tệp không
// mở ra ngoài. Dịch vụ ứng dụng kiểm quyền ở mỗi lần; người không có quyền nhận 404 — mã đó
// được chuyển nguyên, không đổi thành 403.

import { layPhanHoiDichVu } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(
  _yeuCau: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) return new Response("Không tìm thấy tệp.", { status: 404 });

  const phanHoi = await layPhanHoiDichVu(`/attachments/${id}`);
  if (phanHoi === null) {
    return new Response("Phiên đăng nhập đã hết hạn hoặc dịch vụ không trả lời.", {
      status: 401,
    });
  }
  if (!phanHoi.ok) {
    return new Response(phanHoi.status === 404 ? "Không tìm thấy tệp." : "Không tải được tệp.", {
      status: phanHoi.status === 404 ? 404 : 502,
    });
  }

  // Chuyển tiếp đúng các tiêu đề dịch vụ đặt: luôn tải về, không cho trình duyệt tự mở
  const tieuDe = new Headers();
  for (const ten of ["content-type", "content-disposition", "x-content-type-options", "cache-control"]) {
    const giaTri = phanHoi.headers.get(ten);
    if (giaTri) tieuDe.set(ten, giaTri);
  }
  return new Response(phanHoi.body, { status: 200, headers: tieuDe });
}
