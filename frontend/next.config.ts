// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Gói sẵn mọi thứ cần chạy vào một thư mục độc lập. Nhờ đó ảnh chứa không cần
  // mang theo toàn bộ node_modules — ảnh nhẹ hơn nhiều, và bảng chấm PoF mục 4
  // đòi hệ thống chạy được ngoài thư mục mã nguồn.
  //
  // Telemetry của Next tắt bằng biến môi trường NEXT_TELEMETRY_DISABLED, đặt trong
  // Dockerfile — không đặt được ở đây.
  output: "standalone",

  // Tiêu đề bảo mật không đổi theo yêu cầu (#243), phủ mọi đường dẫn kể cả tệp tĩnh. Chính sách
  // nội dung thì cần số dùng một lần mỗi lượt nên đặt ở proxy.ts.
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          // Trình duyệt không đoán lại kiểu nội dung: tệp tải về không bị coi là script
          { key: "X-Content-Type-Options", value: "nosniff" },
          // Gửi sang trang khác chỉ phần gốc của địa chỉ; hồ sơ nào đang mở không lọt ra ngoài.
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          // Bắt buộc HTTPS khi triển khai thật. Trình duyệt bỏ qua tiêu đề này trên http, nên
          // không ảnh hưởng cụm thử ở http://localhost.
          { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
          // Cổng không dùng camera, micro, vị trí — tắt luôn để không trang con nào xin được
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          // Chống nhúng khung cho trình duyệt cũ chưa hiểu `frame-ancestors` của CSP
          { key: "X-Frame-Options", value: "DENY" },
        ],
      },
    ];
  },
};

export default nextConfig;
