// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Trang chủ — nơi mọi người dùng đến đầu tiên, và nơi đăng nhập xong quay về.
//
// Hai việc:
//
//   Lối vào — đã đăng nhập thì dẫn thẳng tới từng không gian làm việc, dựng từ
//             `workspaces` của `/me`. Người gửi thấy cổng gửi yêu cầu; điều phối viên
//             thấy thêm buồng lái. Trang này không biết tên vai trò nào.
//
//   Trạng thái hệ thống — README hứa "mở trang chủ là biết cụm có khỏe không". Hiện cả
//             khi chưa đăng nhập, vì đó là lúc người dựng lại hệ thống từ mã nguồn cần
//             nó nhất: trước khi đăng nhập, họ cần biết cụm đã lên đủ chưa.
//
// Trang này từng là bộ khung của #62, dùng bộ biến màu cũ. #44 thay bộ biến màu mà
// không soát tới đây, nên từ #44 tới #82 trang chủ mất hết màu và viền — ghi lại để
// lần đổi token sau nhớ soát mọi trang, không chỉ trang đang làm.

import Link from "next/link";

import { KhungLamViec } from "@/components/khung-lam-viec";
import { goiDichVu, type DanhTinh } from "@/lib/api";
import { loiVaoCua } from "@/lib/khong-gian";
import { bienHoMau } from "@/lib/trang-thai";

export const dynamic = "force-dynamic";

const DIA_CHI_DICH_VU = process.env.BACKEND_INTERNAL_URL ?? "http://backend:8000";

type SucKhoe = {
  status?: string;
  database?: string;
  version?: string;
  active_rule_set_states?: number;
  detail?: string;
};

async function docSucKhoe(): Promise<SucKhoe | null> {
  try {
    const phanHoi = await fetch(`${DIA_CHI_DICH_VU}/health`, { cache: "no-store" });
    return (await phanHoi.json()) as SucKhoe;
  } catch {
    return null;
  }
}

function DongTrangThai({ nhan, tot, giaTri }: { nhan: string; tot: boolean; giaTri: string }) {
  return (
    <div
      style={{
        ...bienHoMau(tot ? "g" : "r"),
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: "6px 14px",
        padding: "11px 17px",
        borderTop: "1px solid var(--line)",
      }}
    >
      <span style={{ flex: "1 1 170px", fontSize: "13.5px", color: "var(--ink-2)" }}>{nhan}</span>
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "8px",
          fontSize: "13.5px",
          fontWeight: 600,
          color: "var(--ho-ink)",
        }}
      >
        {/* Dấu hiệu chữ đi kèm màu, cùng lý do với nhãn trạng thái hồ sơ: bản in đen
            trắng và người không phân biệt được màu vẫn đọc được. */}
        <span aria-hidden="true">{tot ? "✓" : "✕"}</span>
        {giaTri}
      </span>
    </div>
  );
}

function TheTrangThai({ sucKhoe }: { sucKhoe: SucKhoe | null }) {
  const dungHet = sucKhoe?.status === "ok";

  return (
    <section className="the" style={{ marginTop: "28px" }}>
      <div style={{ padding: "14px 17px" }}>
        <h2 style={{ margin: 0, fontSize: "14.5px", fontWeight: 600 }}>Trạng thái hệ thống</h2>
      </div>
      <DongTrangThai nhan="Cổng người dùng" tot giaTri="đang chạy" />
      <DongTrangThai
        nhan="Dịch vụ ứng dụng"
        tot={Boolean(sucKhoe)}
        giaTri={sucKhoe ? `đang chạy · v${sucKhoe.version ?? "?"}` : "không tới được"}
      />
      <DongTrangThai
        nhan="Cơ sở dữ liệu"
        tot={sucKhoe?.database === "ok"}
        giaTri={sucKhoe?.database === "ok" ? "đã kết nối" : "chưa kết nối"}
      />
      <DongTrangThai
        nhan="Bộ quy tắc quy trình"
        tot={dungHet && Boolean(sucKhoe?.active_rule_set_states)}
        giaTri={
          sucKhoe?.active_rule_set_states
            ? `đã nạp · ${sucKhoe.active_rule_set_states} trạng thái`
            : "chưa nạp"
        }
      />
      {!dungHet && (
        <p
          style={{
            margin: 0,
            padding: "12px 17px",
            borderTop: "1px solid var(--line)",
            background: "var(--surface-2)",
            fontSize: "12.5px",
            color: "var(--ink-3)",
            lineHeight: 1.6,
          }}
        >
          {sucKhoe?.detail ?? "Kiểm tra dịch vụ ứng dụng bằng docker compose logs backend."}
        </p>
      )}
    </section>
  );
}

function ChuaDangNhap({ sucKhoe }: { sucKhoe: SucKhoe | null }) {
  return (
    <main className="khung" style={{ padding: "72px 20px 80px", maxWidth: "44rem" }}>
      <span
        className="mono"
        style={{
          width: "40px",
          height: "40px",
          borderRadius: "11px",
          background: "var(--accent)",
          color: "var(--accent-on)",
          display: "grid",
          placeItems: "center",
          fontSize: "14px",
          fontWeight: 500,
        }}
      >
        YC
      </span>
      <h1
        style={{
          margin: "18px 0 0",
          fontSize: "clamp(24px,4vw,32px)",
          fontWeight: 600,
          letterSpacing: "-.02em",
          lineHeight: 1.2,
        }}
      >
        Cổng yêu cầu nội bộ
      </h1>
      <p style={{ margin: "6px 0 0", fontSize: "14px", color: "var(--ink-3)" }}>
        DX-OS Lab · Hệ điều hành Doanh nghiệp số
      </p>
      <p
        style={{
          margin: "18px 0 0",
          fontSize: "15px",
          color: "var(--ink-2)",
          lineHeight: 1.65,
          maxWidth: "58ch",
        }}
      >
        Tiếp nhận và điều phối tập trung mọi yêu cầu nội bộ trong doanh nghiệp. Mỗi hồ sơ
        đi qua một quy trình khai báo bằng dữ liệu, và mọi bước nó đi đều được ghi lại.
      </p>
      <a
        href="/api/auth/login"
        className="nut"
        data-loai="chinh"
        style={{ marginTop: "22px" }}
      >
        Đăng nhập bằng tài khoản công ty
      </a>

      <TheTrangThai sucKhoe={sucKhoe} />
    </main>
  );
}

export default async function TrangChu() {
  const [sucKhoe, danhTinh] = await Promise.all([
    docSucKhoe(),
    goiDichVu<DanhTinh>("/me"),
  ]);

  if (!danhTinh) return <ChuaDangNhap sucKhoe={sucKhoe} />;

  const ten = danhTinh.name ?? danhTinh.username ?? danhTinh.id;
  const cacLoiVao = loiVaoCua(danhTinh.workspaces ?? ["portal"]);

  return (
    <KhungLamViec canKhongGian="portal">
      <h1
        style={{
          margin: 0,
          fontSize: "clamp(22px,3.4vw,28px)",
          fontWeight: 600,
          letterSpacing: "-.02em",
          lineHeight: 1.25,
        }}
      >
        Chào {ten}
      </h1>
      <p style={{ margin: "7px 0 0", fontSize: "14.5px", color: "var(--ink-2)" }}>
        Bạn muốn làm gì hôm nay?
      </p>

      <div
        style={{
          marginTop: "20px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))",
          gap: "12px",
        }}
      >
        {cacLoiVao.map((l) => (
          <Link
            key={l.duongDan}
            href={l.duongDan}
            className="the"
            style={{
              padding: "18px",
              display: "grid",
              gap: "6px",
              alignContent: "start",
              color: "inherit",
              textDecoration: "none",
            }}
          >
            <span style={{ fontSize: "15.5px", fontWeight: 600 }}>{l.nhan} →</span>
            <span style={{ fontSize: "13px", color: "var(--ink-2)", lineHeight: 1.6 }}>
              {l.moTa}
            </span>
          </Link>
        ))}
      </div>

      <TheTrangThai sucKhoe={sucKhoe} />
    </KhungLamViec>
  );
}
