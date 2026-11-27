// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn Hệ thống (#229): tình trạng các dịch vụ của cụm, chỉ cho quản trị viên; từ #431 thêm nhật ký truy cập dữ
// liệu cá nhân (lọc và trang trên địa chỉ, `doc-truy-cap.ts`). Dịch vụ quyết
// ai thấy màn này qua danh sách không gian của `/me` (`system`); người khác mở đường dẫn
// này thì gặp lời báo không vào được của khung, không thấy chữ kỹ thuật nào.
//
// Bố cục (#561): lưới `.luoi-he-thong` trong `globals.css` thay các bề rộng viết thẳng trước đây.

import { KhungLamViec } from "@/components/khung-lam-viec";
import { docSucKhoe, TheHeThong } from "@/components/the-he-thong";
import { goiDichVu } from "@/lib/api";
import type { DangKyWebhook, LanGuiWebhook } from "@/lib/kieu";
import type { ThamSo } from "@/lib/trang";

import { docTruyCap } from "./doc-truy-cap";
import { NhatKyTruyCap } from "./nhat-ky-truy-cap";
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

export default async function ManHeThong({ searchParams }: { searchParams: Promise<ThamSo> }) {
  const sp = await searchParams;
  const [sucKhoe, webhook, truyCap] = await Promise.all([docSucKhoe(), docWebhook(), docTruyCap(sp)]);
  return (
    <KhungLamViec canKhongGian="system">
      <h1 className="tieu-de-trang">Hệ thống</h1>
      <p className="cau-chao">
        Tình trạng các dịch vụ của cụm, đọc từ điểm kiểm tra sức khỏe của dịch vụ ứng dụng.
      </p>
      {/* Lưới hai cột (#561): dịch vụ bên trái, xuất nhật ký và webhook bên phải; bảng nhật ký truy cập sáu cột
          trải hết bề rộng bên dưới. Màn hẹp về một cột theo đúng thứ tự trong mã */}
      <div className="luoi-he-thong">
        <TheHeThong sucKhoe={sucKhoe} tieuDe="Các dịch vụ" />
        <div className="cot-tong-quan">
          <XuatNhatKy />
          <QuanLyWebhook dangKy={webhook.dangKy} lanGui={webhook.lanGui} />
        </div>
        <div className="trai-het">
          <NhatKyTruyCap duLieu={truyCap} />
        </div>
      </div>
    </KhungLamViec>
  );
}
