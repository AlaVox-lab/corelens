"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Nút mở / thu gọn dòng thời gian trên trang hồ sơ (#189). Giảng viên nhận xét trang hồ sơ
// nghiêng về xem nhật ký; người dùng mở hồ sơ cần thấy việc của mình trước. Mặc định thu
// gọn — chỉ còn bước hiện tại —, mở ra thì đầy đủ như cũ.
//
// Trạng thái nằm trên <html data-dong-thoi-gian="mo">, không trong state React: đoạn mã đầu
// trang (app/layout.tsx) đặt nó trước khi trình duyệt vẽ, nên người đã chọn mở không thấy
// trang nháy từ thu sang mở. CSS ở globals.css ẩn hiện hai khối theo thuộc tính đó. Lựa chọn
// nhớ trên trình duyệt như nút sáng/tối, áp cho mọi trang hồ sơ.

import { ChevronDown } from "lucide-react";
import { useEffect, useState } from "react";

export const KHOA_DONG_THOI_GIAN = "dxlab-dong-thoi-gian";

export function NutDongThoiGian({ soMoc, idDay }: { soMoc: number; idDay: string }) {
  const [mo, datMo] = useState(false);

  // Đọc trạng thái thật sau khi nhận trang — bản dựng ở máy chủ không biết lựa chọn đã nhớ
  useEffect(() => {
    datMo(document.documentElement.dataset.dongThoiGian === "mo");
  }, []);

  return (
    <button
      type="button"
      className="nut nut-nho nut-dtg"
      aria-expanded={mo}
      aria-controls={idDay}
      onClick={() => {
        const moi = !mo;
        datMo(moi);
        if (moi) document.documentElement.dataset.dongThoiGian = "mo";
        else delete document.documentElement.dataset.dongThoiGian;
        try {
          localStorage.setItem(KHOA_DONG_THOI_GIAN, moi ? "mo" : "thu");
        } catch {
          // Trình duyệt chặn lưu trữ: vẫn mở/thu được, chỉ không nhớ cho lần sau
        }
      }}
    >
      {/* Chữ đổi theo thuộc tính trên <html>, nên đúng ngay từ lần vẽ đầu */}
      <span className="khi-thu">Xem toàn bộ {soMoc} mốc</span>
      <span className="khi-mo">Thu gọn</span>
      <ChevronDown aria-hidden />
    </button>
  );
}
