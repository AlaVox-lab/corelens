// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khung của hộp thư (#155). Mọi người đăng nhập đều có hộp thư — người gửi nhắn về hồ sơ
// của mình — nên cửa là không gian chung `portal`; dịch vụ tự lọc cuộc trò chuyện theo
// từng người.

import { KhungLamViec } from "@/components/khung-lam-viec";

export default function KhungHopThu({ children }: Readonly<{ children: React.ReactNode }>) {
  return <KhungLamViec canKhongGian="portal">{children}</KhungLamViec>;
}
