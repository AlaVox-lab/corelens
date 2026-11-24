// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Báo cáo → Quy trình thực tế (#315): quy trình đang thật sự chạy, khai phá từ nhật ký sự kiện (#314),
// đối chiếu với quy trình thiết kế. Cùng cửa với bảng điều khiển (#305): không gian `reports` do dịch
// vụ quyết qua vai trò, và điểm cuối cũng tự từ chối người không được xem.
//
// Khoảng ngày đọc từ địa chỉ (`?tu=YYYY-MM-DD&den=YYYY-MM-DD`), mặc định 90 ngày gần nhất. Trang này
// không tải khung Superset — đó là việc của trang bảng điều khiển.

import { KhungLamViec } from "@/components/khung-lam-viec";
import { TenCapCon } from "@/components/khung-ung-dung";
import { QuyTrinhThucTe } from "@/components/quy-trinh-thuc-te";
import { ThanhBaoCao } from "@/components/thanh-bao-cao";
import { goiDichVu, type DanhTinh } from "@/lib/api";
import { khoangTuDiaChi } from "@/lib/khoang-ngay";

export const dynamic = "force-dynamic";

export default async function ManQuyTrinhThucTe({
  searchParams,
}: Readonly<{ searchParams: Promise<{ tu?: string; den?: string }> }>) {
  const { tu, den } = await searchParams;
  // Mã hồ sơ trên màn dẫn tới buồng lái nào tùy không gian người xem vào được
  const danhTinh = await goiDichVu<DanhTinh>("/me");

  return (
    <KhungLamViec canKhongGian="reports">
      <TenCapCon ten="Quy trình thực tế" chuThuong />
      <h1 className="tieu-de-trang">Báo cáo</h1>
      <p className="cau-chao">
        Quy trình đang thật sự chạy, vẽ lại từ nhật ký sự kiện: hồ sơ đi qua những bước nào, chờ ở đâu
        lâu nhất và rẽ ra khỏi luồng chính ở chỗ nào.
      </p>
      <ThanhBaoCao dang="quy-trinh" />
      <QuyTrinhThucTe
        khoangBanDau={khoangTuDiaChi(tu, den, new Date())}
        khongGian={danhTinh?.workspaces ?? []}
      />
    </KhungLamViec>
  );
}
