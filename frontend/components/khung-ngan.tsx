"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khung ngăn xem nhanh bên phải hàng đợi (#233). Nội dung ngăn dựng ở máy chủ từ đúng các khối
// của trang chi tiết; khung này chỉ lo phần của trình duyệt:
//
//   - đầu ngăn: đóng, hồ sơ trước và sau theo thứ tự danh sách ("2 trên 14"), mở trang đầy đủ
//   - phím mũi tên sang hồ sơ trước/sau, Esc đóng ngăn — trừ khi đang gõ trong ô nhập, hay một
//     menu khác đã nhận phím đó
//   - tiêu điểm: mở ngăn hay sang hồ sơ khác thì tiêu điểm vào tiêu đề hồ sơ; đóng thì trả về
//     đúng dòng của hồ sơ đó trong danh sách
//
// Hồ sơ đang xem nằm trên địa chỉ trang (`?xem=`), nên ngăn gửi đường dẫn được. Ngăn không che
// danh sách bằng lớp phủ: bấm dòng khác là đổi hồ sơ trong ngăn.
//
// Ngăn gắn thẳng vào `<body>`: khung nội dung có hiệu ứng hiện trang mang `transform`, và
// `position: fixed` bên trong một phần tử có `transform` tính theo phần tử đó chứ không theo
// khung trình duyệt — ngăn sẽ lệch xuống và khối thao tác ở đáy rơi khỏi màn hình.

import { ChevronLeft, ChevronRight, ExternalLink, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

export type DieuHuongNgan = {
  /** Vị trí trong danh sách đang lọc; `null` khi hồ sơ không còn trong danh sách. */
  viTri: { so: number; tong: number } | null;
  truoc: string | null;
  sau: string | null;
  /** Đường dẫn danh sách khi đóng ngăn — giữ bộ lọc và trang. */
  dong: string;
  dayDu: string;
};

/** Phím đến từ chỗ đang gõ thì không phải phím điều hướng. */
function dangGo(dich: EventTarget | null): boolean {
  if (!(dich instanceof HTMLElement)) return false;
  return dich.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(dich.tagName);
}

export function KhungNgan({
  maHoSo,
  idTieuDe,
  dieuHuong,
  chan,
  children,
}: {
  maHoSo: number;
  idTieuDe: string;
  dieuHuong: DieuHuongNgan;
  /** Khối thao tác cố định ở đáy ngăn. */
  chan?: React.ReactNode;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { viTri, truoc, sau, dong, dayDu } = dieuHuong;
  // `document` chỉ có ở trình duyệt: lần dựng ở máy chủ chưa có ngăn
  const [daGan, datDaGan] = useState(false);
  useEffect(() => datDaGan(true), []);

  const dongNgan = () => {
    // Trả tiêu điểm về đúng dòng trước khi ngăn biến mất — dòng vẫn ở đó, danh sách không dựng lại
    document.querySelector<HTMLElement>(`[data-xem-dong="${maHoSo}"]`)?.focus();
    router.replace(dong, { scroll: false });
  };

  useEffect(() => {
    document.getElementById(idTieuDe)?.focus({ preventScroll: true });
    // Duyệt bằng phím thì dòng đang xem luôn nằm trong vùng nhìn của danh sách
    document.querySelector(`[data-xem-dong="${maHoSo}"]`)?.closest("tr")?.scrollIntoView({ block: "nearest" });
  }, [maHoSo, idTieuDe, daGan]);

  useEffect(() => {
    const phim = (e: KeyboardEvent) => {
      if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey || dangGo(e.target)) return;
      // Menu sắp xếp hay menu thao tác đang mở tự lo phím của nó
      if (document.querySelector('[aria-haspopup="menu"][aria-expanded="true"], details.menu-thao-tac[open]')) return;
      if (e.key === "Escape") {
        e.preventDefault();
        dongNgan();
      } else if ((e.key === "ArrowDown" || e.key === "ArrowRight") && sau) {
        e.preventDefault();
        router.replace(sau, { scroll: false });
      } else if ((e.key === "ArrowUp" || e.key === "ArrowLeft") && truoc) {
        e.preventDefault();
        router.replace(truoc, { scroll: false });
      }
    };
    document.addEventListener("keydown", phim);
    return () => document.removeEventListener("keydown", phim);
  });

  if (!daGan) return null;
  return createPortal(
    <aside className="ngan" aria-labelledby={idTieuDe}>
      <div className="ngan-dau">
        <button type="button" className="nut-icon" onClick={dongNgan} aria-label="Đóng xem nhanh (Esc)">
          <X aria-hidden />
        </button>
        <nav className="ngan-di" aria-label="Hồ sơ trước và sau">
          {truoc ? (
            <Link className="nut-icon" href={truoc} replace scroll={false} aria-label="Hồ sơ trước">
              <ChevronLeft aria-hidden />
            </Link>
          ) : (
            <span className="nut-icon" aria-disabled="true">
              <ChevronLeft aria-hidden />
            </span>
          )}
          <span className="ngan-vi-tri" aria-live="polite">
            {viTri ? `${viTri.so} trên ${viTri.tong}` : "Không còn trong danh sách"}
          </span>
          {sau ? (
            <Link className="nut-icon" href={sau} replace scroll={false} aria-label="Hồ sơ sau">
              <ChevronRight aria-hidden />
            </Link>
          ) : (
            <span className="nut-icon" aria-disabled="true">
              <ChevronRight aria-hidden />
            </span>
          )}
        </nav>
        <Link className="nut nut-nho" href={dayDu}>
          Mở trang đầy đủ
          <ExternalLink aria-hidden />
        </Link>
      </div>
      <div className="ngan-than">{children}</div>
      {chan ? <div className="ngan-chan">{chan}</div> : null}
    </aside>,
    document.body,
  );
}
