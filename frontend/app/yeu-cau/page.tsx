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

import Link from "next/link";

import { DauLoiNhan } from "@/components/dau-loi-nhan";
import { NhanTrangThai } from "@/components/nhan-trang-thai";
import { goiDichVu } from "@/lib/api";
import { khoangCach, ngayGio } from "@/lib/dinh-dang";
import type { HoSoTomTat, TrangThai } from "@/lib/kieu";
import { docDongHo } from "@/lib/sla";
import {
  CHU_GIAI_NHOM,
  bienHoMau,
  dangChoNguoiDung,
  trinhBayTrangThai,
} from "@/lib/trang-thai";

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
          Hồ sơ dừng lại cho tới khi bạn trả lời hoặc xác nhận. Không ai xử lý tiếp
          thay bạn được.
        </span>
      </span>
    </div>
  );
}

function Dong({ ho_so, bayGio }: { ho_so: HoSoTomTat; bayGio: Date }) {
  const choBan = dangChoNguoiDung(ho_so.state.code);
  const dongHo = docDongHo(ho_so, "nguoi-gui");

  return (
    <Link
      href={`/yeu-cau/${ho_so.id}`}
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "10px 14px",
        padding: "14px 16px",
        borderTop: "1px solid var(--line)",
        color: "inherit",
        textDecoration: "none",
      }}
    >
      <span style={{ flex: "1 1 260px", minWidth: 0, display: "grid", gap: "4px" }}>
        <span
          className="mono"
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "4px 10px",
            alignItems: "center",
            fontSize: "11.5px",
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
                fontSize: "11px",
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
            color: dongHo.canhBao ? "var(--f-r-ink)" : "var(--ink-3)",
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
        <NhanTrangThai ma={ho_so.state.code} nhan={ho_so.state.label} />
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
        <span style={{ fontSize: "11.5px", color: "var(--ink-3)" }}>
          {khoangCach(ho_so.created_at, bayGio)}
        </span>
      </span>

    </Link>
  );
}

function ChuGiai({ cacTrangThai }: { cacTrangThai: TrangThai[] }) {
  return (
    <section className="the" style={{ marginTop: "26px" }}>
      <div style={{ padding: "15px 17px", borderBottom: "1px solid var(--line)" }}>
        <h2 style={{ margin: 0, fontSize: "15px", fontWeight: 600 }}>
          {cacTrangThai.length} trạng thái của hệ thống
        </h2>
        <p
          style={{
            margin: "4px 0 0",
            fontSize: "13px",
            color: "var(--ink-2)",
            lineHeight: 1.6,
            maxWidth: "70ch",
          }}
        >
          Mỗi trạng thái có một dấu hiệu riêng đặt trước nhãn, nên vẫn phân biệt được
          khi in đen trắng hoặc khi người đọc không phân biệt được màu.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit,minmax(248px,1fr))",
          gap: "1px",
          background: "var(--line)",
        }}
      >
        {CHU_GIAI_NHOM.map((nhom) => {
          const thuoc = cacTrangThai.filter(
            (t) => trinhBayTrangThai(t.code).nhom === nhom.nhom,
          );
          if (thuoc.length === 0) return null;

          return (
            <div
              key={nhom.nhom}
              style={{
                padding: "15px 17px",
                background: "var(--surface)",
                display: "grid",
                gap: "11px",
                alignContent: "start",
              }}
            >
              <span style={{ display: "grid", gap: "4px" }}>
                <span style={{ fontSize: "13.5px", fontWeight: 600 }}>
                  {nhom.tieuDe}
                </span>
                <span
                  style={{ fontSize: "12px", color: "var(--ink-3)", lineHeight: 1.55 }}
                >
                  {nhom.moTa}
                </span>
              </span>
              <span style={{ display: "flex", flexWrap: "wrap", gap: "7px" }}>
                {thuoc.map((t) => (
                  <NhanTrangThai key={t.code} ma={t.code} nhan={t.label} />
                ))}
              </span>
            </div>
          );
        })}
      </div>

      <p
        style={{
          margin: 0,
          padding: "13px 17px",
          borderTop: "1px solid var(--line)",
          background: "var(--surface-2)",
          fontSize: "12.5px",
          color: "var(--ink-3)",
        }}
      >
        Nhãn nền đậm = hồ sơ đang chờ bạn. Nhãn viền = hệ thống hoặc phòng ban đang giữ.
      </p>
    </section>
  );
}

export default async function HoSoCuaToi() {
  const [danhSach, danhMucTrangThai] = await Promise.all([
    goiDichVu<HoSoTomTat[]>("/requests"),
    goiDichVu<TrangThai[]>("/states"),
  ]);

  const cacHoSo = danhSach ?? [];
  const bayGio = new Date();
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
              ? `${cacHoSo.length} yêu cầu bạn đã gửi. Bấm một dòng để xem toàn bộ đường đi của hồ sơ.`
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
              <Dong key={h.id} ho_so={h} bayGio={bayGio} />
            ))}
          </div>
        )}
      </div>

      {danhMucTrangThai && danhMucTrangThai.length > 0 && (
        <ChuGiai cacTrangThai={danhMucTrangThai} />
      )}
    </>
  );
}
