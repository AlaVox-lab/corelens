// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Email và số điện thoại của người gửi, dưới tên họ trên trang chi tiết của hai buồng
// lái (#131). Bấm email mở ứng dụng thư; bấm số trên điện thoại thì gọi được.
//
// Bốn trường hợp phải nói khác nhau, không gộp làm một: có liên hệ, chưa điền số, tài
// khoản không còn, và danh bạ không trả lời. Ba trường hợp sau đều "không có số", nhưng
// người đọc cần biết nên làm gì tiếp — nhắn trên hồ sơ, hay thử lại sau.
//
// Thành phần chạy phía máy chủ, không có trạng thái: trang tra danh bạ rồi truyền kết quả
// xuống. Danh bạ hỏng thì chỉ chỗ này báo lỗi, phần còn lại của trang vẫn mở.

import type { KetQua } from "@/lib/api";
import type { LienHeNguoiGui as LienHe } from "@/lib/kieu";

/** Số để quay: bỏ dấu cách, dấu chấm, ngoặc — `tel:` chỉ cần chữ số và dấu cộng. */
function soDeGoi(so: string): string {
  return so.replace(/[^\d+]/g, "");
}

export function LienHeNguoiGui({ ketQua }: { ketQua: KetQua<LienHe> }) {
  if (!ketQua.ok) {
    return (
      <span style={{ display: "block" }}>
        {ketQua.ma === "directory-unavailable"
          ? "Không tra được liên hệ: danh bạ không trả lời. Thử tải lại trang sau ít phút."
          : "Không tra được liên hệ của người gửi."}
      </span>
    );
  }

  const lienHe = ketQua.duLieu;
  if (!lienHe.found) {
    return (
      <span style={{ display: "block" }}>
        Tài khoản không còn trong danh bạ. Nhắn qua lời nhắn trên hồ sơ.
      </span>
    );
  }

  return (
    <span style={{ display: "grid", gap: "2px" }}>
      {lienHe.email ? (
        <a href={`mailto:${lienHe.email}`} style={{ color: "inherit", overflowWrap: "anywhere" }}>
          {lienHe.email}
        </a>
      ) : (
        <span>Chưa có email</span>
      )}
      {lienHe.phone ? (
        <a href={`tel:${soDeGoi(lienHe.phone)}`} className="mono" style={{ color: "inherit" }}>
          {lienHe.phone}
        </a>
      ) : (
        <span>Chưa có số điện thoại</span>
      )}
    </span>
  );
}
