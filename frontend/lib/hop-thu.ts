// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Đường dẫn tới một cuộc trò chuyện trong hộp thư (#155). Từ #156 mỗi hồ sơ có hai cuộc —
// với người gửi và nội bộ — nên địa chỉ mang thêm `kenh=noi-bo` cho cuộc nội bộ. Tải lại
// hay gửi đường dẫn đều mở đúng cuộc đó.

import type { HoSoChiTiet } from "@/lib/kieu";

/** Giá trị `kenh` trên địa chỉ trang của cuộc nội bộ. */
export const KENH_NOI_BO = "noi-bo";

/** Giá trị `loc` trên địa chỉ trang của hai chip lọc hộp thư (#232). */
export const LOC_CHUA_DOC = "chua-doc";
export const LOC_NOI_BO = "noi-bo";

export function duongCuoc(maHoSo: number, noiBo: boolean): string {
  return `/hop-thu?ho-so=${maHoSo}${noiBo ? `&kenh=${KENH_NOI_BO}` : ""}`;
}

/** Nút "Mở trong hộp thư" trên trang hồ sơ: cuộc với người gửi nếu đã có tin, không thì
 *  cuộc nội bộ. */
export function duongHopThu(ho_so: HoSoChiTiet): string {
  return duongCuoc(ho_so.id, !ho_so.messages.some((m) => !m.internal));
}
