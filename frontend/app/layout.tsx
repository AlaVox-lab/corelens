// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DX-OS Lab — Cổng vận hành yêu cầu nội bộ",
  description:
    "Tiếp nhận và điều phối tập trung mọi loại yêu cầu nội bộ trong doanh nghiệp.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
