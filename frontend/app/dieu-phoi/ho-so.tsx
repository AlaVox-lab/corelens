// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Phần dùng chung của một hồ sơ trong buồng lái điều phối: nạp dữ liệu, hàng thông tin dưới
// tiêu đề, khối thao tác. Trang chi tiết (`[id]/page.tsx`) và ngăn xem nhanh của hàng đợi (#233)
// cùng gọi các hàm này — điền sẵn ô nhập, gợi ý phòng, câu khi không còn thao tác chỉ viết một
// nơi.

import { Building2, Flag, Tag } from "lucide-react";

import { chuyenTrangThaiDieuPhoi } from "@/app/dieu-phoi/thao-tac";
import { BangThaoTac } from "@/components/bang-thao-tac";
import type { MucMeta } from "@/components/trang-ho-so";
import { docDichVu, goiDichVu, type KetQua } from "@/lib/api";
import type {
  HoSoDieuPhoi,
  LienHeNguoiGui,
  LoaiYeuCau,
  MucUuTien,
  NhanCoMa,
  PhongBan,
  TrangThai,
} from "@/lib/kieu";

export type DuLieuDieuPhoi = {
  ho_so: HoSoDieuPhoi;
  cacLoai: LoaiYeuCau[] | null;
  cacMuc: MucUuTien[] | null;
  cacPhong: PhongBan[] | null;
  /** Liên hệ người gửi đi điểm cuối riêng (#131): danh bạ hỏng thì chỉ thẻ đó báo lỗi. */
  lienHe: KetQua<LienHeNguoiGui>;
  cacTrangThai: TrangThai[] | null;
};

/** Hồ sơ và mọi thứ khối thao tác cần, gọi song song. Lỗi của hồ sơ trả nguyên cho phía gọi. */
export async function napHoSoDieuPhoi(id: string): Promise<KetQua<DuLieuDieuPhoi>> {
  const [ketQua, cacLoai, cacMuc, cacPhong, lienHe, cacTrangThai] = await Promise.all([
    docDichVu<HoSoDieuPhoi>(`/coordination/requests/${id}`),
    goiDichVu<LoaiYeuCau[]>("/request-types"),
    goiDichVu<MucUuTien[]>("/priorities"),
    goiDichVu<PhongBan[]>("/departments"),
    docDichVu<LienHeNguoiGui>(`/coordination/requests/${id}/requester-contact`),
    goiDichVu<TrangThai[]>("/states"),
  ]);
  if (!ketQua.ok) return ketQua;
  return { ok: true, duLieu: { ho_so: ketQua.duLieu, cacLoai, cacMuc, cacPhong, lienHe, cacTrangThai } };
}

export function metaDieuPhoi(ho_so: HoSoDieuPhoi): MucMeta[] {
  const goiYPhong = ho_so.suggested_department;
  return [
    { icon: <Tag aria-hidden />, chu: ho_so.request_type?.label ?? "Chưa rõ loại" },
    {
      icon: <Building2 aria-hidden />,
      chu:
        ho_so.department?.label ??
        (goiYPhong
          ? `Chưa chuyển phòng · ${goiYPhong.source === "model" ? "mô hình gợi ý" : "gợi ý theo loại"}: ${goiYPhong.label}`
          : "Chưa chuyển phòng"),
    },
    {
      icon: <Flag aria-hidden />,
      chu: ho_so.priority ? `Ưu tiên ${ho_so.priority.label}` : "Mức ưu tiên đặt khi phân loại",
    },
  ];
}

function thanhNhanCoMa<T extends NhanCoMa>(ds: T[] | null): NhanCoMa[] {
  return (ds ?? []).map(({ code, label }) => ({ code, label }));
}

/**
 * Câu giải thích và bảng thao tác. `ngan` có mặt khi khối nằm ở đáy ngăn xem nhanh: bước chính
 * thành nút chính, thao tác khác vào menu, xong thì sang `sauKhiXong`.
 */
export function ThaoTacDieuPhoi({ d, ngan }: { d: DuLieuDieuPhoi; ngan?: { sauKhiXong: string } }) {
  const { ho_so, cacLoai, cacMuc, cacPhong } = d;
  const macDinh = cacMuc?.find((m) => m.is_default)?.code ?? "";
  const goiYPhong = ho_so.suggested_department;
  const goiYLoai = ho_so.suggested_request_type ?? null;
  const goiYMuc = ho_so.suggested_priority ?? null;

  // Điền sẵn: giá trị hồ sơ đang có trước, rồi mới tới gợi ý và mặc định. Điều phối
  // viên vẫn đổi được mọi ô — gợi ý chỉ để trường hợp thường gặp chỉ cần một cú bấm.
  // Loại yêu cầu luôn có giá trị — người gửi đã chọn — nên ô giữ lựa chọn của người, thẻ gợi ý của
  // mô hình (#317) nằm trên ô và nói khi hai bên khác nhau; điều phối viên đổi bằng một cú chọn.
  const giaTriDau: Record<string, string> = {
    request_type_code: ho_so.request_type?.code ?? goiYLoai?.code ?? "",
    priority_code: ho_so.priority?.code ?? goiYMuc?.code ?? macDinh,
    department_code: ho_so.department?.code ?? goiYPhong?.code ?? "",
    assignee_id: ho_so.assignee_id ?? "",
  };

  return (
    <>
      {/* Hồ sơ của chính mình: không có nút điều phối nào, chỉ còn nút của chủ hồ sơ
          nếu có — nói rõ vì sao (#154) */}
      {ho_so.requested_by_me && ho_so.allowed_transitions.length > 0 && (
        <p style={{ margin: "0 0 10px", fontSize: "13px", color: "var(--f-p-ink)", lineHeight: 1.55 }}>
          Đây là hồ sơ bạn gửi — một điều phối viên khác sẽ phân loại và chuyển phòng.
        </p>
      )}
      {/* Khóa có `updated_at`: gia hạn giữ nguyên trạng thái (#101), nên chỉ mã trạng
          thái thì bảng không dựng lại, khung gia hạn vừa xong vẫn mở */}
      <BangThaoTac
        key={`${ho_so.id}-${ho_so.state.code}-${ho_so.updated_at}`}
        maHoSo={ho_so.id}
        cacCanh={ho_so.allowed_transitions}
        giaTriDau={giaTriDau}
        goiY={{
          ...(goiYLoai ? { request_type_code: goiYLoai } : {}),
          ...(goiYMuc ? { priority_code: goiYMuc } : {}),
          ...(goiYPhong ? { department_code: goiYPhong } : {}),
        }}
        cacLoai={cacLoai ?? undefined}
        danhMuc={{
          "request-types": thanhNhanCoMa(cacLoai),
          priorities: thanhNhanCoMa(cacMuc),
          departments: thanhNhanCoMa(cacPhong),
        }}
        hanhDong={chuyenTrangThaiDieuPhoi}
        khiHet={{
          // Bảng trống vì hai lý do khác hẳn nhau — nói đúng lý do (#154)
          cau: ho_so.requested_by_me
            ? "Đây là hồ sơ bạn gửi — một điều phối viên khác sẽ phân loại và chuyển phòng."
            : "Hồ sơ đã rời khỏi tay điều phối viên. Không còn thao tác nào dành cho bạn ở trạng thái này.",
          veHangDoi: "/dieu-phoi",
        }}
        ngan={ngan}
      />
    </>
  );
}
