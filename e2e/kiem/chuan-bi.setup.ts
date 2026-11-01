// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Bước chuẩn bị: mỗi vai đăng nhập thật qua trang của Keycloak, lưu trạng thái trình duyệt; rồi
// người gửi gửi một yêu cầu thật qua biểu mẫu, để cụm dựng sạch cũng có việc chờ điều phối viên.

import { expect, test as setup } from "@playwright/test";

import { MAT_KHAU, VAI, type Vai, luuHoSo, tepPhien } from "./chung";

for (const vai of Object.keys(VAI) as Vai[]) {
  setup(`đăng nhập thật: ${vai}`, async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Đăng nhập bằng tài khoản công ty" }).click();
    // Trang đăng nhập của Keycloak — chủ đề của dự án, tiếng Việt
    await page.locator("#username").fill(VAI[vai]);
    await page.locator("#password").fill(MAT_KHAU);
    await page.locator("#kc-login").click();
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Chào");
    await page.context().storageState({ path: tepPhien(vai) });
  });
}

setup("người gửi gửi một yêu cầu qua biểu mẫu", async ({ browser }) => {
  const nc = await browser.newContext({ storageState: tepPhien("nguoi-gui") });
  const page = await nc.newPage();
  const tieuDe = `Kiểm tra giao diện ${new Date().toISOString().slice(0, 19)}`;

  await page.goto("/yeu-cau/moi");
  await page.getByText("Sự cố thiết bị").first().click();
  await page.locator('input[name="title"]').fill(tieuDe);
  await page.locator('textarea[name="description"]').fill("Hồ sơ do kịch bản kiểm tra giao diện tạo.");
  // Trường riêng bắt buộc của loại Sự cố thiết bị (#250)
  // chọn theo mã ô: nhãn "Vị trí" cũng xuất hiện trong lời gợi ý của ô mô tả
  await page.locator("#truong-rieng-ma-tai-san").fill("KT-0001");
  await page.locator("#truong-rieng-vi-tri").fill("Phòng thử nghiệm");
  await page.getByRole("button", { name: "Tiếp tục" }).click();
  await page.getByRole("button", { name: "Gửi yêu cầu" }).click();

  await page.waitForURL(/\/yeu-cau\/\d+/);
  const ma = Number(new URL(page.url()).pathname.split("/").pop());
  expect(ma).toBeGreaterThan(0);
  await expect(page.getByRole("heading", { level: 1 })).toContainText(tieuDe);
  luuHoSo({ ma, tieuDe });
  await nc.close();
});
