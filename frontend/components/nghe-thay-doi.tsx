"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Nghe tín hiệu "hồ sơ vừa đổi" từ dịch vụ (#387) và làm mới màn đang mở ngay, không đợi lượt hỏi định kỳ.
//
// Mở một `EventSource` tới `/api/su-kien` (tuyến của chính cổng, token nằm ở máy chủ). Nhận `event: ho-so`
// thì:
//   - `router.refresh()`: Next dựng lại phần máy chủ của trang rồi ghép vào, giữ nguyên chữ đang gõ dở,
//     ô tìm, ngăn đang mở — cùng cách hộp thư đã dùng (tu-lam-moi.tsx);
//   - phát `SU_KIEN_HOP_THU` để thanh bên hỏi lại số chưa đọc.
// Nhiều tín hiệu tới sát nhau gộp làm một lần làm mới. Thẻ đang ẩn thì để dành, hiện lại mới làm mới.
//
// Hỏi định kỳ (#155) giữ nguyên làm đường dự phòng: luồng đứt, dịch vụ đủ số luồng (tuyến trả 204 nên
// trình duyệt thôi nối lại) hay proxy chặn SSE thì cổng vẫn chạy như trước.

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { SU_KIEN_HOP_THU } from "@/components/danh-dau-da-doc";

/** Chờ chừng này sau tín hiệu cuối rồi mới làm mới — gộp loạt tín hiệu của cùng một thao tác. */
const GOP_MS = 300;

export function NgheThayDoi() {
  const dieuHuong = useRouter();

  useEffect(() => {
    if (typeof EventSource === "undefined") return;

    const nguon = new EventSource("/api/su-kien");
    let hen: number | undefined;
    let choHien = false;

    const lamMoi = () => {
      if (document.visibilityState !== "visible") {
        choHien = true;
        return;
      }
      dieuHuong.refresh();
      window.dispatchEvent(new Event(SU_KIEN_HOP_THU));
    };
    const khiCoTin = () => {
      window.clearTimeout(hen);
      hen = window.setTimeout(lamMoi, GOP_MS);
    };
    const khiHien = () => {
      if (choHien && document.visibilityState === "visible") {
        choHien = false;
        lamMoi();
      }
    };

    nguon.addEventListener("ho-so", khiCoTin);
    document.addEventListener("visibilitychange", khiHien);
    return () => {
      window.clearTimeout(hen);
      nguon.removeEventListener("ho-so", khiCoTin);
      document.removeEventListener("visibilitychange", khiHien);
      nguon.close();
    };
  }, [dieuHuong]);

  return null;
}
