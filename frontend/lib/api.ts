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

  let moi: Phien;
  try {
    const cauHinh = await layCauHinh();
    const token = await client.refreshTokenGrant(cauHinh, phien.refreshToken);

    moi = {
      accessToken: token.access_token,
      // Keycloak gửi kèm refresh token mới, nên lưu cái mới khi lưu được.
      refreshToken: token.refresh_token ?? phien.refreshToken,
      idToken: token.id_token ?? phien.idToken,
      expiresAt: Math.floor(Date.now() / 1000) + (token.expires_in ?? 300),
    };
  } catch {
    // Refresh token cũng hết hạn. Trả về phiên cũ để lời gọi nhận 401 và giao diện
    // mời đăng nhập lại — đúng hành vi mong muốn.
    return phien;
  }

  // Next chỉ cho ghi cookie trong Server Action và Route Handler. Lúc DỰNG TRANG thì
  // ghi là ném lỗi — mà dựng trang lại là lúc hay làm mới nhất. Trước #150 lỗi đó rơi
  // vào cùng khối `catch` với lỗi làm mới, nên token MỚI vừa lấy được bị vứt, lời gọi
  // đi bằng token đã hết hạn và nhận 401: cứ năm phút (hạn access token mặc định của
  // Keycloak) là trang chi tiết hiện "không tìm thấy" một lần.
  //
  // Không lưu được thì vẫn dùng token mới cho lần dựng này. Cookie giữ refresh token
  // cũ, vẫn dùng được vì realm không bật `revokeRefreshToken`, và được thay bằng cái
  // mới ở lần bấm thao tác kế tiếp — thao tác là Server Action, ghi được cookie. Chỉ xem
  // trang mà không bấm gì lâu hơn hạn rỗi của phiên Keycloak (mặc định 30 phút) thì
  // refresh token cũ hết hạn, và trang mời đăng nhập lại như một phiên hết hạn thật.
  try {
    await luuPhien(moi);
  } catch {
    // Đang dựng trang — xem chú thích ngay trên
  }
  return moi;
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
   * Không gian làm việc người này vào được — `portal`, `coordination`, `department`.
   * Dịch vụ quyết dựa trên vai trò, để mã giao diện không phải chứa tên vai trò nào cả.
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
 * Lời gọi hỏng vì phiên — chưa đăng nhập hay token không còn dùng được — chứ không phải
 * vì hồ sơ không có. Trang chi tiết dùng để mời đăng nhập lại thay vì hiện 404 (#150).
 */
export function laHetPhien(ketQua: KetQua<unknown>): boolean {
  return !ketQua.ok && ketQua.ma === CHUA_DANG_NHAP.ma;
}

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

    // Cửa của các buồng lái trả một câu tiếng Việt trần, không kèm mã
    if (typeof chiTiet === "string" && chiTiet) {
      return { ma: `http-${phanHoi.status}`, thongDiep: chiTiet };
    }

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
    thongDiep: "Hệ thống không xử lý được yêu cầu này.",
  };
}

/**
 * Đọc một điểm cuối, giữ lại lý do khi hỏng.
 *
 * `goiDichVu` nuốt mọi lỗi thành `null` — đủ cho trang, vì trang chỉ cần biết có dữ
 * liệu hay không. Hàm này dành cho chỗ mà LÝ DO hỏng cần tới tay người dùng: ô chọn
 * người xử lý phải nói được "danh bạ không trả lời", khác với "phòng không có ai".
 */
export async function docDichVu<T>(duongDan: string): Promise<KetQua<T>> {
  const phien = await layPhien();
  if (!phien) return CHUA_DANG_NHAP;

  const dungPhien = await lamMoiNeuSapHet(phien);

  let phanHoi: Response;
  try {
    phanHoi = await fetch(`${diaChiDichVu}${duongDan}`, {
      headers: { Authorization: `Bearer ${dungPhien.accessToken}` },
      cache: "no-store",
    });
  } catch {
    return {
      ok: false,
      ma: "khong-ket-noi-duoc",
      thongDiep: "Hệ thống không phản hồi. Thử lại sau ít phút.",
    };
  }

  if (phanHoi.status === 401) return CHUA_DANG_NHAP;
  if (!phanHoi.ok) return { ok: false, ...(await docLoi(phanHoi)) };

  return { ok: true, duLieu: (await phanHoi.json()) as T };
}

/**
 * Lấy nguyên phản hồi nhị phân của một điểm cuối — tải tệp đính kèm (#80). Trả `null` khi
 * chưa đăng nhập hoặc dịch vụ không tới được; phản hồi lỗi (404…) trả nguyên để phía gọi
 * chuyển tiếp đúng mã.
 */
export async function layPhanHoiDichVu(duongDan: string): Promise<Response | null> {
  const phien = await layPhien();
  if (!phien) return null;

  const dungPhien = await lamMoiNeuSapHet(phien);
  try {
    return await fetch(`${diaChiDichVu}${duongDan}`, {
      headers: { Authorization: `Bearer ${dungPhien.accessToken}` },
      cache: "no-store",
    });
  } catch {
    return null;
  }
}

/**
 * Gửi một biểu mẫu nhiều phần (tải tệp lên, #80). Không đặt `Content-Type`: để `fetch` tự
 * đặt kèm ranh giới giữa các phần.
 */
export async function guiBieuMauDichVu<T>(
  duongDan: string,
  bieuMau: FormData,
): Promise<KetQua<T>> {
  const phien = await layPhien();
  if (!phien) return CHUA_DANG_NHAP;

  const dungPhien = await lamMoiNeuSapHet(phien);

  let phanHoi: Response;
  try {
    phanHoi = await fetch(`${diaChiDichVu}${duongDan}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${dungPhien.accessToken}` },
      body: bieuMau,
      cache: "no-store",
    });
  } catch {
    return {
      ok: false,
      ma: "khong-ket-noi-duoc",
      thongDiep: "Hệ thống không phản hồi. Thử lại sau ít phút.",
    };
  }

  if (phanHoi.status === 401) return CHUA_DANG_NHAP;
  if (!phanHoi.ok) return { ok: false, ...(await docLoi(phanHoi)) };
  return { ok: true, duLieu: (await phanHoi.json()) as T };
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
      thongDiep: "Hệ thống không phản hồi. Thử lại sau ít phút.",
    };
  }

  if (phanHoi.status === 401) return CHUA_DANG_NHAP;
  if (!phanHoi.ok) return { ok: false, ...(await docLoi(phanHoi)) };
  // 204: thao tác thành công mà không trả gì — như đánh dấu đã đọc (#155)
  if (phanHoi.status === 204) return { ok: true, duLieu: undefined as T };

  return { ok: true, duLieu: (await phanHoi.json()) as T };
}
