// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Phiên đăng nhập của cổng người dùng.
//
// Token KHÔNG BAO GIỜ tới trình duyệt dưới dạng đọc được. Chúng nằm trong một cookie
// `httpOnly` đã mã hóa, và mã JavaScript phía trình duyệt không chạm tới được. Mọi
// lần gọi dịch vụ ứng dụng đều đi qua máy chủ Next.js, nơi giải mã cookie rồi gắn
// token vào header — đây là khuôn mẫu cổng chặn trước (backend for frontend).
//
// Vì sao không để token trong localStorage: bất kỳ đoạn mã lạ nào lọt vào trang cũng
// đọc được localStorage. Cookie `httpOnly` thì không.

import { cookies } from "next/headers";
import { EncryptJWT, jwtDecrypt, base64url } from "jose";

const TEN_COOKIE = "dxlab_session";
const TEN_COOKIE_TAM = "dxlab_oidc_dang_dang_nhap";

export type Phien = {
  accessToken: string;
  refreshToken?: string;
  idToken?: string;
  /** Mốc hết hạn của access token, tính bằng giây kể từ epoch. */
  expiresAt: number;
};

export type TrangThaiDangNhap = {
  state: string;
  codeVerifier: string;
  /** Đường dẫn muốn quay lại sau khi đăng nhập xong. */
  quayVe: string;
};

/**
 * Khóa mã hóa cookie, dẫn xuất từ biến môi trường.
 *
 * Bí mật phải dài ít nhất 32 byte sau khi giải mã. Cắt hoặc đệm cho đủ sẽ làm khóa
 * yếu đi một cách âm thầm, nên thà báo lỗi ngay lúc khởi động.
 */
function layKhoa(): Uint8Array {
  const biMat = process.env.PORTAL_SESSION_SECRET ?? "";
  const byte = new TextEncoder().encode(biMat);
  if (byte.length < 32) {
    throw new Error(
      "PORTAL_SESSION_SECRET phải dài ít nhất 32 ký tự. " +
        "Sinh bằng: openssl rand -base64 32",
    );
  }
  return byte.slice(0, 32);
}

async function maHoa(du_lieu: object, songGiay: number): Promise<string> {
  return await new EncryptJWT(du_lieu as Record<string, unknown>)
    .setProtectedHeader({ alg: "dir", enc: "A256GCM" })
    .setIssuedAt()
    .setExpirationTime(`${songGiay}s`)
    .encrypt(layKhoa());
}

async function giaiMa<T>(chuoi: string): Promise<T | null> {
  try {
    const { payload } = await jwtDecrypt(chuoi, layKhoa());
    return payload as T;
  } catch {
    // Cookie hỏng, hết hạn, hoặc ký bằng khóa cũ. Coi như chưa đăng nhập.
    return null;
  }
}

// --- Phiên đăng nhập -------------------------------------------------------

export async function luuPhien(phien: Phien): Promise<void> {
  const kho = await cookies();
  kho.set(TEN_COOKIE, await maHoa(phien, 60 * 60 * 12), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    // Bản triển khai thật chạy HTTPS thì bật `secure`. Môi trường phát triển chạy
    // HTTP thuần nên bật ở đây sẽ làm trình duyệt bỏ qua cookie.
    secure: process.env.NODE_ENV === "production",
    maxAge: 60 * 60 * 12,
  });
}

export async function layPhien(): Promise<Phien | null> {
  const kho = await cookies();
  const cookie = kho.get(TEN_COOKIE);
  if (!cookie) return null;
  return await giaiMa<Phien>(cookie.value);
}

export async function xoaPhien(): Promise<void> {
  const kho = await cookies();
  kho.delete(TEN_COOKIE);
}

// --- Trạng thái tạm giữa hai chặng của luồng đăng nhập ---------------------

export async function luuTrangThaiDangNhap(
  trangThai: TrangThaiDangNhap,
): Promise<void> {
  const kho = await cookies();
  // Sống ngắn: người dùng có mười phút để đăng nhập xong. Để lâu hơn thì một liên
  // kết đăng nhập cũ còn dùng lại được, mở đường cho tấn công cố định phiên.
  kho.set(TEN_COOKIE_TAM, await maHoa(trangThai, 600), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
    maxAge: 600,
  });
}

export async function layTrangThaiDangNhap(): Promise<TrangThaiDangNhap | null> {
  const kho = await cookies();
  const cookie = kho.get(TEN_COOKIE_TAM);
  if (!cookie) return null;
  return await giaiMa<TrangThaiDangNhap>(cookie.value);
}

export async function xoaTrangThaiDangNhap(): Promise<void> {
  const kho = await cookies();
  kho.delete(TEN_COOKIE_TAM);
}

/** Sinh chuỗi ngẫu nhiên an toàn, dùng cho tham số `state`. */
export function chuoiNgauNhien(soByte = 32): string {
  const byte = new Uint8Array(soByte);
  crypto.getRandomValues(byte);
  return base64url.encode(byte);
}
