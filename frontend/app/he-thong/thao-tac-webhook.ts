"use server";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Đăng ký và hủy webhook từ màn Hệ thống (#401). Chỉ chuyển tiếp tới API lõi `/core/v1/webhooks` (#390);
// dịch vụ tự gác quyền quản trị viên và tự kiểm địa chỉ, bộ lọc. Bí mật ký trả về đúng một lần, ở kết quả
// của `taoWebhook` — không lưu ở đâu phía cổng.
//
// Nhớ: tệp mang chỉ thị "use server" chỉ được xuất hàm bất đồng bộ.

import { revalidatePath } from "next/cache";

import { guiDichVu } from "@/lib/api";
import type { DangKyWebhookMoi } from "@/lib/kieu";

const DUONG_WEBHOOK = "/core/v1/webhooks";

export async function taoWebhook(
  url: string,
  moTa: string,
  hoatDong: string,
): Promise<{ ok: true; dangKy: DangKyWebhookMoi } | { ok: false; thongDiep: string }> {
  // Mã hoạt động gõ cách nhau bởi dấu phẩy hay khoảng trắng; bỏ trống là nhận mọi hoạt động
  const cacMa = hoatDong
    .split(/[\s,]+/)
    .map((m) => m.trim())
    .filter(Boolean);
  const kq = await guiDichVu<DangKyWebhookMoi>(DUONG_WEBHOOK, {
    url: url.trim(),
    description: moTa.trim() || null,
    activities: cacMa.length ? cacMa : null,
  });
  if (!kq.ok) return { ok: false, thongDiep: kq.thongDiep };
  revalidatePath("/he-thong");
  return { ok: true, dangKy: kq.duLieu };
}

export async function huyWebhook(ma: number): Promise<{ ok: true } | { ok: false; thongDiep: string }> {
  const kq = await guiDichVu<undefined>(`${DUONG_WEBHOOK}/${encodeURIComponent(ma)}`, undefined, "DELETE");
  if (!kq.ok) return { ok: false, thongDiep: kq.thongDiep };
  revalidatePath("/he-thong");
  return { ok: true };
}
