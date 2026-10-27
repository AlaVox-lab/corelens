// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khối thông tin riêng trên trang hồ sơ (#250): nhãn và giá trị theo khai báo của loại yêu
// cầu hiện tại. Trường khai mà chưa có giá trị — ví dụ sau khi điều phối đổi loại lúc phân
// loại — hiện "chưa có", để người xử lý biết cần hỏi thêm người gửi.

import type { TruongRieng } from "@/lib/kieu";

function hien(t: TruongRieng, v: unknown): string {
  if (t.kind === "number" && typeof v === "number") {
    const so = v.toLocaleString("vi-VN");
    return t.unit ? `${so} ${t.unit}` : so;
  }
  if (t.kind === "date" && typeof v === "string") {
    const [n, th, ng] = v.split("-");
    return ng && th && n ? `${ng}/${th}/${n}` : v;
  }
  return String(v);
}

export function TheTruongRieng({ cacTruong, giaTri }: { cacTruong: TruongRieng[]; giaTri: Record<string, unknown> }) {
  if (cacTruong.length === 0) return null;
  return (
    <dl className="ds-truong-rieng">
      {cacTruong.map((t) => {
        const v = giaTri[t.code];
        const co = v !== undefined && v !== null && v !== "";
        return (
          <div key={t.code}>
            <dt>{t.label}</dt>
            <dd data-trong={co ? undefined : ""}>{co ? hien(t, v) : "chưa có"}</dd>
          </div>
        );
      })}
    </dl>
  );
}
