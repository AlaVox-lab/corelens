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
};

export default nextConfig;
