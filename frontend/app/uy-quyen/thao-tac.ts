"use server";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khai và thu hồi ủy quyền (#252). Dịch vụ tự kiểm ai được khai cho ai, vai nào, khoảng ngày nào;
// ở đây chỉ chuyển tiếp và làm mới trang.
//
// Nhớ: tệp mang chỉ thị "use server" chỉ được xuất hàm bất đồng bộ.

import { revalidatePath } from "next/cache";

import { guiDichVu } from "@/lib/api";

export async function khaiUyQuyen(than: {
  delegate_id: string;
  starts_on: string;
  ends_on: string;
  delegator_id: string | null;
}): Promise<{ ok: boolean; thongDiep?: string }> {
  const kq = await guiDichVu<unknown>("/delegations", than);
  if (!kq.ok) return { ok: false, thongDiep: kq.thongDiep };
  revalidatePath("/uy-quyen");
  return { ok: true };
}

export async function thuHoiUyQuyen(ma: number): Promise<{ ok: boolean; thongDiep?: string }> {
  const kq = await guiDichVu<unknown>(`/delegations/${ma}/revoke`, {});
  if (!kq.ok) return { ok: false, thongDiep: kq.thongDiep };
  revalidatePath("/uy-quyen");
  return { ok: true };
}
