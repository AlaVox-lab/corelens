"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khối "Tệp đính kèm" trên trang hồ sơ (#80).
//
// Dùng chung cho ba cổng: ai mở được hồ sơ thì thấy danh sách và tải về được. Chỉ người gửi, ở
// những bước dịch vụ cho phép (`choPhep` lấy từ `can_attach`, không do giao diện suy ra), mới
// có thêm ô chọn tệp và nút tải lên. Tải về và tải lên đi qua máy chủ Next.js — trình duyệt
// không bao giờ nói chuyện với kho tệp.

import { Download, FileText, Paperclip, ShieldAlert } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { OChonTep } from "@/components/o-chon-tep";
import { dungLuong, ngayGio } from "@/lib/dinh-dang";
import { bienHoMau } from "@/lib/trang-thai";
import type { ChinhSachTep, TepDinhKem } from "@/lib/kieu";

export function KhoiTepDinhKem({
  maHoSo,
  tep,
  choPhep,
  chinhSach,
}: {
  maHoSo: number;
  tep: TepDinhKem[];
  choPhep: boolean;
  /** Giới hạn do dịch vụ trả. Không nạp được thì chỉ xem, không thêm tệp. */
  chinhSach: ChinhSachTep | null;
}) {
  const router = useRouter();
  const [chon, datChon] = useState<File[]>([]);
  const [dangTai, datDangTai] = useState(false);
  const [loi, datLoi] = useState("");

  const them = choPhep && chinhSach !== null;
  if (tep.length === 0 && !them) return null;

  async function taiLen() {
    datDangTai(true);
    datLoi("");
    try {
      const bieuMau = new FormData();
      for (const f of chon) bieuMau.append("files", f);
      const phanHoi = await fetch(`/api/tep/ho-so/${maHoSo}`, { method: "POST", body: bieuMau });
      const than = (await phanHoi.json().catch(() => null)) as {
        ok?: boolean;
        thongDiep?: string;
      } | null;
      if (!phanHoi.ok || !than?.ok) {
        datLoi(than?.thongDiep ?? "Không tải được tệp lên. Thử lại sau ít phút.");
        return;
      }
      datChon([]);
      router.refresh();
    } catch {
      datLoi("Hệ thống không phản hồi. Thử lại sau ít phút.");
    } finally {
      datDangTai(false);
    }
  }

  return (
    <div className="the khoi khong-in" id="khoi-tep-dinh-kem">
      <div className="khoi-dau">
        <Paperclip aria-hidden /> Tệp đính kèm
        {tep.length > 0 && <span className="mono nhat"> · {tep.length}</span>}
      </div>

      {tep.length > 0 ? (
        <ul
          style={{ margin: 0, padding: "0 20px 14px", listStyle: "none", display: "grid", gap: "6px" }}
        >
          {tep.map((t) => (
            <li
              key={t.id}
              style={{
                display: "flex",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "4px 10px",
                fontSize: "13.5px",
              }}
            >
              <FileText aria-hidden size={16} />
              <a
                href={`/api/tep/${t.id}`}
                download={t.filename}
                style={{ flex: "1 1 180px", minWidth: 0, overflowWrap: "anywhere" }}
              >
                {t.filename} <Download aria-hidden size={13} style={{ verticalAlign: "-1px" }} />
              </a>
              <span className="mono nhat" style={{ fontSize: "12px" }}>
                {dungLuong(t.size_bytes)} · {t.uploaded_by_label} · {ngayGio(t.created_at)}
              </span>
              {/* #248: tệp có macro vẫn nhận, nhưng người mở phải biết trước */}
              {t.has_macro && (
                <span className="nhan-tt" style={{ ...bienHoMau("a"), fontSize: "12px" }} data-nhan="co-macro">
                  <ShieldAlert aria-hidden size={13} /> có macro — cẩn thận khi mở
                </span>
              )}
              {t.scan_status === "unscanned" && (
                <span className="nhan-tt" style={{ ...bienHoMau("n"), fontSize: "12px" }} data-nhan="chua-quet">
                  chưa quét mã độc
                </span>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p style={{ margin: 0, padding: "0 20px 14px", fontSize: "13px", color: "var(--ink-2)" }}>
          Hồ sơ chưa có tệp nào.
        </p>
      )}

      {them && chinhSach && (
        <div style={{ padding: "0 20px 17px", display: "grid", gap: "9px" }}>
          <OChonTep
            chinhSach={chinhSach}
            tepDaChon={chon}
            doi={datChon}
            daCo={tep.length}
            voHieu={dangTai}
          />
          {loi && (
            <p
              role="alert"
              style={{
                margin: 0,
                padding: "9px 12px",
                borderRadius: "9px",
                background: "var(--f-r-bg)",
                border: "1px solid var(--f-r-line)",
                color: "var(--f-r-ink)",
                fontSize: "13px",
                lineHeight: 1.55,
              }}
            >
              {loi}
            </p>
          )}
          {chon.length > 0 && (
            <div>
              <button
                type="button"
                className="nut"
                data-loai="chinh"
                disabled={dangTai}
                onClick={taiLen}
              >
                {dangTai ? "Đang tải lên…" : `Tải lên ${chon.length} tệp`}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
