// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Xác thực hai lớp (#366), qua ĐĂNG NHẬP THẬT: một tài khoản mới thiết lập mã dùng một lần ở lần đăng
// nhập đầu, rồi đăng nhập lại phải nhập mã. Mã tính bằng mô-đun crypto của Node theo đúng RFC 6238, từ
// khóa và chính sách hiện trên chính màn thiết lập — như một ứng dụng xác thực thật.
//
// Chỉ chạy khi cụm đã bật xác thực hai lớp (`python scripts/xac_thuc_hai_lop.py bat`) VÀ đặt HAI_LOP=1.
// Lượt mặc định bỏ qua bài này. Chạy riêng một cấu hình (dự án `hai-lop` trong playwright.config.ts),
// không phụ thuộc bước chuẩn bị: khi bật, các tài khoản mẫu cũng bị buộc thiết lập mã nên bước chuẩn bị
// không đăng nhập được nữa. Muốn chạy lại trọn bộ thì `tat` trước.
//
// Tài khoản thử tạo riêng qua API quản trị Keycloak, mượn vai trò của tài khoản người gửi mẫu, xóa khi
// xong — không đụng tài khoản mẫu nào ngoài việc ĐỌC xem chúng đã bị buộc thiết lập mã chưa.
//
//     HAI_LOP=1 CONG=http://localhost:3000 KEYCLOAK=http://localhost:8080 npx playwright test xac-thuc-hai-lop

import crypto from "node:crypto";

import { type APIRequestContext, type Page, expect, request, test } from "@playwright/test";

import { VAI } from "./chung";

const BAT = process.env.HAI_LOP === "1";
const KEYCLOAK = (process.env.KEYCLOAK ?? "http://localhost:8080").replace(/\/$/, "");
const REALM = process.env.KEYCLOAK_REALM ?? "dx-os-lab";
// Tài khoản quản trị mẫu của infra/.env.example — chỉ có ý nghĩa trên cụm dựng thử
const QUAN_TRI = process.env.KEYCLOAK_ADMIN_USER ?? "admin";
const MAT_KHAU_QUAN_TRI = process.env.KEYCLOAK_ADMIN_PASSWORD ?? "admin";
const HANH_DONG = "CONFIGURE_TOTP";

// ---------------------------------------------------------------------------
// Mã dùng một lần (RFC 4648 base32, RFC 6238 TOTP)
// ---------------------------------------------------------------------------

function giaiBase32(chuoi: string): Buffer {
  const BANG = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  const ra: number[] = [];
  let bit = 0;
  let gom = 0;
  for (const kyTu of chuoi.replace(/[\s=]/g, "").toUpperCase()) {
    const i = BANG.indexOf(kyTu);
    if (i < 0) throw new Error(`Khóa base32 có ký tự lạ: ${kyTu}`);
    gom = ((gom << 5) | i) & 0xfff;
    bit += 5;
    if (bit >= 8) {
      ra.push((gom >> (bit - 8)) & 0xff);
      bit -= 8;
    }
  }
  return Buffer.from(ra);
}

type ChinhSach = { thuatToan: string; soChu: number; chuKy: number };

function maTotp(khoa: Buffer, buoc: number, cs: ChinhSach): string {
  const dem = Buffer.alloc(8);
  dem.writeBigUInt64BE(BigInt(buoc));
  const h = crypto.createHmac(cs.thuatToan, khoa).update(dem).digest();
  const lech = h[h.length - 1] & 0xf;
  return String((h.readUInt32BE(lech) & 0x7fffffff) % 10 ** cs.soChu).padStart(cs.soChu, "0");
}

const buocHienTai = (cs: ChinhSach) => Math.floor(Date.now() / 1000 / cs.chuKy);

// ---------------------------------------------------------------------------
// API quản trị Keycloak
// ---------------------------------------------------------------------------

class QuanTri {
  private token = "";
  private layLuc = 0;

  private constructor(private api: APIRequestContext) {}

  static async tao(): Promise<QuanTri> {
    return new QuanTri(await request.newContext({ baseURL: `${KEYCLOAK}/admin/realms/${REALM}/` }));
  }

  /** Token quản trị của Keycloak chỉ sống một phút mà bài kéo dài hơn thế: lấy lại sau 30 giây. */
  private async tieuDe() {
    if (Date.now() - this.layLuc > 30_000) {
      const tl = await this.api.post(`${KEYCLOAK}/realms/master/protocol/openid-connect/token`, {
        form: { grant_type: "password", client_id: "admin-cli", username: QUAN_TRI, password: MAT_KHAU_QUAN_TRI },
      });
      expect(tl.status(), "đăng nhập API quản trị Keycloak — kiểm KEYCLOAK và tài khoản quản trị").toBe(200);
      this.token = (await tl.json()).access_token;
      this.layLuc = Date.now();
    }
    return { headers: { Authorization: `Bearer ${this.token}` } };
  }

  async doc<T = unknown>(duong: string): Promise<T> {
    const tl = await this.api.get(duong, await this.tieuDe());
    expect(tl.ok(), `GET ${duong}`).toBeTruthy();
    return tl.json();
  }

  async idCua(ten: string): Promise<string> {
    const ds = await this.doc<{ id: string }[]>(`users?username=${encodeURIComponent(ten)}&exact=true`);
    expect(ds, `tài khoản ${ten}`).toHaveLength(1);
    return ds[0].id;
  }

  /** Tạo tài khoản thử mượn vai trò và nhóm của một tài khoản mẫu. Trả id. */
  async taoTaiKhoan(ten: string, matKhau: string, mau: string): Promise<string> {
    const idMau = await this.idCua(mau);
    const banMau = await this.doc<{ email: string }>(`users/${idMau}`);
    const tl = await this.api.post("users", {
      ...(await this.tieuDe()),
      data: {
        username: ten,
        enabled: true,
        emailVerified: true,
        firstName: "Kiểm",
        lastName: "Hai Lớp",
        email: `${ten}@${banMau.email.split("@")[1]}`,
        credentials: [{ type: "password", value: matKhau, temporary: false }],
      },
    });
    expect(tl.status(), "tạo tài khoản thử").toBe(201);
    const id = await this.idCua(ten);
    const vaiTro = await this.doc<object[]>(`users/${idMau}/role-mappings/realm`);
    const gan = await this.api.post(`users/${id}/role-mappings/realm`, { ...(await this.tieuDe()), data: vaiTro });
    expect(gan.ok(), "gán vai trò cho tài khoản thử").toBeTruthy();
    for (const nhom of await this.doc<{ id: string }[]>(`users/${idMau}/groups`)) {
      expect((await this.api.put(`users/${id}/groups/${nhom.id}`, await this.tieuDe())).ok()).toBeTruthy();
    }
    return id;
  }

  async xoaTaiKhoan(id: string) {
    const tl = await this.api.delete(`users/${id}`, await this.tieuDe());
    expect(tl.ok(), "dọn tài khoản thử").toBeTruthy();
  }

  async dispose() {
    await this.api.dispose();
  }
}

// ---------------------------------------------------------------------------
// Bài kiểm
// ---------------------------------------------------------------------------

async function nhapMatKhau(page: Page, ten: string, matKhau: string) {
  await page.goto("/");
  await page.getByRole("link", { name: "Đăng nhập bằng tài khoản công ty" }).click();
  await page.locator("#username").fill(ten);
  await page.locator("#password").fill(matKhau);
  await page.locator("#kc-login").click();
}

/** Giá trị sau dấu hai chấm của một dòng cấu hình trên màn thiết lập, như "Số chữ số: 6". */
async function giaTriDong(page: Page, id: string): Promise<string> {
  const chu = (await page.locator(`#${id}`).innerText()).trim();
  return chu.slice(chu.lastIndexOf(":") + 1).trim();
}

test.describe("xác thực hai lớp", () => {
  test.skip(!BAT, "chưa bật — chạy scripts/xac_thuc_hai_lop.py bat rồi đặt HAI_LOP=1");

  let qt: QuanTri;
  let idThu: string | undefined;

  test.beforeAll(async () => {
    qt = await QuanTri.tao();
  });

  test.afterAll(async () => {
    if (idThu) await qt.xoaTaiKhoan(idThu);
    await qt?.dispose();
  });

  test("tài khoản mới thiết lập mã ở lần đăng nhập đầu, lần sau phải nhập mã", async ({ browser }) => {
    test.setTimeout(150_000);

    await test.step("realm đã bật và tài khoản mẫu đã bị buộc thiết lập mã", async () => {
      const hd = await qt.doc<{ enabled: boolean; defaultAction: boolean }>(
        `authentication/required-actions/${HANH_DONG}`,
      );
      expect(hd.enabled && hd.defaultAction, "chưa bật — chạy scripts/xac_thuc_hai_lop.py bat").toBeTruthy();
      for (const ten of Object.values(VAI)) {
        const id = await qt.idCua(ten);
        const tk = await qt.doc<{ requiredActions?: string[] }>(`users/${id}`);
        const ma = await qt.doc<{ type: string }[]>(`users/${id}/credentials`);
        expect(
          (tk.requiredActions ?? []).includes(HANH_DONG) || ma.some((c) => c.type === "otp"),
          `${ten} phải đang chờ thiết lập mã hoặc đã có mã`,
        ).toBeTruthy();
      }
    });

    const ten = `kiem-hai-lop-${Date.now()}`;
    const matKhau = crypto.randomBytes(18).toString("base64url");
    idThu = await qt.taoTaiKhoan(ten, matKhau, VAI["nguoi-gui"]);

    await test.step("tài khoản mới tự nhận yêu cầu thiết lập mã", async () => {
      const tk = await qt.doc<{ requiredActions?: string[] }>(`users/${idThu}`);
      expect(tk.requiredActions ?? []).toContain(HANH_DONG);
    });

    let khoa: Buffer;
    let cs: ChinhSach;
    let buocDaDung: number;

    const nc1 = await browser.newContext();
    const page = await nc1.newPage();
    await test.step("màn thiết lập: tiếng Việt, có mã QR", async () => {
      await nhapMatKhau(page, ten, matKhau);
      await expect(page.locator("html")).toHaveAttribute("lang", "vi");
      await expect(page.locator("#kc-page-title")).toHaveText("Thiết lập xác thực hai lớp");
      await expect(page.getByText("Mở ứng dụng và quét mã QR:")).toBeVisible();
      await expect(page.locator("#kc-totp-secret-qr-code")).toBeVisible();
      // Lời báo của hành động bắt buộc, từ tệp thông điệp của chủ đề
      await expect(page.getByText("Tài khoản đã được bật xác thực hai lớp")).toBeVisible();
      await expect(page.locator("#saveTOTPBtn")).toHaveValue("Gửi");
    });

    await test.step("không quét được: khóa và chính sách hiện dạng chữ", async () => {
      await page.getByRole("link", { name: "Không quét được mã QR?" }).click();
      await expect(page.getByText("Mở ứng dụng và nhập khóa:")).toBeVisible();
      khoa = giaiBase32(await page.locator("#kc-totp-secret-key").innerText());
      cs = {
        thuatToan: (await giaTriDong(page, "kc-totp-algorithm")).toLowerCase(),
        soChu: Number(await giaTriDong(page, "kc-totp-digits")),
        chuKy: Number(await giaTriDong(page, "kc-totp-period")),
      };
      expect(khoa.length).toBeGreaterThan(0);
      expect(cs.soChu).toBeGreaterThan(0);
      expect(cs.chuKy).toBeGreaterThan(0);
    });

    await test.step("nhập mã sai bị từ chối bằng câu tiếng Việt, mã đúng thì vào cổng", async () => {
      const dung = maTotp(khoa, buocHienTai(cs), cs);
      await page.locator("#totp").fill(dung === "0".repeat(cs.soChu) ? "1".repeat(cs.soChu) : "0".repeat(cs.soChu));
      await page.locator("#userLabel").fill("Điện thoại kiểm thử");
      await page.locator("#saveTOTPBtn").click();
      await expect(page.getByText("Mã xác thực không hợp lệ.")).toBeVisible();

      buocDaDung = buocHienTai(cs);
      await page.locator("#totp").fill(maTotp(khoa, buocDaDung, cs));
      await page.locator("#userLabel").fill("Điện thoại kiểm thử");
      await page.locator("#saveTOTPBtn").click();
      await expect(page.getByRole("heading", { level: 1 })).toContainText("Chào");
    });
    await nc1.close();

    await test.step("tài khoản đã có mã, không còn chờ thiết lập", async () => {
      const tk = await qt.doc<{ requiredActions?: string[] }>(`users/${idThu}`);
      expect(tk.requiredActions ?? []).not.toContain(HANH_DONG);
      const ma = await qt.doc<{ type: string }[]>(`users/${idThu}/credentials`);
      expect(ma.filter((c) => c.type === "otp")).toHaveLength(1);
    });

    // Phiên trình duyệt mới: không còn cookie của Keycloak, phải đi lại từ mật khẩu
    const nc2 = await browser.newContext();
    const page2 = await nc2.newPage();
    await test.step("đăng nhập lại: sau mật khẩu là màn nhập mã", async () => {
      await nhapMatKhau(page2, ten, matKhau);
      await expect(page2.locator("#otp")).toBeVisible();
      await expect(page2.getByText("Mã một lần")).toBeVisible();
      await expect(page2.locator("#kc-page-title")).toHaveText("Đăng nhập");
    });

    await test.step("mã sai bị từ chối, mã đúng thì vào cổng", async () => {
      const dung = maTotp(khoa, buocHienTai(cs), cs);
      await page2.locator("#otp").fill(dung === "0".repeat(cs.soChu) ? "1".repeat(cs.soChu) : "0".repeat(cs.soChu));
      await page2.locator("#kc-login").click();
      await expect(page2.getByText("Mã xác thực không hợp lệ.")).toBeVisible();

      // Keycloak không nhận lại mã vừa dùng để thiết lập: chờ sang chu kỳ sau
      while (buocHienTai(cs) <= buocDaDung) await page2.waitForTimeout(1_000);
      await page2.locator("#otp").fill(maTotp(khoa, buocHienTai(cs), cs));
      await page2.locator("#kc-login").click();
      await expect(page2.getByRole("heading", { level: 1 })).toContainText("Chào");
    });
    await nc2.close();
  });
});
