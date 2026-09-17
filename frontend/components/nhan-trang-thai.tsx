// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Nhãn trạng thái — thành phần xuất hiện nhiều nhất trong cả ba màn hình.
//
// Nhãn chữ (`label`) luôn đến từ dịch vụ ứng dụng, lấy từ bảng `states`. Thành phần
// này chỉ quyết định phần thị giác: dấu hiệu nào đặt trước chữ, họ màu nào, có tô nền
// đậm không. Xem lib/trang-thai.ts để biết vì sao ranh giới đó quan trọng.

import { bienHoMau, trinhBayTrangThai } from "@/lib/trang-thai";

type Props = {
  ma: string;
  nhan: string;
  /** Nhãn to dùng ở đầu trang chi tiết; mặc định là cỡ trong danh sách. */
  to?: boolean;
};

export function NhanTrangThai({ ma, nhan, to = false }: Props) {
  const kieu = trinhBayTrangThai(ma);
  const dam = kieu.nhom === "cho-ban";

  return (
    <span
      className="nhan-tt"
      data-dam={dam ? "1" : "0"}
      data-to={to ? "1" : "0"}
      style={bienHoMau(kieu.ho)}
    >
      {/* `aria-hidden` vì dấu hiệu là bản sao thị giác của chính nhãn chữ ngay bên
          cạnh. Trình đọc màn hình đọc được chữ rồi; đọc thêm "hình tam giác đen" chỉ
          làm rối. Dấu hiệu phục vụ mắt nhìn màn hình đen trắng, không phục vụ tai. */}
      <span className="dau" aria-hidden="true">
        {kieu.dau}
      </span>
      {nhan}
    </span>
  );
}
