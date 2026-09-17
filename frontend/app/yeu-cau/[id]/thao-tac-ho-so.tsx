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

import { useActionState, useState } from "react";

import type { CanhDiDuoc } from "@/lib/kieu";
import { CHUA_CO_LOI } from "@/app/yeu-cau/ket-qua";
import { chuyenTrangThai } from "@/app/yeu-cau/thao-tac";

/**
 * Cạnh nào nên trông như hành động chính.
 *
 * Suy từ dữ liệu chứ không tra bảng: cạnh dẫn tới trạng thái kết thúc và không đòi
 * ghi lý do thường là đường đi xuôi (“Xác nhận đạt”, “Đóng hồ sơ”), còn cạnh đòi lý
 * do thì bao giờ cũng là ngoại lệ. Đoán sai cũng chỉ sai màu nút, không sai hành vi.
 */
function laDuongXuoi(canh: CanhDiDuoc, tongSo: number): boolean {
  return tongSo > 1 && !canh.requires_note;
}

export function ThaoTacHoSo({
  maHoSo,
  cacCanh,
}: {
  maHoSo: number;
  cacCanh: CanhDiDuoc[];
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
            fontSize: "11px",
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
        {cacCanh.map((canh) =>
          canh.requires_note ? (
            <button
              key={canh.to_state}
              type="button"
              className="nut"
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
              data-loai={laDuongXuoi(canh, cacCanh.length) ? "chinh" : undefined}
              disabled={dangChay}
            >
              {canh.activity_label}
            </button>
          ),
        )}
      </div>

      {/* Ô ghi lý do chỉ hiện khi cạnh đang chọn bắt buộc có lý do. Cột
          `transitions.requires_note` trong cơ sở dữ liệu quyết định điều đó, không
          phải mã nguồn ở đây. */}
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
          <label style={{ display: "grid", gap: "7px" }}>
            <span style={{ fontSize: "13.5px", fontWeight: 600 }}>
              Lý do cho “{dangMo.activity_label}”
            </span>
            <textarea
              name="note"
              className="o-nhap"
              rows={3}
              maxLength={2000}
              required
              placeholder="Nói rõ vì sao. Dòng này đi vào nhật ký hồ sơ và người xử lý sẽ đọc nó."
            />
          </label>
          <span style={{ fontSize: "12px", color: "var(--ink-3)", lineHeight: 1.55 }}>
            Thao tác này bắt buộc ghi lý do. Không có lý do thì người tiếp theo không
            biết chuyện gì đã xảy ra, và bản phân tích quy trình về sau chỉ thấy một
            nhánh lệch chuẩn không rõ nguyên nhân.
          </span>
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
