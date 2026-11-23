// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Thao tác hàng loạt trên hàng đợi điều phối (#440), qua ĐĂNG NHẬP THẬT như mọi kịch bản khác.
//
// Điều phối viên chọn vài hồ sơ, phân loại cả lô, rồi chuyển cả lô về một phòng; một lô có hồ sơ bị
// chặn — hồ sơ do chính điều phối viên gửi (ràng buộc "không tự điều phối hồ sơ của mình", #154) — thì
// thấy danh sách bị chặn kèm lý do, hồ sơ đó vẫn được chọn để làm lại.
//
// Mỗi lượt tự gửi hồ sơ riêng, gắn một dấu ASCII trong tiêu đề rồi lọc hàng đợi bằng ô tìm theo dấu đó:
// bài không phụ thuộc hồ sơ cũ trong cụm hay thứ tự của hàng đợi. Hồ sơ gửi bằng tài khoản người xử lý
// (mọi tài khoản mẫu đều mang vai gửi), KHÔNG bằng tài khoản người gửi mẫu: danh sách "Hồ sơ của tôi"
// của người gửi mẫu xếp mới nhất trước, và giao-dien.spec.ts tìm hồ sơ của bước chuẩn bị ở trang đầu.

import AxeBuilder from "@axe-core/playwright";
import { type Browser, type Page, expect, test } from "@playwright/test";

import { chup, guiYeuCauThu, tepPhien } from "./chung";

test.use({ storageState: tepPhien("dieu-phoi") });

/** `so` hồ sơ của một người gửi khác, và (nếu cần) một hồ sơ do chính điều phối viên gửi. */
async function dungLo(browser: Browser, page: Page, so: number, coCuaMinh: boolean) {
  const dau = `HL440-${test.info().project.name}-${Date.now()}`;
  const ng = await browser.newContext({ storageState: tepPhien("xu-ly") });
  const trangNg = await ng.newPage();
  const cuaNguoiGui: number[] = [];
  for (let i = 1; i <= so; i++) cuaNguoiGui.push(await guiYeuCauThu(trangNg, `${dau} so ${i}`));
  await ng.close();
  const cuaMinh = coCuaMinh ? await guiYeuCauThu(page, `${dau} cua minh`) : 0;
  return { dau, cuaNguoiGui, cuaMinh };
}

const oChon = (page: Page, ma: number) => page.locator(`input[data-chon-ho-so="${ma}"]`);

test("chọn vài hồ sơ, phân loại rồi chuyển phòng cả lô; hồ sơ bị chặn báo riêng", async ({ browser, page }) => {
  const { dau, cuaNguoiGui, cuaMinh } = await dungLo(browser, page, 3, true);
  const tatCa = [...cuaNguoiGui, cuaMinh];
  await page.goto(`/dieu-phoi?q=${encodeURIComponent(dau)}`, { waitUntil: "networkidle" });
  await expect(page.locator("a.lk-dong")).toHaveCount(4);

  // 1. Ô chọn có nhãn; bấm ô chỉ chọn, không mở ngăn xem nhanh
  const chonHet = page.getByRole("checkbox", { name: "Chọn tất cả hồ sơ trên trang này" });
  await expect(page.getByRole("region", { name: "Thao tác với hồ sơ đã chọn" })).toHaveCount(0);
  await oChon(page, cuaNguoiGui[0]).click();
  await expect(oChon(page, cuaNguoiGui[0])).toBeChecked();
  await expect(page).not.toHaveURL(/xem=/);
  await expect(page.locator("aside.ngan")).toHaveCount(0);
  // Chọn một phần: ô đầu bảng ở trạng thái lưng chừng
  expect(await chonHet.evaluate((o) => (o as HTMLInputElement).indeterminate)).toBe(true);
  await chonHet.check();
  for (const ma of tatCa) await expect(oChon(page, ma)).toBeChecked();

  const thanh = page.getByRole("region", { name: "Thao tác với hồ sơ đã chọn" });
  await expect(thanh).toContainText("Đã chọn 4 hồ sơ");
  expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)).toBe(false);
  await chup(page, test.info().project.name, "dieu-phoi-hang-loat-thanh");

  // 2. Hộp thoại: Esc đóng và trả tiêu điểm về nút đã mở
  const nutPhanLoai = thanh.getByRole("button", { name: "Phân loại yêu cầu" });
  await nutPhanLoai.click();
  const hop = page.getByRole("dialog", { name: "Phân loại yêu cầu cho 4 hồ sơ" });
  await expect(hop).toBeVisible();
  await expect(hop.locator("select").first()).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(hop).toHaveCount(0);
  await expect(nutPhanLoai).toBeFocused();

  // 3. Phân loại cả lô: mức ưu tiên điền sẵn mức mặc định, loại giữ nguyên ở từng hồ sơ
  await nutPhanLoai.click();
  await expect(hop.getByRole("list")).toContainText(/YC-\d{4}-\d+/);
  await chup(page, test.info().project.name, "dieu-phoi-hang-loat-hop-thoai");
  await hop.getByRole("button", { name: "Phân loại yêu cầu cho 4 hồ sơ" }).click();
  await expect(hop).toHaveCount(0);

  const ketQua = page.locator(".kq-hang-loat");
  await expect(ketQua.getByRole("heading")).toHaveText("Phân loại yêu cầu: đã chuyển 3/4 hồ sơ");
  await expect(ketQua.getByRole("heading")).toBeFocused();
  // Hồ sơ của chính mình bị chặn, kèm lý do của ràng buộc; mã mở được trang hồ sơ
  const biChan = ketQua.getByRole("listitem");
  await expect(biChan).toHaveCount(1);
  await expect(biChan).toContainText("điều phối viên khác");
  await expect(biChan.getByRole("link")).toHaveAttribute("href", `/dieu-phoi/${cuaMinh}`);
  // Đã chuyển thì bỏ chọn; bị chặn giữ chọn để làm lại
  await expect(oChon(page, cuaMinh)).toBeChecked();
  for (const ma of cuaNguoiGui) await expect(oChon(page, ma)).not.toBeChecked();
  await chup(page, test.info().project.name, "dieu-phoi-hang-loat-ket-qua");
  // Khung kết quả chỉ hiện sau một lần chạy, nên quét riêng ở đây — cùng chuẩn với kha-nang-tiep-can.spec.ts
  const axe = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .include(".kq-hang-loat")
    .analyze();
  const nang = axe.violations.filter((v) => v.impact === "critical" || v.impact === "serious");
  expect(nang.map((v) => `${v.id}: ${v.nodes[0]?.target.join(" ")}`)).toEqual([]);

  // 4. Chuyển về phòng: chọn cả trang; hồ sơ chưa phân loại được báo trước là bỏ qua
  await chonHet.check();
  await thanh.getByRole("button", { name: "Chuyển về phòng ban" }).click();
  const hopPhong = page.getByRole("dialog", { name: "Chuyển về phòng ban cho 3 hồ sơ" });
  await expect(hopPhong).toBeVisible();
  await expect(hopPhong.getByRole("note")).toContainText("1 hồ sơ sẽ bỏ qua");
  // Phòng là ô bắt buộc: chưa chọn thì không gửi
  const oPhong = hopPhong.locator('select[name="department_code"]');
  await hopPhong.getByRole("button", { name: "Chuyển về phòng ban cho 3 hồ sơ" }).click();
  await expect(hopPhong).toBeVisible();
  await oPhong.selectOption({ index: 1 });
  await hopPhong.getByRole("button", { name: "Chuyển về phòng ban cho 3 hồ sơ" }).click();
  await expect(hopPhong).toHaveCount(0);
  await expect(ketQua.getByRole("heading")).toHaveText("Chuyển về phòng ban: đã chuyển 3/3 hồ sơ");
  await expect(ketQua.getByRole("listitem")).toHaveCount(0);

  // Hàng đợi đã làm mới: ba hồ sơ mang trạng thái mới, hồ sơ của mình đứng nguyên
  for (const ma of cuaNguoiGui) {
    await expect(page.locator("tr.dong", { has: oChon(page, ma) })).toContainText("Chờ phòng ban xác duyệt");
  }
  await expect(page.locator("tr.dong", { has: oChon(page, cuaMinh) })).toContainText("Đã gửi");
});

test("đổi bộ lọc thì bỏ chọn; màn phòng ban không có ô chọn", async ({ browser, page }) => {
  const { dau, cuaNguoiGui } = await dungLo(browser, page, 2, false);
  await page.goto(`/dieu-phoi?q=${encodeURIComponent(dau)}`, { waitUntil: "networkidle" });
  await oChon(page, cuaNguoiGui[0]).check();
  await expect(page.getByRole("region", { name: "Thao tác với hồ sơ đã chọn" })).toBeVisible();
  // Mở ngăn xem nhanh không bỏ chọn
  await page.locator(`a[data-xem-dong="${cuaNguoiGui[1]}"]`).click();
  await expect(page).toHaveURL(/xem=/);
  await expect(oChon(page, cuaNguoiGui[0])).toBeChecked();
  await page.keyboard.press("Escape");
  // Đổi ô tìm là đổi bộ lọc
  await page.goto(`/dieu-phoi?q=${encodeURIComponent(`${dau} so 1`)}`, { waitUntil: "networkidle" });
  await expect(oChon(page, cuaNguoiGui[0])).not.toBeChecked();
  await expect(page.getByRole("region", { name: "Thao tác với hồ sơ đã chọn" })).toHaveCount(0);

  const tp = await browser.newContext({ storageState: tepPhien("truong-phong") });
  const trangTp = await tp.newPage();
  await trangTp.goto("/phong-ban", { waitUntil: "networkidle" });
  await expect(trangTp.locator("table.bang, .rong").first()).toBeVisible();
  await expect(trangTp.locator("[data-chon-ho-so], [data-chon-nhieu]")).toHaveCount(0);
  await tp.close();
});
