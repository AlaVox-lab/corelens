// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khối chỉ đọc "Đánh giá của người gửi" (#433) — một component cho ba trang hồ sơ: người gửi xem lại điểm
// của mình, điều phối viên và phòng ban đọc điểm kèm nhận xét. Hồ sơ mở lại rồi xác nhận lần nữa có nhiều
// lần chấm: liệt kê, mới nhất trước. Chưa có lần chấm nào thì không hiện gì.

import { Star } from "lucide-react";

import { ngayGio } from "@/lib/dinh-dang";
import type { DanhGia } from "@/lib/kieu";

export function TheDanhGia({ danhGia, cuaToi = false }: { danhGia?: DanhGia[]; cuaToi?: boolean }) {
  if (!danhGia || danhGia.length === 0) return null;
  const moiTruoc = [...danhGia].reverse();
  return (
    <section className="the khoi the-danh-gia" aria-labelledby="the-danh-gia-tieu-de">
      <h2 id="the-danh-gia-tieu-de" className="khoi-dau">
        {cuaToi ? "Đánh giá của bạn" : "Đánh giá của người gửi"}
      </h2>
      <ol>
        {moiTruoc.map((d) => (
          <li key={d.created_at}>
            <p className="the-danh-gia-diem">
              <span className="an-di">{d.score} trên 5</span>
              <span aria-hidden className="the-danh-gia-sao">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Star key={i} data-day={i <= d.score ? "" : undefined} />
                ))}
              </span>
              <b aria-hidden>{d.score}/5</b>
              <span className="nhat">· {ngayGio(d.created_at)}</span>
            </p>
            {d.comment ? <p className="the-danh-gia-nhan-xet">{d.comment}</p> : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
