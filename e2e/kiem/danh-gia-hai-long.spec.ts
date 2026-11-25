// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Đánh giá mức hài lòng khi người gửi xác nhận hồ sơ hoàn tất (#433), qua ĐĂNG NHẬP THẬT của bốn vai.
//
// Mỗi bài tự đưa một hồ sơ tới Hoàn tất bằng giao diện như người thật: người gửi gửi, điều phối viên phân loại
// và chuyển phòng, trưởng phòng xác duyệt, người xử lý hoàn thành. Rồi người gửi xác nhận đạt — kèm 4 sao và
// nhận xét, chọn sao bằng phím mũi tên — và điều phối viên, trưởng phòng thấy khối đánh giá; hay xác nhận mà
// không chấm, hồ sơ vẫn đóng như cũ. Quét axe hộp xác nhận có ô chấm và khối đánh giá.

import AxeBuilder from "@axe-core/playwright";
import { type Browser, type Page, expect, test } from "@playwright/test";

import { chup, guiYeuCauThu, tepPhien } from "./chung";

test.use({ storageState: tepPhien("nguoi-gui") });

async function bamXacNhan(trang: Page, nhan: string) {
  const thaoTac = trang.locator("#thao-tac");
  await thaoTac.getByRole("button", { name: nhan, exact: true }).click();
  // Bước có ô nhập mở bảng xác nhận; bước không có thì bấm là gửi
  const xacNhan = thaoTac.getByRole("button", { name: new RegExp(`^Xác nhận · ${nhan}`) });
  try {
    await xacNhan.waitFor({ state: "visible", timeout: 3_000 });
    await xacNhan.click();
  } catch {
    // đã gửi thẳng
  }
  await expect(thaoTac.getByRole("button", { name: nhan, exact: true })).toHaveCount(0);
}

/**
 * Người xử lý hoàn thành và ghi cách giải quyết (#556): ô ghi chú của cạnh mang tên ô trong dữ liệu, không bắt
 * buộc — tên ô "Cách giải quyết" của dữ liệu khởi tạo (infra/seed/01).
 */
async function hoanThanhKemCachGiaiQuyet(trang: Page, cach: string) {
  const thaoTac = trang.locator("#thao-tac");
  await thaoTac.getByRole("button", { name: "Hoàn thành xử lý", exact: true }).click();
  const o = thaoTac.getByRole("textbox", { name: /Cách giải quyết/ });
  await expect(o).toBeVisible();
  await expect(thaoTac).toContainText("Cách giải quyết — không bắt buộc");
  expect(await o.evaluate((e: HTMLTextAreaElement) => e.required), "ô không bắt buộc").toBe(false);
  await o.fill(cach);
  await chup(trang, test.info().project.name, "xu-ly-hoan-thanh-cach-giai-quyet");
  await thaoTac.getByRole("button", { name: /^Xác nhận · Hoàn thành xử lý/ }).click();
  await expect(thaoTac.getByRole("button", { name: "Hoàn thành xử lý", exact: true })).toHaveCount(0);
}

/** Một hồ sơ của người gửi mẫu tới Hoàn tất, ở phòng Công nghệ thông tin (loại "Sự cố thiết bị"). */
async function denHoanTat(browser: Browser, page: Page, nhan: string, cachGiaiQuyet?: string): Promise<number> {
  const ma = await guiYeuCauThu(page, `${nhan} ${test.info().project.name} ${new Date().toISOString().slice(0, 19)}`);
  for (const [vai, duong, cacBuoc] of [
    ["dieu-phoi", `/dieu-phoi/${ma}`, ["Phân loại yêu cầu", "Chuyển về phòng ban"]],
    ["truong-phong", `/phong-ban/${ma}`, ["Xác duyệt và giao xử lý"]],
    ["xu-ly", `/phong-ban/${ma}`, ["Hoàn thành xử lý"]],
  ] as const) {
    const ngu = await browser.newContext({ storageState: tepPhien(vai) });
    const trang = await ngu.newPage();
    await trang.goto(duong, { waitUntil: "networkidle" });
    for (const buoc of cacBuoc) {
      if (buoc === "Hoàn thành xử lý" && cachGiaiQuyet) await hoanThanhKemCachGiaiQuyet(trang, cachGiaiQuyet);
      else await bamXacNhan(trang, buoc);
    }
    await ngu.close();
  }
  return ma;
}

async function khongViPhamNang(page: Page, chon: string) {
  const kq = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).include(chon).analyze();
  const nang = kq.violations.filter((v) => v.impact === "critical" || v.impact === "serious");
  expect(nang.map((v) => `${v.id}: ${v.nodes[0]?.target.join(" ")}`), `axe ở ${chon}`).toEqual([]);
}

test("xác nhận đạt kèm 4 sao và nhận xét; điều phối viên và trưởng phòng thấy khối đánh giá", async ({ browser, page }) => {
  const ma = await denHoanTat(browser, page, "Hài lòng");
  const nhanXet = `Sửa nhanh, giải thích dễ hiểu ${test.info().project.name}`;

  await page.goto(`/yeu-cau/${ma}`, { waitUntil: "networkidle" });
  const thaoTac = page.locator("#thao-tac");
  await thaoTac.getByRole("button", { name: "Xác nhận đạt", exact: true }).click();
  const nhom = thaoTac.getByRole("group", { name: /Bạn hài lòng với cách xử lý đến đâu/ });
  await expect(nhom).toBeVisible();
  await expect(nhom.getByRole("radio", { name: "Không chấm" })).toBeChecked();
  // Bàn phím: mũi tên phải đi từ "Không chấm" tới 4 trên 5
  await nhom.getByRole("radio", { name: "Không chấm" }).focus();
  for (let i = 0; i < 4; i++) await page.keyboard.press("ArrowRight");
  await expect(nhom.getByRole("radio", { name: "4 trên 5" })).toBeChecked();
  // Một ô chữ duy nhất (#557): nhận xét kèm điểm cũng là ghi chú của bước; cảnh báo nói với chính người gửi
  await expect(thaoTac.getByRole("textbox")).toHaveCount(1);
  await expect(thaoTac.getByRole("note")).toContainText("Bạn còn mở lại được");
  await thaoTac.getByRole("textbox", { name: /Nhận xét/ }).fill(nhanXet);
  await expect(thaoTac.locator(".cham-diem-dem")).toContainText(`${nhanXet.length}/`);
  expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)).toBe(false);
  await khongViPhamNang(page, "#thao-tac");
  await chup(page, test.info().project.name, "nguoi-gui-xac-nhan-cham-diem");

  // Nhãn cạnh đã mở đầu bằng "Xác nhận": nút gửi không lặp chữ, cũng không trùng tên nút mở bước (#540)
  await expect(thaoTac.getByRole("button", { name: /Xác nhận · Xác nhận/ })).toHaveCount(0);
  await thaoTac.getByRole("button", { name: "Gửi xác nhận đạt", exact: true }).click();
  const khoi = page.locator(".the-danh-gia");
  await expect(khoi).toContainText("4/5");
  await expect(khoi).toContainText(nhanXet);
  await expect(thaoTac.getByRole("button", { name: "Xác nhận đạt", exact: true })).toHaveCount(0);
  // Hồ sơ đã đóng (#557): khung nói đúng trạng thái và đường mở lại, ô người giữ không nói như hồ sơ đang mở
  await expect(page.getByText("Hồ sơ đã kết thúc nhưng vẫn mở lại được trong thời hạn", { exact: false })).toBeVisible();
  await expect(page.getByText("Phòng ban phụ trách", { exact: true })).toBeVisible();
  await expect(page.getByText("Đã có người được phân công xử lý")).toHaveCount(0);
  await expect(page.getByText("Đồng hồ xử lý chưa từng chạy")).toHaveCount(0);

  for (const [vai, duong] of [
    ["dieu-phoi", `/dieu-phoi/${ma}`],
    ["truong-phong", `/phong-ban/${ma}`],
  ] as const) {
    const ngu = await browser.newContext({ storageState: tepPhien(vai) });
    const trang = await ngu.newPage();
    await trang.goto(duong, { waitUntil: "networkidle" });
    const theNv = trang.locator(".the-danh-gia");
    await expect(theNv.getByRole("heading", { name: "Đánh giá của người gửi" })).toBeVisible();
    await expect(theNv).toContainText("4/5");
    await expect(theNv).toContainText(nhanXet);
    expect(await trang.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)).toBe(false);
    await khongViPhamNang(trang, ".the-danh-gia");
    await chup(trang, test.info().project.name, `${vai}-danh-gia-nguoi-gui`);
    await ngu.close();
  }
});

test("xác nhận đạt không chấm: hồ sơ vẫn đóng, không có khối đánh giá", async ({ browser, page }) => {
  const ma = await denHoanTat(browser, page, "Không chấm");
  await page.goto(`/yeu-cau/${ma}`, { waitUntil: "networkidle" });
  const thaoTac = page.locator("#thao-tac");
  await thaoTac.getByRole("button", { name: "Xác nhận đạt", exact: true }).click();
  await thaoTac.getByRole("button", { name: "Gửi xác nhận đạt", exact: true }).click();
  await expect(thaoTac.getByRole("button", { name: "Xác nhận đạt", exact: true })).toHaveCount(0);
  await expect(page.locator(".the-danh-gia")).toHaveCount(0);

  const ngu = await browser.newContext({ storageState: tepPhien("dieu-phoi") });
  const trang = await ngu.newPage();
  await trang.goto(`/dieu-phoi/${ma}`, { waitUntil: "networkidle" });
  await expect(trang.getByText("Đã đóng").first()).toBeVisible();
  await expect(trang.locator(".the-danh-gia")).toHaveCount(0);
  await ngu.close();
});

test("Hoàn thành xử lý ghi được cách giải quyết, không bắt buộc; người gửi đọc được trong dòng thời gian (#556)", async ({
  browser,
  page,
}) => {
  const cach = `Đã vệ sinh con lăn kéo giấy và in thử 20 trang ${test.info().project.name}`;
  const ma = await denHoanTat(browser, page, "Cách giải quyết", cach);

  // Người gửi thấy dòng của bước Hoàn thành xử lý mang đúng tên ô và chữ người xử lý ghi
  await page.goto(`/yeu-cau/${ma}`, { waitUntil: "networkidle" });
  // Khớp đúng nhãn (tiêu đề hồ sơ thử cũng mở đầu bằng "Cách giải quyết") và chỉ chỗ đang hiện: dòng thời gian thu
  // gọn giữ bản đầy đủ đã ẩn của mốc mới nhất
  const ghiChu = page.locator(".tua-muc", { hasText: /^\s*Cách giải quyết\s*$/ }).filter({ visible: true });
  await expect(ghiChu).toHaveCount(1);
  await expect(ghiChu.locator("..")).toContainText(cach);
  // Ô không bắt buộc: hồ sơ ở test trước đi qua Hoàn thành xử lý mà không ghi gì vẫn tới Hoàn tất (denHoanTat)
  const thaoTac = page.locator("#thao-tac");
  await thaoTac.getByRole("button", { name: "Xác nhận đạt", exact: true }).click();
  await thaoTac.getByRole("button", { name: "Gửi xác nhận đạt", exact: true }).click();
  await expect(thaoTac.getByRole("button", { name: "Xác nhận đạt", exact: true })).toHaveCount(0);
  // Sau khi đóng, dòng thời gian thu gọn về bước Xác nhận đạt: ghi chú của bước Hoàn thành nằm ở bản đầy đủ
  await expect(page.locator(".tua-muc", { hasText: /^\s*Cách giải quyết\s*$/ }).first().locator("..")).toContainText(cach);
});
