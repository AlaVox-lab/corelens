// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Bảng Kanban của buồng lái điều phối (#560).
//
// Hàng đợi (`/dieu-phoi`) trả lời "hồ sơ nào đã chờ lâu nhất"; bảng này trả lời "việc điều phối đang dồn ở
// bước nào". Mỗi cột một trạng thái của hàng đợi — danh mục và thứ tự cột là `groups` mà dịch vụ trả về, theo
// thứ tự hiển thị của bộ quy tắc; tệp này không biết trạng thái nào. Cột và thẻ dựng bằng bảng dùng chung với
// buồng lái phòng ban (`components/bang-kanban.tsx`).
//
// Dữ liệu là chính hàng đợi điều phối (`/coordination/queue`), cùng cửa nhìn thấy và cùng tham số lọc trên địa
// chỉ trang với dạng danh sách — chuyển qua lại giữ nguyên bộ lọc — lấy một lần tối đa số dòng dịch vụ cho
// phép. Người không vào được không gian điều phối gặp lời báo của khung (`layout.tsx`), như ở hàng đợi.

import { List } from "lucide-react";
import Link from "next/link";

import { BangKanban, chiaCot, TOI_DA_BANG } from "@/components/bang-kanban";
import { ChipLoc } from "@/components/chan-trang";
import { TenCapCon } from "@/components/khung-ung-dung";
import { goiDichVu } from "@/lib/api";
import type { HangDoi, LoaiYeuCau, MucUuTien, PhongBan } from "@/lib/kieu";
import { chipLoc, docThamSo, docXep, duongVoi, nhanCua, truyVan, type ThamSo } from "@/lib/trang";

export const dynamic = "force-dynamic";

const GOC = "/dieu-phoi";
const GOC_BANG = "/dieu-phoi/bang";

export default async function BangDieuPhoi({ searchParams }: { searchParams: Promise<ThamSo> }) {
  const sp = await searchParams;
  // Cùng tham số với hàng đợi dạng danh sách; khác mỗi số dòng: bảng đọc một lần tới trần của dịch vụ
  const q = new URLSearchParams(
    truyVan(1, {
      state: docThamSo(sp, "state"),
      q: docThamSo(sp, "q"),
      request_type: docThamSo(sp, "loai"),
      priority: docThamSo(sp, "uu-tien"),
      department: docThamSo(sp, "phong"),
      sort: docXep(sp, "cho").ma,
    }),
  );
  q.set("limit", String(TOI_DA_BANG));

  const [hangDoi, cacLoai, cacMuc, cacPhong] = await Promise.all([
    goiDichVu<HangDoi>(`/coordination/queue?${q}`),
    goiDichVu<LoaiYeuCau[]>("/request-types"),
    goiDichVu<MucUuTien[]>("/priorities"),
    goiDichVu<PhongBan[]>("/departments"),
  ]);

  const dau = (
    <>
      <TenCapCon ten="Dạng bảng" chuThuong />
      <h1 className="an-di">Bảng việc điều phối</h1>
      <div className="kb-thanh">
        <Link href={duongVoi(GOC, sp, {})} className="chip">
          <List aria-hidden />
          Dạng danh sách
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

  // Bộ lọc mang từ dạng danh sách hiện thành chip như ở đó, để bảng không âm thầm thiếu thẻ
  const { chip, xoaHet } = chipLoc(GOC_BANG, sp, {
    q: (gt) => `Tìm: “${gt}”`,
    state: (gt) => nhanCua(hangDoi.groups, gt),
    loai: (gt) => nhanCua(cacLoai, gt),
    "uu-tien": (gt) => `Ưu tiên ${nhanCua(cacMuc, gt).toLowerCase()}`,
    phong: (gt) => `Phòng ${nhanCua(cacPhong, gt)}`,
  });

  return (
    <>
      {dau}
      <ChipLoc chip={chip} xoaHet={xoaHet ?? GOC_BANG} />
      <BangKanban
        cot={chiaCot(hangDoi.items, hangDoi.groups)}
        goc={GOC}
        tong={hangDoi.total}
        khiTrong={
          xoaHet
            ? { tieuDe: "Không có hồ sơ nào khớp", cau: "Không hồ sơ nào trong hàng đợi khớp ô tìm và bộ lọc đang bật." }
            : {
                tieuDe: "Không còn hồ sơ nào chờ điều phối",
                cau: "Hồ sơ mới gửi và hồ sơ bị phòng ban trả về sẽ hiện ở đây, chia cột theo trạng thái.",
              }
        }
      />
    </>
  );
}
