// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Địa chỉ mã nguồn của dịch vụ khai phá quy trình (AGPL-3.0, điều 13 — #340). Mọi chỗ của cổng hiện kết
// quả của dịch vụ đó cho người dùng qua mạng phải dẫn được tới mã nguồn của nó: màn Quy trình thực tế,
// và khối bước lệch trên trang hồ sơ (#448). Chỉ gọi ở máy chủ — biến môi trường không tới trình duyệt.

/** Compose đặt `MINING_SOURCE_URL`; giá trị dự phòng chỉ để chạy `npm run dev` ngoài cụm. Chỉ nhận
 * http(s) để không giá trị lạ nào thành liên kết chạy mã. */
export function nguonMaKhaiPha(): string {
  const duPhong = "https://github.com/AlaVox-lab/corelens/tree/main/services/khai-pha";
  try {
    const diaChi = new URL(process.env.MINING_SOURCE_URL ?? "");
    return diaChi.protocol === "https:" || diaChi.protocol === "http:" ? diaChi.href : duPhong;
  } catch {
    return duPhong;
  }
}
