"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Bảng thao tác của điều phối viên trên một hồ sơ.
//
// KHUÔN MẪU ARCHITECTURE.md MỤC 7.2, KÉO DÀI TỪ NÚT SANG Ô NHẬP. Ở cổng người gửi,
// nút bấm dựng từ `allowed_transitions`. Ở đây còn thêm một tầng: ô nhập của mỗi thao
// tác dựng từ `fields` của cạnh đó — tức từ ràng buộc gắn trên cạnh (#78).
//
// Không có bảng nào trong tệp này nói "Phân loại thì hiện ô mức ưu tiên". Gỡ ràng buộc
// `set-priority` khỏi cạnh phân loại trong infra/seed/ thì ô mức ưu tiên tự biến mất;
// gắn nó vào cạnh khác thì ô đó hiện ra ở cạnh kia. Không sửa dòng TypeScript nào.
//
// Mỗi thao tác đều mở một bảng xác nhận, kể cả thao tác không cần nhập gì. Hai lý do:
// điều phối viên thấy rõ hồ sơ sẽ chuyển sang trạng thái nào trước khi bấm, và chỉ ô
// nhập của đúng thao tác đang mở nằm trong biểu mẫu — không có chuyện ô của thao tác
// này lọt vào lần gửi của thao tác kia.

import Link from "next/link";
import { useActionState, useState } from "react";

import { CHUA_CO_LOI } from "@/app/yeu-cau/ket-qua";
import { chuyenTrangThaiDieuPhoi } from "@/app/dieu-phoi/thao-tac";
import { NhanTrangThai } from "@/components/nhan-trang-thai";
import type { CanhDiDuoc, NhanCoMa } from "@/lib/kieu";
import { kieuTruong, type NguonDanhMuc } from "@/lib/truong";

type Props = {
  maHoSo: number;
  cacCanh: CanhDiDuoc[];
  /** Giá trị điền sẵn cho từng trường: giá trị hồ sơ đang có, hoặc gợi ý. */
  giaTriDau: Record<string, string>;
  /** Giá trị nào là gợi ý của hệ thống, để đánh dấu trong ô chọn. */
  goiY: Record<string, string>;
  danhMuc: Record<NguonDanhMuc, NhanCoMa[]>;
};

function OTruong({
  truong,
  giaTriDau,
  goiY,
  danhMuc,
}: {
  truong: string;
  giaTriDau: string;
  goiY?: string;
  danhMuc: Record<NguonDanhMuc, NhanCoMa[]>;
}) {
  const kieu = kieuTruong(truong);
  const ten = `truong:${truong}`;
  const luaChon = kieu.nguon ? danhMuc[kieu.nguon] : null;

  return (
    <label style={{ display: "grid", gap: "6px" }}>
      <span style={{ fontSize: "13px", fontWeight: 600 }}>{kieu.nhan}</span>
      {luaChon ? (
        <select name={ten} defaultValue={giaTriDau} className="o-nhap">
          {/* Không có giá trị sẵn thì để trống. Gửi đi trống thì ràng buộc trên cạnh
              sẽ nói rõ phải chọn gì — không đoán hộ người dùng. */}
          {!giaTriDau && <option value="">— Chọn {kieu.nhan.toLowerCase()} —</option>}
          {luaChon.map((m) => (
            <option key={m.code} value={m.code}>
              {m.label}
              {m.code === goiY ? " · gợi ý" : ""}
            </option>
          ))}
        </select>
      ) : (
        <input name={ten} defaultValue={giaTriDau} className="o-nhap" />
      )}
    </label>
  );
}

export function BangThaoTac({ maHoSo, cacCanh, giaTriDau, goiY, danhMuc }: Props) {
  const [ketQua, thucHien, dangChay] = useActionState(chuyenTrangThaiDieuPhoi, CHUA_CO_LOI);
  const [dangMo, datDangMo] = useState<CanhDiDuoc | null>(null);

  if (cacCanh.length === 0) {
    return (
      <div style={{ display: "grid", gap: "12px" }}>
        <p style={{ margin: 0, fontSize: "13.5px", color: "var(--ink-2)", lineHeight: 1.6 }}>
          Hồ sơ đã rời khỏi tay điều phối viên. Không còn thao tác nào dành cho bạn ở
          trạng thái này.
        </p>
        <Link href="/dieu-phoi" className="nut" data-loai="chinh">
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
              // Thao tác cần nhập liệu là việc chính của điều phối viên; thao tác chỉ
              // cần lý do là ngoại lệ. Suy từ dữ liệu của cạnh, không tra bảng.
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

          {dangMo.fields.map((truong) => (
            <OTruong
              key={truong}
              truong={truong}
              giaTriDau={giaTriDau[truong] ?? ""}
              goiY={goiY[truong]}
              danhMuc={danhMuc}
            />
          ))}

          {dangMo.requires_note && (
            <label style={{ display: "grid", gap: "6px" }}>
              <span style={{ fontSize: "13px", fontWeight: 600 }}>Lý do</span>
              <textarea
                name="note"
                className="o-nhap"
                rows={3}
                maxLength={2000}
                required
                placeholder="Dòng này đi vào nhật ký hồ sơ, người gửi và phòng ban đều đọc được."
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
