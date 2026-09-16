// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Gọi dịch vụ ứng dụng kèm token của người đang đăng nhập.
//
// Mọi lời gọi đi qua máy chủ Next.js chứ không đi thẳng từ trình duyệt. Nhờ vậy token
// không bao giờ rời khỏi phía máy chủ, và địa chỉ nội bộ của dịch vụ không lộ ra
// ngoài — xem lib/session.ts.

import * as client from "openid-client";

import { layCauHinh } from "@/lib/oidc";
import { layPhien, luuPhien, type Phien } from "@/lib/session";

const diaChiDichVu =
  process.env.BACKEND_INTERNAL_URL ?? "http://backend:8000";

// Làm mới sớm hơn hạn một chút. Không có khoảng đệm này, một token còn hai giây sẽ
// hết hạn ngay giữa đường truyền và người dùng nhận lỗi 401 vô cớ.
const DEM_TRUOC_GIAY = 30;

async function lamMoiNeuSapHet(phien: Phien): Promise<Phien> {
  const conSong = phien.expiresAt - Math.floor(Date.now() / 1000);
  if (conSong > DEM_TRUOC_GIAY || !phien.refreshToken) {
    return phien;
  }

  try {
    const cauHinh = await layCauHinh();
    const token = await client.refreshTokenGrant(cauHinh, phien.refreshToken);

    const moi: Phien = {
      accessToken: token.access_token,
      // Keycloak xoay cả refresh token theo mặc định, nên phải lưu cái mới. Giữ cái
      // cũ sẽ làm lần làm mới kế tiếp thất bại.
      refreshToken: token.refresh_token ?? phien.refreshToken,
      idToken: token.id_token ?? phien.idToken,
      expiresAt: Math.floor(Date.now() / 1000) + (token.expires_in ?? 300),
    };

    await luuPhien(moi);
    return moi;
  } catch {
    // Refresh token cũng hết hạn. Trả về phiên cũ để lời gọi nhận 401 và giao diện
    // mời đăng nhập lại — đúng hành vi mong muốn.
    return phien;
  }
}

/**
 * Gọi một điểm cuối của dịch vụ ứng dụng.
 *
 * Trả `null` khi chưa đăng nhập hoặc token không còn dùng được, để phía gọi hiển thị
 * lời mời đăng nhập thay vì phải bắt lỗi.
 */
export async function goiDichVu<T>(duongDan: string): Promise<T | null> {
  const phien = await layPhien();
  if (!phien) return null;

  const dungPhien = await lamMoiNeuSapHet(phien);

  try {
    const phanHoi = await fetch(`${diaChiDichVu}${duongDan}`, {
      headers: { Authorization: `Bearer ${dungPhien.accessToken}` },
      cache: "no-store",
    });

    if (!phanHoi.ok) return null;
    return (await phanHoi.json()) as T;
  } catch {
    // Dịch vụ chưa lên hoặc không tới được
    return null;
  }
}

export type DanhTinh = {
  id: string;
  username: string | null;
  name: string | null;
  email: string | null;
  roles: string[];
  departments: string[];
};
