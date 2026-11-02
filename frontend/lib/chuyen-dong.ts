// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Chuyển động khi ẩn một khối (#237). Hiện thì CSS tự lo — khối mới gắn vào trang chạy hiệu ứng
// vào. Ẩn thì khối phải còn trên trang thêm một nhịp cho hiệu ứng ra chạy xong rồi mới gỡ: phía
// gọi đặt cờ `dangAn` (CSS đọc `data-an`), chờ đúng thời lượng, rồi mới làm việc thật — đóng
// ngăn, đóng hộp xác nhận. Máy bật "giảm chuyển động" thì làm ngay, không chờ.
//
// Thời lượng ở đây phải khớp với hiệu ứng `an-di` trong globals.css (bảng quy tắc ở
// ARCHITECTURE.md mục 8.4).

import { useCallback, useEffect, useRef, useState } from "react";

/** Thời lượng hiệu ứng ẩn, mili giây — cùng số với `--an` trong globals.css. */
export const THOI_LUONG_AN_MS = 140;

export function giamChuyenDong(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * `[dangAn, an]`: gọi `an(xong)` để chạy hiệu ứng ẩn rồi mới gọi `xong`. Gọi lại khi đang ẩn thì
 * bỏ qua. `giuAn`: khối chỉ biến mất khi trang điều hướng xong (ngăn xem nhanh) — giữ cờ ẩn tới
 * lúc đó, không thì khối hiện lại một thoáng trước khi gỡ.
 */
export function useAnCham(giuAn = false): [boolean, (xong: () => void) => void] {
  const [dangAn, datDangAn] = useState(false);
  const hen = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => {
    if (hen.current) clearTimeout(hen.current);
  }, []);
  const an = useCallback(
    (xong: () => void) => {
      if (hen.current) return;
      if (giamChuyenDong()) {
        xong();
        return;
      }
      datDangAn(true);
      hen.current = setTimeout(() => {
        hen.current = null;
        xong();
        if (!giuAn) datDangAn(false);
      }, THOI_LUONG_AN_MS);
    },
    [giuAn],
  );
  return [dangAn, an];
}
