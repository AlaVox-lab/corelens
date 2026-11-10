// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khoảng ngày của màn quy trình thực tế (#315): mặc định, các nút nhanh, đọc từ địa chỉ trang.
//
// Ngày tính theo giờ Việt Nam, cùng múi giờ mà dịch vụ khai phá dùng để cắt ngày (múi giờ của lịch
// làm việc mặc định): người mở trang lúc 23:30 giờ Việt Nam vẫn thấy "hôm nay" là ngày của mình, không
// phải ngày UTC. Mọi hàm nhận mốc hiện tại làm tham số để cùng một lần dựng dùng đúng một mốc.

import { khoaNgay } from "@/lib/dinh-dang";

/** Khoảng ngày dạng `YYYY-MM-DD`, tính cả hai đầu — đúng khóa `from`, `to` của dịch vụ. */
export type KhoangNgay = { tu: string; den: string };

/** Số ngày mặc định của khoảng xem, tính cả hôm nay. */
export const SO_NGAY_MAC_DINH = 90;

/**
 * Các nút chọn nhanh. "12 tháng" là 365 ngày tính cả hôm nay: dịch vụ chặn từ 366 ngày trở lên, nên
 * 365 là khoảng dài nhất chọn được bằng nút.
 */
export const NUT_NHANH: readonly { nhan: string; soNgay: number }[] = [
  { nhan: "30 ngày", soNgay: 30 },
  { nhan: "90 ngày", soNgay: 90 },
  { nhan: "12 tháng", soNgay: 365 },
];

const MOT_NGAY_MS = 86_400_000;

/** Chuỗi `YYYY-MM-DD` thành mốc nửa đêm UTC; `null` khi không phải ngày có thật (không có 31/02). */
function mocNgay(chuoi: string): number | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(chuoi)) return null;
  const moc = Date.parse(`${chuoi}T00:00:00Z`);
  if (Number.isNaN(moc)) return null;
  return new Date(moc).toISOString().slice(0, 10) === chuoi ? moc : null;
}

const NGAY_ISO = (moc: number) => new Date(moc).toISOString().slice(0, 10);

/** Ngày hợp lệ thì trả nguyên chuỗi, không thì `null`. */
export function docNgay(chuoi: string | undefined | null): string | null {
  return chuoi && mocNgay(chuoi) !== null ? chuoi : null;
}

/** Lùi `soNgay` ngày từ `ngay`. */
export function luiNgay(ngay: string, soNgay: number): string {
  return NGAY_ISO((mocNgay(ngay) ?? 0) - soNgay * MOT_NGAY_MS);
}

/** Khoảng `soNgay` ngày gần nhất, tới hôm nay và gồm cả hôm nay. */
export function khoangGanNhat(soNgay: number, bayGio: Date): KhoangNgay {
  const homNay = khoaNgay(bayGio.toISOString());
  return { tu: luiNgay(homNay, soNgay - 1), den: homNay };
}

/**
 * Khoảng ngày từ địa chỉ trang. Thiếu hay sai định dạng một đầu thì dùng khoảng mặc định — gõ tay địa
 * chỉ sai không được làm hỏng trang. Khoảng đúng định dạng nhưng sai về nghĩa (đảo đầu, quá dài) thì
 * giữ nguyên để dịch vụ báo 422, người xem thấy lời báo ngay dưới ô ngày.
 */
export function khoangTuDiaChi(tu: string | undefined, den: string | undefined, bayGio: Date): KhoangNgay {
  const t = docNgay(tu);
  const d = docNgay(den);
  return t && d ? { tu: t, den: d } : khoangGanNhat(SO_NGAY_MAC_DINH, bayGio);
}

/** Số ngày của khoảng, tính cả hai đầu; `null` khi một đầu không phải ngày. */
export function soNgayCua(khoang: KhoangNgay): number | null {
  const t = mocNgay(khoang.tu);
  const d = mocNgay(khoang.den);
  return t === null || d === null ? null : Math.round((d - t) / MOT_NGAY_MS) + 1;
}

/** `2026-08-13` → `13/08/2026`. */
export function ngayVietNam(ngay: string): string {
  const [nam, thang, ngayTrongThang] = ngay.split("-");
  return `${ngayTrongThang}/${thang}/${nam}`;
}
