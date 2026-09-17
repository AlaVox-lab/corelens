"use server";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Hai thao tác ghi của cổng gửi yêu cầu.
//
// Chạy trên máy chủ Next.js, không phải trong trình duyệt. Nhờ vậy token vẫn nằm
// trong cookie đã mã hóa và không bao giờ đi qua mã JavaScript phía người dùng — xem
// lib/session.ts.
//
// ĐIỀU QUAN TRỌNG NHẤT Ở TỆP NÀY: không có phép kiểm nghiệp vụ nào. Không kiểm vai
// trò, không kiểm cạnh nào đi được, không kiểm trường nào bắt buộc ghi lý do. Toàn bộ
// những thứ đó do engine máy trạng thái quyết định, và nó đã kiểm rồi. Kiểm lại ở đây
// sẽ tạo ra nguồn sự thật thứ hai, rồi hai nguồn lệch nhau — mà bản sao ở giao diện
// bao giờ cũng là bản lệch, vì nó xa dữ liệu hơn.
//
// Việc duy nhất ở đây: gom dữ liệu biểu mẫu, gọi dịch vụ, và dịch lỗi trả về thành
// câu cho người đọc.

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { CHUA_CO_LOI, type KetQuaThaoTac } from "@/app/yeu-cau/ket-qua";
import { guiDichVu } from "@/lib/api";
import type { HoSoChiTiet } from "@/lib/kieu";

function chuoiHoacRong(gia_tri: FormDataEntryValue | null): string {
  return typeof gia_tri === "string" ? gia_tri.trim() : "";
}

/**
 * Gửi một yêu cầu mới rồi đưa thẳng người dùng tới hồ sơ vừa tạo.
 *
 * Chuyển trang ngay thay vì hiện một hộp thoại "đã gửi thành công": người dùng cần
 * thấy mã hồ sơ và trạng thái thật của nó, chứ không cần một lời khen.
 */
export async function guiYeuCau(
  _truoc: KetQuaThaoTac,
  duLieu: FormData,
): Promise<KetQuaThaoTac> {
  const tieuDe = chuoiHoacRong(duLieu.get("title"));
  const moTa = chuoiHoacRong(duLieu.get("description"));
  const loai = chuoiHoacRong(duLieu.get("request_type_code"));

  if (tieuDe.length < 3) {
    return { loi: "Tiêu đề phải dài ít nhất 3 ký tự." };
  }

  const ketQua = await guiDichVu<HoSoChiTiet>("/requests", {
    title: tieuDe,
    description: moTa || null,
    request_type_code: loai || null,
  });

  if (!ketQua.ok) return { loi: ketQua.thongDiep };

  revalidatePath("/yeu-cau");
  redirect(`/yeu-cau/${ketQua.duLieu.id}`);
}

/**
 * Đi một cạnh trên hồ sơ.
 *
 * `to_state` lấy từ chính danh sách `allowed_transitions` mà dịch vụ trả về, nên giao
 * diện không bao giờ tự nghĩ ra một đích đến. Dù vậy engine vẫn kiểm lại — chặn ở
 * giao diện chỉ là nửa đầu của Poka-yoke, nửa sau nằm ở engine và không bỏ được.
 */
export async function chuyenTrangThai(
  _truoc: KetQuaThaoTac,
  duLieu: FormData,
): Promise<KetQuaThaoTac> {
  const maHoSo = chuoiHoacRong(duLieu.get("case_id"));
  const den = chuoiHoacRong(duLieu.get("to_state"));
  const lyDo = chuoiHoacRong(duLieu.get("note"));

  if (!maHoSo || !den) {
    return { loi: "Thiếu thông tin thao tác. Tải lại trang rồi thử lại." };
  }

  const ketQua = await guiDichVu<HoSoChiTiet>(
    `/requests/${maHoSo}/transitions`,
    { to_state: den, note: lyDo || null },
  );

  if (!ketQua.ok) return { loi: ketQua.thongDiep };

  revalidatePath("/yeu-cau");
  revalidatePath(`/yeu-cau/${maHoSo}`);
  return CHUA_CO_LOI;
}
