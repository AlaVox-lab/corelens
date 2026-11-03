// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Mục Báo cáo (#305): bảng điều khiển phân tích nhúng, không đăng nhập lần hai. Dịch vụ quyết ai
// thấy mục này qua danh sách không gian của `/me` (`reports`, tra cột `roles.report_scope`);
// người khác mở thẳng đường dẫn thì gặp lời báo không vào được của khung, và điểm cuối cấp token
// cũng tự từ chối.

import { BangDieuKhienNhung } from "@/components/bang-dieu-khien-nhung";
import { KhungLamViec } from "@/components/khung-lam-viec";

export const dynamic = "force-dynamic";

export default function ManBaoCao() {
  return (
    <KhungLamViec canKhongGian="reports">
      <h1 className="tieu-de-trang">Báo cáo</h1>
      <p className="cau-chao">
        Tồn đọng theo phòng ban, thời gian xử lý, tỷ lệ trễ hạn và các loại yêu cầu — tính từ nhật
        ký sự kiện, cập nhật theo từng thao tác trên hồ sơ.
      </p>
      <BangDieuKhienNhung />
    </KhungLamViec>
  );
}
