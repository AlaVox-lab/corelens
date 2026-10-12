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
  };
}

function Tab({ href, nhan, so, chon }: { href: string; nhan: string; so: number; chon: boolean }) {
  return (
    <Link href={href} aria-current={chon ? "page" : undefined}>
      {nhan} <b>{so}</b>
    </Link>
  );
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
            <p>Dịch vụ ứng dụng không trả lời. Thử lại sau ít phút.</p>
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
        cot={{ loai: true, trangThai: true, cuoi: "Đã chờ" }}
        goiYTim="Tìm mã, tiêu đề, người gửi"
        trai={
          <nav className="tab-dem" aria-label="Lọc theo trạng thái">
            <Tab href="/dieu-phoi" nhan="Cần làm" so={tatCa.items.length} chon={!state} />
            {tatCa.groups.map((g) => (
              <Tab
                key={g.code}
                href={`/dieu-phoi?state=${encodeURIComponent(g.code)}`}
                nhan={g.label}
                so={g.count}
                chon={state === g.code}
              />
            ))}
          </nav>
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
