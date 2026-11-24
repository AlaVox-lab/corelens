// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Địa chỉ mã nguồn của dịch vụ khai phá quy trình (AGPL-3.0, điều 13 — #340). Từ #540 cổng dẫn tới đó ở
// MỘT chỗ: trang *Mã nguồn và giấy phép* (`app/ma-nguon/page.tsx`), mở từ chân thanh bên của mọi trang.
// Chỉ gọi ở máy chủ — biến môi trường không tới trình duyệt.

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

/**
 * Kho mã của cả Corelens, suy từ địa chỉ của dịch vụ khai phá — dịch vụ là một thư mục của kho, nên không
 * cần thêm biến môi trường. Nhận dạng đường dẫn thư mục kiểu GitHub/Gitea (`<kho>/tree/<nhánh>/services/
 * khai-pha`), GitLab (`<kho>/-/tree/<nhánh>/…`) hay `<kho>/services/khai-pha`. Không nhận ra thì trả nguyên
 * địa chỉ của dịch vụ — vẫn là mã nguồn đang chạy, chỉ hẹp hơn.
 */
export function khoMaCorelens(): string {
  const dichVu = nguonMaKhaiPha();
  const khop =
    /^(.+?)\/(?:-\/)?tree\/[^/]+\/services\/khai-pha\/?$/.exec(dichVu) ?? /^(.+?)\/services\/khai-pha\/?$/.exec(dichVu);
  return khop ? khop[1] : dichVu;
}
