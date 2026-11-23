// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Đọc nhật ký truy cập dữ liệu cá nhân cho khối trên màn Hệ thống (#431), ở máy chủ: bộ lọc và trang nằm trên địa
// chỉ (`?ho-so=`, `?nguoi=`, `?loai=`, `?tu=`, `?den=`, `?trang=`) như mọi danh sách khác của cổng (`lib/trang.ts`);
// dịch vụ lọc, đếm và cắt trang.

import { goiDichVu, type DanhTinh } from "@/lib/api";
import { dauNgayUtc } from "@/lib/dinh-dang";
import type { DanhSachTruyCap, NhanCoMa } from "@/lib/kieu";
import { chipLoc, docThamSo, duongTrang, nhanCua, soTrang, SO_DONG, type ThamSo } from "@/lib/trang";

export const DUONG_HE_THONG = "/he-thong";

export type LocTruyCap = { hoSo: string; nguoi: string; loai: string; tu: string; den: string };

export type DuLieuTruyCap = {
  /** `null` khi dịch vụ không trả. */
  ds: DanhSachTruyCap | null;
  loai: NhanCoMa[];
  loc: LocTruyCap;
  coLoc: boolean;
  /** Người đang xem mở được buồng lái điều phối: mã hồ sơ thành liên kết tới hồ sơ. */
  moDuocHoSo: boolean;
  truoc: string | null;
  sau: string | null;
  chip: { nhan: string; bo: string }[];
  xoaHet: string | null;
  /** Địa chỉ đang xem — nút Thử lại tải lại đúng nó. */
  hienTai: string;
};

/** "YC-2026-0184" hay "184" → 184: phần số cuối là định danh, như ô tìm của hàng đợi. */
function maHoSo(chu: string): number | null {
  const so = chu.match(/\d+/g);
  const n = so ? Number.parseInt(so[so.length - 1], 10) : NaN;
  return Number.isFinite(n) && n > 0 ? n : null;
}

export async function docTruyCap(sp: ThamSo): Promise<DuLieuTruyCap> {
  const loc: LocTruyCap = {
    hoSo: docThamSo(sp, "ho-so") ?? "",
    nguoi: docThamSo(sp, "nguoi") ?? "",
    loai: docThamSo(sp, "loai") ?? "",
    tu: docThamSo(sp, "tu") ?? "",
    den: docThamSo(sp, "den") ?? "",
  };
  const trang = soTrang(sp);
  const q = new URLSearchParams({ limit: String(SO_DONG), offset: String((trang - 1) * SO_DONG) });
  const ma = maHoSo(loc.hoSo);
  if (ma) q.set("case_id", String(ma));
  if (loc.nguoi.trim()) q.set("actor", loc.nguoi.trim());
  if (loc.loai) q.set("access_kind", loc.loai);
  const tu = dauNgayUtc(loc.tu);
  if (tu) q.set("from", tu);
  const den = dauNgayUtc(loc.den, 1);
  if (den) q.set("to", den);

  const [ds, loai, danhTinh] = await Promise.all([
    goiDichVu<DanhSachTruyCap>(`/admin/access-audit?${q}`),
    goiDichVu<NhanCoMa[]>("/admin/access-audit/kinds"),
    goiDichVu<DanhTinh>("/me"),
  ]);

  const { chip, xoaHet } = chipLoc(DUONG_HE_THONG, sp, {
    "ho-so": (gt) => `Hồ sơ: ${gt}`,
    nguoi: (gt) => `Người: ${gt}`,
    loai: (gt) => nhanCua(loai, gt),
    tu: (gt) => `Từ ${gt.split("-").reverse().join("/")}`,
    den: (gt) => `Đến hết ${gt.split("-").reverse().join("/")}`,
  });
  const soTrangCuoi = ds ? Math.max(1, Math.ceil(ds.total / SO_DONG)) : 1;
  return {
    ds,
    loai: loai ?? [],
    loc,
    coLoc: chip.length > 0,
    moDuocHoSo: (danhTinh?.workspaces ?? []).includes("coordination"),
    truoc: trang > 1 ? duongTrang(DUONG_HE_THONG, sp, trang - 1) : null,
    sau: ds && trang < soTrangCuoi ? duongTrang(DUONG_HE_THONG, sp, trang + 1) : null,
    chip,
    xoaHet,
    hienTai: duongTrang(DUONG_HE_THONG, sp, trang),
  };
}
