"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Biểu mẫu gửi yêu cầu, chia ba bước.
//
// VÌ SAO CHIA BƯỚC thay vì một trang dài: biểu mẫu một trang khiến người dùng nhìn
// thấy cả chục ô cùng lúc và điền qua loa cho xong. Chia ba bước, mỗi bước hỏi đúng
// một chuyện, thì họ trả lời từng chuyện một. Chất lượng mô tả sự cố quyết định hồ sơ
// đi nhanh hay đi lòng vòng, nên vài giây thêm ở đây tiết kiệm vài giờ ở sau.
//
// BA Ô KHÔNG CÓ MẶT, và sự vắng mặt của chúng là cố ý:
//
//   mức ưu tiên  — ai cũng đánh dấu việc của mình là khẩn. Người phân loại đặt sau.
//   phòng ban    — người gửi không phải biết cơ cấu tổ chức. Hệ thống định tuyến.
//   người xử lý  — trưởng bộ phận phân công, không phải người gửi chỉ định.
//
// Đây là Poka-yoke bằng sự vắng mặt: không phải một câu cảnh báo “bạn không nên đặt
// mức ưu tiên”, mà đơn giản là **không có đường mà đi**. Lược đồ dữ liệu vào ở
// `backend/app/workflow/schemas.py` cũng không nhận ba trường đó, nên chặn ở giao
// diện rồi vẫn còn một lớp chặn nữa phía sau.

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useActionState, useRef, useState } from "react";

import { OTruongRieng } from "@/components/o-truong-rieng";
import { GoiYTuongTu } from "@/components/goi-y-tuong-tu";
import { OChonTep } from "@/components/o-chon-tep";
import { hienTruong } from "@/components/the-truong-rieng";
import { dungLuong } from "@/lib/dinh-dang";
import type { ChinhSachTep, LoaiYeuCau } from "@/lib/kieu";
import { CHUA_CO_LOI, type KetQuaThaoTac } from "@/app/yeu-cau/ket-qua";
import { guiYeuCau } from "@/app/yeu-cau/thao-tac";

const BUOC = [
  { so: 1, nhan: "Loại yêu cầu" },
  { so: 2, nhan: "Nội dung" },
  { so: 3, nhan: "Xem lại và gửi" },
];

/** Giá trị đại diện cho “chưa chọn loại nào”. Gửi lên thành `null`. */
const CHUA_RO = "";

/**
 * UUID phiên bản 4 cho phiên soạn (#319). Không dùng `crypto.randomUUID`: hàm đó chỉ có ở ngữ cảnh
 * bảo mật, mà cổng có thể được mở qua http bằng địa chỉ IP trong mạng nội bộ.
 */
function maPhienNgauNhien(): string {
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

/** Hồ sơ cũ mà biểu mẫu này tạo lại (#102): nội dung chép sẵn để người gửi sửa. */
export type HoSoGoc = {
  id: number;
  code: string;
  title: string;
  description: string;
  request_type_code: string | null;
};

export function BieuMauGuiYeuCau({
  cacLoai,
  goc,
  loaiSan,
  chinhSach,
}: {
  cacLoai: LoaiYeuCau[];
  goc: HoSoGoc | null;
  /** Mã loại lấy từ `?loai=` (#434). Mã không khớp danh mục thì bỏ qua, biểu mẫu mở ở bước 1. */
  loaiSan: string | null;
  /** Giới hạn tệp đính kèm do dịch vụ trả. Không nạp được thì ẩn ô chọn tệp (#80). */
  chinhSach: ChinhSachTep | null;
}) {
  const chuyenTrang = useRouter();
  // Tệp chọn ở bước 2 giữ trong `ref` song song với state: hành động gửi chạy sau lần dựng
  // cuối cùng và phải đọc được danh sách mới nhất, không phải bản chụp lúc nó được tạo
  const [tep, datTep] = useState<File[]>([]);
  const tepRef = useRef<File[]>([]);
  tepRef.current = tep;

  // Tạo hồ sơ trước, rồi tải tệp lên chính hồ sơ đó: tệp cần một hồ sơ đã tồn tại để gắn vào.
  // Tệp tải hỏng thì hồ sơ vẫn đã gửi — chuyển sang trang hồ sơ kèm lời nhắc thêm tệp lại ở
  // đó, thay vì báo lỗi ở biểu mẫu và khiến người gửi bấm gửi lần nữa, sinh ra hồ sơ thứ hai.
  const [ketQua, guiDi, dangGui] = useActionState(
    async (truoc: KetQuaThaoTac, duLieu: FormData): Promise<KetQuaThaoTac> => {
      const kq = await guiYeuCau(truoc, duLieu);
      if (kq.loi || kq.id === undefined) return kq;

      let tepLoi = false;
      if (tepRef.current.length > 0) {
        const bieuMau = new FormData();
        for (const f of tepRef.current) bieuMau.append("files", f);
        try {
          const ph = await fetch(`/api/tep/ho-so/${kq.id}`, { method: "POST", body: bieuMau });
          const than = (await ph.json().catch(() => null)) as { ok?: boolean } | null;
          tepLoi = !ph.ok || !than?.ok;
        } catch {
          tepLoi = true;
        }
      }
      chuyenTrang.push(`/yeu-cau/${kq.id}${tepLoi ? "?tep=loi" : ""}`);
      return kq;
    },
    CHUA_CO_LOI,
  );

  // Loại của hồ sơ cũ có thể đã ngừng dùng — khi đó để trống cho người gửi chọn lại
  const loaiCuaGoc =
    goc?.request_type_code && cacLoai.some((l) => l.code === goc.request_type_code)
      ? goc.request_type_code
      : null;
  // `?loai=` chỉ dùng khi không chép từ hồ sơ cũ và mã có trong danh mục: khi đó đã chọn xong
  // bước 1 nên mở thẳng bước 2. Mã lạ hay đã ngừng dùng thì như vào trang bình thường (#434)
  const loaiTuDuongDan =
    !goc && loaiSan && cacLoai.some((l) => l.code === loaiSan) ? loaiSan : null;
  const [buoc, datBuoc] = useState(loaiTuDuongDan ? 2 : 1);
  const [loai, datLoai] = useState<string | null>(loaiCuaGoc ?? loaiTuDuongDan);
  const [tieuDe, datTieuDe] = useState(goc?.title ?? "");
  const [moTa, datMoTa] = useState(goc?.description ?? "");
  // Giá trị trường riêng đang nhập ở bước 2 — chỉ để bước Xem lại liệt kê lại (#552); giá trị gửi đi vẫn nằm trong ô
  // ẩn của OTruongRieng
  const [chiTiet, datChiTiet] = useState<Record<string, string>>({});
  // Mã phiên soạn (#319): nối "đã xem gợi ý tương tự" với lần gửi này — không phải dữ liệu hồ sơ
  const [phienSoan] = useState(maPhienNgauNhien);

  const daChonLoai = loai !== null;
  const loaiDaChon = cacLoai.find((l) => l.code === loai);
  const duDeSang3 = tieuDe.trim().length >= 3;

  const theTiep = buoc === 1 ? daChonLoai : buoc === 2 ? duDeSang3 : true;

  return (
    <form action={guiDi}>
      {goc && (
        <p
          role="note"
          style={{
            margin: "18px 0 0",
            padding: "10px 12px",
            borderRadius: "9px",
            background: "var(--surface-2)",
            border: "1px solid var(--line)",
            fontSize: "13.5px",
            lineHeight: 1.55,
          }}
        >
          Tạo lại từ hồ sơ <strong>{goc.code}</strong>. Nội dung đã chép sẵn, hãy sửa cho rõ hơn
          trước khi gửi; hai hồ sơ sẽ nối với nhau.
        </p>
      )}
      {/* Dải bước */}
      <div
        style={{
          marginTop: "22px",
          display: "flex",
          flexWrap: "wrap",
          gap: "8px 6px",
          alignItems: "center",
        }}
      >
        {BUOC.map((b) => {
          const dang = buoc === b.so;
          const qua = buoc > b.so;
          return (
            <button
              key={b.so}
              type="button"
              onClick={() => datBuoc(b.so)}
              // Không cho nhảy tới bước chưa đủ điều kiện. Cho nhảy lùi thì thoải mái:
              // xem lại thứ mình vừa điền là chuyện bình thường.
              disabled={b.so > buoc && !theTiep}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "9px",
                padding: "8px 14px 8px 10px",
                borderRadius: "999px",
                fontSize: "13px",
                fontWeight: 600,
                whiteSpace: "nowrap",
                background: dang ? "var(--surface)" : "transparent",
                color: dang ? "var(--ink)" : qua ? "var(--ink-2)" : "var(--ink-3)",
                border: dang ? "1px solid var(--line)" : "1px solid transparent",
                boxShadow: dang ? "var(--shadow)" : "none",
              }}
            >
              <span
                className="mono"
                aria-hidden="true"
                style={{
                  width: "20px",
                  height: "20px",
                  borderRadius: "6px",
                  display: "grid",
                  placeItems: "center",
                  fontSize: "12px",
                  background: dang
                    ? "var(--accent)"
                    : qua
                      ? "var(--f-g-solid)"
                      : "var(--surface-3)",
                  color: dang
                    ? "var(--accent-on)"
                    : qua
                      ? "var(--f-g-on)"
                      : "var(--ink-3)",
                }}
              >
                {qua ? "✓" : b.so}
              </span>
              {b.nhan}
            </button>
          );
        })}
      </div>

      <div className="the" style={{ marginTop: "14px" }}>
        {/* Ba khối bước đều nằm sẵn trong biểu mẫu (ô của bước 2 phải gửi đi được từ bước 3) và ẩn bằng `hidden`.
            Khối mang `hidden` KHÔNG được đặt `display` trong `style`: kiểu nội tuyến thắng kiểu ẩn mặc định của trình
            duyệt, khối bị giấu vẫn hiện (#552 — bảng Xem lại từng hiện ở bước 1 và 2). Bố cục lưới đặt ở phần tử con. */}
        {/* --- Bước 1 · Loại yêu cầu ------------------------------------- */}
        <div hidden={buoc !== 1} data-buoc="1" style={{ padding: "22px" }}>
          <div style={{ fontSize: "15px", fontWeight: 600 }}>Loại yêu cầu</div>
          <p style={{ margin: "4px 0 0", fontSize: "13px", color: "var(--ink-3)" }}>
            Chọn một. Loại yêu cầu quyết định phòng ban tiếp nhận và thời hạn cam kết.
          </p>

          <div
            style={{
              marginTop: "16px",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit,minmax(238px,1fr))",
              gap: "12px",
            }}
          >
            {cacLoai.map((l) => (
              <TheLoai
                key={l.code}
                nhan={l.label}
                moTa={l.description ?? ""}
                phu={`Cam kết ${l.sla_hours} giờ làm việc`}
                chon={loai === l.code}
                onChon={() => {
                  datLoai(l.code);
                  datBuoc(2);
                }}
              />
            ))}
          </div>

          <button
            type="button"
            onClick={() => {
              datLoai(CHUA_RO);
              datBuoc(2);
            }}
            style={{
              marginTop: "14px",
              padding: "12px 14px",
              width: "100%",
              textAlign: "left",
              borderRadius: "11px",
              border:
                loai === CHUA_RO
                  ? "1.5px solid var(--accent)"
                  : "1px dashed var(--line-2)",
              background: loai === CHUA_RO ? "var(--accent-soft)" : "var(--surface-2)",
              fontSize: "13.5px",
              color: "var(--ink-2)",
              lineHeight: 1.55,
            }}
          >
            <strong style={{ fontWeight: 600, color: "var(--ink)" }}>
              Chưa rõ thuộc loại nào
            </strong>
            <br />
            Cứ gửi, điều phối viên sẽ phân loại giúp. Hồ sơ có thời hạn cam kết sau khi được
            phân loại.
          </button>
        </div>

        {/* --- Bước 2 · Nội dung ------------------------------------------ */}
        <div hidden={buoc !== 2} data-buoc="2">
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "10px",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "13px 22px",
              background: "var(--surface-2)",
              borderBottom: "1px solid var(--line)",
            }}
          >
            <span style={{ fontSize: "13px", color: "var(--ink-2)" }}>
              Loại yêu cầu ·{" "}
              <strong style={{ fontWeight: 600, color: "var(--ink)" }}>
                {loaiDaChon?.label ?? "Chưa rõ, để điều phối viên phân loại"}
              </strong>
            </span>
            <button
              type="button"
              className="nut nut-nho"
              onClick={() => datBuoc(1)}
            >
              Đổi loại
            </button>
          </div>

          <div style={{ padding: "22px", display: "grid", gap: "20px" }}>
            <label style={{ display: "grid", gap: "7px" }}>
              <span
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "8px",
                  alignItems: "baseline",
                  justifyContent: "space-between",
                }}
              >
                <span style={{ fontSize: "13.5px", fontWeight: 600 }}>
                  Tiêu đề ngắn
                </span>
                <span className="mono nhat" style={{ fontSize: "12px" }}>
                  {tieuDe.length}/200
                </span>
              </span>
              <input
                name="title"
                type="text"
                className="o-nhap"
                maxLength={200}
                value={tieuDe}
                onChange={(e) => datTieuDe(e.target.value)}
                placeholder="Máy in phòng kế toán kẹt giấy liên tục"
              />
              <span style={{ fontSize: "12px", color: "var(--ink-3)" }}>
                Một câu nói rõ chuyện gì xảy ra, đừng chỉ ghi “lỗi” hay “cần hỗ trợ”.
              </span>
            </label>

            <label style={{ display: "grid", gap: "7px" }}>
              <span style={{ fontSize: "13.5px", fontWeight: 600 }}>Mô tả chi tiết</span>
              <textarea
                name="description"
                className="o-nhap"
                rows={6}
                maxLength={5000}
                value={moTa}
                onChange={(e) => datMoTa(e.target.value)}
                placeholder="Máy in ở góc phòng Kế toán kẹt giấy khoảng 3 lần mỗi ngày, bắt đầu từ thứ Năm tuần trước. Đã thử rút khay giấy và thay giấy mới nhưng không đỡ."
              />
              <span style={{ fontSize: "12px", color: "var(--ink-3)" }}>
                Ghi chuyện gì xảy ra, từ khi nào, ở đâu hoặc thiết bị nào, và bạn đã thử gì.
                Đủ bốn điều này thì phòng ban không phải hỏi lại.
              </span>
            </label>

            {/* Hồ sơ đã giải quyết tương tự (#319): hiện khi có, không hiện gì khi mô hình tắt hay
                chậm — không bao giờ giữ chân người gửi */}
            <GoiYTuongTu tieuDe={tieuDe} moTa={moTa} phien={phienSoan} />

            {/* Trường riêng của loại đã chọn ở bước 1 (#250), dựng từ khai báo của dịch vụ.
                `key` theo loại: đổi loại thì bộ ô dựng lại từ đầu, không mang giá trị loại cũ. */}
            <OTruongRieng key={loai ?? ""} ten="details" cacTruong={loaiDaChon?.fields ?? []} khiDoi={datChiTiet} />

            {/* Tệp đính kèm (#80): ảnh chụp màn hình gần như luôn có ích — không có thì người
                xử lý phải hỏi lại và hồ sơ rơi vào chờ bổ sung. Giới hạn do dịch vụ trả. */}
            {chinhSach && (
              <div style={{ display: "grid", gap: "7px" }}>
                <span style={{ fontSize: "13.5px", fontWeight: 600 }}>
                  Tệp đính kèm{" "}
                  <span style={{ fontWeight: 400, color: "var(--ink-3)" }}>— không bắt buộc</span>
                </span>
                <OChonTep chinhSach={chinhSach} tepDaChon={tep} doi={datTep} voHieu={dangGui} />
              </div>
            )}
          </div>
        </div>

        {/* --- Bước 3 · Xem lại ------------------------------------------- */}
        <div hidden={buoc !== 3} data-buoc="3" style={{ padding: "22px" }}>
          <div
            style={{
              display: "grid",
              gap: "1px",
              border: "1px solid var(--line)",
              borderRadius: "11px",
              overflow: "hidden",
              background: "var(--line)",
            }}
          >
            <MucXemLai
              khoa="Loại yêu cầu"
              gia_tri={loaiDaChon?.label ?? "Chưa rõ — điều phối viên sẽ phân loại"}
            />
            <MucXemLai
              khoa="Thời hạn cam kết"
              gia_tri={
                loaiDaChon
                  ? `${loaiDaChon.sla_hours} giờ làm việc kể từ lúc phòng ban bắt đầu xử lý`
                  : "Chưa xác định cho tới khi hồ sơ được phân loại"
              }
            />
            <MucXemLai khoa="Tiêu đề" gia_tri={tieuDe || "—"} />
            <MucXemLai khoa="Mô tả" gia_tri={moTa || "Bạn chưa điền mô tả"} />
            {/* Trường riêng đã điền, nhãn và cách hiện giá trị theo khai báo của loại — cùng nguồn ô ở bước 2 và khối
                thông tin riêng trên trang hồ sơ; ô bỏ trống thì không liệt kê */}
            {(loaiDaChon?.fields ?? [])
              .filter((t) => chiTiet[t.code]?.trim())
              .map((t) => {
                const v = chiTiet[t.code].trim();
                const so = Number(v);
                return (
                  <MucXemLai
                    key={t.code}
                    khoa={t.label}
                    gia_tri={hienTruong(t, t.kind === "number" && Number.isFinite(so) ? so : v)}
                  />
                );
              })}
            {chinhSach && (
              <MucXemLai
                khoa="Tệp đính kèm"
                gia_tri={
                  tep.length > 0
                    ? tep.map((f) => `${f.name} (${dungLuong(f.size)})`).join("\n")
                    : "Không có tệp đính kèm"
                }
              />
            )}
          </div>
        </div>

        {/* --- Chân biểu mẫu ---------------------------------------------- */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "10px",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "15px 22px",
            background: "var(--surface-2)",
            borderTop: "1px solid var(--line)",
          }}
        >
          {buoc > 1 ? (
            <button type="button" className="nut" onClick={() => datBuoc(buoc - 1)}>
              ← Quay lại
            </button>
          ) : (
            <Link href="/yeu-cau" className="nut">
              ← Hồ sơ của tôi
            </Link>
          )}

          {/* Hai nút cùng chỗ phải mang `key` riêng (#188): không có key, React dùng lại một
              phần tử và đổi nó thành `submit` ngay trong cú bấm "Tiếp tục", nên trình duyệt
              gửi biểu mẫu và bỏ qua bước Xem lại. `preventDefault` là lớp chặn thứ hai. */}
          {buoc < 3 ? (
            <button
              key="tiep-tuc"
              type="button"
              className="nut"
              data-loai="chinh"
              disabled={!theTiep}
              onClick={(e) => {
                e.preventDefault();
                datBuoc(buoc + 1);
              }}
            >
              Tiếp tục →
            </button>
          ) : (
            <button
              key="gui"
              type="submit"
              className="nut"
              data-loai="chinh"
              disabled={dangGui || !duDeSang3}
            >
              {dangGui ? "Đang gửi…" : "Gửi yêu cầu"}
            </button>
          )}
        </div>
      </div>

      {/* Loại yêu cầu đi kèm biểu mẫu dưới dạng trường ẩn, vì nó do các thẻ bấm ở
          bước 1 quyết định chứ không phải một ô nhập. */}
      <input type="hidden" name="request_type_code" value={loai ?? CHUA_RO} />
      {goc && <input type="hidden" name="parent_request_id" value={goc.id} />}
      <input type="hidden" name="similar_session_id" value={phienSoan} />

      {ketQua.loi && (
        <p
          role="alert"
          style={{
            ...{ ["--ho-bg" as string]: "var(--f-r-bg)" },
            marginTop: "16px",
            padding: "13px 15px",
            borderRadius: "11px",
            background: "var(--f-r-bg)",
            border: "1px solid var(--f-r-line)",
            color: "var(--f-r-ink)",
            fontSize: "13.5px",
            lineHeight: 1.6,
          }}
        >
          {ketQua.loi}
        </p>
      )}
    </form>
  );
}

function TheLoai({
  nhan,
  moTa,
  phu,
  chon,
  onChon,
}: {
  nhan: string;
  moTa: string;
  phu: string;
  chon: boolean;
  onChon: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onChon}
      style={{
        padding: "15px",
        borderRadius: "12px",
        textAlign: "left",
        background: chon ? "var(--accent-soft)" : "var(--surface)",
        border: chon ? "1.5px solid var(--accent)" : "1px solid var(--line-2)",
      }}
    >
      <span style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
        <span
          aria-hidden="true"
          style={{
            flex: "0 0 auto",
            marginTop: "3px",
            width: "16px",
            height: "16px",
            borderRadius: "50%",
            border: chon ? "5px solid var(--accent)" : "1.5px solid var(--line-2)",
            background: "var(--surface)",
          }}
        />
        <span style={{ display: "grid", gap: "5px" }}>
          <span style={{ fontSize: "14.5px", fontWeight: 600, lineHeight: 1.35 }}>
            {nhan}
          </span>
          {moTa && (
            <span
              style={{ fontSize: "12.5px", color: "var(--ink-2)", lineHeight: 1.55 }}
            >
              {moTa}
            </span>
          )}
          <span className="mono" style={{ fontSize: "12px", color: "var(--ink-3)" }}>
            {phu}
          </span>
        </span>
      </span>
    </button>
  );
}

function MucXemLai({ khoa, gia_tri }: { khoa: string; gia_tri: string }) {
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "4px 18px",
        padding: "12px 15px",
        background: "var(--surface)",
      }}
    >
      <span
        style={{
          flex: "0 0 150px",
          fontSize: "12.5px",
          color: "var(--ink-3)",
          paddingTop: "2px",
        }}
      >
        {khoa}
      </span>
      <span
        style={{
          flex: "1 1 240px",
          minWidth: 0,
          fontSize: "13.5px",
          lineHeight: 1.6,
          whiteSpace: "pre-wrap",
        }}
      >
        {gia_tri}
      </span>
    </div>
  );
}
