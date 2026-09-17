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

import { NhanTrangThai } from "@/components/nhan-trang-thai";
import { ThaoTacHoSo } from "@/app/yeu-cau/[id]/thao-tac-ho-so";
import { goiDichVu } from "@/lib/api";
import { chiGio, khoaNgay, ngayGio, nhanNgay } from "@/lib/dinh-dang";
import type { HoSoChiTiet, SuKien } from "@/lib/kieu";
import { daTroiQua, docDongHo } from "@/lib/sla";
import { CHU_GIAI_NHOM, bienHoMau, trinhBayTrangThai } from "@/lib/trang-thai";

export const dynamic = "force-dynamic";

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

/**
 * Đếm số lần hồ sơ quay lại một trạng thái đã đi qua.
 *
 * Con số này là dấu hiệu rõ nhất của một quy trình chạy không thẳng, nên nó đáng được
 * gọi tên ngay trên dòng thời gian thay vì để người đọc tự đếm.
 */
function danhDauQuayLui(cacSuKien: SuKien[]): Map<number, string> {
  const daGap = new Map<string, number>();
  const nhan = new Map<number, string>();

  cacSuKien.forEach((e, i) => {
    const lan = (daGap.get(e.to_state) ?? 0) + 1;
    daGap.set(e.to_state, lan);
    if (lan > 1) nhan.set(i, `Quay lui lần ${lan - 1}`);
  });

  return nhan;
}

function MocThoiGian({
  su_kien,
  quayLui,
  cuoiCung,
}: {
  su_kien: SuKien;
  quayLui?: string;
  cuoiCung: boolean;
}) {
  const den = trinhBayTrangThai(su_kien.to_state);
  const tu = trinhBayTrangThai(su_kien.from_state);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "32px minmax(0,1fr)", gap: "0 14px" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <span
          aria-hidden="true"
          style={{
            ...bienHoMau(den.ho),
            width: "30px",
            height: "30px",
            borderRadius: "50%",
            display: "grid",
            placeItems: "center",
            fontSize: "13px",
            lineHeight: 1,
            background: "var(--ho-bg)",
            color: "var(--ho-ink)",
            border: `1px ${su_kien.is_system ? "dashed" : "solid"} var(--ho-line)`,
          }}
        >
          {den.dau}
        </span>
        {!cuoiCung && (
          <span
            style={{
              flex: "1 1 auto",
              width: "2px",
              minHeight: "14px",
              background: "var(--line)",
              marginTop: "6px",
            }}
          />
        )}
      </div>

      <div style={{ paddingBottom: "20px", minWidth: 0 }}>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "baseline",
            gap: "4px 11px",
          }}
        >
          <span className="mono" style={{ fontSize: "12.5px", color: "var(--ink-3)" }}>
            {chiGio(su_kien.timestamp)}
          </span>
          <span
            style={{
              fontSize: "13.5px",
              fontWeight: 600,
              // Tác nhân hệ thống viết khác người thật, để không ai nhầm một hành động
              // tự động thành quyết định của đồng nghiệp.
              fontFamily: su_kien.is_system ? "var(--mono)" : undefined,
              letterSpacing: su_kien.is_system ? ".02em" : undefined,
              color: su_kien.is_system ? "var(--ink-2)" : "var(--ink)",
            }}
          >
            {su_kien.is_system ? su_kien.actor_label.toUpperCase() : su_kien.actor_label}
          </span>
          {su_kien.is_system && (
            <span style={{ fontSize: "12.5px", color: "var(--ink-3)" }}>
              Tự động · không phải người
            </span>
          )}
        </div>

        <div style={{ marginTop: "5px", fontSize: "15px", fontWeight: 600, lineHeight: 1.45 }}>
          {su_kien.activity_label ?? su_kien.activity}
        </div>

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: "8px",
            marginTop: "9px",
          }}
        >
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              fontSize: "12.5px",
              color: "var(--ink-3)",
            }}
          >
            <span aria-hidden="true">{tu.dau}</span>
            {su_kien.from_state_label}
          </span>
          <span className="mono" style={{ fontSize: "13px", color: "var(--ink-3)" }}>
            →
          </span>
          <NhanTrangThai ma={su_kien.to_state} nhan={su_kien.to_state_label} />
          {quayLui && (
            <span
              className="mono"
              style={{
                ...bienHoMau("o"),
                fontSize: "11px",
                padding: "3px 8px",
                borderRadius: "999px",
                background: "var(--ho-bg)",
                border: "1px dashed var(--ho-line)",
                color: "var(--ho-ink)",
              }}
            >
              {quayLui}
            </span>
          )}
        </div>

        {su_kien.note && (
          <div
            style={{
              marginTop: "9px",
              padding: "10px 12px",
              borderRadius: "9px",
              background: "var(--surface-2)",
              border: "1px solid var(--line)",
            }}
          >
            <span className="tua-muc">Lý do</span>
            <span
              style={{
                display: "block",
                marginTop: "4px",
                fontSize: "13px",
                lineHeight: 1.65,
                whiteSpace: "pre-wrap",
              }}
            >
              {su_kien.note}
            </span>
          </div>
        )}
      </div>
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

  const bayGio = new Date();
  const dongHo = docDongHo(ho_so);
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
              chinh={`${ho_so.history.length}`}
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

      {/* --- Dòng thời gian ------------------------------------------------- */}
      <div
        style={{
          marginTop: "24px",
          display: "flex",
          flexWrap: "wrap",
          gap: "12px 18px",
          alignItems: "flex-end",
          justifyContent: "space-between",
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: "18px", fontWeight: 600, letterSpacing: "-.01em" }}>
            Dòng thời gian hồ sơ
          </h2>
          <p className="mono" style={{ margin: "6px 0 0", fontSize: "12px", color: "var(--ink-3)" }}>
            {ho_so.history.length} mốc · {quayLui.size} lần quay lui
          </p>
        </div>
      </div>

      <div className="the" style={{ marginTop: "14px", padding: "20px 20px 4px" }}>
        {ho_so.history.length === 0 ? (
          <p style={{ margin: "0 0 16px", fontSize: "13.5px", color: "var(--ink-2)", lineHeight: 1.6 }}>
            Hồ sơ vừa được gửi và chưa đổi trạng thái lần nào. Mốc đầu tiên sẽ xuất hiện
            ở đây ngay khi điều phối viên tiếp nhận.
          </p>
        ) : (
          ho_so.history.map((e, i) => {
            const ngayMoi =
              i === 0 || khoaNgay(e.timestamp) !== khoaNgay(ho_so.history[i - 1].timestamp);

            return (
              <div key={`${e.timestamp}-${i}`}>
                {ngayMoi && (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                      margin: i === 0 ? "0 0 14px" : "6px 0 14px",
                    }}
                  >
                    <span className="mono tua-muc" style={{ whiteSpace: "nowrap" }}>
                      {nhanNgay(e.timestamp, bayGio)}
                    </span>
                    <span style={{ flex: "1 1 auto", height: "1px", background: "var(--line)" }} />
                  </div>
                )}
                <MocThoiGian
                  su_kien={e}
                  quayLui={quayLui.get(i)}
                  cuoiCung={i === ho_so.history.length - 1}
                />
              </div>
            );
          })
        )}
      </div>

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
          <ThaoTacHoSo
            key={ho_so.state.code}
            maHoSo={ho_so.id}
            cacCanh={ho_so.allowed_transitions}
          />
        </div>
      </div>
    </>
  );
}
