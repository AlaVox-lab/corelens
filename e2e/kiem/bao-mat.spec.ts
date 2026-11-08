// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Lớp bảo mật ở biên (#243): các trang chính trả đủ tiêu đề bảo mật, chính sách nội dung có số dùng
// một lần đổi mỗi lượt và khớp với script trong trang, đăng nhập quay về bị giới hạn tốc độ, và
// thao tác bị giới hạn ở dịch vụ ứng dụng hiện câu tiếng Việt thay vì trang lỗi.
//
// Không phụ thuộc cấu hình hiển thị nên chỉ chạy ở một cấu hình (rong-sang). Việc "giao diện vẫn
// chạy dưới chính sách mới" (không vi phạm chính sách ở mọi màn, kể cả Báo cáo nhúng Superset) đã
// nằm trong `moMan` của giao-dien.spec.ts, chạy ở cả bốn cấu hình.

import { type APIResponse, expect, test } from "@playwright/test";

import { type Vai, tepPhien } from "./chung";

test.beforeEach(() => {
  test.skip(test.info().project.name !== "rong-sang", "bài này không đổi theo cấu hình hiển thị");
});

/** Rút số dùng một lần ra khỏi chính sách nội dung của một phản hồi. */
function nonceCuaCsp(csp: string): string {
  const m = /script-src[^;]*'nonce-([^']+)'/.exec(csp);
  expect(m, `script-src không có nonce: ${csp}`).not.toBeNull();
  return m![1];
}

function kiemTieuDeBaoMat(tl: APIResponse, ngu: string) {
  const h = tl.headers();
  expect(h["x-content-type-options"], ngu).toBe("nosniff");
  expect(h["referrer-policy"], ngu).toBe("strict-origin-when-cross-origin");
  expect(h["strict-transport-security"], ngu).toMatch(/^max-age=\d+/);
  expect(h["permissions-policy"], ngu).toContain("camera=()");
  expect(h["permissions-policy"], ngu).toContain("microphone=()");
  expect(h["permissions-policy"], ngu).toContain("geolocation=()");
  expect(h["x-frame-options"], ngu).toBe("DENY");
}

function kiemCsp(csp: string, ngu: string) {
  expect(csp, ngu).toContain("default-src 'self'");
  expect(csp, ngu).toMatch(/script-src 'self' 'nonce-[^']+' 'strict-dynamic'/);
  expect(csp, ngu).not.toMatch(/script-src[^;]*'unsafe-inline'/);
  expect(csp, ngu).not.toMatch(/script-src[^;]*'unsafe-eval'/); // chỉ chế độ phát triển mới có
  expect(csp, ngu).toContain("object-src 'none'");
  expect(csp, ngu).toContain("base-uri 'self'");
  expect(csp, ngu).toContain("frame-ancestors 'none'");
  // Luồng OIDC chuyển hướng qua Keycloak, và mục Báo cáo nhúng khung Superset: đúng hai gốc đó
  expect(csp, ngu).toMatch(/form-action 'self' http:\/\/localhost:\d+;/);
  expect(csp, ngu).toMatch(/frame-src http:\/\/localhost:\d+;/);
}

test("các trang chính trả đủ tiêu đề bảo mật, kể cả khi chưa đăng nhập", async ({ browser }) => {
  const khach = await browser.newContext();
  const duongKhach = ["/"];
  for (const duong of duongKhach) {
    const tl = await khach.request.get(duong);
    kiemTieuDeBaoMat(tl, `khách ${duong}`);
    kiemCsp(tl.headers()["content-security-policy"], `khách ${duong}`);
  }
  await khach.close();

  const vaiTrang: [Vai, string[]][] = [
    ["nguoi-gui", ["/", "/yeu-cau", "/yeu-cau/moi", "/hop-thu"]],
    ["dieu-phoi", ["/dieu-phoi", "/bao-cao"]],
    ["truong-phong", ["/phong-ban"]],
    ["quan-tri", ["/he-thong"]],
  ];
  for (const [vai, cacDuong] of vaiTrang) {
    const nc = await browser.newContext({ storageState: tepPhien(vai) });
    for (const duong of cacDuong) {
      const tl = await nc.request.get(duong);
      expect(tl.status(), `${vai} ${duong}`).toBe(200);
      kiemTieuDeBaoMat(tl, `${vai} ${duong}`);
      kiemCsp(tl.headers()["content-security-policy"], `${vai} ${duong}`);
    }
    await nc.close();
  }
});

test("tệp tĩnh và tuyến API cũng mang tiêu đề chống đoán kiểu và chống nhúng khung", async ({ browser }) => {
  const nc = await browser.newContext({ storageState: tepPhien("nguoi-gui") });
  const trang = await (await nc.request.get("/")).text();
  const duongTinh = /\/_next\/static\/[^"']+\.js/.exec(trang)?.[0];
  expect(duongTinh, "trang có trỏ tới tệp tĩnh của Next").toBeTruthy();

  const tinh = await nc.request.get(duongTinh!);
  expect(tinh.status()).toBe(200);
  kiemTieuDeBaoMat(tinh, "tệp tĩnh");

  const api = await nc.request.get("/api/hop-thu/chua-doc");
  kiemTieuDeBaoMat(api, "tuyến API");
  await nc.close();
});

test("số dùng một lần đổi mỗi lượt và khớp với script trong trang", async ({ browser }) => {
  const khach = await browser.newContext();
  const lan1 = await khach.request.get("/");
  const lan2 = await khach.request.get("/");
  const nonce1 = nonceCuaCsp(lan1.headers()["content-security-policy"]);
  const nonce2 = nonceCuaCsp(lan2.headers()["content-security-policy"]);
  expect(nonce1).not.toBe(nonce2);

  const html = await lan1.text();
  // Đoạn chống nháy sáng/tối tự viết ở layout phải mang đúng số của lượt này...
  expect(html).toContain(`nonce="${nonce1}"`);
  // ...và số của lượt kia không được lọt vào
  expect(html).not.toContain(nonce2);
  // Mọi thẻ script trong trang đều có số, không thẻ nào chạy nhờ 'unsafe-inline'
  const thePhanLop = [...html.matchAll(/<script\b[^>]*>/g)].map((m) => m[0]);
  expect(thePhanLop.length).toBeGreaterThan(0);
  for (const the of thePhanLop) expect(the, "thẻ script thiếu nonce").toContain("nonce=");
  await khach.close();
});

test("đăng nhập quay về bị giới hạn tốc độ theo địa chỉ IP", async ({ browser }) => {
  const khach = await browser.newContext();
  // Địa chỉ giả riêng cho bài: bộ đếm theo IP lấy từ X-Forwarded-For, nên bài không chiếm hạn mức của
  // ai khác (kể cả các lần đăng nhập thật của bước chuẩn bị)
  const ip = `203.0.113.${Math.floor(Math.random() * 250) + 1}`;
  let bi429: APIResponse | undefined;
  let soLan = 0;
  for (; soLan < 200 && !bi429; soLan++) {
    const tl = await khach.request.get("/api/auth/callback", {
      headers: { "x-forwarded-for": ip },
      maxRedirects: 0,
    });
    if (tl.status() === 429) bi429 = tl;
    else expect([302, 303, 307, 308], "trước ngưỡng: chuyển hướng về đầu luồng").toContain(tl.status());
  }
  expect(bi429, "phải gặp 429 trước 200 lượt").toBeDefined();
  expect(soLan).toBeGreaterThan(1);
  expect(Number(bi429!.headers()["retry-after"])).toBeGreaterThan(0);
  const noiDung = await bi429!.text();
  expect(noiDung).toContain("Đăng nhập quá nhiều lần");
  expect(noiDung).toMatch(/Thử lại sau \d+ giây/);

  // Một địa chỉ khác không bị vạ lây
  const khac = await khach.request.get("/api/auth/callback", {
    headers: { "x-forwarded-for": "198.51.100.7" },
    maxRedirects: 0,
  });
  expect(khac.status()).not.toBe(429);
  await khach.close();
});

test("tải tệp vượt giới hạn tốc độ: giao diện nhận câu tiếng Việt, không phải trang lỗi", async ({ browser }) => {
  // Hồ sơ không tồn tại: bộ đếm chạy trước điểm cuối nên vẫn đếm, mà không đụng kho tệp. Dùng tài
  // khoản quản trị — không bài nào khác tải tệp bằng tài khoản này.
  const nc = await browser.newContext({ storageState: tepPhien("quan-tri") });
  const tep = { name: "ghi-chu.txt", mimeType: "text/plain", buffer: Buffer.from("xin chào") };

  let bi: { status: number; than: { ok: boolean; ma?: string; thongDiep?: string } } | undefined;
  for (let i = 0; i < 200 && !bi; i++) {
    const tl = await nc.request.post("/api/tep/ho-so/999999999", { multipart: { files: tep } });
    const than = await tl.json();
    if (than.ma === "rate-limited") bi = { status: tl.status(), than };
  }
  expect(bi, "phải gặp giới hạn tốc độ trước 200 lượt").toBeDefined();
  // Lỗi nghiệp vụ đã dịch, không phải 500 của cổng
  expect(bi!.status).toBe(422);
  expect(bi!.than.ok).toBe(false);
  expect(bi!.than.thongDiep).toMatch(/Bạn tải tệp lên quá nhanh\. Thử lại sau \d+ giây\./);
  await nc.close();
});
