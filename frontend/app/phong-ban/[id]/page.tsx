// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn chi tiết hồ sơ của buồng lái phòng ban (#83).
//
// Cùng bố cục hai cột với buồng lái điều phối (#169, khối chung ở components/trang-ho-so):
// bên trái để ĐỌC — đầu hồ sơ, nội dung, dòng thời gian và trao đổi — bên phải để LÀM —
// hạn, thao tác, liên hệ. Trưởng phòng và người xử lý dùng chung trang này; nút của mỗi
// người khác nhau vì chúng đến từ `allowed_transitions`, không từ một phép so vai trò nào.
//
// Trang KHÔNG đoán trước ô nào sẽ hiện. Nó đọc `fields` của các thao tác đang đi được,
// rồi nạp đúng những danh mục mà các ô đó cần. Cạnh *Phân công lại* mang ràng buộc "không
// được đổi phòng ban", nên nó có cả ô phòng ban — bản đầu của trang chỉ nạp danh sách
// người, và ô phòng ban rơi về một ô gõ chữ trống. Nạp theo `fields` thì trường nào
// dịch vụ cho hiện cũng có danh mục, kể cả trường sau này mới thêm vào một cạnh.
//
// Nhờ vậy danh sách người xử lý chỉ được tra khi có ít nhất một thao tác cho giao người.
// Người xử lý mở hồ sơ thì không có thao tác nào như vậy, và Keycloak không bị hỏi tới —
// danh bạ chỉ nằm trên đường đi của đúng cái ô cần nó (#84).

import { Building2, Flag, MessagesSquare, Tag, User } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { chuyenTrangThaiPhongBan, guiLoiNhanPhongBan } from "@/app/phong-ban/thao-tac";
import { BangThaoTac, type NguonLuaChon } from "@/components/bang-thao-tac";
import { DongThoiGian } from "@/components/dong-thoi-gian";
import { KhungChat } from "@/components/khung-chat";
import { KhungLoiNhan } from "@/components/khung-loi-nhan";
import { MoiDangNhap } from "@/components/khung-lam-viec";
import { NutThanhDau, TenCapCon } from "@/components/khung-ung-dung";
import { TheLienHe } from "@/components/lien-he-nguoi-gui";
import { TheLichSu } from "@/components/the-lich-su";
import { duongHopThu } from "@/lib/hop-thu";
import { GhiChuMoLai, KhoiHoSoLienQuan } from "@/components/ho-so-lien-quan";
import { KhoiTepDinhKem } from "@/components/khoi-tep-dinh-kem";
import { DauHoSo, TheHan, TheThaoTac, ThanhBuoc } from "@/components/trang-ho-so";
import { docDichVu, goiDichVu, laHetPhien } from "@/lib/api";
import { cacBuoc } from "@/lib/buoc";
import type {
  HoSoPhongBan,
  LienHeNguoiGui as LienHe,
  NhanCoMa,
  NguoiNhanViecTrongPhong,
  TrangThai,
} from "@/lib/kieu";
import { kieuTruong, type NguonDanhMuc } from "@/lib/truong";

export const dynamic = "force-dynamic";

async function napNguon(nguon: NguonDanhMuc, ho_so: HoSoPhongBan): Promise<NguonLuaChon> {
  if (nguon === "assignees") {
    if (!ho_so.department) return { loi: "Hồ sơ chưa thuộc phòng nào nên chưa giao được người." };
    const ketQua = await docDichVu<NguoiNhanViecTrongPhong>(
      `/departments/${encodeURIComponent(ho_so.department.code)}/assignees`,
    );
    if (!ketQua.ok) {
      return {
        loi: `${ketQua.thongDiep} Vẫn nhận được hồ sơ mà chưa giao cho ai — cả phòng cùng thấy hồ sơ này.`,
      };
    }
    return ketQua.duLieu.people.map((p) => ({ code: p.id, label: p.name }));
  }

  // Ba danh mục còn lại mang đúng tên điểm cuối của chúng
  const ds = await goiDichVu<NhanCoMa[]>(`/${nguon}`);
  return ds ? ds.map(({ code, label }) => ({ code, label })) : { loi: "Không nạp được danh mục." };
}

/** Nạp đúng những danh mục mà các thao tác đang đi được cần tới — không hơn. */
async function danhMucCan(
  ho_so: HoSoPhongBan,
): Promise<Partial<Record<NguonDanhMuc, NguonLuaChon>>> {
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
  return Object.fromEntries(cap);
}

export default async function ChiTietPhongBan({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const ket_qua = await docDichVu<HoSoPhongBan>(`/department/requests/${id}`);
  // Phiên hết hạn (401) khác hồ sơ không có: mời đăng nhập lại, không hiện 404 (#150)
  if (laHetPhien(ket_qua)) return <MoiDangNhap hetPhien />;
  if (!ket_qua.ok) notFound();
  const ho_so = ket_qua.duLieu;

  // Liên hệ người gửi đi điểm cuối riêng (#131): danh bạ hỏng thì chỉ thẻ đó báo lỗi.
  const [danhMuc, lienHe, cacTrangThai] = await Promise.all([
    danhMucCan(ho_so),
    docDichVu<LienHe>(`/department/requests/${id}/requester-contact`),
    goiDichVu<TrangThai[]>("/states"),
  ]);
  const bayGio = new Date();
  // Hai cuộc của hồ sơ (#156): với người gửi, và nội bộ — dịch vụ đã lọc theo người xem
  const chung = ho_so.messages.filter((m) => !m.internal);
  const noiBo = ho_so.messages.filter((m) => m.internal);
  const nguoiGui = ho_so.requester_label ?? "Không rõ";
  const nguoiXuLy = ho_so.assigned_to_me
    ? "Bạn"
    : ho_so.assignee_id
      ? (ho_so.assignee_label ?? "Một người trong phòng")
      : "chưa giao cho ai";

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
      <DauHoSo
        ho_so={ho_so}
        meta={[
          { icon: <Tag aria-hidden />, chu: ho_so.request_type?.label ?? "Chưa rõ loại" },
          { icon: <Building2 aria-hidden />, chu: ho_so.department?.label ?? "Chưa thuộc phòng nào" },
          {
            icon: <Flag aria-hidden />,
            chu: ho_so.priority ? `Ưu tiên ${ho_so.priority.label}` : "Chưa đặt mức ưu tiên",
          },
          { icon: <User aria-hidden />, chu: `Người xử lý: ${nguoiXuLy}` },
        ]}
      />
      <ThanhBuoc cacBuoc={cacBuoc(cacTrangThai ?? [], ho_so.state.code, ho_so.history)} />

      <div className="hai-cot">
        {/* --- Cột trái: đọc. Màn hẹp thì xuống sau Hạn và thao tác (#189) ------- */}
        <div className="cot-doc" style={{ display: "grid", gap: "16px", minWidth: 0 }}>
          {ho_so.description && (
            <div className="the khoi">
              <div className="khoi-dau">Nội dung yêu cầu</div>
              <p className="mo-ta">{ho_so.description}</p>
            </div>
          )}

          <TheLichSu
            maHoSo={ho_so.id}
            soLoiNhan={chung.length}
            soNoiBo={noiBo.length}
            dongThoiGian={
              <DongThoiGian
                cacSuKien={ho_so.history}
                bayGio={bayGio}
                khiTrong="Hồ sơ chưa đổi trạng thái lần nào."
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
                    hanhDong={guiLoiNhanPhongBan}
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
                      hanhDong={guiLoiNhanPhongBan}
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
            {/* Khóa có `updated_at`: nhận việc giữ nguyên trạng thái (#127), nên chỉ mã
                trạng thái thì bảng không dựng lại sau khi nhận. */}
            <BangThaoTac
              key={`${ho_so.state.code}-${ho_so.updated_at}`}
              maHoSo={ho_so.id}
              cacCanh={ho_so.allowed_transitions}
              // Giá trị hồ sơ đang có, cho cả bốn trường quyết định. Ô phòng ban ở
              // cạnh phân công lại vì thế hiện đúng phòng đang giữ hồ sơ.
              giaTriDau={{
                request_type_code: ho_so.request_type?.code ?? "",
                priority_code: ho_so.priority?.code ?? "",
                department_code: ho_so.department?.code ?? "",
                assignee_id: ho_so.assignee_id ?? "",
              }}
              goiY={{}}
              danhMuc={danhMuc}
              hanhDong={chuyenTrangThaiPhongBan}
              khiHet={{
                cau: "Không có thao tác nào dành cho bạn ở trạng thái này.",
                veHangDoi: "/phong-ban",
              }}
            />
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
