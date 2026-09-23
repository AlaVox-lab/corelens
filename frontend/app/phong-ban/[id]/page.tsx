// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn chi tiết hồ sơ của buồng lái phòng ban (#83).
//
// Cùng bố cục hai cột với buồng lái điều phối: bên trái để ĐỌC, bên phải để LÀM. Trưởng
// phòng và người xử lý dùng chung trang này; nút của mỗi người khác nhau vì chúng đến
// từ `allowed_transitions`, không từ một phép so vai trò nào ở đây.
//
// Trang KHÔNG đoán trước ô nào sẽ hiện. Nó đọc `fields` của các thao tác đang đi được,
// rồi nạp đúng những danh mục mà các ô đó cần. Cạnh *Phân công lại* mang ràng buộc "không
// được đổi phòng ban", nên nó có cả ô phòng ban — bản đầu của trang chỉ nạp danh sách
// người, và ô phòng ban rơi về một ô gõ chữ trống. Nạp theo `fields` thì trường nào
// dịch vụ cho hiện cũng có danh mục, kể cả trường sau này mới thêm vào một cạnh.
//
// Nhờ vậy danh sách người xử lý chỉ được tra khi có ít nhất một thao tác cho giao người.
// Người xử lý mở hồ sơ thì không có thao tác nào như vậy, và Keycloak không bị hỏi tới —
// danh bạ chỉ nằm trên đường đi của đúng cái ô cần nó (#84).

import Link from "next/link";
import { notFound } from "next/navigation";

import { chuyenTrangThaiPhongBan } from "@/app/phong-ban/thao-tac";
import { BangThaoTac, type NguonLuaChon } from "@/components/bang-thao-tac";
import { DongThoiGian } from "@/components/dong-thoi-gian";
import { NhanTrangThai } from "@/components/nhan-trang-thai";
import { docDichVu, goiDichVu } from "@/lib/api";
import { ngayGio, thoiLuong } from "@/lib/dinh-dang";
import type { HoSoPhongBan, NhanCoMa, NguoiNhanViecTrongPhong } from "@/lib/kieu";
import { docDongHo } from "@/lib/sla";
import { kieuTruong, type NguonDanhMuc } from "@/lib/truong";

export const dynamic = "force-dynamic";

function O({
  tua,
  children,
  phu,
  canhBao = false,
}: {
  tua: string;
  children: React.ReactNode;
  phu?: React.ReactNode;
  canhBao?: boolean;
}) {
  return (
    <div style={{ display: "grid", gap: "6px", alignContent: "start" }}>
      <span className="tua-muc">{tua}</span>
      <span
        style={{
          fontSize: "14.5px",
          fontWeight: 600,
          color: canhBao ? "var(--f-r-ink)" : undefined,
        }}
      >
        {children}
      </span>
      {phu && <span style={{ fontSize: "12.5px", color: "var(--ink-3)" }}>{phu}</span>}
    </div>
  );
}

async function napNguon(nguon: NguonDanhMuc, ho_so: HoSoPhongBan): Promise<NguonLuaChon> {
  if (nguon === "assignees") {
    if (!ho_so.department) return { loi: "Hồ sơ chưa thuộc phòng nào nên chưa giao được người." };
    const ketQua = await docDichVu<NguoiNhanViecTrongPhong>(
      `/departments/${encodeURIComponent(ho_so.department.code)}/assignees`,
    );
    if (!ketQua.ok) {
      return {
        loi: `${ketQua.thongDiep} Vẫn nhận được hồ sơ mà chưa giao cho ai — cả phòng cùng thấy hồ sơ này.`,
      };
    }
    return ketQua.duLieu.people.map((p) => ({ code: p.id, label: p.name }));
  }

  // Ba danh mục còn lại mang đúng tên điểm cuối của chúng
  const ds = await goiDichVu<NhanCoMa[]>(`/${nguon}`);
  return ds ? ds.map(({ code, label }) => ({ code, label })) : { loi: "Không nạp được danh mục." };
}

/** Nạp đúng những danh mục mà các thao tác đang đi được cần tới — không hơn. */
async function danhMucCan(
  ho_so: HoSoPhongBan,
): Promise<Partial<Record<NguonDanhMuc, NguonLuaChon>>> {
  const can = new Set<NguonDanhMuc>();
  for (const canh of ho_so.allowed_transitions) {
    for (const truong of canh.fields) {
      const nguon = kieuTruong(truong).nguon;
      if (nguon) can.add(nguon);
    }
  }
  const cap = await Promise.all(
    [...can].map(async (nguon) => [nguon, await napNguon(nguon, ho_so)] as const),
  );
  return Object.fromEntries(cap);
}

export default async function ChiTietPhongBan({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const ho_so = await goiDichVu<HoSoPhongBan>(`/department/requests/${id}`);
  if (!ho_so) notFound();

  const danhMuc = await danhMucCan(ho_so);
  const bayGio = new Date();
  const giayCho = Math.max(
    0,
    (bayGio.getTime() - new Date(ho_so.state_entered_at).getTime()) / 1000,
  );
  const dongHo = docDongHo(ho_so);

  return (
    <>
      <Link href="/phong-ban" className="nut nut-nho khong-in">
        ← Hàng đợi
      </Link>

      <div className="bo-cuc-buong-lai">
        {/* --- Cột trái: đọc -------------------------------------------------- */}
        <div style={{ minWidth: 0 }}>
          <div className="the" style={{ padding: "20px 22px" }}>
            <div
              className="mono"
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "8px 12px",
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
                    padding: "2px 9px",
                    borderRadius: "999px",
                    background: "var(--surface-3)",
                    border: "1px solid var(--line-2)",
                    fontSize: "11.5px",
                    color: "var(--ink-2)",
                  }}
                >
                  {ho_so.request_type.label}
                </span>
              )}
              <span>Gửi {ngayGio(ho_so.created_at)}</span>
            </div>

            <h1
              style={{
                margin: "9px 0 0",
                fontSize: "clamp(20px,3vw,24px)",
                fontWeight: 600,
                letterSpacing: "-.02em",
                lineHeight: 1.3,
              }}
            >
              {ho_so.title}
            </h1>

            <div
              style={{
                marginTop: "18px",
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))",
                gap: "16px",
              }}
            >
              <O tua="Trạng thái" phu={`từ ${thoiLuong(giayCho)} trước`}>
                <NhanTrangThai ma={ho_so.state.code} nhan={ho_so.state.label} />
              </O>
              <O tua="Hạn xử lý" canhBao={dongHo.canhBao}>
                {dongHo.cau}
              </O>
              <O tua="Người xử lý">
                {ho_so.assigned_to_me
                  ? "Bạn"
                  : ho_so.assignee_id
                    ? (ho_so.assignee_label ?? "Một người trong phòng")
                    : "Chưa giao cho ai"}
              </O>
              <O tua="Người gửi">{ho_so.requester_label ?? "Không rõ"}</O>
              <O tua="Mức ưu tiên">{ho_so.priority?.label ?? "—"}</O>
              <O tua="Phòng ban">{ho_so.department?.label ?? "—"}</O>
            </div>
          </div>

          {ho_so.description && (
            <div className="the" style={{ marginTop: "20px", padding: "18px 22px" }}>
              <h2 className="tua-muc" style={{ margin: 0 }}>
                Nội dung yêu cầu
              </h2>
              <p
                style={{
                  margin: "9px 0 0",
                  fontSize: "14px",
                  lineHeight: 1.7,
                  whiteSpace: "pre-wrap",
                }}
              >
                {ho_so.description}
              </p>
            </div>
          )}

          <DongThoiGian
            cacSuKien={ho_so.history}
            bayGio={bayGio}
            khiTrong="Hồ sơ chưa đổi trạng thái lần nào."
          />
        </div>

        {/* --- Cột phải: làm ------------------------------------------------- */}
        <aside className="cot-thao-tac khong-in">
          <div className="the">
            <div
              style={{
                padding: "15px 17px",
                borderBottom: "1px solid var(--line)",
                display: "grid",
                gap: "4px",
              }}
            >
              <h2 style={{ margin: 0, fontSize: "15px", fontWeight: 600 }}>Thao tác</h2>
              <p style={{ margin: 0, fontSize: "12.5px", color: "var(--ink-3)", lineHeight: 1.55 }}>
                Sinh ra từ bộ quy tắc quy trình, theo trạng thái hồ sơ và vai trò của bạn.
              </p>
            </div>
            <div style={{ padding: "15px 17px" }}>
              <BangThaoTac
                key={ho_so.state.code}
                maHoSo={ho_so.id}
                cacCanh={ho_so.allowed_transitions}
                // Giá trị hồ sơ đang có, cho cả bốn trường quyết định. Ô phòng ban ở
                // cạnh phân công lại vì thế hiện đúng phòng đang giữ hồ sơ.
                giaTriDau={{
                  request_type_code: ho_so.request_type?.code ?? "",
                  priority_code: ho_so.priority?.code ?? "",
                  department_code: ho_so.department?.code ?? "",
                  assignee_id: ho_so.assignee_id ?? "",
                }}
                goiY={{}}
                danhMuc={danhMuc}
                hanhDong={chuyenTrangThaiPhongBan}
                khiHet={{
                  cau: "Không có thao tác nào dành cho bạn ở trạng thái này.",
                  veHangDoi: "/phong-ban",
                }}
              />
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}
