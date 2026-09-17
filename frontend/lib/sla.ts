// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Đọc đồng hồ SLA thành một câu tiếng Việt.
//
// Bốn con số từ dịch vụ ứng dụng — đã chạy, đã dừng, ngưỡng, có đang dừng không —
// nói lên bốn tình huống khác nhau, và người dùng cần phân biệt được chúng:
//
//   chưa có ngưỡng  → hồ sơ chưa phân loại, chưa biết áp cam kết nào
//   đang tạm dừng   → đồng hồ đứng vì hồ sơ đang chờ chính người gửi
//   còn trong hạn   → còn bao lâu
//   đã quá hạn      → quá bao lâu
//
// Tình huống thứ hai là chỗ dễ gây hiểu lầm nhất nếu nói không rõ. Hồ sơ nằm ở
// `Chờ bổ sung thông tin` thì đồng hồ dừng, nên người dùng nhìn con số đứng yên qua
// vài ngày sẽ tưởng hệ thống hỏng. Phải nói thẳng ra là nó đang dừng, và dừng vì ai.

import { thoiLuong } from "@/lib/dinh-dang";
import type { HoSoTomTat } from "@/lib/kieu";

export type DocDongHo = {
  cau: string;
  /** Câu này có phải tin xấu không — quyết định màu chữ. */
  canhBao: boolean;
};

export function docDongHo(ho_so: HoSoTomTat): DocDongHo {
  // Hồ sơ đã đóng hoặc đã hủy thì đồng hồ dừng hẳn, và câu "còn 2 ngày trong cam kết"
  // trở thành vô nghĩa — tệ hơn là nó gợi ý rằng vẫn còn việc phải làm. Nói về quá
  // khứ thay vì tương lai.
  //
  // Cờ `is_terminal` tra từ bảng `states`, không so mã trạng thái với một danh sách
  // viết cứng ở đây.
  if (ho_so.state.is_terminal) {
    // Nói về đồng hồ, không suy diễn về phòng ban. Con số 0 xảy ra ở cả hai tình
    // huống khác hẳn nhau — hồ sơ bị hủy trước khi ai bắt tay vào việc, và hồ sơ chạy
    // hết trong vòng chưa tới một giây — nên một câu suy diễn sẽ sai ở tình huống kia.
    if (ho_so.sla_running_seconds === 0) {
      return { cau: "Đồng hồ xử lý chưa từng chạy", canhBao: false };
    }
    if (ho_so.sla_overdue) {
      return { cau: `Khép lại, đã vượt cam kết`, canhBao: true };
    }
    return {
      cau: `Khép lại sau ${thoiLuong(ho_so.sla_running_seconds)} xử lý`,
      canhBao: false,
    };
  }

  if (ho_so.sla_limit_seconds === null) {
    return { cau: "Chưa phân loại nên chưa áp cam kết", canhBao: false };
  }

  const con_lai = ho_so.sla_limit_seconds - ho_so.sla_running_seconds;

  if (ho_so.sla_overdue) {
    return { cau: `Quá hạn ${thoiLuong(-con_lai)}`, canhBao: true };
  }

  if (ho_so.sla_paused) {
    // Nói cả phần còn lại: người dùng cần biết trả lời sớm thì còn bao nhiêu dư địa.
    return {
      cau: `Tạm dừng đếm hạn · còn ${thoiLuong(con_lai)}`,
      canhBao: false,
    };
  }

  return { cau: `Còn ${thoiLuong(con_lai)} trong cam kết`, canhBao: false };
}

/** Tổng thời gian hồ sơ đã nằm trong hệ thống, kể cả những đoạn đồng hồ dừng. */
export function daTroiQua(ho_so: HoSoTomTat, bayGio: Date): string {
  const giay = (bayGio.getTime() - new Date(ho_so.created_at).getTime()) / 1000;
  return thoiLuong(Math.max(0, giay));
}
