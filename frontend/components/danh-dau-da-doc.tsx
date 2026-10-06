"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Đánh dấu đã đọc khi lời nhắn của hồ sơ đang thật sự hiện trước mắt người dùng (#155):
// cuộc trò chuyện đang mở trong hộp thư, thẻ "Trao đổi" trên trang hồ sơ nhân viên, trang
// hồ sơ người gửi; cuộc nội bộ (#156) có mốc riêng. Ghi từ trình duyệt chứ không lúc dựng trang ở máy chủ, để trình duyệt
// tải trước một trang (prefetch) không vô tình đánh dấu tin người dùng chưa thấy.
//
// Xong thì báo thanh bên hỏi lại con số chưa đọc ngay, không đợi lượt hỏi định kỳ.

import { useEffect } from "react";

import { danhDauDaDoc } from "@/app/hop-thu/thao-tac";

/** Sự kiện trên `window` báo thanh bên con số chưa đọc vừa đổi. */
export const SU_KIEN_HOP_THU = "dxlab:hop-thu";

export function DanhDauDaDoc({
  maHoSo,
  soTin,
  bat = true,
  noiBo = false,
}: {
  maHoSo: number;
  /** Số lời nhắn đang hiện — có tin mới tới thì đánh dấu lại. */
  soTin: number;
  /** Tắt khi lời nhắn chưa hiện, ví dụ thẻ "Trao đổi" chưa mở. */
  bat?: boolean;
  /** Đánh dấu cuộc nội bộ thay vì cuộc với người gửi. */
  noiBo?: boolean;
}) {
  useEffect(() => {
    if (!bat || soTin === 0) return;
    danhDauDaDoc(maHoSo, noiBo).then(() => window.dispatchEvent(new Event(SU_KIEN_HOP_THU)));
  }, [maHoSo, soTin, bat, noiBo]);
  return null;
}
