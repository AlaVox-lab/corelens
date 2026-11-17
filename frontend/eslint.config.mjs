// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// ESLint cho cổng người dùng (#382): bộ cấu hình chính thức của Next.js (`eslint-config-next`, MIT) —
// luật React, hook, khả năng truy cập, Core Web Vitals và TypeScript. Next 16 bỏ `next lint`, nên
// chạy thẳng ESLint: `npm run lint`. Lỗi làm CI đỏ, cảnh báo thì không.

import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      // Hai luật mới của React Compiler (eslint-plugin-react-hooks 7) hạ xuống cảnh báo: mã hiện có
      // cố ý đọc localStorage trong effect sau lần dựng đầu (tránh lệch giữa máy chủ và trình duyệt)
      // và giữ `ref` song song state cho Server Action. Viết lại các khuôn đó là đổi hành vi, không
      // phải sửa máy móc — làm riêng khi bật React Compiler.
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/refs": "warn",
    },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);
