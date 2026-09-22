"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Thanh điều hướng, tô sáng mục đang đứng.
//
// Chạy phía trình duyệt chỉ để đọc đường dẫn hiện tại. Danh sách mục do khung trang
// phía máy chủ dựng sẵn từ `workspaces` của `/me` rồi truyền xuống — tệp này không
// biết người dùng mang vai trò gì.

import Link from "next/link";
import { usePathname } from "next/navigation";

export type MucDieuHuong = { duongDan: string; nhan: string };

/**
 * Mục khớp với đường dẫn hiện tại: khớp dài nhất thắng.
 *
 * `/yeu-cau/moi` khớp cả `/yeu-cau/moi` lẫn `/yeu-cau` — chọn mục dài hơn, không thì
 * trang gửi yêu cầu lại tô sáng mục "Hồ sơ của tôi".
 */
function mucDangDung(duongDan: string, cacMuc: MucDieuHuong[]): string | null {
  const khop = cacMuc
    .map((m) => m.duongDan)
    .filter((d) => duongDan === d || duongDan.startsWith(`${d}/`))
    .sort((a, b) => b.length - a.length);
  return khop[0] ?? null;
}

export function DieuHuong({ cacMuc }: { cacMuc: MucDieuHuong[] }) {
  const dang = mucDangDung(usePathname(), cacMuc);

  return (
    <nav
      className="khung"
      style={{ padding: "0 20px", display: "flex", gap: "2px", overflow: "auto" }}
    >
      {cacMuc.map((m) => {
        const chon = m.duongDan === dang;
        return (
          <Link
            key={m.duongDan}
            href={m.duongDan}
            aria-current={chon ? "page" : undefined}
            style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "11px 14px",
              fontSize: "13.5px",
              fontWeight: 600,
              whiteSpace: "nowrap",
              color: chon ? "var(--ink)" : "var(--ink-3)",
              textDecoration: "none",
              borderBottom: chon ? "2px solid var(--accent)" : "2px solid transparent",
            }}
          >
            {m.nhan}
          </Link>
        );
      })}
    </nav>
  );
}
