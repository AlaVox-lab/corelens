// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Nhật ký truy cập dữ liệu cá nhân (#431), qua ĐĂNG NHẬP THẬT của ba vai.
//
// Người gửi gửi một yêu cầu; điều phối viên mở hồ sơ đó trên buồng lái; quản trị viên mở màn Hệ thống, lọc theo
// mã hồ sơ bằng biểu mẫu lọc và thấy đúng dòng "Xem chi tiết hồ sơ" của điều phối viên. Quét axe khối mới; ở màn
// hẹp trang không cuộn ngang.

import AxeBuilder from "@axe-core/playwright";
import { type Page, expect, test } from "@playwright/test";

import { chup, guiYeuCauThu, tepPhien } from "./chung";

test.use({ storageState: tepPhien("quan-tri") });

async function khongViPhamNang(page: Page, chon: string) {
  const kq = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).include(chon).analyze();
  const nang = kq.violations.filter((v) => v.impact === "critical" || v.impact === "serious");
  expect(nang.map((v) => `${v.id}: ${v.nodes[0]?.target.join(" ")}`), `axe ở ${chon}`).toEqual([]);
}

test("điều phối viên mở hồ sơ thì quản trị viên thấy dòng đó, lọc theo mã hồ sơ ra đúng", async ({ browser, page }) => {
  const nguoiGui = await browser.newContext({ storageState: tepPhien("nguoi-gui") });
  const ma = await guiYeuCauThu(
    await nguoiGui.newPage(),
    `Nhật ký truy cập ${test.info().project.name} ${new Date().toISOString().slice(0, 19)}`,
  );
  await nguoiGui.close();

  const dieuPhoi = await browser.newContext({ storageState: tepPhien("dieu-phoi") });
  const trangDp = await dieuPhoi.newPage();
  await trangDp.goto(`/dieu-phoi/${ma}`, { waitUntil: "networkidle" });
  await expect(trangDp.getByRole("heading", { level: 1 })).toBeVisible();
  await dieuPhoi.close();

  await page.goto("/he-thong", { waitUntil: "networkidle" });
  const khoi = page.locator("#nhat-ky-truy-cap");
  await expect(khoi.getByRole("heading", { name: "Nhật ký truy cập dữ liệu cá nhân" })).toBeVisible();

  // Lọc bằng biểu mẫu, như người thật: gõ mã hồ sơ, bấm Lọc
  await khoi.getByLabel("Mã hồ sơ").fill(String(ma));
  await khoi.getByRole("button", { name: "Lọc" }).click();
  await page.waitForURL(new RegExp(`[?&]ho-so=${ma}(&|$|#)`));
  const bang = khoi.getByRole("table");
  const maHienThi = new RegExp(`YC-\\d{4}-0*${ma}\\b`);
  await expect(bang.getByRole("row").filter({ hasText: maHienThi }).first()).toBeVisible();

  const dong = bang.getByRole("row").filter({ hasText: "Xem chi tiết hồ sơ" }).filter({ hasText: "Bình Trần" });
  await expect(dong).toHaveCount(1);
  await expect(dong).toContainText("Cổng");
  // Chỉ dòng của hồ sơ này: mọi dòng dữ liệu đều mang mã của nó
  const soDong = await bang.locator("tbody tr").count();
  await expect(bang.locator("tbody tr").filter({ hasText: maHienThi })).toHaveCount(soDong);
  await expect(khoi.getByRole("link", { name: `Bỏ lọc Hồ sơ: ${ma}` })).toBeVisible();

  expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)).toBe(false);
  await khongViPhamNang(page, "#nhat-ky-truy-cap");
  await chup(page, test.info().project.name, "quan-tri-nhat-ky-truy-cap");

  // Lọc ra rỗng: một dòng chữ kèm lối "Xóa tất cả"
  await page.goto(`/he-thong?ho-so=${ma}&loai=event-log-export`, { waitUntil: "networkidle" });
  await expect(khoi).toContainText("Không có lượt truy cập nào khớp bộ lọc.");
  await khongViPhamNang(page, "#nhat-ky-truy-cap");
});
