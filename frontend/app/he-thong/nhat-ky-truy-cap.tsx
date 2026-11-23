"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khối "Nhật ký truy cập dữ liệu cá nhân" trên màn Hệ thống (#431): ai đã xem hồ sơ, liên hệ người gửi, tệp đính
// kèm của người khác, ai đã xuất nhật ký sự kiện — lúc nào, qua cổng hay qua API lõi. Chỉ đọc; chỉ quản trị viên
// tới được màn này.
//
// Dữ liệu do trang đọc ở máy chủ (`doc-truy-cap.ts`) theo bộ lọc trên địa chỉ. Gửi bộ lọc là đổi địa chỉ trong
// một transition: bảng cũ đứng yên, thanh mảnh ở mép trên bảng chạy tới khi kết quả mới về. Không có JavaScript
// thì biểu mẫu GET vẫn lọc được.

import { Filter } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTransition } from "react";

import { ChanTrang, ChipLoc } from "@/components/chan-trang";
import { ngayGioCoNam } from "@/lib/dinh-dang";
import type { DongTruyCap } from "@/lib/kieu";

import type { DuLieuTruyCap } from "./doc-truy-cap";

const NEO = "nhat-ky-truy-cap";

/** Kênh là hợp đồng của API (`ung-dung` | `loi`), không phải nghiệp vụ. */
const NHAN_KENH: Record<string, string> = { "ung-dung": "Cổng", loi: "API lõi" };

/** Tham số của lần xuất nhật ký, đọc được: "CSV · 01/11/2026 – 30/11/2026". */
function thamSoXuat(d: DongTruyCap): string | null {
  const ct = d.details;
  if (!ct) return null;
  const ngay = (gt: unknown) => (typeof gt === "string" ? gt.split("-").reverse().join("/") : null);
  const khoang = ct.from || ct.to ? `${ngay(ct.from) ?? "đầu"} – ${ngay(ct.to) ?? "nay"}` : "toàn bộ";
  return [typeof ct.format === "string" ? ct.format.toUpperCase() : null, khoang].filter(Boolean).join(" · ");
}

function OHoSo({ d, moDuocHoSo, goc }: { d: DongTruyCap; moDuocHoSo: boolean; goc: string }) {
  if (d.case_id === null || d.case_code === null) {
    const xuat = thamSoXuat(d);
    return xuat ? <span className="ktc-phu">{xuat}</span> : <span className="ktc-phu">—</span>;
  }
  // Mở được buồng lái điều phối thì mở hồ sơ; không thì lọc nhật ký theo hồ sơ đó
  return moDuocHoSo ? (
    <Link className="mono ktc-lien-ket" href={`/dieu-phoi/${d.case_id}`}>
      {d.case_code}
    </Link>
  ) : (
    <Link
      className="mono ktc-lien-ket"
      href={`${goc}?ho-so=${d.case_id}#${NEO}`}
      aria-label={`Lọc nhật ký theo hồ sơ ${d.case_code}`}
      scroll={false}
    >
      {d.case_code}
    </Link>
  );
}

function Dong({ d, moDuocHoSo, goc }: { d: DongTruyCap; moDuocHoSo: boolean; goc: string }) {
  return (
    <tr className="ktc-dong">
      <td className="ktc-luc" data-nhan="Thời điểm">
        <time dateTime={d.at}>{ngayGioCoNam(d.at)}</time>
      </td>
      <td className="ktc-nguoi" data-nhan="Người">
        <span title={d.actor}>{d.actor_label ?? d.actor}</span>
      </td>
      <td data-nhan="Loại">{d.access_kind_label}</td>
      <td data-nhan="Hồ sơ">
        <OHoSo d={d} moDuocHoSo={moDuocHoSo} goc={goc} />
      </td>
      <td className="ktc-tep" data-nhan="Tệp">
        {d.attachment_filename ?? (d.attachment_id ? `#${d.attachment_id}` : <span className="ktc-phu">—</span>)}
      </td>
      <td data-nhan="Kênh">{NHAN_KENH[d.channel] ?? d.channel}</td>
    </tr>
  );
}

export function NhatKyTruyCap({ duLieu }: { duLieu: DuLieuTruyCap }) {
  const { ds, loai, loc, coLoc, moDuocHoSo, truoc, sau, chip, xoaHet, hienTai } = duLieu;
  const router = useRouter();
  const goc = usePathname();
  const [dangTai, chuyen] = useTransition();

  const di = (duong: string) => chuyen(() => router.replace(duong, { scroll: false }));

  const guiLoc = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const q = new URLSearchParams();
    for (const [ten, gt] of new FormData(e.currentTarget)) {
      if (typeof gt === "string" && gt.trim()) q.set(ten, gt.trim());
    }
    const chuoi = q.toString();
    di(chuoi ? `${goc}?${chuoi}` : goc);
  };

  return (
    <section className="the" id={NEO} aria-labelledby="tieu-de-truy-cap">
      <div className="khoi-dau">
        <h2 id="tieu-de-truy-cap">Nhật ký truy cập dữ liệu cá nhân</h2>
      </div>
      <div className="ktc-than">
        <p className="xuat-nhat-ky-giai-thich">
          Mỗi lần ai đó mở chi tiết hồ sơ, xem liên hệ người gửi hay tải tệp đính kèm của người khác, và mỗi lần
          xuất nhật ký sự kiện. Người gửi xem hồ sơ của chính mình không được ghi. Chỉ ghi thêm, không sửa hay xóa
          được.
        </p>
        {/* Khóa theo địa chỉ: đổi bộ lọc từ chip hay nút lùi thì ô nhập theo giá trị mới */}
        <form
          key={hienTai}
          action={`${goc}#${NEO}`}
          method="get"
          className="ktc-loc"
          onSubmit={guiLoc}
          aria-label="Lọc nhật ký truy cập"
        >
          <label className="o-truong">
            <span className="o-truong-nhan">Mã hồ sơ</span>
            <input name="ho-so" defaultValue={loc.hoSo} placeholder="YC-2026-0184" className="o-nhap" />
          </label>
          <label className="o-truong">
            <span className="o-truong-nhan">Người</span>
            <input name="nguoi" defaultValue={loc.nguoi} placeholder="Tên hay mã người" className="o-nhap" />
          </label>
          <label className="o-truong">
            <span className="o-truong-nhan">Loại truy cập</span>
            <select name="loai" defaultValue={loc.loai} className="o-nhap">
              <option value="">Mọi loại</option>
              {loai.map((k) => (
                <option key={k.code} value={k.code}>
                  {k.label}
                </option>
              ))}
            </select>
          </label>
          <label className="o-truong">
            <span className="o-truong-nhan">Từ ngày</span>
            <input type="date" name="tu" defaultValue={loc.tu} className="o-nhap" />
          </label>
          <label className="o-truong">
            <span className="o-truong-nhan">Đến hết ngày</span>
            <input type="date" name="den" defaultValue={loc.den} className="o-nhap" />
          </label>
          <div className="ktc-loc-nut">
            <button type="submit" className="nut" disabled={dangTai}>
              <Filter aria-hidden />
              Lọc
            </button>
          </div>
        </form>
        <ChipLoc chip={chip} xoaHet={xoaHet ?? goc} />
      </div>

      {ds === null ? (
        <div role="alert" className="ktc-trang-thai">
          <p className="ktc-loi">Không tải được nhật ký truy cập</p>
          <p className="ktc-phu">Dịch vụ ứng dụng không trả lời.</p>
          <button type="button" className="nut" onClick={() => router.refresh()}>
            Thử lại
          </button>
        </div>
      ) : ds.items.length === 0 ? (
        <p className="ktc-trang-thai ktc-phu">
          {coLoc ? (
            <>
              Không có lượt truy cập nào khớp bộ lọc.{" "}
              <Link className="ktc-lien-ket" href={xoaHet ?? goc} scroll={false}>
                Xóa tất cả
              </Link>
            </>
          ) : (
            "Chưa có lượt truy cập nào được ghi."
          )}
        </p>
      ) : (
        <>
          <div className="ktc-khung" aria-busy={dangTai}>
            {dangTai ? (
              <div className="ktc-thanh-tai" aria-hidden>
                <span />
              </div>
            ) : null}
            <table className="ktc-bang">
              <caption className="an-di">Các lượt truy cập, mới nhất trước</caption>
              <thead>
                <tr>
                  <th scope="col">Thời điểm</th>
                  <th scope="col">Người</th>
                  <th scope="col">Loại</th>
                  <th scope="col">Hồ sơ</th>
                  <th scope="col">Tệp</th>
                  <th scope="col">Kênh</th>
                </tr>
              </thead>
              <tbody>
                {ds.items.map((d) => (
                  <Dong key={d.id} d={d} moDuocHoSo={moDuocHoSo} goc={goc} />
                ))}
              </tbody>
            </table>
          </div>
          <div className="ktc-chan">
            <ChanTrang
              tong={ds.total}
              tu={ds.offset}
              soDong={ds.items.length}
              donVi="lượt truy cập"
              xep="mới nhất"
              truoc={truoc}
              sau={sau}
            />
          </div>
        </>
      )}
      {dangTai ? (
        <span className="an-di" role="status">
          Đang tải nhật ký truy cập
        </span>
      ) : null}
    </section>
  );
}
