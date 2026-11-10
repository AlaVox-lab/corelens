"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Ngăn danh sách hồ sơ của màn quy trình thực tế (#315): bấm một trạng thái, một nhánh lệch hay một
// đường đi thì danh sách hồ sơ tương ứng hiện ở ngăn bên phải. Dùng lại kiểu dáng của ngăn xem nhanh
// ở hàng đợi (#233, lớp `.ngan`): cùng vị trí, cùng hiệu ứng trượt vào/ra, màn hẹp thì toàn màn hình.
//
// Khác ngăn xem nhanh ở chỗ nội dung do phía gọi dựng và không nằm trên địa chỉ trang. Ngăn chỉ lo
// phần của trình duyệt:
//
//   - Esc đóng ngăn — trừ khi đang gõ trong ô nhập, hay lớp phủ toàn màn hình của sơ đồ đang mở
//     (lớp phủ nhận Esc trước)
//   - tiêu điểm: mở ngăn, hay đổi sang danh sách khác, thì tiêu điểm vào tiêu đề; đóng thì trả về
//     đúng chỗ đã bấm để mở
//
// Ngăn không che nội dung ở màn rộng: trang chừa chỗ bên phải cho nó, nên các khối và sơ đồ vẫn bấm được.
//
// Gắn thẳng vào `<body>` như ngăn xem nhanh: khung nội dung có hiệu ứng hiện trang mang `transform`,
// và `position: fixed` bên trong phần tử có `transform` tính theo phần tử đó chứ không theo cửa sổ.

import { X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { useAnCham } from "@/lib/chuyen-dong";

function dangGo(dich: EventTarget | null): boolean {
  if (!(dich instanceof HTMLElement)) return false;
  return dich.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(dich.tagName);
}

export function NganHoSoQuyTrinh({
  idTieuDe,
  tieuDe,
  khoaNoiDung,
  onDong,
  children,
}: {
  idTieuDe: string;
  tieuDe: string;
  /** Đổi giá trị này (danh sách khác) thì tiêu điểm vào lại tiêu đề. */
  khoaNoiDung: string;
  onDong: () => void;
  children: React.ReactNode;
}) {
  // `document` chỉ có ở trình duyệt: lần dựng ở máy chủ chưa có ngăn
  const [daGan, datDaGan] = useState(false);
  useEffect(() => datDaGan(true), []);

  const [dangAn, an] = useAnCham();
  const dong = () => an(onDong);

  // Chỗ đã bấm để mở ngăn, để trả tiêu điểm khi đóng
  const noiMo = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (!daGan) return;
    noiMo.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    return () => {
      const el = noiMo.current;
      if (el && document.contains(el)) el.focus({ preventScroll: true });
    };
  }, [daGan]);

  // Báo cho CSS chừa chỗ bên phải trang (xem `html[data-qt-ngan]` ở globals.css)
  useEffect(() => {
    if (!daGan) return;
    document.documentElement.dataset.qtNgan = "";
    return () => {
      delete document.documentElement.dataset.qtNgan;
    };
  }, [daGan]);

  useEffect(() => {
    if (daGan) document.getElementById(idTieuDe)?.focus({ preventScroll: true });
  }, [daGan, idTieuDe, khoaNoiDung]);

  useEffect(() => {
    const phim = (e: KeyboardEvent) => {
      if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey || dangGo(e.target)) return;
      if (e.key !== "Escape" || document.querySelector("[data-toan-man]")) return;
      e.preventDefault();
      dong();
    };
    document.addEventListener("keydown", phim);
    return () => document.removeEventListener("keydown", phim);
  });

  if (!daGan) return null;
  return createPortal(
    <aside className="ngan" aria-labelledby={idTieuDe} data-an={dangAn ? "" : undefined}>
      <div className="ngan-dau">
        <button type="button" className="nut-icon" onClick={dong} aria-label="Đóng danh sách hồ sơ (Esc)">
          <X aria-hidden />
        </button>
        <h2 id={idTieuDe} tabIndex={-1} className="qt-ngan-tieu-de">
          {tieuDe}
        </h2>
      </div>
      <div className="ngan-than">{children}</div>
    </aside>,
    document.body,
  );
}
