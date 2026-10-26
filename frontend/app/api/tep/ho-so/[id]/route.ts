// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Tải tệp đính kèm lên một hồ sơ (#80).
//
// Cùng lý do với tải về: trình duyệt gửi cho máy chủ Next.js, máy chủ Next.js gửi cho dịch vụ
// ứng dụng kèm token. Không dùng Server Action vì Server Action giới hạn thân yêu cầu 1 MB
// mặc định, mà tệp đính kèm lớn hơn nhiều — giới hạn thật do dịch vụ quyết, và giao diện hỏi
// dịch vụ thay vì tự giữ một con số thứ hai ở đây.

import { guiBieuMauDichVu } from "@/lib/api";
import type { TepDinhKem } from "@/lib/kieu";

export const dynamic = "force-dynamic";

export async function POST(
  yeuCau: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) {
    return Response.json({ ok: false, thongDiep: "Không tìm thấy hồ sơ." }, { status: 404 });
  }

  let bieuMau: FormData;
  try {
    bieuMau = await yeuCau.formData();
  } catch {
    return Response.json({ ok: false, thongDiep: "Không đọc được tệp gửi lên." }, { status: 400 });
  }

  const ketQua = await guiBieuMauDichVu<TepDinhKem[]>(`/requests/${id}/attachments`, bieuMau);
  if (!ketQua.ok) {
    return Response.json(
      { ok: false, ma: ketQua.ma, thongDiep: ketQua.thongDiep },
      { status: ketQua.ma === "chua-dang-nhap" ? 401 : 422 },
    );
  }
  return Response.json({ ok: true, tep: ketQua.duLieu }, { status: 201 });
}
