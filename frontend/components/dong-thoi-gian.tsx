// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Dòng thời gian của một hồ sơ — bản `event_log` hiện ra cho người đọc.
//
// Dùng chung cho cổng người gửi (#44) và buồng lái điều phối (#82). Hai nơi phải kể
// cùng một câu chuyện theo cùng một cách: nếu người gửi và điều phối viên nhìn cùng
// một hồ sơ mà thấy hai dòng thời gian trình bày khác nhau, họ sẽ nghĩ dữ liệu khác
// nhau, và cuộc trao đổi giữa hai bên bắt đầu bằng một hiểu lầm.

import { NhanTrangThai } from "@/components/nhan-trang-thai";
import { chiGio, khoaNgay, nhanNgay } from "@/lib/dinh-dang";
import type { SuKien, ThayDoiTruong } from "@/lib/kieu";
import { bienHoMau, trinhBayTrangThai } from "@/lib/trang-thai";
import { kieuTruong } from "@/lib/truong";

/**
 * Một dòng "Loại yêu cầu: Đề xuất mua vật tư → Sự cố thiết bị" (#100).
 *
 * Hồ sơ chỉ mang giá trị hiện tại; lịch sử đổi nằm trong nhật ký, và đây là chỗ nó hiện
 * ra cho người đọc — người gửi thấy loại mình chọn đã được sửa thành gì, trưởng phòng
 * thấy hồ sơ từng qua tay phòng nào, người xử lý nào.
 */
function DongThayDoi({ thayDoi }: { thayDoi: ThayDoiTruong }) {
  const { nhan, dai } = kieuTruong(thayDoi.field);

  // Trường đoạn văn như mô tả (#127): nhãn là chính nội dung, dài tới vài nghìn chữ, nên
  // không nhét lên một dòng "A → B". Thu vào một khối mở ra được — bản người gửi viết
  // lúc đầu vẫn đọc trọn, mà dòng thời gian không bị một đoạn văn chiếm hết chỗ.
  if (dai) {
    return (
      <li style={{ fontSize: "12.5px", lineHeight: 1.55, color: "var(--ink-2)" }}>
        <details>
          <summary style={{ cursor: "pointer" }}>
            <span style={{ color: "var(--ink-3)" }}>{nhan}: </span>
            {!thayDoi.after ? "đã xóa" : thayDoi.before ? "đã sửa" : "đã thêm"}
          </summary>
          <div style={{ display: "grid", gap: "6px", marginTop: "6px" }}>
            {thayDoi.before && <DoanVan tua="Bản trước" noiDung={thayDoi.before.label} />}
            {thayDoi.after && <DoanVan tua="Bản mới" noiDung={thayDoi.after.label} />}
          </div>
        </details>
      </li>
    );
  }

  return (
    <li style={{ fontSize: "12.5px", lineHeight: 1.55, color: "var(--ink-2)" }}>
      <span style={{ color: "var(--ink-3)" }}>{nhan}: </span>
      {thayDoi.before && (
        <>
          <span style={{ textDecoration: thayDoi.after ? "none" : "line-through" }}>
            {thayDoi.before.label}
          </span>
          {thayDoi.after && (
            <span className="mono" aria-label="đổi thành" style={{ color: "var(--ink-3)" }}>
              {" → "}
            </span>
          )}
        </>
      )}
      {thayDoi.after && <strong style={{ fontWeight: 600 }}>{thayDoi.after.label}</strong>}
    </li>
  );
}

function DoanVan({ tua, noiDung }: { tua: string; noiDung: string }) {
  return (
    <div
      style={{
        padding: "8px 10px",
        borderRadius: "8px",
        background: "var(--surface-2)",
        border: "1px solid var(--line)",
      }}
    >
      <span className="tua-muc">{tua}</span>
      <span style={{ display: "block", marginTop: "3px", whiteSpace: "pre-wrap" }}>
        {noiDung}
      </span>
    </div>
  );
}

/** Mốc tự trỏ (ADR-0005): đổi hồ sơ — nhận việc, sửa nội dung — mà không đổi trạng thái. */
function laTuTro(e: SuKien): boolean {
  return e.from_state === e.to_state;
}

/** Số lần hồ sơ thật sự đổi trạng thái — không tính mốc tự trỏ. */
export function soLanDoiTrangThai(cacSuKien: SuKien[]): number {
  return cacSuKien.filter((e) => !laTuTro(e)).length;
}

/**
 * Đánh dấu những lần hồ sơ quay lại một trạng thái đã đi qua.
 *
 * Con số này là dấu hiệu rõ nhất của một quy trình chạy không thẳng, nên nó đáng được
 * gọi tên ngay trên dòng thời gian thay vì để người đọc tự đếm.
 *
 * Mốc tự trỏ không đưa hồ sơ vào trạng thái nào, nên không bao giờ là quay lui: người xử
 * lý nhận việc ở *Đang xử lý* không phải là hồ sơ quay lại *Đang xử lý*.
 */
export function danhDauQuayLui(cacSuKien: SuKien[]): Map<number, string> {
  const daGap = new Map<string, number>();
  const nhan = new Map<number, string>();

  cacSuKien.forEach((e, i) => {
    if (laTuTro(e)) return;
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
          {/* Mốc tự trỏ hiện "A → A" thì người đọc tưởng hồ sơ vừa đi đâu đó rồi về */}
          {laTuTro(su_kien) ? (
            <>
              <NhanTrangThai ma={su_kien.to_state} nhan={su_kien.to_state_label} />
              <span style={{ fontSize: "12.5px", color: "var(--ink-3)" }}>
                Giữ nguyên trạng thái
              </span>
            </>
          ) : (
            <>
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
            </>
          )}
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

        {su_kien.changes.length > 0 && (
          <ul style={{ margin: "8px 0 0", padding: 0, listStyle: "none", display: "grid", gap: "2px" }}>
            {su_kien.changes.map((t) => (
              <DongThayDoi key={t.field} thayDoi={t} />
            ))}
          </ul>
        )}

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
            <span className="tua-muc">{su_kien.note_label ?? "Lý do"}</span>
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

/**
 * Tiêu đề, thống kê và thẻ chứa toàn bộ dòng thời gian, gộp theo ngày.
 *
 * `bayGio` truyền vào để cả trang kết xuất bằng đúng một mốc hiện tại — xem
 * `nhanNgay` trong lib/dinh-dang.ts.
 */
export function DongThoiGian({
  cacSuKien,
  bayGio,
  khiTrong,
}: {
  cacSuKien: SuKien[];
  bayGio: Date;
  /** Câu hiện ra khi hồ sơ chưa đổi trạng thái lần nào — mỗi cổng nói theo góc nhìn của mình. */
  khiTrong: string;
}) {
  const quayLui = danhDauQuayLui(cacSuKien);

  return (
    <>
      <div style={{ marginTop: "24px" }}>
        <h2 style={{ margin: 0, fontSize: "18px", fontWeight: 600, letterSpacing: "-.01em" }}>
          Dòng thời gian hồ sơ
        </h2>
        <p className="mono" style={{ margin: "6px 0 0", fontSize: "12px", color: "var(--ink-3)" }}>
          {cacSuKien.length} mốc · {quayLui.size} lần quay lui
        </p>
      </div>

      <div className="the" style={{ marginTop: "14px", padding: "20px 20px 4px" }}>
        {cacSuKien.length === 0 ? (
          <p
            style={{
              margin: "0 0 16px",
              fontSize: "13.5px",
              color: "var(--ink-2)",
              lineHeight: 1.6,
            }}
          >
            {khiTrong}
          </p>
        ) : (
          cacSuKien.map((e, i) => {
            const ngayMoi =
              i === 0 || khoaNgay(e.timestamp) !== khoaNgay(cacSuKien[i - 1].timestamp);

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
                    <span
                      style={{ flex: "1 1 auto", height: "1px", background: "var(--line)" }}
                    />
                  </div>
                )}
                <MocThoiGian
                  su_kien={e}
                  quayLui={quayLui.get(i)}
                  cuoiCung={i === cacSuKien.length - 1}
                />
              </div>
            );
          })
        )}
      </div>
    </>
  );
}
