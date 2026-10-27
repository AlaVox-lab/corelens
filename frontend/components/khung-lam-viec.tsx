// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khung trang dùng chung cho mọi không gian làm việc: cổng người gửi (#44), buồng lái
// điều phối (#82) và buồng lái phòng ban (#83).
//
// Ba việc đặt ở đây chứ không lặp lại trong từng trang:
//
//   Cửa đăng nhập — chưa đăng nhập thì không trang nào có gì để hiển thị.
//   Cửa không gian — trang thuộc buồng lái mà người dùng không vào được thì báo rõ,
//                    thay vì để từng điểm cuối trả 403 thành một trang trống.
//   Số đếm — mỗi mục trên thanh bên mang số hồ sơ còn mở ở đó (#158), mục Hộp thư mang
//            số tin chưa đọc (#155).
//
// Thanh bên dựng từ `workspaces` mà `/me` trả về. Khung này không biết tên vai trò nào:
// dịch vụ quyết ai vào được đâu, giao diện chỉ vẽ theo. Phần chạy ở trình duyệt — ngăn
// kéo, nút sáng/tối — nằm ở `khung-ung-dung.tsx`.

import { ServerCrash } from "lucide-react";
import { Suspense } from "react";

import type { MucDieuHuong } from "@/components/dieu-huong";
import { KhungUngDung } from "@/components/khung-ung-dung";
import { ManRong } from "@/components/man-rong";
import { NutDangNhap } from "@/components/nut-dang-nhap";
import { docDichVu, goiDichVu, laHetPhien, type DanhTinh } from "@/lib/api";
import { loiVaoCua } from "@/lib/khong-gian";
import type { HangDoi, HangDoiPhongBan, HoSoTomTat, NhanCoMa } from "@/lib/kieu";
import { chuCaiDau, mauTheo } from "@/lib/nguoi";
import { layPhien } from "@/lib/session";

/**
 * Lời mời đăng nhập. Nút quay về đúng trang đang mở sau khi đăng nhập xong.
 *
 * `hetPhien`: người dùng ĐÃ đăng nhập nhưng phiên vừa hết hạn giữa chừng — trang chi
 * tiết dùng thay cho trang 404, để người dùng không tưởng hồ sơ đã mất (#150).
 */
export function MoiDangNhap({ hetPhien = false }: { hetPhien?: boolean }) {
  return (
    <main className="khung" style={{ padding: "96px 20px", maxWidth: "36rem" }}>
      <h1 style={{ margin: 0, fontSize: "24px", fontWeight: 600, letterSpacing: "-.02em" }}>
        {hetPhien ? "Phiên đăng nhập đã hết hạn" : "Cổng yêu cầu nội bộ"}
      </h1>
      <p style={{ marginTop: "10px", color: "var(--ink-2)", fontSize: "14.5px" }}>
        {hetPhien
          ? "Đăng nhập lại để mở tiếp trang này. Hồ sơ và mọi thao tác trước đó vẫn còn nguyên."
          : "Đăng nhập bằng tài khoản công ty để gửi yêu cầu và theo dõi hồ sơ của bạn."}
      </p>
      {/* Suspense vì nút đọc tham số trên địa chỉ phía trình duyệt */}
      <Suspense>
        <NutDangNhap>Đăng nhập</NutDangNhap>
      </Suspense>
    </main>
  );
}

/**
 * Dịch vụ ứng dụng không phản hồi hay quá thời hạn chờ (#235). Dựng thẳng ở máy chủ như lời
 * mời đăng nhập, không ném lỗi cho ranh giới lỗi phía trình duyệt: trang vẫn đọc được khi
 * JavaScript chưa chạy, và không bị nhầm với "phiên đã hết hạn".
 */
export function KhongPhanHoi() {
  return (
    <main className="khung" style={{ padding: "72px 20px", maxWidth: "40rem" }}>
      <div className="the">
        <ManRong
          icon={ServerCrash}
          loi
          tieuDe="Hệ thống không phản hồi"
          cau="Trang này chưa tải được. Hồ sơ và mọi thao tác trước đó vẫn còn nguyên — thử lại sau ít phút."
        >
          {/* href rỗng là tải lại đúng trang đang mở */}
          <a className="nut" data-loai="chinh" href="">
            Thử lại
          </a>
          <a className="nut" href="/">
            Về trang chủ
          </a>
        </ManRong>
      </div>
    </main>
  );
}

function KhongVaoDuoc() {
  return (
    <div className="the" style={{ padding: "36px 24px", textAlign: "center" }}>
      <p style={{ margin: 0, fontSize: "15px", fontWeight: 600 }}>
        Tài khoản này không mở được khu vực này
      </p>
      <p style={{ margin: "7px 0 0", fontSize: "13.5px", color: "var(--ink-2)", lineHeight: 1.6 }}>
        Quyền vào từng khu vực do quản trị viên cấp theo vai trò. Nếu bạn cần làm việc ở
        đây, hãy nhờ quản trị hệ thống thêm vai trò cho tài khoản của bạn.
      </p>
    </div>
  );
}

type SoDem = { dem: number | null; cho?: number; gap?: boolean; phongBan?: NhanCoMa[] };

/**
 * Việc chờ chính người xem (#230): hồ sơ có `needs_my_action`, và có cái nào gấp không —
 * đã quá hạn, hay hệ thống sắp tự đi thay (`auto_transition.warn`). Cờ do dịch vụ tính từ
 * dữ liệu quy tắc, giao diện chỉ đếm.
 */
function viecCho(ds: HoSoTomTat[]): Pick<SoDem, "cho" | "gap"> {
  const cho = ds.filter((h) => h.needs_my_action);
  return { cho: cho.length, gap: cho.some((h) => h.sla_overdue || h.auto_transition?.warn) };
}

/**
 * Số hồ sơ còn mở ở từng mục, đếm bằng chính điểm cuối mà trang của mục đó dùng — không
 * thêm điểm cuối riêng cho việc đếm, để dịch vụ không phải đổi gì (#158). Cùng cách đếm
 * với câu tóm tắt đầu mỗi trang:
 *
 *   Hồ sơ của tôi — hồ sơ chưa ở trạng thái kết thúc (`is_terminal` tra từ dữ liệu)
 *   Điều phối     — mọi hồ sơ trong hàng đợi
 *   Phòng ban     — hồ sơ phòng phải làm, không tính nhóm chỉ để theo dõi
 *
 * Lỗi thì trả `null` và mục đó không hiện số — thanh bên không được làm hỏng trang.
 */
const DEM: Record<string, () => Promise<SoDem>> = {
  "/yeu-cau": async () => {
    const ds = await goiDichVu<HoSoTomTat[]>("/requests");
    return ds ? { dem: ds.filter((h) => !h.state.is_terminal).length, ...viecCho(ds) } : { dem: null };
  },
  "/dieu-phoi": async () => {
    const hang = await goiDichVu<HangDoi>("/coordination/queue");
    return hang ? { dem: hang.items.length, ...viecCho(hang.items) } : { dem: null };
  },
  "/phong-ban": async () => {
    const hang = await goiDichVu<HangDoiPhongBan>("/department/queue");
    if (!hang) return { dem: null };
    const theoDoi = new Set(hang.groups.filter((g) => g.watch_only).map((g) => g.code));
    return {
      dem: hang.items.filter((m) => !theoDoi.has(m.state.code)).length,
      ...viecCho(hang.items),
      phongBan: hang.departments,
    };
  },
};

export async function KhungLamViec({
  children,
  canKhongGian,
}: Readonly<{
  children: React.ReactNode;
  /** Không gian mà trang này thuộc về. Người dùng không vào được thì hiện lời báo. */
  canKhongGian: string;
}>) {
  const ketQua = await docDichVu<DanhTinh>("/me");

  // Dịch vụ không phản hồi thì không phải hết phiên (#235): báo đúng như vậy, không mời
  // đăng nhập lại một phiên vẫn còn hạn.
  if (!ketQua.ok && ketQua.ma === "khong-ket-noi-duoc") return <KhongPhanHoi />;
  // Còn cookie phiên mà dịch vụ vẫn từ chối thì phiên đã hết hạn giữa chừng (#150)
  if (!ketQua.ok) return <MoiDangNhap hetPhien={laHetPhien(ketQua) && (await layPhien()) !== null} />;
  const danhTinh = ketQua.duLieu;

  const ten = danhTinh.name ?? danhTinh.username ?? danhTinh.id;
  const khongGian = danhTinh.workspaces ?? ["portal"];
  const loiVao = loiVaoCua(khongGian);

  const [soDem, hopThu] = await Promise.all([
    Promise.all(
      loiVao
        .filter((l) => DEM[l.duongDan])
        .map(async (l) => [l.duongDan, await DEM[l.duongDan]()] as const),
    ).then((cap) => new Map(cap)),
    goiDichVu<{ unread: number }>("/inbox/unread"),
  ]);
  // Nhân viên: hộp thư là chỗ làm việc, cuối nhóm "Làm việc" như wireframe. Người chỉ gửi
  // yêu cầu không có nhóm đó, nên hộp thư nằm cùng các mục chung.
  const laNhanVien = loiVao.some((l) => l.nhom === "lam-viec");

  const cacMuc: MucDieuHuong[] = [
    { duongDan: "/", nhan: "Trang chủ", icon: "trang-chu", nhom: "chung" },
    ...loiVao.map((l) => ({
      duongDan: l.duongDan,
      nhan: l.nhan,
      icon: l.icon,
      nhom: l.nhom,
      dem: soDem.get(l.duongDan)?.dem ?? undefined,
      cho: soDem.get(l.duongDan)?.cho,
      gap: soDem.get(l.duongDan)?.gap,
    })),
    {
      duongDan: "/hop-thu",
      nhan: "Hộp thư",
      icon: "hop-thu",
      nhom: laNhanVien ? "lam-viec" : "chung",
      dem: hopThu?.unread,
    },
  ];

  // Dòng phụ dưới tên: tên phòng nếu người dùng thuộc phòng ban, không thì thư điện tử.
  // `/me` chỉ trả mã vai trò, nên không hiện tên vai trò ở đây.
  const phongBan = soDem.get("/phong-ban")?.phongBan?.map((p) => p.label).join(" · ");

  return (
    <KhungUngDung
      cacMuc={cacMuc}
      nguoi={{ ten, chuCai: chuCaiDau(ten), mau: mauTheo(danhTinh.id), phu: phongBan || danhTinh.email }}
    >
      {khongGian.includes(canKhongGian) ? children : <KhongVaoDuoc />}
    </KhungUngDung>
  );
}
