// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn Ủy quyền (#252), trong không gian phòng ban. Người vắng khai cho một người cùng phòng làm thay
// trong một khoảng ngày; trưởng phòng khai thay được cho người xử lý. Danh sách hiện ủy quyền của chính
// mình (cho hay nhận) và, với trưởng phòng, mọi ủy quyền trong phòng. Mọi luật nằm ở dịch vụ
// (app/workflow/uy_quyen_routes.py); trang không tự quyết ai được khai.

import { KhungLamViec } from "@/components/khung-lam-viec";
import { docDichVu, goiDichVu, type DanhTinh } from "@/lib/api";

import { BieuMauUyQuyen, NutThuHoi, type NguoiTrongPhong } from "./bieu-mau-uy-quyen";

export const dynamic = "force-dynamic";

type UyQuyen = {
  id: number;
  delegator_label: string;
  delegate_label: string;
  department_label: string;
  roles: string[];
  starts_on: string;
  ends_on: string;
  status: "active" | "upcoming" | "ended" | "revoked";
  created_by_label: string;
  revoked_by_label: string | null;
  can_revoke: boolean;
};

type DanhSachUyQuyen = {
  today: string;
  max_days: number;
  can_grant_for_others: boolean;
  items: UyQuyen[];
};

const TINH_TRANG: Record<UyQuyen["status"], string> = {
  active: "Đang hiệu lực",
  upcoming: "Sắp tới",
  ended: "Đã hết",
  revoked: "Đã thu hồi",
};

const ngay = (iso: string) => iso.split("-").reverse().join("/");

export default async function ManUyQuyen() {
  const [danhSach, nguoi, toi] = await Promise.all([
    goiDichVu<DanhSachUyQuyen>("/delegations"),
    docDichVu<{ members: NguoiTrongPhong[] }>("/delegations/members"),
    goiDichVu<DanhTinh>("/me"),
  ]);

  return (
    <KhungLamViec canKhongGian="department">
      <h1 className="tieu-de-trang">Ủy quyền</h1>
      <p className="cau-chao">
        Vắng mặt vài ngày thì nhờ một người cùng phòng làm thay. Người đó mang vai của bạn trong phòng, chỉ trong
        những ngày đã khai, không phải xác nhận; mọi thao tác ghi &ldquo;thay mặt&rdquo; bạn. Không dùng ủy quyền
        để xử lý hồ sơ do chính người làm thay gửi, và không ủy quyền tiếp được.
      </p>

      {danhSach === null || toi === null ? (
        <p className="nhat" style={{ marginTop: "16px" }}>
          Chưa đọc được ủy quyền. Thử tải lại trang sau ít phút.
        </p>
      ) : (
        <>
          <section className="the" style={{ marginTop: "20px", padding: "16px 20px", maxWidth: "900px" }}>
            <h2 style={{ fontSize: "16px", margin: "0 0 12px" }}>Khai ủy quyền mới</h2>
            {nguoi.ok ? (
              <BieuMauUyQuyen
                toi={toi.id}
                homNay={danhSach.today}
                nguoi={nguoi.duLieu.members}
                khaiThayDuoc={danhSach.can_grant_for_others}
              />
            ) : (
              <p className="nhat" role="alert">
                {nguoi.thongDiep}
              </p>
            )}
            <p className="nhat" style={{ fontSize: "12.5px", margin: "12px 0 0" }}>
              Mỗi lần dài tối đa {danhSach.max_days} ngày, tính từ 00:00 ngày đầu tới hết ngày cuối.
            </p>
          </section>

          <section className="the" style={{ marginTop: "20px", padding: "16px 20px", overflowX: "auto" }}>
            <h2 style={{ fontSize: "16px", margin: "0 0 12px" }}>Các ủy quyền</h2>
            {danhSach.items.length === 0 ? (
              <p className="nhat" style={{ fontSize: "13.5px" }}>
                Chưa có ủy quyền nào.
              </p>
            ) : (
              <table className="bang bang-cau-hinh" data-ds-uy-quyen>
                <thead>
                  <tr>
                    <th>Người vắng</th>
                    <th>Người làm thay</th>
                    <th>Vai</th>
                    <th>Từ</th>
                    <th>Đến hết</th>
                    <th>Tình trạng</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {danhSach.items.map((u) => (
                    <tr key={u.id} data-uy-quyen={u.status}>
                      <td>
                        <b>{u.delegator_label}</b>
                      </td>
                      <td>{u.delegate_label}</td>
                      <td>
                        {u.roles.join(", ")} <span className="nhat">· {u.department_label}</span>
                      </td>
                      <td>{ngay(u.starts_on)}</td>
                      <td>{ngay(u.ends_on)}</td>
                      <td>
                        {TINH_TRANG[u.status]}
                        {u.revoked_by_label ? <span className="nhat"> · {u.revoked_by_label}</span> : null}
                      </td>
                      <td style={{ textAlign: "right" }}>
                        {u.can_revoke ? <NutThuHoi ma={u.id} ten={u.delegate_label} /> : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </KhungLamViec>
  );
}
