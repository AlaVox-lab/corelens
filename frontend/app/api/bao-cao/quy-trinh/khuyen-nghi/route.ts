// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khuyến nghị cải tiến bằng câu chữ cho màn Quy trình thực tế (#320).
//
// Màn gọi đây SAU khi đã hiện kết quả khai phá, và hỏi lại vài giây một lần khi dịch vụ báo `pending`.
// KHÔNG BAO GIỜ trả lỗi cho màn: chưa đăng nhập, không được xem, dịch vụ hay mô hình tắt — đều là
// "không có khuyến nghị", màn giữ nguyên câu kết luận dựng từ con số.

import type { NextRequest } from "next/server";

import { docDichVu } from "@/lib/api";
import { docNgay } from "@/lib/khoang-ngay";
import type { KhuyenNghiQuyTrinh } from "@/lib/kieu";

export const dynamic = "force-dynamic";

const KHONG_LUU = { "cache-control": "no-store" };
const KHONG_CO: KhuyenNghiQuyTrinh = { status: "unavailable", sentences: [] };

export async function GET(yeuCau: NextRequest) {
  const tu = docNgay(yeuCau.nextUrl.searchParams.get("tu"));
  const den = docNgay(yeuCau.nextUrl.searchParams.get("den"));
  if (!tu || !den) return Response.json(KHONG_CO, { headers: KHONG_LUU });

  const ketQua = await docDichVu<KhuyenNghiQuyTrinh>(
    `/analytics/process-mining/recommendation?from=${tu}&to=${den}`,
  );
  return Response.json(ketQua.ok ? ketQua.duLieu : KHONG_CO, { headers: KHONG_LUU });
}
