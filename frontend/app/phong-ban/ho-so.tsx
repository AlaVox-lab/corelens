// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Phần dùng chung của một hồ sơ trong buồng lái phòng ban: nạp dữ liệu, hàng thông tin dưới
// tiêu đề, khối thao tác. Trang chi tiết (`[id]/page.tsx`) và ngăn xem nhanh của hàng đợi (#233)
// cùng gọi các hàm này.
//
// Khối thao tác KHÔNG đoán trước ô nào sẽ hiện. Nó đọc `fields` của các thao tác đang đi được,
// rồi nạp đúng những danh mục mà các ô đó cần. Cạnh *Phân công lại* mang ràng buộc "không
// được đổi phòng ban", nên nó có cả ô phòng ban — bản đầu của trang chỉ nạp danh sách
// người, và ô phòng ban rơi về một ô gõ chữ trống. Nạp theo `fields` thì trường nào
// dịch vụ cho hiện cũng có danh mục, kể cả trường sau này mới thêm vào một cạnh.
//
// Nhờ vậy danh sách người xử lý chỉ được tra khi có ít nhất một thao tác cho giao người.
// Người xử lý mở hồ sơ thì không có thao tác nào như vậy, và Keycloak không bị hỏi tới —
// danh bạ chỉ nằm trên đường đi của đúng cái ô cần nó (#84).

import { Building2, Flag, Tag, User } from "lucide-react";

import { chuyenTrangThaiPhongBan } from "@/app/phong-ban/thao-tac";
import { BangThaoTac, type NguonLuaChon } from "@/components/bang-thao-tac";
import type { MucMeta } from "@/components/trang-ho-so";
import { docDichVu, goiDichVu, type KetQua } from "@/lib/api";
import type {
  GoiY,
  HoSoPhongBan,
  LienHeNguoiGui,
  NhanCoMa,
  NguoiNhanViecTrongPhong,
  TrangThai,
} from "@/lib/kieu";
import { kieuTruong, type NguonDanhMuc } from "@/lib/truong";

export type DuLieuPhongBan = {
  ho_so: HoSoPhongBan;
  danhMuc: Partial<Record<NguonDanhMuc, NguonLuaChon>>;
  /**
   * Gợi ý người xử lý (#318), tính lại lúc nạp ô chọn người — cùng lần gọi danh bạ. Danh bạ không
   * trả lời thì lùi về gợi ý đã lưu trên hồ sơ; không có thì ô chọn tay như trước.
   */
  goiYNguoi: GoiY | null;
  /** Liên hệ người gửi đi điểm cuối riêng (#131): danh bạ hỏng thì chỉ thẻ đó báo lỗi. */
  lienHe: KetQua<LienHeNguoiGui>;
  cacTrangThai: TrangThai[] | null;
};

type KetQuaNguon = { luaChon: NguonLuaChon; goiY?: GoiY | null };

async function napNguon(nguon: NguonDanhMuc, ho_so: HoSoPhongBan): Promise<KetQuaNguon> {
  if (nguon === "assignees") {
    if (!ho_so.department) {
      return { luaChon: { loi: "Hồ sơ chưa thuộc phòng nào nên chưa giao được người." } };
    }
    // Gửi kèm mã hồ sơ: dịch vụ tính lại gợi ý trên đúng danh sách vừa tra (#318)
    const ketQua = await docDichVu<NguoiNhanViecTrongPhong>(
      `/departments/${encodeURIComponent(ho_so.department.code)}/assignees?case_id=${ho_so.id}`,
    );
    if (!ketQua.ok) {
      return {
        luaChon: {
          loi: `${ketQua.thongDiep} Vẫn nhận được hồ sơ mà chưa giao cho ai — cả phòng cùng thấy hồ sơ này.`,
        },
      };
    }
    return {
      luaChon: ketQua.duLieu.people.map((p) => ({ code: p.id, label: p.name })),
      goiY: ketQua.duLieu.suggestion ?? null,
    };
  }

  // Ba danh mục còn lại mang đúng tên điểm cuối của chúng
  const ds = await goiDichVu<NhanCoMa[]>(`/${nguon}`);
  return {
    luaChon: ds ? ds.map(({ code, label }) => ({ code, label })) : { loi: "Không nạp được danh mục." },
  };
}

/** Nạp đúng những danh mục mà các thao tác đang đi được cần tới — không hơn. */
async function danhMucCan(
  ho_so: HoSoPhongBan,
): Promise<{ danhMuc: Partial<Record<NguonDanhMuc, NguonLuaChon>>; goiYNguoi: GoiY | null }> {
  const can = new Set<NguonDanhMuc>();
  for (const canh of ho_so.allowed_transitions) {
    for (const truong of canh.fields) {
      const nguon = kieuTruong(truong).nguon;
      if (nguon) can.add(nguon);
    }
  }
  const cap = await Promise.all(
    [...can].map(async (nguon) => [nguon, await napNguon(nguon, ho_so)] as const),
  );
  const nguoi = cap.find(([nguon]) => nguon === "assignees")?.[1];
  return {
    danhMuc: Object.fromEntries(cap.map(([nguon, kq]) => [nguon, kq.luaChon])),
    // Danh bạ hỏng thì không có danh sách để chọn, nên cũng không có gợi ý để điền
    goiYNguoi: nguoi && Array.isArray(nguoi.luaChon) ? (nguoi.goiY ?? ho_so.suggested_assignee ?? null) : null,
  };
}

/** Hồ sơ trước — danh mục cần nạp phụ thuộc thao tác của nó — rồi phần còn lại song song. */
export async function napHoSoPhongBan(id: string): Promise<KetQua<DuLieuPhongBan>> {
  const ketQua = await docDichVu<HoSoPhongBan>(`/department/requests/${id}`);
  if (!ketQua.ok) return ketQua;
  const ho_so = ketQua.duLieu;
  const [{ danhMuc, goiYNguoi }, lienHe, cacTrangThai] = await Promise.all([
    danhMucCan(ho_so),
    docDichVu<LienHeNguoiGui>(`/department/requests/${id}/requester-contact`),
    goiDichVu<TrangThai[]>("/states"),
  ]);
  return { ok: true, duLieu: { ho_so, danhMuc, goiYNguoi, lienHe, cacTrangThai } };
}

export function metaPhongBan(ho_so: HoSoPhongBan): MucMeta[] {
  const nguoiXuLy = ho_so.assigned_to_me
    ? "Bạn"
    : ho_so.assignee_id
      ? (ho_so.assignee_label ?? "Một người trong phòng")
      : "chưa giao cho ai";
  return [
    { icon: <Tag aria-hidden />, chu: ho_so.request_type?.label ?? "Chưa rõ loại" },
    { icon: <Building2 aria-hidden />, chu: ho_so.department?.label ?? "Chưa thuộc phòng nào" },
    {
      icon: <Flag aria-hidden />,
      chu: ho_so.priority ? `Ưu tiên ${ho_so.priority.label}` : "Chưa đặt mức ưu tiên",
    },
    { icon: <User aria-hidden />, chu: `Người xử lý: ${nguoiXuLy}` },
  ];
}

/**
 * Bảng thao tác của phòng ban. `ngan` có mặt khi khối nằm ở đáy ngăn xem nhanh: bước chính
 * thành nút chính, thao tác khác vào menu, xong thì sang `sauKhiXong`.
 */
export function ThaoTacPhongBan({ d, ngan }: { d: DuLieuPhongBan; ngan?: { sauKhiXong: string } }) {
  const { ho_so, danhMuc, goiYNguoi } = d;
  return (
    // Khóa có `updated_at`: nhận việc giữ nguyên trạng thái (#127), nên chỉ mã
    // trạng thái thì bảng không dựng lại sau khi nhận.
    <BangThaoTac
      key={`${ho_so.id}-${ho_so.state.code}-${ho_so.updated_at}`}
      maHoSo={ho_so.id}
      cacCanh={ho_so.allowed_transitions}
      // Giá trị hồ sơ đang có, cho cả bốn trường quyết định. Ô phòng ban ở
      // cạnh phân công lại vì thế hiện đúng phòng đang giữ hồ sơ.
      giaTriDau={{
        request_type_code: ho_so.request_type?.code ?? "",
        priority_code: ho_so.priority?.code ?? "",
        department_code: ho_so.department?.code ?? "",
        // Chưa giao ai thì điền sẵn người được gợi ý (#318); đã có người thì ô giữ người đó, thẻ
        // gợi ý nằm trên ô và nói khi hai bên khác nhau
        assignee_id: ho_so.assignee_id ?? goiYNguoi?.code ?? "",
      }}
      goiY={goiYNguoi ? { assignee_id: goiYNguoi } : {}}
      danhMuc={danhMuc}
      hanhDong={chuyenTrangThaiPhongBan}
      khiHet={{
        cau: "Không có thao tác nào dành cho bạn ở trạng thái này.",
        veHangDoi: "/phong-ban",
      }}
      ngan={ngan}
    />
  );
}
