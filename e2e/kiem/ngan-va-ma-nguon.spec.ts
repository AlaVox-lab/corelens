// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Ngăn xem nhanh không che bảng (#539) và chỗ cố định dẫn tới mã nguồn (#540), qua đăng nhập thật.
//
// #539: ở 1440 và 1280 px, mở ngăn thì ô "Việc tiếp theo" và ô hồ sơ của dòng đang xem nằm trọn trong
// khung nhìn, bên trái mép ngăn, bảng không tràn khung và trang không cuộn ngang. 390 px: ngăn phủ cả màn
// như trước. Mỗi bài tự đặt cỡ cửa sổ nên chạy giống nhau ở mọi cấu hình hiển thị (sáng, tối, giảm chuyển
// động); cấu hình màn hẹp chỉ chạy cỡ 390.
//
// #540: mọi vai thấy liên kết "Mã nguồn và giấy phép" ở chân thanh bên, kể cả khi thanh bên thu gọn; trang
// đó dẫn tới dịch vụ khai phá đúng địa chỉ cấu hình (MINING_SOURCE_URL) và chỉ có dòng Wiki.js khi kho tri
// thức bật.

import { type Page, expect, test } from "@playwright/test";

import { type Vai, VAI, chup, tepPhien } from "./chung";

const NGUON_KHAI_PHA =
  process.env.MINING_SOURCE_URL ?? "https://github.com/AlaVox-lab/corelens/tree/main/services/khai-pha";

/** Đợi mọi hiệu ứng (ngăn trượt vào, dòng hiện lần lượt) chạy xong rồi mới đo hộp bao. */
async function choHieuUng(page: Page) {
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running"));
}

/** Thanh bên chỉ mở sẵn ở màn rộng; màn hẹp mở bằng nút menu. */
async function thanhBen(page: Page) {
  const nutMenu = page.locator(".nut-menu");
  if (await nutMenu.isVisible()) await nutMenu.click();
  const sb = page.locator(".sb");
  await expect(sb).toBeVisible();
  return sb;
}

type Hop = { left: number; right: number; top: number; bottom: number };

for (const [vai, duong] of [
  ["dieu-phoi", "/dieu-phoi"],
  ["truong-phong", "/phong-ban"],
] as const) {
  test.describe(`ngăn xem nhanh ${duong} (#539)`, () => {
    test.use({ storageState: tepPhien(vai) });

    test("mở ngăn: cột hồ sơ và Việc tiếp theo thấy trọn ở 1440, 1280; 390 ngăn phủ cả màn", async ({ page }) => {
      const hep = test.info().project.name === "hep-sang";
      for (const rong of hep ? [390] : [1440, 1280]) {
        await page.setViewportSize({ width: rong, height: rong < 768 ? 844 : 900 });
        await page.goto(duong, { waitUntil: "networkidle" });
        const dong = page.locator("a.lk-dong");
        expect(await dong.count(), "hàng đợi có hồ sơ").toBeGreaterThan(0);
        await dong.first().click();
        const ngan = page.locator("aside.ngan");
        await expect(ngan).toBeVisible();
        await expect(page.locator("tr.dong[data-dang-xem]")).toHaveCount(1);
        await choHieuUng(page);
        expect(
          await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1),
          `cuộn ngang ở ${rong}px`,
        ).toBe(false);

        const hopNgan = (await ngan.boundingBox())!;
        if (rong < 768) {
          // Như trước #539: ngăn chiếm trọn màn
          expect(Math.round(hopNgan.width)).toBe(rong);
          await chup(page, test.info().project.name, `${vai}-ngan-${rong}`);
          continue;
        }

        const hop = await page.evaluate(() => {
          const r = (e: Element | null | undefined): Hop | null => {
            if (!e) return null;
            const b = e.getBoundingClientRect();
            return { left: b.left, right: b.right, top: b.top, bottom: b.bottom };
          };
          const tr = document.querySelector("tr.dong[data-dang-xem]");
          return {
            tiep: r(tr?.querySelector("td.cot-tiep")),
            hoSo: r(tr?.querySelector(".o-ho-so")?.closest("td")),
            thTiep: r(document.querySelector(".bang thead th.cot-tiep")),
            khung: r(document.querySelector(".khung-bang")),
            bang: r(document.querySelector(".khung-bang .bang")),
          };
        });
        expect(hop.tiep, `ô Việc tiếp theo có mặt ở ${rong}px`).not.toBeNull();
        expect(hop.thTiep, `tiêu đề cột Việc tiếp theo có mặt ở ${rong}px`).not.toBeNull();
        for (const [ten, h] of [
          ["ô Việc tiếp theo", hop.tiep!],
          ["ô hồ sơ", hop.hoSo!],
        ] as const) {
          // Trọn trong khung nhìn và không bị ngăn che (làm tròn phần lẻ điểm ảnh)
          expect(h.left, `${ten} ở ${rong}px: mép trái`).toBeGreaterThanOrEqual(-0.5);
          expect(h.right, `${ten} ở ${rong}px: bên trái ngăn`).toBeLessThanOrEqual(hopNgan.x + 0.5);
          // Không bị khung bảng cắt
          expect(h.right, `${ten} ở ${rong}px: trong khung bảng`).toBeLessThanOrEqual(hop.khung!.right + 0.5);
        }
        expect(hop.bang!.right, `bảng không tràn khung ở ${rong}px`).toBeLessThanOrEqual(hop.khung!.right + 0.5);
        await chup(page, test.info().project.name, `${vai}-ngan-${rong}`);

        // Đóng ngăn: bảng giãn lại, tiêu điểm về dòng như trước
        await page.keyboard.press("Escape");
        await expect(ngan).toHaveCount(0);
        await expect(page.locator(".khung-bang[data-co-ngan]")).toHaveCount(0);
      }
    });
  });
}

test.describe("Mã nguồn và giấy phép (#540)", () => {
  test("mọi vai thấy liên kết ở chân thanh bên", async ({ browser }) => {
    const { baseURL, viewport, colorScheme, locale } = test.info().project.use;
    for (const vai of Object.keys(VAI) as Vai[]) {
      const nc = await browser.newContext({
        baseURL: baseURL ?? process.env.CONG,
        viewport,
        colorScheme,
        locale,
        storageState: tepPhien(vai),
      });
      const page = await nc.newPage();
      await page.goto("/", { waitUntil: "networkidle" });
      const sb = await thanhBen(page);
      await expect(sb.getByRole("link", { name: "Mã nguồn và giấy phép" }), vai).toBeVisible();
      await nc.close();
    }
  });

  test.describe("người gửi", () => {
    test.use({ storageState: tepPhien("nguoi-gui") });

    test("trang liệt kê thành phần, dẫn tới mã nguồn dịch vụ khai phá đúng cấu hình", async ({ page }) => {
      await page.goto("/", { waitUntil: "networkidle" });
      const sb = await thanhBen(page);
      // Kho tri thức bật thì thanh bên có lối vào, và trang có thêm dòng Wiki.js
      const coKhoTriThuc = (await sb.locator('[data-loi-ngoai="tri-thuc"]').count()) > 0;
      await sb.getByRole("link", { name: "Mã nguồn và giấy phép" }).click();
      await expect(page).toHaveURL(/\/ma-nguon$/);
      await expect(page.getByRole("heading", { level: 1, name: "Mã nguồn và giấy phép" })).toBeVisible();

      const khaiPha = page.locator('[data-ma-nguon="Dịch vụ khai phá quy trình"]');
      await expect(khaiPha).toHaveAttribute("href", NGUON_KHAI_PHA);
      await expect(khaiPha).toHaveAttribute("target", "_blank");
      await expect(khaiPha).toHaveAttribute("rel", /noopener/);
      await expect(page.locator('[data-ma-nguon="Corelens"]')).toHaveAttribute("href", /^https?:\/\//);
      await expect(page.locator('[data-ma-nguon="Wiki.js"]')).toHaveCount(coKhoTriThuc ? 1 : 0);
      await expect(page.locator(".ds-ma-nguon")).toContainText("AGPL-3.0-or-later");
      expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)).toBe(false);
      await chup(page, test.info().project.name, "ma-nguon");
    });

    test("thanh bên thu gọn: liên kết vẫn với tới được", async ({ page }) => {
      test.skip(test.info().project.name === "hep-sang", "màn hẹp không có thanh bên thu gọn");
      await page.addInitScript(() => localStorage.setItem("dxlab-sb-thu-gon", "1"));
      await page.goto("/", { waitUntil: "networkidle" });
      await expect(page.locator(".app[data-thu-gon]")).toHaveCount(1);
      // Thu gọn thì nhãn mờ đi (opacity 0) mà vẫn là tên của liên kết — Chromium đọc đủ tên; cách tính tên của
      // Playwright bỏ qua chữ mờ nên ở đây dò theo đường dẫn, rồi kiểm chữ và `title` hiện khi rê chuột
      const lk = page.locator('.sb a[href="/ma-nguon"]');
      await expect(lk).toBeVisible();
      await expect(lk).toHaveText("Mã nguồn và giấy phép");
      await expect(lk).toHaveAttribute("title", "Mã nguồn và giấy phép");
      await lk.click();
      await expect(page).toHaveURL(/\/ma-nguon$/);
    });
  });
});
