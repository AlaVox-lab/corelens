// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Trang tài liệu của DX-OS Lab (#279). Chia theo người đọc như trang tài liệu của các nền tảng
// nguồn mở lớn: bắt đầu, cài đặt, hướng dẫn theo vai, quản trị, phát triển, tham khảo. Nội dung
// kỹ thuật sâu (kiến trúc, luồng nghiệp vụ, ADR) vẫn nằm ở `docs/` của kho — trang này dẫn sang,
// không chép lại, để một sự thật chỉ nằm một chỗ.

import starlight from "@astrojs/starlight";
import { defineConfig } from "astro/config";

export default defineConfig({
  // Địa chỉ GitHub Pages của kho, bật khi kho chuyển công khai. Liên kết giữa các trang viết tương
  // đối nên trang chạy đúng dưới tiền tố này lẫn khi đổi sang tên miền riêng.
  site: "https://alavox-lab.github.io",
  base: "/dx-os-lab",
  integrations: [
    starlight({
      title: "DX-OS Lab",
      description: "Cổng vận hành yêu cầu nội bộ — tài liệu cài đặt, sử dụng và phát triển",
      locales: { root: { label: "Tiếng Việt", lang: "vi" } },
      social: [{ icon: "github", label: "GitHub", href: "https://github.com/AlaVox-lab/dx-os-lab" }],
      editLink: { baseUrl: "https://github.com/AlaVox-lab/dx-os-lab/edit/main/docs-site/" },
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
