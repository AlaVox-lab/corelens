// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Chỉ chạy ở cấu hình giảm chuyển động (playwright.config.ts): bật "giảm chuyển động" của hệ điều
// hành thì không phần tử nào còn hiệu ứng hay chuyển tiếp chạy (#237, #238) — trên trang chủ, hàng
// đợi, ngăn xem nhanh và khung xác nhận trong ngăn.

import { type Page, expect, test } from "@playwright/test";

import { tepPhien } from "./chung";

/** Số phần tử mà CSS còn khai hiệu ứng hay chuyển tiếp có thời lượng. */
function conChuyenDong(page: Page) {
  return page.evaluate(() =>
    [...document.querySelectorAll("*")].filter((el) => {
      const s = getComputedStyle(el);
      const thoiLuong = (v: string) => v.split(",").some((x) => parseFloat(x) > 0.001);
      return (s.animationName !== "none" && thoiLuong(s.animationDuration)) || thoiLuong(s.transitionDuration);
    }).length,
  );
}

test("giảm chuyển động: không hiệu ứng nào chạy", async ({ browser }) => {
  const nc = await browser.newContext({ storageState: tepPhien("dieu-phoi"), reducedMotion: "reduce" });
  const page = await nc.newPage();
  await page.goto("/", { waitUntil: "networkidle" });
  expect(await conChuyenDong(page), "trang chủ").toBe(0);

  await page.goto("/dieu-phoi", { waitUntil: "networkidle" });
  expect(await conChuyenDong(page), "hàng đợi").toBe(0);
  await page.locator("a.lk-dong").first().click();
  const ngan = page.locator("aside.ngan");
  await expect(ngan).toBeVisible();
  const chinh = ngan.locator(".ngan-chan .nut[data-loai='chinh']");
  if (await chinh.isVisible()) await chinh.click();
  expect(await conChuyenDong(page), "ngăn xem nhanh và khung xác nhận").toBe(0);
  // Đóng ngăn không chờ hiệu ứng ra: rời `?xem=` ngay
  await page.keyboard.press("Escape");
  await expect(ngan).toHaveCount(0, { timeout: 2000 });

  // Màn quy trình thực tế (#315): sơ đồ, khối xếp hạng và ngăn danh sách hồ sơ cũng không chạy hiệu ứng
  await page.goto("/bao-cao/quy-trinh", { waitUntil: "networkidle" });
  await expect(page.locator(".qt-ket-qua:not([data-dang-tai]), .rong").first()).toBeVisible({ timeout: 30_000 });
  expect(await conChuyenDong(page), "quy trình thực tế").toBe(0);
  const nutTrangThai = page.locator(".sdq-nut[aria-pressed]").first();
  if (await nutTrangThai.isVisible()) {
    await nutTrangThai.click();
    await expect(page.locator("aside.ngan")).toBeVisible();
    expect(await conChuyenDong(page), "ngăn danh sách hồ sơ quy trình").toBe(0);
    await page.keyboard.press("Escape");
    await expect(page.locator("aside.ngan")).toHaveCount(0, { timeout: 2000 });
  }
  await nc.close();
});
