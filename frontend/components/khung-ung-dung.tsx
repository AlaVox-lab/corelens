"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khung ứng dụng phía trình duyệt (#158): thanh bên, thanh đầu trang, ngăn kéo trên điện
// thoại và nút sáng/tối.
//
// Phần cần dữ liệu — danh tính, danh sách mục, số đếm — do `khung-lam-viec.tsx` lấy ở máy
// chủ rồi truyền xuống. Tệp này chỉ giữ thứ thuộc về trình duyệt: đường dẫn đang mở,
// ngăn kéo đang mở hay đóng, và lựa chọn sáng/tối lưu trên máy người dùng.

import { ChevronRight, LogOut, Menu, Moon, Sun } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { DieuHuong, mucDangDung, type MucDieuHuong } from "@/components/dieu-huong";

/** Khóa lưu lựa chọn sáng/tối. Đoạn mã đầu trang trong `app/layout.tsx` đọc cùng khóa. */
export const KHOA_CHE_DO = "dxlab-theme";

/**
 * Đổi sáng/tối và nhớ lựa chọn. Chưa từng bấm thì trang theo thiết lập của hệ điều hành
 * (CSS lo phần đó); bấm rồi thì thuộc tính `data-theme` trên `<html>` thắng.
 */
function doiCheDo() {
  const html = document.documentElement;
  const dangToi =
    html.dataset.theme === "dark" ||
    (html.dataset.theme !== "light" && matchMedia("(prefers-color-scheme: dark)").matches);
  const moi = dangToi ? "light" : "dark";

  html.classList.add("doi-mau");
  html.dataset.theme = moi;
  try {
    localStorage.setItem(KHOA_CHE_DO, moi);
  } catch {
    // Trình duyệt chặn lưu trữ: vẫn đổi được trong lần mở này, chỉ không nhớ.
  }
  window.setTimeout(() => html.classList.remove("doi-mau"), 260);
}

export type NguoiDung = {
  ten: string;
  chuCai: string;
  /** Màu ô chữ cái, 1–5. */
  mau: number;
  /** Dòng phụ dưới tên: phòng ban nếu có, không thì thư điện tử. */
  phu: string | null;
};

export function KhungUngDung({
  cacMuc,
  nguoi,
  children,
}: Readonly<{
  cacMuc: MucDieuHuong[];
  nguoi: NguoiDung;
  children: React.ReactNode;
}>) {
  const duongDan = usePathname();
  const dang = mucDangDung(duongDan, cacMuc);
  const [moMenu, setMoMenu] = useState(false);

  // Bấm một mục trong ngăn kéo là sang trang khác: đóng ngăn kéo lại
  useEffect(() => setMoMenu(false), [duongDan]);

  useEffect(() => {
    if (!moMenu) return;
    const dong = (e: KeyboardEvent) => e.key === "Escape" && setMoMenu(false);
    document.addEventListener("keydown", dong);
    return () => document.removeEventListener("keydown", dong);
  }, [moMenu]);

  // Đứng đúng trang của mục thì thanh đầu ghi tên mục; đi sâu hơn (trang một hồ sơ) thì
  // ghi tên mục thành liên kết để quay lại danh sách.
  const sauHon = dang !== null && duongDan !== dang.duongDan;

  return (
    <div className="app" data-menu-mo={moMenu ? "" : undefined}>
      <aside className="sb khong-in" aria-label="Thanh bên">
        <div className="sb-dau">
          <span className="logo">YC</span>
          <span className="sb-ten">
            <b>Cổng yêu cầu nội bộ</b>
            <span>DX-OS Lab</span>
          </span>
        </div>

        <DieuHuong cacMuc={cacMuc} dang={dang} />

        <div className="sb-chan">
          <button className="sb-muc nut-mau" type="button" onClick={doiCheDo}>
            <span className="khi-sang">
              <Moon aria-hidden />
              <span>Chế độ tối</span>
            </span>
            <span className="khi-toi">
              <Sun aria-hidden />
              <span>Chế độ sáng</span>
            </span>
          </button>
          <div className="nguoi">
            <span className="av" data-c={nguoi.mau} aria-hidden>
              {nguoi.chuCai}
            </span>
            <span className="ten">
              <b>{nguoi.ten}</b>
              {nguoi.phu ? <span>{nguoi.phu}</span> : null}
            </span>
            <a className="nut-icon" href="/api/auth/logout" aria-label="Đăng xuất" title="Đăng xuất">
              <LogOut aria-hidden />
            </a>
          </div>
        </div>
      </aside>
      <div className="phu-mo khong-in" aria-hidden onClick={() => setMoMenu(false)} />

      <div className="noi-dung">
        <header className="thanh-dau khong-in">
          <button
            className="nut-icon nut-menu"
            type="button"
            aria-label="Mở menu"
            aria-expanded={moMenu}
            onClick={() => setMoMenu(true)}
          >
            <Menu aria-hidden />
          </button>
          {dang === null ? null : sauHon ? (
            <p className="cha">
              <Link href={dang.duongDan}>{dang.nhan}</Link>
              <ChevronRight aria-hidden />
              <span>Hồ sơ</span>
            </p>
          ) : (
            <p className="tieu">{dang.nhan}</p>
          )}
        </header>

        <main className="vung vao">{children}</main>
      </div>
    </div>
  );
}
