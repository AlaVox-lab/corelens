// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Siêu dữ liệu TRÌNH BÀY của trạng thái hồ sơ.
//
// ĐỌC KỸ TRƯỚC KHI SỬA — ranh giới ở đây rất dễ vượt qua mà không nhận ra:
//
//   Tệp này KHÔNG chứa nhãn tiếng Việt của trạng thái, KHÔNG chứa danh sách trạng
//   thái nào tồn tại, và KHÔNG quyết định nút nào hiện ra. Ba thứ đó nằm trong cơ sở
//   dữ liệu và đi tới đây qua API. Viết chúng vào mã nguồn giao diện là chép danh mục
//   nghiệp vụ ra chỗ thứ hai, và hai chỗ sẽ lệch nhau ngay lần đầu doanh nghiệp khai
//   lại quy trình của họ — đúng thứ CLAUDE.md mục 1.2 cấm.
//
//   Tệp này CHỈ chứa thứ thuần tuý thị giác: mỗi trạng thái mang dấu hiệu gì, thuộc
//   họ màu nào, xếp vào nhóm nào. Không có chỗ nào trong cơ sở dữ liệu lưu những
//   thông tin đó, và cũng không nên có: bảng `states` mô tả quy trình, không mô tả
//   cách vẽ quy trình.
//
// VÌ SAO PHẢI CÓ DẤU HIỆU RIÊNG cho từng trạng thái, chứ không chỉ màu: bản in đen
// trắng không có màu, và khoảng 8% nam giới không phân biệt được đỏ với xanh lá. Nếu
// màu là thứ duy nhất phân biệt mười trạng thái thì với những người đó, giao diện chỉ
// còn mười cái nhãn xám giống hệt nhau.
//
// KHI GẶP TRẠNG THÁI LẠ: trả về phương án lùi thay vì ném lỗi. Doanh nghiệp thêm một
// trạng thái vào bảng `states` phải thấy nó hiện ra ngay, dù chưa ai gán dấu hiệu cho
// nó. Một giao diện vỡ vì dữ liệu hợp lệ là lỗi của giao diện.

/** Nhóm ý nghĩa, quyết định cách nhấn mạnh nhãn trên màn hình. */
export type NhomTrangThai =
  /** Hồ sơ đang chạy, người gửi không phải làm gì. */
  | "dang-chay"
  /** Hồ sơ dừng lại chờ chính người gửi — nhãn tô nền đậm để bật lên khỏi danh sách. */
  | "cho-ban"
  /** Có can thiệp ngoài luồng thường: phòng ban trả lại, hoặc hệ thống leo thang. */
  | "can-thiep"
  /** Hồ sơ đã kết thúc. */
  | "ket-thuc";

export type KieuTrinhBayTrangThai = {
  /** Dấu hiệu đặt trước nhãn. Phải đọc được một mình khi không có màu. */
  dau: string;
  /** Họ màu, ứng với bộ biến --f-<ho>-* trong globals.css. */
  ho: string;
  nhom: NhomTrangThai;
  /**
   * Đồng hồ hạn xử lý đứng ở trạng thái này để chờ gì, nếu có — chỉ để chọn câu chữ.
   *
   *   cho-tra-loi   — chờ người gửi bổ sung thông tin; việc còn dở, nên nói "còn …"
   *   cho-xac-nhan  — việc đã xong, chờ người gửi xác nhận kết quả; nói "đã xong"
   *
   * Thiếu thì dùng câu chung "Tạm dừng đếm hạn". Đồng hồ có dừng hay không vẫn do cờ
   * `sla_paused` của dịch vụ quyết, không phải bảng này (#97).
   */
  khiDung?: "cho-tra-loi" | "cho-xac-nhan";
};

const PHUONG_AN_LUI: KieuTrinhBayTrangThai = {
  dau: "◇",
  ho: "x",
  nhom: "dang-chay",
};

/**
 * Bảng tra dấu hiệu theo mã trạng thái.
 *
 * Mười dòng dưới đây khớp với bộ quy tắc mẫu trong `infra/seed/`. Doanh nghiệp khai
 * bộ quy tắc khác chỉ cần thêm dòng vào đây; thiếu dòng thì trạng thái vẫn hiện ra,
 * chỉ là mang dấu hiệu chung của phương án lùi.
 */
const BANG: Record<string, KieuTrinhBayTrangThai> = {
  submitted: { dau: "○", ho: "n", nhom: "dang-chay" },
  classified: { dau: "◐", ho: "p", nhom: "dang-chay" },
  "awaiting-acceptance": { dau: "◌", ho: "b", nhom: "dang-chay" },
  "in-progress": { dau: "●", ho: "t", nhom: "dang-chay" },
  "awaiting-info": { dau: "!", ho: "a", nhom: "cho-ban", khiDung: "cho-tra-loi" },
  completed: { dau: "✓", ho: "g", nhom: "cho-ban", khiDung: "cho-xac-nhan" },
  "rejected-by-department": { dau: "✕", ho: "r", nhom: "can-thiep" },
  escalated: { dau: "▲", ho: "o", nhom: "can-thiep" },
  closed: { dau: "■", ho: "x", nhom: "ket-thuc" },
  cancelled: { dau: "–", ho: "x", nhom: "ket-thuc" },
};

export function trinhBayTrangThai(ma: string): KieuTrinhBayTrangThai {
  return BANG[ma] ?? PHUONG_AN_LUI;
}

/** Hồ sơ đang đứng chờ chính người gửi hành động. */
export function dangChoNguoiDung(ma: string): boolean {
  return trinhBayTrangThai(ma).nhom === "cho-ban";
}

/**
 * Biến CSS của một họ màu, truyền vào thuộc tính `style` của nhãn.
 *
 * Nhờ cách này, `globals.css` không cần biết trạng thái nào mang màu nào — nó chỉ đọc
 * `--ho-bg`, `--ho-ink`, `--ho-line`, `--ho-solid`, `--ho-on` và không quan tâm giá
 * trị từ đâu tới.
 */
export function bienHoMau(ho: string): React.CSSProperties {
  return {
    "--ho-bg": `var(--f-${ho}-bg)`,
    "--ho-ink": `var(--f-${ho}-ink)`,
    "--ho-line": `var(--f-${ho}-line)`,
    "--ho-solid": `var(--f-${ho}-solid)`,
    "--ho-on": `var(--f-${ho}-on)`,
  } as React.CSSProperties;
}

/** Chú giải bốn nhóm, dùng cho bảng chú thích ở màn “Hồ sơ của tôi”. */
export const CHU_GIAI_NHOM: {
  nhom: NhomTrangThai;
  tieuDe: string;
  moTa: string;
}[] = [
  {
    nhom: "dang-chay",
    tieuDe: "Đang chạy bình thường",
    // Hệ thống chưa có kênh thông báo nào (#143), nên không hứa "sẽ có thông báo" (#151)
    moTa: "Hồ sơ đang đi trong quy trình. Bạn không cần làm gì; mở lại trang này để xem trạng thái mới nhất.",
  },
  {
    nhom: "cho-ban",
    tieuDe: "Đang chờ bạn",
    moTa: "Hồ sơ dừng lại cho tới khi bạn trả lời hoặc xác nhận. Không ai đi tiếp thay bạn được.",
  },
  {
    nhom: "can-thiep",
    tieuDe: "Có can thiệp",
    // Một câu dùng chung cho cả "Bị phòng ban từ chối" lẫn "Đã leo thang", nên không nêu
    // tên vai trò nào đang giữ hồ sơ: ở hai trạng thái đó người giữ khác nhau, và ai giữ
    // là chuyện của bộ quy tắc, không viết cứng ở đây (#151)
    moTa: "Phòng ban trả hồ sơ về để chọn lại phòng phụ trách, hoặc hồ sơ đã quá hạn nên được đẩy lên cấp trên. Hồ sơ vẫn đang được xử lý, bạn chưa cần làm gì.",
  },
  {
    nhom: "ket-thuc",
    tieuDe: "Đã kết thúc",
    moTa: "Hồ sơ đã đóng hoặc đã hủy. Không còn thao tác nào đi tiếp được.",
  },
];
