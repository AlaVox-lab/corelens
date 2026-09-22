// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khung của buồng lái điều phối viên (#82). Dùng chung khung với cổng người gửi, để
// hai nơi nhìn như một sản phẩm chứ không phải hai.

import { KhungLamViec } from "@/components/khung-lam-viec";

export default function KhungDieuPhoi({ children }: Readonly<{ children: React.ReactNode }>) {
  return <KhungLamViec canKhongGian="coordination">{children}</KhungLamViec>;
}
