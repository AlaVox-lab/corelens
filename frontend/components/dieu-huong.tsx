"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Danh sách mục trên thanh bên, tô sáng mục đang đứng (#158).
//
// Chạy phía trình duyệt chỉ để đọc đường dẫn hiện tại. Danh sách mục và số đếm do khung
// trang phía máy chủ dựng sẵn từ `workspaces` của `/me` rồi truyền xuống — tệp này không
// biết người dùng mang vai trò gì.

import { FolderOpen, GitFork, House, Inbox, SquarePen, type LucideIcon } from "lucide-react";
import Link from "next/link";

import type { TenIcon } from "@/lib/khong-gian";

export type MucDieuHuong = {
  duongDan: string;
  nhan: string;
  icon: TenIcon;
  nhom: "chung" | "lam-viec";
  /** Số hồ sơ còn mở ở mục này. Không có thì không hiện số. */
  dem?: number;
};

const ICON: Record<TenIcon, LucideIcon> = {
  "trang-chu": House,
  gui: SquarePen,
  "ho-so": FolderOpen,
  "dieu-phoi": GitFork,
  "phong-ban": Inbox,
};

/**
 * Mục khớp với đường dẫn hiện tại: khớp dài nhất thắng.
 *
 * `/yeu-cau/moi` khớp cả `/yeu-cau/moi` lẫn `/yeu-cau` — chọn mục dài hơn, không thì
 * trang gửi yêu cầu lại tô sáng mục "Hồ sơ của tôi". Mục `/` chỉ khớp đúng trang chủ.
 */
export function mucDangDung(duongDan: string, cacMuc: MucDieuHuong[]): MucDieuHuong | null {
  const khop = cacMuc
    .filter((m) => duongDan === m.duongDan || (m.duongDan !== "/" && duongDan.startsWith(`${m.duongDan}/`)))
    .sort((a, b) => b.duongDan.length - a.duongDan.length);
  return khop[0] ?? null;
}

function Muc({ muc, chon }: { muc: MucDieuHuong; chon: boolean }) {
  const Icon = ICON[muc.icon];
  return (
    <Link className="sb-muc" href={muc.duongDan} aria-current={chon ? "page" : undefined}>
      <Icon aria-hidden />
      <span>{muc.nhan}</span>
      {muc.dem ? <span className="so">{muc.dem}</span> : null}
    </Link>
  );
}

export function DieuHuong({ cacMuc, dang }: { cacMuc: MucDieuHuong[]; dang: MucDieuHuong | null }) {
  const chung = cacMuc.filter((m) => m.nhom === "chung");
  const lamViec = cacMuc.filter((m) => m.nhom === "lam-viec");

  return (
    <nav className="sb-nav" aria-label="Điều hướng chính">
      {chung.map((m) => (
        <Muc key={m.duongDan} muc={m} chon={m === dang} />
      ))}
      {lamViec.length > 0 ? <div className="sb-nhom">Làm việc</div> : null}
      {lamViec.map((m) => (
        <Muc key={m.duongDan} muc={m} chon={m === dang} />
      ))}
    </nav>
  );
}
