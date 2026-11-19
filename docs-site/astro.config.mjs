// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Trang tài liệu của Corelens (#279). Chia theo người đọc như trang tài liệu của các nền tảng
// nguồn mở lớn: bắt đầu, cài đặt, hướng dẫn theo vai, quản trị, phát triển, tham khảo. Nội dung
// kỹ thuật sâu (kiến trúc, luồng nghiệp vụ, ADR) vẫn nằm ở `docs/` của kho — trang này dẫn sang,
// không chép lại, để một sự thật chỉ nằm một chỗ.

import starlight from "@astrojs/starlight";
import { defineConfig } from "astro/config";

// Địa chỉ trang và đường gốc lấy từ biến môi trường lúc dựng (#381), để một mã nguồn đăng được ở
// nhiều nơi — cách đăng ở CONTRIBUTING.md mục "Đăng trang tài liệu":
//   - DOCS_SITE_URL  — địa chỉ đầy đủ, ví dụ `https://corelens.vercel.app`. Bỏ trống thì dùng tên miền
//     chính thức mà Vercel tự cấp (VERCEL_PROJECT_PRODUCTION_URL); dựng ở máy thì để trống.
//   - DOCS_BASE_PATH — đường gốc, mặc định `/` (Vercel, tên miền riêng). GitHub Pages của kho cần
//     `/corelens`.
// Liên kết giữa các trang và ảnh đều viết tương đối hoặc qua `import`, nên trang chạy đúng với mọi
// đường gốc.
function diaChiTrang() {
  const dat = process.env.DOCS_SITE_URL?.trim();
  if (dat) return dat;
  const vercel = process.env.VERCEL_PROJECT_PRODUCTION_URL?.trim();
  return vercel ? `https://${vercel}` : undefined;
}

function duongGoc() {
  const dat = process.env.DOCS_BASE_PATH?.trim().replace(/\/+$/, "");
  if (!dat) return "/";
  return dat.startsWith("/") ? dat : `/${dat}`;
}

export default defineConfig({
  site: diaChiTrang(),
  base: duongGoc(),
  integrations: [
    starlight({
      title: "Corelens",
      description: "Cổng vận hành yêu cầu nội bộ — tài liệu cài đặt, sử dụng và phát triển",
      locales: { root: { label: "Tiếng Việt", lang: "vi" } },
      social: [{ icon: "github", label: "GitHub", href: "https://github.com/AlaVox-lab/corelens" }],
      editLink: { baseUrl: "https://github.com/AlaVox-lab/corelens/edit/main/docs-site/" },
      customCss: ["./src/styles/nhan-dien.css"],
      lastUpdated: true,
      sidebar: [
        { label: "Bắt đầu", items: [{ autogenerate: { directory: "bat-dau" } }] },
        { label: "Cài đặt và vận hành", items: [{ autogenerate: { directory: "cai-dat" } }] },
        { label: "Hướng dẫn sử dụng", items: [{ autogenerate: { directory: "huong-dan" } }] },
        { label: "Quản trị và tùy biến", items: [{ autogenerate: { directory: "quan-tri" } }] },
        { label: "Phát triển", items: [{ autogenerate: { directory: "phat-trien" } }] },
        { label: "Tham khảo", items: [{ autogenerate: { directory: "tham-khao" } }] },
      ],
    }),
  ],
});
