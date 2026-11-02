// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Các màn chính theo từng vai, chạy ở bốn cấu hình hiển thị (playwright.config.ts). Mỗi màn: mở
// được, không lỗi phía trình duyệt, không cuộn ngang, chụp ảnh. Thêm vài điều kiện nghiệp vụ mà lỗi
// giao diện hay làm sai: số liệu trang chủ khớp danh sách, mục Hệ thống chỉ quản trị viên thấy, nút
// trên dòng việc mở đúng bước.

import { readFileSync } from "node:fs";

import { type Page, expect, test } from "@playwright/test";

import { type Vai, chup, docHoSo, tepPhien } from "./chung";

/** Mở một màn, gom lỗi phía trình duyệt, kiểm không cuộn ngang, chụp ảnh. */
async function moMan(page: Page, duong: string, anh: string) {
  const loi: string[] = [];
  page.on("pageerror", (e) => loi.push(e.message));
  const tl = await page.goto(duong, { waitUntil: "networkidle" });
  expect(tl?.status(), `mở ${duong}`).toBeLessThan(400);
  expect(loi, `lỗi phía trình duyệt ở ${duong}`).toEqual([]);
  const cuonNgang = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  expect(cuonNgang, `thanh cuộn ngang ở ${duong}`).toBe(false);
  await chup(page, test.info().project.name, anh);
}

function theoVai(vai: Vai) {
  test.use({ storageState: tepPhien(vai) });
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
    await expect(page.getByText(h.tieuDe)).toBeVisible();
    await moMan(page, `/yeu-cau/${h.ma}`, "nguoi-gui-ho-so");
    await moMan(page, "/hop-thu", "nguoi-gui-hop-thu");
  });

  test("không thấy mục Hệ thống, mở thẳng thì bị từ chối", async ({ page }) => {
    await page.goto("/");
    await expect((await thanhBen(page)).getByRole("link", { name: "Hệ thống" })).toHaveCount(0);
    await page.goto("/he-thong");
    await expect(page.getByText("Tài khoản này không mở được khu vực này")).toBeVisible();
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
});

test.describe("quản trị viên", () => {
  theoVai("quan-tri");

  test("màn Hệ thống báo bộ quy tắc đã nạp", async ({ page }) => {
    await moMan(page, "/", "quan-tri-trang-chu");
    await expect((await thanhBen(page)).getByRole("link", { name: "Hệ thống" })).toBeVisible();
    await moMan(page, "/he-thong", "quan-tri-he-thong");
    await expect(page.getByText("Bộ quy tắc quy trình")).toBeVisible();
    await expect(page.getByText(/đã nạp/)).toBeVisible();
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
      "case_id,activity,timestamp,actor,from_state,to_state,request_type_code,department_code,priority_code,rule_set_id",
    );
  });
});

test("trưởng phòng không tải được nhật ký sự kiện (#306)", async ({ browser }) => {
  const nc = await browser.newContext({ storageState: tepPhien("truong-phong") });
  const tra = await nc.request.get("/api/xuat/nhat-ky?dinh-dang=csv");
  expect(tra.status()).toBe(403);
  await nc.close();
});
