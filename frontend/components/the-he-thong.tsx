// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Thẻ tình trạng các dịch vụ của cụm (#229). Trước đây nằm trên trang chủ của mọi người
// dùng; nay chỉ quản trị viên thấy — ở màn Hệ thống và ở cột tổng quan trang chủ của họ.
// Nhân viên không làm gì được với tình trạng cụm, và chữ kỹ thuật làm trang chủ rối.

import { bienHoMau } from "@/lib/trang-thai";

const DIA_CHI_DICH_VU = process.env.BACKEND_INTERNAL_URL ?? "http://backend:8000";

export type SucKhoe = {
  status?: string;
  database?: string;
  version?: string;
  active_rule_set_states?: number;
  detail?: string;
};

export async function docSucKhoe(): Promise<SucKhoe | null> {
  try {
    const phanHoi = await fetch(`${DIA_CHI_DICH_VU}/health`, { cache: "no-store" });
    return (await phanHoi.json()) as SucKhoe;
  } catch {
    return null;
  }
}

function DongTrangThai({ nhan, tot, giaTri }: { nhan: string; tot: boolean; giaTri: string }) {
  return (
    <div className="dong-tinh-trang" style={bienHoMau(tot ? "g" : "r")}>
      <span>{nhan}</span>
      {/* Dấu hiệu chữ đi kèm màu: bản in đen trắng và người không phân biệt được màu vẫn đọc được */}
      <b>
        <span aria-hidden="true">{tot ? "✓" : "✕"}</span> {giaTri}
      </b>
    </div>
  );
}

export function TheHeThong({ sucKhoe, tieuDe = "Tình trạng hệ thống" }: { sucKhoe: SucKhoe | null; tieuDe?: string }) {
  const dungHet = sucKhoe?.status === "ok";
  return (
    <section className="the">
      <div className="khoi-dau">
        <h2>{tieuDe}</h2>
      </div>
      <DongTrangThai nhan="Cổng người dùng" tot giaTri="đang chạy" />
      <DongTrangThai
        nhan="Dịch vụ ứng dụng"
        tot={Boolean(sucKhoe)}
        giaTri={sucKhoe ? `đang chạy · v${sucKhoe.version ?? "?"}` : "không tới được"}
      />
      <DongTrangThai
        nhan="Cơ sở dữ liệu"
        tot={sucKhoe?.database === "ok"}
        giaTri={sucKhoe?.database === "ok" ? "đã kết nối" : "chưa kết nối"}
      />
      <DongTrangThai
        nhan="Bộ quy tắc quy trình"
        tot={dungHet && Boolean(sucKhoe?.active_rule_set_states)}
        giaTri={sucKhoe?.active_rule_set_states ? `đã nạp · ${sucKhoe.active_rule_set_states} trạng thái` : "chưa nạp"}
      />
      {!dungHet && (
        <p className="ghi-chu-tinh-trang">
          {sucKhoe?.detail ?? "Kiểm tra dịch vụ ứng dụng bằng docker compose logs backend."}
        </p>
      )}
    </section>
  );
}
