// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Thẻ gợi ý của hệ thống (#239) — khuôn dùng chung cho mọi trường quyết định có gợi ý.
//
// KHUÔN MẪU: gợi ý điền sẵn ô chọn, thẻ nằm NGAY TRÊN ô đó và nói ba điều — gợi ý là gì, vì
// sao, từ nguồn nào. Người xác nhận bằng chính nút thao tác của bảng (ví dụ "Xác nhận · Chuyển
// phòng"); dịch vụ ghi lại họ giữ hay đổi giá trị gợi ý (cột `event_log.suggestion`). Vì vậy thẻ
// KHÔNG có nút "chấp nhận" riêng, cũng không có nút "hoàn tác": chuyển trạng thái không quay
// lui và nhật ký chỉ ghi thêm. Muốn khác gợi ý thì đổi ô chọn — thẻ chỉ nói nhẹ là bạn đang
// chọn khác, không chặn gì.
//
// Độ tin cậy CHỈ hiện khi nguồn có con số thật (`confidence` khác null). Bảng ánh xạ không có
// độ tin cậy, nên không bao giờ vẽ một con số giả.
//
// Thẻ không biết trường nào, phòng ban nào: mọi chữ đến từ `GoiY` do dịch vụ trả. Gợi ý cho
// trường khác về sau (loại, mức ưu tiên, người xử lý) dùng nguyên khuôn này.

import { Lightbulb } from "lucide-react";
import type { ReactNode } from "react";

import type { GoiY } from "@/lib/kieu";

/** Độ tin cậy 0–1 thành phần trăm nguyên: 0,824 → "82%". */
function phanTram(doTinCay: number): string {
  return `${Math.round(doTinCay * 100)}%`;
}

export function TheGoiY({
  id,
  goiY,
  dangChon,
  canCu,
}: {
  /** Để ô chọn trỏ `aria-describedby` vào thẻ. */
  id?: string;
  goiY: GoiY;
  /** Giá trị ô chọn lúc này. Trống nghĩa là chưa chọn gì — chưa gọi là "khác gợi ý". */
  dangChon: string;
  /** Căn cứ thêm dưới dòng nguồn — hồ sơ đã giải quyết tương tự ở màn điều phối (#450). */
  canCu?: ReactNode;
}) {
  const chonKhac = dangChon !== "" && dangChon !== goiY.code;

  return (
    <div id={id} className="the-goi-y" data-khac={chonKhac ? "" : undefined}>
      <p className="the-goi-y-dau">
        <Lightbulb aria-hidden />
        <span>
          Gợi ý: <strong>{goiY.label}</strong>
        </span>
      </p>
      <p className="the-goi-y-ly-do">{goiY.reason}</p>
      <p className="the-goi-y-nguon">
        Nguồn: {goiY.source_label}
        {goiY.confidence !== null && <> · Độ tin cậy {phanTram(goiY.confidence)}</>}
      </p>
      {canCu}
      {/* Luôn có mặt trong cây để trình đọc màn hình đọc được khi nội dung hiện ra */}
      <p className="the-goi-y-khac" role="status">
        {chonKhac ? "Bạn đang chọn khác gợi ý. Lựa chọn của bạn được ghi lại trong nhật ký." : ""}
      </p>
    </div>
  );
}
