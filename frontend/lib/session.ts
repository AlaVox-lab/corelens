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

import { portalBaseUrl } from "@/lib/oidc";

const TEN_COOKIE = "dxlab_session";
const TEN_COOKIE_TAM = "dxlab_oidc_dang_dang_nhap";

/**
 * Cookie chỉ gắn cờ `Secure` khi cổng thật sự chạy HTTPS.
 *
 * Trước đây cờ này bám theo `NODE_ENV === "production"`, với giả định bản production
 * luôn chạy HTTPS. Giả định đó sai ngay với chính bản dựng Docker của dự án: ảnh chứa
 * chạy ở chế độ production nhưng phục vụ qua `http://localhost:3000`. Cookie mang cờ
 * `Secure` gửi qua HTTP thì Safari — và nhiều trình duyệt nhúng — âm thầm bỏ qua: đăng
 * nhập xong, cookie phiên không được lưu, người dùng bị đưa về trang chủ như chưa từng
 * đăng nhập. Chrome có ngoại lệ riêng cho `localhost` nên lỗi này lọt qua mọi lần thử
 * từ #43 tới #82.
 *
 * Bám theo giao thức của địa chỉ công khai thì đúng ở mọi nơi: triển khai HTTPS thật vẫn
 * có `Secure`, còn cụm dựng thử trên máy vẫn đăng nhập được bằng mọi trình duyệt.
 */
const COOKIE_AN_TOAN = portalBaseUrl.startsWith("https://");

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
//
// PHIÊN NẰM Ở HAI COOKIE, KHÔNG PHẢI MỘT.
//
// Trình duyệt vứt mọi cookie mà tên cộng giá trị vượt 4096 byte — không báo lỗi, không
// cảnh báo, chỉ đơn giản là không lưu. Ba token của Keycloak mã hóa chung vào một
// cookie nặng tới 4227 byte với tài khoản thường, 4311 byte với tài khoản mang nhóm
// phòng ban. Hệ quả: đăng nhập xong, quay về cổng, cổng không thấy cookie nào, người
// dùng bị coi như chưa từng đăng nhập. Lỗi này nằm im từ #43 tới #82 vì mọi lần thử đều
// dùng cookie tự đúc từ loại token nhỏ hơn, chưa lần nào đăng nhập thật qua trình duyệt.
//
// Tách theo tần suất dùng:
//
//   dxlab_session   access token + refresh token — dùng ở MỌI lần gọi dịch vụ
//   dxlab_id_token  id token — chỉ dùng đúng một lần, lúc đăng xuất, để Keycloak đóng
//                   phiên mà không hỏi lại người dùng
//
// Giao diện của ba hàm dưới đây giữ nguyên — nơi gọi vẫn đọc và ghi một `Phien` đủ
// trường. Việc tách hai cookie là chuyện riêng của tệp này.

const TEN_COOKIE_ID = "dxlab_id_token";

/**
 * Trần an toàn cho một cookie. Để dưới 4096 một khoảng, vì một số trình duyệt tính cả
 * thuộc tính vào giới hạn.
 */
const TRAN_COOKIE = 4000;

const SONG_GIAY = 60 * 60 * 12;

async function datCookie(ten: string, du_lieu: object): Promise<void> {
  const gia_tri = await maHoa(du_lieu, SONG_GIAY);

  // Trình duyệt vứt cookie quá khổ mà KHÔNG báo gì. Nên phải tự báo, và báo to: nhật
  // ký của cổng là nơi duy nhất lỗi này có thể lộ ra.
  if (ten.length + 1 + gia_tri.length > TRAN_COOKIE) {
    console.error(
      `[phiên] Cookie ${ten} nặng ${ten.length + 1 + gia_tri.length} byte, vượt trần ` +
        `${TRAN_COOKIE}. Trình duyệt sẽ vứt nó và người dùng không đăng nhập được. ` +
        `Xem chú thích ở lib/session.ts.`,
    );
  }

  const kho = await cookies();
  kho.set(ten, gia_tri, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: COOKIE_AN_TOAN,
    maxAge: SONG_GIAY,
  });
}

export async function luuPhien(phien: Phien): Promise<void> {
  const { idToken, ...conLai } = phien;
  await datCookie(TEN_COOKIE, conLai);
  if (idToken) await datCookie(TEN_COOKIE_ID, { idToken });
}

export async function layPhien(): Promise<Phien | null> {
  const kho = await cookies();
  const cookie = kho.get(TEN_COOKIE);
  if (!cookie) return null;

  const phien = await giaiMa<Phien>(cookie.value);
  if (!phien) return null;

  // Thiếu cookie id token thì phiên vẫn dùng được — chỉ lúc đăng xuất Keycloak sẽ hỏi
  // lại người dùng một câu xác nhận.
  const cookieId = kho.get(TEN_COOKIE_ID);
  const id = cookieId ? await giaiMa<{ idToken?: string }>(cookieId.value) : null;
  return { ...phien, idToken: id?.idToken };
}

export async function xoaPhien(): Promise<void> {
  const kho = await cookies();
  kho.delete(TEN_COOKIE);
  kho.delete(TEN_COOKIE_ID);
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
    secure: COOKIE_AN_TOAN,
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
