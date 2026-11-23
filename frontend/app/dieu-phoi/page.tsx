// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn hàng đợi của điều phối viên (#82, bố cục #170).
//
// Câu hỏi màn này trả lời: **hồ sơ nào đã chờ lâu nhất?** Hàng đợi mặc định xếp theo thời
// gian chờ ở trạng thái hiện tại, lâu nhất lên đầu — không theo hạn SLA, vì đồng hồ SLA
// chưa chạy ở những trạng thái này. Nó chỉ bắt đầu khi phòng ban nhận việc.
//
// Hàng tab lọc dựng từ `groups` mà dịch vụ trả về: "Cần làm" là cả hàng đợi, rồi mỗi
// trạng thái một tab kèm số. Trạng thái nào vào hàng đợi là do bộ quy tắc quyết — trạng
// thái nào vai trò điều phối có cạnh đi ra — nên tệp này không liệt kê trạng thái nào.
//
// Từ #232 dịch vụ trả từng trang: tìm, lọc theo loại yêu cầu, mức ưu tiên, phòng, cách xếp
// và trang đang xem nằm trên địa chỉ trang và đi thẳng tới dịch vụ. Số trên các tab tính
// trên cả hàng đợi đã lọc, không đổi khi sang trang.
//
// Bấm một dòng mở ngăn xem nhanh bên phải (#233, `?xem=<mã>`) mà không rời danh sách; ngăn
// dựng từ cùng các khối và cùng khối thao tác với trang chi tiết (`app/dieu-phoi/ho-so.tsx`).
//
// Chọn nhiều hồ sơ trên trang rồi đi một bước cho cả lô (#440): bước nào làm được hàng loạt, từ trạng
// thái nào, cần ô nào — dịch vụ trả ở `/coordination/bulk-transitions`; trang chỉ chuyển danh mục xuống.

import Link from "next/link";
import { redirect } from "next/navigation";

import { metaDieuPhoi, napHoSoDieuPhoi, ThaoTacDieuPhoi } from "@/app/dieu-phoi/ho-so";
import { chuyenHangLoatDieuPhoi } from "@/app/dieu-phoi/thao-tac";
import { BangHangDoi, type DongHangDoi } from "@/components/bang-hang-doi";
import { ChanTrang, ChipLoc } from "@/components/chan-trang";
import { DaiSoLoc } from "@/components/dai-so-loc";
import { ChonLoc } from "@/components/loc-url";
import { NganHoSo, NganLoi } from "@/components/ngan-ho-so";
import { goiDichVu } from "@/lib/api";
import { thoiLuong } from "@/lib/dinh-dang";
import type {
  DanhSachThaoTacHangLoat,
  HangDoi,
  LoaiYeuCau,
  MucHangDoi,
  MucUuTien,
  NhanCoMa,
  PhongBan,
} from "@/lib/kieu";
import { docTuDong } from "@/lib/sla";
import {
  chipLoc,
  docThamSo,
  docXep,
  duongTrang,
  duongVoi,
  duongXem,
  nhanCua,
  quaTrangCuoi,
  soTrang,
  truyVan,
  xemNhanh,
  type ThamSo,
} from "@/lib/trang";

export const dynamic = "force-dynamic";

const GOC = "/dieu-phoi";

/** Chỉ mã và nhãn đi xuống trình duyệt — hộp thoại hàng loạt không cần phần còn lại của danh mục. */
function thanhNhanCoMa(ds: NhanCoMa[] | null): NhanCoMa[] {
  return (ds ?? []).map(({ code, label }) => ({ code, label }));
}

function thanhDong(m: MucHangDoi, bayGio: Date, href: string, dangXem: boolean): DongHangDoi {
  const giay = Math.max(0, (bayGio.getTime() - new Date(m.state_entered_at).getTime()) / 1000);
  const tuDong = docTuDong(m);
  return {
    id: m.id,
    href,
    dangXem,
    ma: m.code,
    tieuDe: m.title,
    phu: m.requester_label ?? "Không rõ người gửi",
    choTraLoi: m.last_message_from_requester === true && !m.state.is_terminal,
    cuaMinh: m.requested_by_me === true,
    nguoiGui: m.requester_label ?? undefined,
    loai: m.request_type?.label ?? null,
    trangThai: { code: m.state.code, label: m.state.label },
    // Hồ sơ sắp tự trả về vì phòng ban chưa xác duyệt (#142): báo thay cho thời gian chờ
    cuoi: tuDong?.canhBao ? { chu: tuDong.cau, muc: "sap" } : { chu: thoiLuong(giay) },
    // Việc tiếp theo (#231): bước chính đang chờ tôi, không thì việc hệ thống sắp tự làm
    tiepTheo: m.needs_my_action && m.next_step_label
      ? { chu: m.next_step_label, cuaToi: true }
      : tuDong
        ? { chu: tuDong.cau, cuaToi: false }
        : null,
  };
}

export default async function HangDoiDieuPhoi({ searchParams }: { searchParams: Promise<ThamSo> }) {
  const sp = await searchParams;
  const state = docThamSo(sp, "state");
  const trang = soTrang(sp);
  const xep = docXep(sp, "cho");
  const [tatCa, cacLoai, cacMuc, cacPhong, hangLoat] = await Promise.all([
    goiDichVu<HangDoi>(
      `/coordination/queue?${truyVan(trang, {
        state,
        q: docThamSo(sp, "q"),
        request_type: docThamSo(sp, "loai"),
        priority: docThamSo(sp, "uu-tien"),
        department: docThamSo(sp, "phong"),
        sort: xep.ma,
      })}`,
    ),
    goiDichVu<LoaiYeuCau[]>("/request-types"),
    goiDichVu<MucUuTien[]>("/priorities"),
    goiDichVu<PhongBan[]>("/departments"),
    // Bước làm được hàng loạt (#440). Không nạp được thì hàng đợi vẫn như cũ, chỉ thiếu cột ô chọn
    goiDichVu<DanhSachThaoTacHangLoat>("/coordination/bulk-transitions"),
  ]);
  const tieuDe = <h1 className="an-di">Hàng đợi điều phối</h1>;

  if (tatCa === null) {
    return (
      <>
        {tieuDe}
        <div className="the">
          <div className="rong" data-loi="">
            <h2>Không tải được dữ liệu</h2>
            <p>Hệ thống không phản hồi. Thử lại sau ít phút.</p>
            <Link href={duongVoi(GOC, sp, {}, true)} className="nut nut-nho">
              Thử lại
            </Link>
          </div>
        </div>
      </>
    );
  }

  const cuoi = quaTrangCuoi(GOC, sp, tatCa);
  if (cuoi) redirect(cuoi);

  // Ngăn xem nhanh (#233): chỉ nạp hồ sơ khi địa chỉ có `?xem=`
  const xem = xemNhanh(GOC, sp, trang, tatCa);
  const hoSoXem = xem ? await napHoSoDieuPhoi(String(xem.ma)) : null;
  const ngan = !xem ? null : hoSoXem?.ok ? (
    <NganHoSo
      ho_so={hoSoXem.duLieu.ho_so}
      meta={metaDieuPhoi(hoSoXem.duLieu.ho_so)}
      lienHe={hoSoXem.duLieu.lienHe}
      thaoTac={<ThaoTacDieuPhoi d={hoSoXem.duLieu} ngan={{ sauKhiXong: xem.sau ?? xem.dong }} />}
      dieuHuong={xem}
    />
  ) : (
    <NganLoi maHoSo={xem.ma} dieuHuong={xem} cau={hoSoXem && !hoSoXem.ok ? hoSoXem.thongDiep : "Hệ thống không phản hồi."} />
  );

  const bayGio = new Date();
  const { chip, xoaHet } = chipLoc(GOC, sp, {
    q: (gt) => `Tìm: “${gt}”`,
    state: (gt) => nhanCua(tatCa.groups, gt),
    loai: (gt) => nhanCua(cacLoai, gt),
    "uu-tien": (gt) => `Ưu tiên ${nhanCua(cacMuc, gt).toLowerCase()}`,
    phong: (gt) => `Phòng ${nhanCua(cacPhong, gt)}`,
  });
  const tong = tatCa.groups.reduce((s, g) => s + g.count, 0);

  return (
    <>
      {tieuDe}
      <BangHangDoi
        nhom={[
          {
            ma: "tat-ca",
            ten: null,
            dong: tatCa.items.map((m) => thanhDong(m, bayGio, duongXem(GOC, sp, m.id), xem?.ma === m.id)),
          },
        ]}
        ngan={ngan}
        chonNhieu={
          hangLoat && hangLoat.actions.length > 0
            ? {
                cacBuoc: hangLoat.actions,
                toiDa: hangLoat.max_cases,
                danhMuc: {
                  "request-types": { ds: thanhNhanCoMa(cacLoai) },
                  priorities: { ds: thanhNhanCoMa(cacMuc), macDinh: cacMuc?.find((m) => m.is_default)?.code },
                  departments: { ds: thanhNhanCoMa(cacPhong) },
                },
                goc: GOC,
                hanhDong: chuyenHangLoatDieuPhoi,
              }
            : undefined
        }
        cot={{ loai: true, trangThai: true, tiepTheo: true, cuoi: "Đã chờ" }}
        goiYTim="Tìm mã, tiêu đề, người gửi"
        xepMacDinh="cho"
        trai={
          <DaiSoLoc
            nhan="Lọc theo trạng thái"
            cacO={[
              {
                href: duongVoi(GOC, sp, { state: null }),
                nhan: "Cần làm",
                so: tong,
                chon: !state,
                quaHan: tatCa.groups.reduce((s, g) => s + (g.overdue ?? 0), 0),
                sapHan: tatCa.groups.reduce((s, g) => s + (g.due_soon ?? 0), 0),
              },
              ...tatCa.groups.map((g) => ({
                href: duongVoi(GOC, sp, { state: g.code }),
                nhan: g.label,
                so: g.count,
                chon: state === g.code,
                quaHan: g.overdue,
                sapHan: g.due_soon,
              })),
            ]}
          />
        }
        phai={
          <>
            <ChonLoc ten="loai" nhan="Lọc theo loại yêu cầu" tatCa="Mọi loại" tuyChon={cacLoai ?? []} />
            <ChonLoc ten="uu-tien" nhan="Lọc theo mức ưu tiên" tatCa="Mọi mức ưu tiên" tuyChon={cacMuc ?? []} />
            <ChonLoc ten="phong" nhan="Lọc theo phòng" tatCa="Mọi phòng" tuyChon={cacPhong ?? []} />
          </>
        }
        chip={<ChipLoc chip={chip} xoaHet={xoaHet ?? GOC} />}
        chan={
          <ChanTrang
            tong={tatCa.total}
            tu={tatCa.offset}
            soDong={tatCa.limit}
            xep={xep.ten.toLowerCase()}
            truoc={trang > 1 ? duongTrang(GOC, sp, trang - 1) : null}
            sau={tatCa.offset + tatCa.limit < tatCa.total ? duongTrang(GOC, sp, trang + 1) : null}
          />
        }
        xoaLoc={xoaHet}
        khiTrong={{
          tieuDe: "Không còn hồ sơ nào chờ điều phối",
          cau: "Hồ sơ mới gửi và hồ sơ bị phòng ban trả về sẽ hiện ở đây.",
        }}
      />
    </>
  );
}
