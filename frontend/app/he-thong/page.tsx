// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn Hệ thống (#229): tình trạng các dịch vụ của cụm, chỉ cho quản trị viên. Dịch vụ quyết
// ai thấy màn này qua danh sách không gian của `/me` (`system`); người khác mở đường dẫn
// này thì gặp lời báo không vào được của khung, không thấy chữ kỹ thuật nào.

import { KhungLamViec } from "@/components/khung-lam-viec";
import { docSucKhoe, TheHeThong } from "@/components/the-he-thong";

import { XuatNhatKy } from "./xuat-nhat-ky";

export const dynamic = "force-dynamic";

export default async function ManHeThong() {
  const sucKhoe = await docSucKhoe();
  return (
    <KhungLamViec canKhongGian="system">
      <h1 className="tieu-de-trang">Hệ thống</h1>
      <p className="cau-chao">
        Tình trạng các dịch vụ của cụm, đọc từ điểm kiểm tra sức khỏe của dịch vụ ứng dụng.
      </p>
      <div style={{ marginTop: "20px", maxWidth: "720px" }}>
        <TheHeThong sucKhoe={sucKhoe} tieuDe="Các dịch vụ" />
      </div>
      <div style={{ marginTop: "20px", maxWidth: "720px" }}>
        <XuatNhatKy />
      </div>
    </KhungLamViec>
  );
}
