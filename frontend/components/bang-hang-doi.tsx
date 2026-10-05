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

import { ChevronDown, CircleHelp, Inbox, MessageCircle, Search, Tag } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

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
  nguoiGui?: string;
  /** `null`: chưa giao ai. Không có khóa: bảng không có cột người xử lý. */
  giao?: { ten: string; mau: number; chuCai: string } | null;
  /** Loại yêu cầu; `null` là chưa rõ loại. Không có khóa: bảng không có cột loại. */
  loai?: string | null;
  trangThai?: { code: string; label: string };
  cuoi: { chu: string; muc?: "qua" | "dung" };
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
  /** Tiêu đề cột cuối: "Hạn" hay "Đã chờ". */
  cuoi: string;
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
            <span className="nhat">Chưa giao ai</span>
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
      <td className="w" style={{ textAlign: "right" }}>
        <span className="chu-han" data-muc={d.cuoi.muc}>
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
  const [thu, datThu] = useState<Set<string>>(new Set());
  const khoa = chuanHoa(tim.trim());

  const loc = nhom
    .map((n) => ({
      ...n,
      dong: khoa
        ? n.dong.filter((d) => chuanHoa(`${d.ma} ${d.tieuDe} ${d.nguoiGui ?? ""} ${d.phu}`).includes(khoa))
        : n.dong,
    }))
    .filter((n) => n.dong.length > 0);

  const soCot =
    2 + [cot.nguoiGui, cot.nguoiXuLy, cot.loai, cot.trangThai].filter(Boolean).length;

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
          {phai}
        </div>
      </div>

      <div className="the">
        {loc.length === 0 ? (
          <div className="rong">
            <span className="icon-to">
              {khoa ? <Search aria-hidden /> : <Inbox aria-hidden />}
            </span>
            <h2>{khoa ? "Không có hồ sơ nào khớp" : khiTrong.tieuDe}</h2>
            <p>{khoa ? `Không hồ sơ nào trong danh sách có mã, tiêu đề hay người gửi chứa “${tim.trim()}”.` : khiTrong.cau}</p>
          </div>
        ) : (
          <table className="bang">
            <thead>
              <tr>
                <th>Hồ sơ</th>
                {cot.nguoiGui && <th className="w an-hep">Người gửi</th>}
                {cot.nguoiXuLy && <th className="w an-hep">Người xử lý</th>}
                {cot.loai && <th className="w an-hep">Loại</th>}
                {cot.trangThai && <th className="w">Trạng thái</th>}
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
