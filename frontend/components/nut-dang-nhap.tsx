"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Nút đăng nhập nhớ trang người dùng đang định mở.
//
// Không có nó thì đăng nhập xong ai cũng bị đưa về trang chủ: mở thẳng /dieu-phoi khi
// chưa đăng nhập, bấm đăng nhập, rồi phải tự tìm đường quay lại. Tham số `quay_ve` đã
// có sẵn ở /api/auth/login từ #43 — kèm phép lọc chặn chuyển hướng ra ngoài — chỉ là
// chưa trang nào dùng tới.
//
// Chạy phía trình duyệt vì cần đọc đường dẫn hiện tại, thứ mà khung trang phía máy chủ
// không biết.

import { usePathname, useSearchParams } from "next/navigation";

export function NutDangNhap({ children }: { children: React.ReactNode }) {
  const duongDan = usePathname();
  const thamSo = useSearchParams().toString();
  const quayVe = thamSo ? `${duongDan}?${thamSo}` : duongDan;

  return (
    <a
      href={`/api/auth/login?quay_ve=${encodeURIComponent(quayVe)}`}
      className="nut"
      data-loai="chinh"
      style={{ marginTop: "20px" }}
    >
      {children}
    </a>
  );
}
