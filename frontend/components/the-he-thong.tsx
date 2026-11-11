// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Thẻ tình trạng các dịch vụ của cụm (#229). Trước đây nằm trên trang chủ của mọi người
// dùng; nay chỉ quản trị viên thấy — ở màn Hệ thống và ở cột tổng quan trang chủ của họ.
// Nhân viên không làm gì được với tình trạng cụm, và chữ kỹ thuật làm trang chủ rối.
//
// Dữ liệu đến từ `GET /system/health` của dịch vụ ứng dụng (#243): điểm cuối có kiểm vai trò quản
// trị, mang đủ chi tiết — phiên bản, bộ quy tắc, nhịp từng bộ quét. `/health` công khai chỉ trả
// trạng thái chung nên không còn là nguồn của màn này.

import { goiDichVu } from "@/lib/api";
import { thoiLuong } from "@/lib/dinh-dang";
import { bienHoMau } from "@/lib/trang-thai";

export type NhipBoQuet = {
  name: string;
  label: string;
  /** `ok`, `starting`, `stale`, `failing` hoặc `disabled` */
  status: string;
  last_error: string | null;
  consecutive_errors: number;
  seconds_since_success: number | null;
  runner_host: string | null;
  runner_pid: number | null;
};

/** Tình trạng mô hình ngôn ngữ cục bộ (#316): `disabled`, `ready` hoặc `unreachable`. */
export type MoHinhNgonNgu = {
  status: string;
  model?: string;
  detail?: string;
};

export type SucKhoe = {
  status?: string;
  database?: string;
  version?: string;
  active_rule_set_states?: number;
  detail?: string;
  scanners?: NhipBoQuet[] | null;
  language_model?: MoHinhNgonNgu;
  /** Mô hình nhúng cho hồ sơ tương tự (#319) — cùng ba mức. */
  embedding_model?: MoHinhNgonNgu;
  scan_settings?: {
    enabled: boolean;
    interval_seconds: number;
    stale_after_seconds: number;
    max_consecutive_errors: number;
  };
};

export async function docSucKhoe(): Promise<SucKhoe | null> {
  return goiDichVu<SucKhoe>("/system/health");
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

/** Một dòng chữ nói tình trạng của bộ quét, kèm bản dịch vụ đã chạy lượt gần nhất. */
function chuBoQuet(b: NhipBoQuet): string {
  const ban = b.runner_host ? ` · bản ${b.runner_host.slice(0, 12)}` : "";
  switch (b.status) {
    case "disabled":
      return "đã tắt theo cấu hình";
    case "starting":
      return "đang khởi động, chưa tới lượt quét đầu";
    case "failing":
      return `hỏng ${b.consecutive_errors} lượt liên tiếp${ban}`;
    case "stale":
      return b.seconds_since_success === null
        ? "chưa có lượt quét thành công nào"
        : `quá lâu không quét thành công — lần cuối cách đây ${thoiLuong(b.seconds_since_success)}`;
    default:
      return b.seconds_since_success === null
        ? `đang chạy${ban}`
        : `quét thành công cách đây ${thoiLuong(b.seconds_since_success)}${ban}`;
  }
}

/** Mô hình là tùy chọn: "tắt" không phải lỗi, chỉ "không phản hồi" mới tô đỏ (mục 8.3). */
function chuMoHinh(m: MoHinhNgonNgu, khiTat = "tắt — điều phối thủ công, không có gợi ý"): string {
  switch (m.status) {
    case "disabled":
      return khiTat;
    case "ready":
      return `sẵn sàng${m.model ? ` · ${m.model}` : ""}`;
    default:
      return `không phản hồi${m.detail ? ` — ${m.detail}` : ""}`;
  }
}

export function TheHeThong({ sucKhoe, tieuDe = "Tình trạng hệ thống" }: { sucKhoe: SucKhoe | null; tieuDe?: string }) {
  const dungHet = sucKhoe?.status === "ok";
  const boQuetXau = (sucKhoe?.scanners ?? []).filter((b) => b.status === "stale" || b.status === "failing");
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
        tot={sucKhoe?.database === "ok" && Boolean(sucKhoe?.active_rule_set_states)}
        giaTri={sucKhoe?.active_rule_set_states ? `đã nạp · ${sucKhoe.active_rule_set_states} trạng thái` : "chưa nạp"}
      />
      {(sucKhoe?.scanners ?? []).map((b) => (
        <DongTrangThai
          key={b.name}
          nhan={b.label}
          tot={b.status !== "stale" && b.status !== "failing"}
          giaTri={chuBoQuet(b)}
        />
      ))}
      {sucKhoe?.language_model && (
        <DongTrangThai
          nhan="Mô hình ngôn ngữ"
          tot={sucKhoe.language_model.status !== "unreachable"}
          giaTri={chuMoHinh(sucKhoe.language_model)}
        />
      )}
      {sucKhoe?.embedding_model && (
        <DongTrangThai
          nhan="Mô hình nhúng"
          tot={sucKhoe.embedding_model.status !== "unreachable"}
          giaTri={chuMoHinh(sucKhoe.embedding_model, "tắt — không gợi ý hồ sơ tương tự")}
        />
      )}
      {!dungHet && (
        <p className="ghi-chu-tinh-trang">
          {sucKhoe?.detail ?? "Kiểm tra dịch vụ ứng dụng bằng docker compose logs backend."}
        </p>
      )}
      {boQuetXau.map((b) =>
        b.last_error ? (
          <p key={b.name} className="ghi-chu-tinh-trang">
            {b.label} — lỗi gần nhất: {b.last_error}
          </p>
        ) : null,
      )}
    </section>
  );
}
