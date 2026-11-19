// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khung ngoài cùng của cổng người dùng: phông chữ và bộ kiểu trình bày.
//
// PHÔNG CHỮ TẢI LÚC DỰNG, KHÔNG TẢI LÚC CHẠY. `next/font/google` kéo tệp phông về
// trong lúc `next build` rồi phục vụ chúng từ chính máy chủ của hệ thống. Ba cái lợi,
// theo thứ tự quan trọng:
//
//   1. Trình duyệt người dùng không gọi sang máy chủ Google, nên địa chỉ IP của nhân
//      viên không chảy ra ngoài mỗi lần họ mở một hồ sơ nội bộ. Với một hệ thống vận
//      hành nội bộ doanh nghiệp, đó không phải chuyện nhỏ.
//   2. Hệ thống chạy được trong mạng nội bộ không có đường ra Internet.
//   3. Chữ không nhảy khi trang vừa hiện.
//
// Đổi lại, lệnh `next build` cần đường mạng — nhưng nó đã cần sẵn cho `npm ci` rồi,
// nên không thêm ràng buộc mới nào lên người dựng lại từ mã nguồn.

import type { Metadata } from "next";
import { Be_Vietnam_Pro, IBM_Plex_Mono } from "next/font/google";
import { headers } from "next/headers";

import "./globals.css";

// Be Vietnam Pro dựng riêng cho tiếng Việt: dấu thanh đặt cân, không chồng lên dấu
// mũ ở những chữ như "ế" hay "ộ". Phông phổ thông phương Tây đặt dấu thanh bằng cách
// ghép cơ học nên hai dấu hay đụng nhau.
const beVietnam = Be_Vietnam_Pro({
  subsets: ["vietnamese", "latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-be-vietnam",
});

// Phông đều nét cho mã hồ sơ, mốc giờ và con số thời lượng. Chúng cần xếp thẳng cột
// khi đặt cạnh nhau trong danh sách.
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
  variable: "--font-plex-mono",
});

export const metadata: Metadata = {
  title: "Corelens — Cổng yêu cầu nội bộ",
  description:
    "Tiếp nhận và điều phối tập trung mọi loại yêu cầu nội bộ trong doanh nghiệp.",
};

// Đọc lựa chọn sáng/tối đã lưu và đặt lên <html> TRƯỚC KHI trình duyệt vẽ trang (#158).
// Đặt muộn hơn — trong một component React — thì người chọn tối thấy trang trắng nháy
// lên rồi mới tối lại. Khóa lưu trùng với `KHOA_CHE_DO` trong khung-ung-dung.tsx.
//
// Cùng lý do, đọc luôn lựa chọn mở dòng thời gian (#189) — khóa trùng `KHOA_DONG_THOI_GIAN`
// trong nut-dong-thoi-gian.tsx. Không có thì dòng thời gian thu gọn, chỉ hiện bước hiện tại.
const DOC_CHE_DO = `try{var d=document.documentElement,t=localStorage.getItem("dxlab-theme");if(t==="dark"||t==="light")d.dataset.theme=t;if(localStorage.getItem("dxlab-dong-thoi-gian")==="mo")d.dataset.dongThoiGian="mo"}catch(e){}`;

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  // Số dùng một lần của yêu cầu này, do proxy.ts đặt (#243). Chính sách nội dung chỉ cho chạy script
  // mang đúng số; đoạn chống nháy bên dưới do ta tự viết nên phải gắn tay, còn script của Next thì
  // Next tự gắn. Đọc header khiến mọi trang dựng động — đúng điều CSP theo lượt đòi hỏi.
  const nonce = (await headers()).get("x-nonce") ?? undefined;

  return (
    // suppressHydrationWarning: đoạn mã đầu trang đặt `data-theme` trước khi React nhận
    // trang, nên thuộc tính đó khác bản dựng ở máy chủ là đúng ý, không phải lỗi.
    <html lang="vi" className={`${beVietnam.variable} ${plexMono.variable}`} suppressHydrationWarning>
      <head>
        <script nonce={nonce} dangerouslySetInnerHTML={{ __html: DOC_CHE_DO }} />
      </head>
      <body
        style={{
          // Ghi đè hai biến phông trong globals.css bằng tên lớp mà next/font sinh ra.
          // Phần dự phòng phía sau giữ nguyên, phòng khi tệp phông không tải được.
          ["--font" as string]: `var(--font-be-vietnam), "Segoe UI", system-ui, sans-serif`,
          ["--mono" as string]: `var(--font-plex-mono), ui-monospace, SFMono-Regular, monospace`,
        }}
      >
        {children}
      </body>
    </html>
  );
}
