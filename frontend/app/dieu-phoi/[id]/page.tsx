// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn chi tiết hồ sơ của điều phối viên (#82).
//
// Hai cột trên màn rộng (#169, khối chung ở components/trang-ho-so): bên trái là hồ sơ,
// dòng thời gian và trao đổi — thứ để ĐỌC; bên phải là hạn, thao tác, liên hệ — thứ để
// LÀM, bám theo khi cuộn. Điều phối viên xử lý hàng chục hồ sơ mỗi ngày, và một nút phải
// cuộn xuống đáy trang mới thấy là một nút bị bấm chậm.
//
// Dòng thời gian dùng chung thành phần với cổng người gửi, để hai bên nhìn cùng một hồ
// sơ thì thấy cùng một câu chuyện.

import { Building2, Flag, MessagesSquare, Tag } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { chuyenTrangThaiDieuPhoi, guiLoiNhanDieuPhoi } from "@/app/dieu-phoi/thao-tac";
import { BangThaoTac } from "@/components/bang-thao-tac";
import { DongThoiGian } from "@/components/dong-thoi-gian";
import { KhungChat } from "@/components/khung-chat";
import { KhungLoiNhan } from "@/components/khung-loi-nhan";
import { MoiDangNhap } from "@/components/khung-lam-viec";
import { NutThanhDau, TenCapCon } from "@/components/khung-ung-dung";
import { TheLienHe } from "@/components/lien-he-nguoi-gui";
import { TheLichSu } from "@/components/the-lich-su";
import { DauHoSo, TheHan, TheThaoTac, ThanhBuoc } from "@/components/trang-ho-so";
import { docDichVu, goiDichVu, laHetPhien } from "@/lib/api";
import { cacBuoc } from "@/lib/buoc";
import type {
  HoSoDieuPhoi,
  LienHeNguoiGui as LienHe,
  LoaiYeuCau,
  MucUuTien,
  NhanCoMa,
  PhongBan,
  TrangThai,
} from "@/lib/kieu";

export const dynamic = "force-dynamic";

function thanhNhanCoMa<T extends NhanCoMa>(ds: T[] | null): NhanCoMa[] {
  return (ds ?? []).map(({ code, label }) => ({ code, label }));
}

export default async function ChiTietDieuPhoi({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  // Liên hệ người gửi đi điểm cuối riêng (#131): danh bạ hỏng thì chỉ ô đó báo lỗi.
  const [ket_qua, cacLoai, cacMuc, cacPhong, lienHe, cacTrangThai] = await Promise.all([
    docDichVu<HoSoDieuPhoi>(`/coordination/requests/${id}`),
    goiDichVu<LoaiYeuCau[]>("/request-types"),
    goiDichVu<MucUuTien[]>("/priorities"),
    goiDichVu<PhongBan[]>("/departments"),
    docDichVu<LienHe>(`/coordination/requests/${id}/requester-contact`),
    goiDichVu<TrangThai[]>("/states"),
  ]);

  // Phiên hết hạn (401) khác hồ sơ không có: mời đăng nhập lại, không hiện 404 (#150)
  if (laHetPhien(ket_qua)) return <MoiDangNhap hetPhien />;
  if (!ket_qua.ok) notFound();
  const ho_so = ket_qua.duLieu;

  const bayGio = new Date();
  const nguoiGui = ho_so.requester_label ?? "Không rõ";
  const macDinh = cacMuc?.find((m) => m.is_default)?.code ?? "";
  const goiYPhong = ho_so.suggested_department;

  // Điền sẵn: giá trị hồ sơ đang có trước, rồi mới tới gợi ý và mặc định. Điều phối
  // viên vẫn đổi được mọi ô — gợi ý chỉ để trường hợp thường gặp chỉ cần một cú bấm.
  const giaTriDau: Record<string, string> = {
    request_type_code: ho_so.request_type?.code ?? "",
    priority_code: ho_so.priority?.code ?? macDinh,
    department_code: ho_so.department?.code ?? goiYPhong?.code ?? "",
    assignee_id: ho_so.assignee_id ?? "",
  };

  return (
    <>
      <TenCapCon ten={ho_so.code} />
      {ho_so.messages.length > 0 && (
        <NutThanhDau>
          <Link className="nut nut-nho" data-loai="ma" href={`/hop-thu?ho-so=${ho_so.id}`}>
            <MessagesSquare aria-hidden />
            Mở trong hộp thư
          </Link>
        </NutThanhDau>
      )}
      <DauHoSo
        ho_so={ho_so}
        meta={[
          { icon: <Tag aria-hidden />, chu: ho_so.request_type?.label ?? "Chưa rõ loại" },
          {
            icon: <Building2 aria-hidden />,
            chu:
              ho_so.department?.label ??
              (goiYPhong ? `Chưa định tuyến · gợi ý theo loại: ${goiYPhong.label}` : "Chưa định tuyến"),
          },
          {
            icon: <Flag aria-hidden />,
            chu: ho_so.priority ? `Ưu tiên ${ho_so.priority.label}` : "Mức ưu tiên đặt khi phân loại",
          },
        ]}
      />
      <ThanhBuoc cacBuoc={cacBuoc(cacTrangThai ?? [], ho_so.state.code, ho_so.history)} />

      <div className="hai-cot">
        {/* --- Cột trái: đọc -------------------------------------------------- */}
        <div style={{ display: "grid", gap: "16px", minWidth: 0 }}>
          {ho_so.description && (
            <div className="the khoi">
              <div className="khoi-dau">Nội dung yêu cầu</div>
              <p className="mo-ta">{ho_so.description}</p>
            </div>
          )}

          <TheLichSu
            maHoSo={ho_so.id}
            soLoiNhan={ho_so.messages.length}
            dongThoiGian={
              <DongThoiGian
                cacSuKien={ho_so.history}
                bayGio={bayGio}
                khiTrong="Hồ sơ chưa đổi trạng thái lần nào. Thao tác đầu tiên của bạn sẽ là mốc đầu tiên ở đây."
                trongThe
              />
            }
            traoDoi={
              <KhungChat
                cacLoiNhan={ho_so.messages}
                bayGio={bayGio}
                soan={
                  <KhungLoiNhan
                    key={ho_so.messages.length}
                    maHoSo={ho_so.id}
                    cacLoai={ho_so.message_kinds}
                    daKetThuc={ho_so.state.is_terminal}
                    hanhDong={guiLoiNhanDieuPhoi}
                    kieu="chat"
                    goiY={`Nhắn cho ${nguoiGui}`}
                  />
                }
              />
            }
          />
        </div>

        {/* --- Cột phải: làm, dính khi cuộn --------------------------------- */}
        <div className="cot-dinh">
          <TheHan ho_so={ho_so} />
          <TheThaoTac>
            <BangThaoTac
              key={ho_so.state.code}
              maHoSo={ho_so.id}
              cacCanh={ho_so.allowed_transitions}
              giaTriDau={giaTriDau}
              goiY={goiYPhong ? { department_code: goiYPhong.code } : {}}
              danhMuc={{
                "request-types": thanhNhanCoMa(cacLoai),
                priorities: thanhNhanCoMa(cacMuc),
                departments: thanhNhanCoMa(cacPhong),
              }}
              hanhDong={chuyenTrangThaiDieuPhoi}
              khiHet={{
                cau: "Hồ sơ đã rời khỏi tay điều phối viên. Không còn thao tác nào dành cho bạn ở trạng thái này.",
                veHangDoi: "/dieu-phoi",
              }}
            />
          </TheThaoTac>
          <TheLienHe ten={nguoiGui} dinhDanh={ho_so.requester_id} ketQua={lienHe} />
        </div>
      </div>
    </>
  );
}
