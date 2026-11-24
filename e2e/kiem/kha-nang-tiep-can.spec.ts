// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khả năng tiếp cận theo WCAG 2.1 A + AA (#435), quét bằng axe-core trên các màn chính — mỗi vai một màn
// nó dùng hằng ngày — qua ĐĂNG NHẬP THẬT như mọi kịch bản khác. Chạy ở cả bốn cấu hình hiển thị, nên
// tương phản được kiểm ở cả chế độ sáng lẫn tối và màn hẹp.
//
// Bài đỏ khi còn vi phạm mức `critical` hoặc `serious`. Vi phạm `moderate`/`minor` không làm đỏ bài nhưng
// được ghi lại: mỗi màn một dòng ở ket-qua/kha-nang-tiep-can/<cấu hình>.jsonl để đếm.
//
// Phạm vi loại trừ — chỉ phần không phải mã của nhóm, mỗi chỗ có lý do ngay tại chỗ:
//   - khung Superset nhúng ở màn Báo cáo: tài liệu của Superset (bên thứ ba), dựng trong iframe riêng
//
// Thêm cũng ở đây: một bài đi bằng bàn phím trên hai màn hay dùng nhất — Gửi yêu cầu và trang hồ sơ
// của điều phối viên — Tab đi đúng thứ tự, thấy viền tiêu điểm, gửi được biểu mẫu chỉ bằng bàn phím.

import fs from "node:fs";
import path from "node:path";

import AxeBuilder from "@axe-core/playwright";
import { type Browser, type Locator, type Page, expect, test } from "@playwright/test";

import { type Vai, docHoSo, guiYeuCauThu, tepPhien } from "./chung";

const THE_WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];
const MUC_NANG = new Set(["critical", "serious"]);
const THU_MUC_KQ = path.join(import.meta.dirname, "..", "ket-qua", "kha-nang-tiep-can");

type ViPham = {
  id: string;
  impact: string | null | undefined;
  nodes: { target: unknown[]; any: { message: string }[] }[];
};

function tomTat(cac: ViPham[]): string {
  return cac
    .map((v) => {
      const dau = v.nodes[0];
      return `${v.id} (${v.impact}) × ${v.nodes.length}: ${dau?.target.join(" ") ?? "?"} — ${dau?.any[0]?.message ?? ""}`;
    })
    .join("\n");
}

/** Quét trang đang mở; ghi mọi vi phạm theo mức, đỏ khi còn mức nặng. `loaiTru`: bộ chọn bỏ khỏi phạm vi. */
async function quet(page: Page, man: string, loaiTru: string[] = []) {
  // Đo khi mọi hiệu ứng hiện ra đã xong: giữa chừng, chữ còn mờ dần nên tương phản đo được thấp giả
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running"));
  let axe = new AxeBuilder({ page }).withTags(THE_WCAG);
  for (const chon of loaiTru) axe = axe.exclude(chon);
  const kq = await axe.analyze();
  const cauHinh = test.info().project.name;
  fs.mkdirSync(THU_MUC_KQ, { recursive: true });
  const dem: Record<string, number> = {};
  for (const v of kq.violations) dem[v.impact ?? "khac"] = (dem[v.impact ?? "khac"] ?? 0) + v.nodes.length;
  fs.appendFileSync(
    path.join(THU_MUC_KQ, `${cauHinh}.jsonl`),
    JSON.stringify({ man, dem, luat: kq.violations.map((v) => ({ id: v.id, impact: v.impact, nut: v.nodes.length })) }) + "\n",
  );
  const nang = kq.violations.filter((v) => MUC_NANG.has(v.impact ?? ""));
  expect.soft(nang.length, `vi phạm mức nặng ở ${man}:\n${tomTat(nang)}`).toBe(0);
}

/** Mở một màn rồi quét. Màn nạp phần còn lại bằng JavaScript sau khi hiện, nên chờ mạng yên. */
async function moVaQuet(page: Page, duong: string, man: string, loaiTru: string[] = []) {
  const tl = await page.goto(duong, { waitUntil: "networkidle" });
  expect(tl?.status(), `mở ${duong}`).toBeLessThan(400);
  await quet(page, man, loaiTru);
}

function theoVai(vai: Vai) {
  test.use({ storageState: tepPhien(vai) });
}

/**
 * Một hồ sơ thuộc phòng Công nghệ thông tin (phòng của trưởng phòng mẫu), dựng bằng giao diện như người
 * thật: người gửi gửi, điều phối viên phân loại và chuyển phòng. Cụm dựng sạch chưa có hồ sơ nào ở phòng.
 */
async function hoSoCuaPhong(browser: Browser): Promise<number> {
  const ng = await browser.newContext({ storageState: tepPhien("nguoi-gui") });
  const ma = await guiYeuCauThu(await ng.newPage(), `Khả năng tiếp cận ${new Date().toISOString().slice(0, 19)}`);
  await ng.close();

  const dp = await browser.newContext({ storageState: tepPhien("dieu-phoi") });
  const page = await dp.newPage();
  await page.goto(`/dieu-phoi/${ma}`, { waitUntil: "networkidle" });
  const thaoTac = page.locator("#thao-tac");
  await thaoTac.getByRole("button", { name: "Phân loại yêu cầu", exact: true }).click();
  await thaoTac.getByRole("button", { name: /^Xác nhận · Phân loại yêu cầu/ }).click();
  await thaoTac.getByRole("button", { name: "Chuyển về phòng ban", exact: true }).click();
  const oPhong = thaoTac.locator('select[name="truong:department_code"]');
  const maPhong = await oPhong
    .locator("option")
    .evaluateAll((os) => (os as HTMLOptionElement[]).find((o) => o.text.startsWith("Công nghệ thông tin"))?.value);
  expect(maPhong, "danh mục có phòng Công nghệ thông tin").toBeTruthy();
  await oPhong.selectOption(maPhong!);
  await thaoTac.getByRole("button", { name: /^Xác nhận · Chuyển về phòng ban/ }).click();
  await expect(thaoTac.getByRole("button", { name: "Chuyển về phòng ban", exact: true })).toHaveCount(0);
  await dp.close();
  return ma;
}

test.describe("chưa đăng nhập", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("trang chủ khi chưa đăng nhập và trang đăng nhập", async ({ page }) => {
    await moVaQuet(page, "/", "trang-chu-chua-dang-nhap");
    // Trang đăng nhập của Keycloak mang chủ đề của dự án (infra/keycloak/themes/dx-os-lab)
    await page.getByRole("link", { name: "Đăng nhập bằng tài khoản công ty" }).click();
    await expect(page.locator("#username")).toBeVisible();
    await page.waitForLoadState("networkidle");
    await quet(page, "dang-nhap-keycloak");
  });
});

test.describe("người gửi", () => {
  theoVai("nguoi-gui");

  test("trang chủ, Gửi yêu cầu, hồ sơ của tôi, một hồ sơ, Mã nguồn và giấy phép", async ({ page }) => {
    const h = docHoSo();
    await moVaQuet(page, "/", "nguoi-gui-trang-chu");
    await moVaQuet(page, "/ma-nguon", "nguoi-gui-ma-nguon");
    await moVaQuet(page, "/yeu-cau/moi", "nguoi-gui-gui-yeu-cau-buoc-1");
    // Bước 2 có ô nhập, trường riêng của loại và ô tải tệp
    await page.getByText("Sự cố thiết bị").first().click();
    await expect(page.locator('input[name="title"]')).toBeVisible();
    await quet(page, "nguoi-gui-gui-yeu-cau-buoc-2");
    await moVaQuet(page, "/yeu-cau", "nguoi-gui-ho-so-cua-toi");
    await moVaQuet(page, `/yeu-cau/${h.ma}`, "nguoi-gui-ho-so");
  });
});

test.describe("điều phối viên", () => {
  theoVai("dieu-phoi");

  test("trang chủ, hàng đợi, một hồ sơ kèm bảng thao tác đang mở", async ({ page }) => {
    const h = docHoSo();
    await moVaQuet(page, "/", "dieu-phoi-trang-chu");
    await moVaQuet(page, "/dieu-phoi", "dieu-phoi-hang-doi");
    // Ngăn xem nhanh mở cạnh bảng đã co lại (#539)
    await moVaQuet(page, `/dieu-phoi?xem=${h.ma}`, "dieu-phoi-hang-doi-xem-nhanh");
    await moVaQuet(page, `/dieu-phoi/${h.ma}`, "dieu-phoi-ho-so");
    // Bảng thao tác mở ra có ô chọn, ô ghi chú, thẻ gợi ý
    await page.locator("#thao-tac").getByRole("button", { name: "Phân loại yêu cầu", exact: true }).click();
    await expect(page.locator("#thao-tac").getByRole("button", { name: /^Xác nhận · Phân loại yêu cầu/ })).toBeVisible();
    await quet(page, "dieu-phoi-ho-so-bang-thao-tac");
  });

  test("hàng đợi có hồ sơ được chọn: thanh thao tác và hộp thoại hàng loạt (#440)", async ({ page }) => {
    // Hai lớp này chỉ hiện khi đã chọn hồ sơ, nên màn hàng đợi quét ở trên không chạm tới
    await page.goto("/dieu-phoi", { waitUntil: "networkidle" });
    await page.locator("input[data-chon-ho-so]").first().check();
    const thanh = page.getByRole("region", { name: "Thao tác với hồ sơ đã chọn" });
    await expect(thanh).toBeVisible();
    await quet(page, "dieu-phoi-hang-loat-thanh");
    await thanh.locator("button[data-buoc-hang-loat]").first().click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await quet(page, "dieu-phoi-hang-loat-hop-thoai");
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
  });

  test("Báo cáo: bảng điều khiển và Quy trình thực tế", async ({ page }) => {
    // Khung Superset là tài liệu của bên thứ ba dựng trong iframe riêng — không phải mã của nhóm, nằm ngoài
    // phạm vi sửa (không sửa mã thư viện). Phần của cổng quanh khung vẫn được quét
    await moVaQuet(page, "/bao-cao", "bao-cao-bang-dieu-khien", [".bao-cao-khung iframe"]);
    await moVaQuet(page, "/bao-cao/quy-trinh", "bao-cao-quy-trinh-thuc-te");
  });
});

test.describe("trưởng phòng", () => {
  theoVai("truong-phong");

  test("buồng lái phòng ban, bảng Kanban, một hồ sơ của phòng, hộp thư", async ({ browser, page }) => {
    const ma = await hoSoCuaPhong(browser);
    await moVaQuet(page, "/", "truong-phong-trang-chu");
    await moVaQuet(page, "/phong-ban", "truong-phong-hang-doi");
    await moVaQuet(page, "/phong-ban/bang", "truong-phong-kanban");
    await moVaQuet(page, `/phong-ban/${ma}`, "truong-phong-ho-so");
    await moVaQuet(page, "/hop-thu", "truong-phong-hop-thu");
  });
});

test.describe("người xử lý", () => {
  theoVai("xu-ly");

  test("buồng lái phòng ban và hộp thư", async ({ page }) => {
    await moVaQuet(page, "/phong-ban", "xu-ly-hang-doi");
    await moVaQuet(page, "/hop-thu", "xu-ly-hop-thu");
  });
});

test.describe("quản trị viên", () => {
  theoVai("quan-tri");

  test("màn Hệ thống và màn Cấu hình quy trình", async ({ page }) => {
    await moVaQuet(page, "/he-thong", "quan-tri-he-thong");
    await moVaQuet(page, "/quan-tri/cau-hinh", "quan-tri-cau-hinh");
  });
});

// ---------------------------------------------------------------------------
// Đi bằng bàn phím
// ---------------------------------------------------------------------------

/**
 * Bấm Tab cho tới khi tiêu điểm nằm trên `dich`. Mỗi bước kiểm: tiêu điểm đi TỚI trong thứ tự tài liệu (không
 * `tabindex` dương nào kéo nó nhảy lùi), và phần tử đang giữ tiêu điểm có viền nhìn thấy được.
 */
async function tabToi(page: Page, dich: Locator, toiDa = 120) {
  await page.evaluate(() => {
    (window as unknown as { __truoc?: Element | null }).__truoc = document.activeElement;
  });
  for (let i = 0; i < toiDa; i++) {
    await page.keyboard.press("Tab");
    const buoc = await page.evaluate(() => {
      const w = window as unknown as { __truoc?: Element | null };
      const dang = document.activeElement as HTMLElement | null;
      const truoc = w.__truoc;
      w.__truoc = dang;
      if (!dang || dang === document.body) return { toi: true, vien: true, mo: "body" };
      const toi =
        !truoc || truoc === document.body || truoc.contains(dang) ||
        !!(truoc.compareDocumentPosition(dang) & Node.DOCUMENT_POSITION_FOLLOWING);
      const cs = getComputedStyle(dang);
      const vien =
        (cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0) || cs.boxShadow !== "none";
      const mo = `${dang.tagName.toLowerCase()}${dang.id ? `#${dang.id}` : ""} "${(dang.textContent ?? "").trim().slice(0, 40)}"`;
      return { toi, vien, mo };
    });
    expect(buoc.toi, `Tab nhảy ngược thứ tự tài liệu ở ${buoc.mo}`).toBe(true);
    expect(buoc.vien, `không thấy viền tiêu điểm ở ${buoc.mo}`).toBe(true);
    if (await dich.evaluate((el) => el === document.activeElement)) return;
  }
  throw new Error(`Bấm Tab ${toiDa} lần chưa tới phần tử cần`);
}

/** Tab đầu tiên của trang là lối bỏ qua; Enter đưa tiêu điểm vào nội dung chính. */
async function boQuaToiNoiDung(page: Page) {
  await page.locator("body").focus();
  await page.keyboard.press("Tab");
  const boQua = page.getByRole("link", { name: "Bỏ qua tới nội dung chính" });
  await expect(boQua).toBeFocused();
  await expect(boQua).toBeInViewport();
  await page.keyboard.press("Enter");
  await expect(page.locator("#noi-dung-chinh")).toBeFocused();
}

test.describe("bàn phím: Gửi yêu cầu", () => {
  theoVai("nguoi-gui");

  test("chọn loại, điền, gửi biểu mẫu chỉ bằng bàn phím", async ({ page }) => {
    await page.goto("/yeu-cau/moi", { waitUntil: "networkidle" });
    await boQuaToiNoiDung(page);
    await tabToi(page, page.getByRole("button", { name: /Sự cố thiết bị/ }).first());
    await page.keyboard.press("Enter");

    const tieuDe = `Bàn phím ${test.info().project.name} ${new Date().toISOString().slice(0, 19)}`;
    await tabToi(page, page.locator('input[name="title"]'));
    await page.keyboard.type(tieuDe);
    await tabToi(page, page.locator('textarea[name="description"]'));
    await page.keyboard.type("Gửi bằng bàn phím, không dùng chuột.");
    await tabToi(page, page.locator("#truong-rieng-ma-tai-san"));
    await page.keyboard.type("KT-0435");
    await tabToi(page, page.locator("#truong-rieng-vi-tri"));
    await page.keyboard.type("Phòng thử nghiệm");
    await tabToi(page, page.getByRole("button", { name: "Tiếp tục" }));
    await page.keyboard.press("Enter");
    // Sang bước xác nhận: tiêu điểm có thể về đầu bước, Tab tới nút gửi
    await tabToi(page, page.getByRole("button", { name: "Gửi yêu cầu" }));
    await page.keyboard.press("Enter");
    await page.waitForURL(/\/yeu-cau\/\d+/);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(tieuDe);
  });
});

test.describe("bàn phím: trang hồ sơ của điều phối viên", () => {
  theoVai("dieu-phoi");

  test("tới bảng thao tác, phân loại hồ sơ chỉ bằng bàn phím", async ({ browser, page }) => {
    const ng = await browser.newContext({ storageState: tepPhien("nguoi-gui") });
    const ma = await guiYeuCauThu(await ng.newPage(), `Bàn phím điều phối ${new Date().toISOString().slice(0, 19)}`);
    await ng.close();

    await page.goto(`/dieu-phoi/${ma}`, { waitUntil: "networkidle" });
    await boQuaToiNoiDung(page);
    const thaoTac = page.locator("#thao-tac");
    await tabToi(page, thaoTac.getByRole("button", { name: "Phân loại yêu cầu", exact: true }));
    await page.keyboard.press("Enter");
    await tabToi(page, thaoTac.getByRole("button", { name: /^Xác nhận · Phân loại yêu cầu/ }));
    await page.keyboard.press("Enter");
    await expect(thaoTac.getByRole("button", { name: "Chuyển về phòng ban", exact: true })).toBeVisible();
  });
});
