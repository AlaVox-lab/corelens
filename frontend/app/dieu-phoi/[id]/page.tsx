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
// sơ thì thấy cùng một câu chuyện. Nạp dữ liệu và khối thao tác dùng chung với ngăn xem nhanh
// của hàng đợi (#233), ở `app/dieu-phoi/ho-so.tsx`.

import { MessagesSquare } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { guiLoiNhanDieuPhoi } from "@/app/dieu-phoi/thao-tac";
import { metaDieuPhoi, napHoSoDieuPhoi, ThaoTacDieuPhoi } from "@/app/dieu-phoi/ho-so";
import { DongThoiGian } from "@/components/dong-thoi-gian";
import { KhungChat } from "@/components/khung-chat";
import { KhungLoiNhan } from "@/components/khung-loi-nhan";
import { KhongPhanHoi, MoiDangNhap } from "@/components/khung-lam-viec";
import { NutThanhDau, TenCapCon } from "@/components/khung-ung-dung";
import { TheLienHe } from "@/components/lien-he-nguoi-gui";
import { TheLichSu } from "@/components/the-lich-su";
import { duongHopThu } from "@/lib/hop-thu";
import { GhiChuMoLai, KhoiHoSoLienQuan } from "@/components/ho-so-lien-quan";
import { KhoiTepDinhKem } from "@/components/khoi-tep-dinh-kem";
import { DauHoSo, TheHan, TheNoiDung, TheThaoTac, ThanhBuoc } from "@/components/trang-ho-so";
import { laHetPhien } from "@/lib/api";
import { cacBuoc } from "@/lib/buoc";

export const dynamic = "force-dynamic";

export default async function ChiTietDieuPhoi({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const ket_qua = await napHoSoDieuPhoi(id);

  // Phiên hết hạn (401) khác hồ sơ không có: mời đăng nhập lại, không hiện 404 (#150)
  if (laHetPhien(ket_qua)) return <MoiDangNhap hetPhien />;
  // Dịch vụ không phản hồi khác hồ sơ không có: báo lỗi để người dùng thử lại (#235)
  if (!ket_qua.ok && ket_qua.ma === "khong-ket-noi-duoc") return <KhongPhanHoi />;
  if (!ket_qua.ok) notFound();
  const d = ket_qua.duLieu;
  const { ho_so, lienHe, cacTrangThai } = d;

  const bayGio = new Date();
  // Hai cuộc của hồ sơ (#156): với người gửi, và nội bộ — dịch vụ đã lọc theo người xem
  const chung = ho_so.messages.filter((m) => !m.internal);
  const noiBo = ho_so.messages.filter((m) => m.internal);
  const nguoiGui = ho_so.requester_label ?? "Không rõ người gửi";

  return (
    <>
      <TenCapCon ten={ho_so.code} />
      {ho_so.messages.length > 0 && (
        <NutThanhDau>
          <Link className="nut nut-nho" data-loai="ma" href={duongHopThu(ho_so)}>
            <MessagesSquare aria-hidden />
            Mở trong hộp thư
          </Link>
        </NutThanhDau>
      )}
      <DauHoSo ho_so={ho_so} meta={metaDieuPhoi(ho_so)} />
      <ThanhBuoc cacBuoc={cacBuoc(cacTrangThai ?? [], ho_so.state.code, ho_so.history)} />

      <div className="hai-cot">
        {/* --- Cột trái: đọc. Màn hẹp thì xuống sau Hạn và thao tác (#189) ------- */}
        <div className="cot-doc" style={{ display: "grid", gap: "16px", minWidth: 0 }}>
          <TheNoiDung ho_so={ho_so} />

          <TheLichSu
            maHoSo={ho_so.id}
            soLoiNhan={chung.length}
            soNoiBo={noiBo.length}
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
                cacLoiNhan={chung}
                bayGio={bayGio}
                soan={
                  <KhungLoiNhan
                    key={chung.length}
                    maHoSo={ho_so.id}
                    cacLoai={ho_so.message_kinds.filter((k) => !k.internal)}
                    daKetThuc={ho_so.state.is_terminal}
                    hanhDong={guiLoiNhanDieuPhoi}
                    kieu="chat"
                    goiY={`Nhắn cho ${nguoiGui}`}
                  />
                }
              />
            }
            noiBo={
              ho_so.sees_internal ? (
                <KhungChat
                  cacLoiNhan={noiBo}
                  bayGio={bayGio}
                  noiBo
                  soan={
                    <KhungLoiNhan
                      key={noiBo.length}
                      maHoSo={ho_so.id}
                      cacLoai={ho_so.message_kinds.filter((k) => k.internal)}
                      daKetThuc={ho_so.state.is_terminal}
                      hanhDong={guiLoiNhanDieuPhoi}
                      kieu="chat"
                      noiBo
                      goiY="Nhắn nội bộ — người gửi không thấy"
                    />
                  }
                />
              ) : undefined
            }
          />
        </div>

        {/* --- Cột phải: làm, dính khi cuộn --------------------------------- */}
        <div className="cot-dinh">
          <TheHan ho_so={ho_so} />
          <GhiChuMoLai hoSo={ho_so} />
          <TheThaoTac>
            <ThaoTacDieuPhoi d={d} />
          </TheThaoTac>
          {/* Hồ sơ gốc và hồ sơ tạo lại (#102): chỉ chữ, không đường dẫn — hồ sơ kia có thể
              đang ở phòng khác */}
          <KhoiHoSoLienQuan hoSo={ho_so} />
          {/* Tệp đính kèm (#80): nhân viên chỉ xem và tải về, không thêm */}
          <KhoiTepDinhKem
            maHoSo={ho_so.id}
            tep={ho_so.attachments}
            choPhep={false}
            chinhSach={null}
          />
          <TheLienHe ten={nguoiGui} dinhDanh={ho_so.requester_id} ketQua={lienHe} />
        </div>
      </div>
    </>
  );
}
