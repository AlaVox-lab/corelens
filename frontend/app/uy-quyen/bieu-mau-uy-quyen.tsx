"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Biểu mẫu khai ủy quyền (#252) và nút thu hồi. Danh sách người lấy từ danh bạ qua dịch vụ; ô "người
// vắng" chỉ hiện với trưởng phòng — người khác luôn khai cho chính mình.

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { khaiUyQuyen, thuHoiUyQuyen } from "./thao-tac";

export type NguoiTrongPhong = { id: string; name: string; roles: string[]; can_be_delegator: boolean };

const KIEU_LOI = {
  margin: "10px 0 0",
  padding: "10px 14px",
  borderRadius: "11px",
  background: "var(--f-r-bg)",
  border: "1px solid var(--f-r-line)",
  color: "var(--f-r-ink)",
  fontSize: "13.5px",
  lineHeight: 1.6,
} as const;

export function BieuMauUyQuyen({
  toi,
  homNay,
  nguoi,
  khaiThayDuoc,
}: Readonly<{ toi: string; homNay: string; nguoi: NguoiTrongPhong[]; khaiThayDuoc: boolean }>) {
  const router = useRouter();
  const [nguoiVang, setNguoiVang] = useState("");
  const [nguoiNhan, setNguoiNhan] = useState("");
  const [tu, setTu] = useState(homNay);
  const [den, setDen] = useState(homNay);
  const [loi, setLoi] = useState<string | null>(null);
  const [xong, setXong] = useState<string | null>(null);
  const [dangGui, batDauGui] = useTransition();

  const vang = nguoiVang || toi;
  const coTheNhan = nguoi.filter((p) => p.id !== vang);

  function gui() {
    setLoi(null);
    setXong(null);
    if (!nguoiNhan) {
      setLoi("Chọn người làm thay.");
      return;
    }
    batDauGui(async () => {
      const kq = await khaiUyQuyen({
        delegate_id: nguoiNhan,
        starts_on: tu,
        ends_on: den,
        delegator_id: nguoiVang || null,
      });
      if (!kq.ok) {
        setLoi(kq.thongDiep ?? "Chưa khai được. Thử lại sau ít phút.");
        return;
      }
      setXong("Đã khai ủy quyền. Từ ngày đầu, người làm thay làm được ngay, không cần họ xác nhận.");
      setNguoiNhan("");
      router.refresh();
    });
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        gui();
      }}
      style={{ display: "grid", gap: "12px", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))" }}
    >
      {khaiThayDuoc ? (
        <label style={{ display: "grid", gap: "4px", fontSize: "13px" }}>
          <span className="nhat">Người vắng</span>
          <select className="o-nhap" name="delegator" value={nguoiVang} onChange={(e) => setNguoiVang(e.target.value)}>
            <option value="">Tôi</option>
            {nguoi
              .filter((p) => p.can_be_delegator && p.id !== toi)
              .map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
          </select>
        </label>
      ) : null}
      <label style={{ display: "grid", gap: "4px", fontSize: "13px" }}>
        <span className="nhat">Người làm thay</span>
        <select className="o-nhap" name="delegate" value={nguoiNhan} onChange={(e) => setNguoiNhan(e.target.value)}>
          <option value="">— Chọn người cùng phòng —</option>
          {coTheNhan.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
              {p.roles.length ? ` (${p.roles.join(", ")})` : ""}
            </option>
          ))}
        </select>
      </label>
      <label style={{ display: "grid", gap: "4px", fontSize: "13px" }}>
        <span className="nhat">Từ ngày</span>
        <input className="o-nhap" type="date" name="starts_on" min={homNay} value={tu} onChange={(e) => setTu(e.target.value)} />
      </label>
      <label style={{ display: "grid", gap: "4px", fontSize: "13px" }}>
        <span className="nhat">Đến hết ngày</span>
        <input className="o-nhap" type="date" name="ends_on" min={tu} value={den} onChange={(e) => setDen(e.target.value)} />
      </label>
      <div style={{ gridColumn: "1 / -1" }}>
        <button type="submit" className="nut" data-loai="chinh" disabled={dangGui}>
          Khai ủy quyền
        </button>
        {loi ? (
          <p role="alert" style={KIEU_LOI}>
            {loi}
          </p>
        ) : null}
        {xong ? (
          <p role="status" className="nhat" style={{ marginTop: "10px", fontSize: "13.5px" }}>
            {xong}
          </p>
        ) : null}
      </div>
    </form>
  );
}

export function NutThuHoi({ ma, ten }: Readonly<{ ma: number; ten: string }>) {
  const router = useRouter();
  const [loi, setLoi] = useState<string | null>(null);
  const [dangGui, batDauGui] = useTransition();
  return (
    <>
      <button
        type="button"
        className="nut nut-nho"
        data-loai="nguy"
        disabled={dangGui}
        aria-label={`Thu hồi ủy quyền cho ${ten}`}
        onClick={() =>
          batDauGui(async () => {
            const kq = await thuHoiUyQuyen(ma);
            if (!kq.ok) setLoi(kq.thongDiep ?? "Chưa thu hồi được.");
            else router.refresh();
          })
        }
      >
        Thu hồi
      </button>
      {loi ? (
        <p role="alert" style={KIEU_LOI}>
          {loi}
        </p>
      ) : null}
    </>
  );
}
