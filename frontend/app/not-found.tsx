// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Trang không tìm thấy (#235). Dùng chung cho đường dẫn sai và hồ sơ không mở được: dịch vụ
// trả 404 cho cả hồ sơ không tồn tại lẫn hồ sơ người này không có quyền xem, nên câu ở đây
// cố ý không nói là trường hợp nào — người dò số định danh không xác nhận được hồ sơ nào có thật.

import { FileQuestion } from "lucide-react";
import Link from "next/link";

import { ManRong } from "@/components/man-rong";

export default function KhongTimThay() {
  return (
    <main className="khung" style={{ padding: "72px 20px", maxWidth: "40rem" }}>
      <div className="the">
        <ManRong
          icon={FileQuestion}
          tieuDe="Không tìm thấy trang này"
          cau="Đường dẫn không đúng, hoặc hồ sơ không tồn tại hay bạn không có quyền xem."
        >
          <Link className="nut" data-loai="chinh" href="/">
            Về trang chủ
          </Link>
          <Link className="nut" href="/yeu-cau">
            Hồ sơ của tôi
          </Link>
        </ManRong>
      </div>
    </main>
  );
}
