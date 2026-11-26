"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Thao tác hàng loạt trên hàng đợi (#440): thanh thao tác dính dưới bảng khi có hồ sơ được chọn, hộp
// thoại chọn giá trị chung, và khung kết quả.
//
// Tệp này không biết bước nào là "phân loại" hay "chuyển phòng": nút dựng từ danh sách bước dịch vụ trả
// (`/coordination/bulk-transitions`), ô trong hộp thoại dựng từ `fields` của bước, nhãn ô và danh mục từ
// `lib/truong.ts` như bảng thao tác một hồ sơ. Hồ sơ nào đi được bước nào là theo trạng thái nguồn dịch
// vụ trả — hồ sơ khác trạng thái được nói trước trong hộp thoại và không gửi đi.
//
// Hộp thoại là phần tử `<dialog>` mở bằng `showModal()`: trình duyệt khóa tiêu điểm trong hộp, đưa
// hộp lên lớp trên cùng, Esc đóng được, và tiêu điểm vào ô đầu tiên (hộp không còn gì để làm thì vào
// nút Hủy thao tác). Hộp có ô chọn nên bấm ra ngoài không đóng.

import Link from "next/link";
import { useEffect, useRef, useState, useTransition } from "react";

import type { DongHangDoi } from "@/components/bang-hang-doi";
import type { KetQua } from "@/lib/api";
import type { KetQuaHangLoat, NhanCoMa, ThaoTacHangLoat } from "@/lib/kieu";
import { kieuTruong, type NguonDanhMuc } from "@/lib/truong";

export type ChonNhieu = {
  cacBuoc: ThaoTacHangLoat[];
  /** Lô lớn nhất dịch vụ nhận (`DXLAB_BULK_MAX_CASES`). */
  toiDa: number;
  /** Lựa chọn của từng danh mục, kèm giá trị mặc định nếu danh mục có (mức ưu tiên `is_default`). */
  danhMuc: Partial<Record<NguonDanhMuc, { ds: NhanCoMa[]; macDinh?: string }>>;
  /** Gốc đường dẫn trang chi tiết: mã hồ sơ bị chặn mở `${goc}/${id}`. */
  goc: string;
  hanhDong: (than: {
    activity_code: string;
    case_ids: number[];
    changes: Record<string, string>;
    note: string | null;
  }) => Promise<KetQua<KetQuaHangLoat>>;
};

export type KetQuaDaChay = { nhan: string; kq: KetQuaHangLoat };

const KIEU_NHAN: React.CSSProperties = { fontSize: "13px", fontWeight: 600 };

function HopThoai({
  buoc,
  dangChon,
  chonNhieu,
  khiDong,
  khiXong,
}: {
  buoc: ThaoTacHangLoat;
  dangChon: DongHangDoi[];
  chonNhieu: ChonNhieu;
  khiDong: () => void;
  khiXong: (kq: KetQuaHangLoat) => void;
}) {
  const hop = useRef<HTMLDialogElement>(null);
  const [loi, datLoi] = useState("");
  const [dangChay, batDau] = useTransition();

  const nguon = new Set(buoc.from_states.map((s) => s.code));
  const apDung = dangChon.filter((d) => d.trangThai && nguon.has(d.trangThai.code));
  const boQua = dangChon.filter((d) => !apDung.includes(d));
  const quaLo = apDung.length > chonNhieu.toiDa;
  const khoa = apDung.length === 0 || quaLo;
  const tenNguon = buoc.from_states.map((s) => s.label).join(", ");

  useEffect(() => {
    const el = hop.current;
    if (el && !el.open) el.showModal();
  }, []);

  function gui(duLieu: FormData) {
    if (khoa || dangChay) return;
    const changes: Record<string, string> = {};
    for (const f of buoc.fields) {
      const gt = String(duLieu.get(f.code) ?? "").trim();
      if (gt) changes[f.code] = gt;
    }
    const ghiChu = String(duLieu.get("note") ?? "").trim();
    datLoi("");
    batDau(async () => {
      const kq = await chonNhieu.hanhDong({
        activity_code: buoc.activity_code,
        case_ids: apDung.map((d) => d.id),
        changes,
        note: ghiChu || null,
      });
      if (!kq.ok) {
        datLoi(kq.thongDiep);
        return;
      }
      hop.current?.close();
      khiXong(kq.duLieu);
    });
  }

  const nhanNut = `${buoc.activity_label} cho ${apDung.length} hồ sơ`;

  return (
    <dialog
      ref={hop}
      className="hop-thoai"
      aria-labelledby="hl-tieu-de"
      aria-describedby="hl-mo-ta"
      // Esc: đóng như nút Hủy thao tác, trừ khi đang gửi — lô đã đi một nửa thì phải đợi kết quả
      onCancel={(e) => {
        e.preventDefault();
        if (!dangChay) khiDong();
      }}
    >
      <form
        className="hop-thoai-than"
        onSubmit={(e) => {
          e.preventDefault();
          gui(new FormData(e.currentTarget));
        }}
      >
        <h2 id="hl-tieu-de">{nhanNut}</h2>
        <p id="hl-mo-ta" className="nhat">
          Giá trị bạn chọn áp chung cho mọi hồ sơ dưới đây. Mỗi hồ sơ vẫn qua đủ các bước kiểm như khi làm
          từng hồ sơ; hồ sơ nào bị chặn sẽ được báo riêng, các hồ sơ khác vẫn đi.
        </p>

        {boQua.length > 0 && (
          <p role="note" className="hl-canh-bao">
            <strong>{boQua.length} hồ sơ sẽ bỏ qua</strong> vì đang ở trạng thái khác — bước này chỉ đi từ{" "}
            {tenNguon}: <span className="mono">{boQua.map((d) => d.ma).join(", ")}</span>
          </p>
        )}

        {apDung.length > 0 && (
          <div style={{ display: "grid", gap: "6px" }}>
            <span style={KIEU_NHAN} id="hl-ds-nhan">
              Sẽ áp cho {apDung.length} hồ sơ
            </span>
            <ul className="hl-ds-ma" aria-labelledby="hl-ds-nhan">
              {apDung.map((d) => (
                <li key={d.id} className="mono">
                  {d.ma}
                </li>
              ))}
            </ul>
          </div>
        )}

        {khoa ? (
          <p role="note" className="hl-canh-bao">
            {quaLo
              ? `Mỗi lần làm hàng loạt tối đa ${chonNhieu.toiDa} hồ sơ. Bỏ chọn bớt ${apDung.length - chonNhieu.toiDa} hồ sơ rồi làm lại.`
              : `Không hồ sơ nào đang chọn ở ${tenNguon}, nên không có gì để làm.`}
          </p>
        ) : (
          <>
            {buoc.fields.map((f) => {
              const kieu = kieuTruong(f.code);
              const danhMuc = kieu.nguon ? chonNhieu.danhMuc[kieu.nguon] : undefined;
              const ds = danhMuc?.ds;
              // Giá trị mặc định của danh mục (mức ưu tiên mặc định) chỉ điền sẵn ô bắt buộc — như bảng
              // thao tác một hồ sơ. Ô không bắt buộc mặc định là giữ nguyên ở từng hồ sơ.
              const macDinh = f.required ? (danhMuc?.macDinh ?? "") : "";
              return (
                <label key={f.code} style={{ display: "grid", gap: "6px" }}>
                  <span style={KIEU_NHAN}>
                    {kieu.nhan}
                    {f.required ? (
                      <span aria-hidden style={{ color: "var(--f-r-ink)" }}> *</span>
                    ) : (
                      <span style={{ fontWeight: 400, color: "var(--ink-3)" }}> — không bắt buộc</span>
                    )}
                  </span>
                  {ds ? (
                    <select
                      name={f.code}
                      className="o-nhap"
                      required={f.required}
                      defaultValue={macDinh}
                      disabled={dangChay}
                    >
                      <option value="">{f.required ? "Chọn một giá trị" : "Giữ nguyên ở từng hồ sơ"}</option>
                      {ds.map((o) => (
                        <option key={o.code} value={o.code}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input name={f.code} className="o-nhap" required={f.required} disabled={dangChay} />
                  )}
                </label>
              );
            })}
            {buoc.requires_note && (
              <label style={{ display: "grid", gap: "6px" }}>
                <span style={KIEU_NHAN}>
                  {buoc.note_label ?? "Lý do"}
                  <span aria-hidden style={{ color: "var(--f-r-ink)" }}> *</span>
                </span>
                <textarea name="note" className="o-nhap" rows={3} maxLength={2000} required disabled={dangChay} />
              </label>
            )}
          </>
        )}

        {loi && (
          <p role="alert" className="hl-loi">
            {loi}
          </p>
        )}

        <div className="hop-thoai-chan">
          <button type="button" className="nut" onClick={khiDong} disabled={dangChay}>
            Hủy thao tác
          </button>
          <button type="submit" className="nut" data-loai="chinh" disabled={khoa || dangChay} aria-busy={dangChay || undefined}>
            {dangChay ? "Đang thực hiện…" : nhanNut}
          </button>
        </div>
      </form>
    </dialog>
  );
}

/** Thanh dính dưới bảng khi có ít nhất một hồ sơ được chọn. */
export function ThanhHangLoat({
  chonNhieu,
  dangChon,
  boChon,
  khiXong,
}: {
  chonNhieu: ChonNhieu;
  dangChon: DongHangDoi[];
  /** Bỏ chọn những hồ sơ này; không truyền là bỏ hết. */
  boChon: (ids?: number[]) => void;
  khiXong: (kq: KetQuaDaChay) => void;
}) {
  const [dangMo, datMo] = useState<ThaoTacHangLoat | null>(null);
  const nutMo = useRef<HTMLButtonElement | null>(null);

  function dong() {
    datMo(null);
    // Trả tiêu điểm về nút đã mở hộp — nếu nút còn trên màn
    requestAnimationFrame(() => {
      if (nutMo.current?.isConnected) nutMo.current.focus();
    });
  }

  if (dangChon.length === 0 && !dangMo) return null;

  return (
    <>
      <div className="thanh-hang-loat khong-in" role="region" aria-label="Thao tác với hồ sơ đã chọn">
        <p>
          Đã chọn <b>{dangChon.length}</b> hồ sơ
        </p>
        <div className="thanh-hang-loat-nut">
          {chonNhieu.cacBuoc.map((b) => (
            <button
              key={b.activity_code}
              type="button"
              className="nut nut-nho"
              data-buoc-hang-loat={b.activity_code}
              onClick={(e) => {
                nutMo.current = e.currentTarget;
                datMo(b);
              }}
            >
              {b.activity_label}
            </button>
          ))}
          <button type="button" className="nut nut-nho" data-loai="ma" onClick={() => boChon()}>
            Bỏ chọn
          </button>
        </div>
      </div>
      {dangMo && (
        <HopThoai
          buoc={dangMo}
          dangChon={dangChon}
          chonNhieu={chonNhieu}
          khiDong={dong}
          khiXong={(kq) => {
            datMo(null);
            // Hồ sơ đã chuyển thì bỏ chọn; hồ sơ bị chặn giữ chọn để làm lại
            boChon(kq.items.filter((m) => m.ok).map((m) => m.case_id));
            khiXong({ nhan: dangMo.activity_label, kq });
          }}
        />
      )}
    </>
  );
}

/**
 * Khung kết quả của lần chạy gần nhất. Vùng `aria-live` có sẵn từ lúc tải trang — trình đọc màn hình
 * mới đọc được nội dung chèn vào sau. Có kết quả thì tiêu điểm chuyển vào khung: nút vừa bấm có thể
 * đã biến mất cùng thanh thao tác.
 */
export function KetQuaHangLoatKhung({
  ketQua,
  goc,
  khiDong,
}: {
  ketQua: KetQuaDaChay | null;
  goc: string;
  khiDong: () => void;
}) {
  const tieuDe = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (ketQua) tieuDe.current?.focus();
  }, [ketQua]);

  const biChan = ketQua?.kq.items.filter((m) => !m.ok) ?? [];
  return (
    <div aria-live="polite" className="khong-in">
      {ketQua && (
        <section className="kq-hang-loat" data-co-chan={biChan.length > 0 ? "" : undefined} aria-labelledby="kq-hl-tieu-de">
          <div className="kq-hang-loat-dau">
            <h2 id="kq-hl-tieu-de" ref={tieuDe} tabIndex={-1}>
              {ketQua.nhan}: đã chuyển {ketQua.kq.succeeded}/{ketQua.kq.total} hồ sơ
            </h2>
            <button type="button" className="nut nut-nho" data-loai="ma" onClick={khiDong}>
              Đóng
            </button>
          </div>
          {biChan.length > 0 && (
            <>
              <p className="nhat">
                {biChan.length} hồ sơ bị chặn, vẫn đứng nguyên và vẫn được chọn để làm lại:
              </p>
              <ul className="kq-hang-loat-ds">
                {biChan.map((m) => (
                  <li key={m.case_id}>
                    {m.code ? (
                      <Link href={`${goc}/${m.case_id}`} className="mono">
                        {m.code}
                      </Link>
                    ) : (
                      <span className="mono">#{m.case_id}</span>
                    )}
                    {" — "}
                    {m.error?.message ?? "Không thực hiện được."}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}
    </div>
  );
}
