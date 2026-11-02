"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Điều khiển danh sách gắn với địa chỉ trang (#232): ô tìm, menu sắp xếp, ô chọn bộ lọc. Mỗi
// điều khiển chỉ đổi một tham số trên địa chỉ rồi để trang ở máy chủ gọi lại dịch vụ — từ khi
// danh sách có phân trang, lọc trên trình duyệt chỉ lọc được trang đang tải, tức là lọc sai.
//
// Đổi bộ lọc thì quay về trang đầu. Dùng `replace` thay vì `push`: gõ từng chữ trong ô tìm
// không được làm đầy lịch sử của nút lùi.

import { Search } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";

import { MenuXep, type CachXep } from "@/components/viec-can-lam";
import type { NhanCoMa } from "@/lib/kieu";

/** Đổi một tham số trên địa chỉ trang, bỏ `?trang=`. */
function useDoiThamSo() {
  const router = useRouter();
  const duong = usePathname();
  const sp = useSearchParams();
  const [dangTai, chuyen] = useTransition();
  const doi = (ten: string, gt: string | null) => {
    const q = new URLSearchParams(sp.toString());
    if (gt) q.set(ten, gt);
    else q.delete(ten);
    q.delete("trang");
    const chuoi = q.toString();
    chuyen(() => router.replace(chuoi ? `${duong}?${chuoi}` : duong, { scroll: false }));
  };
  return { sp, doi, dangTai };
}

/**
 * Ô tìm phía dịch vụ: gõ xong một nhịp thì tìm, Enter thì tìm ngay. Dịch vụ khớp mã, tiêu đề,
 * người gửi. Địa chỉ đổi từ chỗ khác — chip "Xóa", nút lùi — thì ô theo địa chỉ, nhưng không
 * đè chữ đang gõ dở bằng kết quả của một lần tìm cũ.
 */
export function OTimUrl({ goiY, nhan = "Tìm hồ sơ" }: { goiY: string; nhan?: string }) {
  const { sp, doi } = useDoiThamSo();
  const tuDiaChi = sp.get("q") ?? "";
  const [chu, datChu] = useState(tuDiaChi);
  const daGui = useRef(tuDiaChi);

  useEffect(() => {
    if (tuDiaChi !== daGui.current) {
      daGui.current = tuDiaChi;
      datChu(tuDiaChi);
    }
  }, [tuDiaChi]);

  const gui = (gt: string) => {
    const sach = gt.trim();
    if (sach === daGui.current) return;
    daGui.current = sach;
    doi("q", sach || null);
  };

  useEffect(() => {
    const hen = setTimeout(() => gui(chu), 350);
    return () => clearTimeout(hen);
    // `gui` đọc địa chỉ mới nhất mỗi lần dựng; chỉ hẹn lại khi chữ đổi
  }, [chu]);

  return (
    <form
      role="search"
      className="o-tim"
      onSubmit={(e) => {
        e.preventDefault();
        gui(chu);
      }}
    >
      <Search aria-hidden />
      <input
        className="o-nhap"
        type="search"
        placeholder={goiY}
        aria-label={nhan}
        value={chu}
        onChange={(e) => datChu(e.target.value)}
      />
    </form>
  );
}

/**
 * Menu sắp xếp ghi cách xếp lên `?xep=`. Lựa chọn được nhớ trong trình duyệt như trước #232:
 * mở trang không kèm `?xep=` mà đã từng chọn cách khác mặc định thì chuyển sang cách đó.
 */
export function MenuXepUrl<M extends string>({
  cacCach,
  macDinh,
  khoaNho,
}: {
  cacCach: readonly CachXep<M>[];
  macDinh: M;
  khoaNho: string;
}) {
  const { sp, doi } = useDoiThamSo();
  const tuDiaChi = sp.get("xep") as M | null;
  const hopLe = (m: string | null): m is M => cacCach.some((c) => c.ma === m);
  const dang = hopLe(tuDiaChi) ? tuDiaChi : macDinh;

  useEffect(() => {
    if (tuDiaChi) return;
    try {
      const luu = localStorage.getItem(khoaNho);
      if (hopLe(luu) && luu !== macDinh) doi("xep", luu);
    } catch {
      // Trình duyệt chặn lưu trữ: giữ cách xếp mặc định
    }
    // Chỉ xét một lần khi mở trang
  }, []);

  const chon = (m: M) => {
    try {
      localStorage.setItem(khoaNho, m);
    } catch {
      // Vẫn xếp được trong lần mở này, chỉ không nhớ
    }
    doi("xep", m === macDinh ? null : m);
  };

  return <MenuXep dang={dang} chon={chon} cacCach={cacCach} />;
}

/** Một bộ lọc dạng ô chọn — loại yêu cầu, mức ưu tiên, phòng. Ô chọn gốc dùng được bằng bàn phím. */
export function ChonLoc({ ten, nhan, tatCa, tuyChon }: { ten: string; nhan: string; tatCa: string; tuyChon: NhanCoMa[] }) {
  const { sp, doi } = useDoiThamSo();
  if (tuyChon.length === 0) return null;
  return (
    <select
      className="o-nhap o-chon-loc"
      aria-label={nhan}
      value={sp.get(ten) ?? ""}
      onChange={(e) => doi(ten, e.target.value || null)}
    >
      <option value="">{tatCa}</option>
      {tuyChon.map((o) => (
        <option key={o.code} value={o.code}>
          {o.label}
        </option>
      ))}
    </select>
  );
}
