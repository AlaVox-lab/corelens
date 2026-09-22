// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khung trang dùng chung cho mọi không gian làm việc: cổng người gửi (#44) và buồng
// lái điều phối (#82).
//
// Hai việc đặt ở đây chứ không lặp lại trong từng trang:
//
//   Cửa đăng nhập — chưa đăng nhập thì không trang nào có gì để hiển thị.
//   Cửa không gian — trang thuộc buồng lái mà người dùng không vào được thì báo rõ,
//                    thay vì để từng điểm cuối trả 403 thành một trang trống.
//
// Thanh điều hướng dựng từ `workspaces` mà `/me` trả về. Khung này không biết tên vai
// trò nào: dịch vụ quyết ai vào được đâu, giao diện chỉ vẽ theo.

import Link from "next/link";
import { Suspense } from "react";

import { DieuHuong } from "@/components/dieu-huong";
import { NutDangNhap } from "@/components/nut-dang-nhap";
import { goiDichVu, type DanhTinh } from "@/lib/api";
import { loiVaoCua } from "@/lib/khong-gian";

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
      {/* Suspense vì nút đọc tham số trên địa chỉ phía trình duyệt */}
      <Suspense>
        <NutDangNhap>Đăng nhập</NutDangNhap>
      </Suspense>
    </main>
  );
}

function KhongVaoDuoc() {
  return (
    <div className="the" style={{ padding: "36px 24px", textAlign: "center" }}>
      <p style={{ margin: 0, fontSize: "15px", fontWeight: 600 }}>
        Tài khoản này không mở được khu vực này
      </p>
      <p style={{ margin: "7px 0 0", fontSize: "13.5px", color: "var(--ink-2)", lineHeight: 1.6 }}>
        Quyền vào từng khu vực do quản trị viên cấp theo vai trò. Nếu bạn cần làm việc ở
        đây, hãy nhờ quản trị hệ thống thêm vai trò cho tài khoản của bạn.
      </p>
    </div>
  );
}

export async function KhungLamViec({
  children,
  canKhongGian,
}: Readonly<{
  children: React.ReactNode;
  /** Không gian mà trang này thuộc về. Người dùng không vào được thì hiện lời báo. */
  canKhongGian: string;
}>) {
  const danhTinh = await goiDichVu<DanhTinh>("/me");

  if (!danhTinh) return <MoiDangNhap />;

  const ten = danhTinh.name ?? danhTinh.username ?? danhTinh.id;
  const khongGian = danhTinh.workspaces ?? ["portal"];
  const cacMuc = loiVaoCua(khongGian);

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
            href="/"
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

        <DieuHuong cacMuc={cacMuc} />
      </header>

      <main className="khung" style={{ padding: "26px 20px 80px" }}>
        {khongGian.includes(canKhongGian) ? children : <KhongVaoDuoc />}
      </main>
    </>
  );
}
