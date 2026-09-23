// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Nút lọc hàng đợi, kèm số hồ sơ. Dùng chung cho hàng đợi điều phối (#82) và hàng đợi
// phòng ban (#83). Nút là một liên kết chứ không phải nút bấm: bộ lọc nằm trên địa chỉ
// trang, nên tải lại hay gửi đường dẫn cho đồng nghiệp đều giữ nguyên bộ lọc.

import Link from "next/link";

export function NutLoc({
  href,
  nhan,
  so,
  chon,
}: {
  href: string;
  nhan: string;
  so: number;
  chon: boolean;
}) {
  return (
    <Link
      href={href}
      aria-current={chon ? "page" : undefined}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "8px",
        padding: "7px 12px",
        borderRadius: "999px",
        fontSize: "13px",
        fontWeight: 600,
        whiteSpace: "nowrap",
        textDecoration: "none",
        background: chon ? "var(--surface)" : "transparent",
        color: chon ? "var(--ink)" : "var(--ink-2)",
        border: chon ? "1px solid var(--line-2)" : "1px solid var(--line)",
        boxShadow: chon ? "var(--shadow)" : "none",
      }}
    >
      {nhan}
      <span
        className="mono"
        style={{
          minWidth: "20px",
          padding: "0 6px",
          borderRadius: "999px",
          fontSize: "11.5px",
          textAlign: "center",
          background: chon ? "var(--accent)" : "var(--surface-3)",
          color: chon ? "var(--accent-on)" : "var(--ink-3)",
        }}
      >
        {so}
      </span>
    </Link>
  );
}
