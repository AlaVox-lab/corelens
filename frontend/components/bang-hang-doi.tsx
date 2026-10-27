"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Bảng hàng đợi dùng chung cho buồng lái phòng ban và điều phối (#170).
//
// Trang ở máy chủ lấy hàng đợi, chia nhóm, dịch mỗi hồ sơ thành một dòng chữ sẵn; bảng
// này chỉ lo phần thuộc về trình duyệt: ô tìm lọc ngay khi gõ, thu gọn từng nhóm. Cả dòng
// bấm được nhờ một liên kết trong suốt phủ kín dòng — chuột, ngón tay, bàn phím đều mở
// đúng hồ sơ, không cần mã. Không gọi dịch vụ lần nào — hàng đợi vài chục hồ sơ đã nằm sẵn trên
// trang. Tìm không phân biệt dấu: gõ "may in" vẫn ra "Máy in".
//
// Tệp này không biết tên trạng thái hay vai trò nào: nhóm, nhãn, màu đều do trang truyền.

import { AlarmClock, ChevronDown, CircleHelp, Clock, Inbox, MessageCircle, Search, Tag } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { ManRong } from "@/components/man-rong";
import { MenuXep, type CachXep } from "@/components/viec-can-lam";
import { NhanTrangThai } from "@/components/nhan-trang-thai";

export type DongHangDoi = {
  id: number;
  href: string;
  ma: string;
  tieuDe: string;
  /** Dòng phụ dưới tiêu đề, sau mã hồ sơ: loại yêu cầu hay người gửi. */
  phu: string;
  /** Lời nhắn cuối là của người gửi (#128): người gửi đang chờ trả lời. */
  choTraLoi: boolean;
  /** Hồ sơ do chính người đang xem gửi — ở hàng đợi điều phối, người khác phải lo (#154). */
  cuaMinh?: boolean;
  nguoiGui?: string;
  /** `null`: chưa giao ai. Không có khóa: bảng không có cột người xử lý. */
  giao?: { ten: string; mau: number; chuCai: string } | null;
  /** Loại yêu cầu; `null` là chưa rõ loại. Không có khóa: bảng không có cột loại. */
  loai?: string | null;
  trangThai?: { code: string; label: string };
  cuoi: { chu: string; muc?: "qua" | "sap" | "dung" };
  /**
   * Cột "Việc tiếp theo" (#231): bước chính đang chờ chính người xem (`cuaToi`), hay việc
   * đang chờ ai khác. Nhãn lấy từ dữ liệu (`next_step_label`, `auto_transition`).
   */
  tiepTheo?: { chu: string; cuaToi: boolean } | null;
  /** Khóa sắp xếp (#231): 0 quá hạn, 1 sắp hạn, 2 bình thường; mốc chờ và mốc tạo (ms). */
  xep: { gap: 0 | 1 | 2; cho: number; moi: number };
};

export type NhomHangDoi = {
  ma: string;
  /** `null`: bảng một nhóm, không có dòng tiêu đề nhóm. */
  ten: string | null;
  mau?: string;
  dong: DongHangDoi[];
};

export type CotHangDoi = {
  nguoiGui?: boolean;
  nguoiXuLy?: boolean;
  loai?: boolean;
  trangThai?: boolean;
  tiepTheo?: boolean;
  /** Tiêu đề cột cuối: "Hạn" hay "Đã chờ". */
  cuoi: string;
};

/** Cách xếp trong từng nhóm của hàng đợi (#231). Mặc định độ gấp, cùng quy tắc với trang chủ. */
const CACH_XEP_HANG = [
  { ma: "gap", ten: "Độ gấp", moTa: "Quá hạn → sắp hạn → chờ lâu nhất" },
  { ma: "cho", ten: "Chờ lâu nhất", moTa: "Hồ sơ nằm im lâu nhất lên trước" },
  { ma: "moi", ten: "Mới nhất", moTa: "Hồ sơ vừa tạo lên trước" },
] as const satisfies readonly CachXep<string>[];
type MaXepHang = (typeof CACH_XEP_HANG)[number]["ma"];
const KHOA_XEP_HANG = "dxlab-xep-hang-doi";
const SO_SANH_HANG: Record<MaXepHang, (a: DongHangDoi, b: DongHangDoi) => number> = {
  gap: (a, b) => a.xep.gap - b.xep.gap || a.xep.cho - b.xep.cho,
  cho: (a, b) => a.xep.cho - b.xep.cho,
  moi: (a, b) => b.xep.moi - a.xep.moi,
};

/** Bỏ dấu và viết thường, để tìm "may in" ra "Máy in", "dung" ra "Dũng". */
function chuanHoa(chu: string): string {
  return chu.normalize("NFD").replace(/\p{M}/gu, "").replace(/đ/g, "d").replace(/Đ/g, "d").toLowerCase();
}

function Dong({ d, cot, thuTu }: { d: DongHangDoi; cot: CotHangDoi; thuTu: number }) {
  return (
    <tr
      className="dong vao"
      data-qua={d.cuoi.muc === "qua" ? "" : undefined}
      style={{ ["--i" as string]: Math.min(thuTu, 12) }}
    >
      <td>
        <div className="o-ho-so">
          <Link href={d.href} className="lk-dong" aria-label={`${d.ma} · ${d.tieuDe}`} />
          <b title={d.tieuDe}>{d.tieuDe}</b>
          <span>
            <span className="mono">{d.ma}</span> · {d.phu}
            {d.cuaMinh && (
              <>
                {" · "}
                <span style={{ color: "var(--f-p-ink)", fontWeight: 600 }}>Bạn gửi — người khác điều phối</span>
              </>
            )}
            {d.choTraLoi && (
              <>
                {" · "}
                <span className="dang-cho">
                  <MessageCircle aria-hidden />
                  Người gửi đang chờ trả lời
                </span>
              </>
            )}
          </span>
        </div>
      </td>
      {cot.nguoiGui && <td className="w an-hep">{d.nguoiGui}</td>}
      {cot.nguoiXuLy && (
        <td className="w an-hep">
          {d.giao ? (
            <span style={{ display: "inline-flex", gap: "6px", alignItems: "center" }}>
              <span className="av av-nho" data-c={d.giao.mau} aria-hidden>
                {d.giao.chuCai}
              </span>
              {d.giao.ten}
            </span>
          ) : (
            <span className="nhat">Chưa giao cho ai</span>
          )}
        </td>
      )}
      {cot.loai && (
        <td className="w an-hep">
          {d.loai ? (
            <span className="nhan-loai">
              <Tag aria-hidden />
              {d.loai}
            </span>
          ) : (
            <span className="nhan-loai" style={{ color: "var(--f-a-ink)" }}>
              <CircleHelp aria-hidden />
              Chưa rõ loại
            </span>
          )}
        </td>
      )}
      {cot.trangThai && d.trangThai && (
        <td className="w">
          <NhanTrangThai ma={d.trangThai.code} nhan={d.trangThai.label} />
        </td>
      )}
      {cot.tiepTheo && (
        <td className="w an-hep">
          {d.tiepTheo ? (
            <span className="viec-tiep" data-cua-toi={d.tiepTheo.cuaToi ? "" : undefined}>
              {d.tiepTheo.chu}
            </span>
          ) : (
            <span className="viec-tiep">—</span>
          )}
        </td>
      )}
      <td className="w" style={{ textAlign: "right" }}>
        <span className="chu-han" data-muc={d.cuoi.muc}>
          {/* Dấu hiệu bằng biểu tượng kèm chữ, không chỉ bằng màu (#231) */}
          {d.cuoi.muc === "qua" ? <AlarmClock aria-hidden /> : d.cuoi.muc === "sap" ? <Clock aria-hidden /> : null}
          {d.cuoi.chu}
        </span>
      </td>
    </tr>
  );
}

export function BangHangDoi({
  nhom,
  cot,
  trai,
  phai,
  goiYTim,
  khiTrong,
}: {
  nhom: NhomHangDoi[];
  cot: CotHangDoi;
  /** Bên trái thanh công cụ — hàng tab lọc trạng thái. */
  trai?: React.ReactNode;
  /** Bên phải, sau ô tìm — nút "Giao cho tôi". */
  phai?: React.ReactNode;
  goiYTim: string;
  khiTrong: { tieuDe: string; cau: string };
}) {
  const [tim, datTim] = useState("");
  const [xep, datXep] = useState<MaXepHang>("gap");
  useEffect(() => {
    try {
      const luu = localStorage.getItem(KHOA_XEP_HANG) as MaXepHang | null;
      if (luu && luu in SO_SANH_HANG) datXep(luu);
    } catch {
      // Trình duyệt chặn lưu trữ: giữ cách xếp mặc định
    }
  }, []);
  const chonXep = (m: MaXepHang) => {
    datXep(m);
    try {
      localStorage.setItem(KHOA_XEP_HANG, m);
    } catch {
      // Vẫn xếp được trong lần mở này, chỉ không nhớ
    }
  };
  const [thu, datThu] = useState<Set<string>>(new Set());
  const khoa = chuanHoa(tim.trim());

  const loc = nhom
    .map((n) => ({
      ...n,
      dong: khoa
        ? n.dong.filter((d) => chuanHoa(`${d.ma} ${d.tieuDe} ${d.nguoiGui ?? ""} ${d.phu}`).includes(khoa))
        : n.dong,
    }))
    .map((n) => ({ ...n, dong: [...n.dong].sort(SO_SANH_HANG[xep]) }))
    .filter((n) => n.dong.length > 0);

  const soCot =
    2 + [cot.nguoiGui, cot.nguoiXuLy, cot.loai, cot.trangThai, cot.tiepTheo].filter(Boolean).length;

  return (
    <>
      <div className="hang-cong-cu khong-in">
        {trai}
        <div className="phai">
          <label className="o-tim">
            <Search aria-hidden />
            <input
              className="o-nhap"
              type="search"
              placeholder={goiYTim}
              aria-label="Tìm hồ sơ"
              value={tim}
              onChange={(e) => datTim(e.target.value)}
            />
          </label>
          <MenuXep dang={xep} chon={chonXep} cacCach={CACH_XEP_HANG} />
          {phai}
        </div>
      </div>

      <div className="the">
        {loc.length === 0 ? (
          khoa ? (
            // Trống vì ô tìm (#234): nói rõ là do lọc, và cho xóa lọc ngay tại chỗ
            <ManRong
              icon={Search}
              tieuDe="Không có hồ sơ nào khớp"
              cau={`Không hồ sơ nào trong danh sách có mã, tiêu đề hay người gửi chứa “${tim.trim()}”.`}
            >
              <button className="nut" type="button" onClick={() => datTim("")}>
                Xóa tìm kiếm
              </button>
            </ManRong>
          ) : (
            <ManRong icon={Inbox} tieuDe={khiTrong.tieuDe} cau={khiTrong.cau} />
          )
        ) : (
          <table className="bang">
            <thead>
              <tr>
                <th>Hồ sơ</th>
                {cot.nguoiGui && <th className="w an-hep">Người gửi</th>}
                {cot.nguoiXuLy && <th className="w an-hep">Người xử lý</th>}
                {cot.loai && <th className="w an-hep">Loại</th>}
                {cot.trangThai && <th className="w">Trạng thái</th>}
                {cot.tiepTheo && <th className="w an-hep">Việc tiếp theo</th>}
                <th className="w" style={{ textAlign: "right" }}>
                  {cot.cuoi}
                </th>
              </tr>
            </thead>
            {loc.map((n) => {
              const daThu = thu.has(n.ma);
              return (
                <tbody key={n.ma}>
                  {n.ten !== null && (
                    <tr className="nhom-hang">
                      <th colSpan={soCot} scope="rowgroup">
                        <button
                          type="button"
                          aria-expanded={!daThu}
                          onClick={() =>
                            datThu((cu) => {
                              const moi = new Set(cu);
                              if (daThu) moi.delete(n.ma);
                              else moi.add(n.ma);
                              return moi;
                            })
                          }
                        >
                          <ChevronDown aria-hidden />
                          <span className="dau-nhom" style={{ background: n.mau }} />
                          {n.ten}
                          <span className="so">{n.dong.length}</span>
                        </button>
                      </th>
                    </tr>
                  )}
                  {!daThu && n.dong.map((d, i) => <Dong key={d.id} d={d} cot={cot} thuTu={i} />)}
                </tbody>
              );
            })}
          </table>
        )}
      </div>
    </>
  );
}
