// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Phần dùng chung của kịch bản: tài khoản mẫu theo vai, nơi lưu trạng thái đăng nhập, và hồ sơ thử
// mà bước chuẩn bị tạo ra. Tài khoản lấy từ realm mẫu (infra/keycloak/realm-dx-os-lab.json).

import fs from "node:fs";
import path from "node:path";

import type { Page } from "@playwright/test";

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

/** Ảnh chụp theo cấu hình hiển thị và vai: ket-qua/anh/<cấu hình>/<vai>-<màn>.png */
export async function chup(page: Page, cauHinh: string, ten: string) {
  await page.mouse.move(0, 0);
  await page.screenshot({ path: path.join(import.meta.dirname, "..", "ket-qua", "anh", cauHinh, `${ten}.png`) });
}
