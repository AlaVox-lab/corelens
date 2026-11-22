"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Danh sách mục trên thanh bên, tô sáng mục đang đứng (#158).
//
// Chạy phía trình duyệt chỉ để đọc đường dẫn hiện tại. Danh sách mục và số đếm do khung
// trang phía máy chủ dựng sẵn từ `workspaces` của `/me` rồi truyền xuống — tệp này không
// biết người dùng mang vai trò gì.
//
// Riêng mục Hộp thư (#155) tự hỏi lại số chưa đọc khoảng 12 giây một lần khi trang đang
// hiện, và hỏi ngay khi có nơi vừa đánh dấu đã đọc — con số không đợi chuyển trang.

import {
  Activity,
  BookOpen,
  ChartColumn,
  FolderOpen,
  GitFork,
  House,
  Inbox,
  MessagesSquare,
  Settings2,
  SquarePen,
  UserCheck,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { SU_KIEN_HOP_THU } from "@/components/danh-dau-da-doc";
import { SoCuon } from "@/components/so-cuon";
import type { TenIcon } from "@/lib/khong-gian";

export type MucDieuHuong = {
  duongDan: string;
  nhan: string;
  icon: TenIcon;
  nhom: "chung" | "lam-viec";
  /** Số hồ sơ còn mở ở mục này — hay số tin chưa đọc ở Hộp thư. Không có thì không hiện. */
  dem?: number;
  /** Số hồ sơ đang chờ chính người xem làm bước chính (#230), huy hiệu đặc màu nhấn. */
  cho?: number;
  /** Có việc chờ người xem đã quá hạn hoặc sắp tự đi: chấm đỏ trên icon (#230). */
  gap?: boolean;
  /**
   * Lối ra một dịch vụ khác của cụm, mở ở thẻ mới — kho tri thức (#321). Có trường này thì `duongDan`
   * chỉ làm khóa, liên kết đi tới `ngoai`.
   */
  ngoai?: string;
  /** Mã nguồn của dịch vụ ngoài đó, ghi dưới tên mục cùng giấy phép (AGPL-3.0, điều 13). */
  nguon?: { ten: string; giayPhep: string; url: string };
};

/** Mỗi bao lâu thanh bên hỏi lại số chưa đọc, khi trang đang hiện. */
const CHU_KY_HOI_MS = 12_000;

const ICON: Record<TenIcon, LucideIcon> = {
  "trang-chu": House,
  gui: SquarePen,
  "ho-so": FolderOpen,
  "dieu-phoi": GitFork,
  "phong-ban": Inbox,
  "bao-cao": ChartColumn,
  "hop-thu": MessagesSquare,
  "he-thong": Activity,
  "cau-hinh": Settings2,
  "uy-quyen": UserCheck,
  "tri-thuc": BookOpen,
};

/** Số chưa đọc của Hộp thư, bắt đầu từ con số máy chủ dựng sẵn rồi tự hỏi lại. */
function useSoChuaDoc(banDau: number | undefined): number | undefined {
  const [so, datSo] = useState(banDau);
  useEffect(() => datSo(banDau), [banDau]);

  useEffect(() => {
    let huy = false;
    const hoi = async () => {
      if (document.visibilityState !== "visible") return;
      try {
        const kq = (await (await fetch("/api/hop-thu/chua-doc", { cache: "no-store" })).json()) as {
          unread: number | null;
        };
        if (!huy && kq.unread !== null) datSo(kq.unread);
      } catch {
        // Mạng chập chờn: giữ con số đang hiện, lượt sau hỏi lại
      }
    };
    const dongHo = window.setInterval(hoi, CHU_KY_HOI_MS);
    window.addEventListener(SU_KIEN_HOP_THU, hoi);
    document.addEventListener("visibilitychange", hoi);
    return () => {
      huy = true;
      window.clearInterval(dongHo);
      window.removeEventListener(SU_KIEN_HOP_THU, hoi);
      document.removeEventListener("visibilitychange", hoi);
    };
  }, []);

  return so;
}

/**
 * Mục khớp với đường dẫn hiện tại: khớp dài nhất thắng.
 *
 * `/yeu-cau/moi` khớp cả `/yeu-cau/moi` lẫn `/yeu-cau` — chọn mục dài hơn, không thì
 * trang gửi yêu cầu lại tô sáng mục "Hồ sơ của tôi". Mục `/` chỉ khớp đúng trang chủ.
 */
export function mucDangDung(duongDan: string, cacMuc: MucDieuHuong[]): MucDieuHuong | null {
  const khop = cacMuc
    .filter((m) => duongDan === m.duongDan || (m.duongDan !== "/" && duongDan.startsWith(`${m.duongDan}/`)))
    .sort((a, b) => b.duongDan.length - a.duongDan.length);
  return khop[0] ?? null;
}

/**
 * Huy hiệu hai mức (#230): số đặc màu nhấn là việc đang chờ chính mình — tin chưa đọc ở Hộp
 * thư, hồ sơ có `needs_my_action` ở các mục khác; số mờ là hồ sơ còn mở. Nhãn đọc màn hình
 * nói đủ cả hai số, vì khi thu gọn thanh bên chỉ còn số đặc.
 */
function MucNgoai({ muc }: { muc: MucDieuHuong & { ngoai: string } }) {
  const Icon = ICON[muc.icon];
  return (
    <>
      <a
        className="sb-muc"
        href={muc.ngoai}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={`${muc.nhan} (mở thẻ mới)`}
        title={muc.nhan}
        data-loi-ngoai={muc.icon}
      >
        <span className="sb-icon">
          <Icon aria-hidden />
        </span>
        <span className="sb-nhan">{muc.nhan}</span>
      </a>
      {muc.nguon ? (
        <p className="sb-nguon">
          {muc.nguon.ten} · {muc.nguon.giayPhep} ·{" "}
          <a href={muc.nguon.url} target="_blank" rel="noopener noreferrer">
            mã nguồn
          </a>
        </p>
      ) : null}
    </>
  );
}

function Muc({ muc, chon, dem }: { muc: MucDieuHuong; chon: boolean; dem?: number }) {
  if (muc.ngoai) return <MucNgoai muc={{ ...muc, ngoai: muc.ngoai }} />;
  const Icon = ICON[muc.icon];
  const laHopThu = muc.icon === "hop-thu";
  const cho = laHopThu ? (dem ?? muc.dem) : muc.cho;
  const mo = laHopThu ? undefined : muc.dem;
  // Phần số chỉ trình đọc màn hình đọc (#435): tên liên kết dựng từ NỘI DUNG — chữ nhìn thấy rồi tới phần
  // này — chứ không bằng `aria-label`, để tên đọc lên luôn bắt đầu bằng đúng chữ người dùng thấy và gọi
  // bằng giọng nói được (WCAG 2.5.3). Thanh bên thu gọn chỉ làm mờ nhãn, nên tên vẫn đủ.
  const phu = [
    cho ? (laHopThu ? `${cho} tin chưa đọc` : `${cho} việc cần xử lý`) : null,
    mo ? `${mo} đang mở` : null,
    muc.gap ? "có việc quá hạn hoặc sắp tự đi" : null,
  ]
    .filter(Boolean)
    .join(", ");
  return (
    <Link className="sb-muc" href={muc.duongDan} aria-current={chon ? "page" : undefined} title={muc.nhan}>
      <span className="sb-icon">
        <Icon aria-hidden />
        {muc.gap ? <span className="sb-cham" aria-hidden /> : null}
      </span>
      <span className="sb-nhan">{muc.nhan}</span>
      {phu ? <span className="an-di">, {phu}</span> : null}
      {/* Ô số luôn có mặt, bằng 0 thì ẩn (#237): số đi từ 0 lên lúc đang xem vẫn cuộn —
          gắn ô mới vào trang thì đó là lần dựng đầu, không có hiệu ứng */}
      <span className="so" data-moi="" data-trong={cho ? undefined : ""} aria-hidden>
        <SoCuon so={cho ?? 0} />
      </span>
      <span className="so" data-mo="" data-trong={mo ? undefined : ""} aria-hidden>
        <SoCuon so={mo ?? 0} />
      </span>
    </Link>
  );
}

export function DieuHuong({ cacMuc, dang }: { cacMuc: MucDieuHuong[]; dang: MucDieuHuong | null }) {
  const chung = cacMuc.filter((m) => m.nhom === "chung");
  const lamViec = cacMuc.filter((m) => m.nhom === "lam-viec");
  const soChuaDoc = useSoChuaDoc(cacMuc.find((m) => m.icon === "hop-thu")?.dem);
  const demCua = (m: MucDieuHuong) => (m.icon === "hop-thu" ? soChuaDoc : undefined);

  return (
    <nav className="sb-nav" aria-label="Điều hướng chính">
      {chung.map((m) => (
        <Muc key={m.duongDan} muc={m} chon={m === dang} dem={demCua(m)} />
      ))}
      {lamViec.length > 0 ? <div className="sb-nhom">Làm việc</div> : null}
      {lamViec.map((m) => (
        <Muc key={m.duongDan} muc={m} chon={m === dang} dem={demCua(m)} />
      ))}
    </nav>
  );
}
