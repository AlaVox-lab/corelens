// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn rỗng dùng chung (#234): biểu tượng, một câu nói vì sao trống, và một lối đi tiếp.
// Danh sách trống mà chỉ có chữ "Không có dữ liệu" thì người dùng không biết là do chưa có
// gì, do bộ lọc, hay do hỏng — mỗi chỗ dùng nói rõ trường hợp của nó và đặt hành động vào
// `children` (liên kết, hay nút xóa bộ lọc ở thành phần phía trình duyệt).

import type { LucideIcon } from "lucide-react";

export function ManRong({
  icon: Icon,
  tieuDe,
  cau,
  loi = false,
  children,
}: {
  icon: LucideIcon;
  tieuDe: string;
  cau: React.ReactNode;
  /** Trống vì hỏng, không phải vì chưa có gì: tiêu đề đổi màu báo lỗi. */
  loi?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <div className="rong" data-loi={loi ? "" : undefined}>
      <span className="icon-to">
        <Icon aria-hidden />
      </span>
      <h2>{tieuDe}</h2>
      <p>{cau}</p>
      {children ? <div className="rong-hanh-dong">{children}</div> : null}
    </div>
  );
}
