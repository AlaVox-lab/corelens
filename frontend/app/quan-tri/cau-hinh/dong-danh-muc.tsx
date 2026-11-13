"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Một dòng danh mục sửa được trên màn quản trị cấu hình (#255): dòng xem, và khi bấm Sửa thì một dòng
// biểu mẫu ngay dưới. Lưu đi hai bước — "Xem trước" chạy thử trên dịch vụ (ghi, kiểm cấu hình, đếm hồ
// sơ đang mở rồi hoàn tác), người sửa đọc tóm tắt rồi mới bấm "Lưu". Cấu hình hỏng thì bị chặn ngay ở
// bước xem trước, kèm câu lỗi của dịch vụ.
//
// Tệp không biết tên trường nào: danh sách trường, nhãn và kiểu ô do trang dựng từ dữ liệu dịch vụ.

import { useRouter } from "next/navigation";
import { Fragment, useId, useState, useTransition, type ReactNode } from "react";

import type { KetQuaSuaCauHinh } from "@/lib/kieu";

import { suaCauHinh } from "./thao-tac";

export type TruongO = {
  ten: string;
  nhan: string;
  giaTri: string | number | boolean | null;
  kieu: "chu" | "so" | "bat-tat" | "chon";
  luaChon?: { code: string; label: string }[];
  toiThieu?: number;
  toiDa?: number;
};

function hienGiaTri(gt: unknown, luaChon?: { code: string; label: string }[]): string {
  if (gt === null || gt === undefined || gt === "") return "(trống)";
  if (typeof gt === "boolean") return gt ? "Có" : "Không";
  if (luaChon) return luaChon.find((l) => l.code === gt)?.label ?? String(gt);
  return String(gt);
}

export function DongDanhMuc({
  danhMuc,
  ma,
  ten,
  o,
  truong,
  soCot,
}: Readonly<{
  danhMuc: string;
  ma: string;
  ten: string;
  o: ReactNode[];
  truong: TruongO[];
  soCot: number;
}>) {
  const router = useRouter();
  const id = useId();
  const [mo, setMo] = useState(false);
  const [nhap, setNhap] = useState<Record<string, string | boolean>>({});
  const [xemTruoc, setXemTruoc] = useState<KetQuaSuaCauHinh | null>(null);
  const [loi, setLoi] = useState<string | null>(null);
  const [dangGui, batDauGui] = useTransition();

  function batDau() {
    setNhap(
      Object.fromEntries(
        truong.map((t) => [t.ten, typeof t.giaTri === "boolean" ? t.giaTri : t.giaTri === null ? "" : String(t.giaTri)]),
      ),
    );
    setXemTruoc(null);
    setLoi(null);
    setMo(true);
  }

  function thayDoi(): Record<string, unknown> {
    const ra: Record<string, unknown> = {};
    for (const t of truong) {
      const v = nhap[t.ten];
      if (t.kieu === "bat-tat") ra[t.ten] = Boolean(v);
      else if (t.kieu === "so") ra[t.ten] = v === "" ? null : Number(v);
      else ra[t.ten] = v === "" ? null : v;
    }
    // Chỉ gửi trường đổi giá trị, để nhật ký và tóm tắt không có dòng thừa
    return Object.fromEntries(
      Object.entries(ra).filter(([k, v]) => v !== truong.find((t) => t.ten === k)?.giaTri),
    );
  }

  function gui(chayThu: boolean) {
    const doi = thayDoi();
    if (Object.keys(doi).length === 0) {
      setLoi("Chưa đổi giá trị nào.");
      return;
    }
    setLoi(null);
    batDauGui(async () => {
      const kq = await suaCauHinh(danhMuc, ma, doi, chayThu);
      if (!kq.ok) {
        setLoi(kq.thongDiep);
        setXemTruoc(null);
        return;
      }
      if (chayThu) {
        setXemTruoc(kq.ketQua);
        return;
      }
      setMo(false);
      setXemTruoc(null);
      router.refresh();
    });
  }

  return (
    <Fragment>
      <tr data-dong-cau-hinh={`${danhMuc}/${ma}`}>
        {o.map((noiDung, i) => (
          <td key={i}>{noiDung}</td>
        ))}
        <td style={{ textAlign: "right" }}>
          <button
            type="button"
            className="nut nut-nho"
            onClick={() => (mo ? setMo(false) : batDau())}
            aria-expanded={mo}
            aria-controls={id}
            aria-label={`${mo ? "Đóng" : "Sửa"} ${ten}`}
          >
            {mo ? "Đóng" : "Sửa"}
          </button>
        </td>
      </tr>
      {mo ? (
        <tr id={id}>
          <td colSpan={soCot}>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                gui(true);
              }}
              style={{ display: "grid", gap: "12px", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))" }}
            >
              {truong.map((t) => (
                <label key={t.ten} style={{ display: "grid", gap: "4px", fontSize: "13px" }}>
                  <span className="nhat">{t.nhan}</span>
                  {t.kieu === "bat-tat" ? (
                    <input
                      type="checkbox"
                      name={t.ten}
                      checked={Boolean(nhap[t.ten])}
                      onChange={(e) => {
                        setNhap({ ...nhap, [t.ten]: e.target.checked });
                        setXemTruoc(null);
                      }}
                      style={{ justifySelf: "start" }}
                    />
                  ) : t.kieu === "chon" ? (
                    <select
                      className="o-nhap"
                      name={t.ten}
                      value={String(nhap[t.ten] ?? "")}
                      onChange={(e) => {
                        setNhap({ ...nhap, [t.ten]: e.target.value });
                        setXemTruoc(null);
                      }}
                    >
                      {(t.luaChon ?? []).map((l) => (
                        <option key={l.code} value={l.code}>
                          {l.label}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      className="o-nhap"
                      name={t.ten}
                      type={t.kieu === "so" ? "number" : "text"}
                      min={t.toiThieu}
                      max={t.toiDa}
                      value={String(nhap[t.ten] ?? "")}
                      onChange={(e) => {
                        setNhap({ ...nhap, [t.ten]: e.target.value });
                        setXemTruoc(null);
                      }}
                    />
                  )}
                </label>
              ))}
              <div style={{ gridColumn: "1 / -1", display: "flex", gap: "8px", flexWrap: "wrap" }}>
                <button type="submit" className="nut" disabled={dangGui}>
                  Xem trước
                </button>
                {xemTruoc ? (
                  <button type="button" className="nut" data-loai="chinh" disabled={dangGui} onClick={() => gui(false)}>
                    Lưu
                  </button>
                ) : null}
              </div>
            </form>
            {loi ? (
              <p
                role="alert"
                style={{
                  margin: "10px 0 0",
                  padding: "10px 14px",
                  borderRadius: "11px",
                  background: "var(--f-r-bg)",
                  border: "1px solid var(--f-r-line)",
                  color: "var(--f-r-ink)",
                  fontSize: "13.5px",
                  lineHeight: 1.6,
                }}
              >
                {loi}
              </p>
            ) : null}
            {xemTruoc ? (
              <div role="status" className="the" style={{ marginTop: "12px", padding: "12px 16px", fontSize: "13.5px" }}>
                <ul style={{ margin: 0, paddingLeft: "18px" }}>
                  {xemTruoc.changes.map((c) => {
                    const t = truong.find((x) => x.ten === c.field);
                    return (
                      <li key={c.field}>
                        {c.field_label}: {hienGiaTri(c.old_value, t?.luaChon)} → <b>{hienGiaTri(c.new_value, t?.luaChon)}</b>
                      </li>
                    );
                  })}
                </ul>
                <p style={{ margin: "8px 0 0" }}>
                  {xemTruoc.affects_deadlines
                    ? xemTruoc.open_cases > 0
                      ? `${xemTruoc.open_cases} hồ sơ đang mở sẽ tính theo hạn mới ngay khi lưu.`
                      : "Không có hồ sơ đang mở nào bị đổi hạn."
                    : `Thay đổi áp ngay cho mọi hồ sơ (${xemTruoc.open_cases} hồ sơ đang mở liên quan).`}{" "}
                  Cấu hình sau khi sửa đã qua kiểm tra.
                </p>
              </div>
            ) : null}
          </td>
        </tr>
      ) : null}
    </Fragment>
  );
}
