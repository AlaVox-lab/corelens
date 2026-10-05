"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Danh sách mục trên thanh bên, tô sáng mục đang đứng (#158).
//
// Chạy phía trình duyệt chỉ để đọc đường dẫn hiện tại. Danh sách mục và số đếm do khung
// trang phía máy chủ dựng sẵn từ `workspaces` của `/me` rồi truyền xuống — tệp này không
// biết người dùng mang vai trò gì.
//
// Riêng mục Hộp thư (#155) tự hỏi lại số chưa đọc khoảng 12 giây một lần khi trang đang
// hiện, và hỏi ngay khi có nơi vừa đánh dấu đã đọc — con số không đợi chuyển trang.

import {
  FolderOpen,
  GitFork,
  House,
  Inbox,
  MessagesSquare,
  SquarePen,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { SU_KIEN_HOP_THU } from "@/components/danh-dau-da-doc";
import type { TenIcon } from "@/lib/khong-gian";

export type MucDieuHuong = {
  duongDan: string;
  nhan: string;
  icon: TenIcon;
  nhom: "chung" | "lam-viec";
  /** Số hồ sơ còn mở ở mục này — hay số tin chưa đọc ở Hộp thư. Không có thì không hiện. */
  dem?: number;
};

/** Mỗi bao lâu thanh bên hỏi lại số chưa đọc, khi trang đang hiện. */
const CHU_KY_HOI_MS = 12_000;

const ICON: Record<TenIcon, LucideIcon> = {
  "trang-chu": House,
  gui: SquarePen,
  "ho-so": FolderOpen,
  "dieu-phoi": GitFork,
  "phong-ban": Inbox,
  "hop-thu": MessagesSquare,
};

/** Số chưa đọc của Hộp thư, bắt đầu từ con số máy chủ dựng sẵn rồi tự hỏi lại. */
function useSoChuaDoc(banDau: number | undefined): number | undefined {
  const [so, datSo] = useState(banDau);
  useEffect(() => datSo(banDau), [banDau]);

  useEffect(() => {
    let huy = false;
    const hoi = async () => {
      if (document.visibilityState !== "visible") return;
      try {
        const kq = (await (await fetch("/api/hop-thu/chua-doc", { cache: "no-store" })).json()) as {
          unread: number | null;
        };
        if (!huy && kq.unread !== null) datSo(kq.unread);
      } catch {
        // Mạng chập chờn: giữ con số đang hiện, lượt sau hỏi lại
      }
    };
    const dongHo = window.setInterval(hoi, CHU_KY_HOI_MS);
    window.addEventListener(SU_KIEN_HOP_THU, hoi);
    document.addEventListener("visibilitychange", hoi);
    return () => {
      huy = true;
      window.clearInterval(dongHo);
      window.removeEventListener(SU_KIEN_HOP_THU, hoi);
      document.removeEventListener("visibilitychange", hoi);
    };
  }, []);

  return so;
}

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

function Muc({ muc, chon, dem }: { muc: MucDieuHuong; chon: boolean; dem?: number }) {
  const Icon = ICON[muc.icon];
  const so = dem ?? muc.dem;
  const laHopThu = muc.icon === "hop-thu";
  return (
    <Link
      className="sb-muc"
      href={muc.duongDan}
      aria-current={chon ? "page" : undefined}
      aria-label={laHopThu && so ? `${muc.nhan}, ${so} tin chưa đọc` : undefined}
    >
      <Icon aria-hidden />
      <span>{muc.nhan}</span>
      {so ? (
        <span className="so" data-moi={laHopThu ? "" : undefined}>
          {so}
        </span>
      ) : null}
    </Link>
  );
}

export function DieuHuong({ cacMuc, dang }: { cacMuc: MucDieuHuong[]; dang: MucDieuHuong | null }) {
  const chung = cacMuc.filter((m) => m.nhom === "chung");
  const lamViec = cacMuc.filter((m) => m.nhom === "lam-viec");
  const soChuaDoc = useSoChuaDoc(cacMuc.find((m) => m.icon === "hop-thu")?.dem);
  const demCua = (m: MucDieuHuong) => (m.icon === "hop-thu" ? soChuaDoc : undefined);

  return (
    <nav className="sb-nav" aria-label="Điều hướng chính">
      {chung.map((m) => (
        <Muc key={m.duongDan} muc={m} chon={m === dang} dem={demCua(m)} />
      ))}
      {lamViec.length > 0 ? <div className="sb-nhom">Làm việc</div> : null}
      {lamViec.map((m) => (
        <Muc key={m.duongDan} muc={m} chon={m === dang} dem={demCua(m)} />
      ))}
    </nav>
  );
}
