"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Một ô bật/tắt cho một loại thông báo thư (#251). Đổi là lưu ngay, không có nút Lưu riêng —
// danh sách ngắn, mỗi ô độc lập. Lưu hỏng thì ô trả về trạng thái cũ và báo lý do.

import { useState, useTransition } from "react";

import { doiThongBao } from "./thao-tac";

export function OThongBao({
  ma,
  nhan,
  moTa,
  batSan,
}: Readonly<{ ma: string; nhan: string; moTa: string | null; batSan: boolean }>) {
  const [bat, setBat] = useState(batSan);
  const [loi, setLoi] = useState<string | null>(null);
  const [dangLuu, batDauLuu] = useTransition();

  function doi(moi: boolean) {
    setBat(moi);
    setLoi(null);
    batDauLuu(async () => {
      const kq = await doiThongBao(ma, moi);
      if (!kq.ok) {
        setBat(!moi);
        setLoi(kq.thongDiep ?? "Chưa lưu được. Thử lại sau ít phút.");
      }
    });
  }

  return (
    <li style={{ padding: "12px 0", borderBottom: "1px solid var(--line)" }}>
      <label style={{ display: "flex", gap: "12px", alignItems: "flex-start", cursor: "pointer" }}>
        <input
          type="checkbox"
          checked={bat}
          disabled={dangLuu}
          onChange={(e) => doi(e.target.checked)}
          data-loai-thong-bao={ma}
          style={{ marginTop: "4px" }}
        />
        <span>
          <b>{nhan}</b>
          {moTa ? (
            <span className="nhat" style={{ display: "block", fontSize: "13px" }}>
              {moTa}
            </span>
          ) : null}
        </span>
      </label>
      {loi ? (
        <p role="alert" className="nhat" style={{ fontSize: "13px", marginTop: "4px" }}>
          {loi}
        </p>
      ) : null}
    </li>
  );
}
