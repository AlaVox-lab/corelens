"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Bảng thao tác trên một hồ sơ, dùng chung cho buồng lái điều phối (#82) và buồng lái
// phòng ban (#83). Mỗi buồng lái truyền vào thao tác gửi đi của riêng nó, vì mỗi nơi có
// một cửa riêng ở phía dịch vụ.
//
// KHUÔN MẪU ARCHITECTURE.md MỤC 7.2, KÉO DÀI TỪ NÚT SANG Ô NHẬP. Nút bấm dựng từ
// `allowed_transitions`; ô nhập của mỗi thao tác dựng từ `fields` của cạnh đó — tức từ
// ràng buộc gắn trên cạnh (#78). Không có bảng nào trong tệp này nói "Phân loại thì hiện
// ô mức ưu tiên" hay "Nhận việc thì hiện ô người xử lý".
//
// Mỗi thao tác đều mở một bảng xác nhận, kể cả thao tác không cần nhập gì. Hai lý do:
// người bấm thấy rõ hồ sơ sẽ chuyển sang trạng thái nào trước khi bấm, và chỉ ô nhập
// của đúng thao tác đang mở nằm trong biểu mẫu — không có chuyện ô của thao tác này lọt
// vào lần gửi của thao tác kia.

import Link from "next/link";
import { useActionState, useState } from "react";

import { CHUA_CO_LOI, type KetQuaThaoTac } from "@/app/yeu-cau/ket-qua";
import { CanhBaoKetThuc } from "@/components/canh-bao-ket-thuc";
import { NhanTrangThai } from "@/components/nhan-trang-thai";
import { TIEN_TO_TRUONG } from "@/lib/bieu-mau";
import type { CanhDiDuoc, NhanCoMa } from "@/lib/kieu";
import { kieuTruong, type NguonDanhMuc } from "@/lib/truong";

/** Lựa chọn cho một ô chọn, hoặc lý do không nạp được chúng. */
export type NguonLuaChon = NhanCoMa[] | { loi: string };

type Props = {
  maHoSo: number;
  cacCanh: CanhDiDuoc[];
  /** Giá trị điền sẵn cho từng trường: giá trị hồ sơ đang có, hoặc gợi ý. */
  giaTriDau: Record<string, string>;
  /** Giá trị nào là gợi ý của hệ thống, để đánh dấu trong ô chọn. */
  goiY: Record<string, string>;
  danhMuc: Partial<Record<NguonDanhMuc, NguonLuaChon>>;
  /** Thao tác gửi đi — một server action của buồng lái đang dùng bảng này. */
  hanhDong: (truoc: KetQuaThaoTac, duLieu: FormData) => Promise<KetQuaThaoTac>;
  /** Khi không còn thao tác nào: câu giải thích và đường về hàng đợi. */
  khiHet: { cau: string; veHangDoi: string };
};

const KIEU_NHAN: React.CSSProperties = { fontSize: "13px", fontWeight: 600 };

function OTruong({
  truong,
  giaTriDau,
  goiY,
  nguon,
}: {
  truong: string;
  giaTriDau: string;
  goiY?: string;
  nguon?: NguonLuaChon;
}) {
  const kieu = kieuTruong(truong);
  const ten = `${TIEN_TO_TRUONG}${truong}`;

  // Danh mục không nạp được — ví dụ danh bạ Keycloak không trả lời. Khóa ô lại và nói
  // lý do. Ô bị khóa thì trình duyệt không gửi nó đi, nên thao tác vẫn làm được nếu
  // trường này không bắt buộc; nếu bắt buộc, ràng buộc trên cạnh sẽ nói rõ.
  if (nguon && !Array.isArray(nguon)) {
    return (
      <label style={{ display: "grid", gap: "6px" }}>
        <span style={KIEU_NHAN}>{kieu.nhan}</span>
        <select disabled className="o-nhap">
          <option>Không nạp được danh sách</option>
        </select>
        <span role="status" style={{ fontSize: "12.5px", color: "var(--f-r-ink)", lineHeight: 1.55 }}>
          {nguon.loi}
        </span>
      </label>
    );
  }

  if (!nguon) {
    return (
      <label style={{ display: "grid", gap: "6px" }}>
        <span style={KIEU_NHAN}>{kieu.nhan}</span>
        <input name={ten} defaultValue={giaTriDau} className="o-nhap" />
      </label>
    );
  }

  // Giá trị đang có mà không còn trong danh sách — người xử lý đã rời phòng chẳng hạn —
  // thì để trống. Không có ô trống, trình duyệt sẽ âm thầm chọn mục đầu tiên, và một
  // cú bấm xác nhận vội sẽ giao hồ sơ cho người không ai chọn.
  const coSan = nguon.some((m) => m.code === giaTriDau);

  return (
    <label style={{ display: "grid", gap: "6px" }}>
      <span style={KIEU_NHAN}>{kieu.nhan}</span>
      <select name={ten} defaultValue={coSan ? giaTriDau : ""} className="o-nhap">
        {/* Không có giá trị sẵn thì để trống. Gửi đi trống thì ràng buộc trên cạnh
            sẽ nói rõ phải chọn gì — không đoán hộ người dùng. */}
        {!coSan && <option value="">— Chọn {kieu.nhan.toLowerCase()} —</option>}
        {nguon.map((m) => (
          <option key={m.code} value={m.code}>
            {m.label}
            {m.code === goiY ? " · gợi ý" : ""}
          </option>
        ))}
      </select>
    </label>
  );
}

export function BangThaoTac({
  maHoSo,
  cacCanh,
  giaTriDau,
  goiY,
  danhMuc,
  hanhDong,
  khiHet,
}: Props) {
  const [ketQua, thucHien, dangChay] = useActionState(hanhDong, CHUA_CO_LOI);
  const [dangMo, datDangMo] = useState<CanhDiDuoc | null>(null);

  if (cacCanh.length === 0) {
    return (
      <div style={{ display: "grid", gap: "12px" }}>
        <p style={{ margin: 0, fontSize: "13.5px", color: "var(--ink-2)", lineHeight: 1.6 }}>
          {khiHet.cau}
        </p>
        <Link href={khiHet.veHangDoi} className="nut" data-loai="chinh">
          ← Về hàng đợi
        </Link>
      </div>
    );
  }

  return (
    <form action={thucHien} style={{ display: "grid", gap: "12px" }}>
      <input type="hidden" name="case_id" value={maHoSo} />

      <div style={{ display: "grid", gap: "8px" }}>
        {cacCanh.map((canh) => {
          const mo = dangMo?.to_state === canh.to_state;
          return (
            <button
              key={canh.to_state}
              type="button"
              className="nut"
              // Thao tác cần nhập liệu là việc chính; thao tác chỉ cần lý do là ngoại lệ.
              // Suy từ dữ liệu của cạnh, không tra bảng.
              data-loai={canh.fields.length > 0 ? "chinh" : undefined}
              aria-expanded={mo}
              onClick={() => datDangMo(mo ? null : canh)}
              style={{ justifyContent: "space-between", width: "100%" }}
            >
              <span>{canh.activity_label}</span>
              <span aria-hidden="true">{mo ? "−" : "+"}</span>
            </button>
          );
        })}
      </div>

      {dangMo && (
        <div
          // Đổi thao tác thì dựng lại ô nhập, để giá trị điền sẵn không mang từ thao
          // tác trước sang.
          key={dangMo.to_state}
          style={{
            padding: "15px",
            borderRadius: "11px",
            background: "var(--surface-2)",
            border: "1px solid var(--line)",
            display: "grid",
            gap: "13px",
          }}
        >
          <div style={{ display: "grid", gap: "7px" }}>
            <span style={{ fontSize: "14px", fontWeight: 600 }}>{dangMo.activity_label}</span>
            <span
              style={{
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                gap: "7px",
                fontSize: "12.5px",
                color: "var(--ink-3)",
              }}
            >
              Hồ sơ sẽ chuyển sang
              <NhanTrangThai ma={dangMo.to_state} nhan={dangMo.to_state_label} />
            </span>
          </div>

          {dangMo.fields.map((truong) => {
            const nguonMa = kieuTruong(truong).nguon;
            return (
              <OTruong
                key={truong}
                truong={truong}
                giaTriDau={giaTriDau[truong] ?? ""}
                goiY={goiY[truong]}
                nguon={nguonMa ? danhMuc[nguonMa] : undefined}
              />
            );
          })}

          {dangMo.to_state_is_terminal && (
            <CanhBaoKetThuc nhanTrangThai={dangMo.to_state_label} />
          )}

          {/* Lý do: bắt buộc khi cạnh đòi (`requires_note`); tùy chọn khi cạnh dẫn tới
              trạng thái kết thúc — ai đóng một hồ sơ cũng nên được để lại một dòng (#98).
              Tên ô lấy từ cạnh khi có (#79): khi hỏi thêm, ô này là câu hỏi chứ không
              phải lý do. */}
          {(dangMo.requires_note || dangMo.to_state_is_terminal) && (
            <label style={{ display: "grid", gap: "6px" }}>
              <span style={KIEU_NHAN}>
                {dangMo.note_label ?? "Lý do"}
                {!dangMo.requires_note && (
                  <span style={{ fontWeight: 400, color: "var(--ink-3)" }}> — không bắt buộc</span>
                )}
              </span>
              <textarea
                name="note"
                className="o-nhap"
                rows={3}
                maxLength={2000}
                required={dangMo.requires_note}
                placeholder="Dòng này đi vào nhật ký hồ sơ, người gửi và các bên xử lý đều đọc được."
              />
            </label>
          )}

          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
            <button
              type="submit"
              name="to_state"
              value={dangMo.to_state}
              className="nut"
              data-loai="chinh"
              disabled={dangChay}
            >
              {dangChay ? "Đang gửi…" : `Xác nhận · ${dangMo.activity_label}`}
            </button>
            <button type="button" className="nut" onClick={() => datDangMo(null)}>
              Thôi
            </button>
          </div>
        </div>
      )}

      {ketQua.loi && (
        <p
          role="alert"
          style={{
            margin: 0,
            padding: "12px 14px",
            borderRadius: "11px",
            background: "var(--f-r-bg)",
            border: "1px solid var(--f-r-line)",
            color: "var(--f-r-ink)",
            fontSize: "13.5px",
            lineHeight: 1.6,
          }}
        >
          {ketQua.loi}
        </p>
      )}
    </form>
  );
}
