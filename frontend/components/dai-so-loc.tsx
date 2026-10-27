// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Dải số đầu hàng đợi (#231): mỗi ô là một trạng thái hay một nhóm do trang dựng từ dữ liệu
// bộ quy tắc, kèm số hồ sơ; bấm ô là lọc hàng đợi theo ô đó. Ô có hồ sơ quá hạn hay sắp hạn
// mang dòng phụ có biểu tượng và chữ — không chỉ bằng màu. Màn hẹp thì dải cuộn ngang.
//
// Tệp này không biết tên trạng thái nào: nhãn, số, đường dẫn đều do trang truyền.

import { AlarmClock, Clock } from "lucide-react";
import Link from "next/link";

export type OLoc = {
  href: string;
  nhan: string;
  so: number;
  chon: boolean;
  quaHan?: number;
  sapHan?: number;
};

export function DaiSoLoc({ cacO, nhan }: { cacO: OLoc[]; nhan: string }) {
  return (
    <nav className="dai-so-loc" aria-label={nhan}>
      {cacO.map((o) => (
        <Link key={o.href} href={o.href} className="o-loc" aria-current={o.chon ? "page" : undefined}>
          <span className="o-loc-nhan">{o.nhan}</span>
          <strong>{o.so}</strong>
          {o.quaHan ? (
            <span className="o-loc-phu" data-muc="qua">
              <AlarmClock aria-hidden />
              {o.quaHan} quá hạn
            </span>
          ) : o.sapHan ? (
            <span className="o-loc-phu" data-muc="sap">
              <Clock aria-hidden />
              {o.sapHan} sắp hạn
            </span>
          ) : null}
        </Link>
      ))}
    </nav>
  );
}
