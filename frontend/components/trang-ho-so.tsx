// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Các khối của trang hồ sơ phía nhân viên (#169), dùng chung cho buồng lái điều phối và
// buồng lái phòng ban: đầu hồ sơ, thanh các bước, thẻ hạn, thẻ thao tác.
//
// Mỗi trang tự quyết khối nào chứa gì — người xử lý chỉ có nghĩa ở phòng ban, gợi ý phòng
// chỉ có nghĩa ở điều phối — còn ở đây chỉ là hình. Không khối nào biết tên trạng thái hay
// vai trò: bước suy từ thứ tự trạng thái (lib/buoc.ts), nút thao tác vẫn đến từ
// `allowed_transitions`.

import { Check, Info } from "lucide-react";

import { NhanTrangThai } from "@/components/nhan-trang-thai";
import type { Buoc } from "@/lib/buoc";
import { thoiLuongLamViec } from "@/lib/dinh-dang";
import type { HoSoTomTat } from "@/lib/kieu";
import { docDongHo, docTuDong, vachHan } from "@/lib/sla";

export type MucMeta = { icon: React.ReactNode; chu: string };

/** Mã, tiêu đề, một hàng thông tin có icon, và nhãn trạng thái to bên phải. */
export function DauHoSo({ ho_so, meta }: { ho_so: HoSoTomTat; meta: MucMeta[] }) {
  return (
    <div className="dau-ho-so">
      <div className="trai">
        <span className="ma">{ho_so.code}</span>
        <h1 className="h1-ho-so">{ho_so.title}</h1>
        <div className="meta">
          {meta.map((m) => (
            <span key={m.chu}>
              {m.icon}
              {m.chu}
            </span>
          ))}
        </div>
      </div>
      <NhanTrangThai ma={ho_so.state.code} nhan={ho_so.state.label} to />
    </div>
  );
}

/** Thanh "hồ sơ đang ở đâu" trên đường chính. */
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
          <span className="vong">{b.xong && <Check aria-hidden />}</span>
          <span className="chu">{b.label}</span>
        </li>
      ))}
    </ol>
  );
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
            <span className="han-so">{dongHo.cau}</span>
            <div className="vach">
              <i style={{ width: `${vach.phan}%` }} />
            </div>
            <small>
              Cam kết {thoiLuongLamViec(ho_so.sla_limit_seconds ?? 0)}, tính từ lúc phòng ban
              nhận việc
            </small>
          </>
        ) : (
          <span
            style={{
              fontSize: "14.5px",
              fontWeight: 600,
              color: dongHo.canhBao ? "var(--f-r-ink)" : undefined,
            }}
          >
            {dongHo.cau}
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

/** Thẻ "Bạn có thể làm gì" bọc bảng thao tác. Không in ra giấy. */
export function TheThaoTac({ children }: { children: React.ReactNode }) {
  return (
    <div className="the khoi khong-in">
      <div className="khoi-dau">Bạn có thể làm gì lúc này</div>
      {children}
      <p className="ghi-quy-tac">
        <Info aria-hidden />
        Các nút phụ thuộc vào trạng thái hồ sơ và vai trò của bạn.
      </p>
    </div>
  );
}
