// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Bảng Kanban dùng chung của hai buồng lái: phòng ban (#403, `app/phong-ban/bang`) và điều phối (#560,
// `app/dieu-phoi/bang`).
//
// Hàng đợi trả lời "hồ sơ nào cần làm trước"; bảng trả lời "việc đang dồn ở bước nào". Mỗi cột một trạng thái —
// thứ tự cột do trang truyền từ danh mục mà dịch vụ trả về, tệp này không biết trạng thái nào. Chỉ hiện cột có hồ
// sơ: bảng của một phòng không cần cột "Đã gửi" mà hồ sơ chưa bao giờ tới phòng.
//
// Thẻ chỉ để nhìn và mở hồ sơ: không kéo thả đổi trạng thái — đổi trạng thái phải qua các nút engine trả trên trang
// hồ sơ, nơi có ghi chú bắt buộc và ràng buộc Poka-yoke. Phần khác nhau giữa hai buồng lái (thẻ phòng ban có người
// xử lý) đi qua thuộc tính, bảng không rẽ nhánh theo vai.

import Link from "next/link";

import { ChamLoai } from "@/components/cham-loai";
import type { HoSoTomTat, NhanCoMa } from "@/lib/kieu";
import { docDongHo, docTuDong } from "@/lib/sla";
import { bienHoMau, trinhBayTrangThai } from "@/lib/trang-thai";

/** Số hồ sơ tối đa bảng đọc một lần — trần `limit` của dịch vụ (backend/app/workflow/phan_trang.py). */
export const TOI_DA_BANG = 200;

export type CotKanban<T> = { ma: string; ten: string; the: T[] };

/**
 * Chia hồ sơ thành cột theo trạng thái. `thuTu` là danh mục trạng thái dịch vụ trả về, theo thứ tự hiển thị;
 * trạng thái không có trong đó (bộ quy tắc cũ) xếp cuối theo thứ tự gặp. Tên cột là nhãn trạng thái trên chính
 * hồ sơ. Chỉ giữ cột có hồ sơ.
 */
export function chiaCot<T extends HoSoTomTat>(cacHoSo: T[], thuTu: NhanCoMa[]): CotKanban<T>[] {
  // Map giữ thứ tự chèn: cột của danh mục đứng trước, đúng thứ tự dịch vụ trả
  const theoCot = new Map<string, CotKanban<T>>(thuTu.map((t) => [t.code, { ma: t.code, ten: t.label, the: [] }]));
  for (const m of cacHoSo) {
    const cot = theoCot.get(m.state.code);
    if (cot && cot.the.length > 0) cot.the.push(m);
    else theoCot.set(m.state.code, { ma: m.state.code, ten: m.state.label, the: [m] });
  }
  return [...theoCot.values()].filter((c) => c.the.length > 0);
}

/** Mức của câu hạn — cùng quy tắc tô màu với cột "Hạn" của hàng đợi. */
function mucHan(m: HoSoTomTat): "qua" | "sap" | "dung" | undefined {
  const tuDong = docTuDong(m);
  if (tuDong?.canhBao) return "sap";
  if (docDongHo(m).canhBao) return "qua";
  if (!m.sla_started || m.sla_paused) return "dung";
  return m.sla_due_soon ? "sap" : undefined;
}

function TheHoSo<T extends HoSoTomTat>({ m, goc, nguoi }: { m: T; goc: string; nguoi?: (m: T) => React.ReactNode }) {
  // Hồ sơ sắp tự đi vì nằm im quá hạn chờ (#142): câu đó thay chỗ câu hạn trong khoảng báo trước
  const tuDong = docTuDong(m);
  const cauHan = (tuDong?.canhBao ? tuDong : docDongHo(m)).cau;
  return (
    <li>
      <Link href={`${goc}/${m.id}`} className="kb-the" data-muc={mucHan(m)}>
        <span className="kb-ma mono">{m.code}</span>
        <span className="kb-tieu-de">{m.title}</span>
        <span className="kb-phu">
          <ChamLoai ma={m.request_type?.code} />
          {m.request_type?.label ?? "Chưa rõ loại"}
        </span>
        <span className="kb-chan">
          {nguoi?.(m)}
          <span className="kb-han">{cauHan}</span>
        </span>
      </Link>
    </li>
  );
}

export function BangKanban<T extends HoSoTomTat>({
  cot,
  goc,
  nguoi,
  tong,
  khiTrong,
}: {
  cot: CotKanban<T>[];
  /** Đường của trang hồ sơ trong buồng lái này: thẻ mở `{goc}/{id}`. */
  goc: string;
  /** Phần đầu dòng chân của thẻ, trước câu hạn — phòng ban đặt người xử lý. Bỏ trống thì thẻ chỉ có câu hạn. */
  nguoi?: (m: T) => React.ReactNode;
  /** Tổng hồ sơ khớp bộ lọc ở dịch vụ — lớn hơn số thẻ thì có dòng nhắc xem đủ ở dạng danh sách. */
  tong: number;
  khiTrong: { tieuDe: string; cau: string };
}) {
  const soThe = cot.reduce((s, c) => s + c.the.length, 0);
  return (
    <>
      {tong > soThe && (
        <p className="kb-ghi-chu" role="status">
          Bảng hiện {soThe} trên {tong} hồ sơ — xem đủ ở dạng danh sách.
        </p>
      )}
      {cot.length === 0 ? (
        <div className="the">
          <div className="rong">
            <h2>{khiTrong.tieuDe}</h2>
            <p>{khiTrong.cau}</p>
          </div>
        </div>
      ) : (
        <div className="kb-bang" aria-label="Bảng việc theo trạng thái">
          {cot.map((c) => (
            <section key={c.ma} className="kb-cot" aria-labelledby={`kb-${c.ma}`}>
              <h2 id={`kb-${c.ma}`} className="kb-dau-cot">
                <span className="nhan-tt" style={{ ...bienHoMau(trinhBayTrangThai(c.ma).ho), fontSize: "12.5px" }}>
                  {c.ten}
                </span>
                <span className="kb-so">{c.the.length}</span>
              </h2>
              <ul className="kb-ds">
                {c.the.map((m) => (
                  <TheHoSo key={m.id} m={m} goc={goc} nguoi={nguoi} />
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </>
  );
}
