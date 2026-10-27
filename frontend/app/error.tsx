"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Trang lỗi chung (#235). Trang nào ném lỗi khi dựng — thường là dịch vụ ứng dụng không phản
// hồi hay quá thời hạn chờ — thì rơi vào đây thay cho trang lỗi mặc định tiếng Anh của Next.
// Chữ theo ARCHITECTURE mục 8.3: "hệ thống không phản hồi", không nói tên dịch vụ hay mã lỗi.

import { RefreshCw, ServerCrash } from "lucide-react";
import Link from "next/link";

import { ManRong } from "@/components/man-rong";

export default function TrangLoi({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="khung" style={{ padding: "72px 20px", maxWidth: "40rem" }}>
      <div className="the">
        <ManRong
          icon={ServerCrash}
          loi
          tieuDe="Hệ thống không phản hồi"
          cau="Trang này chưa tải được. Hồ sơ và mọi thao tác trước đó vẫn còn nguyên — thử lại sau ít phút."
        >
          <button className="nut" data-loai="chinh" type="button" onClick={reset}>
            <RefreshCw aria-hidden />
            Thử lại
          </button>
          <Link className="nut" href="/">
            Về trang chủ
          </Link>
        </ManRong>
      </div>
    </main>
  );
}
