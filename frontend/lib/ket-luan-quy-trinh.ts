// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Câu kết luận của màn quy trình thực tế (#315): dựng từ các con số của dịch vụ khai phá bằng mẫu
// câu tiếng Việt TẤT ĐỊNH — cùng một JSON luôn ra cùng những câu, từng chữ. Không mô hình ngôn ngữ,
// không số ngẫu nhiên, không đọc đồng hồ: người xem tin được câu vì kiểm lại được từng con số trong
// sơ đồ và các khối bên dưới.
//
// Hàm thuần, không đụng React hay trình duyệt, để đọc và thử một mình.
//
// Tên trạng thái, loại yêu cầu và phòng ban đều lấy từ JSON (`states[].label`, `labels.*`) — tệp này
// không biết trạng thái nào. Ngoại lệ duy nhất là bảng nhãn năm nhánh lệch bên dưới: đó là năm loại
// phân tích do dịch vụ khai phá định nghĩa (hợp đồng ở ARCHITECTURE.md mục 6.4), không phải cấu hình
// nghiệp vụ của doanh nghiệp. Mã lạ thì hiện nguyên mã.

import { thoiLuongLamViec } from "@/lib/dinh-dang";
import { ngayVietNam } from "@/lib/khoang-ngay";
import type { QuyTrinhThucTe } from "@/lib/kieu";

/** Nhãn của năm nhánh lệch: `ten` cho danh sách và chú giải, `cum` để nối vào câu "hồ sơ …". */
export const NHAN_NHANH_LECH: Record<string, { ten: string; cum: string }> = {
  rework: { ten: "Trả về làm lại", cum: "bị trả về làm lại" },
  escalation: { ten: "Leo thang do quá hạn", cum: "bị leo thang vì quá hạn xử lý" },
  wait_expiry: { ten: "Tự chuyển khi hết hạn chờ", cum: "bị hệ thống tự chuyển khi hết hạn chờ" },
  reopen: { ten: "Mở lại sau khi kết thúc", cum: "được mở lại sau khi kết thúc" },
  multiple_routing: { ten: "Chuyển phòng nhiều lần", cum: "bị chuyển phòng từ hai lần trở lên" },
};

export function tenNhanhLech(loai: string): string {
  return NHAN_NHANH_LECH[loai]?.ten ?? loai;
}

/** Tên loại cạnh của sơ đồ: luồng chính, hay một trong các nhánh lệch. */
export function tenLoaiCanh(loai: string): string {
  return loai === "main" ? "Luồng chính" : tenNhanhLech(loai);
}

// ---------------------------------------------------------------------------
// Số theo kiểu Việt Nam
// ---------------------------------------------------------------------------

/** Số nguyên, dấu chấm ngăn nghìn: `1234` → `1.234`. Ghép tay để không lệ thuộc bản ICU. */
export function soVN(so: number): string {
  return Math.round(so)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

/** Số có phần thập phân dấu phẩy, bỏ ",0" thừa: `3.4` → `3,4`, `2` → `2`. */
export function soThapPhan(so: number): string {
  const lam = Math.round(so * 10) / 10;
  const [nguyen, le] = lam.toFixed(1).split(".");
  const dau = soVN(Number(nguyen));
  return le === "0" ? dau : `${dau},${le}`;
}

/** Tỷ lệ (0–1) thành phần trăm có dấu cách trước ký hiệu: `0.18` → `18 %`, `0.042` → `4,2 %`. */
export function phanTram(tyLe: number): string {
  const p = tyLe * 100;
  if (p <= 0) return "0 %";
  if (p < 0.05) return "dưới 0,1 %";
  return `${p >= 10 ? Math.round(p).toString() : soThapPhan(p)} %`;
}

/** Thời gian chờ không kèm "làm việc", cho chỗ hẹp như nút trên sơ đồ: `9 giờ 5 phút`. */
export function thoiGianNgan(giay: number): string {
  return thoiLuongLamViec(giay).replace(/ làm việc$/, "");
}

// ---------------------------------------------------------------------------
// Tra nhãn
// ---------------------------------------------------------------------------

export function nhanTrangThai(duLieu: QuyTrinhThucTe, ma: string): string {
  const coLuot = duLieu.states.find((t) => t.code === ma)?.label;
  if (coLuot) return coLuot;
  // Trạng thái chưa hồ sơ nào vào chỉ có mặt ở luồng thiết kế, kèm nhãn của bộ quy tắc
  for (const c of duLieu.designed_main_flow) {
    if (c.from === ma) return c.from_label;
    if (c.to === ma) return c.to_label;
  }
  return ma;
}

/** Mã hiển thị của hồ sơ (`YC-2026-0184`), như trang hồ sơ; thiếu thì số định danh. */
export function maHienThi(duLieu: QuyTrinhThucTe, ma: number): string {
  return duLieu.case_codes[String(ma)] ?? `#${ma}`;
}

/** Nhãn loại yêu cầu; mã rỗng không xảy ra với hồ sơ đã gửi nhưng vẫn không được làm hỏng câu. */
export function nhanLoaiYeuCau(duLieu: QuyTrinhThucTe, ma: string | null): string {
  if (ma === null) return "chưa rõ loại";
  return duLieu.labels.request_types[ma] ?? ma;
}

/** Nhãn phòng ban; mã rỗng là hồ sơ chưa được chuyển về phòng nào. */
export function nhanPhong(duLieu: QuyTrinhThucTe, ma: string | null): string {
  if (ma === null) return "chưa chuyển phòng";
  return duLieu.labels.departments[ma] ?? ma;
}

/** "phòng X", hay "nhóm chưa chuyển phòng" cho mã rỗng — để nối vào câu sau "ở". */
function diaDiem(duLieu: QuyTrinhThucTe, ma: string | null): string {
  return ma === null ? "nhóm chưa chuyển phòng" : `phòng ${nhanPhong(duLieu, ma)}`;
}

/** Có đủ phòng để so sánh giữa các phòng: phạm vi toàn công ty và từ hai phòng có hồ sơ. */
export function coNhieuPhong(duLieu: QuyTrinhThucTe): boolean {
  return duLieu.scope.all && duLieu.groups.departments.length >= 2;
}

/** Phạm vi người xem, viết liền vào câu: "toàn công ty", "phòng Kế toán", "các phòng A, B". */
export function chuPhamVi(duLieu: QuyTrinhThucTe): string {
  const { all, departments } = duLieu.scope;
  if (all) return "toàn công ty";
  const ten = departments.map((p) => p.label);
  if (ten.length === 0) return "phạm vi của bạn";
  return ten.length === 1 ? `phòng ${ten[0]}` : `các phòng ${ten.join(", ")}`;
}

// ---------------------------------------------------------------------------
// Câu kết luận
// ---------------------------------------------------------------------------

export type CauKetLuan = { id: string; chu: string };

/** Số lần dạng "gấp 3,4 lần": một chữ số thập phân khi dưới 10, số nguyên từ 10. */
function soLan(so: number): string {
  return so >= 10 ? soVN(so) : soThapPhan(so);
}

function cauTongQuan(d: QuyTrinhThucTe): CauKetLuan {
  const khoang = `Từ ${ngayVietNam(d.range.from)} đến ${ngayVietNam(d.range.to)}`;
  const chu =
    d.cases_count === 0
      ? `${khoang}, ${chuPhamVi(d)} không có hồ sơ nào được gửi.`
      : `${khoang}, ${chuPhamVi(d)} có ${soVN(d.cases_count)} hồ sơ được gửi.`;
  return { id: "tong-quan", chu };
}

/** Nối danh sách tên kiểu câu tiếng Việt: "A", "A và B", "A, B và C". */
function noiVa(ds: string[]): string {
  return ds.length < 2 ? (ds[0] ?? "") : `${ds.slice(0, -1).join(", ")} và ${ds[ds.length - 1]}`;
}

function cauDiemNghen(d: QuyTrinhThucTe): CauKetLuan[] {
  const { overall_median_wait_seconds: chung, factor, ranking } = d.bottlenecks;
  if (chung === null) {
    return [{ id: "diem-nghen", chu: "Chưa đủ dữ liệu thời gian chờ để xác định điểm nghẽn." }];
  }
  // Bảng xếp hạng đã xếp theo thời gian chờ giảm dần: trạng thái nghẽn đầu tiên là nghẽn nhất
  const nghen = ranking.filter((r) => r.is_bottleneck);
  if (nghen.length === 0) {
    return [
      {
        id: "diem-nghen",
        chu: `Không trạng thái nào chờ gấp từ ${soThapPhan(factor)} lần mức chung (${thoiLuongLamViec(chung)}).`,
      },
    ];
  }
  const dau = nghen[0];
  let chu =
    `Điểm nghẽn rõ nhất là “${dau.label}”: hồ sơ chờ ở đó trung vị ${thoiLuongLamViec(dau.median_wait_seconds)}, ` +
    `gấp ${soLan(dau.median_wait_seconds / chung)} lần mức chung (${thoiLuongLamViec(chung)}).`;
  const tt = d.states.find((t) => t.code === dau.code);
  if (tt) {
    // Nhóm chậm nhất: theo phòng khi so sánh được giữa các phòng, không thì theo loại yêu cầu
    if (coNhieuPhong(d) && tt.by_department.length > 0) {
      const n = tt.by_department[0];
      chu += ` Chậm nhất ở ${diaDiem(d, n.code)} (trung vị ${thoiLuongLamViec(n.median_wait_seconds)}).`;
    } else if (tt.by_request_type.length > 0) {
      const n = tt.by_request_type[0];
      chu += ` Chậm nhất ở loại ${nhanLoaiYeuCau(d, n.code)} (trung vị ${thoiLuongLamViec(n.median_wait_seconds)}).`;
    }
  }
  const cau: CauKetLuan[] = [{ id: "diem-nghen", chu }];
  if (nghen.length > 1) {
    const con = nghen.slice(1).map((r) => `“${r.label}”`);
    cau.push({
      id: "diem-nghen-khac",
      chu: `${noiVa(con)} cũng là điểm nghẽn.`,
    });
  }
  return cau;
}

function cauNhanhLech(d: QuyTrinhThucTe): CauKetLuan[] {
  // Nhánh nhiều hồ sơ nhất nói trước; bằng nhau thì giữ thứ tự dịch vụ trả
  const co = d.deviations
    .map((n, i) => ({ n, i }))
    .filter(({ n }) => n.cases_count > 0)
    .sort((a, b) => b.n.ratio - a.n.ratio || a.i - b.i)
    .map(({ n }) => n);
  if (co.length === 0) {
    return d.cases_count > 0
      ? [{ id: "nhanh-lech-khong", chu: "Không có hồ sơ nào đi ra ngoài luồng chính." }]
      : [];
  }
  const nhieuPhong = coNhieuPhong(d);
  return co.map((n) => {
    const cum = NHAN_NHANH_LECH[n.kind]?.cum ?? `đi theo nhánh lệch “${n.kind}”`;
    let chu = `${phanTram(n.ratio)} hồ sơ ${cum} (${soVN(n.cases_count)} hồ sơ)`;
    const loai = n.by_request_type[0];
    const phong = n.by_department[0];
    if (loai) {
      chu += `, nhiều nhất ở loại ${nhanLoaiYeuCau(d, loai.code)}`;
      if (nhieuPhong && phong) chu += ` và ở ${diaDiem(d, phong.code)}`;
    } else if (nhieuPhong && phong) {
      chu += `, nhiều nhất ở ${diaDiem(d, phong.code)}`;
    }
    return { id: `nhanh-lech-${n.kind}`, chu: `${chu}.` };
  });
}

/** Các cạnh của luồng thiết kế mà không hồ sơ nào đi qua, theo thứ tự của hợp đồng. */
export function canhThietKeChuaDi(d: QuyTrinhThucTe): { from: string; to: string }[] {
  const daDi = new Set(d.edges.map((e) => `${e.from}\u0000${e.to}`));
  return d.designed_main_flow.filter((c) => !daDi.has(`${c.from}\u0000${c.to}`));
}

function cauLuongThietKe(d: QuyTrinhThucTe): CauKetLuan[] {
  const chua = canhThietKeChuaDi(d);
  if (chua.length === 0) return [];
  const toiDa = 4;
  const buoc = chua
    .slice(0, toiDa)
    .map((c) => `“${nhanTrangThai(d, c.from)}” → “${nhanTrangThai(d, c.to)}”`);
  const them = chua.length > toiDa ? ` và ${chua.length - toiDa} bước khác` : "";
  return [
    {
      id: "luong-thiet-ke",
      chu: `Luồng thiết kế còn ${chua.length} bước chưa hồ sơ nào đi qua: ${buoc.join(", ")}${them}.`,
    },
  ];
}

/** Các câu kết luận, theo thứ tự: tổng quan, điểm nghẽn, từng nhánh lệch, bước thiết kế chưa ai đi. */
export function ketLuanQuyTrinh(d: QuyTrinhThucTe): CauKetLuan[] {
  if (d.cases_count === 0) return [cauTongQuan(d)];
  return [cauTongQuan(d), ...cauDiemNghen(d), ...cauNhanhLech(d), ...cauLuongThietKe(d)];
}
