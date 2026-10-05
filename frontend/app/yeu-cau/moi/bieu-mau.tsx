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
import { useActionState, useState } from "react";

import type { LoaiYeuCau } from "@/lib/kieu";
import { CHUA_CO_LOI } from "@/app/yeu-cau/ket-qua";
import { guiYeuCau } from "@/app/yeu-cau/thao-tac";

const BUOC = [
  { so: 1, nhan: "Loại yêu cầu" },
  { so: 2, nhan: "Nội dung" },
  { so: 3, nhan: "Xem lại và gửi" },
];

/** Giá trị đại diện cho “chưa chọn loại nào”. Gửi lên thành `null`. */
const CHUA_RO = "";

export function BieuMauGuiYeuCau({ cacLoai }: { cacLoai: LoaiYeuCau[] }) {
  const [ketQua, guiDi, dangGui] = useActionState(guiYeuCau, CHUA_CO_LOI);

  const [buoc, datBuoc] = useState(1);
  const [loai, datLoai] = useState<string | null>(null);
  const [tieuDe, datTieuDe] = useState("");
  const [moTa, datMoTa] = useState("");

  const daChonLoai = loai !== null;
  const loaiDaChon = cacLoai.find((l) => l.code === loai);
  const duDeSang3 = tieuDe.trim().length >= 3;

  const theTiep = buoc === 1 ? daChonLoai : buoc === 2 ? duDeSang3 : true;

  return (
    <form action={guiDi}>
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
        {/* --- Bước 1 · Loại yêu cầu ------------------------------------- */}
        <div hidden={buoc !== 1} style={{ padding: "22px" }}>
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
                phu={`Cam kết ${l.sla_hours} giờ`}
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
            Gửi vậy cũng được — điều phối viên sẽ phân loại giúp bạn. Hồ sơ chỉ chưa có
            thời hạn cam kết cho tới lúc đó.
          </button>
        </div>

        {/* --- Bước 2 · Nội dung ------------------------------------------ */}
        <div hidden={buoc !== 2}>
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
                Một câu nói rõ hiện tượng. Đừng chỉ ghi “lỗi” hay “cần hỗ trợ” — người
                tiếp nhận đọc dòng này trước tiên để xếp việc.
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
                Nêu rõ bốn điều: hiện tượng, thời điểm bắt đầu, vị trí hoặc thiết bị, và
                bạn đã thử cách gì. Thiếu chúng thì phòng ban phải hỏi lại, và hồ sơ
                đứng lại chờ bạn trả lời.
              </span>
            </label>
          </div>
        </div>

        {/* --- Bước 3 · Xem lại ------------------------------------------- */}
        <div hidden={buoc !== 3} style={{ padding: "22px", display: "grid", gap: "18px" }}>
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
                  ? `${loaiDaChon.sla_hours} giờ kể từ lúc phòng ban bắt đầu xử lý`
                  : "Chưa xác định cho tới khi hồ sơ được phân loại"
              }
            />
            <MucXemLai khoa="Tiêu đề" gia_tri={tieuDe || "—"} />
            <MucXemLai khoa="Mô tả" gia_tri={moTa || "Bạn chưa điền mô tả"} />
          </div>

          <p
            style={{
              margin: 0,
              padding: "13px 15px",
              borderRadius: "11px",
              background: "var(--accent-soft)",
              border: "1px solid var(--accent-line)",
              fontSize: "13px",
              lineHeight: 1.65,
              color: "var(--ink)",
            }}
          >
            Gửi xong, hồ sơ vào hàng đợi tiếp nhận và bạn theo dõi được toàn bộ đường đi
            của nó ở mục <strong style={{ fontWeight: 600 }}>Hồ sơ của tôi</strong>. Mức
            độ ưu tiên do người tiếp nhận đặt sau khi phân loại.
          </p>
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

          {buoc < 3 ? (
            <button
              type="button"
              className="nut"
              data-loai="chinh"
              disabled={!theTiep}
              onClick={() => datBuoc(buoc + 1)}
            >
              Tiếp tục →
            </button>
          ) : (
            <button
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
