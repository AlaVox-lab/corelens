"use client";
// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Hồ sơ đã giải quyết tương tự làm căn cứ, ngay trong thẻ gợi ý của điều phối viên (#450).
//
// Khi bật mô hình nhúng (#319), người duyệt gợi ý thấy vài hồ sơ cũ gần nội dung hồ sơ đang xét, mở được
// từng hồ sơ để xem đã giải quyết thế nào, rồi mới quyết định giữ hay đổi gợi ý. Như khối hồ sơ tương tự
// của người gửi (goi-y-tuong-tu.tsx), khối này KHÔNG BAO GIỜ làm màn điều phối khác đi khi không có gì để
// nói: mô hình nhúng tắt, chậm, hỏng, hay không có hồ sơ nào đủ gần — đều không vẽ gì, không ô trống, không
// lời báo lỗi. Hỏi sau khi thẻ hiện, có hạn chót; nút thao tác không bao giờ chờ khối này.
import { History } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import type { HoSoCanCu, KetQuaCanCu } from "@/lib/kieu";

/** Hạn chót phía trình duyệt — dịch vụ có hạn nhúng riêng ngắn hơn. Quá hạn thì không hiện gì. */
const HAN_CHOT_MS = 4000;

export function CanCuTuongTu({ maHoSo }: { maHoSo: number }) {
  const [cacHoSo, datCacHoSo] = useState<HoSoCanCu[]>([]);

  useEffect(() => {
    const huy = new AbortController();
    (async () => {
      try {
        const ph = await fetch(`/api/dieu-phoi/tuong-tu/${maHoSo}`, {
          signal: AbortSignal.any([huy.signal, AbortSignal.timeout(HAN_CHOT_MS)]),
        });
        if (!ph.ok) return;
        const kq = (await ph.json()) as KetQuaCanCu;
        if (kq.enabled) datCacHoSo(kq.items);
      } catch {
        // Hủy, quá hạn, mạng lỗi: không hiện gì — thẻ gợi ý vẫn đủ như trước
      }
    })();
    return () => huy.abort();
  }, [maHoSo]);

  if (cacHoSo.length === 0) return null;
  // Gập sẵn (#561): mỗi dòng ở bề rộng một thẻ gợi ý dài 3–7 dòng chữ, mở hết ra thì khung thao tác dài gấp đôi.
  // Nhãn ghi số hồ sơ để người duyệt biết có căn cứ mà không phải mở
  return (
    <details className="can-cu-tuong-tu">
      <summary className="can-cu-tuong-tu-dau">
        <History aria-hidden />
        <span>Xem {cacHoSo.length} hồ sơ đã giải quyết tương tự</span>
      </summary>
      <ul>
        {cacHoSo.map((h) => (
          <li key={h.case_id}>
            <Link href={`/dieu-phoi/${h.case_id}`} target="_blank" rel="noopener" className="mono">
              {h.code}
            </Link>{" "}
            {h.title}
            {h.request_type && <span className="can-cu-tuong-tu-phu"> · {h.request_type}</span>}
            {/* Hồ sơ không ghi cách giải quyết thì không có gạch nối treo ở cuối dòng (#556) */}
            {h.resolution ? <span className="can-cu-tuong-tu-phu"> — {h.resolution}</span> : null}
          </li>
        ))}
      </ul>
    </details>
  );
}
