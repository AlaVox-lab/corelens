"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Cột trái của hộp thư (#155): các cuộc trò chuyện gom theo người, ô tìm và chip "Chưa
// đọc". Trang ở máy chủ đã gom nhóm và dịch mỗi cuộc thành dòng chữ sẵn; ở đây chỉ lọc
// trên trình duyệt, không gọi dịch vụ. Bấm một cuộc là đổi `?ho-so=` trên địa chỉ trang —
// tải lại hay gửi đường dẫn đều mở đúng cuộc đó.

import { FileText, Hourglass, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

export type MucCuoc = {
  maHoSo: number;
  tieuDe: string;
  ma: string;
  /** Dòng xem trước: "Bạn: …", "Cường Lê: …" hay chính lời nhắn. */
  xemTruoc: string;
  luc: string;
  chuaDoc: number;
  choBan: boolean;
  /** Chữ để tìm: tên người, mã, tiêu đề. */
  tim: string;
};

export type NhomCuoc = {
  ma: string;
  /** `null`: không có dòng tiêu đề nhóm — hộp thư của người chỉ gửi yêu cầu. */
  ten: string | null;
  anh?: { chuCai: string; mau: number };
  cuoc: MucCuoc[];
};

function chuanHoa(chu: string): string {
  return chu.normalize("NFD").replace(/\p{M}/gu, "").replace(/[đĐ]/g, "d").toLowerCase();
}

export function DanhSachHopThu({ nhom, chon }: { nhom: NhomCuoc[]; chon: number | null }) {
  const [tim, datTim] = useState("");
  const [chiChuaDoc, datChiChuaDoc] = useState(false);
  const khoa = chuanHoa(tim.trim());
  const tongChuaDoc = nhom.reduce((t, n) => t + n.cuoc.filter((c) => c.chuaDoc > 0).length, 0);

  const loc = nhom
    .map((n) => ({
      ...n,
      cuoc: n.cuoc.filter(
        (c) => (!chiChuaDoc || c.chuaDoc > 0) && (!khoa || chuanHoa(c.tim).includes(khoa)),
      ),
    }))
    .filter((n) => n.cuoc.length > 0);

  return (
    <section className="ht-ds" aria-label="Các cuộc trò chuyện">
      <div className="ht-tim">
        <label className="o-tim">
          <Search aria-hidden />
          <input
            className="o-nhap"
            type="search"
            placeholder="Tìm người, mã hồ sơ"
            aria-label="Tìm cuộc trò chuyện"
            value={tim}
            onChange={(e) => datTim(e.target.value)}
          />
        </label>
        <div className="chip-hang">
          <button className="chip" type="button" aria-pressed={!chiChuaDoc} onClick={() => datChiChuaDoc(false)}>
            Tất cả
          </button>
          <button className="chip" type="button" aria-pressed={chiChuaDoc} onClick={() => datChiChuaDoc(true)}>
            Chưa đọc {tongChuaDoc}
          </button>
        </div>
      </div>

      <div className="ht-cuon">
        {loc.length === 0 && (
          <p className="nhat" style={{ fontSize: "13px", margin: "12px 8px" }}>
            {chiChuaDoc && !khoa ? "Không còn cuộc trò chuyện nào chưa đọc." : "Không có cuộc trò chuyện nào khớp."}
          </p>
        )}
        {loc.map((n) => (
          <div key={n.ma} style={{ display: "contents" }}>
            {n.ten !== null && (
              <div className="nhom-nguoi">
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
                key={c.maHoSo}
                className="cuoc"
                href={`/hop-thu?ho-so=${c.maHoSo}`}
                scroll={false}
                aria-current={c.maHoSo === chon ? "true" : undefined}
                data-chua-doc={c.chuaDoc > 0 ? "" : undefined}
              >
                <span className="icon-o">
                  <FileText aria-hidden />
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
    </section>
  );
}
