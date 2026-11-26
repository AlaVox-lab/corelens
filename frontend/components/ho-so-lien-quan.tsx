// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Hồ sơ nối với nhau bằng `parent_request_id` và lời mời tạo hồ sơ mới (#102).
//
// Giảng viên chốt 08/10: hồ sơ hết lượt mở lại, quá cửa sổ mở lại hay bị Không tiếp nhận thì
// người gửi tạo hồ sơ mới liên kết hồ sơ cũ. Hai khối ở đây chỉ trình bày — hồ sơ nào được
// mở lại, cạnh nào còn hiện, tất cả đến từ dịch vụ qua `allowed_transitions`; tệp này không
// biết tên trạng thái nào, chỉ biết "đã kết thúc và không còn thao tác nào".

import { Link2, RotateCcw } from "lucide-react";
import Link from "next/link";

import type { HoSoChiTiet, HoSoLienQuan } from "@/lib/kieu";

function MucLienQuan({
  hoSo,
  lienKet,
}: {
  hoSo: HoSoLienQuan;
  lienKet?: (id: number) => string;
}) {
  const chu = (
    <>
      <span className="ma">{hoSo.code}</span> {hoSo.title}
      <span style={{ color: "var(--ink-3)" }}> — {hoSo.state.label}</span>
    </>
  );
  return (
    <li style={{ fontSize: "13.5px", lineHeight: 1.6 }}>
      {lienKet ? <Link href={lienKet(hoSo.id)}>{chu}</Link> : chu}
    </li>
  );
}

/**
 * Hồ sơ gốc và các hồ sơ tạo lại. `lienKet` bỏ trống thì chỉ hiện chữ: nhân viên phòng này
 * không chắc mở được hồ sơ ở phòng khác, nên các buồng lái không gắn đường dẫn.
 */
export function KhoiHoSoLienQuan({
  hoSo,
  lienKet,
}: {
  hoSo: HoSoChiTiet;
  lienKet?: (id: number) => string;
}) {
  if (!hoSo.parent && hoSo.children.length === 0) return null;
  return (
    <div className="the khoi khong-in">
      <div className="khoi-dau">
        <span className="khoi-dau-tua">
          <Link2 aria-hidden /> Hồ sơ liên quan
        </span>
      </div>
      <ul style={{ margin: 0, padding: "0 20px 16px 38px", display: "grid", gap: "6px" }}>
        {hoSo.parent && (
          <li style={{ listStyle: "none", marginLeft: "-18px", fontSize: "12.5px", color: "var(--ink-3)" }}>
            Tạo lại từ
          </li>
        )}
        {hoSo.parent && <MucLienQuan hoSo={hoSo.parent} lienKet={lienKet} />}
        {hoSo.children.length > 0 && (
          <li style={{ listStyle: "none", marginLeft: "-18px", fontSize: "12.5px", color: "var(--ink-3)" }}>
            Đã tạo lại thành
          </li>
        )}
        {hoSo.children.map((c) => (
          <MucLienQuan key={c.id} hoSo={c} lienKet={lienKet} />
        ))}
      </ul>
    </div>
  );
}

/**
 * Lời mời tạo hồ sơ mới ở cổng người gửi. Hiện khi hồ sơ đã kết thúc mà dịch vụ không còn
 * cho thao tác nào — hết lượt mở lại, quá cửa sổ, Không tiếp nhận, tự đóng vì chưa bổ sung.
 * Số lần đã mở lại hiện riêng ở `GhiChuMoLai`.
 */
export function MoiTaoHoSoMoi({ hoSo }: { hoSo: HoSoChiTiet }) {
  if (!hoSo.state.is_terminal || hoSo.allowed_transitions.length > 0) return null;
  return (
    <div className="the khong-in" style={{ marginTop: "16px", padding: "17px 20px", display: "grid", gap: "9px" }}>
      <h2 style={{ margin: 0, fontSize: "15px", fontWeight: 600 }}>Cần làm tiếp?</h2>
      <p style={{ margin: 0, fontSize: "13.5px", color: "var(--ink-2)", lineHeight: 1.6, maxWidth: "72ch" }}>
        Hồ sơ này đã kết thúc và không mở lại được. Gửi một hồ sơ mới — nội dung chép sẵn từ
        hồ sơ này để bạn sửa lại cho rõ hơn, và hai hồ sơ nối với nhau để điều phối viên đọc được
        chuyện đã qua.
      </p>
      <div>
        <Link className="nut" data-loai="chinh" href={`/yeu-cau/moi?tu=${hoSo.id}`}>
          Tạo hồ sơ mới từ hồ sơ này
        </Link>
      </div>
    </div>
  );
}

/** Dòng "đã mở lại N/M lần" — không hiện khi chưa mở lại lần nào. */
export function GhiChuMoLai({ hoSo }: { hoSo: HoSoChiTiet }) {
  if (hoSo.reopen_count === 0) return null;
  return (
    <p style={{ margin: "10px 0 0", fontSize: "13px", color: "var(--ink-2)", display: "flex", gap: "6px", alignItems: "center" }}>
      <RotateCcw aria-hidden size={14} />
      Đã mở lại {hoSo.reopen_count}
      {hoSo.reopen_max_count !== null && `/${hoSo.reopen_max_count}`} lần. Mỗi lần mở lại hồ sơ có
      hạn xử lý mới.
    </p>
  );
}
