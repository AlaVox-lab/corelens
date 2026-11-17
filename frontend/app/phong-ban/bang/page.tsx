// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Bảng Kanban của buồng lái phòng ban (#403).
//
// Hàng đợi (`/phong-ban`) trả lời "hồ sơ nào sắp trễ"; bảng này trả lời "việc của phòng đang dồn ở bước
// nào". Mỗi cột một trạng thái — tên và thứ tự cột lấy từ danh mục trạng thái của dịch vụ (`GET /states`),
// tệp này không biết trạng thái nào. Chỉ hiện cột có hồ sơ: bảng của một phòng không cần cột "Đã gửi" mà hồ
// sơ chưa bao giờ tới phòng.
//
// Dữ liệu là chính hàng đợi phòng ban (`/department/queue`, cùng cửa nhìn thấy, cùng bộ lọc "Giao cho tôi"),
// lấy một lần tối đa số dòng dịch vụ cho phép. Thẻ chỉ để nhìn và mở hồ sơ: không kéo thả đổi trạng thái — đổi
// trạng thái phải qua các nút engine trả trên trang hồ sơ, nơi có ghi chú bắt buộc và ràng buộc Poka-yoke.

import { List, User } from "lucide-react";
import Link from "next/link";

import { TenCapCon } from "@/components/khung-ung-dung";
import { goiDichVu } from "@/lib/api";
import type { HangDoiPhongBan, MucHangDoiPhongBan, TrangThai } from "@/lib/kieu";
import { chuCaiDau, mauTheo } from "@/lib/nguoi";
import { docDongHo, docTuDong } from "@/lib/sla";
import { bienHoMau, trinhBayTrangThai } from "@/lib/trang-thai";

export const dynamic = "force-dynamic";

/** Số hồ sơ tối đa một lần đọc — trần `limit` của dịch vụ (backend/app/workflow/phan_trang.py). */
const TOI_DA = 200;

type ThamSo = Record<string, string | string[] | undefined>;

/** Mức của câu hạn — cùng quy tắc tô màu với cột "Hạn" của hàng đợi. */
function mucHan(m: MucHangDoiPhongBan): "qua" | "sap" | "dung" | undefined {
  const tuDong = docTuDong(m);
  if (tuDong?.canhBao) return "sap";
  if (docDongHo(m).canhBao) return "qua";
  if (!m.sla_started || m.sla_paused) return "dung";
  return m.sla_due_soon ? "sap" : undefined;
}

function TheHoSo({ m }: { m: MucHangDoiPhongBan }) {
  const tuDong = docTuDong(m);
  const cauHan = (tuDong?.canhBao ? tuDong : docDongHo(m)).cau;
  const muc = mucHan(m);
  return (
    <li>
      <Link href={`/phong-ban/${m.id}`} className="kb-the" data-muc={muc}>
        <span className="kb-ma mono">{m.code}</span>
        <span className="kb-tieu-de">{m.title}</span>
        <span className="kb-phu">{m.request_type?.label ?? "Chưa rõ loại"}</span>
        <span className="kb-chan">
          {m.assignee_id ? (
            <span
              className="av av-nho"
              data-c={mauTheo(m.assignee_id)}
              title={m.assigned_to_me ? "Bạn" : (m.assignee_label ?? "Một người trong phòng")}
            >
              {chuCaiDau(m.assignee_label ?? "?")}
            </span>
          ) : (
            <span className="kb-phu">Chưa giao</span>
          )}
          <span className="kb-han">{cauHan}</span>
        </span>
      </Link>
    </li>
  );
}

export default async function BangPhongBan({ searchParams }: { searchParams: Promise<ThamSo> }) {
  const sp = await searchParams;
  const cuaToi = sp.mine === "1";
  const q = new URLSearchParams({ limit: String(TOI_DA), offset: "0" });
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
        <Link href={cuaToi ? "/phong-ban/bang" : "/phong-ban/bang?mine=1"} className="chip" aria-pressed={cuaToi}>
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

  // Cột theo thứ tự của danh mục trạng thái; trạng thái lạ (bộ quy tắc cũ) xếp cuối theo thứ tự gặp
  const thuTu = new Map((cacTrangThai ?? []).map((t, i) => [t.code, i]));
  const theoCot = new Map<string, { ten: string; the: MucHangDoiPhongBan[] }>();
  for (const m of hangDoi.items) {
    const cot = theoCot.get(m.state.code) ?? { ten: m.state.label, the: [] };
    cot.the.push(m);
    theoCot.set(m.state.code, cot);
  }
  const cacCot = [...theoCot.entries()].sort(
    ([a], [b]) => (thuTu.get(a) ?? Number.MAX_SAFE_INTEGER) - (thuTu.get(b) ?? Number.MAX_SAFE_INTEGER),
  );

  return (
    <>
      {dau}
      {hangDoi.total > hangDoi.items.length && (
        <p className="kb-ghi-chu" role="status">
          Bảng hiện {hangDoi.items.length} trên {hangDoi.total} hồ sơ — xem đủ ở dạng danh sách.
        </p>
      )}
      {cacCot.length === 0 ? (
        <div className="the">
          <div className="rong">
            <h2>{cuaToi ? "Chưa có hồ sơ nào giao cho bạn" : "Phòng chưa có hồ sơ nào"}</h2>
            <p>Hồ sơ điều phối viên chuyển về phòng sẽ hiện ở đây, chia cột theo trạng thái.</p>
          </div>
        </div>
      ) : (
        <div className="kb-bang" aria-label="Bảng việc theo trạng thái">
          {cacCot.map(([ma, cot]) => (
            <section key={ma} className="kb-cot" aria-labelledby={`kb-${ma}`}>
              <h2 id={`kb-${ma}`} className="kb-dau-cot">
                <span className="nhan-tt" style={{ ...bienHoMau(trinhBayTrangThai(ma).ho), fontSize: "12.5px" }}>
                  {cot.ten}
                </span>
                <span className="kb-so">{cot.the.length}</span>
              </h2>
              <ul className="kb-ds">
                {cot.the.map((m) => (
                  <TheHoSo key={m.id} m={m} />
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </>
  );
}
