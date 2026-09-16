// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Chặng hai của luồng mã ủy quyền: đổi mã lấy token rồi mở phiên.

import * as client from "openid-client";
import { NextResponse, type NextRequest } from "next/server";

import { layCauHinh, portalBaseUrl, redirectUri } from "@/lib/oidc";
import {
  layTrangThaiDangNhap,
  luuPhien,
  xoaTrangThaiDangNhap,
} from "@/lib/session";

export async function GET(request: NextRequest) {
  const trangThai = await layTrangThaiDangNhap();
  if (!trangThai) {
    // Cookie tạm đã hết hạn, hoặc người dùng mở thẳng địa chỉ này. Đẩy về đầu luồng
    // thay vì hiện lỗi — với người dùng thì đây chỉ là "đăng nhập lâu quá".
    return NextResponse.redirect(new URL("/api/auth/login", portalBaseUrl));
  }

  const cauHinh = await layCauHinh();

  // Dựng lại địa chỉ hiện tại từ redirect_uri đã đăng ký thay vì lấy thẳng
  // `request.url`. Trong mạng Compose, địa chỉ mà máy chủ Next.js nhìn thấy có thể
  // khác địa chỉ trình duyệt đã gọi, và thư viện sẽ đối chiếu chúng.
  const diaChiHienTai = new URL(redirectUri);
  diaChiHienTai.search = request.nextUrl.search;

  try {
    const token = await client.authorizationCodeGrant(cauHinh, diaChiHienTai, {
      pkceCodeVerifier: trangThai.codeVerifier,
      expectedState: trangThai.state,
    });

    const conLai = token.expires_in ?? 300;

    await luuPhien({
      accessToken: token.access_token,
      refreshToken: token.refresh_token,
      idToken: token.id_token,
      expiresAt: Math.floor(Date.now() / 1000) + conLai,
    });
  } catch (loi) {
    return NextResponse.json(
      {
        error: "dang-nhap-that-bai",
        detail: loi instanceof Error ? loi.message : String(loi),
      },
      { status: 400 },
    );
  } finally {
    // Dùng một lần rồi bỏ, kể cả khi thất bại. Để lại thì mã ủy quyền cũ còn dùng
    // lại được.
    await xoaTrangThaiDangNhap();
  }

  return NextResponse.redirect(new URL(trangThai.quayVe, portalBaseUrl));
}
