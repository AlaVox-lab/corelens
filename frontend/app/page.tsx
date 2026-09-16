// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Trang tạm của bộ khung.
//
// Hai việc: chứng minh cổng gọi được dịch vụ ứng dụng, và chứng minh chuỗi định danh
// chạy thông. Không có nghiệp vụ nào ở đây — cổng gửi yêu cầu thuộc #44, buồng lái
// vận hành thuộc #45.

import { goiDichVu, type DanhTinh } from "@/lib/api";
import { layPhien } from "@/lib/session";

const DIA_CHI_DICH_VU =
  process.env.BACKEND_INTERNAL_URL ?? "http://backend:8000";

type SucKhoe = {
  status?: string;
  database?: string;
  version?: string;
  active_rule_set_states?: number;
  detail?: string;
};

async function docSucKhoe(): Promise<SucKhoe | null> {
  try {
    const phanHoi = await fetch(`${DIA_CHI_DICH_VU}/health`, {
      cache: "no-store",
    });
    return (await phanHoi.json()) as SucKhoe;
  } catch {
    return null;
  }
}

const oDay = {
  the: {
    marginTop: "2rem",
    border: "1px solid var(--vien)",
    borderRadius: "0.5rem",
    padding: "1.25rem 1.5rem",
  },
  nhan: { color: "var(--chu-nhat)" },
  nut: {
    display: "inline-block",
    marginTop: "1rem",
    padding: "0.5rem 1.1rem",
    borderRadius: "0.375rem",
    background: "var(--nhan-manh)",
    color: "#fff",
    textDecoration: "none",
    fontSize: "0.95rem",
  },
} as const;

export default async function TrangChu() {
  const [sucKhoe, phien] = await Promise.all([docSucKhoe(), layPhien()]);
  const danhTinh = phien ? await goiDichVu<DanhTinh>("/me") : null;
  const dungHet = sucKhoe?.status === "ok";

  return (
    <main style={{ maxWidth: "44rem", margin: "0 auto", padding: "4rem 1.5rem" }}>
      <h1 style={{ fontSize: "1.75rem", margin: 0 }}>DX-OS Lab</h1>
      <p style={{ color: "var(--chu-nhat)", marginTop: "0.5rem" }}>
        Cổng vận hành yêu cầu nội bộ — Hệ điều hành Doanh nghiệp số
      </p>

      {/* --- Danh tính --- */}
      <section style={oDay.the}>
        <h2 style={{ fontSize: "1rem", margin: 0 }}>Danh tính</h2>

        {danhTinh ? (
          <>
            <dl
              style={{
                display: "grid",
                gridTemplateColumns: "auto 1fr",
                gap: "0.5rem 1.5rem",
                margin: "1rem 0 0",
              }}
            >
              <dt style={oDay.nhan}>Người dùng</dt>
              <dd style={{ margin: 0 }}>
                {danhTinh.name ?? danhTinh.username}{" "}
                <span style={oDay.nhan}>({danhTinh.username})</span>
              </dd>

              <dt style={oDay.nhan}>Vai trò</dt>
              <dd style={{ margin: 0 }}>
                {danhTinh.roles.length ? danhTinh.roles.join(", ") : "chưa gán"}
              </dd>

              <dt style={oDay.nhan}>Phòng ban</dt>
              <dd style={{ margin: 0 }}>
                {danhTinh.departments.length
                  ? danhTinh.departments.join(", ")
                  : "không thuộc phòng nào"}
              </dd>
            </dl>
            <a href="/api/auth/logout" style={{ ...oDay.nut, background: "transparent", color: "var(--nhan-manh)", border: "1px solid var(--vien)" }}>
              Đăng xuất
            </a>
          </>
        ) : (
          <>
            <p style={{ ...oDay.nhan, marginTop: "0.75rem", marginBottom: 0 }}>
              {phien
                ? "Phiên đã hết hạn hoặc dịch vụ ứng dụng không phản hồi."
                : "Chưa đăng nhập."}
            </p>
            <a href="/api/auth/login" style={oDay.nut}>
              Đăng nhập bằng Keycloak
            </a>
          </>
        )}
      </section>

      {/* --- Trạng thái hệ thống --- */}
      <section style={oDay.the}>
        <h2 style={{ fontSize: "1rem", margin: 0 }}>Trạng thái hệ thống</h2>

        <dl
          style={{
            display: "grid",
            gridTemplateColumns: "auto 1fr",
            gap: "0.5rem 1.5rem",
            margin: "1rem 0 0",
          }}
        >
          <dt style={oDay.nhan}>Cổng người dùng</dt>
          <dd style={{ margin: 0, color: "var(--tot)" }}>đang chạy</dd>

          <dt style={oDay.nhan}>Dịch vụ ứng dụng</dt>
          <dd style={{ margin: 0, color: sucKhoe ? "var(--tot)" : "var(--hong)" }}>
            {sucKhoe ? `đang chạy · v${sucKhoe.version ?? "?"}` : "không tới được"}
          </dd>

          <dt style={oDay.nhan}>Cơ sở dữ liệu</dt>
          <dd
            style={{
              margin: 0,
              color: sucKhoe?.database === "ok" ? "var(--tot)" : "var(--hong)",
            }}
          >
            {sucKhoe?.database === "ok" ? "đã kết nối" : "chưa kết nối"}
          </dd>

          <dt style={oDay.nhan}>Bộ quy tắc quy trình</dt>
          <dd style={{ margin: 0, color: dungHet ? "var(--tot)" : "var(--hong)" }}>
            {sucKhoe?.active_rule_set_states
              ? `đã nạp · ${sucKhoe.active_rule_set_states} trạng thái`
              : "chưa nạp"}
          </dd>
        </dl>

        {!dungHet && (
          <p
            style={{
              marginTop: "1.25rem",
              marginBottom: 0,
              ...oDay.nhan,
              fontSize: "0.9rem",
            }}
          >
            {sucKhoe?.detail ??
              "Kiểm tra dịch vụ ứng dụng bằng docker compose logs backend."}
          </p>
        )}
      </section>

      <p style={{ marginTop: "2rem", ...oDay.nhan, fontSize: "0.9rem" }}>
        Đây là bộ khung. Giao diện gửi yêu cầu và buồng lái vận hành đang được xây
        dựng.
      </p>
    </main>
  );
}
