// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Bảng Kanban của buồng lái phòng ban (#403).
//
// Hàng đợi (`/phong-ban`) trả lời "hồ sơ nào sắp trễ"; bảng này trả lời "việc của phòng đang dồn ở bước
// nào". Mỗi cột một trạng thái — tên và thứ tự cột lấy từ danh mục trạng thái của dịch vụ (`GET /states`),
// tệp này không biết trạng thái nào. Cột và thẻ dựng bằng bảng dùng chung với buồng lái điều phối
// (`components/bang-kanban.tsx`, #560); thẻ của phòng thêm người xử lý.
//
// Dữ liệu là chính hàng đợi phòng ban (`/department/queue`, cùng cửa nhìn thấy, cùng bộ lọc "Giao cho tôi"),
// lấy một lần tối đa số dòng dịch vụ cho phép.

import { List, User } from "lucide-react";
import Link from "next/link";

import { BangKanban, chiaCot, TOI_DA_BANG } from "@/components/bang-kanban";
import { TenCapCon } from "@/components/khung-ung-dung";
import { goiDichVu } from "@/lib/api";
import type { HangDoiPhongBan, MucHangDoiPhongBan, TrangThai } from "@/lib/kieu";
import { chuCaiDau, mauTheo } from "@/lib/nguoi";

export const dynamic = "force-dynamic";

type ThamSo = Record<string, string | string[] | undefined>;

/** Người xử lý ở chân thẻ: ảnh chữ cái khi đã giao, không thì "Chưa giao". */
function nguoiXuLy(m: MucHangDoiPhongBan) {
  return m.assignee_id ? (
    <span
      className="av av-nho"
      data-c={mauTheo(m.assignee_id)}
      title={m.assigned_to_me ? "Bạn" : (m.assignee_label ?? "Một người trong phòng")}
    >
      {chuCaiDau(m.assignee_label ?? "?")}
    </span>
  ) : (
    <span className="kb-phu">Chưa giao</span>
  );
}

export default async function BangPhongBan({ searchParams }: { searchParams: Promise<ThamSo> }) {
  const sp = await searchParams;
  const cuaToi = sp.mine === "1";
  const q = new URLSearchParams({ limit: String(TOI_DA_BANG), offset: "0" });
  if (cuaToi) q.set("mine", "true");

  const [hangDoi, cacTrangThai] = await Promise.all([
    goiDichVu<HangDoiPhongBan>(`/department/queue?${q}`),
    goiDichVu<TrangThai[]>("/states"),
  ]);
  const tenPhong = hangDoi?.departments.map((p) => p.label).join(" · ");

  const dau = (
    <>
      {tenPhong && <TenCapCon ten={tenPhong} />}
      <h1 className="an-di">{tenPhong ? `Bảng việc phòng ${tenPhong}` : "Bảng việc phòng ban"}</h1>
      <div className="kb-thanh">
        <Link href="/phong-ban" className="chip">
          <List aria-hidden />
          Dạng danh sách
        </Link>
        <Link href={cuaToi ? "/phong-ban/bang" : "/phong-ban/bang?mine=1"} className="chip" aria-current={cuaToi ? "true" : undefined}>
          <User aria-hidden />
          Giao cho tôi
        </Link>
      </div>
    </>
  );

  if (hangDoi === null) {
    return (
      <>
        {dau}
        <div className="the">
          <div className="rong" data-loi="">
            <h2>Không tải được dữ liệu</h2>
            <p>Hệ thống không phản hồi. Thử lại sau ít phút.</p>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      {dau}
      <BangKanban
        cot={chiaCot(hangDoi.items, cacTrangThai ?? [])}
        goc="/phong-ban"
        nguoi={nguoiXuLy}
        tong={hangDoi.total}
        khiTrong={{
          tieuDe: cuaToi ? "Chưa có hồ sơ nào giao cho bạn" : "Phòng chưa có hồ sơ nào",
          cau: "Hồ sơ điều phối viên chuyển về phòng sẽ hiện ở đây, chia cột theo trạng thái.",
        }}
      />
    </>
  );
}
