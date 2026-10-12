// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn “Hồ sơ của tôi”.
//
// Câu hỏi mà màn này phải trả lời trong hai giây đầu: **có hồ sơ nào đang chờ tôi
// không?** Mọi thứ khác đứng sau câu đó.
//
// Vì vậy những hồ sơ đang chờ người dùng được đánh dấu ba lần, không phải một:
//
//   1. Một dải nhắc ngay đầu trang, đếm số hồ sơ
//   2. Nhãn trạng thái tô nền đậm thay vì chỉ có viền
//   3. Một dòng gợi ý việc cần làm ngay dưới tiêu đề hồ sơ
//
// Ba lần là cố ý. Một người mở trang này giữa lúc bận sẽ lướt qua rất nhanh, và thứ
// họ bỏ lỡ sẽ nằm đó thêm vài ngày — trong khi đồng hồ SLA của hệ thống thì dừng, nên
// không ai bị nhắc cả. Đó là kiểu tắc nghẽn không hiện lên trong báo cáo nào.
//
// Câu hỏi thứ hai — **hồ sơ này đang ở đâu** — trả lời ngay trên dòng của nó (#192): rê,
// Tab hay chạm vào nhãn trạng thái thì hiện sơ đồ nhỏ của đường chính. Bảng giải thích
// mười trạng thái từng nằm cuối trang đã bỏ: không ai đọc nó để biết hồ sơ của mình ở đâu.

import Link from "next/link";

import { DauLoiNhan } from "@/components/dau-loi-nhan";
import { XemNhanhTrangThai } from "@/components/xem-nhanh-trang-thai";
import { goiDichVu } from "@/lib/api";
import { type Buoc, cacBuoc, duongChinh } from "@/lib/buoc";
import { khoangCach, ngayGio } from "@/lib/dinh-dang";
import type { HoSoChiTiet, HoSoTomTat, SuKien, TrangThai } from "@/lib/kieu";
import { docDongHo, docTuDong } from "@/lib/sla";
import { bienHoMau, dangChoNguoiDung, viecCuaBan } from "@/lib/trang-thai";

export const dynamic = "force-dynamic";

function Trong() {
  return (
    <div className="the" style={{ padding: "44px 24px", textAlign: "center" }}>
      <p style={{ margin: 0, fontSize: "15px", fontWeight: 600 }}>
        Bạn chưa gửi yêu cầu nào
      </p>
      <p
        style={{
          margin: "7px 0 20px",
          fontSize: "13.5px",
          color: "var(--ink-2)",
          lineHeight: 1.6,
        }}
      >
        Mọi yêu cầu nội bộ — sự cố thiết bị, cấp quyền phần mềm, giấy tờ nhân sự, đề
        xuất mua sắm — đều gửi từ một chỗ duy nhất.
      </p>
      <Link href="/yeu-cau/moi" className="nut" data-loai="chinh">
        Gửi yêu cầu đầu tiên
      </Link>
    </div>
  );
}

function DaiNhac({ so }: { so: number }) {
  return (
    <div
      style={{
        ...bienHoMau("a"),
        marginTop: "18px",
        display: "flex",
        flexWrap: "wrap",
        gap: "12px 18px",
        alignItems: "center",
        padding: "14px 16px",
        borderRadius: "12px",
        background: "var(--ho-bg)",
        border: "1px solid var(--ho-line)",
      }}
    >
      <span
        aria-hidden="true"
        style={{
          flex: "0 0 auto",
          width: "22px",
          height: "22px",
          borderRadius: "50%",
          background: "var(--ho-solid)",
          color: "var(--ho-on)",
          display: "grid",
          placeItems: "center",
          fontSize: "13px",
          fontWeight: 700,
          lineHeight: 1,
        }}
      >
        !
      </span>
      <span style={{ display: "grid", gap: "3px", minWidth: 0 }}>
        <span style={{ fontSize: "14px", fontWeight: 600, color: "var(--ho-ink)" }}>
          {so} hồ sơ đang chờ bạn
        </span>
        <span style={{ fontSize: "13px", color: "var(--ink-2)", lineHeight: 1.55 }}>
          Hồ sơ dừng lại cho tới khi bạn trả lời hoặc xác nhận.
        </span>
      </span>
    </div>
  );
}

type ViTri = { buoc: Buoc[] | null; dong: string | null };

/**
 * Hồ sơ đang ở đâu trên đường chính, cho sơ đồ xem nhanh (#192).
 *
 * Trạng thái nằm trên đường chính thì tự nó là vị trí. Trạng thái nhánh chưa kết thúc —
 * chờ bổ sung, bị trả lại, leo thang — cần lịch sử để biết hồ sơ dừng ở bước nào, nên
 * trang tải thêm chi tiết của riêng những hồ sơ đó (`lichSu`). Trạng thái kết thúc ngoài
 * đường chính (đã hủy) không tô bước nào và không tải gì: hồ sơ cũ dồn nhiều lên theo thời
 * gian, mà câu trả lời chỉ cần một dòng.
 */
function tinhViTri(
  ho_so: HoSoTomTat,
  cacTrangThai: TrangThai[],
  lichSu: SuKien[] | null | undefined,
): ViTri {
  const tt = ho_so.state;
  if (cacTrangThai.length === 0) return { buoc: null, dong: null };
  if (duongChinh(cacTrangThai).some((t) => t.code === tt.code)) {
    return { buoc: cacBuoc(cacTrangThai, tt.code, []), dong: null };
  }
  const moDau = tt.is_terminal ? "Đã kết thúc ở" : "Đang dừng ở";
  const dong = `${moDau}: ${tt.label} — ${viecCuaBan(tt.code)}`;
  if (tt.is_terminal || !lichSu) return { buoc: null, dong };
  return { buoc: cacBuoc(cacTrangThai, tt.code, lichSu), dong };
}

function Dong({ ho_so, bayGio, viTri }: { ho_so: HoSoTomTat; bayGio: Date; viTri: ViTri }) {
  const choBan = dangChoNguoiDung(ho_so.state.code);
  // Ngày làm việc cuối trước khi hồ sơ tự đóng (#144): câu đó thay câu đồng hồ, tô cam
  const tuDong = docTuDong(ho_so);
  const dongHo = tuDong?.canhBao ? tuDong : docDongHo(ho_so, "nguoi-gui");

  return (
    <div
      className="dong-hs"
      style={{
        position: "relative",
        display: "flex",
        flexWrap: "wrap",
        gap: "10px 14px",
        padding: "14px 16px",
        borderTop: "1px solid var(--line)",
      }}
    >
      {/* Liên kết trong suốt phủ kín dòng như bảng hàng đợi (#170): bấm đâu trên dòng cũng
          mở hồ sơ, trừ nhãn trạng thái — nút đó nằm trên liên kết và mở sơ đồ xem nhanh.
          Không bọc cả dòng trong <a> như trước: nút bên trong liên kết là HTML sai. */}
      <Link
        href={`/yeu-cau/${ho_so.id}`}
        className="lk-dong"
        aria-label={`${ho_so.code} · ${ho_so.title}`}
      />
      <span style={{ flex: "1 1 260px", minWidth: 0, display: "grid", gap: "4px" }}>
        <span
          className="mono"
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "4px 10px",
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
                padding: "1px 7px",
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
          <DauLoiNhan hoSo={ho_so} gocNhin="nguoi-gui" />
        </span>
        <span style={{ fontSize: "14.5px", fontWeight: 600, lineHeight: 1.4 }}>
          {ho_so.title}
        </span>
        <span
          style={{
            fontSize: "12.5px",
            lineHeight: 1.5,
            color:
              dongHo === tuDong
                ? "var(--f-a-ink)"
                : dongHo.canhBao
                  ? "var(--f-r-ink)"
                  : "var(--ink-3)",
            fontWeight: dongHo === tuDong ? 600 : undefined,
          }}
        >
          {dongHo.cau}
        </span>
      </span>

      {/* Lời nhắc "Cần bạn xử lý" nằm DƯỚI nhãn trạng thái, trong cùng cột. Để nó thành
          một ô riêng ở cuối dòng thì dòng đó có năm ô trong khi tiêu đề bảng có bốn —
          cột tiêu đề co lại và mọi cột sau lệch khỏi tiêu đề (#97). */}
      <span
        style={{
          flex: "0 0 190px",
          display: "grid",
          gap: "6px",
          alignContent: "center",
          justifyItems: "start",
        }}
      >
        <XemNhanhTrangThai
          ma={ho_so.state.code}
          nhan={ho_so.state.label}
          buoc={viTri.buoc}
          dong={viTri.dong}
        />
        {choBan && (
          <span style={{ fontSize: "12.5px", fontWeight: 600, color: "var(--f-a-ink)" }}>
            Cần bạn xử lý →
          </span>
        )}
      </span>

      <span
        style={{
          flex: "0 0 130px",
          fontSize: "13px",
          color: ho_so.department ? "var(--ink-2)" : "var(--ink-3)",
        }}
      >
        {ho_so.department?.label ?? "Chưa định tuyến"}
      </span>

      <span style={{ flex: "0 0 96px", display: "grid", gap: "2px" }}>
        <span className="mono" style={{ fontSize: "12.5px", color: "var(--ink-2)" }}>
          {ngayGio(ho_so.created_at)}
        </span>
        <span style={{ fontSize: "12px", color: "var(--ink-3)" }}>
          {khoangCach(ho_so.created_at, bayGio)}
        </span>
      </span>
    </div>
  );
}

export default async function HoSoCuaToi() {
  const [danhSach, danhMucTrangThai] = await Promise.all([
    goiDichVu<HoSoTomTat[]>("/requests"),
    goiDichVu<TrangThai[]>("/states"),
  ]);

  const cacHoSo = danhSach ?? [];
  const cacTrangThai = danhMucTrangThai ?? [];
  const bayGio = new Date();

  // Lịch sử chỉ cần cho hồ sơ đang ở nhánh phụ chưa kết thúc — thường không quá vài hồ sơ
  const duong = new Set(duongChinh(cacTrangThai).map((t) => t.code));
  const canLichSu = cacHoSo.filter(
    (h) => cacTrangThai.length > 0 && !duong.has(h.state.code) && !h.state.is_terminal,
  );
  const chiTiet = await Promise.all(
    canLichSu.map((h) => goiDichVu<HoSoChiTiet>(`/requests/${h.id}`)),
  );
  const lichSu = new Map(canLichSu.map((h, i) => [h.id, chiTiet[i]?.history]));
  const soChoBan = cacHoSo.filter((h) => dangChoNguoiDung(h.state.code)).length;

  return (
    <>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "12px 20px",
          alignItems: "flex-end",
          justifyContent: "space-between",
        }}
      >
        <div>
          <h1
            style={{
              margin: 0,
              fontSize: "clamp(22px,3.4vw,28px)",
              fontWeight: 600,
              letterSpacing: "-.02em",
              lineHeight: 1.25,
            }}
          >
            Hồ sơ của tôi
          </h1>
          <p style={{ margin: "7px 0 0", fontSize: "14.5px", color: "var(--ink-2)" }}>
            {cacHoSo.length > 0
              ? `${cacHoSo.length} yêu cầu bạn đã gửi. Rê hoặc chạm vào nhãn trạng thái để xem nhanh hồ sơ đang ở bước nào; bấm vào dòng để mở hồ sơ.`
              : "Nơi theo dõi mọi yêu cầu bạn đã gửi."}
          </p>
        </div>
        <Link href="/yeu-cau/moi" className="nut khong-in" data-loai="chinh">
          Gửi yêu cầu mới
        </Link>
      </div>

      {soChoBan > 0 && <DaiNhac so={soChoBan} />}

      <div style={{ marginTop: "18px" }}>
        {cacHoSo.length === 0 ? (
          <Trong />
        ) : (
          <div className="the">
            <div
              className="tua-muc hang-tieu-de"
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "10px 14px",
                padding: "10px 16px",
                background: "var(--surface-2)",
              }}
            >
              <span style={{ flex: "1 1 260px", minWidth: 0 }}>Yêu cầu</span>
              <span style={{ flex: "0 0 190px" }}>Trạng thái</span>
              <span style={{ flex: "0 0 130px" }}>Đang giữ</span>
              <span style={{ flex: "0 0 96px" }}>Đã gửi</span>
            </div>
            {cacHoSo.map((h) => (
              <Dong
                key={h.id}
                ho_so={h}
                bayGio={bayGio}
                viTri={tinhViTri(h, cacTrangThai, lichSu.get(h.id))}
              />
            ))}
          </div>
        )}
      </div>
    </>
  );
}
