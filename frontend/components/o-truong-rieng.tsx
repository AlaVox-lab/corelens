"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Ô nhập các trường thông tin riêng của một loại yêu cầu (#250), dựng từ khai báo dịch vụ trả
// về — nhãn, kiểu, bắt buộc, lựa chọn. Không có tên trường nào viết ở đây: thêm một trường
// trong dữ liệu là biểu mẫu tự có ô đó.
//
// Cả bộ giá trị gửi đi trong MỘT ô ẩn dạng JSON (`ten`), vì dịch vụ nhận nó là một trường
// `details`. Ô bắt buộc mang `aria-required` chứ không `required`: biểu mẫu gửi ba bước giấu
// bước 2 khi gửi ở bước 3, và ô `required` bị giấu làm trình duyệt chặn gửi mà không nói
// gì. Dịch vụ kiểm và trả câu "Chưa điền …" bằng nhãn trường.

import { useEffect, useRef, useState } from "react";

import type { LoaiYeuCau, TruongRieng } from "@/lib/kieu";

type GiaTri = Record<string, string>;

function chuoi(v: unknown): string {
  return v === null || v === undefined ? "" : String(v);
}

export function OTruongRieng({
  ten,
  cacTruong: truongCoDinh,
  giaTriDau = {},
  theoLoai,
  khiDoi,
}: {
  /** Tên ô ẩn mang JSON — "details" ở biểu mẫu gửi, "truong:details" ở sửa nội dung. */
  ten: string;
  cacTruong?: TruongRieng[];
  giaTriDau?: Record<string, unknown>;
  /** Báo bộ giá trị đang nhập mỗi lần đổi — bước Xem lại của biểu mẫu gửi liệt kê lại các trường đã điền (#552). */
  khiDoi?: (giaTri: Record<string, string>) => void;
  /**
   * Ở bảng sửa nội dung, người gửi đổi được cả loại yêu cầu: ô trường riêng nghe ô chọn loại
   * cùng biểu mẫu (tên `tenOChon`) và đổi bộ ô theo loại mới. Không nghe thì đổi loại xong vẫn
   * thấy ô của loại cũ, và dịch vụ từ chối vì thiếu trường của loại mới.
   */
  theoLoai?: { cacLoai: LoaiYeuCau[]; loaiDau: string | null; tenOChon: string };
}) {
  const goc = useRef<HTMLFieldSetElement>(null);
  const [loai, datLoai] = useState(theoLoai?.loaiDau ?? null);
  const [giaTri, datGiaTri] = useState<GiaTri>(() =>
    Object.fromEntries(Object.entries(giaTriDau).map(([k, v]) => [k, chuoi(v)])),
  );

  useEffect(() => {
    khiDoi?.(giaTri);
  }, [giaTri, khiDoi]);

  useEffect(() => {
    if (!theoLoai) return;
    const oChon = goc.current?.form?.elements.namedItem(theoLoai.tenOChon);
    if (!(oChon instanceof HTMLSelectElement)) return;
    const doi = () => datLoai(oChon.value || null);
    oChon.addEventListener("change", doi);
    return () => oChon.removeEventListener("change", doi);
  }, [theoLoai]);

  const cacTruong = theoLoai
    ? (theoLoai.cacLoai.find((l) => l.code === loai)?.fields ?? [])
    : (truongCoDinh ?? []);

  if (cacTruong.length === 0) {
    // Vẫn giữ ô ẩn: loại mới không có trường riêng thì gửi bộ rỗng để xóa trường của loại cũ
    return theoLoai ? <input type="hidden" name={ten} value="{}" /> : null;
  }

  // Chỉ gửi trường của loại đang chọn, bỏ ô rỗng — dịch vụ coi ô rỗng là chưa điền
  const guiDi = Object.fromEntries(
    cacTruong.filter((t) => giaTri[t.code]?.trim()).map((t) => [t.code, giaTri[t.code].trim()]),
  );
  const dat = (ma: string, v: string) => datGiaTri((cu) => ({ ...cu, [ma]: v }));

  return (
    <fieldset className="o-truong-rieng" ref={goc}>
      <legend>Thông tin riêng của loại yêu cầu</legend>
      <input type="hidden" name={ten} value={JSON.stringify(guiDi)} />
      {cacTruong.map((t) => {
        const id = `truong-rieng-${t.code}`;
        const v = giaTri[t.code] ?? "";
        return (
          <label key={t.code} htmlFor={id} className="o-truong">
            <span className="o-truong-nhan">
              {t.label}
              {t.required ? (
                <span className="bat-buoc" aria-hidden>
                  {" "}*
                </span>
              ) : (
                <span className="khong-bat-buoc"> — không bắt buộc</span>
              )}
            </span>
            {t.kind === "choice" ? (
              <select id={id} className="o-nhap" value={v} aria-required={t.required} onChange={(e) => dat(t.code, e.target.value)}>
                <option value="">Chọn…</option>
                {(t.options ?? []).map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
            ) : (
              <span className="o-truong-dong">
                <input
                  id={id}
                  className="o-nhap"
                  type={t.kind === "number" ? "number" : t.kind === "date" ? "date" : "text"}
                  inputMode={t.kind === "number" ? "decimal" : undefined}
                  min={t.kind === "number" ? 0 : undefined}
                  maxLength={t.kind === "text" ? 500 : undefined}
                  aria-required={t.required}
                  value={v}
                  onChange={(e) => dat(t.code, e.target.value)}
                />
                {t.unit ? <span className="o-truong-don-vi">{t.unit}</span> : null}
              </span>
            )}
            {t.help_text ? <span className="o-truong-goi-y">{t.help_text}</span> : null}
          </label>
        );
      })}
    </fieldset>
  );
}
