// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Chặng một của luồng mã ủy quyền: đẩy người dùng sang Keycloak.

import * as client from "openid-client";
import { NextResponse, type NextRequest } from "next/server";

import { layCauHinh, redirectUri } from "@/lib/oidc";
import { chuoiNgauNhien, luuTrangThaiDangNhap } from "@/lib/session";

/**
 * Chỉ nhận đường dẫn nội bộ làm chỗ quay về.
 *
 * Không có phép lọc này thì `/api/auth/login?quay_ve=https://trang-lua-dao` biến cổng
 * đăng nhập của chính mình thành bàn đạp chuyển hướng cho kẻ tấn công.
 */
function locDuongDanQuayVe(tho: string | null): string {
  if (!tho) return "/";
  if (!tho.startsWith("/") || tho.startsWith("//")) return "/";
  return tho;
}

export async function GET(request: NextRequest) {
  const cauHinh = await layCauHinh();

  // PKCE: chặn kẻ chặn được mã ủy quyền đem đi đổi lấy token. Bắt buộc ngay cả với
  // client bí mật, vì nó bảo vệ đúng đoạn mã đi qua trình duyệt.
  const codeVerifier = client.randomPKCECodeVerifier();
  const codeChallenge = await client.calculatePKCECodeChallenge(codeVerifier);

  // `state` chống giả mạo yêu cầu liên trang trên chính luồng đăng nhập
  const state = chuoiNgauNhien();

  await luuTrangThaiDangNhap({
    state,
    codeVerifier,
    quayVe: locDuongDanQuayVe(request.nextUrl.searchParams.get("quay_ve")),
  });

  const diaChi = client.buildAuthorizationUrl(cauHinh, {
    redirect_uri: redirectUri,
    scope: "openid profile email",
    code_challenge: codeChallenge,
    code_challenge_method: "S256",
    state,
  });

  return NextResponse.redirect(diaChi.href);
}
