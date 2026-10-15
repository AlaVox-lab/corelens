// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Đọc đồng hồ SLA thành một câu tiếng Việt.
//
// Các con số từ dịch vụ ứng dụng — đã chạy, đã dừng, ngưỡng, đang dừng, đã khởi động —
// nói lên những tình huống khác nhau, và người dùng cần phân biệt được chúng:
//
//   chưa có ngưỡng  → hồ sơ chưa phân loại, chưa biết áp cam kết nào
//   chưa khởi động  → có ngưỡng nhưng phòng ban chưa nhận việc, đồng hồ chưa chạy
//   chờ xác nhận    → việc đã xong, đồng hồ đứng chờ người gửi xác nhận kết quả
//   đang tạm dừng   → đồng hồ đứng vì hồ sơ đang chờ người gửi trả lời
//   còn trong hạn   → còn bao lâu
//   đã quá hạn      → quá bao lâu
//
// Hai chỗ dễ gây hiểu lầm nhất (#97): nói "còn 3 ngày" khi đồng hồ chưa chạy làm người
// gửi tưởng hạn đang đếm; nói "tạm dừng đếm hạn" ở hồ sơ đã hoàn tất làm người gửi tưởng
// việc còn dở. Đồng hồ đứng ở trạng thái nào để chờ gì thì tra `khiDung` trong
// lib/trang-thai.ts — bảng trình bày, có câu chung cho trạng thái lạ.
//
// Cùng một hồ sơ, người gửi đọc "chờ bạn", người trong phòng đọc "chờ người gửi".
//
// Mọi con số của đồng hồ là GIỜ LÀM VIỆC theo lịch trong dữ liệu (#199), nên câu luôn nói
// "giờ làm việc" và, khi đồng hồ đang chạy, kèm hạn chót dịch vụ tính sẵn — "còn 6 giờ làm
// việc" mà không có giờ cụ thể thì người đọc phải tự đếm qua đêm và cuối tuần.

import { hanLuc, thoiLuong, thoiLuongLamViec } from "@/lib/dinh-dang";
import type { HoSoTomTat } from "@/lib/kieu";
import { trinhBayTrangThai } from "@/lib/trang-thai";

export type DocDongHo = {
  cau: string;
  /** Câu này có phải tin xấu không — quyết định màu chữ. */
  canhBao: boolean;
};

/** Ai đang đọc câu này: chính người gửi, hay người xử lý bên trong. */
export type NguoiXem = "nguoi-gui" | "noi-bo";

export function docDongHo(ho_so: HoSoTomTat, nguoiXem: NguoiXem = "noi-bo"): DocDongHo {
  const laNguoiGui = nguoiXem === "nguoi-gui";

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
      cau: `Khép lại sau ${thoiLuongLamViec(ho_so.sla_running_seconds)}`,
      canhBao: false,
    };
  }

  if (ho_so.sla_limit_seconds === null) {
    return { cau: "Chưa phân loại nên chưa áp cam kết", canhBao: false };
  }

  // Có ngưỡng nhưng đồng hồ chưa chạy: phòng ban chưa nhận việc. Nói ngưỡng và nói
  // rõ mốc bắt đầu, không nói "còn …" như thể hạn đang đếm.
  if (!ho_so.sla_started) {
    return {
      cau: `Cam kết ${thoiLuongLamViec(ho_so.sla_limit_seconds)}, tính từ lúc phòng ban nhận việc`,
      canhBao: false,
    };
  }

  const con_lai = ho_so.sla_limit_seconds - ho_so.sla_running_seconds;
  const khiDung = ho_so.sla_paused ? trinhBayTrangThai(ho_so.state.code).khiDung : undefined;

  // Việc đã xong, chỉ còn chờ xác nhận: nói về kết quả, không nói "còn …". Trễ hạn thì
  // vẫn nói ra, vì đó là sự thật của lần xử lý này.
  if (khiDung === "cho-xac-nhan") {
    const cho = laNguoiGui ? "chờ bạn xác nhận" : "chờ người gửi xác nhận";
    if (ho_so.sla_overdue) {
      return { cau: `Đã xử lý xong, trễ hạn ${thoiLuongLamViec(-con_lai)} · ${cho}`, canhBao: true };
    }
    const trong =
      ho_so.sla_running_seconds < 60
        ? ""
        : ` trong ${thoiLuongLamViec(ho_so.sla_running_seconds)}`;
    return { cau: `Đã xử lý xong${trong} · ${cho}`, canhBao: false };
  }

  if (ho_so.sla_overdue) {
    // Quá hạn mà vừa được giao lại hay mở lại: nói luôn còn bao lâu trước khi bị leo
    // thang lần nữa, để không ai tưởng hệ thống quên hồ sơ này (#94).
    const anHan =
      ho_so.sla_grace_seconds !== null && ho_so.sla_grace_seconds > 0
        ? ` · ân hạn còn ${thoiLuongLamViec(ho_so.sla_grace_seconds)}`
        : "";
    return { cau: `Quá hạn ${thoiLuongLamViec(-con_lai)}${anHan}`, canhBao: true };
  }

  if (ho_so.sla_paused) {
    // Nói cả phần còn lại: người gửi cần biết trả lời sớm thì còn bao nhiêu dư địa.
    const vi =
      khiDung === "cho-tra-loi" ? (laNguoiGui ? " trong lúc chờ bạn" : ", chờ người gửi") : "";
    return {
      cau: `Tạm dừng đếm hạn${vi} · còn ${thoiLuongLamViec(con_lai)}`,
      canhBao: false,
    };
  }

  const han = ho_so.sla_due_at ? ` · hạn ${hanLuc(ho_so.sla_due_at)}` : " trong cam kết";
  return { cau: `Còn ${thoiLuongLamViec(con_lai)}${han}`, canhBao: false };
}

/**
 * Câu báo hồ sơ sẽ tự đi lúc nào khi nằm im quá hạn chờ (#142): "Tự trả về điều phối lúc
 * 10:41 Thứ Ba 13/10". Nhãn hành động lấy từ dữ liệu của cạnh, không viết ở đây. `canhBao`
 * khi đã vào khoảng báo trước khai trong dữ liệu. `null` khi trạng thái không có hạn chờ.
 */
export function docTuDong(ho_so: HoSoTomTat): DocDongHo | null {
  const td = ho_so.auto_transition;
  if (!td) return null;
  const luc = td.at ? ` lúc ${hanLuc(td.at)}` : "";
  return { cau: `${td.activity_label}${luc}`, canhBao: td.warn };
}

/**
 * Vạch hạn trên trang hồ sơ (#169): đã dùng bao nhiêu phần trăm cam kết, sắp hạn hay quá
 * hạn chưa. `null` khi chưa có gì để vẽ — chưa có ngưỡng, đồng hồ chưa chạy, hồ sơ đã kết
 * thúc. Ba mức theo đúng cờ dịch vụ trả về: ngưỡng "sắp hạn" khai theo loại yêu cầu trong
 * dữ liệu (#175), giao diện không tự đặt con số nào.
 */
export function vachHan(
  ho_so: HoSoTomTat,
): { phan: number; muc: "qua" | "sap" | undefined } | null {
  if (ho_so.state.is_terminal || ho_so.sla_limit_seconds === null || !ho_so.sla_started) {
    return null;
  }
  const phan = (ho_so.sla_running_seconds / ho_so.sla_limit_seconds) * 100;
  const muc = ho_so.sla_overdue ? "qua" : ho_so.sla_due_soon ? "sap" : undefined;
  return { phan: Math.min(100, Math.max(0, phan)), muc };
}

/** Tổng thời gian hồ sơ đã nằm trong hệ thống, kể cả những đoạn đồng hồ dừng. */
export function daTroiQua(ho_so: HoSoTomTat, bayGio: Date): string {
  const giay = (bayGio.getTime() - new Date(ho_so.created_at).getTime()) / 1000;
  return thoiLuong(Math.max(0, giay));
}
