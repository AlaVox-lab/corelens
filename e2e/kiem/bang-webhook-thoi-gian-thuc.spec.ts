// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Ba màn của cổng chưa có bài nào (#493): bảng Kanban của phòng ban (#403), khối Webhook trên màn Hệ thống
// (#401), và cập nhật thời gian thực (#387). Dịch vụ ứng dụng đã có kiểm thử cho các điểm cuối phía sau; ở
// đây kiểm phần nằm ở cổng — cách gom cột của bảng, hành động máy chủ đăng ký và hủy webhook, tuyến chuyển
// tiếp luồng sự kiện `/api/su-kien`. Bảng Kanban của điều phối (#560) dùng chung cột và thẻ với bảng phòng
// ban, nên bài của nó đứng ngay sau: cột khớp dải số của hàng đợi, bộ lọc đi theo khi chuyển dạng xem.
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
    await expect(page.getByRole("link", { name: "Giao cho tôi" })).toHaveAttribute("aria-current", "true");

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

/**
 * Hai hồ sơ trong hàng đợi điều phối, tiêu đề chung một chuỗi để tìm: một vừa gửi, một điều phối viên đã phân
 * loại — hai trạng thái khác nhau, nên bảng chắc có hai cột để so thứ tự.
 */
async function dungHaiHoSoDieuPhoi(browser: Browser, chung: string) {
  const nguoiGui = await browser.newContext({ storageState: tepPhien("nguoi-gui") });
  const trangGui = await nguoiGui.newPage();
  const vuaGui = { tieuDe: `${chung} vừa gửi`, ma: 0 };
  vuaGui.ma = await guiYeuCauThu(trangGui, vuaGui.tieuDe);
  const daPhanLoai = { tieuDe: `${chung} đã phân loại`, ma: 0 };
  daPhanLoai.ma = await guiYeuCauThu(trangGui, daPhanLoai.tieuDe);
  await nguoiGui.close();

  const dieuPhoi = await browser.newContext({ storageState: tepPhien("dieu-phoi") });
  const trang = await dieuPhoi.newPage();
  await trang.goto(`/dieu-phoi/${daPhanLoai.ma}`, { waitUntil: "networkidle" });
  const thaoTac = trang.locator("#thao-tac");
  await thaoTac.getByRole("button", { name: "Phân loại yêu cầu", exact: true }).click();
  await thaoTac.getByRole("button", { name: /^Xác nhận · Phân loại yêu cầu/ }).click();
  // Bước kế của hồ sơ đã phân loại: còn ở hàng đợi điều phối, chờ chuyển phòng
  await expect(thaoTac.getByRole("button", { name: "Chuyển về phòng ban", exact: true })).toBeVisible();
  await dieuPhoi.close();
  return { vuaGui, daPhanLoai };
}

type CotDem = { ten: string; so: number };

/** Ô trạng thái trên dải số của hàng đợi điều phối, bỏ ô "Cần làm" đầu dải; chỉ ô có hồ sơ, theo thứ tự trên dải. */
async function daiSoTrangThai(page: Page): Promise<{ tong: number; cacO: CotDem[] }> {
  const cacO: CotDem[] = [];
  for (const o of await page.getByRole("navigation", { name: "Lọc theo trạng thái" }).locator(".o-loc").all()) {
    cacO.push({
      ten: ((await o.locator(".o-loc-nhan").textContent()) ?? "").trim(),
      so: Number(await o.locator("strong").textContent()),
    });
  }
  const [canLam, ...theoTrangThai] = cacO;
  return { tong: canLam.so, cacO: theoTrangThai.filter((o) => o.so > 0) };
}

/** Cột của bảng Kanban theo thứ tự trên trang: nhãn trạng thái ở đầu cột và số thẻ đếm được (bằng số đầu cột). */
async function cotKanban(page: Page): Promise<CotDem[]> {
  // Bấm nút chuyển là điều hướng phía trình duyệt: địa chỉ đổi khi khung chờ (`loading.tsx`) còn hiện
  await expect(page.locator(".kb-bang")).toBeVisible();
  const ra: CotDem[] = [];
  for (const cot of await page.locator(".kb-cot").all()) {
    const so = await cot.locator(".kb-the").count();
    await expect(cot.locator(".kb-so")).toHaveText(String(so));
    ra.push({ ten: ((await cot.locator(".kb-dau-cot .nhan-tt").textContent()) ?? "").trim(), so });
  }
  return ra;
}

test.describe("bảng Kanban của điều phối (#560)", () => {
  test.use({ storageState: tepPhien("dieu-phoi") });

  test("mở bằng nút Dạng bảng; cột và số thẻ khớp dải số của hàng đợi, cùng thứ tự; bấm thẻ mở đúng hồ sơ", async ({
    browser,
    page,
  }) => {
    const chung = `Kanban điều phối ${test.info().project.name} ${Date.now()}`;
    const h = await dungHaiHoSoDieuPhoi(browser, chung);

    // Cả hàng đợi: mỗi cột là một ô có hồ sơ của dải số, đúng thứ tự dải, số thẻ bằng số trên ô
    await page.goto("/dieu-phoi", { waitUntil: "networkidle" });
    const ca = await daiSoTrangThai(page);
    await page.getByRole("link", { name: "Dạng bảng" }).click();
    await page.waitForURL((u) => u.pathname === "/dieu-phoi/bang");
    const cot = await cotKanban(page);
    if (ca.tong <= 200) {
      expect(cot).toEqual(ca.cacO);
    } else {
      // Vượt trần một lần đọc: bảng nhắc xem đủ ở dạng danh sách; cột vẫn theo thứ tự dải, không cột rỗng
      await expect(page.locator(".kb-ghi-chu")).toContainText(`trên ${ca.tong} hồ sơ`);
      expect(cot.reduce((s, c) => s + c.so, 0)).toBe(200);
      const viTri = cot.map((c) => ca.cacO.findIndex((o) => o.ten === c.ten));
      expect(viTri.every((v) => v >= 0)).toBe(true);
      expect(viTri).toEqual([...viTri].sort((a, b) => a - b));
      for (const c of cot) expect(c.so).toBeGreaterThan(0);
    }

    // Chỉ hai hồ sơ vừa dựng (ô tìm): hai cột một thẻ, khớp đúng từng ô của dải số
    await page.goto(`/dieu-phoi?q=${encodeURIComponent(chung)}`, { waitUntil: "networkidle" });
    const loc = await daiSoTrangThai(page);
    expect(loc.cacO.map((o) => o.so)).toEqual([1, 1]);
    await page.getByRole("link", { name: "Dạng bảng" }).click();
    await page.waitForURL((u) => u.pathname === "/dieu-phoi/bang" && u.searchParams.get("q") === chung);
    expect(await cotKanban(page)).toEqual(loc.cacO);

    const the = theKanban(page).filter({ hasText: h.daPhanLoai.tieuDe });
    await expect(the).toHaveCount(1);
    await the.click();
    await page.waitForURL(new RegExp(`/dieu-phoi/${h.daPhanLoai.ma}$`));
    await expect(page.getByRole("heading", { level: 1 })).toContainText(h.daPhanLoai.tieuDe);
  });

  test("lọc một loại yêu cầu rồi chuyển qua lại: bộ lọc còn trên địa chỉ trang và trên ô lọc", async ({ page }) => {
    await page.goto("/dieu-phoi", { waitUntil: "networkidle" });
    const oLoai = () => page.getByRole("combobox", { name: "Lọc theo loại yêu cầu" });
    // Mọi kịch bản gửi loại "Sự cố thiết bị", nên hàng đợi có hồ sơ của loại này
    const maLoai = await oLoai()
      .locator("option")
      .evaluateAll((os) => (os as HTMLOptionElement[]).find((o) => o.text === "Sự cố thiết bị")?.value);
    expect(maLoai, "danh mục có loại Sự cố thiết bị").toBeTruthy();
    await oLoai().selectOption(maLoai!);
    await page.waitForURL((u) => u.searchParams.get("loai") === maLoai);
    await page.waitForLoadState("networkidle");

    await page.getByRole("link", { name: "Dạng bảng" }).click();
    await page.waitForURL((u) => u.pathname === "/dieu-phoi/bang" && u.searchParams.get("loai") === maLoai, {
      timeout: 15_000,
    });
    // Bảng đọc theo bộ lọc: chip của bộ lọc hiện, mọi thẻ mang đúng loại đó
    await expect(page.getByRole("link", { name: "Bỏ lọc Sự cố thiết bị" })).toBeVisible();
    const loaiTrenThe = (await page.locator(".kb-the > .kb-phu").allTextContents()).map((s) => s.trim());
    expect(loaiTrenThe.length).toBeGreaterThan(0);
    expect(new Set(loaiTrenThe)).toEqual(new Set(["Sự cố thiết bị"]));

    await page.getByRole("link", { name: "Dạng danh sách" }).click();
    await page.waitForURL((u) => u.pathname === "/dieu-phoi" && u.searchParams.get("loai") === maLoai, {
      timeout: 15_000,
    });
    await expect(oLoai()).toHaveValue(maLoai!);
  });
});

test.describe("bảng Kanban của điều phối với tài khoản không phải điều phối viên (#560)", () => {
  test.use({ storageState: tepPhien("truong-phong") });

  test("mở thẳng /dieu-phoi/bang thì gặp đúng màn từ chối của hàng đợi điều phối", async ({ page }) => {
    for (const duong of ["/dieu-phoi", "/dieu-phoi/bang"]) {
      await page.goto(duong, { waitUntil: "networkidle" });
      await expect(page.getByText("Tài khoản này không mở được khu vực này"), duong).toBeVisible();
      await expect(page.locator(".kb-bang"), duong).toHaveCount(0);
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
