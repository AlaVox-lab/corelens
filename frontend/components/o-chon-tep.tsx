"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Ô chọn tệp đính kèm: kéo thả hoặc bấm chọn (#80).
//
// Chặn đuôi, dung lượng và số tệp theo `ChinhSachTep` — con số do dịch vụ trả, không có giới
// hạn nào viết ở đây. Đây là lớp chặn thứ nhất, để người gửi biết ngay chứ không đợi tải xong
// mới bị từ chối; lớp thứ hai là dịch vụ, vẫn kiểm lại mọi thứ (chặn ở giao diện thôi thì không
// đủ). Component chỉ giữ danh sách tệp ĐÃ CHỌN, chưa gửi đi đâu: phía dùng quyết định gửi lúc
// nào — cùng lúc gửi hồ sơ, hay bấm "Tải lên" trên trang hồ sơ.

import { FileText, Paperclip, X } from "lucide-react";
import { useId, useRef, useState } from "react";

import { dungLuong } from "@/lib/dinh-dang";
import type { ChinhSachTep } from "@/lib/kieu";

/** Đuôi tệp, viết thường, không dấu chấm. Không có đuôi thì trả chuỗi rỗng. */
function duoiTep(ten: string): string {
  const i = ten.lastIndexOf(".");
  return i < 0 ? "" : ten.slice(i + 1).toLowerCase();
}

export function OChonTep({
  chinhSach,
  tepDaChon,
  doi,
  daCo = 0,
  voHieu = false,
}: {
  chinhSach: ChinhSachTep;
  tepDaChon: File[];
  doi: (tep: File[]) => void;
  /** Số tệp hồ sơ đã có sẵn, để chặn vượt trần của cả hồ sơ. */
  daCo?: number;
  voHieu?: boolean;
}) {
  const maO = useId();
  const oNhap = useRef<HTMLInputElement>(null);
  const [keoVao, datKeoVao] = useState(false);
  const [loi, datLoi] = useState<string[]>([]);

  const duoiHopLe = chinhSach.allowed_extensions;
  const tranByte = chinhSach.max_mb * 1024 * 1024;
  const conChoTrong = Math.min(
    chinhSach.max_files - tepDaChon.length,
    chinhSach.max_files_per_case - daCo - tepDaChon.length,
  );

  function them(moi: FileList | File[]) {
    const nhan: File[] = [];
    const tuChoi: string[] = [];
    let cho = conChoTrong;
    for (const f of Array.from(moi)) {
      if (!duoiHopLe.includes(duoiTep(f.name))) {
        tuChoi.push(`“${f.name}”: chỉ nhận đuôi ${duoiHopLe.join(", ")}.`);
      } else if (f.size === 0) {
        tuChoi.push(`“${f.name}” rỗng.`);
      } else if (f.size > tranByte) {
        tuChoi.push(`“${f.name}” lớn hơn giới hạn: tối đa ${chinhSach.max_mb} MB mỗi tệp.`);
      } else if (tepDaChon.some((t) => t.name === f.name && t.size === f.size)) {
        // Chọn lại đúng tệp đã chọn thì bỏ qua, không báo lỗi
      } else if (cho <= 0) {
        tuChoi.push(
          `“${f.name}”: mỗi lần tối đa ${chinhSach.max_files} tệp, mỗi hồ sơ tối đa ${chinhSach.max_files_per_case} tệp.`,
        );
      } else {
        nhan.push(f);
        cho -= 1;
      }
    }
    datLoi(tuChoi);
    if (nhan.length > 0) doi([...tepDaChon, ...nhan]);
    if (oNhap.current) oNhap.current.value = "";
  }

  function bo(i: number) {
    datLoi([]);
    doi(tepDaChon.filter((_, j) => j !== i));
  }

  return (
    <div style={{ display: "grid", gap: "9px" }}>
      <div
        data-keo-vao={keoVao ? "" : undefined}
        onDragOver={(e) => {
          if (voHieu) return;
          e.preventDefault();
          datKeoVao(true);
        }}
        onDragLeave={() => datKeoVao(false)}
        onDrop={(e) => {
          e.preventDefault();
          datKeoVao(false);
          if (!voHieu) them(e.dataTransfer.files);
        }}
        style={{
          display: "grid",
          gap: "6px",
          justifyItems: "center",
          padding: "18px 14px",
          textAlign: "center",
          borderRadius: "11px",
          border: `1.5px dashed ${keoVao ? "var(--accent)" : "var(--line-strong, var(--line))"}`,
          background: keoVao ? "var(--accent-soft)" : "var(--surface-2)",
        }}
      >
        <Paperclip aria-hidden size={20} />
        <label htmlFor={maO} style={{ fontSize: "13.5px", lineHeight: 1.5 }}>
          Kéo tệp vào đây, hoặc{" "}
          <span style={{ color: "var(--accent)", fontWeight: 600, cursor: "pointer" }}>
            bấm để chọn
          </span>
        </label>
        <span style={{ fontSize: "12px", color: "var(--ink-3)", lineHeight: 1.5 }}>
          Tối đa {chinhSach.max_files} tệp, mỗi tệp không quá {chinhSach.max_mb} MB. Nhận:{" "}
          {duoiHopLe.join(", ")}.
        </span>
        <input
          id={maO}
          ref={oNhap}
          type="file"
          multiple
          disabled={voHieu || conChoTrong <= 0}
          accept={duoiHopLe.map((d) => `.${d}`).join(",")}
          onChange={(e) => e.target.files && them(e.target.files)}
          style={{ position: "absolute", width: 1, height: 1, opacity: 0, overflow: "hidden" }}
        />
      </div>

      {loi.length > 0 && (
        <ul
          role="alert"
          style={{
            margin: 0,
            padding: "9px 12px 9px 28px",
            borderRadius: "9px",
            background: "var(--f-r-bg)",
            border: "1px solid var(--f-r-line)",
            color: "var(--f-r-ink)",
            fontSize: "13px",
            lineHeight: 1.55,
          }}
        >
          {loi.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      )}

      {tepDaChon.length > 0 && (
        <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: "6px" }}>
          {tepDaChon.map((f, i) => (
            <li
              key={`${f.name}-${f.size}`}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "9px",
                padding: "7px 10px",
                borderRadius: "9px",
                border: "1px solid var(--line)",
                background: "var(--surface)",
                fontSize: "13.5px",
              }}
            >
              <FileText aria-hidden size={16} />
              <span style={{ flex: 1, minWidth: 0, overflowWrap: "anywhere" }}>{f.name}</span>
              <span className="mono nhat" style={{ fontSize: "12px" }}>
                {dungLuong(f.size)}
              </span>
              <button
                type="button"
                className="nut nut-nho"
                aria-label={`Bỏ tệp ${f.name}`}
                disabled={voHieu}
                onClick={() => bo(i)}
              >
                <X aria-hidden size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
