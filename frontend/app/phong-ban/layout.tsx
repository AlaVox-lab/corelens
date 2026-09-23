// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khung của buồng lái phòng ban (#83). Cùng khung với cổng người gửi và buồng lái điều
// phối, để ba nơi nhìn như một sản phẩm.

import { KhungLamViec } from "@/components/khung-lam-viec";

export default function KhungPhongBan({ children }: Readonly<{ children: React.ReactNode }>) {
  return <KhungLamViec canKhongGian="department">{children}</KhungLamViec>;
}
