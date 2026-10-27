// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn hàng đợi của điều phối viên (#82, bố cục #170).
//
// Câu hỏi màn này trả lời: **hồ sơ nào đã chờ lâu nhất?** Hàng đợi xếp theo thời gian
// chờ ở trạng thái hiện tại, lâu nhất lên đầu — không theo hạn SLA, vì đồng hồ SLA
// chưa chạy ở những trạng thái này. Nó chỉ bắt đầu khi phòng ban nhận việc.
//
// Hàng tab lọc dựng từ `groups` mà dịch vụ trả về: "Cần làm" là cả hàng đợi, rồi mỗi
// trạng thái một tab kèm số. Trạng thái nào vào hàng đợi là do bộ quy tắc quyết — trạng
// thái nào vai trò điều phối có cạnh đi ra — nên tệp này không liệt kê trạng thái nào.
// Bộ lọc nằm trên địa chỉ trang, tải lại hay gửi đường dẫn đều giữ nguyên.

import Link from "next/link";

import { DaiSoLoc } from "@/components/dai-so-loc";
import { BangHangDoi, type DongHangDoi } from "@/components/bang-hang-doi";
import { goiDichVu } from "@/lib/api";
import { thoiLuong } from "@/lib/dinh-dang";
import type { HangDoi, MucHangDoi } from "@/lib/kieu";
import { docTuDong } from "@/lib/sla";

export const dynamic = "force-dynamic";

function thanhDong(m: MucHangDoi, bayGio: Date): DongHangDoi {
  const giay = Math.max(0, (bayGio.getTime() - new Date(m.state_entered_at).getTime()) / 1000);
  const tuDong = docTuDong(m);
  return {
    id: m.id,
    href: `/dieu-phoi/${m.id}`,
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
    xep: {
      gap: m.sla_overdue ? 0 : tuDong?.canhBao || m.sla_due_soon ? 1 : 2,
      cho: new Date(m.state_entered_at).getTime(),
      moi: new Date(m.created_at).getTime(),
    },
  };
}

/** Số hồ sơ quá hạn và sắp hạn trong một nhóm — dòng phụ của ô trên dải số. */
function demGap(ds: MucHangDoi[]): { quaHan: number; sapHan: number } {
  return {
    quaHan: ds.filter((m) => m.sla_overdue).length,
    sapHan: ds.filter((m) => !m.sla_overdue && (m.sla_due_soon || m.auto_transition?.warn)).length,
  };
}


export default async function HangDoiDieuPhoi({
  searchParams,
}: {
  searchParams: Promise<{ state?: string }>;
}) {
  const { state } = await searchParams;
  const tatCa = await goiDichVu<HangDoi>("/coordination/queue");
  const tieuDe = <h1 className="an-di">Hàng đợi điều phối</h1>;

  if (tatCa === null) {
    return (
      <>
        {tieuDe}
        <div className="the">
          <div className="rong" data-loi="">
            <h2>Không tải được dữ liệu</h2>
            <p>Hệ thống không phản hồi. Thử lại sau ít phút.</p>
            <Link href={state ? `/dieu-phoi?state=${encodeURIComponent(state)}` : "/dieu-phoi"} className="nut nut-nho">
              Thử lại
            </Link>
          </div>
        </div>
      </>
    );
  }

  // Lọc lại phía máy chủ Next.js thay vì gọi lần hai kèm `?state=`: một lần gọi đã có đủ
  // số đếm cho mọi tab lẫn danh sách, và hàng đợi ở quy mô này không lớn.
  const bayGio = new Date();
  const cacMuc = tatCa.items.filter((m) => !state || m.state.code === state);

  return (
    <>
      {tieuDe}
      <BangHangDoi
        nhom={[{ ma: "tat-ca", ten: null, dong: cacMuc.map((m) => thanhDong(m, bayGio)) }]}
        cot={{ loai: true, trangThai: true, tiepTheo: true, cuoi: "Đã chờ" }}
        goiYTim="Tìm mã, tiêu đề, người gửi"
        trai={
          <DaiSoLoc
            nhan="Lọc theo trạng thái"
            cacO={[
              { href: "/dieu-phoi", nhan: "Cần làm", so: tatCa.items.length, chon: !state, ...demGap(tatCa.items) },
              ...tatCa.groups.map((g) => ({
                href: `/dieu-phoi?state=${encodeURIComponent(g.code)}`,
                nhan: g.label,
                so: g.count,
                chon: state === g.code,
                ...demGap(tatCa.items.filter((m) => m.state.code === g.code)),
              })),
            ]}
          />
        }
        khiTrong={
          state
            ? { tieuDe: "Không có hồ sơ ở trạng thái này", cau: "Chọn “Cần làm” để xem cả hàng đợi." }
            : {
                tieuDe: "Không còn hồ sơ nào chờ điều phối",
                cau: "Hồ sơ mới gửi và hồ sơ bị phòng ban trả về sẽ hiện ở đây.",
              }
        }
      />
    </>
  );
}
