// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Phần thuần của lớp bảo mật ở cổng (#243): dựng chính sách nội dung (CSP) và đếm giới hạn đăng nhập.
// `proxy.ts` chỉ nối hai việc này vào yêu cầu; tách ra đây để mỗi việc đọc được một mình.

// ---------------------------------------------------------------------------
// Chính sách nội dung
// ---------------------------------------------------------------------------

type ThamSoCsp = {
  /** Số dùng một lần của yêu cầu này — chỉ script mang đúng số này mới chạy */
  nonce: string;
  /** Chế độ phát triển: React cần `eval` để dựng lại dấu vết lỗi, và Next mở websocket nạp nóng */
  phatTrien: boolean;
  /** Gốc công khai của Superset, nơi duy nhất được nhúng khung. Trống thì cấm mọi khung */
  gocSuperset?: string;
  /** Gốc công khai của Keycloak: luồng OIDC chuyển hướng qua đó */
  gocKeycloak?: string;
};

/** Rút gốc (`https://host:port`) từ một địa chỉ; sai định dạng thì bỏ qua thay vì làm hỏng chính sách. */
export function gocCua(diaChi: string | undefined): string | undefined {
  if (!diaChi) return undefined;
  try {
    return new URL(diaChi).origin;
  } catch {
    return undefined;
  }
}

/**
 * Chính sách nội dung của một yêu cầu trang.
 *
 * - `script-src` đi theo số dùng một lần mỗi lượt + `strict-dynamic`: script nào của Next sinh ra
 *   mang đúng số thì chạy, và nạp được các gói con của nó; script chèn từ ngoài thì không.
 * - `style-src` cho `'unsafe-inline'`: giao diện dùng thuộc tính `style={{…}}` của React ở rất
 *   nhiều chỗ (chiều rộng thanh tiến độ, biến màu theo trạng thái), và CSP không cho phép nối
 *   số dùng một lần vào thuộc tính style. Chấp nhận có chủ đích — rủi ro còn lại là chèn kiểu dáng,
 *   không phải chạy mã — và mọi `script-src` vẫn chặt.
 * - `frame-src` chỉ Superset (mục Báo cáo); `frame-ancestors 'none'` cấm chính cổng bị nhúng.
 * - `form-action` thêm Keycloak vì đăng nhập/đăng xuất chuyển hướng qua đó, và Chrome kiểm
 *   `form-action` cả trên đích chuyển hướng.
 */
export function dungCsp({ nonce, phatTrien, gocSuperset, gocKeycloak }: ThamSoCsp): string {
  const chiThi = [
    `default-src 'self'`,
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${phatTrien ? " 'unsafe-eval'" : ""}`,
    `style-src 'self' 'unsafe-inline'`,
    `img-src 'self' data: blob:`,
    `font-src 'self'`,
    `connect-src 'self'${phatTrien ? " ws: wss:" : ""}`,
    `frame-src ${gocSuperset ?? "'none'"}`,
    `object-src 'none'`,
    `base-uri 'self'`,
    `form-action 'self'${gocKeycloak ? ` ${gocKeycloak}` : ""}`,
    `frame-ancestors 'none'`,
  ];
  return chiThi.join("; ");
}

/** Số dùng một lần: 128 bit ngẫu nhiên, mã hóa base64. */
export function sinhNonce(): string {
  const byte = new Uint8Array(16);
  crypto.getRandomValues(byte);
  return Buffer.from(byte).toString("base64");
}

// ---------------------------------------------------------------------------
// Giới hạn đăng nhập quay về
// ---------------------------------------------------------------------------
//
// Đếm trong BỘ NHỚ tiến trình theo địa chỉ IP, cửa sổ cố định — cùng kiểu với giới hạn ở dịch vụ
// ứng dụng. Khác ở nơi lưu: cổng không chạm cơ sở dữ liệu nên không có bộ đếm chung; chạy nhiều bản
// cổng thì mỗi bản đếm riêng và giới hạn thực tế lỏng hơn theo số bản. Chấp nhận, vì mục đích ở đây
// là chặn vòng lặp thử đổi mã ủy quyền dồn dập, không phải chặn tuyệt đối.

type Cua = { batDau: number; dem: number };

const bangDem = new Map<string, Cua>();
// Quá ngưỡng này thì dọn các cửa sổ đã qua, để bảng không phình vô hạn dưới địa chỉ ngẫu nhiên
const NGUONG_DON_BANG = 5000;

export type KetQuaGioiHan = { duocPhep: boolean; conLaiGiay: number };

function docSo(giaTri: string | undefined, macDinh: number): number {
  const so = Number(giaTri);
  return giaTri !== undefined && giaTri !== "" && Number.isFinite(so) ? so : macDinh;
}

/** Ghi một lượt gọi callback đăng nhập từ `ip`. Số lượt tối đa bằng 0 là tắt giới hạn. */
export function ghiNhanDangNhap(ip: string, luc: number = Date.now()): KetQuaGioiHan {
  const toiDa = docSo(process.env.RATE_LIMIT_LOGIN_MAX, 30);
  const cuaSoMs = Math.max(1, docSo(process.env.RATE_LIMIT_LOGIN_WINDOW_SECONDS, 60)) * 1000;
  if (toiDa <= 0) return { duocPhep: true, conLaiGiay: 0 };

  const batDau = Math.floor(luc / cuaSoMs) * cuaSoMs;
  const hienCo = bangDem.get(ip);
  const cua: Cua = hienCo && hienCo.batDau === batDau ? hienCo : { batDau, dem: 0 };
  cua.dem += 1;
  bangDem.set(ip, cua);

  if (bangDem.size > NGUONG_DON_BANG) {
    for (const [khoa, c] of bangDem) if (c.batDau < batDau) bangDem.delete(khoa);
  }

  return {
    duocPhep: cua.dem <= toiDa,
    conLaiGiay: Math.max(1, Math.ceil((batDau + cuaSoMs - luc) / 1000)),
  };
}

/** Địa chỉ IP của người gọi. Chỉ đáng tin khi cổng đứng sau reverse proxy đặt header này. */
export function diaChiIp(tieuDe: Headers): string {
  const chuyenTiep = tieuDe.get("x-forwarded-for")?.split(",")[0]?.trim();
  return chuyenTiep || tieuDe.get("x-real-ip")?.trim() || "khong-ro";
}
