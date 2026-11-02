// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Tải nhật ký sự kiện dạng CSV hay JSON (#306), cho quản trị viên ở màn Hệ thống.
//
// Đi qua máy chủ Next.js như tải tệp đính kèm: token không tới trình duyệt. Dịch vụ ứng dụng
// tự kiểm vai trò; người không phải quản trị viên nhận 403 và mã đó được chuyển nguyên.

import { layPhanHoiDichVu } from "@/lib/api";

export const dynamic = "force-dynamic";

const NGAY = /^\d{4}-\d{2}-\d{2}$/;

export async function GET(yeuCau: Request) {
  const tham = new URL(yeuCau.url).searchParams;
  const dinhDang = tham.get("dinh-dang") === "json" ? "json" : "csv";
  const goi = new URLSearchParams({ format: dinhDang });
  for (const [tuCong, tuDichVu] of [
    ["tu", "from"],
    ["den", "to"],
  ] as const) {
    const ngay = tham.get(tuCong);
    if (!ngay) continue;
    if (!NGAY.test(ngay)) return new Response("Ngày không hợp lệ.", { status: 400 });
    goi.set(tuDichVu, ngay);
  }

  const phanHoi = await layPhanHoiDichVu(`/analytics/event-log?${goi}`);
  if (phanHoi === null) {
    return new Response("Phiên đăng nhập đã hết hạn hoặc hệ thống không phản hồi.", {
      status: 401,
    });
  }
  if (!phanHoi.ok) {
    const thongBao =
      phanHoi.status === 403
        ? "Chỉ quản trị viên tải được nhật ký sự kiện."
        : phanHoi.status === 422
          ? "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc."
          : "Không tải được nhật ký sự kiện.";
    return new Response(thongBao, {
      status: [403, 422].includes(phanHoi.status) ? phanHoi.status : 502,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }

  const tieuDe = new Headers();
  for (const ten of ["content-type", "content-disposition", "cache-control"]) {
    const giaTri = phanHoi.headers.get(ten);
    if (giaTri) tieuDe.set(ten, giaTri);
  }
  return new Response(phanHoi.body, { status: 200, headers: tieuDe });
}
