"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Thẻ tab trên trang hồ sơ phía nhân viên (#169): "Dòng thời gian" — các mốc hồ sơ đổi — và
// "Trao đổi" — lời nhắn qua lại với người gửi. Hai thứ khác nhau về bản chất (ADR-0005) nên
// tách tab, không trộn. Người đang xem đọc được cuộc nội bộ (#156) thì có thêm tab thứ ba
// "Nội bộ" — tách hẳn khỏi "Trao đổi" để không nhắn nhầm cho người gửi.
//
// Các bảng dựng sẵn ở máy chủ rồi truyền vào; tab chỉ ẩn hiện, không dựng lại, nên chữ đang
// gõ dở trong ô soạn không mất khi chuyển qua lại. Bản in luôn hiện dòng thời gian (CSS
// trong globals.css).

import { Lock } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { DanhDauDaDoc } from "@/components/danh-dau-da-doc";

type Tab = "dong-thoi-gian" | "trao-doi" | "noi-bo";

export function TheLichSu({
  maHoSo,
  dongThoiGian,
  traoDoi,
  soLoiNhan,
  noiBo,
  soNoiBo = 0,
}: {
  maHoSo: number;
  dongThoiGian: React.ReactNode;
  traoDoi: React.ReactNode;
  /** Số lời nhắn với người gửi. */
  soLoiNhan: number;
  /** Cuộc nội bộ — chỉ truyền khi người đang xem đọc được nó (#156). */
  noiBo?: React.ReactNode;
  soNoiBo?: number;
}) {
  const [tab, datTab] = useState<Tab>("dong-thoi-gian");
  const khung = useRef<HTMLDivElement>(null);

  // Mở một cuộc trò chuyện thì cuộn tới lời nhắn mới nhất, như mọi khung chat
  useEffect(() => {
    if (tab === "dong-thoi-gian") return;
    const cuon = khung.current?.querySelector<HTMLElement>(`#bang-${tab} [data-cuon]`);
    if (cuon) cuon.scrollTop = cuon.scrollHeight;
  }, [tab, soLoiNhan, soNoiBo]);

  const cacTab: { ma: Tab; nhan: React.ReactNode; dem?: number }[] = [
    { ma: "dong-thoi-gian", nhan: "Dòng thời gian" },
    { ma: "trao-doi", nhan: "Trao đổi", dem: soLoiNhan },
  ];
  if (noiBo !== undefined) {
    cacTab.push({
      ma: "noi-bo",
      nhan: (
        <>
          <Lock aria-hidden />
          Nội bộ
        </>
      ),
      dem: soNoiBo,
    });
  }

  const bang: { ma: Tab; noi: React.ReactNode; lop?: string }[] = [
    { ma: "dong-thoi-gian", noi: dongThoiGian, lop: "khoi" },
    { ma: "trao-doi", noi: traoDoi },
    ...(noiBo !== undefined ? [{ ma: "noi-bo" as Tab, noi: noiBo }] : []),
  ];

  return (
    <div className="the" ref={khung}>
      <div
        className="tabs"
        role="tablist"
        aria-label="Dòng thời gian và trao đổi của hồ sơ"
        onKeyDown={(e) => {
          // Mũi tên trái phải chuyển tab, như mọi thanh tab
          if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
          const i = cacTab.findIndex((t) => t.ma === tab);
          const buoc = e.key === "ArrowRight" ? 1 : -1;
          const moi = cacTab[(i + buoc + cacTab.length) % cacTab.length].ma;
          datTab(moi);
          document.getElementById(`tab-${moi}`)?.focus();
        }}
      >
        {cacTab.map((t) => (
          <button
            key={t.ma}
            id={`tab-${t.ma}`}
            type="button"
            role="tab"
            aria-selected={tab === t.ma}
            aria-controls={`bang-${t.ma}`}
            tabIndex={tab === t.ma ? 0 : -1}
            onClick={() => datTab(t.ma)}
          >
            {t.nhan}
            {/* "Trao đổi (2)" (#561): số trong ngoặc đọc liền với tên thẻ, không lẫn thành một phần của tên */}
            {t.dem !== undefined && <span className="dem">({t.dem})</span>}
          </button>
        ))}
      </div>

      {bang.map((b) => (
        <div
          key={b.ma}
          id={`bang-${b.ma}`}
          role="tabpanel"
          aria-labelledby={`tab-${b.ma}`}
          data-tab-than={b.ma}
          className={b.lop}
          hidden={tab !== b.ma}
        >
          {b.noi}
        </div>
      ))}
      {/* Mở thẻ nào là đã đọc cuộc đó (#155) — hai cuộc hai mốc riêng (#156) */}
      <DanhDauDaDoc maHoSo={maHoSo} soTin={soLoiNhan} bat={tab === "trao-doi"} />
      {noiBo !== undefined && (
        <DanhDauDaDoc maHoSo={maHoSo} soTin={soNoiBo} bat={tab === "noi-bo"} noiBo />
      )}
    </div>
  );
}
