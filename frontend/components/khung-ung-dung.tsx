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
import { createContext, useContext, useEffect, useState } from "react";
import { createPortal } from "react-dom";

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

/** Trang con đặt tên cấp con lên thanh đầu, ví dụ mã hồ sơ (#169). */
const DatTenCon = createContext<(ten: string | null) => void>(() => {});

/**
 * Đặt tên cấp con cho thanh đầu trang — "Phòng ban › YC-2026-0005" ở trang một hồ sơ,
 * "Phòng ban · Công nghệ thông tin" ở trang của chính mục (#170). Trang chạy ở máy chủ
 * nên không chạm được thanh đầu; thành phần rỗng này chuyển tên lên qua context, và trả
 * tên về mặc định khi rời trang.
 */
export function TenCapCon({ ten }: { ten: string }) {
  const dat = useContext(DatTenCon);
  useEffect(() => {
    dat(ten);
    return () => dat(null);
  }, [ten, dat]);
  return null;
}

/** Chỗ bên phải thanh đầu trang, nơi trang con đặt nút riêng của nó. */
const ID_THANH_DAU_PHAI = "thanh-dau-phai";

/**
 * Đặt nút lên bên phải thanh đầu trang — ví dụ "Mở trong hộp thư" ở trang hồ sơ (#155).
 * Dùng portal: nút vẫn thuộc trang (rời trang là mất), chỉ hiện ở thanh đầu.
 */
export function NutThanhDau({ children }: { children: React.ReactNode }) {
  const [cho, datCho] = useState<HTMLElement | null>(null);
  useEffect(() => datCho(document.getElementById(ID_THANH_DAU_PHAI)), []);
  return cho ? createPortal(children, cho) : null;
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
  const [tenCon, setTenCon] = useState<string | null>(null);

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
              {tenCon ? <span className="mono">{tenCon}</span> : <span>Hồ sơ</span>}
            </p>
          ) : (
            // Ở trang của mục, tên con là phần nói rõ thêm: "Phòng ban · Công nghệ thông tin"
            <p className="tieu">{tenCon ? `${dang.nhan} · ${tenCon}` : dang.nhan}</p>
          )}
          <div className="phai" id={ID_THANH_DAU_PHAI} />
        </header>

        <main className="vung vao">
          <DatTenCon.Provider value={setTenCon}>{children}</DatTenCon.Provider>
        </main>
      </div>
    </div>
  );
}
