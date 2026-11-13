"use server";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Sửa một dòng cấu hình (#255). Dịch vụ tự gác quyền quản trị viên và tự kiểm cấu hình sau khi sửa;
// ở đây chỉ chuyển tiếp. `chayThu` đi trọn đường thật rồi hoàn tác, để màn báo trước số hồ sơ đang mở
// bị ảnh hưởng.
//
// Nhớ: tệp mang chỉ thị "use server" chỉ được xuất hàm bất đồng bộ.

import { revalidatePath } from "next/cache";

import { guiDichVu } from "@/lib/api";
import type { KetQuaSuaCauHinh } from "@/lib/kieu";

export async function suaCauHinh(
  danhMuc: string,
  ma: string,
  thayDoi: Record<string, unknown>,
  chayThu: boolean,
): Promise<{ ok: true; ketQua: KetQuaSuaCauHinh } | { ok: false; thongDiep: string }> {
  const kq = await guiDichVu<KetQuaSuaCauHinh>(
    `/admin/config/${encodeURIComponent(danhMuc)}/${encodeURIComponent(ma)}`,
    { changes: thayDoi, dry_run: chayThu },
  );
  if (!kq.ok) return { ok: false, thongDiep: kq.thongDiep };
  if (!chayThu) revalidatePath("/quan-tri/cau-hinh");
  return { ok: true, ketQua: kq.duLieu };
}
