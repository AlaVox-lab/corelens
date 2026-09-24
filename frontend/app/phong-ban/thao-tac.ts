"use server";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Thao tác ghi của buồng lái phòng ban (#83).
//
// Cùng nguyên tắc với app/dieu-phoi/thao-tac.ts: không kiểm nghiệp vụ nào ở đây. Người
// được giao chỉ gửi đi bằng định danh; dịch vụ tra danh bạ để kiểm người đó nhận được
// việc của phòng và tự lấy tên của họ — trình duyệt không gửi tên lên.
//
// Nhớ: tệp mang chỉ thị "use server" chỉ được xuất hàm bất đồng bộ.

import { revalidatePath } from "next/cache";

import { CHUA_CO_LOI, type KetQuaThaoTac } from "@/app/yeu-cau/ket-qua";
import { guiDichVu } from "@/lib/api";
import { chuoi, docLoiNhan, gomThayDoi } from "@/lib/bieu-mau";
import type { HoSoPhongBan } from "@/lib/kieu";

export async function chuyenTrangThaiPhongBan(
  _truoc: KetQuaThaoTac,
  duLieu: FormData,
): Promise<KetQuaThaoTac> {
  const maHoSo = chuoi(duLieu.get("case_id"));
  const den = chuoi(duLieu.get("to_state"));
  const lyDo = chuoi(duLieu.get("note"));

  if (!maHoSo || !den) {
    return { loi: "Thiếu thông tin thao tác. Tải lại trang rồi thử lại." };
  }

  const ketQua = await guiDichVu<HoSoPhongBan>(
    `/department/requests/${maHoSo}/transitions`,
    { to_state: den, note: lyDo || null, changes: gomThayDoi(duLieu) },
  );

  if (!ketQua.ok) return { loi: ketQua.thongDiep };

  revalidatePath("/phong-ban");
  revalidatePath(`/phong-ban/${maHoSo}`);
  // Người gửi thấy ngay hồ sơ của mình đã được nhận hay đã xong
  revalidatePath(`/yeu-cau/${maHoSo}`);
  revalidatePath("/yeu-cau");
  // Hồ sơ bị trả về thì quay lại hàng đợi điều phối
  revalidatePath("/dieu-phoi");
  return CHUA_CO_LOI;
}

/** Gửi một lời nhắn trên hồ sơ của phòng (#128) — thường là trả lời người gửi. */
export async function guiLoiNhanPhongBan(
  _truoc: KetQuaThaoTac,
  duLieu: FormData,
): Promise<KetQuaThaoTac> {
  const doc = docLoiNhan(duLieu);
  if (!doc) return { loi: "Thiếu thông tin lời nhắn. Tải lại trang rồi thử lại." };

  const ketQua = await guiDichVu<HoSoPhongBan>(
    `/department/requests/${doc.maHoSo}/messages`,
    doc.than,
  );
  if (!ketQua.ok) return { loi: ketQua.thongDiep };

  revalidatePath("/phong-ban");
  revalidatePath(`/phong-ban/${doc.maHoSo}`);
  revalidatePath(`/yeu-cau/${doc.maHoSo}`);
  revalidatePath("/yeu-cau");
  revalidatePath("/dieu-phoi");
  return CHUA_CO_LOI;
}
