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
//   Trong hạn      — đồng hồ đang chạy, chưa quá hạn
//   <trạng thái>   — mỗi trạng thái đồng hồ chưa chạy một nhóm, tên lấy từ dữ liệu
//                    (bộ quy tắc hiện tại: "Chờ phòng ban xác duyệt")
//   Chờ người gửi  — nhóm chỉ để theo dõi (#99), do cờ `watch_only` của dịch vụ quyết
//
// Chưa có nhóm "Sắp hết hạn": dữ liệu chưa có ngưỡng nào cho nó (#175), và giao diện
// không tự đặt. Tệp này không liệt kê trạng thái nào.
//
// Cả phòng nhìn chung một hàng đợi, nhưng nút "Giao cho tôi" thu về đúng phần việc của
// mình — bộ lọc gửi sang dịch vụ để số đếm đi cùng bộ lọc, và nằm trên địa chỉ trang.

import { User } from "lucide-react";
import Link from "next/link";

import { BangHangDoi, type DongHangDoi, type NhomHangDoi } from "@/components/bang-hang-doi";
import { TenCapCon } from "@/components/khung-ung-dung";
import { goiDichVu } from "@/lib/api";
import type { HangDoiPhongBan, MucHangDoiPhongBan } from "@/lib/kieu";
import { chuCaiDau, mauTheo } from "@/lib/nguoi";
import { docDongHo, docTuDong } from "@/lib/sla";
import { trinhBayTrangThai } from "@/lib/trang-thai";

export const dynamic = "force-dynamic";

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
    nguoiGui: m.requester_label ?? "Không rõ",
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
  };
}

export default async function HangDoiPhongBan({
  searchParams,
}: {
  searchParams: Promise<{ mine?: string }>;
}) {
  const { mine } = await searchParams;
  const cuaToi = mine === "1";
  const tatCa = await goiDichVu<HangDoiPhongBan>(
    cuaToi ? "/department/queue?mine=true" : "/department/queue",
  );
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
            <p>Dịch vụ ứng dụng không trả lời. Thử lại sau ít phút.</p>
            <Link href={cuaToi ? "/phong-ban?mine=1" : "/phong-ban"} className="nut nut-nho">
              Thử lại
            </Link>
          </div>
        </div>
      </>
    );
  }

  const theoDoi = new Set(tatCa.groups.filter((g) => g.watch_only).map((g) => g.code));
  const viec = tatCa.items.filter((m) => !theoDoi.has(m.state.code));
  const nhom: NhomHangDoi[] = [
    {
      ma: "qua-han",
      ten: "Quá hạn",
      mau: "var(--f-r-solid)",
      dong: viec.filter((m) => m.sla_overdue).map(thanhDong),
    },
    {
      // Ngưỡng khai theo loại yêu cầu trong dữ liệu (#175), giao diện chỉ đọc cờ
      ma: "sap-het-han",
      ten: "Sắp hết hạn",
      mau: "var(--f-a-solid)",
      dong: viec.filter((m) => m.sla_due_soon && !m.sla_overdue).map(thanhDong),
    },
    {
      ma: "trong-han",
      ten: "Trong hạn",
      mau: "var(--f-t-solid)",
      dong: viec
        .filter((m) => !m.sla_overdue && !m.sla_due_soon && m.sla_started)
        .map(thanhDong),
    },
    // Đồng hồ chưa chạy: mỗi trạng thái một nhóm, theo thứ tự nhóm dịch vụ trả về
    ...tatCa.groups
      .filter((g) => !g.watch_only)
      .map((g) => ({
        ma: g.code,
        ten: g.label,
        mau: `var(--f-${trinhBayTrangThai(g.code).ho}-solid)`,
        dong: viec
          .filter((m) => m.state.code === g.code && !m.sla_overdue && !m.sla_started)
          .map(thanhDong),
      })),
    {
      ma: "cho-nguoi-gui",
      ten: "Chờ người gửi",
      mau: "var(--ink-3)",
      dong: tatCa.items.filter((m) => theoDoi.has(m.state.code)).map(thanhDong),
    },
  ];

  return (
    <>
      {tieuDe}
      <BangHangDoi
        nhom={nhom}
        cot={{ nguoiGui: true, nguoiXuLy: true, cuoi: "Hạn" }}
        goiYTim="Tìm mã, tiêu đề, người gửi"
        phai={
          <Link href={cuaToi ? "/phong-ban" : "/phong-ban?mine=1"} className="chip" aria-pressed={cuaToi}>
            <User aria-hidden />
            Giao cho tôi
          </Link>
        }
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
