"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Bảng hàng đợi dùng chung cho buồng lái phòng ban và điều phối (#170).
//
// Trang ở máy chủ lấy một trang của hàng đợi, chia nhóm, dịch mỗi hồ sơ thành một dòng chữ
// sẵn. Từ #232 tìm, lọc, xếp và chuyển trang đều đi qua địa chỉ trang tới dịch vụ — lọc trên
// trình duyệt chỉ lọc được trang đang tải. Bảng này lo hàng công cụ, thu gọn từng nhóm, và
// dòng nào cũng bấm được nhờ một liên kết trong suốt phủ kín dòng — chuột, ngón tay, bàn
// phím đều mở đúng hồ sơ, không cần mã.
//
// Tệp này không biết tên trạng thái hay vai trò nào: nhóm, nhãn, màu đều do trang truyền.
//
// Chọn nhiều (#440) chỉ bật khi trang truyền `chonNhieu` — hàng đợi điều phối. Không truyền thì bảng y
// như trước: không cột ô chọn, không thanh thao tác. Chọn chỉ trong trang đang xem; đổi trang, tìm hay
// lọc là bỏ chọn — mở ngăn xem nhanh (`?xem=`) thì không.
//
// Ngăn xem nhanh mở ở màn rộng thì bảng co lại nhường chỗ chứ không bị ngăn che (#539). Cột phụ mang
// `data-phu` (1 ẩn trước, 2 ẩn sau) và CSS ẩn chúng theo bề rộng còn lại của khung bảng; cột hồ sơ và
// "Việc tiếp theo" không bao giờ ẩn.

import { AlarmClock, ChevronDown, CircleHelp, Clock, Inbox, MessageCircle, SearchX, Tag } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { MenuXepUrl, OTimUrl } from "@/components/loc-url";
import { ManRong } from "@/components/man-rong";
import { NhanTrangThai } from "@/components/nhan-trang-thai";
import {
  KetQuaHangLoatKhung,
  ThanhHangLoat,
  type ChonNhieu,
  type KetQuaDaChay,
} from "@/components/thanh-hang-loat";
import { CACH_XEP_HANG, KHOA_XEP_HANG, type MaXepHang } from "@/lib/trang";

export type DongHangDoi = {
  id: number;
  /** Đường mở hồ sơ trong ngăn xem nhanh (`?xem=`), giữ bộ lọc và trang (#233). */
  href: string;
  /** Trang đầy đủ của hồ sơ — Ctrl + bấm hay bấm chuột giữa trên dòng mở nó ở thẻ mới (#557). */
  dayDu: string;
  /** Hồ sơ đang mở trong ngăn. */
  dangXem?: boolean;
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
};

export type NhomHangDoi = {
  ma: string;
  /** `null`: bảng một nhóm, không có dòng tiêu đề nhóm. */
  ten: string | null;
  mau?: string;
  /** Số hồ sơ của nhóm trên cả hàng đợi đã lọc — trang này có thể chỉ chứa một phần. */
  tong?: number;
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

function Dong({
  d,
  cot,
  thuTu,
  chon,
}: {
  d: DongHangDoi;
  cot: CotHangDoi;
  thuTu: number;
  /** Có mặt khi bảng bật chọn nhiều. */
  chon?: { da: boolean; doi: () => void };
}) {
  return (
    <tr
      className="dong vao"
      data-qua={d.cuoi.muc === "qua" ? "" : undefined}
      data-dang-xem={d.dangXem ? "" : undefined}
      data-chon={chon?.da ? "" : undefined}
      style={{ ["--i" as string]: Math.min(thuTu, 6) }}
    >
      {chon && (
        // Ô chọn nằm trên liên kết phủ dòng: bấm ô (cả phần đệm quanh nó) chỉ chọn, không mở ngăn
        <td className="w o-chon-dong">
          <label>
            <input
              type="checkbox"
              checked={chon.da}
              onChange={chon.doi}
              aria-label={`Chọn hồ sơ ${d.ma}`}
              data-chon-ho-so={d.id}
            />
          </label>
        </td>
      )}
      <td>
        <div className="o-ho-so">
          {/* Bấm dòng mở ngăn xem nhanh ngay bên cạnh (#233); trang đầy đủ ở nút trong ngăn. Ctrl/⌘ +
              bấm hay bấm chuột giữa — cách quen để mở thẻ mới — thì mở trang đầy đủ, không phải bản
              sao của hàng đợi kèm ngăn (#557). */}
          <Link
            href={d.href}
            className="lk-dong"
            aria-label={`${d.ma} · ${d.tieuDe}`}
            aria-current={d.dangXem ? "true" : undefined}
            data-xem-dong={d.id}
            scroll={false}
            onClick={(e) => {
              if (!(e.ctrlKey || e.metaKey || e.shiftKey)) return;
              e.preventDefault();
              window.open(d.dayDu, "_blank", "noopener");
            }}
            onAuxClick={(e) => {
              if (e.button !== 1) return;
              e.preventDefault();
              window.open(d.dayDu, "_blank", "noopener");
            }}
          />
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
      {cot.nguoiGui && (
        <td className="w an-hep" data-phu="1">
          {d.nguoiGui}
        </td>
      )}
      {cot.nguoiXuLy && (
        <td className="w an-hep" data-phu="2">
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
        <td className="w an-hep" data-phu="1">
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
        <td className="w" data-phu="2">
          <NhanTrangThai ma={d.trangThai.code} nhan={d.trangThai.label} />
        </td>
      )}
      {cot.tiepTheo && (
        <td className="w an-hep cot-tiep">
          {d.tiepTheo ? (
            <span className="viec-tiep" data-cua-toi={d.tiepTheo.cuaToi ? "" : undefined}>
              {d.tiepTheo.chu}
            </span>
          ) : (
            <span className="viec-tiep">—</span>
          )}
        </td>
      )}
      <td className="w cot-cuoi" style={{ textAlign: "right" }}>
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
  xepMacDinh,
  chip,
  chan,
  xoaLoc,
  khiTrong,
  ngan,
  chonNhieu,
}: {
  /** Một trang của hàng đợi, dịch vụ đã lọc và xếp. */
  nhom: NhomHangDoi[];
  cot: CotHangDoi;
  /** Bên trái thanh công cụ — dải số lọc theo trạng thái hay nhóm. */
  trai?: React.ReactNode;
  /** Giữa ô tìm và menu xếp — ô chọn bộ lọc, nút "Giao cho tôi". */
  phai?: React.ReactNode;
  goiYTim: string;
  xepMacDinh: MaXepHang;
  /** Chip các bộ lọc đang bật, dưới hàng công cụ. */
  chip?: React.ReactNode;
  /** Dòng chân "Đang xem … trên …" và nút chuyển trang. */
  chan?: React.ReactNode;
  /** Có bộ lọc đang bật: đường dẫn bỏ hết bộ lọc, cho màn trống do lọc. */
  xoaLoc: string | null;
  khiTrong: { tieuDe: string; cau: string };
  /** Ngăn xem nhanh của hồ sơ đang mở (#233), cạnh bảng. */
  ngan?: React.ReactNode;
  /** Bật cột ô chọn và thanh thao tác hàng loạt (#440). Không truyền: bảng như cũ. */
  chonNhieu?: ChonNhieu;
}) {
  const [thu, datThu] = useState<Set<string>>(new Set());
  const loc = nhom.filter((n) => n.dong.length > 0);

  // Lựa chọn gắn với bộ lọc và trang lúc chọn: địa chỉ đổi (trừ `xem`) thì coi như chưa chọn gì
  const sp = useSearchParams();
  const khoaChon = [...sp.entries()].filter(([k]) => k !== "xem").map(([k, v]) => `${k}=${v}`).join("&");
  const [chon, datChon] = useState<{ khoa: string; ids: ReadonlySet<number> }>({ khoa: khoaChon, ids: new Set() });
  const [ketQua, datKetQua] = useState<KetQuaDaChay | null>(null);
  const idsChon = chon.khoa === khoaChon ? chon.ids : new Set<number>();
  const moiDong = loc.flatMap((n) => n.dong);
  const dangChon = moiDong.filter((d) => idsChon.has(d.id));
  const chonHet = moiDong.length > 0 && dangChon.length === moiDong.length;

  function doiChon(ids: number[], bat: boolean) {
    // Cập nhật theo giá trị mới nhất: kết quả hàng loạt về sau một lần gọi mạng, lúc đó bảng đã dựng lại
    datChon((cu) => {
      const moi = new Set(cu.khoa === khoaChon ? cu.ids : []);
      for (const id of ids) {
        if (bat) moi.add(id);
        else moi.delete(id);
      }
      return { khoa: khoaChon, ids: moi };
    });
  }

  const soCot =
    2 +
    (chonNhieu ? 1 : 0) +
    [cot.nguoiGui, cot.nguoiXuLy, cot.loai, cot.trangThai, cot.tiepTheo].filter(Boolean).length;

  return (
    <>
      <div className="hang-cong-cu khong-in">
        {trai}
        <div className="phai">
          <OTimUrl goiY={goiYTim} />
          {phai}
          <MenuXepUrl cacCach={CACH_XEP_HANG} macDinh={xepMacDinh} khoaNho={KHOA_XEP_HANG} />
        </div>
      </div>
      {chip}

      {chonNhieu && (
        <KetQuaHangLoatKhung ketQua={ketQua} goc={chonNhieu.goc} khiDong={() => datKetQua(null)} />
      )}

      {/* `data-co-ngan`: ngăn xem nhanh đang mở — CSS chừa chỗ bên phải cho nó ở màn rộng (#539). Dấu có
          ngay ở bản dựng máy chủ, nên mở thẳng đường dẫn `?xem=` không thấy bảng co lại sau khi tải */}
      <div className="the khung-bang" data-co-ngan={ngan ? "" : undefined}>
        {loc.length === 0 ? (
          xoaLoc ? (
            // Trống vì bộ lọc (#234): nói rõ là do lọc, và cho xóa lọc ngay tại chỗ
            <ManRong
              icon={SearchX}
              tieuDe="Không có hồ sơ nào khớp"
              cau="Không hồ sơ nào trong hàng đợi khớp ô tìm và bộ lọc đang bật."
            >
              <Link className="nut" href={xoaLoc} scroll={false}>
                Xóa bộ lọc
              </Link>
            </ManRong>
          ) : (
            <ManRong icon={Inbox} tieuDe={khiTrong.tieuDe} cau={khiTrong.cau} />
          )
        ) : (
          <table className="bang" data-chon-nhieu={chonNhieu ? "" : undefined}>
            <thead>
              <tr>
                {chonNhieu && (
                  <th className="w o-chon-dong">
                    <label>
                      <input
                        type="checkbox"
                        checked={chonHet}
                        // Chọn một phần: không có thuộc tính HTML nào cho trạng thái này, đặt bằng mã
                        ref={(o) => {
                          if (o) o.indeterminate = dangChon.length > 0 && !chonHet;
                        }}
                        onChange={() => doiChon(moiDong.map((d) => d.id), !chonHet)}
                        aria-label="Chọn tất cả hồ sơ trên trang này"
                      />
                      <span className="chi-man-hep">Chọn tất cả trên trang này</span>
                    </label>
                  </th>
                )}
                <th>Hồ sơ</th>
                {cot.nguoiGui && (
                  <th className="w an-hep" data-phu="1">
                    Người gửi
                  </th>
                )}
                {cot.nguoiXuLy && (
                  <th className="w an-hep" data-phu="2">
                    Người xử lý
                  </th>
                )}
                {cot.loai && (
                  <th className="w an-hep" data-phu="1">
                    Loại
                  </th>
                )}
                {cot.trangThai && (
                  <th className="w" data-phu="2">
                    Trạng thái
                  </th>
                )}
                {cot.tiepTheo && <th className="w an-hep cot-tiep">Việc tiếp theo</th>}
                <th className="w cot-cuoi" style={{ textAlign: "right" }}>
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
                          <span className="so">{n.tong ?? n.dong.length}</span>
                        </button>
                      </th>
                    </tr>
                  )}
                  {!daThu &&
                    n.dong.map((d, i) => (
                      <Dong
                        key={d.id}
                        d={d}
                        cot={cot}
                        thuTu={i}
                        chon={
                          chonNhieu
                            ? { da: idsChon.has(d.id), doi: () => doiChon([d.id], !idsChon.has(d.id)) }
                            : undefined
                        }
                      />
                    ))}
                </tbody>
              );
            })}
          </table>
        )}
      </div>
      {chonNhieu && (
        <ThanhHangLoat
          chonNhieu={chonNhieu}
          dangChon={dangChon}
          boChon={(ids) => (ids ? doiChon(ids, false) : datChon({ khoa: khoaChon, ids: new Set() }))}
          khiXong={datKetQua}
        />
      )}
      {chan}
      {ngan}
    </>
  );
}
