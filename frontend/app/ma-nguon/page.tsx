// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Trang Mã nguồn và giấy phép (#540): chỗ cố định duy nhất của cổng dẫn tới mã nguồn, mở từ chân thanh
// bên của mọi trang. Đáp ứng điều 13 của AGPL cho hai thành phần AGPL mà người dùng tương tác qua mạng —
// dịch vụ khai phá quy trình và, khi bật, kho tri thức Wiki.js — thay cho các dòng giấy phép trước đây
// chen giữa nội dung nghiệp vụ. Mọi người đăng nhập đều vào được.
//
// Không địa chỉ nào viết cứng: dịch vụ khai phá đọc `MINING_SOURCE_URL`, kho Corelens suy từ địa chỉ đó
// (`lib/nguon-ma-khai-pha.ts`), Wiki.js lấy `knowledge_base.source_url` mà `/me` trả.

import { KhungLamViec } from "@/components/khung-lam-viec";
import { goiDichVu, type DanhTinh } from "@/lib/api";
import { khoMaCorelens, nguonMaKhaiPha } from "@/lib/nguon-ma-khai-pha";

export const dynamic = "force-dynamic";

type ThanhPhan = { ten: string; viec: string; giayPhep: string; url: string };

/** Địa chỉ đọc được, bỏ giao thức: chữ của liên kết vừa cho biết nó dẫn đi đâu, vừa khác nhau giữa các dòng. */
function chuDiaChi(url: string): string {
  return url.replace(/^https?:\/\//, "").replace(/\/$/, "");
}

export default async function TrangMaNguon() {
  const toi = await goiDichVu<DanhTinh>("/me");
  const cacThanhPhan: ThanhPhan[] = [
    {
      ten: "Corelens",
      viec: "Cổng, dịch vụ ứng dụng và cấu hình cụm.",
      giayPhep: "MIT, riêng thư mục services/khai-pha theo AGPL-3.0-or-later",
      url: khoMaCorelens(),
    },
    {
      ten: "Dịch vụ khai phá quy trình",
      viec: "Dựng quy trình thực tế từ dòng thời gian của hồ sơ, tìm bước đi lệch.",
      giayPhep: "AGPL-3.0-or-later",
      url: nguonMaKhaiPha(),
    },
    ...(toi?.knowledge_base
      ? [
          {
            ten: "Wiki.js",
            viec: "Kho tri thức.",
            giayPhep: "AGPL-3.0",
            url: toi.knowledge_base.source_url,
          },
        ]
      : []),
  ];

  return (
    <KhungLamViec canKhongGian="portal">
      <h1 className="tieu-de-trang">Mã nguồn và giấy phép</h1>
      <p className="cau-chao">Corelens là phần mềm nguồn mở. Mã nguồn của từng thành phần ở dưới.</p>
      <ul className="the ds-ma-nguon">
        {cacThanhPhan.map((t) => (
          <li key={t.ten}>
            <div>
              <h2>{t.ten}</h2>
              <p>{t.viec}</p>
            </div>
            <dl>
              <dt>Giấy phép</dt>
              <dd>{t.giayPhep}</dd>
              <dt>Mã nguồn</dt>
              <dd>
                <a href={t.url} target="_blank" rel="noopener noreferrer" data-ma-nguon={t.ten}>
                  {chuDiaChi(t.url)}
                </a>
              </dd>
            </dl>
          </li>
        ))}
      </ul>
    </KhungLamViec>
  );
}
