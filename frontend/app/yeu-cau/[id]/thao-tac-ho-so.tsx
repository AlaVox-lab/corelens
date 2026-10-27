"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Những nút bấm trên một hồ sơ.
//
// ĐÂY LÀ CHỖ QUAN TRỌNG NHẤT CỦA CẢ MÀN HÌNH, và cũng là chỗ dễ làm sai nhất.
//
// Danh sách nút dựng **hoàn toàn** từ `allowed_transitions` mà dịch vụ trả về. Không
// có bảng ánh xạ “trạng thái nào thì hiện nút nào” trong tệp này, và không được thêm
// vào. Bảng đó nằm trong cơ sở dữ liệu — bảng `transitions` cùng ma trận phân quyền —
// và engine đọc nó để trả lời.
//
// Bản thiết kế giao diện của màn này có một bảng như vậy, và nó vẽ sai hai chỗ: đặt
// nút “Hủy yêu cầu” ở trạng thái *Đang xử lý* và *Đã leo thang*, trong khi dữ liệu
// không có cạnh nào đi từ hai trạng thái đó tới *Đã hủy*. Đó là ràng buộc Poka-yoke
// “chỉ hủy được trước khi phòng ban bắt tay vào việc”. Chép bảng của bản thiết kế vào
// đây sẽ dựng ra hai cái nút bấm vào là báo lỗi — thứ tệ hơn cả việc không có nút.
//
// Lấy nút từ API thì hai cái nút sai đó tự biến mất, và mãi mãi không quay lại được.
//
// Nhãn chữ trên nút cũng đến từ dữ liệu (`activity_label`), không phải hằng số ở đây.
//
// Nút nào bấm là gửi ngay, nút nào mở bảng xác nhận — cũng suy từ dữ liệu của cạnh:
//
//   bắt buộc lý do (`requires_note`)          → mở bảng, ô lý do bắt buộc
//   dẫn tới trạng thái kết thúc (#98)         → mở bảng, cảnh báo không hoàn tác được,
//                                               ô lý do tùy chọn
//   cho đặt trường (`fields`, #127)            → mở bảng, ô nhập điền sẵn giá trị đang có
//   còn lại                                    → bấm là gửi
//
// Trước #98, "Hủy yêu cầu" bấm là hủy ngay: không hỏi lại, không ghi được lý do, mà
// *Đã hủy* thì không có đường ra — bấm nhầm là mất hồ sơ.

import { useActionState, useState } from "react";

import { OTruong, type NguonLuaChon } from "@/components/bang-thao-tac";
import { CanhBaoKetThuc } from "@/components/canh-bao-ket-thuc";
import { OTruongRieng } from "@/components/o-truong-rieng";
import { TIEN_TO_TRUONG } from "@/lib/bieu-mau";
import type { CanhDiDuoc, LoaiYeuCau } from "@/lib/kieu";
import { kieuTruong, type NguonDanhMuc } from "@/lib/truong";
import { CHUA_CO_LOI } from "@/app/yeu-cau/ket-qua";
import { chuyenTrangThai } from "@/app/yeu-cau/thao-tac";

/**
 * Cạnh nào nên trông như hành động chính: cạnh đứng đầu, khi có từ hai nút trở lên.
 *
 * Danh sách đã xếp theo `transitions.display_order`, và dữ liệu khởi tạo đặt đường
 * xuôi lên trước — nên đây vẫn là dữ liệu quyết, không phải bảng trong tệp này.
 *
 * Trước #79 tệp này đoán bằng cờ: cạnh không đòi lý do là đường xuôi. Đoán vậy hỏng
 * ngay khi cạnh “Bổ sung thông tin” bắt đầu đòi ghi chú — nút “Hủy yêu cầu” thành nút
 * chính. Cờ không phân biệt được hai trường hợp: ở *Chờ bổ sung thông tin* và ở *Hoàn
 * tất*, hai cạnh mang y hệt cờ nhưng đường xuôi nằm ở hai phía ngược nhau.
 */
function laDuongXuoi(chiSo: number, tongSo: number): boolean {
  return tongSo > 1 && chiSo === 0;
}

/** Cạnh này cần mở bảng trước khi gửi, thay vì bấm là gửi. */
function canHoiLai(canh: CanhDiDuoc): boolean {
  return canh.requires_note || canh.to_state_is_terminal || canh.fields.length > 0;
}

export function ThaoTacHoSo({
  maHoSo,
  cacCanh,
  giaTriDau = {},
  danhMuc = {},
  truongRieng,
}: {
  maHoSo: number;
  cacCanh: CanhDiDuoc[];
  /** Nội dung hồ sơ đang có, điền sẵn vào ô nhập của thao tác sửa nội dung (#127). */
  giaTriDau?: Record<string, string>;
  danhMuc?: Partial<Record<NguonDanhMuc, NguonLuaChon>>;
  /** Trường riêng (#250): giá trị đang có, loại hiện tại và danh mục loại kèm khai báo trường. */
  truongRieng?: { giaTri: Record<string, unknown>; loaiDau: string | null; cacLoai: LoaiYeuCau[] };
}) {
  const [ketQua, thucHien, dangChay] = useActionState(chuyenTrangThai, CHUA_CO_LOI);
  const [dangMo, datDangMo] = useState<CanhDiDuoc | null>(null);

  if (cacCanh.length === 0) {
    return (
      <p
        style={{
          margin: 0,
          display: "flex",
          alignItems: "center",
          gap: "9px",
          fontSize: "13px",
          color: "var(--ink-3)",
        }}
      >
        <span
          className="mono"
          aria-hidden="true"
          style={{
            width: "20px",
            height: "20px",
            borderRadius: "50%",
            border: "1px dashed var(--line-2)",
            display: "grid",
            placeItems: "center",
            fontSize: "12px",
          }}
        >
          –
        </span>
        Không có thao tác nào dành cho bạn ở trạng thái này.
      </p>
    );
  }

  return (
    <form action={thucHien}>
      <input type="hidden" name="case_id" value={maHoSo} />

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "10px",
          alignItems: "center",
        }}
      >
        {cacCanh.map((canh, chiSo) =>
          canHoiLai(canh) ? (
            <button
              key={canh.to_state}
              type="button"
              className="nut"
              data-loai={laDuongXuoi(chiSo, cacCanh.length) ? "chinh" : undefined}
              onClick={() => datDangMo(dangMo?.to_state === canh.to_state ? null : canh)}
              aria-expanded={dangMo?.to_state === canh.to_state}
            >
              {canh.activity_label}
            </button>
          ) : (
            <button
              key={canh.to_state}
              type="submit"
              name="to_state"
              value={canh.to_state}
              className="nut"
              data-loai={laDuongXuoi(chiSo, cacCanh.length) ? "chinh" : undefined}
              disabled={dangChay}
            >
              {canh.activity_label}
            </button>
          ),
        )}
      </div>

      {/* Bảng xác nhận. Lý do bắt buộc hay tùy chọn do cột `transitions.requires_note`
          quyết; có cảnh báo không hoàn tác được hay không do `states.is_terminal` quyết.
          Không phải mã nguồn ở đây. */}
      {dangMo && (
        <div
          style={{
            marginTop: "14px",
            padding: "15px",
            borderRadius: "11px",
            background: "var(--surface-2)",
            border: "1px solid var(--line)",
            display: "grid",
            gap: "9px",
          }}
        >
          {dangMo.to_state_is_terminal && (
            <CanhBaoKetThuc
              nhanTrangThai={dangMo.to_state_label}
              moLaiGio={dangMo.to_state_reopen_hours}
            />
          )}
          {/* Ô nhập dựng từ `fields` của cạnh — chỉ thao tác sửa nội dung có (#127). Sửa
              ở Đã phân loại thì hồ sơ về Đã gửi; nói trước để người gửi không bất ngờ. */}
          {dangMo.fields.length > 0 && (
            <>
              <span style={{ fontSize: "12.5px", color: "var(--ink-3)", lineHeight: 1.55 }}>
                {dangMo.keeps_state
                  ? "Trạng thái giữ nguyên. Bản cũ vẫn nằm trong dòng thời gian."
                  : `Hồ sơ sẽ chuyển sang “${dangMo.to_state_label}”. Bản cũ vẫn nằm trong dòng thời gian.`}
              </span>
              {dangMo.fields.map((truong) => {
                const nguonMa = kieuTruong(truong).nguon;
                if (kieuTruong(truong).rieng) {
                  return truongRieng ? (
                    <OTruongRieng
                      key={truong}
                      ten={`${TIEN_TO_TRUONG}${truong}`}
                      giaTriDau={truongRieng.giaTri}
                      theoLoai={{
                        cacLoai: truongRieng.cacLoai,
                        loaiDau: truongRieng.loaiDau,
                        tenOChon: `${TIEN_TO_TRUONG}request_type_code`,
                      }}
                    />
                  ) : null;
                }
                return (
                  <OTruong
                    key={truong}
                    truong={truong}
                    giaTriDau={giaTriDau[truong] ?? ""}
                    nguon={nguonMa ? danhMuc[nguonMa] : undefined}
                  />
                );
              })}
            </>
          )}
          {/* Tên ô từ `transitions.note_label` (#79): ở cạnh bổ sung thông tin, ô này là
              câu trả lời của người gửi chứ không phải lý do. */}
          <label style={{ display: "grid", gap: "7px" }}>
            <span style={{ fontSize: "13.5px", fontWeight: 600 }}>
              {dangMo.note_label ?? `Lý do cho “${dangMo.activity_label}”`}
              {!dangMo.requires_note && (
                <span style={{ fontWeight: 400, color: "var(--ink-3)" }}> — không bắt buộc</span>
              )}
            </span>
            <textarea
              name="note"
              className="o-nhap"
              rows={3}
              maxLength={2000}
              required={dangMo.requires_note}
              placeholder={
                !dangMo.requires_note
                  ? "Có thể bỏ trống. Nếu ghi, dòng này đi vào dòng thời gian của hồ sơ."
                  : dangMo.note_label
                    ? "Dòng này đi vào dòng thời gian của hồ sơ, và người đã hỏi bạn sẽ đọc nó."
                    : "Nói rõ vì sao. Dòng này đi vào dòng thời gian của hồ sơ và người xử lý sẽ đọc nó."
              }
            />
          </label>
          {dangMo.requires_note && (
            <span style={{ fontSize: "12px", color: "var(--ink-3)", lineHeight: 1.55 }}>
              Ô này bắt buộc: người nhận việc tiếp theo cần biết vì sao.
            </span>
          )}
          <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
            <button
              type="submit"
              name="to_state"
              value={dangMo.to_state}
              className="nut"
              data-loai="chinh"
              disabled={dangChay}
            >
              {dangChay ? "Đang gửi…" : `Xác nhận · ${dangMo.activity_label}`}
            </button>
            <button type="button" className="nut" onClick={() => datDangMo(null)}>
              Thôi
            </button>
          </div>
        </div>
      )}

      {ketQua.loi && (
        <p
          role="alert"
          style={{
            marginTop: "14px",
            marginBottom: 0,
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
