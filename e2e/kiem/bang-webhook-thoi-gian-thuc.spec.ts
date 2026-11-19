// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Ba màn của cổng chưa có bài nào (#493): bảng Kanban của phòng ban (#403), khối Webhook trên màn Hệ thống
// (#401), và cập nhật thời gian thực (#387). Dịch vụ ứng dụng đã có kiểm thử cho các điểm cuối phía sau; ở
// đây kiểm phần nằm ở cổng — cách gom cột của bảng, hành động máy chủ đăng ký và hủy webhook, tuyến chuyển
// tiếp luồng sự kiện `/api/su-kien`.
//
// Như các kịch bản khác: đăng nhập thật, không bài nào dựa vào số tuyệt đối — cụm thử có ít hay nhiều hồ
// sơ tùy lúc chạy. Bài nào cần hồ sơ ở phòng thì tự dựng một hồ sơ qua giao diện.

import { type Browser, type Page, expect, test } from "@playwright/test";

import { guiYeuCauThu, tepPhien } from "./chung";

/** Người gửi gửi một hồ sơ, điều phối viên phân loại rồi giữ gợi ý phòng ban mà chuyển phòng. */
async function dungHoSoOPhong(browser: Browser, nhan: string): Promise<{ ma: number; tieuDe: string }> {
  const tieuDe = `${nhan} ${test.info().project.name} ${new Date().toISOString().slice(0, 19)}`;
  const nguoiGui = await browser.newContext({ storageState: tepPhien("nguoi-gui") });
  const ma = await guiYeuCauThu(await nguoiGui.newPage(), tieuDe);
  await nguoiGui.close();

  const dieuPhoi = await browser.newContext({ storageState: tepPhien("dieu-phoi") });
  const trang = await dieuPhoi.newPage();
  await trang.goto(`/dieu-phoi/${ma}`, { waitUntil: "networkidle" });
  const thaoTac = trang.locator("#thao-tac");
  await thaoTac.getByRole("button", { name: "Phân loại yêu cầu", exact: true }).click();
  await thaoTac.getByRole("button", { name: /^Xác nhận · Phân loại yêu cầu/ }).click();
  await thaoTac.getByRole("button", { name: "Chuyển về phòng ban", exact: true }).click();
  await thaoTac.getByRole("button", { name: /^Xác nhận · Chuyển về phòng ban/ }).click();
  await expect(trang.getByText("Chờ phòng ban xác duyệt").first()).toBeVisible();
  await dieuPhoi.close();
  return { ma, tieuDe };
}

/** Thẻ của bảng Kanban — mỗi thẻ là một liên kết tới trang hồ sơ của phòng. */
const theKanban = (page: Page) => page.locator(".kb-bang .kb-the");

test.describe("bảng Kanban của phòng ban (#403)", () => {
  // Trưởng phòng Công nghệ thông tin: loại "Sự cố thiết bị" mặc định chuyển về phòng này
  test.use({ storageState: tepPhien("truong-phong") });

  test("cột theo trạng thái, số trên đầu cột khớp số thẻ, tổng khớp hàng đợi; bấm thẻ mở đúng hồ sơ", async ({
    browser,
    page,
  }) => {
    const h = await dungHoSoOPhong(browser, "Kanban");

    await page.goto("/phong-ban/bang", { waitUntil: "networkidle" });
    const cacCot = page.locator(".kb-cot");
    expect(await cacCot.count()).toBeGreaterThan(0);

    // Mỗi cột: con số ở đầu cột bằng số thẻ trong cột
    let tongThe = 0;
    for (const cot of await cacCot.all()) {
      const so = Number(await cot.locator(".kb-so").innerText());
      await expect(cot.locator(".kb-the")).toHaveCount(so);
      tongThe += so;
    }

    // Tổng số thẻ khớp tổng của hàng đợi dạng danh sách — bảng đọc đúng hàng đợi đó (trần 200 dòng)
    await page.goto("/phong-ban", { waitUntil: "networkidle" });
    const tongHangDoi = Number(await page.locator(".chan-trang b").last().innerText());
    if (tongHangDoi <= 200) expect(tongThe).toBe(tongHangDoi);
    else expect(tongThe).toBe(200);

    // Hồ sơ vừa chuyển về nằm ở cột trạng thái của nó; bấm thẻ thì mở trang hồ sơ đó
    await page.goto("/phong-ban/bang", { waitUntil: "networkidle" });
    const cotCho = page.locator(".kb-cot", { has: page.locator(".kb-dau-cot", { hasText: "Chờ phòng ban xác duyệt" }) });
    const the = cotCho.locator(".kb-the", { hasText: h.tieuDe });
    await expect(the).toHaveCount(1);
    await the.click();
    await page.waitForURL(new RegExp(`/phong-ban/${h.ma}$`));
    await expect(page.getByRole("heading", { level: 1 })).toContainText(h.tieuDe);
  });

  test("nút Giao cho tôi chỉ giữ thẻ đã giao cho chính mình", async ({ page }) => {
    await page.goto("/phong-ban/bang", { waitUntil: "networkidle" });
    const tatCa = await theKanban(page).count();

    await page.getByRole("link", { name: "Giao cho tôi" }).click();
    await page.waitForURL(/\/phong-ban\/bang\?mine=1$/);
    await expect(page.getByRole("link", { name: "Giao cho tôi" })).toHaveAttribute("aria-pressed", "true");

    const cuaToi = await theKanban(page).count();
    expect(cuaToi).toBeLessThanOrEqual(tatCa);
    if (cuaToi === 0) {
      await expect(page.getByText("Chưa có hồ sơ nào giao cho bạn")).toBeVisible();
    } else {
      // Thẻ đã giao cho người xem mang ảnh đại diện có nhãn "Bạn"
      await expect(theKanban(page).locator('.av[title="Bạn"]')).toHaveCount(cuaToi);
    }
  });
});

test.describe("khối Webhook trên màn Hệ thống (#401)", () => {
  test.describe("quản trị viên", () => {
    test.use({ storageState: tepPhien("quan-tri") });

    test("đăng ký thì thấy bí mật ký đúng một lần, danh sách có đăng ký mới, hủy được", async ({ page }) => {
      const diaChi = `https://nhan-su-kien.example/e2e/${test.info().project.name}/${Date.now()}`;
      await page.goto("/he-thong", { waitUntil: "networkidle" });
      const khoi = page.locator("section", { has: page.locator("#quan-ly-webhook") });

      await khoi.locator('input[name="url"]').fill(diaChi);
      await khoi.locator('input[name="mo-ta"]').fill("Kịch bản giao diện");
      await khoi.getByRole("button", { name: "Đăng ký webhook" }).click();

      // Bí mật hiện ngay sau khi tạo, kèm địa chỉ vừa đăng ký
      const biMat = khoi.locator(".wh-bi-mat");
      await expect(biMat).toContainText(diaChi);
      const chuoiBiMat = (await biMat.locator("code").innerText()).trim();
      expect(chuoiBiMat.length).toBeGreaterThan(15);
      const dong = khoi.locator(".wh-dang-ky", { hasText: diaChi });
      await expect(dong).toHaveCount(1);

      // Tải lại: đăng ký vẫn còn, bí mật thì không hiện lại ở đâu trên trang
      await page.reload({ waitUntil: "networkidle" });
      await expect(khoi.locator(".wh-dang-ky", { hasText: diaChi })).toHaveCount(1);
      await expect(khoi.locator(".wh-bi-mat")).toHaveCount(0);
      expect(await page.locator("main").innerText()).not.toContain(chuoiBiMat);

      // Hủy: hộp xác nhận của trình duyệt, đồng ý thì dòng biến mất
      page.once("dialog", (hop) => hop.accept());
      await khoi.locator(".wh-dang-ky", { hasText: diaChi }).getByRole("button", { name: "Hủy" }).click();
      await expect(khoi.locator(".wh-dang-ky", { hasText: diaChi })).toHaveCount(0);
      await page.reload({ waitUntil: "networkidle" });
      await expect(khoi.locator(".wh-dang-ky", { hasText: diaChi })).toHaveCount(0);
    });
  });

  test.describe("vai không phải quản trị viên", () => {
    test.use({ storageState: tepPhien("dieu-phoi") });

    test("không thấy khối Webhook, không đăng ký được", async ({ page }) => {
      await page.goto("/he-thong", { waitUntil: "networkidle" });
      await expect(page.locator("#quan-ly-webhook")).toHaveCount(0);
      await expect(page.getByRole("button", { name: "Đăng ký webhook" })).toHaveCount(0);
    });
  });
});

test.describe("cập nhật thời gian thực (#387)", () => {
  test.use({ storageState: tepPhien("nguoi-gui") });

  test("điều phối viên chuyển trạng thái, trang hồ sơ của người gửi đổi theo không cần tải lại", async ({
    browser,
    page,
  }) => {
    const tieuDe = `Thời gian thực ${test.info().project.name} ${new Date().toISOString().slice(0, 19)}`;
    const ma = await guiYeuCauThu(page, tieuDe);

    // Trang hồ sơ không có lượt hỏi định kỳ (chỉ hộp thư có): đổi được trong vài giây là nhờ luồng sự kiện
    const luong = page.waitForResponse((r) => new URL(r.url()).pathname === "/api/su-kien");
    await page.goto(`/yeu-cau/${ma}`, { waitUntil: "domcontentloaded" });
    // Tuyến chuyển tiếp trả 204 khi không mở được luồng — khi đó trình duyệt thôi nghe và bài phải đỏ
    expect((await luong).status()).toBe(200);
    await expect(page.getByText("Đã phân loại")).toHaveCount(0);

    const dieuPhoi = await browser.newContext({ storageState: tepPhien("dieu-phoi") });
    const trang = await dieuPhoi.newPage();
    await trang.goto(`/dieu-phoi/${ma}`, { waitUntil: "networkidle" });
    const thaoTac = trang.locator("#thao-tac");
    await thaoTac.getByRole("button", { name: "Phân loại yêu cầu", exact: true }).click();
    await thaoTac.getByRole("button", { name: /^Xác nhận · Phân loại yêu cầu/ }).click();
    await expect(trang.getByText("Đã phân loại").first()).toBeVisible();
    await dieuPhoi.close();

    // Màn của người gửi đổi theo mà không ai tải lại trang
    await expect(page.getByText("Đã phân loại").first()).toBeVisible({ timeout: 8_000 });
  });
});
