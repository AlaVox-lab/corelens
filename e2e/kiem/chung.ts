// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Phần dùng chung của kịch bản: tài khoản mẫu theo vai, nơi lưu trạng thái đăng nhập, và hồ sơ thử
// mà bước chuẩn bị tạo ra. Tài khoản lấy từ realm mẫu (infra/keycloak/realm-dx-os-lab.json).

import fs from "node:fs";
import path from "node:path";

import { expect, type Page } from "@playwright/test";

export const VAI = {
  "nguoi-gui": "an.nguyen",
  "dieu-phoi": "binh.tran",
  "truong-phong": "dung.pham",
  "quan-tri": "khanh.vo",
} as const;

export type Vai = keyof typeof VAI;

// Mật khẩu chung của dữ liệu mẫu — chỉ có ý nghĩa trên cụm dựng thử. Đổi bằng biến MAT_KHAU.
export const MAT_KHAU = process.env.MAT_KHAU ?? "matkhau123";

const THU_MUC = path.join(import.meta.dirname, "..", "ket-qua", "trang-thai");
export const tepPhien = (vai: Vai) => path.join(THU_MUC, `${vai}.json`);
const TEP_HO_SO = path.join(THU_MUC, "ho-so.json");

export type HoSoThu = { ma: number; tieuDe: string };

export function luuHoSo(h: HoSoThu) {
  fs.mkdirSync(THU_MUC, { recursive: true });
  fs.writeFileSync(TEP_HO_SO, JSON.stringify(h));
}

export function docHoSo(): HoSoThu {
  return JSON.parse(fs.readFileSync(TEP_HO_SO, "utf8"));
}

/**
 * Bắt vi phạm chính sách nội dung (#243) ở tài liệu chính của trang. Trình duyệt chỉ ghi vi phạm
 * vào bảng điều khiển, không ném lỗi trang, nên bài kiểm thử chỉ nhìn `pageerror` sẽ bỏ lọt. Phải
 * gọi TRƯỚC `goto`; gọi nhiều lần vẫn chỉ cài một bộ nghe. Khung nhúng (Superset) có tài liệu và
 * chính sách riêng, không tính ở đây.
 */
export async function theoDoiCsp(page: Page) {
  await page.addInitScript(() => {
    const w = window as unknown as { __viPhamCsp?: string[] };
    if (w.__viPhamCsp) return;
    w.__viPhamCsp = [];
    document.addEventListener("securitypolicyviolation", (e) => {
      w.__viPhamCsp!.push(`${e.violatedDirective} ← ${e.blockedURI || "(nội tuyến)"}`);
    });
  });
}

/** Các vi phạm chính sách nội dung đã gom từ lúc `theoDoiCsp`; mảng rỗng là sạch. */
export function viPhamCsp(page: Page): Promise<string[]> {
  return page.evaluate(() => (window as unknown as { __viPhamCsp?: string[] }).__viPhamCsp ?? []);
}

/** Ảnh chụp theo cấu hình hiển thị và vai: ket-qua/anh/<cấu hình>/<vai>-<màn>.png */
export async function chup(page: Page, cauHinh: string, ten: string) {
  await page.mouse.move(0, 0);
  await page.screenshot({ path: path.join(import.meta.dirname, "..", "ket-qua", "anh", cauHinh, `${ten}.png`) });
}

/**
 * Người gửi gửi một yêu cầu "Sự cố thiết bị" qua biểu mẫu, đúng như người thật: chọn loại, điền
 * tiêu đề và mô tả, điền trường riêng bắt buộc của loại, đi hết ba bước. Trả mã hồ sơ vừa tạo.
 * `page` phải đang ở phiên của người gửi.
 */
export async function guiYeuCauThu(page: Page, tieuDe: string): Promise<number> {
  await page.goto("/yeu-cau/moi");
  await page.getByText("Sự cố thiết bị").first().click();
  await page.locator('input[name="title"]').fill(tieuDe);
  await page.locator('textarea[name="description"]').fill("Hồ sơ do kịch bản kiểm tra giao diện tạo.");
  // Trường riêng bắt buộc của loại Sự cố thiết bị (#250)
  // chọn theo mã ô: nhãn "Vị trí" cũng xuất hiện trong lời gợi ý của ô mô tả
  await page.locator("#truong-rieng-ma-tai-san").fill("KT-0001");
  await page.locator("#truong-rieng-vi-tri").fill("Phòng thử nghiệm");
  await page.getByRole("button", { name: "Tiếp tục" }).click();
  await page.getByRole("button", { name: "Gửi yêu cầu" }).click();

  await page.waitForURL(/\/yeu-cau\/\d+/);
  const ma = Number(new URL(page.url()).pathname.split("/").pop());
  expect(ma).toBeGreaterThan(0);
  await expect(page.getByRole("heading", { level: 1 })).toContainText(tieuDe);
  return ma;
}
