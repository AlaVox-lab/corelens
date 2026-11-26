// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Các khối của trang hồ sơ phía nhân viên (#169, bố cục #561), dùng chung cho buồng lái điều phối và
// buồng lái phòng ban: đầu hồ sơ, thanh các bước, thẻ hạn, thẻ thông tin hồ sơ, thẻ thao tác.
//
// Khuôn trang (#561): đầu trang chỉ còn mã, tiêu đề, nhãn trạng thái và thanh bước; cột chính mở đầu bằng
// thẻ "Bạn có thể làm gì lúc này" — nút xếp ngang, khung nhập mở ngay trong thẻ — rồi tới nội dung và dòng
// thời gian; cột phải hẹp, dính khi cuộn, chỉ còn thông tin tĩnh: Hạn xử lý và Thông tin hồ sơ.
//
// Mỗi trang tự quyết khối nào chứa gì — người xử lý chỉ có nghĩa ở phòng ban, gợi ý phòng
// chỉ có nghĩa ở điều phối — còn ở đây chỉ là hình. Không khối nào biết tên trạng thái hay
// vai trò: bước suy từ thứ tự trạng thái (lib/buoc.ts), nút thao tác vẫn đến từ
// `allowed_transitions`.

import Link from "next/link";

import { NhanTrangThai } from "@/components/nhan-trang-thai";
import { hienTruong, TheTruongRieng } from "@/components/the-truong-rieng";
import type { Buoc } from "@/lib/buoc";
import { thoiLuongLamViec } from "@/lib/dinh-dang";
import type { HoSoChiTiet, HoSoTomTat } from "@/lib/kieu";
import { docDongHo, docTuDong, vachHan } from "@/lib/sla";

export type MucMeta = { icon: React.ReactNode; chu: string };

/** Một dòng của thẻ "Thông tin hồ sơ": nhãn, giá trị, và dòng phụ nhỏ khi có (gợi ý theo loại chẳng hạn). */
export type DongThongTin = { nhan: string; giaTri: React.ReactNode; phu?: string };

/**
 * Mã, tiêu đề và nhãn trạng thái to bên phải; `meta` — một hàng thông tin có icon — chỉ ở ngăn xem nhanh,
 * trang đầy đủ đặt các thông tin đó ở thẻ "Thông tin hồ sơ" (#561). Trong ngăn xem nhanh (#233) tiêu đề là
 * cấp 2 — cấp 1 của trang vẫn là tên hàng đợi — và nhận tiêu điểm khi ngăn mở; mã và tiêu đề là liên kết tới
 * trang đầy đủ (#557), chỗ người dùng quen bấm để "mở hồ sơ ra".
 */
export function DauHoSo({
  ho_so,
  meta,
  trongNgan,
}: {
  ho_so: HoSoTomTat;
  meta?: MucMeta[];
  /** `id` của tiêu đề trong ngăn, để ngăn gọi tên mình và đặt tiêu điểm vào đó; `dayDu`: trang đầy đủ. */
  trongNgan?: { idTieuDe: string; dayDu: string };
}) {
  return (
    <div className="dau-ho-so">
      <div className="trai">
        {trongNgan ? (
          <Link className="ma lk-dau-ngan" href={trongNgan.dayDu} tabIndex={-1} aria-hidden>
            {ho_so.code}
          </Link>
        ) : (
          <span className="ma">{ho_so.code}</span>
        )}
        {trongNgan ? (
          <h2 className="h1-ho-so" id={trongNgan.idTieuDe} tabIndex={-1}>
            <Link className="lk-dau-ngan" href={trongNgan.dayDu}>
              {ho_so.title}
            </Link>
          </h2>
        ) : (
          <h1 className="h1-ho-so">{ho_so.title}</h1>
        )}
        {meta && meta.length > 0 && (
          <div className="meta">
            {meta.map((m) => (
              <span key={m.chu}>
                {m.icon}
                {m.chu}
              </span>
            ))}
          </div>
        )}
      </div>
      <NhanTrangThai ma={ho_so.state.code} nhan={ho_so.state.label} to />
    </div>
  );
}

/**
 * Thanh "hồ sơ đang ở đâu" trên đường chính: mỗi bước một vạch, vạch tô màu nhấn tới bước hiện tại (#561),
 * nhãn bước hiện tại màu nhấn. Bước đã qua và bước hiện tại nói bằng `aria-current` và chữ ẩn, không chỉ bằng màu.
 */
export function ThanhBuoc({ cacBuoc }: { cacBuoc: Buoc[] }) {
  if (cacBuoc.length === 0) return null;
  return (
    <ol className="buoc" aria-label="Các bước của hồ sơ">
      {cacBuoc.map((b) => (
        <li
          key={b.code}
          data-xong={b.xong ? "" : undefined}
          data-dang={b.dang ? "" : undefined}
          aria-current={b.dang ? "step" : undefined}
        >
          <span className="vach-buoc" aria-hidden />
          <span className="chu">
            {b.label}
            {b.xong && <span className="an-di"> (đã qua)</span>}
          </span>
        </li>
      ))}
    </ol>
  );
}

/**
 * Dấu ngăn " · " của câu đồng hồ dính vào chữ đứng trước (khoảng trắng không ngắt), để câu chữ lớn xuống dòng
 * thì dòng sau không mở đầu bằng "·" (#557: "Còn 3 giờ 49 phút làm việc / · hạn 11:49 Thứ Năm 26/11").
 */
function ngatSauDauNgan(cau: string): string {
  return cau.replaceAll(" · ", " · ");
}

/**
 * Thẻ hạn xử lý. Đồng hồ đang chạy thì câu thành con số to kèm vạch đã dùng bao nhiêu
 * phần cam kết; chưa chạy hay đã khép thì chỉ còn câu — câu lấy nguyên từ `docDongHo`,
 * nên vẫn nói đúng sáu tình huống của lib/sla.ts.
 */
export function TheHan({ ho_so }: { ho_so: HoSoTomTat }) {
  const dongHo = docDongHo(ho_so);
  const vach = vachHan(ho_so);
  // Trạng thái có hạn chờ (#142): nói luôn lúc hệ thống sẽ tự đi, nhấn mạnh khi sắp tới
  const tuDong = docTuDong(ho_so);

  return (
    <div className="the khoi">
      <div className="han" data-muc={dongHo.canhBao ? "qua" : vach?.muc}>
        <span className="tua-muc">Hạn xử lý</span>
        {vach ? (
          <>
            <span className="han-so">{ngatSauDauNgan(dongHo.cau)}</span>
            <div className="vach">
              <i style={{ width: `${vach.phan}%` }} />
            </div>
            <small>
              Cam kết {thoiLuongLamViec(ho_so.sla_limit_seconds ?? 0)}, tính từ lúc phòng ban
              nhận việc
            </small>
          </>
        ) : (
          <span className="han-cau" data-canh-bao={dongHo.canhBao ? "" : undefined}>
            {ngatSauDauNgan(dongHo.cau)}
          </span>
        )}
        {/* Gia hạn (#101): hạn ở trên đã gồm phần này; nói ra để người đọc biết vì sao
            cam kết dài hơn mức của loại yêu cầu */}
        {ho_so.sla_extension_count > 0 && (
          <small>
            Đã gia hạn {ho_so.sla_extension_count} lần, thêm{" "}
            {thoiLuongLamViec(ho_so.sla_extension_total_hours * 3600)}
          </small>
        )}
        {tuDong && (
          <small className="tu-dong" data-sap={tuDong.canhBao ? "" : undefined}>
            {tuDong.cau}
          </small>
        )}
      </div>
    </div>
  );
}

/**
 * Thẻ "Thông tin hồ sơ" ở cột phải (#561): loại, phòng, ưu tiên, người xử lý — trước là hàng icon dưới tiêu đề —
 * rồi các dòng liên hệ người gửi (`lienHe`, gộp thẻ Liên hệ người gửi cũ). Trang truyền dòng nào có nghĩa với nó.
 */
export function TheThongTinHoSo({ cacDong, lienHe }: { cacDong: DongThongTin[]; lienHe?: React.ReactNode }) {
  return (
    <section className="the khoi the-thong-tin" aria-labelledby="tua-thong-tin">
      <h2 className="tua-the" id="tua-thong-tin">
        Thông tin hồ sơ
      </h2>
      <dl className="ds-mt ds-ngang">
        {cacDong.map((d) => (
          <div key={d.nhan}>
            <dt>{d.nhan}</dt>
            <dd>
              <span className="dd-chinh">{d.giaTri}</span>
              {d.phu && <span className="dd-phu">{d.phu}</span>}
            </dd>
          </div>
        ))}
        {lienHe}
      </dl>
    </section>
  );
}

/** Nội dung người gửi viết: trường riêng theo loại (#250) đứng trước mô tả tự do. */
export function TheNoiDung({ ho_so }: { ho_so: HoSoChiTiet }) {
  if (!ho_so.description && (ho_so.detail_fields?.length ?? 0) === 0) return null;
  return (
    <div className="the khoi">
      <div className="khoi-dau">Nội dung yêu cầu</div>
      <TheTruongRieng cacTruong={ho_so.detail_fields ?? []} giaTri={ho_so.details ?? {}} />
      {ho_so.description ? <p className="mo-ta">{ho_so.description}</p> : null}
    </div>
  );
}

/**
 * Thẻ "Bạn có thể làm gì lúc này" bọc bảng thao tác, ĐẦU cột chính (#561). Tiêu đề và hàng nút do bảng thao tác
 * dựng, để nút nằm ngang cạnh tiêu đề. Không còn dòng ghi chú cuối thẻ: chỉ nút làm được mới hiện, nói thêm không
 * giúp gì. Không in ra giấy.
 */
export function TheThaoTac({ children }: { children: React.ReactNode }) {
  return <section className="the the-thao-tac khong-in" aria-labelledby="tua-thao-tac">{children}</section>;
}

/**
 * Tóm tắt nội dung hồ sơ trong một đoạn — giá trị trường riêng nối bằng dấu phẩy, rồi mô tả — cho ngăn xem nhanh khi
 * một thao tác đang mở (#561): người phân loại vẫn đọc được nội dung mà khung nhập không đẩy nó khuất.
 */
export function tomTatNoiDung(ho_so: HoSoChiTiet): string {
  const truong = (ho_so.detail_fields ?? []).flatMap((t) => {
    const v = ho_so.details?.[t.code];
    return v === undefined || v === null || v === "" ? [] : [hienTruong(t, v)];
  });
  return [truong.join(", "), (ho_so.description ?? "").trim()].filter(Boolean).join(". ");
}
