// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn hàng đợi của điều phối viên (#82).
//
// Câu hỏi màn này trả lời: **hồ sơ nào đã chờ lâu nhất?** Hàng đợi xếp theo thời gian
// chờ ở trạng thái hiện tại, lâu nhất lên đầu — không theo hạn SLA, vì đồng hồ SLA
// chưa chạy ở những trạng thái này. Nó chỉ bắt đầu khi phòng ban nhận việc.
//
// Nút lọc dựng từ `groups` mà dịch vụ trả về. Trạng thái nào vào hàng đợi là do bộ quy
// tắc quyết — trạng thái nào vai trò điều phối có cạnh đi ra — nên tệp này không liệt
// kê trạng thái nào cả.

import Link from "next/link";

import { DauLoiNhan } from "@/components/dau-loi-nhan";
import { NhanTrangThai } from "@/components/nhan-trang-thai";
import { NutLoc } from "@/components/nut-loc";
import { goiDichVu } from "@/lib/api";
import { thoiLuong } from "@/lib/dinh-dang";
import type { HangDoi, MucHangDoi } from "@/lib/kieu";

export const dynamic = "force-dynamic";

function giayCho(muc: MucHangDoi, bayGio: Date): number {
  return Math.max(0, (bayGio.getTime() - new Date(muc.state_entered_at).getTime()) / 1000);
}

function Dong({ muc, bayGio, dauTien }: { muc: MucHangDoi; bayGio: Date; dauTien: boolean }) {
  return (
    <Link
      href={`/dieu-phoi/${muc.id}`}
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "10px 16px",
        alignItems: "center",
        padding: "14px 16px",
        borderTop: dauTien ? "none" : "1px solid var(--line)",
        color: "inherit",
        textDecoration: "none",
      }}
    >
      <span style={{ flex: "1 1 300px", minWidth: 0, display: "grid", gap: "4px" }}>
        <span
          className="mono"
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "4px 10px",
            alignItems: "center",
            fontSize: "11.5px",
            color: "var(--ink-3)",
          }}
        >
          {muc.code}
          <span
            style={{
              fontFamily: "var(--font)",
              padding: "1px 7px",
              borderRadius: "999px",
              background: "var(--surface-3)",
              border: `1px ${muc.request_type ? "solid" : "dashed"} var(--line-2)`,
              fontSize: "11px",
              color: muc.request_type ? "var(--ink-2)" : "var(--ink-3)",
            }}
          >
            {muc.request_type?.label ?? "Chưa rõ loại"}
          </span>
          <DauLoiNhan hoSo={muc} gocNhin="nhan-vien" />
        </span>
        <span style={{ fontSize: "14.5px", fontWeight: 600, lineHeight: 1.4 }}>
          {muc.title}
        </span>
        <span style={{ fontSize: "12.5px", color: "var(--ink-3)" }}>
          {muc.requester_label ?? "Không rõ người gửi"}
          {muc.priority && <> · Ưu tiên {muc.priority.label.toLowerCase()}</>}
          {muc.department && <> · {muc.department.label}</>}
        </span>
      </span>

      <span style={{ flex: "0 0 auto" }}>
        <NhanTrangThai ma={muc.state.code} nhan={muc.state.label} />
      </span>

      <span
        style={{
          flex: "0 0 auto",
          minWidth: "108px",
          display: "grid",
          gap: "1px",
          textAlign: "right",
        }}
      >
        <span
          className="mono"
          style={{ fontSize: "13px", fontWeight: 500, whiteSpace: "nowrap" }}
        >
          {thoiLuong(giayCho(muc, bayGio))}
        </span>
        <span style={{ fontSize: "11.5px", color: "var(--ink-3)" }}>đã chờ</span>
      </span>
    </Link>
  );
}

export default async function HangDoiDieuPhoi({
  searchParams,
}: {
  searchParams: Promise<{ state?: string }>;
}) {
  const { state } = await searchParams;
  const tatCa = await goiDichVu<HangDoi>("/coordination/queue");
  // Lọc lại phía máy chủ Next.js thay vì gọi lần hai kèm `?state=`: một lần gọi đã
  // có đủ số đếm cho mọi nút lọc lẫn danh sách, và hàng đợi ở quy mô này không lớn.
  const cacMuc = (tatCa?.items ?? []).filter((m) => !state || m.state.code === state);
  const tong = tatCa?.items.length ?? 0;
  const bayGio = new Date();

  return (
    <>
      <h1
        style={{
          margin: 0,
          fontSize: "clamp(22px,3.4vw,28px)",
          fontWeight: 600,
          letterSpacing: "-.02em",
          lineHeight: 1.25,
        }}
      >
        Hàng đợi điều phối
      </h1>
      <p
        style={{
          margin: "7px 0 0",
          fontSize: "14.5px",
          color: "var(--ink-2)",
          maxWidth: "68ch",
          lineHeight: 1.6,
        }}
      >
        {tong > 0
          ? `${tong} hồ sơ đang chờ phân loại hoặc chuyển về phòng ban. Hồ sơ chờ lâu nhất nằm trên cùng.`
          : "Hồ sơ gửi lên sẽ xuất hiện ở đây để phân loại và chuyển về phòng ban phụ trách."}
      </p>

      {tatCa === null ? (
        <div className="the" style={{ marginTop: "20px", padding: "24px", textAlign: "center" }}>
          <p style={{ margin: 0, fontSize: "14.5px", fontWeight: 600 }}>
            Chưa nạp được hàng đợi
          </p>
          <p style={{ margin: "6px 0 0", fontSize: "13.5px", color: "var(--ink-2)" }}>
            Dịch vụ ứng dụng không phản hồi. Tải lại trang sau ít phút.
          </p>
        </div>
      ) : (
        <>
          <div
            className="khong-in"
            style={{ marginTop: "18px", display: "flex", flexWrap: "wrap", gap: "7px" }}
          >
            <NutLoc href="/dieu-phoi" nhan="Tất cả" so={tong} chon={!state} />
            {tatCa.groups.map((g) => (
              <NutLoc
                key={g.code}
                href={`/dieu-phoi?state=${encodeURIComponent(g.code)}`}
                nhan={g.label}
                so={g.count}
                chon={state === g.code}
              />
            ))}
          </div>

          <div className="the" style={{ marginTop: "14px" }}>
            {cacMuc.length === 0 ? (
              <p
                style={{
                  margin: 0,
                  padding: "36px 24px",
                  textAlign: "center",
                  fontSize: "14px",
                  color: "var(--ink-2)",
                }}
              >
                {state
                  ? "Không có hồ sơ nào ở trạng thái này."
                  : "Hàng đợi trống — không hồ sơ nào đang chờ điều phối."}
              </p>
            ) : (
              cacMuc.map((m, i) => (
                <Dong key={m.id} muc={m} bayGio={bayGio} dauTien={i === 0} />
              ))
            )}
          </div>
        </>
      )}
    </>
  );
}
