// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Hình dạng kết quả của hai thao tác ghi, tách khỏi `thao-tac.ts`.
//
// VÌ SAO PHẢI TÁCH RA MỘT TỆP RIÊNG: một tệp mang chỉ thị `"use server"` chỉ được
// xuất ra hàm bất đồng bộ, không được xuất hằng số hay đối tượng. Lý do là mọi thứ
// tệp đó xuất ra đều trở thành một điểm cuối gọi được từ trình duyệt, và một đối
// tượng thì không phải điểm cuối.
//
// Điều đáng nhớ: `next build` KHÔNG bắt lỗi này. Nó chỉ nổ ra lúc chạy, khi một
// thành phần phía trình duyệt nạp tệp đó — nghĩa là trang vẫn dựng xong, vẫn lên
// ảnh chứa, rồi trả 500 ngay lần đầu người dùng mở. Đây chính là loại lỗi mà chỉ
// việc chạy thử thật mới tìm ra.

export type KetQuaThaoTac = {
  /** Thông điệp lỗi để hiện cạnh biểu mẫu. Chuỗi rỗng nghĩa là chưa có lỗi nào. */
  loi: string;
  /** Mã hồ sơ vừa tạo (#80): biểu mẫu gửi tải tệp lên hồ sơ đó rồi mới chuyển trang. */
  id?: number;
};

export const CHUA_CO_LOI: KetQuaThaoTac = { loi: "" };
