"use server";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Thao tác ghi của buồng lái điều phối viên.
//
// Cùng nguyên tắc với app/yeu-cau/thao-tac.ts: không kiểm nghiệp vụ nào ở đây. Engine
// kiểm cạnh, vai trò, trường được phép (#78), giá trị trong danh mục và ràng buộc trên
// cạnh. Việc ở đây chỉ là gom biểu mẫu thành `changes` rồi gửi đi.
//
// Nhớ: tệp mang chỉ thị "use server" chỉ được xuất hàm bất đồng bộ. Hằng số và kiểu
// dùng chung nằm ở app/yeu-cau/ket-qua.ts.

import { revalidatePath } from "next/cache";

import { CHUA_CO_LOI, type KetQuaThaoTac } from "@/app/yeu-cau/ket-qua";
import { guiDichVu } from "@/lib/api";
import { chuoi, gomThayDoi } from "@/lib/bieu-mau";
import type { HoSoDieuPhoi } from "@/lib/kieu";

export async function chuyenTrangThaiDieuPhoi(
  _truoc: KetQuaThaoTac,
  duLieu: FormData,
): Promise<KetQuaThaoTac> {
  const maHoSo = chuoi(duLieu.get("case_id"));
  const den = chuoi(duLieu.get("to_state"));
  const lyDo = chuoi(duLieu.get("note"));

  if (!maHoSo || !den) {
    return { loi: "Thiếu thông tin thao tác. Tải lại trang rồi thử lại." };
  }

  const ketQua = await guiDichVu<HoSoDieuPhoi>(
    `/coordination/requests/${maHoSo}/transitions`,
    { to_state: den, note: lyDo || null, changes: gomThayDoi(duLieu) },
  );

  if (!ketQua.ok) return { loi: ketQua.thongDiep };

  revalidatePath("/dieu-phoi");
  revalidatePath(`/dieu-phoi/${maHoSo}`);
  // Hồ sơ đổi trạng thái thì cổng người gửi cũng phải thấy ngay, không đợi bộ đệm hết hạn
  revalidatePath(`/yeu-cau/${maHoSo}`);
  revalidatePath("/yeu-cau");
  // Hồ sơ vừa được chuyển về phòng ban thì hàng đợi phòng ban cũng phải thấy ngay
  revalidatePath("/phong-ban");
  return CHUA_CO_LOI;
}
