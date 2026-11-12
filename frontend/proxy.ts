// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Lớp biên của cổng người dùng (#243). Next.js 16 đổi tên `middleware.ts` thành `proxy.ts`.
//
// Hai việc, cả hai cần chạy trước khi trang dựng:
//
// 1. Chính sách nội dung (CSP) kèm số dùng một lần cho MỖI yêu cầu. Số nằm ở header yêu cầu để
//    Next gắn vào script của chính nó; `layout.tsx` đọc `x-nonce` để gắn vào script chống nháy
//    sáng/tối. Vì cần số mới mỗi lượt nên mọi trang phải dựng động — layout gốc đọc header nên
//    đã vậy.
// 2. Giới hạn đăng nhập quay về (`/api/auth/callback`) theo địa chỉ IP, đếm trong bộ nhớ tiến
//    trình — xem `lib/bao-mat.ts`.
//
// Các tiêu đề không đổi theo yêu cầu (nosniff, HSTS, chống nhúng khung, chính sách tham chiếu,
// quyền trình duyệt) đặt tĩnh ở `next.config.ts` để phủ cả tệp tĩnh.

import { NextResponse, type NextRequest } from "next/server";

import { diaChiIp, dungCsp, ghiNhanDangNhap, gocCua, sinhNonce } from "@/lib/bao-mat";

const DUONG_CALLBACK = "/api/auth/callback";

function trangQuaNhieuLan(conLaiGiay: number): NextResponse {
  const html =
    `<!doctype html><html lang="vi"><head><meta charset="utf-8">` +
    `<meta name="viewport" content="width=device-width, initial-scale=1">` +
    `<title>Thử lại sau</title>` +
    `<style>body{font-family:system-ui,sans-serif;max-width:32rem;margin:15vh auto;padding:0 1rem;line-height:1.5}</style>` +
    `</head><body><h1>Đăng nhập quá nhiều lần</h1>` +
    `<p>Có quá nhiều lượt đăng nhập từ địa chỉ của bạn trong thời gian ngắn. ` +
    `Thử lại sau ${conLaiGiay} giây.</p>` +
    `<p><a href="/">Về trang chủ</a></p></body></html>`;
  return new NextResponse(html, {
    status: 429,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Retry-After": String(conLaiGiay),
      "Cache-Control": "no-store",
      // Trang tự dựng, không có script: chính sách chặt nhất vẫn cho kiểu dáng nội tuyến của nó
      "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'",
    },
  });
}

export function proxy(request: NextRequest) {
  if (request.nextUrl.pathname === DUONG_CALLBACK) {
    const ketQua = ghiNhanDangNhap(diaChiIp(request.headers));
    return ketQua.duocPhep ? NextResponse.next() : trangQuaNhieuLan(ketQua.conLaiGiay);
  }

  const nonce = sinhNonce();
  const csp = dungCsp({
    nonce,
    phatTrien: process.env.NODE_ENV === "development",
    gocSuperset: gocCua(process.env.SUPERSET_PUBLIC_URL),
    gocKeycloak: gocCua(process.env.OIDC_ISSUER_PUBLIC),
  });

  const tieuDeYeuCau = new Headers(request.headers);
  // Mã yêu cầu của lượt tải trang (#247): lib/api.ts gửi kèm mọi lời gọi dịch vụ. Luôn sinh mới —
  // không nhận mã trình duyệt gửi lên, để không ai gắn được mã tùy ý vào nhật ký của người khác
  tieuDeYeuCau.set("x-request-id", crypto.randomUUID());
  tieuDeYeuCau.set("x-nonce", nonce);
  // Next đọc số dùng một lần từ CSP của YÊU CẦU để gắn vào script nó sinh ra
  tieuDeYeuCau.set("Content-Security-Policy", csp);

  const phanHoi = NextResponse.next({ request: { headers: tieuDeYeuCau } });
  phanHoi.headers.set("Content-Security-Policy", csp);
  return phanHoi;
}

export const config = {
  matcher: [
    // Callback đăng nhập: chỉ giới hạn tốc độ, không cần CSP. Next đòi chuỗi viết thẳng ở đây,
    // không nhận hằng số — giữ khớp với DUONG_CALLBACK ở trên.
    "/api/auth/callback",
    {
      // Mọi trang, trừ tuyến API, tệp tĩnh và các lượt tải trước (prefetch) của liên kết
      source: "/((?!api|_next/static|_next/image|favicon.ico|icon.svg).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
