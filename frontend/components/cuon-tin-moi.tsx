"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Cuộn khung trò chuyện xuống tin mới nhất khi mở trang, như mọi ứng dụng chat (#189). Dùng
// ở trang hồ sơ người gửi — nơi khung chat nằm thẳng trên trang, không qua thẻ hay hộp thư
// (hai nơi đó tự cuộn trong the-lich-su.tsx và tu-lam-moi.tsx).

import { useEffect } from "react";

export function CuonTinMoi({ chon, soTin }: { chon: string; soTin: number }) {
  useEffect(() => {
    const cuon = document.querySelector<HTMLElement>(`${chon} [data-cuon]`);
    if (cuon) cuon.scrollTop = cuon.scrollHeight;
  }, [chon, soTin]);
  return null;
}
