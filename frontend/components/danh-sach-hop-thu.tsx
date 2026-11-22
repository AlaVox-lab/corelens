"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Cột trái của hộp thư (#155): các cuộc trò chuyện gom theo người, ô tìm và chip "Chưa
// đọc" — thêm chip "Nội bộ" khi có cuộc nội bộ (#156). Trang ở máy chủ đã gom nhóm và dịch
// mỗi cuộc thành dòng chữ sẵn. Bấm một cuộc là đổi `?ho-so=` (và `kenh=`) trên địa chỉ trang
// — tải lại hay gửi đường dẫn đều mở đúng cuộc đó.
//
// Từ #232 hộp thư có phân trang: ô tìm (`?q=`), chip (`?loc=`) và trang (`?trang=`) cũng nằm
// trên địa chỉ trang và đi tới dịch vụ. Mở một cuộc giữ nguyên bộ lọc và trang đang xem.

import { FileText, Hourglass, Lock } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { OTimUrl } from "@/components/loc-url";
import { KENH_NOI_BO, LOC_CHUA_DOC, LOC_NOI_BO } from "@/lib/hop-thu";

export type MucCuoc = {
  maHoSo: number;
  /** Cuộc nội bộ giữa nhân viên (#156). */
  noiBo: boolean;
  tieuDe: string;
  ma: string;
  /** Dòng xem trước: "Bạn: …", "Cường Lê: …" hay chính lời nhắn. */
  xemTruoc: string;
  luc: string;
  chuaDoc: number;
  choBan: boolean;
};

export type NhomCuoc = {
  ma: string;
  /** `null`: không có dòng tiêu đề nhóm — hộp thư của người chỉ gửi yêu cầu. */
  ten: string | null;
  anh?: { chuCai: string; mau: number };
  /** Nhóm các cuộc nội bộ — đầu nhóm là ổ khóa thay cho ảnh người. */
  noiBo?: boolean;
  cuoc: MucCuoc[];
};

export function DanhSachHopThu({
  nhom,
  chon,
  soChuaDoc,
  soNoiBo,
  chan,
}: {
  /** Các cuộc của trang đang xem, dịch vụ đã lọc. */
  nhom: NhomCuoc[];
  /** Cuộc đang mở: hồ sơ và kênh. */
  chon: { maHoSo: number; noiBo: boolean } | null;
  /** Số cuộc còn tin chưa đọc, số cuộc nội bộ — trên cả hộp thư khớp ô tìm. */
  soChuaDoc: number;
  soNoiBo: number;
  /** Dòng chân "Đang xem … trên …" và nút chuyển trang. */
  chan?: React.ReactNode;
}) {
  const sp = useSearchParams();
  const loc = sp.get("loc");

  /** Đường dẫn giữ bộ lọc và trang đang xem, đổi vài tham số. */
  const duong = (doi: Record<string, string | null>) => {
    const q = new URLSearchParams(sp.toString());
    for (const [ten, gt] of Object.entries(doi)) {
      if (gt) q.set(ten, gt);
      else q.delete(ten);
    }
    return `/hop-thu?${q.toString()}`;
  };
  const duongLoc = (gt: string | null) => duong({ loc: gt, trang: null });
  const duongCuoc = (maHoSo: number, noiBo: boolean) =>
    duong({ "ho-so": String(maHoSo), kenh: noiBo ? KENH_NOI_BO : null });

  return (
    <section className="ht-ds" aria-label="Các cuộc trò chuyện">
      <div className="ht-tim">
        <OTimUrl goiY="Tìm người, mã hồ sơ" nhan="Tìm cuộc trò chuyện" />
        <nav className="chip-hang" aria-label="Lọc cuộc trò chuyện">
          <Link className="chip" href={duongLoc(null)} scroll={false} aria-current={!loc ? "true" : undefined}>
            Tất cả
          </Link>
          <Link className="chip" href={duongLoc(LOC_CHUA_DOC)} scroll={false} aria-current={loc === LOC_CHUA_DOC ? "true" : undefined}>
            Chưa đọc {soChuaDoc}
          </Link>
          {(soNoiBo > 0 || loc === LOC_NOI_BO) && (
            <Link className="chip" href={duongLoc(LOC_NOI_BO)} scroll={false} aria-current={loc === LOC_NOI_BO ? "true" : undefined}>
              <Lock aria-hidden />
              Nội bộ
            </Link>
          )}
        </nav>
      </div>

      <div className="ht-cuon">
        {nhom.length === 0 && (
          <p className="nhat" style={{ fontSize: "13px", margin: "12px 8px" }}>
            {loc === LOC_CHUA_DOC && !sp.get("q")
              ? "Không còn cuộc trò chuyện nào chưa đọc."
              : "Không có cuộc trò chuyện nào khớp."}
          </p>
        )}
        {nhom.map((n) => (
          <div key={n.ma} style={{ display: "contents" }}>
            {n.ten !== null && (
              <div className="nhom-nguoi">
                {n.noiBo && (
                  <span className="icon-o" data-noi-bo="" style={{ width: "24px", height: "24px", borderRadius: "8px" }} aria-hidden>
                    <Lock />
                  </span>
                )}
                {n.anh && (
                  <span className="av av-nho" data-c={n.anh.mau} aria-hidden>
                    {n.anh.chuCai}
                  </span>
                )}
                <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {n.ten}
                </span>
                <span className="phai">{n.cuoc.length} hồ sơ</span>
              </div>
            )}
            {n.cuoc.map((c) => (
              <Link
                key={`${c.maHoSo}-${c.noiBo}`}
                className="cuoc"
                href={duongCuoc(c.maHoSo, c.noiBo)}
                scroll={false}
                aria-current={chon && c.maHoSo === chon.maHoSo && c.noiBo === chon.noiBo ? "true" : undefined}
                data-chua-doc={c.chuaDoc > 0 ? "" : undefined}
              >
                <span className="icon-o" data-noi-bo={c.noiBo ? "" : undefined}>
                  {c.noiBo ? <Lock aria-label="Nội bộ" /> : <FileText aria-hidden />}
                </span>
                <span className="than">
                  <span className="d1">
                    <b>{c.tieuDe}</b>
                    <time>{c.luc}</time>
                  </span>
                  <span className="d2">
                    <p>{c.xemTruoc}</p>
                    {c.chuaDoc > 0 && (
                      <span className="dem-chua-doc" aria-label={`${c.chuaDoc} tin chưa đọc`}>
                        {c.chuaDoc}
                      </span>
                    )}
                  </span>
                  <span className="d2" style={{ marginTop: "4px" }}>
                    <span className="mono nhat" style={{ fontSize: "12px" }}>
                      {c.ma}
                    </span>
                    {c.choBan && (
                      <span className="dang-cho">
                        <Hourglass aria-hidden />
                        Đang chờ bạn
                      </span>
                    )}
                  </span>
                </span>
              </Link>
            ))}
          </div>
        ))}
      </div>
      {chan}
    </section>
  );
}
