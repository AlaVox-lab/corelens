"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Hộp thư tự tải tin mới khoảng 12 giây một lần khi trang đang hiện (#155), và cuộn khung
// chat xuống tin mới nhất khi có tin.
//
// Dùng `router.refresh()`: Next dựng lại phần máy chủ của trang rồi ghép vào, giữ nguyên
// trạng thái phía trình duyệt — chữ đang gõ dở trong ô soạn, ô tìm, chip đang chọn không
// mất. Không thêm dịch vụ nào vào Compose, không mở kết nối thường trực.

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { SU_KIEN_HOP_THU } from "@/components/danh-dau-da-doc";

const CHU_KY_MS = 12_000;

export function TuLamMoi({ soTin }: { soTin: number }) {
  const dieuHuong = useRouter();

  useEffect(() => {
    const lamMoi = () => {
      if (document.visibilityState === "visible") dieuHuong.refresh();
    };
    const dongHo = window.setInterval(lamMoi, CHU_KY_MS);
    document.addEventListener("visibilitychange", lamMoi);
    // Vừa đánh dấu đã đọc: tải lại ngay để số chưa đọc trong danh sách khớp, không đợi lượt sau
    window.addEventListener(SU_KIEN_HOP_THU, lamMoi);
    return () => {
      window.clearInterval(dongHo);
      document.removeEventListener("visibilitychange", lamMoi);
      window.removeEventListener(SU_KIEN_HOP_THU, lamMoi);
    };
  }, [dieuHuong]);

  // Tin mới tới (hay vừa mở cuộc khác): cuộn xuống cuối
  useEffect(() => {
    const cuon = document.querySelector<HTMLElement>(".ht-chat [data-cuon]");
    if (cuon) cuon.scrollTop = cuon.scrollHeight;
  }, [soTin]);

  return null;
}
