// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Dòng chân và chip lọc của danh sách có phân trang (#232). Trang ở máy chủ tính sẵn mọi đường
// dẫn từ địa chỉ đang xem (`lib/trang.ts`); hai khối ở đây chỉ hiện ra, không giữ trạng thái nào.

import { ChevronLeft, ChevronRight, X } from "lucide-react";
import Link from "next/link";

/**
 * "Đang xem 51–100 trên 230 hồ sơ · xếp theo độ gấp", kèm trang trước, trang sau. Một trang là đủ
 * thì không có nút chuyển. Nút không đi được thì vẫn giữ chỗ, để nút kia không nhảy vị trí.
 */
export function ChanTrang({
  tong,
  tu,
  soDong,
  donVi = "hồ sơ",
  xep,
  truoc,
  sau,
}: {
  tong: number;
  /** Vị trí dòng đầu của trang, đếm từ 0 (`offset`). */
  tu: number;
  soDong: number;
  donVi?: string;
  /** Tên cách xếp đang dùng, viết thường. */
  xep?: string;
  truoc: string | null;
  sau: string | null;
}) {
  if (tong === 0) return null;
  const den = Math.min(tu + soDong, tong);
  return (
    <nav className="chan-trang khong-in" aria-label="Chuyển trang">
      <p aria-live="polite">
        Đang xem{" "}
        <b>
          {tu + 1}–{den}
        </b>{" "}
        trên <b>{tong}</b> {donVi}
        {xep ? ` · xếp theo ${xep}` : ""}
      </p>
      {truoc || sau ? (
        <span className="chan-trang-nut">
          {truoc ? (
            <Link className="nut nut-nho" href={truoc} rel="prev" scroll={false}>
              <ChevronLeft aria-hidden />
              Trang trước
            </Link>
          ) : (
            <span className="nut nut-nho" aria-disabled="true">
              <ChevronLeft aria-hidden />
              Trang trước
            </span>
          )}
          {sau ? (
            <Link className="nut nut-nho" href={sau} rel="next" scroll={false}>
              Trang sau
              <ChevronRight aria-hidden />
            </Link>
          ) : (
            <span className="nut nut-nho" aria-disabled="true">
              Trang sau
              <ChevronRight aria-hidden />
            </span>
          )}
        </span>
      ) : null}
    </nav>
  );
}

export type ChipDangLoc = { nhan: string; bo: string };

/** Các bộ lọc đang bật, mỗi chip một liên kết bỏ đúng bộ lọc đó; từ hai chip có thêm "Xóa tất cả". */
export function ChipLoc({ chip, xoaHet }: { chip: ChipDangLoc[]; xoaHet: string }) {
  if (chip.length === 0) return null;
  return (
    <div className="chip-loc khong-in" aria-label="Bộ lọc đang bật">
      {chip.map((c) => (
        <Link key={c.bo} className="chip" href={c.bo} scroll={false} aria-label={`Bỏ lọc ${c.nhan}`}>
          {c.nhan}
          <X aria-hidden />
        </Link>
      ))}
      {chip.length > 1 ? (
        <Link className="xoa-het" href={xoaHet} scroll={false}>
          Xóa tất cả
        </Link>
      ) : null}
    </div>
  );
}
