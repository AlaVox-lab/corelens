// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Dấu hiệu lời nhắn trên danh sách hồ sơ (#128).
//
// Suy từ ai nhắn sau cùng — dịch vụ trả `last_message_from_requester` — không theo dõi
// đã đọc hay chưa (chốt với navigator ngày 24/09/2026). Hai góc nhìn, hai câu:
//
//   nhân viên — lời nhắn cuối là của người gửi: người gửi đang chờ trả lời
//   người gửi — lời nhắn cuối là của nhân viên: đã có trả lời
//
// Hồ sơ đã kết thúc thì không hiện: không còn ai phải làm gì với nó.

import type { HoSoTomTat } from "@/lib/kieu";

export function DauLoiNhan({
  hoSo,
  gocNhin,
}: {
  hoSo: Pick<HoSoTomTat, "last_message_from_requester" | "state">;
  gocNhin: "nhan-vien" | "nguoi-gui";
}) {
  const cuoi = hoSo.last_message_from_requester;
  const hien = gocNhin === "nhan-vien" ? cuoi === true : cuoi === false;
  if (!hien || hoSo.state.is_terminal) return null;

  return (
    <span
      style={{
        fontFamily: "var(--font)",
        padding: "1px 8px",
        borderRadius: "999px",
        background: "var(--accent-soft)",
        border: "1px solid var(--accent-line)",
        color: "var(--accent-2)",
        fontSize: "12px",
        fontWeight: 600,
      }}
    >
      <span aria-hidden="true">✉ </span>
      {gocNhin === "nhan-vien" ? "Người gửi đang chờ trả lời" : "Có trả lời"}
    </span>
  );
}
