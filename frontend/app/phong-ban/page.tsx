// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Hàng đợi của buồng lái phòng ban (#83, bố cục #170).
//
// Câu hỏi màn này trả lời: **hồ sơ nào của phòng sắp trễ, hay đã trễ?** Khác hàng đợi
// điều phối — xếp theo thời gian chờ — vì ở đây đồng hồ SLA đang chạy, nên thời hạn còn
// lại mới là con số cần nhìn. Thứ tự do dịch vụ xếp: quá hạn lên đầu, rồi gần hạn nhất.
//
// Hàng đợi chia nhóm theo mức gấp (#170), nhóm gấp nhất trên cùng:
//
//   Quá hạn        — cờ `sla_overdue` của dịch vụ
//   Sắp hết hạn    — ngưỡng khai theo loại yêu cầu trong dữ liệu (#175)
//   Trong hạn      — đồng hồ đang chạy, chưa quá hạn
//   <trạng thái>   — mỗi trạng thái đồng hồ chưa chạy một nhóm, tên lấy từ dữ liệu
//                    (bộ quy tắc hiện tại: "Chờ phòng ban xác duyệt")
//   Chờ người gửi  — nhóm chỉ để theo dõi (#99), do cờ `watch_only` của dịch vụ quyết
//
// Từ #232 dịch vụ chia nhóm trên cả hàng đợi (`urgency_groups`, `urgency` trên từng hồ sơ) và
// trả từng trang, nên số trên dải lọc đúng dù trang chỉ chứa một phần. Tìm, lọc, cách xếp và
// trang đang xem nằm trên địa chỉ trang. Tệp này không liệt kê trạng thái nào.
//
// Cả phòng nhìn chung một hàng đợi, nhưng nút "Giao cho tôi" thu về đúng phần việc của
// mình — bộ lọc gửi sang dịch vụ để số đếm đi cùng bộ lọc, và nằm trên địa chỉ trang.

import { User } from "lucide-react";
import Link from "next/link";
import { redirect } from "next/navigation";

import { BangHangDoi, type DongHangDoi, type NhomHangDoi } from "@/components/bang-hang-doi";
import { ChanTrang, ChipLoc } from "@/components/chan-trang";
import { DaiSoLoc } from "@/components/dai-so-loc";
import { TenCapCon } from "@/components/khung-ung-dung";
import { ChonLoc } from "@/components/loc-url";
import { goiDichVu } from "@/lib/api";
import type { HangDoiPhongBan, LoaiYeuCau, MucHangDoiPhongBan, MucUuTien } from "@/lib/kieu";
import { chuCaiDau, mauTheo } from "@/lib/nguoi";
import { docDongHo, docTuDong } from "@/lib/sla";
import {
  chipLoc,
  docThamSo,
  docXep,
  duongTrang,
  duongVoi,
  nhanCua,
  quaTrangCuoi,
  soTrang,
  truyVan,
  type ThamSo,
} from "@/lib/trang";
import { trinhBayTrangThai } from "@/lib/trang-thai";

export const dynamic = "force-dynamic";

const GOC = "/phong-ban";

/** Màu chấm đầu nhóm. Bốn nhóm theo hạn do dịch vụ đặt mã; nhóm theo trạng thái lấy màu trạng thái. */
const MAU_NHOM: Record<string, string> = {
  "qua-han": "var(--f-r-solid)",
  "sap-het-han": "var(--f-a-solid)",
  "trong-han": "var(--f-t-solid)",
  "cho-nguoi-gui": "var(--ink-3)",
};

function thanhDong(m: MucHangDoiPhongBan): DongHangDoi {
  // Hồ sơ sắp tự đi vì nằm im quá hạn chờ (#142): câu đó quan trọng hơn câu cam kết chưa
  // chạy, nên thay chỗ trong khoảng báo trước
  const tuDong = docTuDong(m);
  const dongHo = tuDong?.canhBao ? tuDong : docDongHo(m);
  const tenGiao = m.assigned_to_me ? "Bạn" : (m.assignee_label ?? "Một người trong phòng");
  return {
    id: m.id,
    href: `/phong-ban/${m.id}`,
    ma: m.code,
    tieuDe: m.title,
    phu: m.request_type?.label ?? "Chưa rõ loại",
    choTraLoi: m.last_message_from_requester === true && !m.state.is_terminal,
    nguoiGui: m.requester_label ?? "Không rõ người gửi",
    giao: m.assignee_id
      ? { ten: tenGiao, mau: mauTheo(m.assignee_id), chuCai: chuCaiDau(m.assignee_label ?? "?") }
      : null,
    cuoi: {
      chu: dongHo.cau,
      // Quá hạn đỏ; sắp hết hạn vàng (#175); đồng hồ đứng (chưa nhận việc, đang chờ người
      // gửi) thì nhạt
      muc:
        dongHo === tuDong
          ? "sap"
          : dongHo.canhBao
            ? "qua"
            : !m.sla_started || m.sla_paused
              ? "dung"
              : m.sla_due_soon
                ? "sap"
                : undefined,
    },
    // Việc tiếp theo (#231): bước chính đang chờ tôi, không thì ai đang giữ việc
    tiepTheo: m.needs_my_action && m.next_step_label
      ? { chu: m.next_step_label, cuaToi: true }
      : tuDong
        ? { chu: tuDong.cau, cuaToi: false }
        : m.assignee_id && !m.assigned_to_me
          ? { chu: `${tenGiao} đang làm`, cuaToi: false }
          : null,
  };
}

export default async function HangDoiPhongBan({ searchParams }: { searchParams: Promise<ThamSo> }) {
  const sp = await searchParams;
  const cuaToi = docThamSo(sp, "mine") === "1";
  const nhomChon = docThamSo(sp, "nhom");
  const trang = soTrang(sp);
  const xep = docXep(sp, "gap");
  const [tatCa, cacLoai, cacMuc] = await Promise.all([
    goiDichVu<HangDoiPhongBan>(
      `/department/queue?${truyVan(trang, {
        mine: cuaToi,
        group: nhomChon,
        q: docThamSo(sp, "q"),
        request_type: docThamSo(sp, "loai"),
        priority: docThamSo(sp, "uu-tien"),
        sort: xep.ma,
      })}`,
    ),
    goiDichVu<LoaiYeuCau[]>("/request-types"),
    goiDichVu<MucUuTien[]>("/priorities"),
  ]);
  const tenPhong = tatCa?.departments.map((p) => p.label).join(" · ");

  const tieuDe = (
    <>
      {tenPhong && <TenCapCon ten={tenPhong} />}
      <h1 className="an-di">{tenPhong ? `Hàng đợi phòng ${tenPhong}` : "Hàng đợi phòng ban"}</h1>
    </>
  );

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

  // Dịch vụ xếp theo thứ tự nhóm trước, nên các dòng của trang nằm liền nhau theo nhóm
  const nhom: NhomHangDoi[] = tatCa.urgency_groups.map((g) => ({
    ma: g.code,
    ten: g.label,
    mau: MAU_NHOM[g.code] ?? `var(--f-${trinhBayTrangThai(g.code).ho}-solid)`,
    tong: g.count,
    dong: tatCa.items.filter((m) => m.urgency === g.code).map(thanhDong),
  }));

  // "Giao cho tôi" là chế độ xem của hàng đợi, không phải bộ lọc có chip: nó có nút riêng
  const { chip, xoaHet } = chipLoc(GOC, sp, {
    q: (gt) => `Tìm: “${gt}”`,
    nhom: (gt) => nhanCua(tatCa.urgency_groups, gt),
    loai: (gt) => nhanCua(cacLoai, gt),
    "uu-tien": (gt) => `Ưu tiên ${nhanCua(cacMuc, gt).toLowerCase()}`,
  });

  return (
    <>
      {tieuDe}
      <BangHangDoi
        nhom={nhom}
        trai={
          <DaiSoLoc
            nhan="Lọc theo nhóm"
            cacO={[
              {
                href: duongVoi(GOC, sp, { nhom: null }),
                nhan: "Tất cả",
                so: tatCa.urgency_groups.reduce((tong, g) => tong + g.count, 0),
                chon: !nhomChon,
              },
              // Nhóm rỗng không thành ô: dải số chỉ nói về hồ sơ đang có
              ...tatCa.urgency_groups.map((g) => ({
                href: duongVoi(GOC, sp, { nhom: g.code }),
                nhan: g.label,
                so: g.count,
                chon: nhomChon === g.code,
                quaHan: g.overdue,
                sapHan: g.due_soon,
              })),
            ]}
          />
        }
        cot={{ nguoiGui: true, nguoiXuLy: true, tiepTheo: true, cuoi: "Hạn" }}
        goiYTim="Tìm mã, tiêu đề, người gửi"
        xepMacDinh="gap"
        phai={
          <>
            <ChonLoc ten="loai" nhan="Lọc theo loại yêu cầu" tatCa="Mọi loại" tuyChon={cacLoai ?? []} />
            <ChonLoc ten="uu-tien" nhan="Lọc theo mức ưu tiên" tatCa="Mọi mức ưu tiên" tuyChon={cacMuc ?? []} />
            <Link
              href={duongVoi(GOC, sp, { mine: cuaToi ? null : "1" })}
              className="chip"
              aria-pressed={cuaToi}
            >
              <User aria-hidden />
              Giao cho tôi
            </Link>
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
        khiTrong={
          cuaToi
            ? { tieuDe: "Chưa có hồ sơ nào giao cho bạn", cau: "Hồ sơ trưởng phòng giao cho bạn sẽ hiện ở đây." }
            : {
                tieuDe: "Phòng chưa có hồ sơ nào",
                cau: "Hồ sơ điều phối viên chuyển về phòng sẽ hiện ở đây để nhận và giao người xử lý.",
              }
        }
      />
    </>
  );
}
