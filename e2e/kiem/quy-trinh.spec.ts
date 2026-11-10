// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn Quy trình thực tế (#315), qua đăng nhập thật như mọi kịch bản khác: ai thấy gì, khoảng ngày
// nằm trên địa chỉ, sơ đồ hiện, bấm một điều thì danh sách hồ sơ mở và mã hồ sơ dẫn tới trang hồ sơ,
// màn hẹp có nút xem toàn màn hình. Không bài nào phụ thuộc số tuyệt đối — chỉ dựa vào hình dạng
// của kết quả — vì cụm thử có thể có ít hay nhiều hồ sơ tùy lúc chạy.
//
// Bài cần nhánh lệch (trả về làm lại, leo thang…) bỏ qua có lý do khi khoảng đang xem không có hồ
// sơ nào đi nhánh đó; nạp dữ liệu trình diễn (scripts/nap_du_lieu_trinh_dien.py) rồi chạy lại thì chạy.

import { type Page, expect, test } from "@playwright/test";

import { type Vai, chup, tepPhien, theoDoiCsp, viPhamCsp } from "./chung";

const DUONG_DAN = "/bao-cao/quy-trinh";

function theoVai(vai: Vai) {
  test.use({ storageState: tepPhien(vai) });
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

/** Mở màn, gom lỗi phía trình duyệt, đợi kết quả về (không còn mờ vì đang tải), kiểm không cuộn ngang. */
async function moMan(page: Page, duong = DUONG_DAN) {
  const loi: string[] = [];
  page.on("pageerror", (e) => loi.push(e.message));
  await theoDoiCsp(page);
  const tl = await page.goto(duong, { waitUntil: "networkidle" });
  expect(tl?.status(), `mở ${duong}`).toBeLessThan(400);
  await expect(page.locator(".qt-ket-qua:not([data-dang-tai]), .rong")).toBeVisible({ timeout: 30_000 });
  expect(loi, `lỗi phía trình duyệt ở ${duong}`).toEqual([]);
  expect(await viPhamCsp(page), `vi phạm chính sách nội dung ở ${duong}`).toEqual([]);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1),
    `thanh cuộn ngang ở ${duong}`,
  ).toBe(false);
}

/** Số ngày giữa hai ngày `YYYY-MM-DD`. */
function soNgayGiua(tu: string, den: string): number {
  return Math.round((Date.parse(`${den}T00:00:00Z`) - Date.parse(`${tu}T00:00:00Z`)) / 86_400_000);
}

test.describe("điều phối viên", () => {
  theoVai("dieu-phoi");

  test("thấy phạm vi toàn công ty, thanh chuyển và mục Báo cáo đều sáng đúng", async ({ page }) => {
    await moMan(page);
    await expect(page.locator(".bao-cao-pham-vi")).toHaveText("Phạm vi số liệu: toàn công ty");
    // Thanh chuyển hai mục: mục đang mở mang aria-current
    const thanh = page.getByRole("navigation", { name: "Các mục báo cáo" });
    await expect(thanh.getByRole("link", { name: "Quy trình thực tế" })).toHaveAttribute("aria-current", "page");
    await expect(thanh.getByRole("link", { name: "Bảng điều khiển" })).not.toHaveAttribute("aria-current", "page");
    // Thanh bên chỉ có một mục Báo cáo, sáng ở cả hai trang
    const sb = await thanhBen(page);
    await expect(sb.getByRole("link", { name: "Báo cáo" })).toHaveCount(1);
    await expect(sb.getByRole("link", { name: "Báo cáo" })).toHaveAttribute("aria-current", "page");
    // Mở màn khai phá thì không tải khung Superset
    await expect(page.locator(".bao-cao-khung")).toHaveCount(0);
    await expect(page.locator("iframe")).toHaveCount(0);
    await chup(page, test.info().project.name, "dieu-phoi-quy-trinh");
  });

  test("từ trang Bảng điều khiển bấm sang Quy trình thực tế, rồi quay lại", async ({ page }) => {
    await page.goto("/bao-cao", { waitUntil: "networkidle" });
    const thanh = page.getByRole("navigation", { name: "Các mục báo cáo" });
    await expect(thanh.getByRole("link", { name: "Bảng điều khiển" })).toHaveAttribute("aria-current", "page");
    await thanh.getByRole("link", { name: "Quy trình thực tế" }).click();
    await page.waitForURL(/\/bao-cao\/quy-trinh/);
    await expect(page.locator(".qt-ket-qua:not([data-dang-tai]), .rong")).toBeVisible({ timeout: 30_000 });
    await page.getByRole("navigation", { name: "Các mục báo cáo" }).getByRole("link", { name: "Bảng điều khiển" }).click();
    await page.waitForURL(/\/bao-cao$/);
  });

  test("đổi nút nhanh thì khoảng ngày trên địa chỉ đổi theo, tải lại vẫn giữ", async ({ page }) => {
    await moMan(page);
    await page.getByRole("button", { name: "30 ngày" }).click();
    await expect(page.getByRole("button", { name: "30 ngày" })).toHaveAttribute("aria-pressed", "true");
    await expect(page).toHaveURL(/[?&]tu=\d{4}-\d{2}-\d{2}&den=\d{4}-\d{2}-\d{2}/);
    const tham = new URL(page.url()).searchParams;
    // 30 ngày tính cả hôm nay: hai đầu cách nhau 29 ngày
    expect(soNgayGiua(tham.get("tu")!, tham.get("den")!)).toBe(29);
    await expect(page.locator('input[type="date"]').first()).toHaveValue(tham.get("tu")!);

    await page.reload({ waitUntil: "networkidle" });
    await expect(page.getByRole("button", { name: "30 ngày" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator('input[type="date"]').nth(1)).toHaveValue(tham.get("den")!);

    // 12 tháng là 365 ngày tính cả hôm nay — khoảng dài nhất mà dịch vụ nhận
    await page.getByRole("button", { name: "12 tháng" }).click();
    await expect(page).toHaveURL(/den=/);
    const nam = new URL(page.url()).searchParams;
    expect(soNgayGiua(nam.get("tu")!, nam.get("den")!)).toBe(364);
    await expect(page.locator(".qt-loi-ngay")).toHaveCount(0);
  });

  test("khoảng ngày sai thì lời báo hiện ngay dưới ô ngày", async ({ page }) => {
    await moMan(page);
    // Ngày bắt đầu sau ngày kết thúc: dịch vụ báo 422 kèm thông điệp
    await page.locator('input[type="date"]').first().fill("2099-12-31");
    const loi = page.locator(".qt-loi-ngay");
    await expect(loi).toBeVisible({ timeout: 15_000 });
    await expect(loi).toContainText("Khoảng ngày");
    await expect(loi).toHaveAttribute("role", "alert");
    // Không còn sơ đồ của khoảng cũ gây hiểu nhầm
    await expect(page.locator(".sdq-khung")).toHaveCount(0);
    // Chọn lại khoảng đúng thì lời báo mất
    await page.getByRole("button", { name: "90 ngày" }).click();
    await expect(loi).toHaveCount(0);
    await expect(page.locator(".sdq-khung").first()).toBeVisible({ timeout: 30_000 });
  });

  test("sơ đồ hiện, có nút trạng thái; bấm một trạng thái thì ngăn hồ sơ chờ lâu nhất mở", async ({ page }) => {
    await moMan(page);
    const nut = page.locator(".sdq-nut[aria-pressed]");
    await expect(page.locator(".sdq-nut").first()).toBeVisible({ timeout: 30_000 });
    expect(await nut.count(), "có ít nhất một trạng thái bấm được").toBeGreaterThan(0);
    // Mỗi nút trạng thái có nhãn đọc màn hình nói đủ: tên, số lượt
    await expect(nut.first()).toHaveAttribute("aria-label", /lượt vào/);

    await nut.first().click();
    const ngan = page.locator("aside.ngan");
    await expect(ngan).toBeVisible();
    await expect(ngan.getByRole("heading", { level: 2 })).toContainText("Hồ sơ chờ lâu nhất ở");
    await expect(ngan.getByRole("heading", { level: 2 })).toBeFocused();
    await expect(nut.first()).toHaveAttribute("aria-pressed", "true");
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)).toBe(false);
    await chup(page, test.info().project.name, "dieu-phoi-quy-trinh-ngan-trang-thai");

    // Esc đóng ngăn và trả tiêu điểm về nút đã bấm
    await page.keyboard.press("Escape");
    await expect(ngan).toHaveCount(0);
    await expect(nut.first()).toBeFocused();
  });

  test("bấm một nhánh lệch có hồ sơ: danh sách mở, mã hồ sơ đầu tiên dẫn tới trang hồ sơ", async ({ page }) => {
    await moMan(page);
    const nhanh = page.locator("section[aria-labelledby='qt-h-lech'] button.qt-dong");
    test.skip(
      (await nhanh.count()) === 0,
      "khoảng đang xem không có hồ sơ nào đi nhánh lệch — nạp dữ liệu trình diễn rồi chạy lại",
    );

    await nhanh.first().click();
    const ngan = page.locator("aside.ngan");
    await expect(ngan).toBeVisible();
    await expect(ngan.getByRole("heading", { level: 2 })).toContainText("Nhánh lệch");
    // Đầu danh sách có số tách theo loại yêu cầu
    await expect(ngan.getByRole("heading", { level: 3, name: "Theo loại yêu cầu" })).toBeVisible();
    const ma = ngan.locator("a.qt-ma").first();
    await expect(ma).toBeVisible();
    await ma.click();
    // Điều phối viên mở hồ sơ ở buồng lái điều phối
    await page.waitForURL(/\/dieu-phoi\/\d+/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("bấm một đường đi phổ biến: tô sáng trên sơ đồ, bấm lại thì trở về", async ({ page }) => {
    await moMan(page);
    const duong = page.locator("section[aria-labelledby='qt-h-bien-the'] button.qt-dong");
    test.skip((await duong.count()) === 0, "khoảng đang xem chưa có đường đi nào");

    await duong.first().click();
    await expect(duong.first()).toHaveAttribute("aria-pressed", "true");
    const ngan = page.locator("aside.ngan");
    await expect(ngan).toBeVisible();
    await expect(ngan.getByRole("heading", { level: 2 })).toContainText("Hồ sơ đi theo đường này");
    if ((page.viewportSize()?.width ?? 0) >= 768) {
      // Màn rộng: trang chừa chỗ cho ngăn, không khối nào nằm dưới ngăn
      await expect
        .poll(async () => {
          const khoi = await page.locator("section[aria-labelledby='qt-h-bien-the']").boundingBox();
          const nganBox = await ngan.boundingBox();
          return khoi!.x + khoi!.width <= nganBox!.x + 1;
        })
        .toBe(true);
    }

    // Đóng ngăn thì danh sách mất nhưng đường vừa chọn vẫn sáng trên sơ đồ, cho tới khi bỏ chọn
    await page.keyboard.press("Escape");
    await expect(ngan).toHaveCount(0);
    await expect(duong.first()).toHaveAttribute("aria-pressed", "true");
    // Bấm lại đường đang chọn lúc ngăn đã đóng thì mở lại ngăn
    await duong.first().click();
    await expect(ngan).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(ngan).toHaveCount(0);

    await page.getByRole("button", { name: "Bỏ chọn" }).click();
    await expect(duong.first()).toHaveAttribute("aria-pressed", "false");
    await expect(page.getByRole("button", { name: "Bỏ chọn" })).toHaveCount(0);
  });

  test("hệ thống không phản hồi: màn báo đúng câu chữ, có nút thử lại", async ({ page }) => {
    // Dịch vụ khai phá tắt: Route Handler trả 503. Giả lập ở đây để bài không đụng tới cụm.
    await page.route("**/api/bao-cao/quy-trinh*", (r) =>
      r.fulfill({ status: 503, contentType: "application/json", body: '{"ma":"mining-unavailable","thongDiep":"x"}' }),
    );
    await page.goto(DUONG_DAN, { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: "Hệ thống không phản hồi" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Thử lại" })).toBeVisible();
    // Phần còn lại của cổng vẫn dùng được
    await expect(page.getByRole("navigation", { name: "Các mục báo cáo" })).toBeVisible();
    await page.unroute("**/api/bao-cao/quy-trinh*");
    await page.getByRole("button", { name: "Thử lại" }).click();
    await expect(page.locator(".qt-ket-qua:not([data-dang-tai]), .rong").first()).toBeVisible({ timeout: 30_000 });
  });

  test("chân màn có dòng mã nguồn AGPL dẫn đúng địa chỉ cấu hình, cả khi màn rỗng", async ({ page }) => {
    // Điều 13 của AGPL (#340). Địa chỉ cấu hình ở MINING_SOURCE_URL của cổng; chạy bài với cụm đặt
    // giá trị khác thì truyền cùng biến cho Playwright.
    const diaChi =
      process.env.MINING_SOURCE_URL ?? "https://github.com/AlaVox-lab/dx-os-lab/tree/main/services/khai-pha";
    const kiemDong = async () => {
      const dong = page.locator(".qt-nguon-ma");
      await expect(dong).toHaveCount(1);
      await expect(dong).toContainText("Phân tích bởi dịch vụ khai phá quy trình, giấy phép AGPL-3.0");
      const lienKet = dong.getByRole("link", { name: "mã nguồn" });
      await expect(lienKet).toHaveAttribute("href", diaChi);
      await expect(lienKet).toHaveAttribute("rel", /noopener/);
      // Màn không nêu tên bộ máy khai phá
      await expect(dong).not.toContainText(/pm4py|noi_bo/i);
    };
    await moMan(page);
    await kiemDong();
    // Khoảng không có hồ sơ nào: màn rỗng vẫn giữ dòng này
    await moMan(page, `${DUONG_DAN}?tu=2001-01-01&den=2001-01-31`);
    await expect(page.getByText("Không có hồ sơ nào gửi trong khoảng này")).toBeVisible();
    await kiemDong();
  });

  test("màn hẹp: nút Xem toàn màn hình mở lớp phủ, Esc đóng và trả tiêu điểm", async ({ page }) => {
    test.skip((page.viewportSize()?.width ?? 1440) >= 768, "nút này chỉ có ở màn hẹp (dưới 768 px)");
    await moMan(page);
    const nut = page.getByRole("button", { name: "Xem toàn màn hình" });
    await expect(nut).toBeVisible();
    // Màn hẹp: kết luận, rồi các khối xếp hạng, sơ đồ nằm cuối
    const yKetLuan = (await page.locator(".qt-ket-luan").boundingBox())!.y;
    const yNghen = (await page.locator("section[aria-labelledby='qt-h-nghen']").boundingBox())!.y;
    const ySoDo = (await page.locator(".qt-so-do").boundingBox())!.y;
    expect(yKetLuan).toBeLessThan(yNghen);
    expect(yNghen).toBeLessThan(ySoDo);
    await chup(page, test.info().project.name, "dieu-phoi-quy-trinh-hep");

    await nut.click();
    const lop = page.getByRole("dialog", { name: /toàn màn hình/ });
    await expect(lop).toBeVisible();
    await expect(lop.getByRole("button", { name: "Đóng", exact: true })).toBeFocused();
    await expect(lop.locator(".sdq-nut").first()).toBeVisible();
    await chup(page, test.info().project.name, "dieu-phoi-quy-trinh-toan-man-hinh");
    await page.keyboard.press("Escape");
    await expect(lop).toHaveCount(0);
    await expect(nut).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)).toBe(false);
  });

  test("màn rộng: không có nút Xem toàn màn hình", async ({ page }) => {
    test.skip((page.viewportSize()?.width ?? 0) < 768, "bài này dành cho màn rộng");
    await moMan(page);
    await expect(page.getByRole("button", { name: "Xem toàn màn hình" })).toBeHidden();
  });
});

test.describe("trưởng phòng", () => {
  theoVai("truong-phong");

  test("chỉ thấy phòng của mình ở dòng phạm vi", async ({ page }) => {
    await moMan(page);
    await expect(page.locator(".bao-cao-pham-vi")).toHaveText("Phạm vi số liệu: Công nghệ thông tin");
    // Phạm vi một phòng: câu kết luận nói đúng phòng đó, không nói "toàn công ty"
    await expect(page.locator(".qt-ket-luan")).not.toContainText("toàn công ty");
  });
});

test.describe("người gửi", () => {
  theoVai("nguoi-gui");

  test("không thấy mục Báo cáo, mở thẳng thì bị từ chối, điểm cuối cũng từ chối", async ({ page }) => {
    await page.goto("/");
    await expect((await thanhBen(page)).getByRole("link", { name: "Báo cáo" })).toHaveCount(0);
    await page.goto(DUONG_DAN);
    await expect(page.getByText("Tài khoản này không mở được khu vực này")).toBeVisible();
    await expect(page.locator(".qt-ket-qua, .sdq-khung")).toHaveCount(0);
    const tra = await page.request.get("/api/bao-cao/quy-trinh?tu=2026-01-01&den=2026-01-31");
    expect(tra.status()).toBe(403);
  });
});

test("chưa đăng nhập: điểm cuối quy trình trả 401", async ({ browser }) => {
  const nc = await browser.newContext();
  const tra = await nc.request.get("/api/bao-cao/quy-trinh?tu=2026-01-01&den=2026-01-31");
  expect(tra.status()).toBe(401);
  expect(tra.headers()["cache-control"]).toBe("no-store");
  await nc.close();
});
