// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Trang Thông báo (#251): người dùng bật/tắt từng loại thư thông báo của chính mình. Danh sách
// loại đến từ dịch vụ (bảng `notification_types`), cổng không giữ bản sao. Mọi người đăng nhập
// đều vào được — mở từ biểu tượng chuông cạnh tên ở thanh bên.

import { KhungLamViec } from "@/components/khung-lam-viec";
import { goiDichVu } from "@/lib/api";
import type { TuyChonThongBao } from "@/lib/kieu";

import { OThongBao } from "./o-thong-bao";

export const dynamic = "force-dynamic";

export default async function TrangThongBao() {
  const tuyChon = await goiDichVu<TuyChonThongBao>("/me/notifications");
  return (
    <KhungLamViec canKhongGian="portal">
      <h1 className="tieu-de-trang">Thông báo thư</h1>
      <p className="cau-chao">
        Chọn những lúc hệ thống gửi thư cho bạn. Địa chỉ thư là địa chỉ trong tài khoản đăng nhập của bạn.
      </p>
      <div className="the" style={{ marginTop: "20px", maxWidth: "720px", padding: "8px 20px" }}>
        {tuyChon === null ? (
          <p className="nhat">Chưa đọc được tùy chọn thông báo. Thử tải lại trang sau ít phút.</p>
        ) : (
          <>
            {!tuyChon.email_enabled && (
              <p className="nhat" data-thong-bao-tat style={{ padding: "12px 0" }}>
                Hệ thống chưa cấu hình máy chủ thư nên hiện chưa gửi thư nào. Lựa chọn của bạn vẫn được lưu và áp
                dụng khi thư được bật.
              </p>
            )}
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {tuyChon.types.map((t) => (
                <OThongBao key={t.code} ma={t.code} nhan={t.label} moTa={t.description} batSan={t.enabled} />
              ))}
            </ul>
          </>
        )}
      </div>
    </KhungLamViec>
  );
}
