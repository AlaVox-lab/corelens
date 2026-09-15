// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Trang tạm của bộ khung.
//
// Nhiệm vụ duy nhất: chứng minh cổng người dùng gọi được tới dịch vụ ứng dụng, và
// dịch vụ đó nối được tới cơ sở dữ liệu. Không có nghiệp vụ nào ở đây — cổng gửi
// yêu cầu thuộc #44, buồng lái vận hành thuộc #45.

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
    // Dịch vụ chưa lên hoặc không tới được. Trả null để trang vẫn hiện, thay vì
    // đổ lỗi 500 — người dựng cụm cần nhìn thấy cái gì đó để biết đang thiếu gì.
    return null;
  }
}

export default async function TrangChu() {
  const sucKhoe = await docSucKhoe();
  const dungHet = sucKhoe?.status === "ok";

  return (
    <main
      style={{
        maxWidth: "44rem",
        margin: "0 auto",
        padding: "4rem 1.5rem",
      }}
    >
      <h1 style={{ fontSize: "1.75rem", margin: 0 }}>DX-OS Lab</h1>
      <p style={{ color: "var(--chu-nhat)", marginTop: "0.5rem" }}>
        Cổng vận hành yêu cầu nội bộ — Hệ điều hành Doanh nghiệp số
      </p>

      <section
        style={{
          marginTop: "2.5rem",
          border: "1px solid var(--vien)",
          borderRadius: "0.5rem",
          padding: "1.25rem 1.5rem",
        }}
      >
        <h2 style={{ fontSize: "1rem", margin: 0 }}>Trạng thái hệ thống</h2>

        <dl
          style={{
            display: "grid",
            gridTemplateColumns: "auto 1fr",
            gap: "0.5rem 1.5rem",
            margin: "1rem 0 0",
          }}
        >
          <dt style={{ color: "var(--chu-nhat)" }}>Cổng người dùng</dt>
          <dd style={{ margin: 0, color: "var(--tot)" }}>đang chạy</dd>

          <dt style={{ color: "var(--chu-nhat)" }}>Dịch vụ ứng dụng</dt>
          <dd
            style={{ margin: 0, color: sucKhoe ? "var(--tot)" : "var(--hong)" }}
          >
            {sucKhoe ? `đang chạy · v${sucKhoe.version ?? "?"}` : "không tới được"}
          </dd>

          <dt style={{ color: "var(--chu-nhat)" }}>Cơ sở dữ liệu</dt>
          <dd
            style={{
              margin: 0,
              color: sucKhoe?.database === "ok" ? "var(--tot)" : "var(--hong)",
            }}
          >
            {sucKhoe?.database === "ok" ? "đã kết nối" : "chưa kết nối"}
          </dd>

          <dt style={{ color: "var(--chu-nhat)" }}>Bộ quy tắc quy trình</dt>
          <dd
            style={{
              margin: 0,
              color: dungHet ? "var(--tot)" : "var(--hong)",
            }}
          >
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
              color: "var(--chu-nhat)",
              fontSize: "0.9rem",
            }}
          >
            {sucKhoe?.detail ??
              "Kiểm tra dịch vụ ứng dụng bằng docker compose logs backend."}
          </p>
        )}
      </section>

      <p
        style={{
          marginTop: "2rem",
          color: "var(--chu-nhat)",
          fontSize: "0.9rem",
        }}
      >
        Đây là bộ khung. Giao diện gửi yêu cầu và buồng lái vận hành đang được xây
        dựng.
      </p>
    </main>
  );
}
