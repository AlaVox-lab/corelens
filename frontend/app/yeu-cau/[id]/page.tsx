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
//
// Bố cục (#561): đầu trang gọn, một dải ba ô số, dải trạng thái trọn bề ngang, rồi hai cột — chính: nội dung,
// trao đổi, dòng thời gian; phụ: thao tác, tệp đính kèm, hồ sơ liên quan. Số lần đổi trạng thái không còn ô
// riêng: đầu dòng thời gian đã ghi số mốc và số lần quay lui.

import { MessagesSquare } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { TheTruongRieng } from "@/components/the-truong-rieng";
import type { NguonLuaChon } from "@/components/bang-thao-tac";
import { ChamLoai } from "@/components/cham-loai";
import { DongThoiGian } from "@/components/dong-thoi-gian";
import { NhanTrangThai } from "@/components/nhan-trang-thai";
import { ThaoTacHoSo } from "@/app/yeu-cau/[id]/thao-tac-ho-so";
import { guiLoiNhan } from "@/app/yeu-cau/thao-tac";
import { DanhDauDaDoc } from "@/components/danh-dau-da-doc";
import { GhiChuMoLai, KhoiHoSoLienQuan, MoiTaoHoSoMoi } from "@/components/ho-so-lien-quan";
import { KhoiTepDinhKem } from "@/components/khoi-tep-dinh-kem";
import { TheDanhGia } from "@/components/the-danh-gia";
import { CuonTinMoi } from "@/components/cuon-tin-moi";
import { KhungChat } from "@/components/khung-chat";
import { KhungLoiNhan } from "@/components/khung-loi-nhan";
import { NutThanhDau, TenCapCon } from "@/components/khung-ung-dung";
import { KhongPhanHoi, MoiDangNhap } from "@/components/khung-lam-viec";
import { docDichVu, goiDichVu, laHetPhien } from "@/lib/api";
import { ngayGio } from "@/lib/dinh-dang";
import type { ChinhSachTep, HoSoChiTiet, LoaiYeuCau, NhanCoMa } from "@/lib/kieu";
import { daTroiQua, docDongHo, docTuDong } from "@/lib/sla";
import { CHU_GIAI_NHOM, bienHoMau, chuGiaiKetThuc, trinhBayTrangThai } from "@/lib/trang-thai";
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
  // Kết thúc hay chưa tra cờ `is_terminal` của dữ liệu, không tra bảng trình bày (#557)
  const nhomChuGiai = ho_so.state.is_terminal
    ? chuGiaiKetThuc(ho_so.state.label, ho_so.allowed_transitions.length > 0)
    : CHU_GIAI_NHOM.find((n) => n.nhom === kieu.nhom);

  return (
    <>
      {/* Đường dẫn đầu trang ghi mã hồ sơ, như buồng lái: "Hồ sơ của tôi › YC-…" (#557) */}
      <TenCapCon ten={ho_so.code} />
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

      {/* --- Đầu trang (#561): mã, loại, lúc gửi, tiêu đề; nhãn trạng thái bên phải ---------- */}
      <div className="dau-ho-so dau-ho-so-ng">
        <div className="trai">
          <div className="dong-ma">
            <span className="mono">{ho_so.code}</span>
            {ho_so.request_type && (
              <span className="chip-loai">
                <ChamLoai ma={ho_so.request_type.code} />
                {ho_so.request_type.label}
              </span>
            )}
            <span>Gửi lúc {ngayGio(ho_so.created_at)}</span>
          </div>
          <h1 className="h1-ho-so">{ho_so.title}</h1>
        </div>
        <NhanTrangThai ma={ho_so.state.code} nhan={ho_so.state.label} to />
      </div>

      {/* --- Dải số (#561): ba ô một hàng thay bốn ô cao. Ô thời gian giữ tên và câu của #559: "Đã trôi qua" tính
          giờ đồng hồ, câu đồng hồ hạn tính giờ làm việc nằm ở ô "Hạn xử lý" bên cạnh ------------------------------- */}
      <dl className="dai-so-ho-so">
        {/* Cố ý KHÔNG hiện `assignee_id`. Nó là định danh `sub` của Keycloak — một chuỗi UUID — và
            dịch vụ chưa có đường tra ngược ra tên người cho người gửi. Hồ sơ đã kết thúc thì không còn ai
            "đang giữ" — nói phòng đã phụ trách (#557) */}
        <div>
          <dt className="tua-muc">{ho_so.state.is_terminal ? "Phòng ban phụ trách" : "Đang giữ hồ sơ"}</dt>
          <dd>{ho_so.department?.label ?? "Chưa chuyển về phòng nào"}</dd>
          <dd className="dai-so-ho-so-phu">
            {ho_so.state.is_terminal
              ? "Hồ sơ đã kết thúc, không còn ai giữ"
              : ho_so.assignee_id
                ? "Đã có người được phân công xử lý"
                : "Chưa phân công người xử lý cụ thể"}
          </dd>
        </div>
        <div>
          <dt className="tua-muc">Đã trôi qua</dt>
          <dd>{daTroiQua(ho_so, bayGio)}</dd>
        </div>
        <div>
          <dt className="tua-muc">Hạn xử lý</dt>
          <dd data-canh-bao={dongHo.canhBao ? "" : undefined}>{dongHo.cau}</dd>
        </div>
      </dl>

      {/* --- Dải trạng thái trọn bề ngang (#561): câu của nhóm trạng thái, kèm lúc hệ thống sẽ tự đi ------------- */}
      {nhomChuGiai && (
        <div className="dai-chu-giai" style={bienHoMau(kieu.ho)}>
          <span aria-hidden="true" className="dai-chu-giai-dau">
            {kieu.dau}
          </span>
          <span className="dai-chu-giai-chu">
            <strong>{nhomChuGiai.tieuDe}</strong>
            <span>{nhomChuGiai.moTa}</span>
            {tuDong && <span data-sap={tuDong.canhBao ? "" : undefined}>{tuDong.cau}</span>}
          </span>
        </div>
      )}

      {/* --- Hai cột (#561). Cột phụ — thao tác, tệp, hồ sơ liên quan — đứng TRƯỚC cột chính trong mã: điện
          thoại và trình đọc màn hình gặp việc của người gửi trước nhật ký (#189); màn rộng đặt nó sang phải bằng
          `grid-template-areas` --------------------------------------------------------------------------- */}
      <div className="hai-cot-ng trang-ho-so">
        <div className="cot-phu">
          <section id="thao-tac" className="the khong-in the-thao-tac-ng" aria-labelledby="tua-thao-tac-ng">
            <h2 className="tua-the-ng" id="tua-thao-tac-ng">
              Bạn có thể làm gì lúc này
            </h2>
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
              nhanXetToiDa={ho_so.feedback_comment_max_chars}
              truongRieng={
                cacLoaiDayDu
                  ? { giaTri: ho_so.details ?? {}, loaiDau: ho_so.request_type?.code ?? null, cacLoai: cacLoaiDayDu }
                  : undefined
              }
            />
            <GhiChuMoLai hoSo={ho_so} />
          </section>
          {/* Điểm hài lòng mình đã chấm (#433); chưa chấm lần nào thì không có khối */}
          {(ho_so.feedback?.length ?? 0) > 0 && <TheDanhGia danhGia={ho_so.feedback} cuaToi />}
          {/* Biểu mẫu gửi đã tạo hồ sơ nhưng tải tệp lên hỏng (#80): nói rõ hồ sơ ĐÃ gửi, để
              người gửi không bấm gửi lần nữa và sinh hồ sơ thứ hai */}
          {tepLoi === "loi" && (
            <p role="alert" className="bao-tep-loi">
              Hồ sơ đã được gửi, nhưng tệp đính kèm chưa tải lên được. Thêm lại tệp ở khối “Tệp đính
              kèm” — đừng gửi hồ sơ mới.
            </p>
          )}
          <KhoiTepDinhKem
            maHoSo={ho_so.id}
            tep={ho_so.attachments}
            choPhep={ho_so.can_attach}
            chinhSach={chinhSachTep}
          />
          {/* Hết đường mở lại thì mời tạo hồ sơ mới; hồ sơ nối nhau thì liệt kê (#102) */}
          <MoiTaoHoSoMoi hoSo={ho_so} />
          <KhoiHoSoLienQuan hoSo={ho_so} lienKet={(id) => `/yeu-cau/${id}`} />
        </div>

        <div className="cot-chinh">
          {(ho_so.description || (ho_so.detail_fields?.length ?? 0) > 0) && (
            <section className="the khoi-ng" aria-labelledby="tua-noi-dung">
              <h2 className="tua-the-ng" id="tua-noi-dung">
                Nội dung yêu cầu
              </h2>
              <TheTruongRieng cacTruong={ho_so.detail_fields ?? []} giaTri={ho_so.details ?? {}} />
              {ho_so.description ? <p className="mo-ta-ng">{ho_so.description}</p> : null}
            </section>
          )}

          {/* --- Lời nhắn (#128) — khung trò chuyện riêng, như thẻ Trao đổi phía nhân viên
              (#169): dòng thời gian thu gọn (#189) không được giấu mất tin nhắn ---------- */}
          <div id="khung-loi-nhan" className="the khong-in">
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
        </div>
      </div>
    </>
  );
}
