"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Một con số trên thanh bên, trang chủ hay dải lọc (#237). Số đổi giá trị lúc người dùng đang xem
// — hộp thư tự tải lại, một việc vừa xong — thì chữ số cuộn vào từ phía số đi: lên khi tăng,
// xuống khi giảm, để mắt bắt được chỗ vừa đổi. Lần dựng đầu KHÔNG có hiệu ứng: số việc cần làm
// không bao giờ thoáng hiện 0 rồi đếm lên — người đọc lướt sẽ tưởng không có việc.

import { useEffect, useRef, useState } from "react";

export function SoCuon({ so }: { so: number }) {
  const truoc = useRef(so);
  const [doi, datDoi] = useState<{ lan: number; huong: "len" | "xuong" } | null>(null);

  useEffect(() => {
    if (so === truoc.current) return;
    const huong = so > truoc.current ? "len" : "xuong";
    truoc.current = so;
    datDoi((d) => ({ lan: (d?.lan ?? 0) + 1, huong }));
  }, [so]);

  // Khóa theo lần đổi: phần tử mới gắn vào trang thì hiệu ứng chạy lại từ đầu
  return (
    <span key={doi?.lan ?? 0} className="so-cuon" data-huong={doi?.huong}>
      {so}
    </span>
  );
}
