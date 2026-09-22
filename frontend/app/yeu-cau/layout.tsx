// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khung của ba màn hình cổng gửi yêu cầu (#44). Phần dùng chung nằm ở
// components/khung-lam-viec.tsx.

import { KhungLamViec } from "@/components/khung-lam-viec";

export default function KhungCong({ children }: Readonly<{ children: React.ReactNode }>) {
  return <KhungLamViec canKhongGian="portal">{children}</KhungLamViec>;
}
