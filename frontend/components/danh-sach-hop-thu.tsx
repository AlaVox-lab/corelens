"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Cột trái của hộp thư (#155): các cuộc trò chuyện gom theo người, ô tìm và chip "Chưa
// đọc" — thêm chip "Nội bộ" khi có cuộc nội bộ (#156). Trang ở máy chủ đã gom nhóm và dịch
// mỗi cuộc thành dòng chữ sẵn; ở đây chỉ lọc trên trình duyệt, không gọi dịch vụ. Bấm một
// cuộc là đổi `?ho-so=` (và `kenh=`) trên địa chỉ trang — tải lại hay gửi đường dẫn đều mở
// đúng cuộc đó.

import { FileText, Hourglass, Lock, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { duongCuoc } from "@/lib/hop-thu";

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
  /** Chữ để tìm: tên người, mã, tiêu đề. */
  tim: string;
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

function chuanHoa(chu: string): string {
  return chu.normalize("NFD").replace(/\p{M}/gu, "").replace(/[đĐ]/g, "d").toLowerCase();
}

type Loc = "tat-ca" | "chua-doc" | "noi-bo";

export function DanhSachHopThu({
  nhom,
  chon,
}: {
  nhom: NhomCuoc[];
  /** Cuộc đang mở: hồ sơ và kênh. */
  chon: { maHoSo: number; noiBo: boolean } | null;
}) {
  const [tim, datTim] = useState("");
  const [loc, datLoc] = useState<Loc>("tat-ca");
  const khoa = chuanHoa(tim.trim());
  const tatCa = nhom.flatMap((n) => n.cuoc);
  const tongChuaDoc = tatCa.filter((c) => c.chuaDoc > 0).length;
  const coNoiBo = tatCa.some((c) => c.noiBo);

  const conLai = nhom
    .map((n) => ({
      ...n,
      cuoc: n.cuoc.filter(
        (c) =>
          (loc !== "chua-doc" || c.chuaDoc > 0) &&
          (loc !== "noi-bo" || c.noiBo) &&
          (!khoa || chuanHoa(c.tim).includes(khoa)),
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
          <button className="chip" type="button" aria-pressed={loc === "tat-ca"} onClick={() => datLoc("tat-ca")}>
            Tất cả
          </button>
          <button
            className="chip"
            type="button"
            aria-pressed={loc === "chua-doc"}
            onClick={() => datLoc("chua-doc")}
          >
            Chưa đọc {tongChuaDoc}
          </button>
          {coNoiBo && (
            <button className="chip" type="button" aria-pressed={loc === "noi-bo"} onClick={() => datLoc("noi-bo")}>
              <Lock aria-hidden />
              Nội bộ
            </button>
          )}
        </div>
      </div>

      <div className="ht-cuon">
        {conLai.length === 0 && (
          <p className="nhat" style={{ fontSize: "13px", margin: "12px 8px" }}>
            {loc === "chua-doc" && !khoa
              ? "Không còn cuộc trò chuyện nào chưa đọc."
              : "Không có cuộc trò chuyện nào khớp."}
          </p>
        )}
        {conLai.map((n) => (
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
    </section>
  );
}
