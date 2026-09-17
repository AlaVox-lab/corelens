// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khung chung của ba màn hình cổng gửi yêu cầu (#44).
//
// Cửa kiểm soát đăng nhập đặt ở đây chứ không lặp lại trong từng trang: mọi thứ dưới
// `/yeu-cau` đều là dữ liệu riêng của người dùng, nên nếu chưa đăng nhập thì không
// trang nào có gì để hiển thị. Gom về một chỗ cũng loại được kiểu lỗi "quên chặn ở
// trang mới thêm".

import Link from "next/link";

import { goiDichVu, type DanhTinh } from "@/lib/api";

function chuCaiDau(ten: string): string {
  const tu = ten.trim().split(/\s+/).filter(Boolean);
  if (tu.length === 0) return "?";
  // Tên Việt Nam đọc họ trước, tên gọi sau cùng. "Nguyễn Minh Anh" → "NA": chữ đầu
  // của họ và chữ đầu của tên gọi, giống cách người ta tự viết tắt.
  const dau = tu[0][0];
  const cuoi = tu.length > 1 ? tu[tu.length - 1][0] : "";
  return (dau + cuoi).toUpperCase();
}

function MoiDangNhap() {
  return (
    <main className="khung" style={{ padding: "96px 20px", maxWidth: "36rem" }}>
      <h1 style={{ margin: 0, fontSize: "24px", fontWeight: 600, letterSpacing: "-.02em" }}>
        Cổng yêu cầu nội bộ
      </h1>
      <p style={{ marginTop: "10px", color: "var(--ink-2)", fontSize: "14.5px" }}>
        Đăng nhập bằng tài khoản công ty để gửi yêu cầu và theo dõi hồ sơ của bạn.
      </p>
      <a href="/api/auth/login" className="nut" data-loai="chinh" style={{ marginTop: "20px" }}>
        Đăng nhập
      </a>
    </main>
  );
}

const MUC = [
  { duongDan: "/yeu-cau/moi", nhan: "Gửi yêu cầu" },
  { duongDan: "/yeu-cau", nhan: "Hồ sơ của tôi" },
];

export default async function KhungCong({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const danhTinh = await goiDichVu<DanhTinh>("/me");

  if (!danhTinh) return <MoiDangNhap />;

  const ten = danhTinh.name ?? danhTinh.username ?? danhTinh.id;

  return (
    <>
      <header
        className="khong-in"
        style={{
          position: "sticky",
          top: 0,
          zIndex: 20,
          background: "var(--surface)",
          borderBottom: "1px solid var(--line)",
        }}
      >
        <div
          className="khung"
          style={{
            padding: "11px 20px",
            display: "flex",
            alignItems: "center",
            gap: "14px",
            flexWrap: "wrap",
          }}
        >
          <Link
            href="/yeu-cau"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              marginRight: "auto",
              color: "inherit",
              textDecoration: "none",
            }}
          >
            <span
              className="mono"
              style={{
                width: "30px",
                height: "30px",
                borderRadius: "9px",
                background: "var(--accent)",
                color: "var(--accent-on)",
                display: "grid",
                placeItems: "center",
                fontSize: "11.5px",
                fontWeight: 500,
              }}
            >
              YC
            </span>
            <span style={{ display: "grid", lineHeight: 1.28 }}>
              <span style={{ fontSize: "14.5px", fontWeight: 600, letterSpacing: "-.01em" }}>
                Cổng yêu cầu nội bộ
              </span>
              <span style={{ fontSize: "11.5px", color: "var(--ink-3)" }}>
                Tiếp nhận · Phân loại · Điều phối
              </span>
            </span>
          </Link>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "9px",
              paddingLeft: "13px",
              borderLeft: "1px solid var(--line)",
            }}
          >
            <span
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "50%",
                background: "var(--surface-3)",
                border: "1px solid var(--line)",
                display: "grid",
                placeItems: "center",
                fontSize: "11px",
                fontWeight: 600,
                color: "var(--ink-2)",
              }}
            >
              {chuCaiDau(ten)}
            </span>
            <span style={{ display: "grid", lineHeight: 1.28 }}>
              <span style={{ fontSize: "12.5px", fontWeight: 600 }}>{ten}</span>
              <a
                href="/api/auth/logout"
                style={{ fontSize: "11px", color: "var(--ink-3)" }}
              >
                Đăng xuất
              </a>
            </span>
          </div>
        </div>

        <nav
          className="khung"
          style={{ padding: "0 20px", display: "flex", gap: "2px", overflow: "auto" }}
        >
          {MUC.map((m) => (
            <Link
              key={m.duongDan}
              href={m.duongDan}
              style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "11px 14px",
                fontSize: "13.5px",
                fontWeight: 600,
                whiteSpace: "nowrap",
                color: "var(--ink-2)",
                textDecoration: "none",
                borderBottom: "2px solid transparent",
              }}
            >
              {m.nhan}
            </Link>
          ))}
        </nav>
      </header>

      <main className="khung" style={{ padding: "26px 20px 80px" }}>
        {children}
      </main>
    </>
  );
}
