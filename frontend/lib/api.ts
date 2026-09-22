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
  /**
   * Không gian làm việc người này vào được — `portal`, `coordination`. Dịch vụ quyết
   * dựa trên vai trò, để mã giao diện không phải chứa tên vai trò nào cả.
   */
  workspaces: string[];
};

/** Kết quả một lời gọi ghi: hoặc dữ liệu trả về, hoặc lỗi đã dịch sang tiếng người. */
export type KetQua<T> =
  | { ok: true; duLieu: T }
  | { ok: false; ma: string; thongDiep: string };

/** Lỗi khi chưa đăng nhập hoặc phiên đã hết hạn. */
const CHUA_DANG_NHAP = {
  ok: false as const,
  ma: "chua-dang-nhap",
  thongDiep: "Phiên đăng nhập đã hết hạn. Đăng nhập lại để tiếp tục.",
};

/**
 * Đọc mã lỗi máy đọc được từ thân phản hồi.
 *
 * Dịch vụ ứng dụng trả hai dạng khác nhau và phải phân biệt được:
 *
 *   {"detail": {"code": "note-required", "message": "..."}}   ← lỗi nghiệp vụ
 *   {"detail": [{"loc": [...], "msg": "..."}]}                ← Pydantic chặn ở cửa
 *
 * Dạng thứ hai là lỗi lược đồ, nghĩa là giao diện gửi sai hình dạng dữ liệu — một lỗi
 * lập trình chứ không phải lỗi người dùng. Gộp chung hai dạng sẽ khiến lỗi lập trình
 * hiện lên như một lời nhắc bình thường và không ai đi sửa.
 */
async function docLoi(phanHoi: Response): Promise<{ ma: string; thongDiep: string }> {
  try {
    const than = (await phanHoi.json()) as { detail?: unknown };
    const chiTiet = than.detail;

    if (chiTiet && typeof chiTiet === "object" && !Array.isArray(chiTiet)) {
      const o = chiTiet as { code?: string; message?: string };
      if (o.code) {
        return {
          ma: o.code,
          thongDiep: o.message ?? "Thao tác không thực hiện được.",
        };
      }
    }

    if (Array.isArray(chiTiet)) {
      return {
        ma: "du-lieu-khong-hop-le",
        thongDiep: "Dữ liệu gửi lên không đúng định dạng. Kiểm tra lại các ô đã điền.",
      };
    }
  } catch {
    // Phản hồi không phải JSON — rơi xuống thông điệp chung bên dưới
  }

  return {
    ma: `http-${phanHoi.status}`,
    thongDiep: "Dịch vụ ứng dụng không xử lý được yêu cầu này.",
  };
}

/**
 * Gọi một điểm cuối ghi dữ liệu.
 *
 * Khác `goiDichVu` ở chỗ trả về cả lỗi thay vì nuốt thành `null`: khi người dùng bấm
 * một nút và thao tác bị từ chối, họ cần biết vì sao. Mã lỗi (`ma`) là thứ mã nguồn
 * so khớp; thông điệp là thứ người đọc.
 */
export async function guiDichVu<T>(
  duongDan: string,
  than: unknown,
): Promise<KetQua<T>> {
  const phien = await layPhien();
  if (!phien) return CHUA_DANG_NHAP;

  const dungPhien = await lamMoiNeuSapHet(phien);

  let phanHoi: Response;
  try {
    phanHoi = await fetch(`${diaChiDichVu}${duongDan}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${dungPhien.accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(than),
      cache: "no-store",
    });
  } catch {
    return {
      ok: false,
      ma: "khong-ket-noi-duoc",
      thongDiep: "Không kết nối được tới dịch vụ ứng dụng. Thử lại sau ít phút.",
    };
  }

  if (phanHoi.status === 401) return CHUA_DANG_NHAP;
  if (!phanHoi.ok) return { ok: false, ...(await docLoi(phanHoi)) };

  return { ok: true, duLieu: (await phanHoi.json()) as T };
}
