// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Hàng đợi của buồng lái phòng ban (#83).
//
// Câu hỏi màn này trả lời: **hồ sơ nào của phòng sắp trễ, hay đã trễ?** Khác hàng đợi
// điều phối — xếp theo thời gian chờ — vì ở đây đồng hồ SLA đang chạy, nên thời hạn còn
// lại mới là con số cần nhìn. Thứ tự do dịch vụ xếp: quá hạn lên đầu, rồi gần hạn nhất.
//
// Cả phòng nhìn chung một hàng đợi — trưởng phòng thấy hồ sơ đang xử lý, người xử lý
// thấy hồ sơ đang chờ nhận — nhưng nút "Giao cho tôi" thu về đúng phần việc của mình.
// Nút lọc trạng thái dựng từ `groups` mà dịch vụ trả về; tệp này không liệt kê trạng
// thái nào.

import Link from "next/link";

import { NhanTrangThai } from "@/components/nhan-trang-thai";
import { NutLoc } from "@/components/nut-loc";
import { goiDichVu } from "@/lib/api";
import type { HangDoiPhongBan, MucHangDoiPhongBan } from "@/lib/kieu";
import { docDongHo } from "@/lib/sla";

export const dynamic = "force-dynamic";

function diaChi(state?: string, mine?: boolean): string {
  const q = new URLSearchParams();
  if (state) q.set("state", state);
  if (mine) q.set("mine", "1");
  const chuoi = q.toString();
  return chuoi ? `/phong-ban?${chuoi}` : "/phong-ban";
}

function nguoiXuLy(muc: MucHangDoiPhongBan): string {
  if (muc.assigned_to_me) return "Giao cho bạn";
  if (muc.assignee_id) return `Giao cho ${muc.assignee_label ?? "một người trong phòng"}`;
  return "Chưa giao cho ai";
}

function Dong({ muc, dauTien }: { muc: MucHangDoiPhongBan; dauTien: boolean }) {
  const dongHo = docDongHo(muc);
  return (
    <Link
      href={`/phong-ban/${muc.id}`}
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "10px 16px",
        alignItems: "center",
        padding: "14px 16px",
        borderTop: dauTien ? "none" : "1px solid var(--line)",
        // Hồ sơ quá hạn mang một vạch đỏ ở mép trái. Không chỉ dựa vào màu: câu bên
        // phải nói rõ "Quá hạn …", để người không phân biệt được màu vẫn đọc được.
        boxShadow: muc.sla_overdue ? "inset 3px 0 0 var(--f-r-ink)" : "none",
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
          {muc.request_type && (
            <span
              style={{
                fontFamily: "var(--font)",
                padding: "1px 7px",
                borderRadius: "999px",
                background: "var(--surface-3)",
                border: "1px solid var(--line-2)",
                fontSize: "11px",
                color: "var(--ink-2)",
              }}
            >
              {muc.request_type.label}
            </span>
          )}
        </span>
        <span style={{ fontSize: "14.5px", fontWeight: 600, lineHeight: 1.4 }}>
          {muc.title}
        </span>
        <span style={{ fontSize: "12.5px", color: "var(--ink-3)" }}>
          {muc.requester_label ?? "Không rõ người gửi"}
          {muc.priority && <> · Ưu tiên {muc.priority.label.toLowerCase()}</>}
          {" · "}
          <span style={{ color: muc.assigned_to_me ? "var(--ink)" : undefined, fontWeight: muc.assigned_to_me ? 600 : undefined }}>
            {nguoiXuLy(muc)}
          </span>
        </span>
      </span>

      <span style={{ flex: "0 0 auto" }}>
        <NhanTrangThai ma={muc.state.code} nhan={muc.state.label} />
      </span>

      <span
        style={{
          flex: "0 0 auto",
          minWidth: "150px",
          textAlign: "right",
          fontSize: "12.5px",
          fontWeight: dongHo.canhBao ? 600 : 500,
          color: dongHo.canhBao ? "var(--f-r-ink)" : "var(--ink-2)",
        }}
      >
        {dongHo.cau}
      </span>
    </Link>
  );
}

export default async function HangDoiPhongBan({
  searchParams,
}: {
  searchParams: Promise<{ state?: string; mine?: string }>;
}) {
  const { state, mine } = await searchParams;
  const cuaToi = mine === "1";
  // Bộ lọc "của tôi" gửi sang dịch vụ để số đếm trên nút lọc đi cùng bộ lọc; bộ lọc
  // trạng thái thì lọc ở đây, vì một lần gọi đã đủ số đếm cho mọi nút.
  const tatCa = await goiDichVu<HangDoiPhongBan>(
    cuaToi ? "/department/queue?mine=true" : "/department/queue",
  );
  const cacMuc = (tatCa?.items ?? []).filter((m) => !state || m.state.code === state);
  const tong = tatCa?.items.length ?? 0;
  const soQuaHan = (tatCa?.items ?? []).filter((m) => m.sla_overdue).length;
  const tenPhong = tatCa?.departments.map((p) => p.label).join(" · ");

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
        {tenPhong ? `Hàng đợi phòng ${tenPhong}` : "Hàng đợi phòng ban"}
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
        {tong === 0
          ? cuaToi
            ? "Chưa có hồ sơ nào đang giao cho bạn."
            : "Hồ sơ điều phối viên chuyển về phòng sẽ xuất hiện ở đây để nhận và giao người xử lý."
          : `${tong} hồ sơ${soQuaHan > 0 ? `, ${soQuaHan} đã quá hạn` : ""}. Hồ sơ quá hạn nằm trên cùng, rồi tới hồ sơ gần hạn nhất.`}
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
            <NutLoc href={diaChi(undefined, cuaToi)} nhan="Tất cả" so={tong} chon={!state} />
            {tatCa.groups.map((g) => (
              <NutLoc
                key={g.code}
                href={diaChi(g.code, cuaToi)}
                nhan={g.label}
                so={g.count}
                chon={state === g.code}
              />
            ))}
            <Link
              href={diaChi(state, !cuaToi)}
              aria-pressed={cuaToi}
              className="nut nut-nho"
              data-loai={cuaToi ? "chinh" : undefined}
              style={{ marginLeft: "auto" }}
            >
              {cuaToi ? "✓ Giao cho tôi" : "Giao cho tôi"}
            </Link>
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
                  : "Hàng đợi trống — phòng không có hồ sơ nào đang chờ."}
              </p>
            ) : (
              cacMuc.map((m, i) => <Dong key={m.id} muc={m} dauTien={i === 0} />)
            )}
          </div>
        </>
      )}
    </>
  );
}
