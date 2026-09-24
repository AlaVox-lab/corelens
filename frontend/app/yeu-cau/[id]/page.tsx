// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn “Chi tiết hồ sơ”.
//
// Phần đáng nói nhất là DÒNG THỜI GIAN. Nó không phải đồ trang trí: nó là bản
// `event_log` của chính hồ sơ này, hiện ra nguyên vẹn cho người gửi đọc.
//
// Hầu hết hệ thống quản lý yêu cầu chỉ cho người gửi thấy trạng thái hiện tại, và
// toàn bộ đường đi nằm trong phần quản trị. Hệ quả là khi hồ sơ đi lòng vòng — phòng
// ban A trả lại, điều phối viên chuyển sang phòng ban B — người gửi chỉ thấy con số
// ngày chờ tăng lên mà không hiểu vì sao. Họ gọi điện hỏi, và cuộc gọi đó không để
// lại dấu vết nào trong dữ liệu.
//
// Ở đây thì ngược lại: mỗi lần quay lui hiện ra thành một mốc có ghi lý do. Cùng một
// dữ liệu đó, tầng `D` dùng để khai phá quy trình thực tế và chỉ ra điểm nghẽn —
// nghĩa là thứ người dùng đọc để yên tâm và thứ hệ thống đọc để tự cải tiến là **một**.
// Xem CLAUDE.md mục 4.1.

import Link from "next/link";
import { notFound } from "next/navigation";

import type { NguonLuaChon } from "@/components/bang-thao-tac";
import {
  DongThoiGian,
  danhDauQuayLui,
  soLanDoiTrangThai,
} from "@/components/dong-thoi-gian";
import { NhanTrangThai } from "@/components/nhan-trang-thai";
import { ThaoTacHoSo } from "@/app/yeu-cau/[id]/thao-tac-ho-so";
import { goiDichVu } from "@/lib/api";
import { ngayGio } from "@/lib/dinh-dang";
import type { HoSoChiTiet, NhanCoMa } from "@/lib/kieu";
import { daTroiQua, docDongHo } from "@/lib/sla";
import { CHU_GIAI_NHOM, bienHoMau, trinhBayTrangThai } from "@/lib/trang-thai";
import { kieuTruong, type NguonDanhMuc } from "@/lib/truong";

export const dynamic = "force-dynamic";

/**
 * Danh mục cho ô chọn của các thao tác đang đi được — ở cổng này chỉ có ô loại yêu cầu
 * của thao tác sửa nội dung (#127). Nạp theo `fields` giống buồng lái phòng ban: hồ sơ
 * không có thao tác sửa thì trang không gọi thêm lần nào.
 */
async function danhMucCan(
  ho_so: HoSoChiTiet,
): Promise<Partial<Record<NguonDanhMuc, NguonLuaChon>>> {
  const can = new Set<NguonDanhMuc>();
  for (const canh of ho_so.allowed_transitions) {
    for (const truong of canh.fields) {
      const nguon = kieuTruong(truong).nguon;
      if (nguon) can.add(nguon);
    }
  }
  const cap = await Promise.all(
    [...can].map(async (nguon) => {
      const ds = await goiDichVu<NhanCoMa[]>(`/${nguon}`);
      const luaChon: NguonLuaChon = ds
        ? ds.map(({ code, label }) => ({ code, label }))
        : { loi: "Không nạp được danh mục." };
      return [nguon, luaChon] as const;
    }),
  );
  return Object.fromEntries(cap);
}

function O({
  tua,
  chinh,
  phu,
  phuCanhBao = false,
}: {
  tua: string;
  chinh: React.ReactNode;
  phu?: string;
  phuCanhBao?: boolean;
}) {
  return (
    <div style={{ display: "grid", gap: "7px", alignContent: "start" }}>
      <span className="tua-muc">{tua}</span>
      <span style={{ fontSize: "15px", fontWeight: 600 }}>{chinh}</span>
      {phu && (
        <span
          style={{
            fontSize: "12.5px",
            color: phuCanhBao ? "var(--f-r-ink)" : "var(--ink-3)",
          }}
        >
          {phu}
        </span>
      )}
    </div>
  );
}

export default async function ChiTietHoSo({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const ho_so = await goiDichVu<HoSoChiTiet>(`/requests/${id}`);

  // Dịch vụ trả 404 cho cả hồ sơ không tồn tại lẫn hồ sơ của người khác — cố ý, để
  // người dò số định danh không xác nhận được hồ sơ nào có thật.
  if (!ho_so) notFound();

  const danhMuc = await danhMucCan(ho_so);
  const bayGio = new Date();
  const dongHo = docDongHo(ho_so, "nguoi-gui");
  const kieu = trinhBayTrangThai(ho_so.state.code);
  const nhomChuGiai = CHU_GIAI_NHOM.find((n) => n.nhom === kieu.nhom);
  const quayLui = danhDauQuayLui(ho_so.history);

  return (
    <>
      <Link href="/yeu-cau" className="nut nut-nho khong-in">
        ← Hồ sơ của tôi
      </Link>

      {/* --- Thẻ đầu trang -------------------------------------------------- */}
      <div className="the" style={{ marginTop: "14px" }}>
        <div style={{ padding: "20px 22px" }}>
          <div
            className="mono"
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "8px 12px",
              alignItems: "center",
              fontSize: "12px",
              color: "var(--ink-3)",
            }}
          >
            {ho_so.code}
            {ho_so.request_type && (
              <span
                style={{
                  fontFamily: "var(--font)",
                  padding: "2px 9px",
                  borderRadius: "999px",
                  background: "var(--surface-3)",
                  border: "1px solid var(--line)",
                  fontSize: "11.5px",
                  color: "var(--ink-2)",
                }}
              >
                {ho_so.request_type.label}
              </span>
            )}
            <span>Gửi {ngayGio(ho_so.created_at)}</span>
          </div>

          <h1
            style={{
              margin: "9px 0 0",
              fontSize: "clamp(20px,3.2vw,26px)",
              fontWeight: 600,
              letterSpacing: "-.02em",
              lineHeight: 1.3,
            }}
          >
            {ho_so.title}
          </h1>

          <div
            style={{
              marginTop: "18px",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit,minmax(190px,1fr))",
              gap: "16px",
            }}
          >
            <O
              tua="Trạng thái hiện tại"
              chinh={
                <NhanTrangThai ma={ho_so.state.code} nhan={ho_so.state.label} to />
              }
              phu={`Đổi lần cuối ${ngayGio(ho_so.updated_at)}`}
            />
            {/* Cố ý KHÔNG hiện `assignee_id`. Nó là định danh `sub` của Keycloak —
                một chuỗi UUID — và dịch vụ chưa có đường tra ngược ra tên người. Đưa
                một dãy ký tự vô nghĩa lên màn hình thì tệ hơn là không đưa gì. Tên
                người xử lý sẽ có khi dịch vụ biết tra danh bạ; tới lúc đó thay dòng
                dưới đây. */}
            <O
              tua="Đang giữ hồ sơ"
              chinh={ho_so.department?.label ?? "Chưa định tuyến"}
              phu={
                ho_so.assignee_id
                  ? "Đã có người được phân công xử lý"
                  : "Chưa phân công người xử lý cụ thể"
              }
            />
            <O
              tua="Đã trôi qua"
              chinh={daTroiQua(ho_so, bayGio)}
              phu={dongHo.cau}
              phuCanhBao={dongHo.canhBao}
            />
            <O
              tua="Số lần đổi trạng thái"
              chinh={`${soLanDoiTrangThai(ho_so.history)}`}
              phu={
                quayLui.size > 0
                  ? `${quayLui.size} lần quay lui`
                  : "Hồ sơ đi thẳng, chưa quay lui lần nào"
              }
              phuCanhBao={quayLui.size > 0}
            />
          </div>
        </div>

        {nhomChuGiai && (
          <div
            style={{
              ...bienHoMau(kieu.ho),
              display: "flex",
              gap: "12px",
              padding: "15px 22px",
              background: "var(--ho-bg)",
              borderTop: "1px solid var(--ho-line)",
            }}
          >
            <span
              aria-hidden="true"
              style={{
                flex: "0 0 auto",
                width: "24px",
                height: "24px",
                borderRadius: "50%",
                background: "var(--ho-solid)",
                color: "var(--ho-on)",
                display: "grid",
                placeItems: "center",
                fontSize: "12px",
                lineHeight: 1,
              }}
            >
              {kieu.dau}
            </span>
            <span style={{ display: "grid", gap: "4px", minWidth: 0 }}>
              <span style={{ fontSize: "13.5px", fontWeight: 600 }}>
                {nhomChuGiai.tieuDe}
              </span>
              <span style={{ fontSize: "13px", color: "var(--ink-2)", lineHeight: 1.6 }}>
                {nhomChuGiai.moTa}
              </span>
            </span>
          </div>
        )}
      </div>

      {ho_so.description && (
        <div className="the" style={{ marginTop: "24px", padding: "18px 22px" }}>
          <h2 className="tua-muc" style={{ margin: 0 }}>
            Nội dung yêu cầu
          </h2>
          <p
            style={{
              margin: "9px 0 0",
              fontSize: "14px",
              lineHeight: 1.7,
              whiteSpace: "pre-wrap",
            }}
          >
            {ho_so.description}
          </p>
        </div>
      )}

      <DongThoiGian
        cacSuKien={ho_so.history}
        bayGio={bayGio}
        khiTrong="Hồ sơ vừa được gửi và chưa đổi trạng thái lần nào. Mốc đầu tiên sẽ xuất hiện ở đây ngay khi điều phối viên tiếp nhận."
      />

      {/* --- Thao tác ------------------------------------------------------- */}
      <div className="the khong-in" style={{ marginTop: "24px" }}>
        <div style={{ padding: "17px 20px", display: "grid", gap: "5px", borderBottom: "1px solid var(--line)" }}>
          <h2 style={{ margin: 0, fontSize: "15px", fontWeight: 600 }}>
            Bạn có thể làm gì lúc này
          </h2>
          <p style={{ margin: 0, fontSize: "13px", color: "var(--ink-2)", lineHeight: 1.6, maxWidth: "72ch" }}>
            Danh sách dưới đây do chính bộ quy tắc quy trình sinh ra, dựa trên trạng
            thái hồ sơ và vai trò của bạn. Thao tác nào không có ở đây thì không tồn tại
            đường đi cho nó.
          </p>
        </div>
        <div style={{ padding: "17px 20px" }}>
          {/* Khóa có `updated_at`: sửa nội dung giữ nguyên trạng thái (#127), nên chỉ mã
              trạng thái thì bảng không dựng lại, và bảng sửa vẫn mở sau khi đã lưu. */}
          <ThaoTacHoSo
            key={`${ho_so.state.code}-${ho_so.updated_at}`}
            maHoSo={ho_so.id}
            cacCanh={ho_so.allowed_transitions}
            giaTriDau={{
              title: ho_so.title,
              description: ho_so.description ?? "",
              request_type_code: ho_so.request_type?.code ?? "",
            }}
            danhMuc={danhMuc}
          />
        </div>
      </div>
    </>
  );
}
