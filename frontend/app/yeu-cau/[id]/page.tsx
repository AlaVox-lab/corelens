// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn “Chi tiết hồ sơ”.
//
// Phần đáng nói nhất là DÒNG THỜI GIAN. Nó không phải đồ trang trí: nó là bản
// `event_log` của chính hồ sơ này, hiện ra nguyên vẹn cho người gửi đọc.
//
// Hầu hết hệ thống quản lý yêu cầu chỉ cho người gửi thấy trạng thái hiện tại, và
// toàn bộ đường đi nằm trong phần quản trị. Hệ quả là khi hồ sơ đi lòng vòng — phòng
// ban A trả lại, điều phối viên chuyển sang phòng ban B — người gửi chỉ thấy con số
// ngày chờ tăng lên mà không hiểu vì sao. Họ gọi điện hỏi, và cuộc gọi đó không để
// lại dấu vết nào trong dữ liệu.
//
// Ở đây thì ngược lại: mỗi lần quay lui hiện ra thành một mốc có ghi lý do. Cùng một
// dữ liệu đó, tầng `D` dùng để khai phá quy trình thực tế và chỉ ra điểm nghẽn —
// nghĩa là thứ người dùng đọc để yên tâm và thứ hệ thống đọc để tự cải tiến là **một**.
// Xem CLAUDE.md mục 4.1.

import { MessagesSquare } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { TheTruongRieng } from "@/components/the-truong-rieng";
import type { NguonLuaChon } from "@/components/bang-thao-tac";
import {
  DongThoiGian,
  danhDauQuayLui,
  soLanDoiTrangThai,
} from "@/components/dong-thoi-gian";
import { NhanTrangThai } from "@/components/nhan-trang-thai";
import { ThaoTacHoSo } from "@/app/yeu-cau/[id]/thao-tac-ho-so";
import { guiLoiNhan } from "@/app/yeu-cau/thao-tac";
import { DanhDauDaDoc } from "@/components/danh-dau-da-doc";
import { GhiChuMoLai, KhoiHoSoLienQuan, MoiTaoHoSoMoi } from "@/components/ho-so-lien-quan";
import { KhoiTepDinhKem } from "@/components/khoi-tep-dinh-kem";
import { CuonTinMoi } from "@/components/cuon-tin-moi";
import { KhungChat } from "@/components/khung-chat";
import { KhungLoiNhan } from "@/components/khung-loi-nhan";
import { NutThanhDau } from "@/components/khung-ung-dung";
import { KhongPhanHoi, MoiDangNhap } from "@/components/khung-lam-viec";
import { docDichVu, goiDichVu, laHetPhien } from "@/lib/api";
import { ngayGio } from "@/lib/dinh-dang";
import type { ChinhSachTep, HoSoChiTiet, LoaiYeuCau, NhanCoMa } from "@/lib/kieu";
import { daTroiQua, docDongHo, docTuDong } from "@/lib/sla";
import { CHU_GIAI_NHOM, bienHoMau, trinhBayTrangThai } from "@/lib/trang-thai";
import { kieuTruong, type NguonDanhMuc } from "@/lib/truong";

export const dynamic = "force-dynamic";

/**
 * Danh mục cho ô chọn của các thao tác đang đi được — ở cổng này chỉ có ô loại yêu cầu
 * của thao tác sửa nội dung (#127). Nạp theo `fields` giống buồng lái phòng ban: hồ sơ
 * không có thao tác sửa thì trang không gọi thêm lần nào.
 */
async function danhMucCan(
  ho_so: HoSoChiTiet,
): Promise<Partial<Record<NguonDanhMuc, NguonLuaChon>>> {
  const can = new Set<NguonDanhMuc>();
  for (const canh of ho_so.allowed_transitions) {
    for (const truong of canh.fields) {
      const nguon = kieuTruong(truong).nguon;
      if (nguon) can.add(nguon);
    }
  }
  const cap = await Promise.all(
    [...can].map(async (nguon) => {
      const ds = await goiDichVu<NhanCoMa[]>(`/${nguon}`);
      const luaChon: NguonLuaChon = ds
        ? ds.map(({ code, label }) => ({ code, label }))
        : { loi: "Không nạp được danh mục." };
      return [nguon, luaChon] as const;
    }),
  );
  return Object.fromEntries(cap);
}

function O({
  tua,
  chinh,
  phu,
  phuCanhBao = false,
  lop,
  lopPhu,
}: {
  tua: string;
  chinh: React.ReactNode;
  phu?: string;
  phuCanhBao?: boolean;
  /** Lớp CSS cho cách xếp trên điện thoại (#189). */
  lop?: string;
  /** Lớp CSS cho dòng phụ — ẩn được trên điện thoại (#189). */
  lopPhu?: string;
}) {
  return (
    <div className={lop} style={{ display: "grid", gap: "7px", alignContent: "start" }}>
      <span className="tua-muc">{tua}</span>
      <span style={{ fontSize: "15px", fontWeight: 600 }}>{chinh}</span>
      {phu && (
        <span
          className={lopPhu}
          style={{
            fontSize: "12.5px",
            color: phuCanhBao ? "var(--f-r-ink)" : "var(--ink-3)",
          }}
        >
          {phu}
        </span>
      )}
    </div>
  );
}

export default async function ChiTietHoSo({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tep?: string }>;
}) {
  const { id } = await params;
  const { tep: tepLoi } = await searchParams;
  const ket_qua = await docDichVu<HoSoChiTiet>(`/requests/${id}`);

  // Phiên hết hạn (401) khác hồ sơ không có: mời đăng nhập lại, không hiện 404 (#150)
  if (laHetPhien(ket_qua)) return <MoiDangNhap hetPhien />;
  // Dịch vụ trả 404 cho cả hồ sơ không tồn tại lẫn hồ sơ của người khác — cố ý, để
  // người dò số định danh không xác nhận được hồ sơ nào có thật.
  // Dịch vụ không phản hồi khác hồ sơ không có: báo lỗi để người dùng thử lại (#235)
  if (!ket_qua.ok && ket_qua.ma === "khong-ket-noi-duoc") return <KhongPhanHoi />;
  if (!ket_qua.ok) notFound();
  const ho_so = ket_qua.duLieu;

  const danhMuc = await danhMucCan(ho_so);
  // Bảng sửa nội dung có trường riêng (#250): cần danh mục loại KÈM khai báo trường, để đổi
  // loại trong bảng thì ô trường riêng đổi theo
  const coTruongRieng = ho_so.allowed_transitions.some((c) => c.fields.includes("details"));
  const cacLoaiDayDu = coTruongRieng ? await goiDichVu<LoaiYeuCau[]>("/request-types") : null;
  // Giới hạn tệp chỉ cần khi người gửi thêm được tệp lúc này (#80)
  const chinhSachTep = ho_so.can_attach
    ? await goiDichVu<ChinhSachTep>("/attachments/policy")
    : null;
  const bayGio = new Date();
  const dongHo = docDongHo(ho_so, "nguoi-gui");
  // Hồ sơ đang chờ người gửi mà có hạn chờ — Hoàn tất tự đóng sau 3 ngày làm việc (#144)
  const tuDong = docTuDong(ho_so);
  const kieu = trinhBayTrangThai(ho_so.state.code);
  const nhomChuGiai = CHU_GIAI_NHOM.find((n) => n.nhom === kieu.nhom);
  const quayLui = danhDauQuayLui(ho_so.history);

  return (
    <>
      {/* Trang người gửi chưa có thẻ Trao đổi: mở trang là đã đọc lời nhắn (#155) */}
      <DanhDauDaDoc maHoSo={ho_so.id} soTin={ho_so.messages.length} />
      {ho_so.messages.length > 0 && (
        <NutThanhDau>
          <Link className="nut nut-nho" data-loai="ma" href={`/hop-thu?ho-so=${ho_so.id}`}>
            <MessagesSquare aria-hidden />
            Mở trong hộp thư
          </Link>
        </NutThanhDau>
      )}
      {/* Điện thoại đã có đường dẫn ở thanh đầu — nút này nhường chỗ cho thao tác (#189) */}
      <Link href="/yeu-cau" className="nut nut-nho khong-in an-tren-hep">
        ← Hồ sơ của tôi
      </Link>

      {/* --- Thẻ đầu trang -------------------------------------------------- */}
      <div className="the" style={{ marginTop: "14px" }}>
        <div style={{ padding: "20px 22px" }}>
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
            {ho_so.request_type && (
              <span
                style={{
                  fontFamily: "var(--font)",
                  padding: "2px 9px",
                  borderRadius: "999px",
                  background: "var(--surface-3)",
                  border: "1px solid var(--line)",
                  fontSize: "12px",
                  color: "var(--ink-2)",
                }}
              >
                {ho_so.request_type.label}
              </span>
            )}
            <span>Gửi {ngayGio(ho_so.created_at)}</span>
          </div>

          <h1
            style={{
              margin: "9px 0 0",
              fontSize: "clamp(20px,3.2vw,26px)",
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
              // 140px: điện thoại xếp 2×2 thay vì một cột, nút thao tác lên màn hình đầu (#189)
              gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))",
              gap: "16px",
            }}
          >
            <O
              lop="o-tron-hang"
              lopPhu="an-tren-hep"
              tua="Trạng thái hiện tại"
              chinh={
                <NhanTrangThai ma={ho_so.state.code} nhan={ho_so.state.label} to />
              }
              phu={`Đổi lần cuối ${ngayGio(ho_so.updated_at)}`}
            />
            {/* Cố ý KHÔNG hiện `assignee_id`. Nó là định danh `sub` của Keycloak —
                một chuỗi UUID — và dịch vụ chưa có đường tra ngược ra tên người. Đưa
                một dãy ký tự vô nghĩa lên màn hình thì tệ hơn là không đưa gì. Tên
                người xử lý sẽ có khi dịch vụ biết tra danh bạ; tới lúc đó thay dòng
                dưới đây. */}
            <O
              tua="Đang giữ hồ sơ"
              chinh={ho_so.department?.label ?? "Chưa chuyển về phòng nào"}
              phu={
                ho_so.assignee_id
                  ? "Đã có người được phân công xử lý"
                  : "Chưa phân công người xử lý cụ thể"
              }
            />
            <O
              tua="Đã trôi qua"
              chinh={daTroiQua(ho_so, bayGio)}
              phu={dongHo.cau}
              phuCanhBao={dongHo.canhBao}
            />
            {/* Số liệu nhật ký — dòng thời gian bên dưới vẫn đủ; điện thoại nhường chỗ (#189) */}
            <O
              lop="an-tren-hep"
              tua="Số lần đổi trạng thái"
              chinh={`${soLanDoiTrangThai(ho_so.history)}`}
              phu={
                quayLui.size > 0
                  ? `${quayLui.size} lần quay lui`
                  : "Hồ sơ đi thẳng, chưa quay lui lần nào"
              }
              phuCanhBao={quayLui.size > 0}
            />
          </div>
        </div>

        {nhomChuGiai && (
          <div
            style={{
              ...bienHoMau(kieu.ho),
              display: "flex",
              gap: "12px",
              padding: "15px 22px",
              background: "var(--ho-bg)",
              borderTop: "1px solid var(--ho-line)",
            }}
          >
            <span
              aria-hidden="true"
              style={{
                flex: "0 0 auto",
                width: "24px",
                height: "24px",
                borderRadius: "50%",
                background: "var(--ho-solid)",
                color: "var(--ho-on)",
                display: "grid",
                placeItems: "center",
                fontSize: "12px",
                lineHeight: 1,
              }}
            >
              {kieu.dau}
            </span>
            <span style={{ display: "grid", gap: "4px", minWidth: 0 }}>
              <span style={{ fontSize: "13.5px", fontWeight: 600 }}>
                {nhomChuGiai.tieuDe}
              </span>
              <span style={{ fontSize: "13px", color: "var(--ink-2)", lineHeight: 1.6 }}>
                {nhomChuGiai.moTa}
              </span>
            </span>
          </div>
        )}
      </div>

      {/* --- Thao tác — ngay dưới phần đầu (#189): người gửi mở hồ sơ là thấy việc của
          mình, không phải cuộn qua nhật ký --------------------------------------- */}
      <div id="thao-tac" className="the khong-in" style={{ marginTop: "16px", scrollMarginTop: "72px" }}>
        <div style={{ padding: "17px 20px", display: "grid", gap: "5px", borderBottom: "1px solid var(--line)" }}>
          <h2 style={{ margin: 0, fontSize: "15px", fontWeight: 600 }}>
            Bạn có thể làm gì lúc này
          </h2>
          {/* Lời giải thích nhường chỗ cho nút trên điện thoại (#189) */}
          <p className="an-tren-hep" style={{ margin: 0, fontSize: "13px", color: "var(--ink-2)", lineHeight: 1.6, maxWidth: "72ch" }}>
            Các nút dưới đây phụ thuộc vào trạng thái hồ sơ và vai trò của bạn. Thao
            tác nào không có ở đây thì ở bước này chưa làm được.
          </p>
          {tuDong && (
            <p
              style={{
                margin: "4px 0 0",
                fontSize: "13px",
                fontWeight: tuDong.canhBao ? 600 : undefined,
                color: tuDong.canhBao ? "var(--f-a-ink)" : "var(--ink-2)",
              }}
            >
              {tuDong.cau}
            </p>
          )}
        </div>
        <div style={{ padding: "17px 20px" }}>
          {/* Khóa có `updated_at`: sửa nội dung giữ nguyên trạng thái (#127), nên chỉ mã
              trạng thái thì bảng không dựng lại, và bảng sửa vẫn mở sau khi đã lưu. */}
          <ThaoTacHoSo
            key={`${ho_so.state.code}-${ho_so.updated_at}`}
            maHoSo={ho_so.id}
            cacCanh={ho_so.allowed_transitions}
            giaTriDau={{
              title: ho_so.title,
              description: ho_so.description ?? "",
              request_type_code: ho_so.request_type?.code ?? "",
            }}
            danhMuc={danhMuc}
            truongRieng={
              cacLoaiDayDu
                ? { giaTri: ho_so.details ?? {}, loaiDau: ho_so.request_type?.code ?? null, cacLoai: cacLoaiDayDu }
                : undefined
            }
          />
          <GhiChuMoLai hoSo={ho_so} />
        </div>
      </div>
      {/* Biểu mẫu gửi đã tạo hồ sơ nhưng tải tệp lên hỏng (#80): nói rõ hồ sơ ĐÃ gửi, để
          người gửi không bấm gửi lần nữa và sinh hồ sơ thứ hai */}
      {tepLoi === "loi" && (
        <p
          role="alert"
          style={{
            margin: "16px 0 0",
            padding: "10px 12px",
            borderRadius: "9px",
            background: "var(--f-a-bg)",
            border: "1px solid var(--f-a-line)",
            color: "var(--f-a-ink)",
            fontSize: "13px",
            lineHeight: 1.55,
          }}
        >
          Hồ sơ đã được gửi, nhưng tệp đính kèm chưa tải lên được. Thêm lại tệp ở khối “Tệp đính
          kèm” bên dưới — đừng gửi hồ sơ mới.
        </p>
      )}
      <div style={{ marginTop: "16px" }}>
        <KhoiTepDinhKem
          maHoSo={ho_so.id}
          tep={ho_so.attachments}
          choPhep={ho_so.can_attach}
          chinhSach={chinhSachTep}
        />
      </div>
      {/* Hết đường mở lại thì mời tạo hồ sơ mới; hồ sơ nối nhau thì liệt kê (#102) */}
      <MoiTaoHoSoMoi hoSo={ho_so} />
      <div style={{ marginTop: "16px" }}>
        <KhoiHoSoLienQuan hoSo={ho_so} lienKet={(id) => `/yeu-cau/${id}`} />
      </div>
      {(ho_so.description || (ho_so.detail_fields?.length ?? 0) > 0) && (
        <div className="the" style={{ marginTop: "24px", padding: "18px 22px" }}>
          <h2 className="tua-muc" style={{ margin: 0 }}>
            Nội dung yêu cầu
          </h2>
          <TheTruongRieng cacTruong={ho_so.detail_fields ?? []} giaTri={ho_so.details ?? {}} />
          {ho_so.description ? (
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
          ) : null}
        </div>
      )}

      {/* --- Lời nhắn (#128) — khung trò chuyện riêng, như thẻ Trao đổi phía nhân viên
          (#169): dòng thời gian thu gọn (#189) không được giấu mất tin nhắn ---------- */}
      <div id="khung-loi-nhan" className="the khong-in" style={{ marginTop: "16px" }}>
        <CuonTinMoi chon="#khung-loi-nhan" soTin={ho_so.messages.length} />
        <div style={{ padding: "17px 20px", display: "grid", gap: "5px", borderBottom: "1px solid var(--line)" }}>
          <h2 style={{ margin: 0, fontSize: "15px", fontWeight: 600 }}>Trao đổi</h2>
          <p style={{ margin: 0, fontSize: "13px", color: "var(--ink-2)", lineHeight: 1.6, maxWidth: "72ch" }}>
            Nhắn cho điều phối viên hay phòng ban đang giữ hồ sơ, thay cho gọi điện: câu hỏi và
            câu trả lời đều nằm lại trên hồ sơ. Lời nhắn không đổi trạng thái và không dừng
            đồng hồ hạn xử lý.
          </p>
        </div>
        <KhungChat
          cacLoiNhan={ho_so.messages}
          bayGio={bayGio}
          phiaMinh="nguoi-gui"
          soan={
            <div style={{ padding: "4px 20px 17px" }}>
              <KhungLoiNhan
                key={ho_so.messages.length}
                maHoSo={ho_so.id}
                cacLoai={ho_so.message_kinds}
                daKetThuc={ho_so.state.is_terminal}
                hanhDong={guiLoiNhan}
              />
            </div>
          }
        />
      </div>

      <DongThoiGian
        cacSuKien={ho_so.history}
        bayGio={bayGio}
        khiTrong="Hồ sơ vừa được gửi và chưa đổi trạng thái lần nào. Mốc đầu tiên sẽ xuất hiện ở đây ngay khi điều phối viên tiếp nhận."
      />

    </>
  );
}
