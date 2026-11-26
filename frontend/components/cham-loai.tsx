// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Chấm màu theo loại yêu cầu (#561) — ở đầu trang hồ sơ, bảng hàng đợi, thẻ Kanban, Hồ sơ của tôi.
//
// Màu SUY TỪ MÃ LOẠI bằng cùng phép băm với ảnh đại diện (`mauTheo`, lib/nguoi.ts): không có bảng "loại nào màu
// gì" trong mã. Loại mới thêm ở màn Cấu hình tự có màu, cùng một loại luôn cùng màu ở mọi màn. Chấm chỉ để mắt
// nhận nhóm nhanh — tên loại luôn đứng ngay cạnh, nên chấm ẩn với trình đọc màn hình.

import { mauTheo } from "@/lib/nguoi";

export function ChamLoai({ ma }: { ma: string | null | undefined }) {
  if (!ma) return null;
  return <span className="cham-loai" data-c={mauTheo(ma)} aria-hidden />;
}
