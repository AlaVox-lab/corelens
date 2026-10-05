// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Ô chữ cái thay ảnh đại diện: chữ nào, màu nào. Dùng ở thanh bên (#158) và thẻ liên hệ
// người gửi (#169), để cùng một người mang cùng một ô ở mọi chỗ.

export function chuCaiDau(ten: string): string {
  const tu = ten.trim().split(/\s+/).filter(Boolean);
  if (tu.length === 0) return "?";
  // Tên Việt Nam đọc họ trước, tên gọi sau cùng. "Nguyễn Minh Anh" → "NA": chữ đầu
  // của họ và chữ đầu của tên gọi, giống cách người ta tự viết tắt.
  const dau = tu[0][0];
  const cuoi = tu.length > 1 ? tu[tu.length - 1][0] : "";
  return (dau + cuoi).toUpperCase();
}

/** Màu ô chữ cái, 1–5, tính từ định danh: cùng người luôn cùng màu. */
export function mauTheo(dinhDanh: string): number {
  let tong = 0;
  for (const kyTu of dinhDanh) tong = (tong + kyTu.charCodeAt(0)) % 5;
  return tong + 1;
}
