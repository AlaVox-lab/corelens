// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn chi tiết hồ sơ của điều phối viên (#82).
//
// Hai cột trên màn rộng: bên trái là hồ sơ và dòng thời gian — thứ để ĐỌC; bên phải
// là bảng thao tác — thứ để LÀM, bám theo khi cuộn. Điều phối viên xử lý hàng chục hồ
// sơ mỗi ngày, và một nút phải cuộn xuống đáy trang mới thấy là một nút bị bấm chậm.
//
// Dòng thời gian dùng chung thành phần với cổng người gửi, để hai bên nhìn cùng một hồ
// sơ thì thấy cùng một câu chuyện.

import Link from "next/link";
import { notFound } from "next/navigation";

import { chuyenTrangThaiDieuPhoi, guiLoiNhanDieuPhoi } from "@/app/dieu-phoi/thao-tac";
import { BangThaoTac } from "@/components/bang-thao-tac";
import { DongThoiGian } from "@/components/dong-thoi-gian";
import { KhungLoiNhan } from "@/components/khung-loi-nhan";
import { LienHeNguoiGui } from "@/components/lien-he-nguoi-gui";
import { NhanTrangThai } from "@/components/nhan-trang-thai";
import { MoiDangNhap } from "@/components/khung-lam-viec";
import { docDichVu, goiDichVu, laHetPhien } from "@/lib/api";
import { ngayGio, thoiLuong } from "@/lib/dinh-dang";
import type {
  HoSoDieuPhoi,
  LienHeNguoiGui as LienHe,
  LoaiYeuCau,
  MucUuTien,
  NhanCoMa,
  PhongBan,
} from "@/lib/kieu";

export const dynamic = "force-dynamic";

function O({
  tua,
  children,
  phu,
}: {
  tua: string;
  children: React.ReactNode;
  phu?: React.ReactNode;
}) {
  return (
    <div style={{ display: "grid", gap: "6px", alignContent: "start" }}>
      <span className="tua-muc">{tua}</span>
      <span style={{ fontSize: "14.5px", fontWeight: 600 }}>{children}</span>
      {phu && <span style={{ fontSize: "12.5px", color: "var(--ink-3)" }}>{phu}</span>}
    </div>
  );
}

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
  const [ket_qua, cacLoai, cacMuc, cacPhong, lienHe] = await Promise.all([
    docDichVu<HoSoDieuPhoi>(`/coordination/requests/${id}`),
    goiDichVu<LoaiYeuCau[]>("/request-types"),
    goiDichVu<MucUuTien[]>("/priorities"),
    goiDichVu<PhongBan[]>("/departments"),
    docDichVu<LienHe>(`/coordination/requests/${id}/requester-contact`),
  ]);

  // Phiên hết hạn (401) khác hồ sơ không có: mời đăng nhập lại, không hiện 404 (#150)
  if (laHetPhien(ket_qua)) return <MoiDangNhap hetPhien />;
  if (!ket_qua.ok) notFound();
  const ho_so = ket_qua.duLieu;

  const bayGio = new Date();
  const giayCho = Math.max(
    0,
    (bayGio.getTime() - new Date(ho_so.state_entered_at).getTime()) / 1000,
  );
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
      <Link href="/dieu-phoi" className="nut nut-nho khong-in">
        ← Hàng đợi
      </Link>

      <div className="bo-cuc-buong-lai">
        {/* --- Cột trái: đọc -------------------------------------------------- */}
        <div style={{ minWidth: 0 }}>
          <div className="the" style={{ padding: "20px 22px" }}>
            <div
              className="mono"
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "8px 12px",
                alignItems: "center",
                fontSize: "12px",
                color: "var(--ink-3)",
              }}
            >
              {ho_so.code}
              <span
                style={{
                  fontFamily: "var(--font)",
                  padding: "2px 9px",
                  borderRadius: "999px",
                  background: "var(--surface-3)",
                  border: `1px ${ho_so.request_type ? "solid" : "dashed"} var(--line-2)`,
                  fontSize: "12px",
                  color: "var(--ink-2)",
                }}
              >
                {ho_so.request_type?.label ?? "Chưa rõ loại"}
              </span>
              <span>Gửi {ngayGio(ho_so.created_at)}</span>
            </div>

            <h1
              style={{
                margin: "9px 0 0",
                fontSize: "clamp(20px,3vw,24px)",
                fontWeight: 600,
                letterSpacing: "-.02em",
                lineHeight: 1.3,
              }}
            >
              {ho_so.title}
            </h1>

            <div
              style={{
                marginTop: "18px",
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))",
                gap: "16px",
              }}
            >
              <O tua="Trạng thái" phu={`đã chờ ${thoiLuong(giayCho)}`}>
                <NhanTrangThai ma={ho_so.state.code} nhan={ho_so.state.label} />
              </O>
              <O tua="Người gửi" phu={<LienHeNguoiGui ketQua={lienHe} />}>
                {ho_so.requester_label ?? "Không rõ"}
              </O>
              <O
                tua="Mức ưu tiên"
                phu={ho_so.priority ? undefined : "Đặt khi phân loại"}
              >
                {ho_so.priority?.label ?? "—"}
              </O>
              <O
                tua="Phòng ban"
                phu={
                  !ho_so.department && goiYPhong
                    ? `Gợi ý theo loại: ${goiYPhong.label}`
                    : undefined
                }
              >
                {ho_so.department?.label ?? "Chưa định tuyến"}
              </O>
            </div>
          </div>

          {ho_so.description && (
            <div className="the" style={{ marginTop: "20px", padding: "18px 22px" }}>
              <h2 className="tua-muc" style={{ margin: 0 }}>
                Nội dung yêu cầu
              </h2>
              <p
                style={{
                  margin: "9px 0 0",
                  fontSize: "14px",
                  lineHeight: 1.7,
                  whiteSpace: "pre-wrap",
                }}
              >
                {ho_so.description}
              </p>
            </div>
          )}

          <DongThoiGian
            cacSuKien={ho_so.history}
            cacLoiNhan={ho_so.messages}
            bayGio={bayGio}
            khiTrong="Hồ sơ chưa đổi trạng thái lần nào. Thao tác đầu tiên của bạn sẽ là mốc đầu tiên ở đây."
          />

          {/* Lời nhắn (#128): ngay dưới dòng thời gian, vì lời nhắn nằm trong đó. Không đặt ở
              cột thao tác bên phải — cột đó dính khi cuộn, thêm thẻ là cao quá màn hình. */}
          <div className="the khong-in" style={{ marginTop: "16px" }}>
            <div
              style={{
                padding: "15px 17px",
                borderBottom: "1px solid var(--line)",
                display: "grid",
                gap: "4px",
              }}
            >
              <h2 style={{ margin: 0, fontSize: "15px", fontWeight: 600 }}>Lời nhắn</h2>
              <p style={{ margin: 0, fontSize: "12.5px", color: "var(--ink-3)", lineHeight: 1.55 }}>
                Trao đổi với người gửi ngay trên hồ sơ. Không đổi trạng thái, không dừng đồng hồ.
              </p>
            </div>
            <div style={{ padding: "15px 17px" }}>
              <KhungLoiNhan
                key={ho_so.messages.length}
                maHoSo={ho_so.id}
                cacLoai={ho_so.message_kinds}
                daKetThuc={ho_so.state.is_terminal}
                hanhDong={guiLoiNhanDieuPhoi}
              />
            </div>
          </div>
        </div>

        {/* --- Cột phải: làm ------------------------------------------------- */}
        <aside className="cot-thao-tac khong-in">
          <div className="the">
            <div
              style={{
                padding: "15px 17px",
                borderBottom: "1px solid var(--line)",
                display: "grid",
                gap: "4px",
              }}
            >
              <h2 style={{ margin: 0, fontSize: "15px", fontWeight: 600 }}>Thao tác</h2>
              <p style={{ margin: 0, fontSize: "12.5px", color: "var(--ink-3)", lineHeight: 1.55 }}>
                Sinh ra từ bộ quy tắc quy trình, theo trạng thái hồ sơ và vai trò của bạn.
              </p>
            </div>
            <div style={{ padding: "15px 17px" }}>
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
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}
