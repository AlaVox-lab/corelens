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
    // Đường dẫn đầu trang ghi mã hồ sơ như buồng lái; không còn câu bảo mở lại trang (#557), không còn dòng ghi chú
    // về các nút dưới khung thao tác — chỉ nút làm được mới hiện (#561)
    await expect(page.locator("header.thanh-dau .cha .mono")).toHaveText(/^YC-\d{4}-\d+$/);
    await expect(page.getByText("mở lại trang này", { exact: false })).toHaveCount(0);
    await expect(page.getByText("Chỉ hiện những thao tác", { exact: false })).toHaveCount(0);
    // Dải ba ô số (#561): ô thời gian theo giờ đồng hồ, ô hạn theo giờ làm việc
    await expect(page.locator(".dai-so-ho-so > div")).toHaveCount(3);
    await moMan(page, "/hop-thu", "nguoi-gui-hop-thu");
  });

  test("trang hồ sơ chỉ tô màu chính cho bước chính trong dữ liệu (#559)", async ({ page }) => {
    // Vừa gửi: hồ sơ chờ điều phối viên chứ không chờ người gửi — Sửa nội dung bấm được nhưng không nút nào tô
    await guiYeuCauThu(page, `Nút chính ${test.info().project.name} ${new Date().toISOString().slice(0, 19)}`);
    const thaoTac = page.locator("#thao-tac");
    await expect(thaoTac.getByRole("button", { name: "Sửa nội dung", exact: true })).toBeVisible();
    await expect(thaoTac.locator(".nut[data-loai='chinh']")).toHaveCount(0);
  });

  test("điện thoại 390 px: nút bước chính của người gửi nằm trên thẻ Nội dung yêu cầu (#561)", async ({ browser, page }) => {
    // Hồ sơ chờ người gửi bổ sung thông tin: bước chính là "Bổ sung thông tin" — điều phối viên hỏi thêm qua giao diện
    const ma = await guiYeuCauThu(page, `Thứ tự 390 ${test.info().project.name} ${new Date().toISOString().slice(0, 19)}`);
    const dieuPhoi = await browser.newContext({ storageState: tepPhien("dieu-phoi") });
    const trang = await dieuPhoi.newPage();
    await trang.goto(`/dieu-phoi/${ma}`, { waitUntil: "networkidle" });
    const thaoTacDp = trang.locator("#thao-tac");
    await thaoTacDp.getByRole("button", { name: "Yêu cầu bổ sung thông tin", exact: true }).click();
    await thaoTacDp.getByRole("textbox").fill("Nhờ bạn gửi thêm ảnh chụp thiết bị.");
    await thaoTacDp.getByRole("button", { name: /^Xác nhận · Yêu cầu bổ sung thông tin/ }).click();
    await expect(thaoTacDp.getByRole("button", { name: "Yêu cầu bổ sung thông tin", exact: true })).toHaveCount(0);
    await dieuPhoi.close();

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`/yeu-cau/${ma}`, { waitUntil: "networkidle" });
    const nutChinh = page.locator("#thao-tac .nut[data-loai='chinh']");
    await expect(nutChinh).toHaveText("Bổ sung thông tin");
    const noiDung = page.getByRole("heading", { level: 2, name: "Nội dung yêu cầu" });
    const [hopNut, hopNoiDung] = [await nutChinh.boundingBox(), await noiDung.boundingBox()];
    expect(hopNut && hopNoiDung && hopNut.y < hopNoiDung.y, "thao tác đứng trước nội dung trên điện thoại").toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)).toBe(false);
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

  test("bảng Xem lại chỉ hiện ở bước 3 và liệt kê trường riêng đã điền (#552)", async ({ page }) => {
    // Khối bước 3 từng mang `display` trong style, đè thuộc tính `hidden`: bảng Xem lại hiện cả ở bước 1 và 2
    const xemLai = page.locator('[data-buoc="3"]');
    await page.goto("/yeu-cau/moi", { waitUntil: "networkidle" });
    await expect(page.locator('[data-buoc="1"]')).toBeVisible();
    await expect(xemLai).toBeHidden();
    await expect(page.getByText("Thời hạn cam kết", { exact: true })).toBeHidden();

    await page.getByText("Sự cố thiết bị").first().click();
    await expect(page.locator('input[name="title"]')).toBeVisible();
    await expect(xemLai).toBeHidden();
    await expect(page.getByText("Thời hạn cam kết", { exact: true })).toBeHidden();

    // Trường riêng của loại "Sự cố thiết bị" trong dữ liệu khởi tạo: hai ô chữ bắt buộc, một ô chọn không bắt buộc
    await page.locator('input[name="title"]').fill("Bảng Xem lại có trường riêng");
    await page.locator("#truong-rieng-ma-tai-san").fill("KT-0552");
    await page.locator("#truong-rieng-vi-tri").fill("Tầng 2, phòng họp nhỏ");
    await page.getByRole("button", { name: /Tiếp tục/ }).click();

    await expect(xemLai).toBeVisible();
    await expect(page.locator('[data-buoc="2"]')).toBeHidden();
    await expect(xemLai).toContainText("Mã tài sản");
    await expect(xemLai).toContainText("KT-0552");
    await expect(xemLai).toContainText("Vị trí");
    await expect(xemLai).toContainText("Tầng 2, phòng họp nhỏ");
    // Ô chọn bỏ trống thì không liệt kê
    await expect(xemLai).not.toContainText("Mức ảnh hưởng");
    await chup(page, test.info().project.name, "nguoi-gui-gui-yeu-cau-buoc-3");
  });

  test("thiếu trường bắt buộc không qua được bước 2, câu báo dưới ô; khung lỗi cũ không bám (#555)", async ({ page }) => {
    // Loại "Sự cố thiết bị" của dữ liệu khởi tạo có hai trường bắt buộc: Mã tài sản, Vị trí
    const buoc2 = page.locator('[data-buoc="2"]');
    const buoc3 = page.locator('[data-buoc="3"]');
    const thieuMa = page.getByText("Chưa điền Mã tài sản.", { exact: true });
    const thieuViTri = page.getByText("Chưa điền Vị trí.", { exact: true });
    await page.goto("/yeu-cau/moi", { waitUntil: "networkidle" });
    await page.getByText("Sự cố thiết bị").first().click();
    await page.locator('input[name="title"]').fill(`Thiếu trường bắt buộc ${Date.now()}`);
    await expect(thieuMa).toHaveCount(0);

    // Bấm Tiếp tục khi cả hai còn trống: ở lại bước 2, báo dưới từng ô, tiêu điểm về ô trống đầu tiên
    await page.getByRole("button", { name: /Tiếp tục/ }).click();
    await expect(buoc2).toBeVisible();
    await expect(buoc3).toBeHidden();
    await expect(thieuMa).toBeVisible();
    await expect(thieuViTri).toBeVisible();
    await expect(page.locator("#truong-rieng-ma-tai-san")).toBeFocused();
    await expect(page.locator("#truong-rieng-ma-tai-san")).toHaveAttribute("aria-invalid", "true");
    await chup(page, test.info().project.name, "nguoi-gui-gui-yeu-cau-thieu-truong");
    // Dải bước cũng không mở đường tắt tới bước 3
    await page.getByRole("button", { name: /Xem lại và gửi/ }).click();
    await expect(buoc3).toBeHidden();

    // Điền một ô: câu báo của ô đó mất, ô kia còn; bấm tiếp thì tiêu điểm sang ô còn thiếu
    await page.locator("#truong-rieng-ma-tai-san").fill("KT-0555");
    await expect(thieuMa).toHaveCount(0);
    await expect(thieuViTri).toBeVisible();
    await page.getByRole("button", { name: /Tiếp tục/ }).click();
    await expect(buoc3).toBeHidden();
    await expect(page.locator("#truong-rieng-vi-tri")).toBeFocused();

    // Đủ thì qua
    await page.locator("#truong-rieng-vi-tri").fill("Tầng 2");
    await expect(thieuViTri).toHaveCount(0);
    await page.getByRole("button", { name: /Tiếp tục/ }).click();
    await expect(buoc3).toBeVisible();

    // Dịch vụ vẫn là lớp chặn cuối và báo đủ mọi trường thiếu một lần. Giả lập khai báo loại đổi giữa lúc nạp biểu
    // mẫu và lúc gửi bằng cách xóa bộ giá trị trong ô ẩn ngay trước khi bấm gửi
    await page.locator('input[name="details"]').evaluate((o: HTMLInputElement) => {
      o.value = "{}";
    });
    await page.getByRole("button", { name: "Gửi yêu cầu" }).click();
    const khungLoi = page.locator('form p[role="alert"]');
    await expect(khungLoi).toHaveText("Chưa điền Mã tài sản, Vị trí.");
    await expect(page).toHaveURL(/\/yeu-cau\/moi/);
    // Người gửi quay lại sửa: khung lỗi của lần gửi trước biến mất, không bám theo
    await page.getByRole("button", { name: /Quay lại/ }).click();
    await expect(khungLoi).toHaveCount(0);
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

  test("gõ thêm mô tả thì biểu mẫu hỏi lại theo mô tả mới, khối gợi ý đổi theo (#556)", async ({ page }) => {
    // Lượt test tay 25/11: gõ thêm mô tả khác hẳn mà khung gợi ý không đổi. Bài này giữ phần của cổng: mỗi lần
    // ngừng gõ mô tả, biểu mẫu gửi lại cả tiêu đề lẫn mô tả mới và vẽ đúng danh sách dịch vụ trả về
    const hoi: { title: string; description: string }[] = [];
    await page.route("**/api/yeu-cau/tuong-tu", (r) => {
      const than = r.request().postDataJSON() as { title: string; description: string };
      hoi.push(than);
      const ketGiay = than.description.includes("nhét nhiều giấy");
      return r.fulfill({
        json: {
          enabled: true,
          items: [
            ketGiay
              ? { title: "Máy in tầng 3 kẹt giấy liên tục", request_type: "Sự cố thiết bị",
                  resolution: "Vệ sinh con lăn kéo giấy.", closed_at: "2026-10-20T03:00:00Z", score: 0.8 }
              : { title: "Máy in phòng Kinh doanh báo hết mực", request_type: "Sự cố thiết bị",
                  resolution: "Lắp lại hộp mực cho khớp chip.", closed_at: "2026-10-21T03:00:00Z", score: 0.8 },
          ],
        },
      });
    });

    await page.goto("/yeu-cau/moi");
    await page.getByText("Sự cố thiết bị").first().click();
    await page.locator('input[name="title"]').fill("Máy in bị lỗi không in được");
    const khoi = page.getByTestId("goi-y-tuong-tu");
    await expect(khoi).toContainText("báo hết mực");

    await page.locator('textarea[name="description"]').fill("Máy in bị lỗi khi lỡ nhét nhiều giấy quá");
    await expect(khoi).toContainText("kẹt giấy liên tục");
    await expect(khoi).not.toContainText("báo hết mực");
    expect(hoi.at(-1)).toMatchObject({ title: "Máy in bị lỗi không in được", description: "Máy in bị lỗi khi lỡ nhét nhiều giấy quá" });
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
    // Tiêu đề ở đầu ngăn là liên kết tới trang đầy đủ (#557)
    await expect(ngan.getByRole("heading", { level: 2 }).getByRole("link")).toHaveAttribute("href", `/dieu-phoi/${h.ma}`);
  });

  test("xem nhanh: mở thao tác thì nội dung thu thành tóm tắt, nút xác nhận dính đáy ngăn (#561)", async ({ page }) => {
    const h = docHoSo();
    await page.goto(`/dieu-phoi?xem=${h.ma}`, { waitUntil: "networkidle" });
    const ngan = page.locator("aside.ngan");
    const noiDung = ngan.getByText("Nội dung yêu cầu", { exact: true });
    await expect(noiDung).toBeVisible();
    await ngan.locator(".ngan-chan .nut[data-loai='chinh']").click();

    // Đoạn tóm tắt mang mô tả người gửi viết; thẻ Nội dung và Dòng thời gian nhường chỗ
    const tomTat = ngan.locator(".ngan-tom-tat");
    await expect(tomTat).toContainText("Hồ sơ do kịch bản kiểm tra giao diện tạo.");
    await expect(noiDung).toBeHidden();
    // Tiêu điểm vào khung — nhóm mang tên thao tác — không rơi về đầu trang khi nút vừa bấm rời hàng nút
    await expect(ngan.getByRole("group", { name: "Phân loại yêu cầu" })).toBeFocused();
    // Hàng nút ở đáy ngăn: xác nhận, hủy thao tác, các thao tác khác; nằm trong khung nhìn
    const hang = ngan.locator(".hang-xac-nhan-ngan");
    await expect(hang.getByRole("button", { name: /^Xác nhận · Phân loại yêu cầu/ })).toBeInViewport();
    await expect(hang.getByRole("button", { name: "Hủy thao tác" })).toBeVisible();
    await expect(hang.locator("details.menu-thao-tac > summary")).toHaveText("Thao tác khác");

    // "Xem đủ nội dung và dòng thời gian" đóng khung, nội dung trở lại
    await tomTat.getByRole("button", { name: "Xem đủ nội dung và dòng thời gian" }).click();
    await expect(ngan.locator(".khung-xac-nhan")).toHaveCount(0);
    await expect(noiDung).toBeVisible();
    await expect(ngan.locator(".ngan-chan .nut[data-loai='chinh']")).toBeFocused();
  });

  test("Ctrl + bấm hay bấm chuột giữa trên dòng hàng đợi mở trang đầy đủ ở thẻ mới (#557)", async ({ page, context }) => {
    await page.goto("/dieu-phoi", { waitUntil: "networkidle" });
    const dong = page.locator("[data-xem-dong]").first();
    const ma = await dong.getAttribute("data-xem-dong");
    for (const cach of [{ modifiers: ["ControlOrMeta"] as const }, { button: "middle" as const }]) {
      const [moi] = await Promise.all([context.waitForEvent("page"), dong.click(cach)]);
      await moi.waitForLoadState();
      expect(new URL(moi.url()).pathname, JSON.stringify(cach)).toBe(`/dieu-phoi/${ma}`);
      await moi.close();
      // Thẻ đang mở không mở ngăn xem nhanh
      await expect(page).not.toHaveURL(/xem=/);
    }
  });

  test("trang đầy đủ chỉ tô màu chính cho bước chính trong dữ liệu (#557)", async ({ page }) => {
    const h = docHoSo();
    await page.goto(`/dieu-phoi/${h.ma}`, { waitUntil: "networkidle" });
    const chinh = page.locator("#thao-tac .nut[data-loai='chinh']");
    await expect(chinh).toHaveCount(1);
    await expect(chinh).toContainText("Phân loại yêu cầu");
    // Không còn dòng ghi chú cuối khung thao tác (#561): chỉ nút làm được mới hiện, nói thêm không giúp gì
    await expect(page.getByText("Chỉ hiện những thao tác", { exact: false })).toHaveCount(0);
    await expect(page.getByText("Các nút phụ thuộc vào trạng thái hồ sơ", { exact: false })).toHaveCount(0);
    // Khuôn #561: thẻ thao tác đứng đầu cột chính, trên Nội dung yêu cầu; cột phải có Hạn xử lý và Thông tin hồ sơ
    const [hopThaoTac, hopNoiDung] = [
      await page.locator(".the-thao-tac").boundingBox(),
      await page.getByText("Nội dung yêu cầu", { exact: true }).boundingBox(),
    ];
    expect(hopThaoTac && hopNoiDung && hopThaoTac.y < hopNoiDung.y, "thao tác trên nội dung").toBe(true);
    await expect(page.locator(".cot-dinh")).toContainText("Hạn xử lý");
    await expect(page.locator(".cot-dinh .the-thong-tin")).toContainText("Loại yêu cầu");
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
      await ngan.getByRole("button", { name: "Hủy thao tác" }).click();
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
            // Hồ sơ không ghi cách giải quyết (#556): dòng không được kết thúc bằng gạch nối treo
            { case_id: 11, code: "YC-2026-0011", title: "Máy in tầng 2 kẹt giấy", request_type: "Sự cố thiết bị",
              resolution: "", closed_at: "2026-10-05T03:00:00+00:00", score: 0.61 },
          ],
        },
      }),
    );
    await dungHoSoChoChuyenPhong(browser, page, "Căn cứ bật");
    const { thaoTac, the } = await moBangChuyenPhong(page);
    const khoi = the.locator(".can-cu-tuong-tu");
    // Gập sẵn (#561): nhãn ghi số hồ sơ, bấm mới mở danh sách; thẻ gợi ý (gợi ý, lý do, nguồn) vẫn hiện đủ
    const tom = khoi.locator("summary");
    await expect(tom).toHaveText("Xem 3 hồ sơ đã giải quyết tương tự");
    await expect(khoi.getByRole("link", { name: "YC-2026-0007" })).toBeHidden();
    await expect(the.locator(".the-goi-y-nguon").first()).toBeVisible();
    await tom.click();
    // Một khối mỗi bảng (#559): bảng có ô loại lẫn ô phòng; có thẻ gợi ý cho cả hai thì danh sách vẫn hiện một lần
    await expect(thaoTac.locator(".can-cu-tuong-tu")).toHaveCount(1);
    await expect(khoi.locator("li")).toHaveCount(3);
    await expect(khoi.getByRole("link", { name: "YC-2026-0007" })).toHaveAttribute("href", "/dieu-phoi/7");
    await expect(khoi).toContainText("Đổi cáp HDMI mới.");
    const khongCach = (await khoi.locator("li").nth(2).innerText()).trim();
    expect(khongCach, "dòng không có cách giải quyết").toBe("YC-2026-0011 Máy in tầng 2 kẹt giấy · Sự cố thiết bị");
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

  /** Thẻ mang tiêu đề cấp 2 đúng chữ đó. */
  const theCo = (page: Page, tieuDe: string) =>
    page.locator("section.the", { has: page.getByRole("heading", { level: 2, name: tieuDe, exact: true }) });

  test("trang chủ 1440 × 900: thẻ Tình trạng hệ thống gọn, không dài hơn thẻ cột trái, đủ dịch vụ (#561)", async ({ page }) => {
    // Đặt khổ trong bài: cấu hình màn hẹp cũng kiểm đúng khổ hai cột
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/", { waitUntil: "networkidle" });
    const theTinhTrang = theCo(page, "Tình trạng hệ thống");
    const trai = await page.locator(".cot-viec > *").first().boundingBox();
    const phai = await theTinhTrang.boundingBox();
    expect(trai, "thẻ cột trái").not.toBeNull();
    expect(phai, "thẻ tình trạng").not.toBeNull();
    expect(phai!.y + phai!.height, "cạnh dưới thẻ tình trạng so với thẻ cột trái").toBeLessThanOrEqual(
      trai!.y + trai!.height + 0.5,
    );
    // Dịch vụ ổn: một dòng (chấm, tên, chữ ngắn)
    for (const dong of await theTinhTrang.locator(".dong-tinh-trang[data-gon]").all()) {
      expect((await dong.boundingBox())!.height).toBeLessThanOrEqual(24);
    }
    // Không bỏ dịch vụ nào: đủ các hàng như dạng đầy đủ của màn Hệ thống
    const soGon = await theTinhTrang.locator(".dong-tinh-trang").count();
    await page.goto("/he-thong", { waitUntil: "networkidle" });
    await expect(theCo(page, "Các dịch vụ").locator(".dong-tinh-trang")).toHaveCount(soGon);
  });

  test("màn Hệ thống: lưới hai cột ở 1440, một cột không cuộn ngang ở 375, đúng thứ tự khối (#561)", async ({ page }) => {
    const khoi = ["Các dịch vụ", "Xuất nhật ký sự kiện", "Webhook", "Nhật ký truy cập dữ liệu cá nhân"];
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/he-thong", { waitUntil: "networkidle" });
    const [dv, xuat, wh, tc] = await Promise.all(khoi.map(async (t) => (await theCo(page, t).boundingBox())!));
    // Cột trái: các dịch vụ; cột phải: xuất nhật ký rồi webhook; nhật ký truy cập trải hết hai cột bên dưới
    expect(Math.abs(dv.y - xuat.y), "Các dịch vụ và Xuất nhật ký cùng top").toBeLessThanOrEqual(4);
    expect(xuat.x).toBeGreaterThanOrEqual(dv.x + dv.width);
    expect(Math.abs(wh.x - xuat.x)).toBeLessThanOrEqual(1);
    expect(wh.y).toBeGreaterThan(xuat.y + xuat.height - 1);
    expect(Math.abs(tc.x - dv.x)).toBeLessThanOrEqual(1);
    expect(Math.abs(tc.x + tc.width - (xuat.x + xuat.width))).toBeLessThanOrEqual(1);
    expect(tc.y).toBeGreaterThanOrEqual(Math.max(dv.y + dv.height, wh.y + wh.height) - 1);

    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/he-thong", { waitUntil: "networkidle" });
    expect(await page.evaluate(() => document.documentElement.scrollWidth), "không cuộn ngang").toBeLessThanOrEqual(375);
    const top = await Promise.all(khoi.map(async (t) => (await theCo(page, t).boundingBox())!.y));
    // Một cột: dịch vụ → xuất nhật ký → webhook → nhật ký truy cập, khối sau nằm hẳn dưới khối trước
    for (let i = 1; i < top.length; i++) expect(top[i], `${khoi[i]} dưới ${khoi[i - 1]}`).toBeGreaterThan(top[i - 1]);
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
