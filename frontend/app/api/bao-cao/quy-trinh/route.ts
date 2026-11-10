// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Quy trình thực tế cho màn Báo cáo → Quy trình thực tế (#315).
//
// Trình duyệt gọi đây mỗi lần đổi khoảng ngày. Đi qua máy chủ Next.js như mọi lời gọi khác: token
// Keycloak không tới trình duyệt. Dịch vụ ứng dụng kiểm vai trò và gắn phạm vi phòng — tệp này
// không quyết ai xem được gì, chỉ chuyển nguyên JSON và đổi mã lỗi về bốn mã mà màn hình hiểu:
//
//   401 chưa đăng nhập · 403 vai không được xem báo cáo · 422 khoảng ngày sai · 503 còn lại
//
// 503 gồm cả dịch vụ khai phá tắt hay quá hạn chờ: màn hình nói "hệ thống không phản hồi", còn hồ
// sơ và các màn khác vẫn chạy.

import type { NextRequest } from "next/server";

import { docDichVu } from "@/lib/api";
import { docNgay } from "@/lib/khoang-ngay";
import type { QuyTrinhThucTe } from "@/lib/kieu";

export const dynamic = "force-dynamic";

const KHONG_LUU = { "cache-control": "no-store" };

export async function GET(yeuCau: NextRequest) {
  const tu = docNgay(yeuCau.nextUrl.searchParams.get("tu"));
  const den = docNgay(yeuCau.nextUrl.searchParams.get("den"));
  // Thiếu hay sai định dạng thì không cần làm phiền dịch vụ: nói luôn như khoảng sai
  if (!tu || !den) {
    return Response.json(
      { ma: "invalid-range", thongDiep: "Chọn đủ hai ngày, theo dạng ngày/tháng/năm." },
      { status: 422, headers: KHONG_LUU },
    );
  }

  const ketQua = await docDichVu<QuyTrinhThucTe>(`/analytics/process-mining?from=${tu}&to=${den}`);
  if (ketQua.ok) return Response.json(ketQua.duLieu, { headers: KHONG_LUU });

  const trangThai =
    ketQua.ma === "chua-dang-nhap"
      ? 401
      : ketQua.ma === "reports-forbidden"
        ? 403
        : ketQua.ma === "invalid-range"
          ? 422
          : 503;
  return Response.json(
    { ma: ketQua.ma, thongDiep: ketQua.thongDiep },
    { status: trangThai, headers: KHONG_LUU },
  );
}
