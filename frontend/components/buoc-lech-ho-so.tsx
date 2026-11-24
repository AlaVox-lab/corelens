"use client";
// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Bước lệch quy trình của một hồ sơ, trên trang hồ sơ phía nhân viên (#448).
//
// Vòng tự soi quy trình (CLAUDE.md 4.1) tới tận từng hồ sơ: người xử lý thấy hồ sơ mình đang giữ đã đi
// lệch quy trình thiết kế ở bước nào — trả về làm lại, leo thang, mở lại, chuyển phòng lần nữa. Định nghĩa
// lệch là đúng định nghĩa nhánh lệch của màn Quy trình thực tế (dịch vụ khai phá), nhãn loại lệch cũng là
// bảng nhãn của màn đó, nên hai nơi gọi một bước cùng một tên.
//
// CHỈ THÔNG TIN (ADR-0005): không nút nào, không đổi gì trên hồ sơ. Và như khối căn cứ tương tự (#450),
// khối không bao giờ làm trang khác đi khi không có gì để nói: hồ sơ đi đúng luồng, người xem không được
// xem, dịch vụ khai phá tắt, chậm hay hỏng — đều không vẽ gì, không khung trống, không lời báo lỗi. Hỏi sau
// khi trang hiện, có hạn chót; thao tác trên hồ sơ không bao giờ chờ khối này.
//
// Khối hiện kết quả của dịch vụ AGPL qua mạng; liên kết mã nguồn của dịch vụ (điều 13, #340) nằm ở trang
// Mã nguồn và giấy phép, chân thanh bên (#540), không lặp ở đây.
import { GitBranch } from "lucide-react";
import { useEffect, useState } from "react";

import { ngayGio } from "@/lib/dinh-dang";
import { tenNhanhLech } from "@/lib/ket-luan-quy-trinh";
import type { BuocLech, KetQuaTuanThu } from "@/lib/kieu";

/** Hạn chót phía trình duyệt. Quá hạn thì không hiện gì — trang vẫn đủ như trước. */
const HAN_CHOT_MS = 6000;

export function BuocLechHoSo({ maHoSo }: { maHoSo: number }) {
  const [cacBuoc, datCacBuoc] = useState<BuocLech[]>([]);

  useEffect(() => {
    const huy = new AbortController();
    (async () => {
      try {
        const ph = await fetch(`/api/tuan-thu/${maHoSo}`, {
          signal: AbortSignal.any([huy.signal, AbortSignal.timeout(HAN_CHOT_MS)]),
        });
        if (!ph.ok) return;
        const kq = (await ph.json()) as KetQuaTuanThu;
        if (kq.status === "ready" && Array.isArray(kq.steps)) datCacBuoc(kq.steps);
      } catch {
        // Hủy, quá hạn, mạng lỗi: không hiện gì
      }
    })();
    return () => huy.abort();
  }, [maHoSo]);

  if (cacBuoc.length === 0) return null;
  return (
    <section className="the khoi buoc-lech" aria-labelledby={`buoc-lech-${maHoSo}`}>
      <h2 className="khoi-dau" id={`buoc-lech-${maHoSo}`}>
        <GitBranch aria-hidden />
        Đi lệch quy trình thiết kế
      </h2>
      <p className="buoc-lech-giai">
        {cacBuoc.length === 1 ? "Một bước" : `${cacBuoc.length} bước`} của hồ sơ này rẽ khỏi luồng chính,
        theo cùng cách tính với màn Quy trình thực tế. Chỉ để thông tin — không cần thao tác gì.
      </p>
      <ol className="buoc-lech-ds">
        {cacBuoc.map((b, i) => (
          <li key={`${b.at}-${b.kind}-${i}`}>
            <span className="buoc-lech-loai">{tenNhanhLech(b.kind)}</span>
            <span>
              {b.from_label ? `${b.from_label} → ` : ""}
              {b.to_label}
            </span>
            <span className="buoc-lech-phu">
              <time dateTime={b.at}>{ngayGio(b.at)}</time>
              {b.actor_label ? ` · ${b.actor_label}` : ""}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
