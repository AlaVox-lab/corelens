// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Trang chủ — nơi mọi người dùng đến đầu tiên, và nơi đăng nhập xong quay về.
//
// Mở lên là biết hôm nay phải làm gì (#228). Ba phần:
//
//   Cần bạn xử lý — mọi hồ sơ đang chờ chính người xem làm bước chính, gộp từ mọi vai họ
//             có, xếp theo độ gấp. Cờ `needs_my_action` và nhãn bước do dịch vụ tính từ dữ
//             liệu quy tắc (#227); trang này không biết tên trạng thái hay vai trò nào.
//   Dải số    — chờ bạn, quá hạn, sắp hạn, và số hồ sơ đang mở ở khu vực chính của họ.
//   Tổng quan — tách theo vai: hồ sơ của tôi, hàng đợi điều phối, hàng đợi phòng ban. Quản
//             trị viên thấy thêm tình trạng hệ thống (#229) — người khác không thấy nữa.
//
// Trang chưa đăng nhập không còn bảng trạng thái hệ thống: tình trạng cụm chỉ có nghĩa với
// người vận hành, và họ xem ở màn Hệ thống sau khi đăng nhập (navigator chốt 27/10).
//
// Từ #232 các danh sách có phân trang. Trang chủ không tải cả danh sách: với mỗi vai, một lần
// gọi một dòng (`limit=1`) lấy số đếm trên cả danh sách — cùng lời gọi với thanh bên — và một
// lần gọi kèm `needs_action=true` lấy đúng những hồ sơ đang chờ người xem.

import { AlarmClock, CircleCheck, Clock, FolderOpen, Hand } from "lucide-react";
import Link from "next/link";

import { KhongPhanHoi, KhungLamViec } from "@/components/khung-lam-viec";
import { SoCuon } from "@/components/so-cuon";
import { docSucKhoe, TheHeThong } from "@/components/the-he-thong";
import { ViecCanLam, type DongViec } from "@/components/viec-can-lam";
import { docDichVu, goiDichVu, type DanhTinh } from "@/lib/api";
import type { DanhSachHoSo, HangDoi, HangDoiPhongBan, HoSoTomTat, NhanCoMa } from "@/lib/kieu";
import { docDongHo, docTuDong, type NguoiXem } from "@/lib/sla";

export const dynamic = "force-dynamic";

const XA_NHAT = Number.MAX_SAFE_INTEGER;

/** Việc chờ một người ở một vai — trần của dịch vụ (`GIOI_HAN_TOI_DA`), vượt mức đó là chuyện khác. */
const CHO_TOI = "needs_action=true&limit=200";

function ChuaDangNhap() {
  // Căn giữa màn, ngắn, nút đăng nhập nổi bật (#236) — không còn bảng kỹ thuật (#229)
  return (
    <main className="chua-dang-nhap">
      <span className="logo-lon mono">YC</span>
      <h1 className="tieu-de-trang">Cổng yêu cầu nội bộ</h1>
      <p className="cdn-phu">Corelens · Hệ điều hành Doanh nghiệp số</p>
      <p className="cdn-mo-ta">
        Gửi yêu cầu nội bộ, theo dõi hồ sơ, và biết ngay hôm nay việc nào đang chờ bạn.
      </p>
      <a href="/api/auth/login" className="nut" data-loai="chinh">
        Đăng nhập bằng tài khoản công ty
      </a>
    </main>
  );
}

type Nguon = {
  ds: HoSoTomTat[];
  href: (h: HoSoTomTat) => string;
  vai: string;
  nguoiXem: NguoiXem;
  phu: (h: HoSoTomTat) => string | null;
};

/** Một hồ sơ đang chờ người xem → một dòng việc, kèm câu hạn và khóa sắp xếp dựng sẵn. */
function thanhDong(h: HoSoTomTat, n: Nguon, nhieuVai: boolean): DongViec {
  const tuDong = docTuDong(h);
  const dongHo = docDongHo(h, n.nguoiXem);
  const gap: DongViec["gap"] = h.sla_overdue ? 0 : tuDong?.canhBao || h.sla_due_soon ? 1 : 2;
  const han = h.sla_overdue || h.sla_due_soon ? dongHo.cau : (tuDong?.cau ?? null);
  const moc = h.sla_due_at ?? h.auto_transition?.at;
  const vao = (h as HoSoTomTat & { state_entered_at?: string }).state_entered_at ?? h.updated_at;
  return {
    khoa: `${n.vai}-${h.id}`,
    href: n.href(h),
    ma: h.code,
    tieuDe: h.title,
    trangThai: { ma: h.state.code, nhan: h.state.label },
    han,
    gap,
    phu: n.phu(h),
    vai: nhieuVai ? n.vai : null,
    buoc: h.next_step_label ?? "Mở hồ sơ",
    xep: { han: moc ? Date.parse(moc) : XA_NHAT, cho: Date.parse(vao), moi: Date.parse(h.created_at) },
  };
}

function OSo({ icon: Icon, nhan, so, phu, xau }: { icon: typeof Hand; nhan: string; so: number; phu?: string; xau?: boolean }) {
  return (
    <div className="o-so">
      <span className="o-so-nhan">
        <span className="o-so-icon" aria-hidden>
          <Icon />
        </span>
        {nhan}
      </span>
      <strong>
        <SoCuon so={so} />
      </strong>
      {phu ? <em data-xau={xau ? "" : undefined}>{phu}</em> : null}
    </div>
  );
}

function TongQuan({ tieuDe, href, dong }: { tieuDe: string; href: string; dong: { nhan: string; so: number }[] }) {
  const coSo = dong.filter((d) => d.so > 0);
  if (coSo.length === 0) return null;
  return (
    <section className="the">
      <div className="khoi-dau">
        <h2>{tieuDe}</h2>
        <Link href={href}>Xem tất cả</Link>
      </div>
      <ul className="ds-tong-quan">
        {coSo.map((d) => (
          <li key={d.nhan}>
            <span>{d.nhan}</span>
            <b>{d.so}</b>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default async function TrangChu() {
  const ketQua = await docDichVu<DanhTinh>("/me");
  // Dịch vụ không phản hồi: trang lỗi chung, không giả làm trang chưa đăng nhập (#235)
  if (!ketQua.ok && ketQua.ma === "khong-ket-noi-duoc") return <KhongPhanHoi />;
  if (!ketQua.ok) return <ChuaDangNhap />;
  const danhTinh = ketQua.duLieu;

  const kg = danhTinh.workspaces ?? ["portal"];
  const coDieuPhoi = kg.includes("coordination");
  const coPhongBan = kg.includes("department");
  const [cuaToi, choCuaToi, dieuPhoi, choDieuPhoi, phongBan, choPhongBan, sucKhoe] = await Promise.all([
    goiDichVu<DanhSachHoSo>("/requests?limit=1"),
    goiDichVu<DanhSachHoSo>(`/requests?${CHO_TOI}`),
    coDieuPhoi ? goiDichVu<HangDoi>("/coordination/queue?limit=1") : null,
    coDieuPhoi ? goiDichVu<HangDoi>(`/coordination/queue?${CHO_TOI}`) : null,
    coPhongBan ? goiDichVu<HangDoiPhongBan>("/department/queue?limit=1") : null,
    coPhongBan ? goiDichVu<HangDoiPhongBan>(`/department/queue?${CHO_TOI}`) : null,
    kg.includes("system") ? docSucKhoe() : null,
  ]);

  const cacNguon = ([
    choCuaToi && {
      ds: choCuaToi.items,
      href: (h: HoSoTomTat) => `/yeu-cau/${h.id}`,
      vai: "Người gửi",
      nguoiXem: "nguoi-gui" as const,
      phu: () => null,
    },
    choDieuPhoi && {
      ds: choDieuPhoi.items,
      href: (h: HoSoTomTat) => `/dieu-phoi/${h.id}`,
      vai: "Điều phối",
      nguoiXem: "noi-bo" as const,
      phu: (h: HoSoTomTat) => (h as HoSoTomTat & { requester_label?: string }).requester_label ?? null,
    },
    choPhongBan && {
      ds: choPhongBan.items,
      href: (h: HoSoTomTat) => `/phong-ban/${h.id}`,
      vai: "Phòng ban",
      nguoiXem: "noi-bo" as const,
      phu: (h: HoSoTomTat) => {
        const giao = (h as HoSoTomTat & { assignee_label?: string | null }).assignee_label;
        return giao ? `Đang giao: ${giao}` : null;
      },
    },
  ] as (Nguon | null)[]).filter((n): n is Nguon => n !== null);

  // Dịch vụ đã lọc đúng hồ sơ đang chờ người xem (`needs_action`)
  const coViec = cacNguon.filter((n) => n.ds.length > 0);
  const nhieuVai = coViec.length > 1;
  const dong = coViec.flatMap((n) => n.ds.map((h) => thanhDong(h, n, nhieuVai)));

  // Số chờ đếm trên cả danh sách của từng vai, không phụ thuộc trần số dòng đã tải
  const soCho = [choCuaToi, choDieuPhoi, choPhongBan].reduce((tong, ds) => tong + (ds?.waiting_me ?? 0), 0);
  const quaHan = dong.filter((d) => d.gap === 0).length;
  const sapHan = dong.filter((d) => d.gap === 1).length;
  const theoDoi = (phongBan?.groups ?? []).filter((g) => g.watch_only).reduce((tong, g) => tong + g.count, 0);
  const oCuoi = dieuPhoi
    ? { nhan: "Trong hàng đợi điều phối", so: dieuPhoi.total }
    : phongBan
      ? { nhan: "Phòng đang giữ", so: phongBan.total - theoDoi }
      : { nhan: "Hồ sơ của tôi đang mở", so: cuaToi?.open_count ?? 0 };

  const ten = danhTinh.name ?? danhTinh.username ?? danhTinh.id;
  const cauChao = soCho
    ? `Hôm nay có ${soCho} việc chờ bạn${quaHan ? `, trong đó ${quaHan} việc đã quá hạn` : ""}.`
    : "Hôm nay không có việc nào chờ bạn.";
  const loiTiep = kg.includes("coordination")
    ? { href: "/dieu-phoi", nhan: "Mở hàng đợi điều phối" }
    : kg.includes("department")
      ? { href: "/phong-ban", nhan: "Mở hàng đợi phòng ban" }
      : kg.includes("system")
        ? { href: "/he-thong", nhan: "Mở màn Hệ thống" }
        : { href: "/yeu-cau/moi", nhan: "Gửi yêu cầu mới" };

  const phongNhan = (phongBan?.departments ?? []).map((p: NhanCoMa) => p.label).join(" · ");

  return (
    <KhungLamViec canKhongGian="portal">
      <div className="trang-chu">
        <h1 className="tieu-de-trang">Chào {ten}</h1>
        <p className="cau-chao">{cauChao}</p>
        {(danhTinh.acting_for ?? []).map((u) => (
          <p key={`${u.delegator_label}-${u.ends_on}`} className="the-goi-y" role="status" data-dai-uy-quyen style={{ marginTop: "12px" }}>
            Bạn đang làm thay <b>{u.delegator_label}</b> ({u.roles.join(", ")} · {u.department_label}) đến hết ngày{" "}
            {u.ends_on.split("-").reverse().join("/")}. Việc của người đó hiện trong việc chờ bạn; mọi thao tác ghi
            &ldquo;thay mặt&rdquo;. <a href="/uy-quyen">Xem ủy quyền</a>
          </p>
        ))}

        <div className="dai-so">
          <OSo icon={Hand} nhan="Chờ bạn" so={soCho} />
          <OSo icon={AlarmClock} nhan="Quá hạn" so={quaHan} phu={quaHan ? "Làm trước tiên" : undefined} xau />
          <OSo icon={Clock} nhan="Sắp hạn hoặc sắp tự đi" so={sapHan} />
          <OSo icon={FolderOpen} nhan={oCuoi.nhan} so={oCuoi.so} />
        </div>

        <div className="luoi-chu">
          <div className="cot-viec">
            {dong.length ? (
              <>
                <ViecCanLam dong={dong} />
                {/* Mỗi vai tải tối đa 200 việc chờ (`CHO_TOI`); vượt trần thì nói rõ phần còn
                    lại nằm ở đâu, để con số trên ô và danh sách không kể hai chuyện */}
                {soCho > dong.length && (
                  <p className="ghi-con-lai">
                    Đang hiện {dong.length} trên {soCho} việc chờ bạn. Việc còn lại xem ở{" "}
                    <Link href={coDieuPhoi ? "/dieu-phoi" : coPhongBan ? "/phong-ban" : "/yeu-cau"}>
                      {coDieuPhoi ? "hàng đợi điều phối" : coPhongBan ? "hàng đợi phòng ban" : "Hồ sơ của tôi"}
                    </Link>
                    .
                  </p>
                )}
              </>
            ) : (
              <section className="the khoi-viec">
                <div className="khoi-dau">
                  <h2>Cần bạn xử lý</h2>
                </div>
                <div className="rong">
                  <span className="rong-vong" aria-hidden>
                    <CircleCheck />
                  </span>
                  <h3>Không có việc nào chờ bạn</h3>
                  <p>Hồ sơ cần bạn làm bước tiếp theo sẽ hiện ở đây, việc gấp nhất lên đầu.</p>
                  <Link className="nut" href={loiTiep.href}>
                    {loiTiep.nhan}
                  </Link>
                </div>
              </section>
            )}
          </div>

          <div className="cot-tong-quan">
            {dieuPhoi ? (
              <TongQuan
                tieuDe="Hàng đợi điều phối"
                href="/dieu-phoi"
                dong={dieuPhoi.groups.map((g) => ({ nhan: g.label, so: g.count }))}
              />
            ) : null}
            {phongBan ? (
              <TongQuan
                tieuDe={phongNhan ? `Phòng ${phongNhan}` : "Hàng đợi phòng ban"}
                href="/phong-ban"
                dong={phongBan.groups.map((g) => ({ nhan: g.label, so: g.count }))}
              />
            ) : null}
            <TongQuan
              tieuDe="Hồ sơ của tôi đang mở"
              href="/yeu-cau"
              dong={(cuaToi?.groups ?? []).filter((g) => !g.is_terminal).map((g) => ({ nhan: g.label, so: g.count }))}
            />
            {kg.includes("system") ? <TheHeThong sucKhoe={sucKhoe} /> : null}
          </div>
        </div>
      </div>
    </KhungLamViec>
  );
}
