// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn Hệ thống (#229): tình trạng các dịch vụ của cụm, chỉ cho quản trị viên. Dịch vụ quyết
// ai thấy màn này qua danh sách không gian của `/me` (`system`); người khác mở đường dẫn
// này thì gặp lời báo không vào được của khung, không thấy chữ kỹ thuật nào.

import { KhungLamViec } from "@/components/khung-lam-viec";
import { docSucKhoe, TheHeThong } from "@/components/the-he-thong";
import { goiDichVu } from "@/lib/api";
import type { DangKyWebhook, LanGuiWebhook } from "@/lib/kieu";

import { QuanLyWebhook } from "./quan-ly-webhook";
import { XuatNhatKy } from "./xuat-nhat-ky";

export const dynamic = "force-dynamic";

/** Số lần gửi gần nhất hiện cho mỗi đăng ký webhook (#401). */
const SO_LAN_GUI_HIEN = 5;

/** Đăng ký webhook và vài lần gửi gần nhất của từng cái — `null` khi dịch vụ không trả (#401). */
async function docWebhook(): Promise<{
  dangKy: DangKyWebhook[] | null;
  lanGui: Record<number, LanGuiWebhook[] | null>;
}> {
  const dangKy = await goiDichVu<DangKyWebhook[]>("/core/v1/webhooks");
  const lanGui: Record<number, LanGuiWebhook[] | null> = {};
  await Promise.all(
    (dangKy ?? []).map(async (dk) => {
      const ds = await goiDichVu<LanGuiWebhook[]>(`/core/v1/webhooks/${dk.id}/deliveries`);
      lanGui[dk.id] = ds ? ds.slice(0, SO_LAN_GUI_HIEN) : null;
    }),
  );
  return { dangKy, lanGui };
}

export default async function ManHeThong() {
  const [sucKhoe, webhook] = await Promise.all([docSucKhoe(), docWebhook()]);
  return (
    <KhungLamViec canKhongGian="system">
      <h1 className="tieu-de-trang">Hệ thống</h1>
      <p className="cau-chao">
        Tình trạng các dịch vụ của cụm, đọc từ điểm kiểm tra sức khỏe của dịch vụ ứng dụng.
      </p>
      <div style={{ marginTop: "20px", maxWidth: "720px" }}>
        <TheHeThong sucKhoe={sucKhoe} tieuDe="Các dịch vụ" />
      </div>
      <div style={{ marginTop: "20px", maxWidth: "720px" }}>
        <XuatNhatKy />
      </div>
      <div style={{ marginTop: "20px", maxWidth: "720px" }}>
        <QuanLyWebhook dangKy={webhook.dangKy} lanGui={webhook.lanGui} />
      </div>
    </KhungLamViec>
  );
}
