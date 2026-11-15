// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Kịch bản kiểm tra giao diện qua ĐĂNG NHẬP THẬT (#238). Không tự đúc cookie phiên: lỗi #87 từng
// bị che đúng vì kiểm thử tự đúc cookie. Mỗi tài khoản đi trọn luồng OIDC qua trang đăng nhập của
// Keycloak một lần, trạng thái trình duyệt lưu lại cho các bài sau.
//
// Bốn cấu hình hiển thị chạy cùng một bộ bài: rộng sáng, rộng tối, hẹp (375 px), và giảm chuyển
// động. Địa chỉ cổng đổi bằng biến CONG — mặc định cụm dựng theo README.

import { defineConfig, devices } from "@playwright/test";

const CONG = process.env.CONG ?? "http://localhost:3000";

// Dùng Chrome cài sẵn trên máy thay trình duyệt Playwright tải về: đặt KENH=chrome
const kenh = process.env.KENH ? { channel: process.env.KENH } : {};
const rong = { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 }, ...kenh };

export default defineConfig({
  testDir: "./kiem",
  outputDir: "ket-qua/tam",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  reporter: [["list"], ["html", { outputFolder: "ket-qua/bao-cao", open: "never" }]],
  use: {
    baseURL: CONG,
    locale: "vi-VN",
    timezoneId: "Asia/Ho_Chi_Minh",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "chuan-bi", testMatch: /chuan-bi\.setup\.ts/, use: rong },
    { name: "rong-sang", dependencies: ["chuan-bi"], testIgnore: [/giam-chuyen-dong/, /xac-thuc-hai-lop/], use: { ...rong, colorScheme: "light" } },
    { name: "rong-toi", dependencies: ["chuan-bi"], testIgnore: [/giam-chuyen-dong/, /xac-thuc-hai-lop/], use: { ...rong, colorScheme: "dark" } },
    {
      name: "hep-sang",
      dependencies: ["chuan-bi"],
      testIgnore: [/giam-chuyen-dong/, /xac-thuc-hai-lop/],
      use: { ...rong, viewport: { width: 375, height: 812 }, colorScheme: "light" },
    },
    {
      name: "giam-chuyen-dong",
      dependencies: ["chuan-bi"],
      testIgnore: /xac-thuc-hai-lop/,
      use: { ...rong, colorScheme: "light", reducedMotion: "reduce" },
    },
    // Xác thực hai lớp (#366): chỉ chạy khi HAI_LOP=1, KHÔNG phụ thuộc bước chuẩn bị — khi bật, tài khoản
    // mẫu bị buộc thiết lập mã nên bước chuẩn bị không đăng nhập được. Xem kiem/xac-thuc-hai-lop.spec.ts
    { name: "hai-lop", testMatch: /xac-thuc-hai-lop\.spec\.ts/, use: { ...rong, colorScheme: "light" } },
  ],
});
