// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Định dạng thời gian cho người đọc Việt Nam.
//
// MÚI GIỜ LÀ ĐIỂM DỄ SAI NHẤT Ở ĐÂY. Dịch vụ ứng dụng lưu và trả mọi mốc thời gian
// theo UTC — bắt buộc, vì khai phá quy trình so sánh mốc giữa các bản ghi và một
// nhật ký trộn nhiều múi giờ thì vô nghĩa (CLAUDE.md mục 4.1).
//
// Nhưng ảnh chứa chạy theo giờ UTC, còn người dùng đọc theo giờ Việt Nam. Nếu gọi
// `toLocaleString()` mà không nêu múi giờ, máy chủ Next.js sẽ kết xuất ra giờ UTC và
// người dùng thấy mọi mốc lệch bảy tiếng — một lỗi âm thầm, vì nó chỉ lộ ra khi có
// người đối chiếu với đồng hồ thật.
//
// Vì vậy mọi hàm dưới đây nêu múi giờ tường minh. Đừng bỏ tham số đó đi.

const MUI_GIO = "Asia/Ho_Chi_Minh";
const DIA_PHUONG = "vi-VN";

// Ngày tháng ghép tay từ từng phần thay vì để `Intl` tự xếp.
//
// Lý do: cách xếp của địa phương `vi-VN` đổi giữa các phiên bản thư viện ICU — bản
// trong ảnh chứa Node hiện tại cho ra `08:29 17-09`, tức là giờ đứng trước ngày và
// dấu phân cách là gạch ngang. Trong một bảng danh sách thì cột ngày phải đọc được
// theo đúng một lối, và `17/09 08:29` là lối người Việt quen. Ghép tay thì con số
// không đổi chỗ khi ai đó nâng cấp ảnh nền.
const NGAY_THANG = new Intl.DateTimeFormat(DIA_PHUONG, {
  timeZone: MUI_GIO,
  day: "2-digit",
  month: "2-digit",
});

function phan(dinh_dang: Intl.DateTimeFormat, d: Date, loai: string): string {
  return dinh_dang.formatToParts(d).find((p) => p.type === loai)?.value ?? "";
}

const CHI_GIO = new Intl.DateTimeFormat(DIA_PHUONG, {
  timeZone: MUI_GIO,
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const NGAY_DAY_DU = new Intl.DateTimeFormat(DIA_PHUONG, {
  timeZone: MUI_GIO,
  weekday: "long",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

/** Khóa gộp theo ngày, ví dụ `2026-09-14`. Tính theo giờ Việt Nam, không theo UTC. */
const KHOA_NGAY = new Intl.DateTimeFormat("en-CA", {
  timeZone: MUI_GIO,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/** `14/09 08:52` */
/** Dung lượng tệp cho người đọc: 842 B, 1,4 MB. */
export function dungLuong(byte: number): string {
  if (byte < 1024) return `${byte} B`;
  if (byte < 1024 * 1024) return `${(byte / 1024).toFixed(0)} KB`;
  return `${(byte / (1024 * 1024)).toFixed(1).replace(".", ",")} MB`;
}

export function ngayGio(iso: string): string {
  const d = new Date(iso);
  const ngay = phan(NGAY_THANG, d, "day");
  const thang = phan(NGAY_THANG, d, "month");
  return `${ngay}/${thang} ${CHI_GIO.format(d)}`;
}

/** `08:52` */
export function chiGio(iso: string): string {
  return CHI_GIO.format(new Date(iso));
}

/** `Thứ Hai, 14/09/2026` */
export function ngayDayDu(iso: string): string {
  const d = new Date(iso);
  const thu = phan(NGAY_DAY_DU, d, "weekday");
  const ngay = phan(NGAY_DAY_DU, d, "day");
  const thang = phan(NGAY_DAY_DU, d, "month");
  const nam = phan(NGAY_DAY_DU, d, "year");
  return `${thu}, ${ngay}/${thang}/${nam}`;
}

export function khoaNgay(iso: string): string {
  return KHOA_NGAY.format(new Date(iso));
}

/**
 * Nhãn ngày cho dải phân cách trong dòng thời gian, có nhận ra hôm nay và hôm qua.
 *
 * `bayGio` truyền vào thay vì gọi `Date.now()` bên trong, để người gọi kết xuất cả
 * trang bằng đúng một mốc hiện tại. Nếu mỗi dòng tự lấy giờ riêng thì một trang kết
 * xuất đúng lúc nửa đêm sẽ có dòng ghi "hôm nay" và dòng ghi "hôm qua" cho cùng một ngày.
 */
export function nhanNgay(iso: string, bayGio: Date): string {
  const cua = khoaNgay(iso);
  const homNay = khoaNgay(bayGio.toISOString());

  if (cua === homNay) return `Hôm nay · ${ngayDayDu(iso)}`;

  const homQua = new Date(bayGio.getTime() - 86_400_000);
  if (cua === khoaNgay(homQua.toISOString())) return `Hôm qua · ${ngayDayDu(iso)}`;

  return ngayDayDu(iso);
}

/**
 * Khoảng cách tới hiện tại, nói theo lối người ta hay nói: `hôm nay`, `3 ngày`.
 *
 * Không dùng `Intl.RelativeTimeFormat` vì nó sinh ra "3 ngày trước", mà trong bảng
 * danh sách thì cột đã có tiêu đề "Đã gửi" nên chữ "trước" thành thừa.
 */
export function khoangCach(iso: string, bayGio: Date): string {
  const giay = Math.max(0, (bayGio.getTime() - new Date(iso).getTime()) / 1000);

  if (giay < 3600) return "vừa xong";
  if (khoaNgay(iso) === khoaNgay(bayGio.toISOString())) return "hôm nay";

  const ngay = Math.floor(giay / 86_400);
  if (ngay < 1) return "hôm qua";
  if (ngay < 30) return `${ngay} ngày`;

  const thang = Math.floor(ngay / 30);
  return `${thang} tháng`;
}

/**
 * Một khoảng thời lượng nói bằng đơn vị lớn nhất có nghĩa: `2 ngày 11 giờ`.
 *
 * Cắt ở hai đơn vị. "2 ngày 11 giờ 3 phút 8 giây" đúng hơn nhưng không ai đọc tới
 * cuối, và độ chính xác thừa làm con số khó so sánh giữa các dòng.
 */
export function thoiLuong(giay: number): string {
  if (giay < 60) return "chưa tới một phút";

  const phut = Math.floor(giay / 60);
  if (phut < 60) return `${phut} phút`;

  const gio = Math.floor(phut / 60);
  if (gio < 24) {
    const le = phut % 60;
    return le > 0 ? `${gio} giờ ${le} phút` : `${gio} giờ`;
  }

  const ngay = Math.floor(gio / 24);
  const le = gio % 24;
  return le > 0 ? `${ngay} ngày ${le} giờ` : `${ngay} ngày`;
}

/**
 * Thời lượng tính bằng GIỜ LÀM VIỆC (#199): `12 giờ 30 phút làm việc`.
 *
 * Mọi con số của đồng hồ SLA đếm giờ làm việc theo lịch trong dữ liệu, nên không quy ra
 * ngày như `thoiLuong`: một ngày làm việc dài bao nhiêu giờ là chuyện của lịch, không phải
 * 24 giờ — "1 ngày" ở đây sẽ đọc thành một ngày lịch và sai gấp ba.
 */
export function thoiLuongLamViec(giay: number): string {
  if (giay < 60) return "chưa tới một phút làm việc";

  const phut = Math.floor(giay / 60);
  if (phut < 60) return `${phut} phút làm việc`;

  const gio = Math.floor(phut / 60);
  const le = phut % 60;
  return le > 0 ? `${gio} giờ ${le} phút làm việc` : `${gio} giờ làm việc`;
}

/** `23/11/2026 14:05` — mốc có năm, cho nhật ký kiểm toán (#431): dòng cũ phải đọc ra được năm nào. */
export function ngayGioCoNam(iso: string): string {
  const d = new Date(iso);
  const ngay = phan(NGAY_DAY_DU, d, "day");
  const thang = phan(NGAY_DAY_DU, d, "month");
  const nam = phan(NGAY_DAY_DU, d, "year");
  return `${ngay}/${thang}/${nam} ${CHI_GIO.format(d)}`;
}

const PHAN_GIO_DAY_DU = new Intl.DateTimeFormat("en-US", {
  timeZone: MUI_GIO,
  hourCycle: "h23",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

/**
 * Mốc UTC (ISO 8601) của 00:00 ngày `YYYY-MM-DD` theo giờ Việt Nam — để lọc theo ngày người dùng chọn mà
 * dịch vụ so trên mốc UTC (#431). Chuỗi không đúng dạng ngày thì `null`. `cong` cộng thêm chừng ấy ngày:
 * "đến hết ngày X" là "trước 00:00 ngày X + 1".
 */
export function dauNgayUtc(ngay: string, cong = 0): string | null {
  const khop = /^(\d{4})-(\d{2})-(\d{2})$/.exec(ngay);
  if (!khop) return null;
  const goc = Date.UTC(Number(khop[1]), Number(khop[2]) - 1, Number(khop[3]) + cong);
  if (Number.isNaN(goc)) return null;
  // Độ lệch của múi giờ ở mốc đó: giờ địa phương của `goc` đọc như thể UTC, trừ đi chính `goc`
  const p = Object.fromEntries(PHAN_GIO_DAY_DU.formatToParts(new Date(goc)).map((x) => [x.type, x.value]));
  const diaPhuong = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second);
  return new Date(goc - (diaPhuong - goc)).toISOString();
}

/** Hạn chót: `15:00 Thứ Hai 19/10` (#199). */
export function hanLuc(iso: string): string {
  const d = new Date(iso);
  const thu = phan(NGAY_DAY_DU, d, "weekday");
  const ngay = phan(NGAY_DAY_DU, d, "day");
  const thang = phan(NGAY_DAY_DU, d, "month");
  return `${CHI_GIO.format(d)} ${thu} ${ngay}/${thang}`;
}

/**
 * Nhãn nút xác nhận một bước: "Xác nhận · Chuyển về phòng ban". Nhãn cạnh lấy từ dữ liệu; nhãn nào đã mở đầu
 * bằng "Xác nhận" ("Xác nhận đạt") thì thành "Gửi xác nhận đạt" — nút không lặp chữ "Xác nhận · Xác nhận đạt"
 * (#540), mà cũng không trùng tên với nút mở bước đó đang đứng ngay trên (#540).
 */
export function nhanNutXacNhan(nhanCanh: string): string {
  const nhan = nhanCanh.normalize("NFC");
  return nhan.toLocaleLowerCase(DIA_PHUONG).startsWith("xác nhận")
    ? `Gửi ${nhan.charAt(0).toLocaleLowerCase(DIA_PHUONG)}${nhan.slice(1)}`
    : `Xác nhận · ${nhanCanh}`;
}
