"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Thẻ hai tab trên trang hồ sơ phía nhân viên (#169): "Dòng thời gian" — các mốc hồ sơ
// đổi — và "Trao đổi" — lời nhắn qua lại. Hai thứ khác nhau về bản chất (ADR-0005) nên
// tách tab, không trộn.
//
// Cả hai bảng dựng sẵn ở máy chủ rồi truyền vào; tab chỉ ẩn hiện, không dựng lại, nên chữ
// đang gõ dở trong ô soạn không mất khi chuyển qua lại. Bản in luôn hiện dòng thời gian
// (CSS trong globals.css).

import { useEffect, useRef, useState } from "react";

import { DanhDauDaDoc } from "@/components/danh-dau-da-doc";

type Tab = "dong-thoi-gian" | "trao-doi";

export function TheLichSu({
  maHoSo,
  dongThoiGian,
  traoDoi,
  soLoiNhan,
}: {
  maHoSo: number;
  dongThoiGian: React.ReactNode;
  traoDoi: React.ReactNode;
  soLoiNhan: number;
}) {
  const [tab, datTab] = useState<Tab>("dong-thoi-gian");
  const bangTraoDoi = useRef<HTMLDivElement>(null);

  // Mở trao đổi thì cuộn tới lời nhắn mới nhất, như mọi khung chat
  useEffect(() => {
    if (tab !== "trao-doi") return;
    const cuon = bangTraoDoi.current?.querySelector<HTMLElement>("[data-cuon]");
    if (cuon) cuon.scrollTop = cuon.scrollHeight;
  }, [tab, soLoiNhan]);

  const cacTab: { ma: Tab; nhan: string; dem?: number }[] = [
    { ma: "dong-thoi-gian", nhan: "Dòng thời gian" },
    { ma: "trao-doi", nhan: "Trao đổi", dem: soLoiNhan },
  ];

  return (
    <div className="the">
      <div
        className="tabs"
        role="tablist"
        aria-label="Lịch sử hồ sơ"
        onKeyDown={(e) => {
          // Mũi tên trái phải chuyển tab, như mọi thanh tab
          if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
          const moi = tab === "dong-thoi-gian" ? "trao-doi" : "dong-thoi-gian";
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
            {t.dem !== undefined && <span className="dem">{t.dem}</span>}
          </button>
        ))}
      </div>

      <div
        id="bang-dong-thoi-gian"
        role="tabpanel"
        aria-labelledby="tab-dong-thoi-gian"
        data-tab-than="dong-thoi-gian"
        className="khoi"
        hidden={tab !== "dong-thoi-gian"}
      >
        {dongThoiGian}
      </div>
      <div
        id="bang-trao-doi"
        ref={bangTraoDoi}
        role="tabpanel"
        aria-labelledby="tab-trao-doi"
        data-tab-than="trao-doi"
        hidden={tab !== "trao-doi"}
      >
        {traoDoi}
      </div>
      {/* Mở thẻ Trao đổi là đã đọc lời nhắn của hồ sơ (#155) */}
      <DanhDauDaDoc maHoSo={maHoSo} soTin={soLoiNhan} bat={tab === "trao-doi"} />
    </div>
  );
}
