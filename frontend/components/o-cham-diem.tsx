"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Ô chấm mức hài lòng trong bảng xác nhận của người gửi (#433). Hiện khi cạnh mang cờ dữ liệu
// `collects_feedback` — tệp này không biết bước nào là "Xác nhận đạt".
//
// Nhóm chấm là radio thật trong `fieldset`/`legend`: phím mũi tên chạy trong nhóm, trình đọc màn hình đọc
// "1 trên 5"… Lựa chọn "Không chấm" đứng đầu và chọn sẵn — nhóm radio không bỏ chọn được, nên đây là lối
// quay về "chưa chấm". Cả điểm và nhận xét đều không bắt buộc; nhận xét chỉ gửi đi khi có điểm.

import { Star } from "lucide-react";
import { useState } from "react";

const CAC_DIEM = [1, 2, 3, 4, 5] as const;

export function OChamDiem({ toiDa }: { toiDa: number }) {
  const [diem, datDiem] = useState("");
  const [nhanXet, datNhanXet] = useState("");
  const soKyTu = nhanXet.trim().length;
  const qua = soKyTu > toiDa;

  return (
    <div className="cham-diem">
      <fieldset>
        <legend>
          Bạn hài lòng với cách xử lý đến đâu?
          <span className="nhat"> — không bắt buộc</span>
        </legend>
        <div className="cham-diem-hang">
          <label className="cham-diem-o" data-bo-chon="">
            <input
              type="radio"
              name="feedback_score"
              value=""
              checked={diem === ""}
              onChange={() => datDiem("")}
            />
            <span>Không chấm</span>
          </label>
          {CAC_DIEM.map((d) => (
            <label key={d} className="cham-diem-o">
              <input
                type="radio"
                name="feedback_score"
                value={d}
                checked={diem === String(d)}
                onChange={() => datDiem(String(d))}
                aria-label={`${d} trên 5`}
              />
              <Star aria-hidden data-day={Number(diem) >= d ? "" : undefined} />
              <span aria-hidden>{d}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <label style={{ display: "grid", gap: "6px" }}>
        <span style={{ fontSize: "13.5px", fontWeight: 600 }}>
          Nhận xét
          <span className="nhat" style={{ fontWeight: 400 }}> — không bắt buộc, gửi kèm khi có điểm</span>
        </span>
        <textarea
          name="feedback_comment"
          className="o-nhap"
          rows={3}
          value={nhanXet}
          onChange={(e) => datNhanXet(e.target.value)}
          aria-describedby="cham-diem-dem"
          aria-invalid={qua || undefined}
          placeholder="Điều gì làm tốt, điều gì nên làm khác. Điều phối viên và phòng ban đọc được."
        />
        <span id="cham-diem-dem" className="cham-diem-dem" data-qua={qua ? "" : undefined}>
          {soKyTu}/{toiDa} ký tự{qua ? ` — bớt ${soKyTu - toiDa} ký tự` : ""}
        </span>
      </label>
    </div>
  );
}
