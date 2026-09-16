// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Đăng xuất đồng bộ: đóng phiên ở cổng VÀ kết thúc phiên ở Keycloak.
//
// Chỉ xóa cookie phía cổng là chưa đủ — phiên trình duyệt ở Keycloak vẫn còn, nên
// lần bấm đăng nhập kế tiếp sẽ vào thẳng mà không hỏi mật khẩu. Người dùng tưởng đã
// đăng xuất trong khi chưa. Trên máy dùng chung thì đó là lỗi thật sự.

import * as client from "openid-client";
import { NextResponse, type NextRequest } from "next/server";

import { layCauHinh, portalBaseUrl, postLogoutRedirectUri } from "@/lib/oidc";
import { layPhien, xoaPhien } from "@/lib/session";

export async function GET(request: NextRequest) {
  const phien = await layPhien();
  await xoaPhien();

  if (!phien?.idToken) {
    // Không có phiên thì chẳng có gì để đóng ở Keycloak
    return NextResponse.redirect(new URL("/", portalBaseUrl));
  }

  const cauHinh = await layCauHinh();

  // `id_token_hint` để Keycloak biết đóng phiên của ai, và cũng là thứ cho phép nó
  // chuyển hướng về mà không cần hỏi lại người dùng.
  const diaChi = client.buildEndSessionUrl(cauHinh, {
    post_logout_redirect_uri: postLogoutRedirectUri,
    id_token_hint: phien.idToken,
  });

  return NextResponse.redirect(diaChi.href);
}
