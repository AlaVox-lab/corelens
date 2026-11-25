"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Ô chấm mức hài lòng trong bảng xác nhận của người gửi (#433). Hiện khi cạnh mang cờ dữ liệu
// `collects_feedback` — tệp này không biết bước nào là "Xác nhận đạt".
//
// Nhóm chấm là radio thật trong `fieldset`/`legend`: phím mũi tên chạy trong nhóm, trình đọc màn hình đọc
// "1 trên 5"… Lựa chọn "Không chấm" đứng đầu và chọn sẵn — nhóm radio không bỏ chọn được, nên đây là lối
// quay về "chưa chấm". Điểm không bắt buộc.
//
// Nhận xét không có ô riêng ở đây nữa (#557): bảng xác nhận đã có ô ghi chú của bước, và hai ô chữ tự do
// cạnh nhau làm người gửi không biết viết vào đâu. Chữ ở ô ghi chú vừa là ghi chú của bước (dòng thời gian),
// vừa là nhận xét kèm điểm khi có chấm — `app/yeu-cau/thao-tac.ts` gửi cả hai.

import { Star } from "lucide-react";
import { useState } from "react";

const CAC_DIEM = [1, 2, 3, 4, 5] as const;

export function OChamDiem() {
  const [diem, datDiem] = useState("");

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
    </div>
  );
}
