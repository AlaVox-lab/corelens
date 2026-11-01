// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Chỉ chạy ở cấu hình giảm chuyển động (playwright.config.ts): bật "giảm chuyển động" của hệ điều
// hành thì không phần tử nào trên trang chủ còn hiệu ứng hay chuyển tiếp chạy (#237, #238).

import { expect, test } from "@playwright/test";

import { tepPhien } from "./chung";

test("giảm chuyển động: không hiệu ứng nào chạy", async ({ browser }) => {
  const nc = await browser.newContext({ storageState: tepPhien("dieu-phoi"), reducedMotion: "reduce" });
  const page = await nc.newPage();
  await page.goto("/", { waitUntil: "networkidle" });
  const dangChay = await page.evaluate(() =>
    [...document.querySelectorAll("*")].filter((el) => {
      const s = getComputedStyle(el);
      const thoiLuong = (v: string) => v.split(",").some((x) => parseFloat(x) > 0.001);
      return (s.animationName !== "none" && thoiLuong(s.animationDuration)) || thoiLuong(s.transitionDuration);
    }).length,
  );
  expect(dangChay, "số phần tử còn chuyển động").toBe(0);
  await nc.close();
});
