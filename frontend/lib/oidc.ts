// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Cấu hình OIDC cho cổng người dùng.
//
// Dùng `openid-client` — bản cài đặt được OpenID Foundation chứng nhận, giấy phép MIT.
// Giao thức thì lắp ghép thư viện chuẩn, còn luồng và giao diện thì tự viết, đúng
// phân định ở CLAUDE.md mục 3.2. Không nhúng thư viện riêng của Keycloak, không phụ
// thuộc API riêng của nền tảng — xem ADR-0001.

import * as client from "openid-client";

const issuerNoiBo = process.env.OIDC_ISSUER_INTERNAL ?? "";
const clientId = process.env.OIDC_CLIENT_ID ?? "";
const clientSecret = process.env.OIDC_CLIENT_SECRET ?? "";

export const redirectUri =
  process.env.OIDC_REDIRECT_URI ?? "http://localhost:3000/api/auth/callback";
export const postLogoutRedirectUri =
  process.env.OIDC_POST_LOGOUT_REDIRECT_URI ?? "http://localhost:3000";

/**
 * Địa chỉ gốc mà TRÌNH DUYỆT nhìn thấy cổng người dùng.
 *
 * Bắt buộc phải khai riêng, không được suy ra từ `request.url`: trong container,
 * máy chủ Next.js nghe ở `0.0.0.0:3000`, nên `new URL("/", request.url)` cho ra
 * `http://0.0.0.0:3000/` và trình duyệt đi tới đó sẽ lạc.
 *
 * Cùng một gốc vấn đề với chuyện Keycloak phải cố định `KC_HOSTNAME`: địa chỉ bên
 * trong mạng Compose và địa chỉ bên ngoài là hai thứ khác nhau, và mã nguồn không
 * được lẫn lộn chúng.
 */
export const portalBaseUrl =
  process.env.PORTAL_PUBLIC_URL ?? postLogoutRedirectUri;

let bo_nho_dem: client.Configuration | null = null;

/**
 * Cấu hình OIDC, tải một lần rồi giữ lại cho cả vòng đời tiến trình.
 *
 * Vì sao TỰ tải tài liệu discovery thay vì gọi `client.discovery()`:
 *
 * Keycloak công bố `issuer` là địa chỉ CÔNG KHAI (`http://localhost:8080/...`) vì đó
 * là địa chỉ trình duyệt nhìn thấy, trong khi máy chủ Next.js phải đọc tài liệu qua
 * địa chỉ NỘI BỘ (`http://keycloak:8080/...`). Hàm `discovery()` kiểm rằng `issuer`
 * đọc được phải khớp URL đã gọi, nên nó sẽ báo lỗi với cặp địa chỉ lệch nhau này.
 *
 * Dựng `Configuration` thẳng từ siêu dữ liệu tránh được phép kiểm đó mà không mất gì:
 * Keycloak đã tự trả đúng chiều cho từng điểm cuối — `authorization_endpoint` và
 * `end_session_endpoint` là địa chỉ công khai cho trình duyệt, còn `token_endpoint`
 * và `jwks_uri` là địa chỉ nội bộ cho máy chủ.
 */
export async function layCauHinh(): Promise<client.Configuration> {
  if (bo_nho_dem) return bo_nho_dem;

  if (!issuerNoiBo || !clientId || !clientSecret) {
    throw new Error(
      "Thiếu cấu hình OIDC. Cần OIDC_ISSUER_INTERNAL, OIDC_CLIENT_ID và " +
        "OIDC_CLIENT_SECRET — xem infra/.env.example.",
    );
  }

  const phanHoi = await fetch(
    `${issuerNoiBo}/.well-known/openid-configuration`,
    { cache: "no-store" },
  );
  if (!phanHoi.ok) {
    throw new Error(
      `Không đọc được tài liệu discovery của Keycloak (HTTP ${phanHoi.status}). ` +
        `Kiểm tra dịch vụ keycloak đã lên chưa.`,
    );
  }

  const sieuDuLieu = (await phanHoi.json()) as client.ServerMetadata;

  const cauHinh = new client.Configuration(sieuDuLieu, clientId, clientSecret);

  // Môi trường phát triển chạy HTTP thuần. Thư viện mặc định từ chối mọi thứ không
  // phải HTTPS, và từ chối như vậy là đúng — bản triển khai thật bắt buộc dùng HTTPS
  // và phải bỏ dòng này đi.
  client.allowInsecureRequests(cauHinh);

  bo_nho_dem = cauHinh;
  return cauHinh;
}
