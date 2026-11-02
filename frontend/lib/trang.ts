// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Phân trang và bộ lọc nằm trên địa chỉ trang (#232): `?trang=`, `?q=`, `?xep=` cùng các bộ lọc
// của từng màn. Tải lại, bấm lùi hay gửi đường dẫn đều giữ nguyên trang và bộ lọc đang xem.
// Dịch vụ lọc, đếm và cắt trang; giao diện chỉ đọc địa chỉ, dựng chuỗi truy vấn và liên kết.

/** Số dòng một trang — cùng mặc định với dịch vụ (`phan_trang.GIOI_HAN_MAC_DINH`). */
export const SO_DONG = 50;

export type ThamSo = Record<string, string | string[] | undefined>;

/** Giá trị đầu của một tham số trên địa chỉ trang. */
export function docThamSo(sp: ThamSo, ten: string): string | undefined {
  const gt = sp[ten];
  return (Array.isArray(gt) ? gt[0] : gt) || undefined;
}

/** Số trang đang xem, đếm từ 1; giá trị hỏng thì về trang đầu. */
export function soTrang(sp: ThamSo): number {
  const n = Number.parseInt(docThamSo(sp, "trang") ?? "", 10);
  return Number.isFinite(n) && n > 0 ? n : 1;
}

/**
 * Đường dẫn giữ mọi tham số đang có và đổi những tham số trong `doi` — giá trị rỗng là bỏ. Đổi
 * bộ lọc thì bỏ luôn `trang`: trang 5 của bộ lọc cũ không còn nghĩa gì với bộ lọc mới.
 */
export function duongVoi(goc: string, sp: ThamSo, doi: Record<string, string | null>, giuTrang = false): string {
  const q = new URLSearchParams();
  for (const ten of Object.keys(sp)) {
    const gt = docThamSo(sp, ten);
    if (gt) q.set(ten, gt);
  }
  if (!giuTrang) q.delete("trang");
  for (const [ten, gt] of Object.entries(doi)) {
    if (gt) q.set(ten, gt);
    else q.delete(ten);
  }
  const chuoi = q.toString();
  return chuoi ? `${goc}?${chuoi}` : goc;
}

/** Liên kết sang một trang khác của cùng danh sách; trang đầu thì bỏ hẳn `?trang=`. */
export function duongTrang(goc: string, sp: ThamSo, trang: number): string {
  return duongVoi(goc, sp, { trang: trang > 1 ? String(trang) : null }, true);
}

/**
 * Chip của các bộ lọc đang bật. `nhan` khai các tham số là bộ lọc và cách đọc giá trị thành chữ
 * — tra nhãn từ dữ liệu, không in mã. Trả kèm đường dẫn bỏ mọi bộ lọc (giữ cách xếp), hoặc `null`
 * khi không bộ lọc nào bật.
 */
export function chipLoc(
  goc: string,
  sp: ThamSo,
  nhan: Record<string, (gt: string) => string>,
): { chip: { nhan: string; bo: string }[]; xoaHet: string | null } {
  const chip = Object.entries(nhan).flatMap(([ten, doc]) => {
    const gt = docThamSo(sp, ten);
    return gt ? [{ nhan: doc(gt), bo: duongVoi(goc, sp, { [ten]: null }) }] : [];
  });
  const bo = Object.fromEntries(Object.keys(nhan).map((ten) => [ten, null]));
  return { chip, xoaHet: chip.length ? duongVoi(goc, sp, bo) : null };
}

/** Nhãn của một mã trong danh mục, hoặc chính mã khi danh mục không có. */
export function nhanCua(ds: { code: string; label: string }[] | null | undefined, ma: string): string {
  return ds?.find((o) => o.code === ma)?.label ?? ma;
}

/**
 * Cách xếp của hai hàng đợi (#231) — mã trùng tham số `sort` của dịch vụ. Hàng đợi phòng ban mặc
 * định độ gấp, hàng đợi điều phối mặc định chờ lâu nhất (đồng hồ chưa chạy ở đó).
 */
export const CACH_XEP_HANG = [
  { ma: "gap", ten: "Độ gấp", moTa: "Quá hạn → sắp hạn → chờ lâu nhất" },
  { ma: "cho", ten: "Chờ lâu nhất", moTa: "Hồ sơ nằm im lâu nhất lên trước" },
  { ma: "moi", ten: "Mới nhất", moTa: "Hồ sơ vừa tạo lên trước" },
] as const;
export type MaXepHang = (typeof CACH_XEP_HANG)[number]["ma"];
export const KHOA_XEP_HANG = "dxlab-xep-hang-doi";

/** Cách xếp đang chọn trên địa chỉ trang, hoặc mặc định của màn. */
export function docXep(sp: ThamSo, macDinh: MaXepHang): (typeof CACH_XEP_HANG)[number] {
  const ma = docThamSo(sp, "xep");
  return CACH_XEP_HANG.find((c) => c.ma === ma) ?? CACH_XEP_HANG.find((c) => c.ma === macDinh)!;
}

/**
 * Trang đang xem đã quá trang cuối — hồ sơ vừa được xử lý xong, hay đường dẫn cũ — thì đường dẫn
 * sang trang cuối; còn trong phạm vi thì `null`.
 */
export function quaTrangCuoi(
  goc: string,
  sp: ThamSo,
  ds: { items: unknown[]; total: number; limit: number },
): string | null {
  if (ds.items.length > 0 || ds.total === 0) return null;
  return duongTrang(goc, sp, Math.ceil(ds.total / ds.limit));
}

/**
 * Hồ sơ đang mở trong ngăn xem nhanh (#233) và đường đi của ngăn, từ `?xem=` và trang đang xem.
 *
 * `?xem=` là mã hồ sơ, hay `dau`/`cuoi` — hồ sơ đầu, cuối của trang: ở mép trang, nút trước/sau
 * sang trang kế mà chưa biết mã hồ sơ ở đó. Vị trí đếm trên cả danh sách đã lọc ("51 trên 230").
 * Hồ sơ không có trên trang — vừa xử lý xong nên rời danh sách, hay đường dẫn cũ — vẫn mở được,
 * chỉ không có vị trí và nút trước/sau.
 */
export function xemNhanh(
  goc: string,
  sp: ThamSo,
  trang: number,
  ds: { items: { id: number }[]; offset: number; total: number },
): {
  ma: number;
  viTri: { so: number; tong: number } | null;
  truoc: string | null;
  sau: string | null;
  dong: string;
  dayDu: string;
} | null {
  const xem = docThamSo(sp, "xem");
  const ids = ds.items.map((m) => m.id);
  const ma = xem === "dau" ? ids[0] : xem === "cuoi" ? ids.at(-1) : Number.parseInt(xem ?? "", 10);
  if (ma === undefined || !Number.isFinite(ma) || ma <= 0) return null;

  const i = ids.indexOf(ma);
  const toi = (id: number | string, trangMoi = trang) =>
    duongVoi(goc, sp, { xem: String(id), trang: trangMoi > 1 ? String(trangMoi) : null }, true);
  return {
    ma,
    viTri: i >= 0 ? { so: ds.offset + i + 1, tong: ds.total } : null,
    truoc: i > 0 ? toi(ids[i - 1]) : i === 0 && trang > 1 ? toi("cuoi", trang - 1) : null,
    sau:
      i >= 0 && i < ids.length - 1
        ? toi(ids[i + 1])
        : i >= 0 && ds.offset + ids.length < ds.total
          ? toi("dau", trang + 1)
          : null,
    dong: duongVoi(goc, sp, { xem: null }, true),
    dayDu: `${goc}/${ma}`,
  };
}

/** Đường mở một hồ sơ trong ngăn xem nhanh, giữ bộ lọc và trang đang xem. */
export function duongXem(goc: string, sp: ThamSo, ma: number): string {
  return duongVoi(goc, sp, { xem: String(ma) }, true);
}

/** Chuỗi truy vấn gửi dịch vụ: trang đang xem cộng các bộ lọc có giá trị. */
export function truyVan(trang: number, loc: Record<string, string | boolean | undefined>): string {
  const q = new URLSearchParams({ limit: String(SO_DONG), offset: String((trang - 1) * SO_DONG) });
  for (const [ten, gt] of Object.entries(loc)) {
    if (gt) q.set(ten, gt === true ? "true" : gt);
  }
  return q.toString();
}
