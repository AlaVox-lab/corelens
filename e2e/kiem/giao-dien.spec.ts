// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Các màn chính theo từng vai, chạy ở bốn cấu hình hiển thị (playwright.config.ts). Mỗi màn: mở
// được, không lỗi phía trình duyệt, không cuộn ngang, chụp ảnh. Thêm vài điều kiện nghiệp vụ mà lỗi
// giao diện hay làm sai: số liệu trang chủ khớp danh sách, mục Hệ thống chỉ quản trị viên thấy, nút
// trên dòng việc mở đúng bước.

import { readFileSync } from "node:fs";

import { type Browser, type Page, expect, test } from "@playwright/test";

import { type HoSoThu, type Vai, chup, docHoSo, guiYeuCauThu, tepPhien, theoDoiCsp, viPhamCsp } from "./chung";

/** Mở một màn, gom lỗi phía trình duyệt, kiểm không cuộn ngang, chụp ảnh. */
async function moMan(page: Page, duong: string, anh: string) {
  const loi: string[] = [];
  page.on("pageerror", (e) => loi.push(e.message));
  await theoDoiCsp(page);
  const tl = await page.goto(duong, { waitUntil: "networkidle" });
  expect(tl?.status(), `mở ${duong}`).toBeLessThan(400);
  expect(loi, `lỗi phía trình duyệt ở ${duong}`).toEqual([]);
  expect(await viPhamCsp(page), `vi phạm chính sách nội dung ở ${duong}`).toEqual([]);
  const cuonNgang = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  expect(cuonNgang, `thanh cuộn ngang ở ${duong}`).toBe(false);
  await chup(page, test.info().project.name, anh);
}

/**
 * Dựng một hồ sơ mới tới bước "Chuyển về phòng ban" bằng giao diện, như người thật: người gửi gửi
 * qua biểu mẫu, điều phối viên (phiên của `page`) phân loại. Mỗi bài tự dựng hồ sơ riêng vì bài
 * chuyển phòng làm hồ sơ rời hàng đợi.
 */
async function dungHoSoChoChuyenPhong(browser: Browser, page: Page, nhan: string): Promise<HoSoThu> {
  const nguoiGui = await browser.newContext({ storageState: tepPhien("nguoi-gui") });
  const tieuDe = `${nhan} ${test.info().project.name} ${new Date().toISOString().slice(0, 19)}`;
  const ma = await guiYeuCauThu(await nguoiGui.newPage(), tieuDe);
  await nguoiGui.close();

  await page.goto(`/dieu-phoi/${ma}`, { waitUntil: "networkidle" });
  const thaoTac = page.locator("#thao-tac");
  await thaoTac.getByRole("button", { name: "Phân loại yêu cầu", exact: true }).click();
  await thaoTac.getByRole("button", { name: /^Xác nhận · Phân loại yêu cầu/ }).click();
  await expect(thaoTac.getByRole("button", { name: "Chuyển về phòng ban", exact: true })).toBeVisible();
  return { ma, tieuDe };
}

/** Mở bảng "Chuyển về phòng ban" của hồ sơ và trả ô chọn phòng cùng thẻ gợi ý trên nó. */
async function moBangChuyenPhong(page: Page) {
  const thaoTac = page.locator("#thao-tac");
  await thaoTac.getByRole("button", { name: "Chuyển về phòng ban", exact: true }).click();
  return {
    thaoTac,
    the: thaoTac.locator(".the-goi-y"),
    oPhong: thaoTac.locator('select[name="truong:department_code"]'),
  };
}

function theoVai(vai: Vai) {
  test.use({ storageState: tepPhien(vai) });
}

/**
 * Mục Báo cáo (#305): bảng điều khiển nhúng hiện trong khung, không đòi đăng nhập Superset, đúng
 * phạm vi của người xem. Tên biểu đồ đọc trong khung — có tên là Superset đã nhận token khách và
 * dựng được dashboard; trang đăng nhập của Superset thì không có các tên đó.
 */
async function kiemBaoCao(page: Page, phamVi: string, anh: string) {
  await page.goto("/");
  await expect((await thanhBen(page)).getByRole("link", { name: "Báo cáo" })).toBeVisible();
  await moMan(page, "/bao-cao", anh);
  await expect(page.locator(".bao-cao-pham-vi")).toHaveText(`Phạm vi số liệu: ${phamVi}`);
  const khung = page.frameLocator(".bao-cao-khung iframe");
  for (const ten of ["Tồn đọng theo phòng ban", "Tỷ lệ vi phạm hạn theo phòng ban", "Tỷ lệ ghi đè gợi ý"]) {
    await expect(khung.getByText(new RegExp(ten)).first()).toBeVisible({ timeout: 30_000 });
  }
  // Hàng đánh giá mức hài lòng (#433) ở cuối bảng: cuộn tới để Superset dựng nó, rồi không có thông báo lỗi
  const hangHaiLong = khung.getByText(/Điểm hài lòng trung bình theo phòng ban/).first();
  await hangHaiLong.scrollIntoViewIfNeeded({ timeout: 30_000 });
  await expect(hangHaiLong).toBeVisible({ timeout: 30_000 });
  await expect(khung.getByText(/Phân bố điểm hài lòng/).first()).toBeVisible({ timeout: 30_000 });
  await expect(khung.getByText(/Unexpected error|Lỗi không mong đợi|An error occurred/i)).toHaveCount(0);
  // Khung Superset đã dựng xong: chính sách nội dung của cổng (frame-src) không được chặn nó
  expect(await viPhamCsp(page), "vi phạm chính sách nội dung sau khi nhúng Superset").toEqual([]);
  await chup(page, test.info().project.name, `${anh}-da-ve`);
}

/**
 * Ô "Chờ bạn" kể đúng số việc chờ: bằng số dòng của danh sách, hoặc — khi danh sách chạm trần số
 * dòng mỗi vai — dòng ghi chú nói rõ đang hiện bao nhiêu trên tổng số (#237).
 */
async function kiemSoChoBan(page: Page) {
  const soDong = await page.locator(".ds-viec .dong-viec").count();
  const soCho = Number(await page.locator(".o-so", { hasText: "Chờ bạn" }).locator("strong").innerText());
  if (await page.locator(".ghi-con-lai").isVisible()) {
    expect(soDong).toBeLessThan(soCho);
    await expect(page.locator(".ghi-con-lai")).toContainText(`Đang hiện ${soDong} trên ${soCho} việc`);
  } else {
    expect(soCho).toBe(soDong);
  }
  return soDong;
}

/** Thanh bên chỉ mở ở màn rộng; màn hẹp mở bằng nút menu. */
async function thanhBen(page: Page) {
  await page.waitForLoadState("networkidle");
  const sb = page.locator(".sb");
  const nutMenu = page.locator(".nut-menu");
  if (await nutMenu.isVisible()) {
    await nutMenu.click();
    await expect(sb).toBeVisible();
  }
  return sb;
}

test.describe("người gửi", () => {
  theoVai("nguoi-gui");

  test("các màn chính", async ({ page }) => {
    const h = docHoSo();
    await moMan(page, "/", "nguoi-gui-trang-chu");
    await moMan(page, "/yeu-cau/moi", "nguoi-gui-gui-yeu-cau");
    await moMan(page, "/yeu-cau", "nguoi-gui-ho-so-cua-toi");
    // Hồ sơ dựng lúc chuẩn bị trôi khỏi trang đầu khi các bài khác gửi thêm hồ sơ: tìm theo tiêu đề như người dùng
    await page.goto(`/yeu-cau?q=${encodeURIComponent(h.tieuDe)}`, { waitUntil: "networkidle" });
    await expect(page.getByText(h.tieuDe, { exact: true })).toBeVisible();
    await moMan(page, `/yeu-cau/${h.ma}`, "nguoi-gui-ho-so");
    await moMan(page, "/hop-thu", "nguoi-gui-hop-thu");
  });

  test("bước 2 của biểu mẫu không cuộn ngang, có ô tải tệp (#436)", async ({ page }) => {
    // Bước 2 có trường riêng của loại và ô tải tệp — rộng nhất trong ba bước
    await moMan(page, "/yeu-cau/moi", "nguoi-gui-gui-yeu-cau-buoc-1");
    // Bấm thẻ loại là sang thẳng bước 2, như guiYeuCauThu trong chung.ts
    await page.getByText("Sự cố thiết bị").first().click();
    await expect(page.locator('input[name="title"]')).toBeVisible();
    await expect(page.locator('input[type="file"]')).toHaveCount(1);
    const cuonNgang = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    expect(cuonNgang, "thanh cuộn ngang ở bước 2 của biểu mẫu").toBe(false);
    await chup(page, test.info().project.name, "nguoi-gui-gui-yeu-cau-buoc-2");
  });

  test("?loai= mở thẳng bước 2 với loại chọn sẵn; mã lạ về bước 1 (#434)", async ({ page }) => {
    // `device-incident` là mã của loại "Sự cố thiết bị" trong dữ liệu khởi tạo (infra/seed/)
    await moMan(page, "/yeu-cau/moi?loai=device-incident", "nguoi-gui-gui-yeu-cau-loai-san");
    await expect(page.locator('input[name="title"]')).toBeVisible();
    await expect(page.locator("#truong-rieng-ma-tai-san")).toBeVisible();

    await moMan(page, "/yeu-cau/moi?loai=khong-co-loai-nay", "nguoi-gui-gui-yeu-cau-loai-la");
    await expect(page.locator('input[name="title"]')).toBeHidden();
    await expect(page.getByText("Sự cố thiết bị").first()).toBeVisible();
  });

  test("mô hình nhúng tắt: gõ nội dung không hiện hồ sơ tương tự, vẫn gửi bình thường (#319)", async ({ page }) => {
    // Cụm mặc định không bật hồ sơ `tri-tue`: dịch vụ báo tắt, biểu mẫu không hiện gì, không báo lỗi
    const tra = await page.request.post("/api/yeu-cau/tuong-tu", {
      data: { title: "Máy in tầng 3 kẹt giấy liên tục", description: "In vài trang là kẹt" },
    });
    expect(tra.status()).toBe(200);
    // Từ #321 phản hồi có thêm phần bài kho tri thức, rỗng khi tắt
    expect(await tra.json()).toEqual({ items: [], articles: [], articles_source_url: null, enabled: false });

    // Biểu mẫu có hỏi sau khi ngừng gõ, không hiện gì, và vẫn gửi xong như cũ
    await page.goto("/yeu-cau/moi");
    await page.getByText("Sự cố thiết bị").first().click();
    const hoi = page.waitForResponse("**/api/yeu-cau/tuong-tu");
    await page.locator('input[name="title"]').fill(`Gửi khi mô hình tắt ${Date.now()}`);
    await page.locator('textarea[name="description"]').fill("Máy in tầng 3 kẹt giấy liên tục.");
    expect((await hoi).status()).toBe(200);
    await expect(page.getByTestId("goi-y-tuong-tu")).toHaveCount(0);
    await page.locator("#truong-rieng-ma-tai-san").fill("KT-0001");
    await page.locator("#truong-rieng-vi-tri").fill("Phòng thử nghiệm");
    await page.getByRole("button", { name: "Tiếp tục" }).click();
    await page.getByRole("button", { name: "Gửi yêu cầu" }).click();
    await page.waitForURL(/\/yeu-cau\/\d+/);
  });

  test("hồ sơ tương tự hiện dưới ô mô tả, bấm không gửi nữa thì rời biểu mẫu (#319)", async ({ page }) => {
    // Dữ liệu gợi ý dựng ở Route Handler, không cần mô hình nhúng thật
    await page.route("**/api/yeu-cau/tuong-tu", (r) =>
      r.fulfill({
        json: {
          enabled: true,
          items: [
            {
              title: "Máy in tầng 3 kẹt giấy liên tục",
              request_type: "Sự cố thiết bị",
              resolution: "Đã vệ sinh và thay con lăn kéo giấy.",
              closed_at: "2026-10-20T03:00:00Z",
              score: 0.81,
            },
          ],
        },
      }),
    );
    let phienBo: string | null = null;
    page.on("request", (r) => {
      if (r.url().endsWith("/api/yeu-cau/tuong-tu/bo")) phienBo = (r.postDataJSON() as { session_id: string }).session_id;
    });

    await page.goto("/yeu-cau/moi");
    await page.getByText("Sự cố thiết bị").first().click();
    await page.locator('input[name="title"]').fill("Máy in chung cứ bị mắc giấy");
    await page.locator('textarea[name="description"]').fill("In vài tờ là giấy bị nghẽn bên trong.");
    const khoi = page.getByTestId("goi-y-tuong-tu");
    await expect(khoi).toBeVisible();
    await expect(khoi).toContainText("Máy in tầng 3 kẹt giấy liên tục");
    await expect(khoi).toContainText("Đã vệ sinh và thay con lăn kéo giấy.");
    await expect(khoi).toContainText("Gợi ý của hệ thống");
    // Không lộ mã hồ sơ của người khác, không dẫn tới hồ sơ nào
    await expect(khoi.locator("a")).toHaveCount(0);

    await khoi.getByRole("button", { name: "Đã giải quyết được, không gửi nữa" }).click();
    await page.waitForURL(/\/yeu-cau$/);
    expect(phienBo).toMatch(/^[0-9a-f-]{36}$/);
  });

  test("không thấy mục Hệ thống, mở thẳng thì bị từ chối", async ({ page }) => {
    await page.goto("/");
    await expect((await thanhBen(page)).getByRole("link", { name: "Hệ thống" })).toHaveCount(0);
    await page.goto("/he-thong");
    await expect(page.getByText("Tài khoản này không mở được khu vực này")).toBeVisible();
  });

  test("không thấy mục Cấu hình quy trình, mở thẳng thì bị từ chối (#255)", async ({ page }) => {
    await page.goto("/");
    await expect((await thanhBen(page)).getByRole("link", { name: "Cấu hình quy trình" })).toHaveCount(0);
    await page.goto("/quan-tri/cau-hinh");
    await expect(page.getByText("Tài khoản này không mở được khu vực này")).toBeVisible();
    await expect(page.locator("tr[data-dong-cau-hinh]")).toHaveCount(0);
  });

  test("không thấy mục Báo cáo, mở thẳng thì bị từ chối (#305)", async ({ page }) => {
    await page.goto("/");
    await expect((await thanhBen(page)).getByRole("link", { name: "Báo cáo" })).toHaveCount(0);
    await page.goto("/bao-cao");
    await expect(page.getByText("Tài khoản này không mở được khu vực này")).toBeVisible();
    await expect(page.locator(".bao-cao-khung")).toHaveCount(0);
    expect((await page.request.post("/api/bao-cao/token")).status()).toBe(403);
  });
});

test.describe("điều phối viên", () => {
  theoVai("dieu-phoi");

  test("các màn chính", async ({ page }) => {
    const h = docHoSo();
    await moMan(page, "/", "dieu-phoi-trang-chu");
    await moMan(page, "/dieu-phoi", "dieu-phoi-hang-doi");
    await moMan(page, `/dieu-phoi/${h.ma}`, "dieu-phoi-ho-so");
  });

  test("số liệu trang chủ khớp danh sách việc chờ", async ({ page }) => {
    await page.goto("/", { waitUntil: "networkidle" });
    // Ô "Chờ bạn", câu chào và danh sách kể cùng một con số
    await kiemSoChoBan(page);
    const soCho = await page.locator(".o-so", { hasText: "Chờ bạn" }).locator("strong").innerText();
    if (soCho !== "0") await expect(page.locator(".cau-chao")).toContainText(`${soCho} việc chờ bạn`);
  });

  test("hồ sơ vừa gửi nằm trong việc chờ, nút mở đúng bước", async ({ page }) => {
    const h = docHoSo();
    await page.goto("/", { waitUntil: "networkidle" });
    // Cụm có hơn 200 việc chờ: hồ sơ mới nhất có thể nằm ngoài trần của trang chủ
    test.skip(await page.locator(".ghi-con-lai").isVisible(), "danh sách trang chủ chạm trần số dòng");
    const dong = page.locator(".dong-viec", { hasText: h.tieuDe });
    await expect(dong).toBeVisible();
    const nut = dong.locator("a.nut");
    const buoc = (await nut.innerText()).replace(/→/g, "").trim();
    expect(buoc).toBe("Phân loại yêu cầu");
    await nut.click();
    await page.waitForURL(new RegExp(`/dieu-phoi/${h.ma}#thao-tac$`));
    // Bảng thao tác có đúng bước mà dòng việc hứa
    await expect(page.locator("#thao-tac").getByRole("button", { name: buoc })).toBeVisible();
  });

  test("xem nhanh: mở từ dòng, duyệt bằng mũi tên, Esc trả tiêu điểm về dòng", async ({ page }) => {
    await page.goto("/dieu-phoi", { waitUntil: "networkidle" });
    const dong = page.locator("a.lk-dong");
    const soDong = await dong.count();
    expect(soDong, "hàng đợi có ít nhất hồ sơ của bước chuẩn bị").toBeGreaterThan(0);

    await dong.first().click();
    const ngan = page.locator("aside.ngan");
    await expect(ngan).toBeVisible();
    await expect(page).toHaveURL(/[?&]xem=\d+/);
    await expect(ngan.getByRole("heading", { level: 2 })).toBeFocused();
    await expect(ngan.locator(".ngan-vi-tri")).toHaveText(/^1 trên \d+$/);
    // Màn hẹp: ngăn chiếm trọn chiều ngang; không màn nào cuộn ngang khi ngăn mở
    const rong = page.viewportSize()!.width;
    // Làm tròn: lúc hiệu ứng trượt vào còn chạy, trình duyệt trả bề ngang lệch phần nghìn điểm ảnh
    if (rong < 768) expect(Math.round((await ngan.boundingBox())!.width)).toBe(rong);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)).toBe(false);
    await chup(page, test.info().project.name, "dieu-phoi-xem-nhanh");

    // Duyệt tới 10 hồ sơ chỉ bằng phím, không rời trang danh sách
    for (let i = 2; i <= Math.min(10, soDong); i++) {
      await page.keyboard.press("ArrowDown");
      await expect(ngan.locator(".ngan-vi-tri")).toHaveText(new RegExp(`^${i} trên \\d+$`));
      await expect(page).toHaveURL(/\/dieu-phoi\?/);
    }

    const ma = new URL(page.url()).searchParams.get("xem");
    await page.keyboard.press("Escape");
    await expect(ngan).toHaveCount(0);
    await expect(page).not.toHaveURL(/xem=/);
    await expect(page.locator(`[data-xem-dong="${ma}"]`)).toBeFocused();
  });

  test("xem nhanh mở thẳng bằng địa chỉ, nút chính là bước chính của hồ sơ", async ({ page }) => {
    const h = docHoSo();
    await page.goto(`/dieu-phoi?xem=${h.ma}`, { waitUntil: "networkidle" });
    const ngan = page.locator("aside.ngan");
    await expect(ngan.getByRole("heading", { level: 2 })).toHaveText(h.tieuDe);
    // Hồ sơ vừa gửi chờ điều phối viên phân loại — bước chính khai trong dữ liệu quy tắc
    await expect(ngan.locator(".ngan-chan .nut[data-loai='chinh']")).toContainText("Phân loại yêu cầu");
    await expect(ngan.getByRole("link", { name: "Mở trang đầy đủ" })).toHaveAttribute("href", `/dieu-phoi/${h.ma}`);
  });

  test("chuyển động: không quá 300 ms, số trang chủ không đếm từ 0", async ({ page }) => {
    // Ghi mọi hiệu ứng CSS bắt đầu chạy trên trang, kèm mốc kết thúc (thời lượng + độ trễ)
    await page.addInitScript(() => {
      const ghi: { ten: string; ms: number }[] = [];
      (window as unknown as { __chuyenDong: typeof ghi }).__chuyenDong = ghi;
      const nghe = (e: AnimationEvent | TransitionEvent) => {
        const ten = "animationName" in e ? e.animationName : e.propertyName;
        for (const a of (e.target as Element).getAnimations()) {
          const t = a.effect?.getComputedTiming();
          if (t && t.iterations !== Infinity) ghi.push({ ten, ms: Number(t.endTime) });
        }
      };
      document.addEventListener("animationstart", nghe, true);
      document.addEventListener("transitionrun", nghe, true);
    });
    const qua300 = () =>
      page.evaluate(() =>
        (window as unknown as { __chuyenDong: { ten: string; ms: number }[] }).__chuyenDong.filter((c) => c.ms > 300),
      );

    await page.goto("/", { waitUntil: "networkidle" });
    await expect(page.locator(".so-cuon[data-huong]"), "mở trang không cuộn số nào").toHaveCount(0);
    if (await page.locator(".khoi-viec .nut-sx").isVisible()) {
      await page.locator(".khoi-viec .nut-sx").click();
      await page.keyboard.press("Escape");
    }
    expect(await qua300(), "trang chủ").toEqual([]);

    await page.goto("/dieu-phoi", { waitUntil: "networkidle" });
    await page.locator("a.lk-dong").first().click();
    const ngan = page.locator("aside.ngan");
    await expect(ngan).toBeVisible();
    const menu = ngan.locator("details.menu-thao-tac > summary");
    if (await menu.isVisible()) {
      await menu.click();
      await page.keyboard.press("Escape");
    }
    const chinh = ngan.locator(".ngan-chan .nut[data-loai='chinh']");
    if (await chinh.isVisible()) {
      await chinh.click();
      await ngan.getByRole("button", { name: "Thôi" }).click();
      await expect(ngan.locator(".khung-xac-nhan")).toHaveCount(0);
    }
    await page.keyboard.press("Escape");
    await expect(ngan).toHaveCount(0);
    expect(await qua300(), "hàng đợi và ngăn xem nhanh").toEqual([]);
  });

  test("thẻ gợi ý phòng ban: có lý do và nguồn, không độ tin cậy giả, không hoàn tác, đổi phòng thì thẻ báo chọn khác (#239)", async ({ browser, page }) => {
    const loi: string[] = [];
    page.on("pageerror", (e) => loi.push(e.message));
    const h = await dungHoSoChoChuyenPhong(browser, page, "Thẻ gợi ý");
    const { thaoTac, the, oPhong } = await moBangChuyenPhong(page);

    // Thẻ nằm ngay trên ô chọn phòng và nói đủ ba điều: gợi ý gì, vì sao, từ đâu
    await expect(the).toBeVisible();
    await expect(the.locator(".the-goi-y-dau")).toContainText("Gợi ý:");
    const goiY = await the.locator(".the-goi-y-dau strong").innerText();
    expect(goiY.trim(), "thẻ nêu tên phòng gợi ý").not.toBe("");
    await expect(the.locator(".the-goi-y-ly-do")).not.toBeEmpty();
    await expect(the.locator(".the-goi-y-nguon")).toContainText("Nguồn:");
    // Nguồn là bảng ánh xạ, không có con số thật: không được vẽ độ tin cậy
    await expect(the).not.toContainText(/tin cậy/i);
    await expect(the).not.toContainText("%");
    // Gợi ý điền sẵn ô, và ô trỏ vào thẻ để trình đọc màn hình đọc cùng nhau
    await expect(oPhong.locator("option:checked")).toContainText(goiY);
    await expect(oPhong).toHaveAttribute("aria-describedby", (await the.getAttribute("id"))!);
    // Chuyển trạng thái không quay lui và nhật ký chỉ ghi thêm: không có nút hoàn tác hay chấp nhận riêng
    await expect(thaoTac.getByRole("button", { name: /hoàn tác|chấp nhận/i })).toHaveCount(0);
    await expect(thaoTac.getByRole("button", { name: /^Xác nhận · Chuyển về phòng ban/ })).toBeVisible();
    await expect(the.locator(".the-goi-y-khac")).toHaveText("");
    await chup(page, test.info().project.name, "dieu-phoi-the-goi-y");

    // Đổi sang phòng khác: thẻ nói nhẹ là đang chọn khác gợi ý, không chặn gì
    const maGoiY = await oPhong.inputValue();
    const cacMa = await oPhong.locator("option").evaluateAll((os) => os.map((o) => (o as HTMLOptionElement).value));
    const maKhac = cacMa.find((v) => v !== "" && v !== maGoiY);
    expect(maKhac, "danh mục có ít nhất một phòng khác gợi ý").toBeTruthy();
    await oPhong.selectOption(maKhac!);
    await expect(the.locator(".the-goi-y-khac")).toHaveText(/Bạn đang chọn khác gợi ý/);
    await expect(the).toHaveAttribute("data-khac", "");
    await expect(thaoTac.getByRole("button", { name: /^Xác nhận · Chuyển về phòng ban/ })).toBeEnabled();
    await chup(page, test.info().project.name, "dieu-phoi-the-goi-y-chon-khac");
    // Chọn lại đúng gợi ý thì lời nhắc biến mất
    await oPhong.selectOption(maGoiY);
    await expect(the.locator(".the-goi-y-khac")).toHaveText("");
    await expect(the).not.toHaveAttribute("data-khac", "");

    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1), "cuộn ngang").toBe(false);
    expect(loi, `lỗi phía trình duyệt ở hồ sơ ${h.ma}`).toEqual([]);
  });

  test("giữ gợi ý phòng ban rồi bấm chuyển phòng: hồ sơ sang trạng thái mới, đúng phòng gợi ý (#239)", async ({ browser, page }) => {
    await dungHoSoChoChuyenPhong(browser, page, "Giữ gợi ý");
    const { thaoTac, the, oPhong } = await moBangChuyenPhong(page);
    const goiY = await the.locator(".the-goi-y-dau strong").innerText();
    await expect(oPhong.locator("option:checked")).toContainText(goiY);

    await thaoTac.getByRole("button", { name: /^Xác nhận · Chuyển về phòng ban/ }).click();
    // Chuyển xong: trạng thái mới, phòng là phòng được gợi ý, và không còn thao tác chuyển phòng nào
    await expect(page.getByText("Chờ phòng ban xác duyệt").first()).toBeVisible();
    await expect(page.locator("main")).toContainText(goiY);
    await expect(page.locator("#thao-tac").getByRole("button", { name: "Chuyển về phòng ban", exact: true })).toHaveCount(0);
  });

  test("đổi sang phòng khác gợi ý rồi chuyển phòng: hồ sơ đến đúng phòng đã chọn (#239)", async ({ browser, page }) => {
    await dungHoSoChoChuyenPhong(browser, page, "Ghi đè gợi ý");
    const { thaoTac, oPhong } = await moBangChuyenPhong(page);
    const maGoiY = await oPhong.inputValue();
    const khac = await oPhong
      .locator("option")
      .evaluateAll((os, ma) => os.map((o) => ({ v: (o as HTMLOptionElement).value, t: o.textContent ?? "" })).find((o) => o.v && o.v !== ma), maGoiY);
    expect(khac, "danh mục có ít nhất một phòng khác gợi ý").toBeTruthy();
    await oPhong.selectOption(khac!.v);

    await thaoTac.getByRole("button", { name: /^Xác nhận · Chuyển về phòng ban/ }).click();
    await expect(page.getByText("Chờ phòng ban xác duyệt").first()).toBeVisible();
    await expect(page.locator("main")).toContainText(khac!.t.trim());
  });

  test("đổi loại yêu cầu thì thẻ và phòng điền sẵn đổi theo, trừ khi đã tự chọn phòng (#239)", async ({ browser, page }) => {
    await dungHoSoChoChuyenPhong(browser, page, "Thẻ đổi theo loại");
    const { thaoTac, the, oPhong } = await moBangChuyenPhong(page);
    const oLoai = thaoTac.locator('select[name="truong:request_type_code"]');
    const goiYDau = await the.locator(".the-goi-y-dau strong").innerText();
    const maLoaiDau = await oLoai.inputValue();
    const cacLoai = await oLoai
      .locator("option")
      .evaluateAll((os) => os.map((o) => ({ v: (o as HTMLOptionElement).value, t: (o.textContent ?? "").trim() })).filter((o) => o.v));

    // Thử lần lượt các loại khác cho tới khi gặp loại có phòng gợi ý khác — dữ liệu quyết, không mã cứng
    let loaiMoi: { v: string; t: string } | undefined;
    for (const loai of cacLoai.filter((l) => l.v !== maLoaiDau)) {
      await oLoai.selectOption(loai.v);
      if ((await the.locator(".the-goi-y-dau strong").innerText()) !== goiYDau) {
        loaiMoi = loai;
        break;
      }
    }
    expect(loaiMoi, "có loại yêu cầu gợi ý phòng khác loại đầu").toBeTruthy();
    // Thẻ nói đúng loại mới, và ô phòng điền sẵn theo gợi ý mới vì người dùng chưa đụng vào nó
    const goiYMoi = await the.locator(".the-goi-y-dau strong").innerText();
    await expect(the.locator(".the-goi-y-ly-do")).toContainText(loaiMoi!.t);
    await expect(oPhong.locator("option:checked")).toContainText(goiYMoi);
    await expect(the.locator(".the-goi-y-khac")).toHaveText("");

    // Tự chọn một phòng khác gợi ý, rồi quay lại loại đầu: thẻ đổi, phòng của người dùng giữ nguyên
    const maGoiYMoi = await oPhong.inputValue();
    const phongTay = await oPhong
      .locator("option")
      .evaluateAll((os, ma) => os.map((o) => (o as HTMLOptionElement).value).find((v) => v && v !== ma), maGoiYMoi);
    await oPhong.selectOption(phongTay!);
    await oLoai.selectOption(maLoaiDau);
    await expect(the.locator(".the-goi-y-dau strong")).toHaveText(goiYDau);
    await expect(oPhong).toHaveValue(phongTay!);
    // Phòng người dùng chọn có thể trùng đúng gợi ý của loại đầu; khi khác thì thẻ phải nói
    const oPhongKhacGoiY = !(await oPhong.locator("option:checked").innerText()).includes(goiYDau);
    if (oPhongKhacGoiY) await expect(the.locator(".the-goi-y-khac")).toHaveText(/Bạn đang chọn khác gợi ý/);
  });

  test("mô hình nhúng tắt: thẻ gợi ý phòng ban y như cũ, không khối hồ sơ tương tự (#450)", async ({ browser, page }) => {
    // Cụm mặc định không bật hồ sơ `tri-tue`: tuyến căn cứ báo tắt, thẻ không có gì thêm, không lỗi
    const loi: string[] = [];
    page.on("pageerror", (e) => loi.push(e.message));
    const traLoi = page.waitForResponse((r) => r.url().includes("/api/dieu-phoi/tuong-tu/"));
    await dungHoSoChoChuyenPhong(browser, page, "Căn cứ tắt");
    const { the } = await moBangChuyenPhong(page);
    await expect(the).toBeVisible();
    expect(await (await traLoi).json()).toEqual({ items: [], enabled: false });
    await expect(the.locator(".can-cu-tuong-tu")).toHaveCount(0);
    expect(loi).toEqual([]);
  });

  test("mô hình nhúng bật: thẻ gợi ý kèm hồ sơ đã giải quyết tương tự, mã mở hồ sơ đó (#450)", async ({ browser, page }) => {
    // Cụm thử không chạy mô hình nhúng: giả lập đúng phản hồi của tuyến để kiểm phần hiển thị
    await page.route("**/api/dieu-phoi/tuong-tu/*", (route) =>
      route.fulfill({
        json: {
          enabled: true,
          items: [
            { case_id: 7, code: "YC-2026-0007", title: "Máy chiếu không lên hình", request_type: "Sự cố thiết bị",
              resolution: "Đổi cáp HDMI mới.", closed_at: "2026-10-01T03:00:00+00:00", score: 0.81 },
            { case_id: 9, code: "YC-2026-0009", title: "Màn hình phòng họp nhấp nháy", request_type: null,
              resolution: "Thay nguồn màn hình.", closed_at: "2026-10-03T03:00:00+00:00", score: 0.66 },
          ],
        },
      }),
    );
    await dungHoSoChoChuyenPhong(browser, page, "Căn cứ bật");
    const { the } = await moBangChuyenPhong(page);
    const khoi = the.locator(".can-cu-tuong-tu");
    await expect(khoi).toContainText("Hồ sơ đã giải quyết tương tự");
    await expect(khoi.locator("li")).toHaveCount(2);
    await expect(khoi.getByRole("link", { name: "YC-2026-0007" })).toHaveAttribute("href", "/dieu-phoi/7");
    await expect(khoi).toContainText("Đổi cáp HDMI mới.");
    // Không cuộn ngang dù thêm khối
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)).toBe(false);
    await the.scrollIntoViewIfNeeded();
    await chup(page, test.info().project.name, "dieu-phoi-the-goi-y-can-cu");
  });

  test("Báo cáo có số của toàn công ty (#305)", async ({ page }) => {
    await kiemBaoCao(page, "toàn công ty", "dieu-phoi-bao-cao");
  });

  test("thấy mục Điều phối, không thấy Hệ thống", async ({ page }) => {
    await page.goto("/");
    const sb = await thanhBen(page);
    await expect(sb.getByRole("link", { name: /Điều phối/ })).toBeVisible();
    await expect(sb.getByRole("link", { name: "Hệ thống" })).toHaveCount(0);
  });
});

test.describe("trưởng phòng", () => {
  theoVai("truong-phong");

  test("các màn chính", async ({ page }) => {
    await moMan(page, "/", "truong-phong-trang-chu");
    await moMan(page, "/phong-ban", "truong-phong-hang-doi");
    await moMan(page, "/hop-thu", "truong-phong-hop-thu");
  });

  test("số liệu trang chủ khớp danh sách việc chờ", async ({ page }) => {
    await page.goto("/", { waitUntil: "networkidle" });
    await kiemSoChoBan(page);
  });

  test("Báo cáo chỉ có số của phòng mình (#305)", async ({ page }) => {
    await kiemBaoCao(page, "Công nghệ thông tin", "truong-phong-bao-cao");
  });
});

/** Mở trang hồ sơ và chờ tuyến bước lệch trả lời (#448) — khối vẽ sau khi trang hiện. */
async function moVaChoTuanThu(page: Page, duong: string) {
  const traLoi = page.waitForResponse((r) => r.url().includes("/api/tuan-thu/"));
  await page.goto(duong, { waitUntil: "networkidle" });
  return (await traLoi).json();
}

test.describe("bước lệch quy trình trên trang hồ sơ (#448)", () => {
  theoVai("dieu-phoi");

  test("hồ sơ đi đúng luồng không có khối; bị phòng từ chối thì khối hiện đúng bước, chỉ đọc", async ({ browser, page }) => {
    // Luồng thật, không giả lập: người gửi gửi, điều phối viên phân loại và chuyển về phòng của trưởng phòng
    const h = await dungHoSoChoChuyenPhong(browser, page, "Bước lệch");
    const { thaoTac, oPhong } = await moBangChuyenPhong(page);
    // Phòng của trưởng phòng mẫu; tùy chọn được gợi ý mang thêm đuôi "· gợi ý" nên tìm theo đầu chữ
    const maPhong = await oPhong
      .locator("option")
      .evaluateAll((os) => (os as HTMLOptionElement[]).find((o) => o.text.startsWith("Công nghệ thông tin"))?.value);
    expect(maPhong, "danh mục có phòng Công nghệ thông tin").toBeTruthy();
    await oPhong.selectOption(maPhong!);
    await thaoTac.getByRole("button", { name: /^Xác nhận · Chuyển về phòng ban/ }).click();
    await expect(page.getByText("Chờ phòng ban xác duyệt").first()).toBeVisible();

    const tp = await browser.newContext({ storageState: tepPhien("truong-phong") });
    const trang = await tp.newPage();
    const loi: string[] = [];
    trang.on("pageerror", (e) => loi.push(e.message));

    // Chưa lệch: dịch vụ trả lời đủ, trang không có khối, không khung trống
    const truoc = await moVaChoTuanThu(trang, `/phong-ban/${h.ma}`);
    expect(truoc).toMatchObject({ status: "ready", deviates: false, steps: [] });
    await expect(trang.locator(".buoc-lech")).toHaveCount(0);

    // Trưởng phòng từ chối vì sai chuyên môn — cạnh làm lại của bộ quy tắc mẫu
    const tt = trang.locator("#thao-tac");
    await tt.getByRole("button", { name: "Từ chối vì sai chuyên môn", exact: true }).click();
    await tt.locator('textarea[name="note"]').fill("Việc này thuộc phòng khác — kịch bản #448.");
    await tt.getByRole("button", { name: /^Xác nhận · Từ chối vì sai chuyên môn/ }).click();
    // Chờ bước chuyển ghi xong: tên trạng thái đích đã có sẵn trong bảng xác nhận nên không dùng làm dấu
    // được; hồ sơ rời trạng thái chờ xác duyệt thì thao tác từ chối không còn
    await expect(tt.getByRole("button", { name: "Từ chối vì sai chuyên môn", exact: true })).toHaveCount(0);

    const sau = await moVaChoTuanThu(trang, `/phong-ban/${h.ma}`);
    // Trang dựng sau khi bước chuyển đã ghi: không còn thao tác của trạng thái chờ xác duyệt
    await expect(trang.locator("#thao-tac").getByRole("button", { name: "Xác duyệt và giao xử lý", exact: true })).toHaveCount(0);
    expect(sau).toMatchObject({ status: "ready", deviates: true });
    const khoi = trang.locator(".buoc-lech");
    await expect(khoi).toBeVisible();
    await expect(khoi.locator("li")).toHaveCount(1);
    // Nhãn loại lệch của màn Quy trình thực tế; nhãn trạng thái từ bộ quy tắc
    await expect(khoi).toContainText("Trả về làm lại");
    await expect(khoi).toContainText("Chờ phòng ban xác duyệt → Bị phòng ban từ chối");
    // Chỉ thông tin: không nút nào. Liên kết mã nguồn AGPL ở trang Mã nguồn và giấy phép, không chen vào khối (#540)
    await expect(khoi.getByRole("button")).toHaveCount(0);
    await expect(khoi).not.toContainText("AGPL");
    expect(await trang.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)).toBe(false);
    await khoi.scrollIntoViewIfNeeded();
    await chup(trang, test.info().project.name, "phong-ban-buoc-lech");
    expect(loi).toEqual([]);
    await tp.close();

    // Điều phối viên mở cùng hồ sơ cũng thấy cùng bước
    await moVaChoTuanThu(page, `/dieu-phoi/${h.ma}`);
    await expect(page.locator(".buoc-lech")).toContainText("Trả về làm lại");

    // Người gửi: trang của mình không có khối, gọi thẳng tuyến cũng chỉ nhận "không có"
    const ng = await browser.newContext({ storageState: tepPhien("nguoi-gui") });
    const trangNg = await ng.newPage();
    await trangNg.goto(`/yeu-cau/${h.ma}`, { waitUntil: "networkidle" });
    await expect(trangNg.locator(".buoc-lech")).toHaveCount(0);
    const tuyen = await trangNg.request.get(`/api/tuan-thu/${h.ma}`);
    expect(await tuyen.json()).toMatchObject({ status: "unavailable", steps: [] });
    await ng.close();
  });

  test("dịch vụ khai phá không trả lời: trang hồ sơ y như cũ, không lỗi", async ({ page }) => {
    await page.route("**/api/tuan-thu/*", (route) =>
      route.fulfill({ json: { status: "unavailable", case_id: 0, deviates: false, steps: [] } }),
    );
    const loi: string[] = [];
    page.on("pageerror", (e) => loi.push(e.message));
    await moVaChoTuanThu(page, `/dieu-phoi/${docHoSo().ma}`);
    await expect(page.locator(".buoc-lech")).toHaveCount(0);
    await expect(page.locator("#thao-tac")).toBeVisible();
    expect(loi).toEqual([]);
  });
});

test.describe("quản trị viên", () => {
  theoVai("quan-tri");

  test("màn Hệ thống báo bộ quy tắc đã nạp", async ({ page }) => {
    await moMan(page, "/", "quan-tri-trang-chu");
    await expect((await thanhBen(page)).getByRole("link", { name: "Hệ thống" })).toBeVisible();
    await moMan(page, "/he-thong", "quan-tri-he-thong");
    await expect(page.getByText("Bộ quy tắc quy trình")).toBeVisible();
    await expect(page.getByText(/đã nạp/)).toBeVisible();
    // Nhịp hai bộ quét nền (#253) đọc từ điểm cuối chi tiết của quản trị viên
    await expect(page.getByText("Bộ quét quá hạn SLA")).toBeVisible();
    await expect(page.getByText("Bộ quét hạn chờ")).toBeVisible();
  });

  test("tải nhật ký sự kiện dạng CSV từ màn Hệ thống (#306)", async ({ page }) => {
    await page.goto("/he-thong", { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: "Xuất nhật ký sự kiện" })).toBeVisible();
    const [tep] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Tải CSV" }).click(),
    ]);
    expect(tep.suggestedFilename()).toMatch(/\.csv$/);
    const noiDung = readFileSync((await tep.path()) as string);
    // Có BOM để bảng tính nhận UTF-8, dòng đầu là đúng các cột của định dạng
    expect([...noiDung.subarray(0, 3)]).toEqual([0xef, 0xbb, 0xbf]);
    expect(noiDung.toString("utf-8").slice(1).split("\r\n")[0]).toBe(
      // `process_code` ở cuối từ #376 — công cụ đọc theo vị trí cột cũ không vỡ
      "case_id,activity,timestamp,actor,from_state,to_state,request_type_code,department_code,priority_code,rule_set_id,process_code",
    );
  });

  // Màn quản trị cấu hình (#255). Mỗi bài sửa rồi trả lại giá trị cũ, nên chạy lại ở cả bốn cấu hình
  // hiển thị vẫn ra cùng kết quả; nhật ký sửa thì dài thêm — đúng là chỉ ghi thêm.
  async function suaMotO(page: Page, dong: ReturnType<Page["locator"]>, o: string, giaTri: string) {
    await dong.getByRole("button", { name: /^Sửa / }).click();
    const bieuMau = page.locator("tr:has(form)");
    await bieuMau.locator(`[name="${o}"]`).fill(giaTri);
    await bieuMau.getByRole("button", { name: "Xem trước" }).click();
    await expect(bieuMau.getByRole("status")).toContainText("đã qua kiểm tra");
    await bieuMau.getByRole("button", { name: "Lưu" }).click();
    await expect(bieuMau).toHaveCount(0);
  }

  test("sửa hạn chuẩn của loại yêu cầu ngay trên màn, có xem trước và nhật ký (#255)", async ({ page }) => {
    // Kiểm thanh bên trước khi mở màn: ở màn hẹp thanh bên là ngăn kéo, mở ra thì che nội dung
    await page.goto("/");
    await expect((await thanhBen(page)).getByRole("link", { name: "Cấu hình quy trình" })).toBeVisible();
    await moMan(page, "/quan-tri/cau-hinh", "quan-tri-cau-hinh");
    const dong = page.locator('tr[data-dong-cau-hinh^="request-types/"]').first();
    const cu = (await dong.locator("td").nth(1).innerText()).trim();
    const moi = String(Number(cu) + 1);

    await dong.getByRole("button", { name: /^Sửa / }).click();
    const bieuMau = page.locator("tr:has(form)");
    await bieuMau.locator('[name="sla_hours"]').fill(moi);
    await bieuMau.getByRole("button", { name: "Xem trước" }).click();
    // Đổi hạn: màn báo trước số hồ sơ đang mở bị ảnh hưởng, chưa lưu gì
    await expect(bieuMau.getByRole("status")).toContainText(`→ ${moi}`);
    await expect(bieuMau.getByRole("status")).toContainText(/hồ sơ đang mở/);
    await expect(dong.locator("td").nth(1)).toHaveText(cu);
    await bieuMau.getByRole("button", { name: "Lưu" }).click();
    await expect(dong.locator("td").nth(1)).toHaveText(moi);

    const nhatKy = page.locator("[data-nhat-ky-cau-hinh] tbody tr").first();
    await expect(nhatKy).toContainText("Hạn chuẩn");
    await expect(nhatKy).toContainText(cu);
    await expect(nhatKy).toContainText(moi);

    await suaMotO(page, dong, "sla_hours", cu);
    await expect(dong.locator("td").nth(1)).toHaveText(cu);
  });

  test("đổi tên phòng ban ngay trên màn rồi trả lại (#255)", async ({ page }) => {
    await page.goto("/quan-tri/cau-hinh", { waitUntil: "networkidle" });
    const dong = page.locator('tr[data-dong-cau-hinh^="departments/"]').first();
    const cu = (await dong.locator("td").first().innerText()).trim();
    await suaMotO(page, dong, "label", `${cu} (thử)`);
    await expect(dong.locator("td").first()).toHaveText(`${cu} (thử)`);
    await suaMotO(page, dong, "label", cu);
    await expect(dong.locator("td").first()).toHaveText(cu);
  });

  test("ngưng phòng đang là phòng mặc định thì bị chặn kèm lý do, không lưu gì (#255)", async ({ page }) => {
    await page.goto("/quan-tri/cau-hinh", { waitUntil: "networkidle" });
    const dong = page.locator('tr[data-dong-cau-hinh^="departments/"]').first();
    await dong.getByRole("button", { name: /^Sửa / }).click();
    const bieuMau = page.locator("tr:has(form)");
    await bieuMau.locator('[name="is_active"]').uncheck();
    await bieuMau.getByRole("button", { name: "Xem trước" }).click();
    await expect(bieuMau.getByRole("alert")).toContainText("phòng ban mặc định đã ngưng");
    await expect(bieuMau.getByRole("button", { name: "Lưu" })).toHaveCount(0);
    await expect(dong.locator("td").nth(2)).toHaveText("Có");
  });
});

test("trưởng phòng không tải được nhật ký sự kiện (#306)", async ({ browser }) => {
  const nc = await browser.newContext({ storageState: tepPhien("truong-phong") });
  const tra = await nc.request.get("/api/xuat/nhat-ky?dinh-dang=csv");
  expect(tra.status()).toBe(403);
  await nc.close();
});

test("trưởng phòng ủy quyền cho người xử lý: dải báo hiện ngay, thu hồi là mất (#252)", async ({ browser }) => {
  const tp = await browser.newContext({ storageState: tepPhien("truong-phong") });
  const xl = await browser.newContext({ storageState: tepPhien("xu-ly") });
  const trangTp = await tp.newPage();
  const trangXl = await xl.newPage();

  await moMan(trangTp, "/uy-quyen", "truong-phong-uy-quyen");
  const chon = trangTp.locator('select[name="delegate"]');
  const ma = await chon.locator("option", { hasText: "Cường" }).getAttribute("value");
  await chon.selectOption(ma!);
  await trangTp.getByRole("button", { name: "Khai ủy quyền" }).click();
  await expect(trangTp.getByRole("status")).toContainText("Đã khai ủy quyền");
  const dong = trangTp.locator('[data-ds-uy-quyen] tr[data-uy-quyen="active"]', { hasText: "Cường" }).first();
  await expect(dong).toBeVisible();

  // Người làm thay thấy ngay, không phải xác nhận
  await trangXl.goto("/", { waitUntil: "networkidle" });
  await expect(trangXl.locator("[data-dai-uy-quyen]").first()).toContainText("Bạn đang làm thay");

  await dong.getByRole("button", { name: /^Thu hồi/ }).click();
  // Chờ đúng dòng vừa khai rời trạng thái hiệu lực — dòng "Đã thu hồi" của lượt chạy trước có sẵn rồi
  await expect(
    trangTp.locator('[data-ds-uy-quyen] tr[data-uy-quyen="active"]', { hasText: "Cường" }),
  ).toHaveCount(0);

  // Thu hồi là mất ngay ở lần tải kế tiếp
  await trangXl.goto("/", { waitUntil: "networkidle" });
  await expect(trangXl.locator("[data-dai-uy-quyen]")).toHaveCount(0);
  await tp.close();
  await xl.close();
});
