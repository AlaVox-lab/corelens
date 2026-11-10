// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Thanh chuyển giữa hai màn của mục Báo cáo (#315): Bảng điều khiển (Superset nhúng, #305) và
// Quy trình thực tế (khai phá quy trình, #314). Hai màn là hai trang riêng, nên mở một màn không
// tải màn kia — nhất là khung Superset, nặng, chỉ tải ở Bảng điều khiển. Thanh bên giữ một mục
// "Báo cáo", sáng ở cả hai trang.

import Link from "next/link";

const CAC_MUC = [
  { ma: "bang-dieu-khien", nhan: "Bảng điều khiển", duongDan: "/bao-cao" },
  { ma: "quy-trinh", nhan: "Quy trình thực tế", duongDan: "/bao-cao/quy-trinh" },
] as const;

export type MucBaoCao = (typeof CAC_MUC)[number]["ma"];

export function ThanhBaoCao({ dang }: { dang: MucBaoCao }) {
  return (
    <nav className="tab-dem thanh-bao-cao khong-in" aria-label="Các mục báo cáo">
      {CAC_MUC.map((m) => (
        <Link key={m.ma} href={m.duongDan} aria-current={m.ma === dang ? "page" : undefined}>
          {m.nhan}
        </Link>
      ))}
    </nav>
  );
}
