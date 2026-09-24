"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khung gửi lời nhắn trên hồ sơ (#128, ADR-0005). Dùng chung cho cổng người gửi và hai
// buồng lái; mỗi nơi truyền vào thao tác gửi đi của riêng nó, vì mỗi nơi có một cửa riêng
// ở phía dịch vụ.
//
// Cùng khuôn với bảng thao tác (ARCHITECTURE.md mục 7.2): nút dựng từ `message_kinds` mà
// dịch vụ trả về. Không có bảng "vai trò nào gửi được loại nào" hay "trạng thái nào được
// hỏi tiến độ" trong tệp này — danh sách đã được dịch vụ lọc theo dữ liệu.
//
// Lời nhắn khác thao tác trên hồ sơ ở chỗ nó không đổi gì: không trạng thái, không đồng
// hồ, không bắt ai phải trả lời. Câu dưới ô nhập nói rõ điều đó, để không ai tưởng gửi
// lời nhắn là đã "hỏi thêm thông tin" chính thức.

import { useActionState } from "react";

import { CHUA_CO_LOI, type KetQuaThaoTac } from "@/app/yeu-cau/ket-qua";
import { ngayGio } from "@/lib/dinh-dang";
import type { LoaiLoiNhan } from "@/lib/kieu";

export function KhungLoiNhan({
  maHoSo,
  cacLoai,
  daKetThuc,
  hanhDong,
}: {
  maHoSo: number;
  cacLoai: LoaiLoiNhan[];
  /** Hồ sơ ở trạng thái kết thúc: lời nhắn chỉ còn để đọc. */
  daKetThuc: boolean;
  /** Thao tác gửi đi — một server action của nơi đang dùng khung này. */
  hanhDong: (truoc: KetQuaThaoTac, duLieu: FormData) => Promise<KetQuaThaoTac>;
}) {
  const [ketQua, thucHien, dangChay] = useActionState(hanhDong, CHUA_CO_LOI);

  if (cacLoai.length === 0) {
    return (
      <p style={{ margin: 0, fontSize: "13px", color: "var(--ink-3)", lineHeight: 1.6 }}>
        {daKetThuc
          ? "Hồ sơ đã kết thúc — lời nhắn chỉ còn để đọc."
          : "Bạn chưa gửi được lời nhắn trên hồ sơ này."}
      </p>
    );
  }

  // Ô nội dung bắt buộc khi có loại cần nội dung; nút của loại không cần thì bỏ qua phép
  // kiểm của trình duyệt (`formNoValidate`) — "Hỏi tiến độ" bấm là gửi được ngay.
  const coLoaiCanNoiDung = cacLoai.some((k) => k.body_required);
  const dangCho = cacLoai.filter((k) => k.retry_at);

  return (
    <form action={thucHien} style={{ display: "grid", gap: "10px" }}>
      <input type="hidden" name="case_id" value={maHoSo} />
      <textarea
        name="body"
        className="o-nhap"
        rows={3}
        maxLength={2000}
        required={coLoaiCanNoiDung}
        placeholder="Nhắn thêm cho các bên đang giữ hồ sơ. Lời nhắn không đổi trạng thái và không dừng đồng hồ."
      />
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
        {cacLoai.map((k, i) => (
          <button
            key={k.code}
            type="submit"
            name="kind"
            value={k.code}
            className="nut"
            data-loai={i === 0 ? "chinh" : undefined}
            formNoValidate={!k.body_required}
            disabled={dangChay || k.retry_at !== null}
            title={k.description ?? undefined}
          >
            {dangChay ? "Đang gửi…" : k.label}
          </button>
        ))}
      </div>
      {dangCho.map((k) => (
        <span
          key={k.code}
          role="status"
          style={{ fontSize: "12.5px", color: "var(--ink-3)", lineHeight: 1.55 }}
        >
          Bạn đã “{k.label}”, chưa có ai trả lời. Gửi lại được ngay khi có trả lời, hoặc sau{" "}
          {ngayGio(k.retry_at as string)}.
        </span>
      ))}
      {ketQua.loi && (
        <p
          role="alert"
          style={{
            margin: 0,
            padding: "12px 14px",
            borderRadius: "11px",
            background: "var(--f-r-bg)",
            border: "1px solid var(--f-r-line)",
            color: "var(--f-r-ink)",
            fontSize: "13.5px",
            lineHeight: 1.6,
          }}
        >
          {ketQua.loi}
        </p>
      )}
    </form>
  );
}
