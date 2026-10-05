// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Các bước của đường chính, cho thanh "hồ sơ đang ở đâu" trên trang hồ sơ (#169).
//
// Đường chính suy từ dữ liệu, không viết cứng tên trạng thái nào: các trạng thái theo
// `display_order` (thứ tự `/states` trả về), tính tới và gồm trạng thái kết thúc đầu
// tiên. Bộ quy tắc hiện tại xếp sáu trạng thái của đường thẳng trước — Đã gửi tới Đã
// đóng — rồi mới tới bốn trạng thái nhánh (chờ bổ sung, bị từ chối, leo thang, hủy).
// Doanh nghiệp triển khai đổi đường chính bằng cách đổi thứ tự trong dữ liệu khởi tạo.
//
// Hồ sơ đang ở một trạng thái nhánh thì thanh dừng ở bước đường chính gần nhất nó đã đi
// qua — nhãn trạng thái to cạnh tiêu đề vẫn nói đúng trạng thái thật.

import type { SuKien, TrangThai } from "@/lib/kieu";

export type Buoc = { code: string; label: string; xong: boolean; dang: boolean };

export function duongChinh(cacTrangThai: TrangThai[]): TrangThai[] {
  const cuoi = cacTrangThai.findIndex((t) => t.is_terminal);
  return cuoi < 0 ? cacTrangThai : cacTrangThai.slice(0, cuoi + 1);
}

export function cacBuoc(cacTrangThai: TrangThai[], hienTai: string, lichSu: SuKien[]): Buoc[] {
  const duong = duongChinh(cacTrangThai);
  const viTri = (ma: string) => duong.findIndex((t) => t.code === ma);

  let dang = viTri(hienTai);
  if (dang < 0) {
    // Trạng thái nhánh: lấy bước đường chính cuối cùng hồ sơ đã vào
    for (let i = lichSu.length - 1; i >= 0 && dang < 0; i--) dang = viTri(lichSu[i].to_state);
    if (dang < 0) dang = 0;
  }

  // Đã tới trạng thái kết thúc của đường chính thì bước cuối cũng xong, không còn dở
  const toiDich = duong[dang]?.code === hienTai && duong[dang].is_terminal;
  return duong.map((t, i) => ({
    code: t.code,
    label: t.label,
    xong: i < dang || (toiDich && i === dang),
    dang: i === dang,
  }));
}
