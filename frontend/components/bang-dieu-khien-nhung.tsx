"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Bảng điều khiển phân tích nhúng trong cổng (#305), dựng bằng thư viện nhúng chính thức của
// Superset (`@superset-ui/embedded-sdk`, Apache-2.0).
//
// Không đăng nhập lần hai: thư viện xin token khách qua `/api/bao-cao/token`, nơi dịch vụ ứng
// dụng đã kiểm vai trò và gắn phạm vi phòng ban. Token sống vài phút; thư viện tự gọi lại hàm
// xin token trước khi hết hạn, nên trang để mở cả buổi vẫn chạy.
//
// Khung của Superset — tiêu đề, thanh bộ lọc — ẩn đi, tiếng Anh và trùng với tiêu đề trang. Cổng
// tự ghi phạm vi số liệu người xem đang thấy. Chế độ sáng/tối đi theo nút của cổng.

import type { EmbeddedDashboard } from "@superset-ui/embedded-sdk";
import { ServerCrash } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { ManRong } from "@/components/man-rong";
import type { TokenBaoCao } from "@/lib/kieu";

type TinhTrang = "dang-tai" | "san-sang" | "khong-phan-hoi" | "het-phien" | "khong-duoc-xem";

class LoiToken extends Error {
  constructor(readonly maHttp: number) {
    super(`Không xin được token khách (${maHttp})`);
  }
}

async function xinToken(): Promise<TokenBaoCao> {
  const phanHoi = await fetch("/api/bao-cao/token", { method: "POST", cache: "no-store" });
  if (!phanHoi.ok) throw new LoiToken(phanHoi.status);
  return (await phanHoi.json()) as TokenBaoCao;
}

function cheDoToi(): boolean {
  const html = document.documentElement;
  return (
    html.dataset.theme === "dark" ||
    (html.dataset.theme !== "light" && matchMedia("(prefers-color-scheme: dark)").matches)
  );
}

/** Dòng phạm vi dưới tiêu đề: người xem biết con số là của ai, không phải đoán. */
function DongPhamVi({ phamVi }: { phamVi: TokenBaoCao["scope"] }) {
  const noi = phamVi.all ? "toàn công ty" : phamVi.departments.map((p) => p.label).join(", ");
  return (
    <p className="bao-cao-pham-vi">
      Phạm vi số liệu: <strong>{noi}</strong>
    </p>
  );
}

function KhungChoBangDieuKhien() {
  return (
    <div className="bao-cao-cho" role="status" aria-label="Đang tải bảng điều khiển">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="the bao-cao-cho-o">
          <span className="khung-cho-vach" style={{ width: "46%", height: "14px" }} />
          <span className="khung-cho-vach" style={{ width: "100%", height: "180px" }} />
        </div>
      ))}
    </div>
  );
}

export function BangDieuKhienNhung() {
  const choGan = useRef<HTMLDivElement>(null);
  const [tinhTrang, datTinhTrang] = useState<TinhTrang>("dang-tai");
  const [phamVi, datPhamVi] = useState<TokenBaoCao["scope"] | null>(null);
  // Tăng lên mỗi lần bấm Thử lại để dựng lại từ đầu
  const [lanThu, datLanThu] = useState(0);

  useEffect(() => {
    let huy = false;
    let bang: EmbeddedDashboard | null = null;
    let doCao: number | undefined;
    let theoDoiCheDo: MutationObserver | undefined;

    (async () => {
      const goc = choGan.current;
      if (!goc) return;
      try {
        const dau = await xinToken();
        if (huy) return;
        datPhamVi(dau.scope);
        // Nạp thư viện lúc chạy: nó đụng `window` ngay khi được nạp
        const { embedDashboard } = await import("@superset-ui/embedded-sdk");
        let tokenDau: string | null = dau.token;
        bang = await embedDashboard({
          id: dau.dashboard_id,
          supersetDomain: dau.superset_url,
          mountPoint: goc,
          // Lần đầu dùng token vừa xin để biết phạm vi; các lần sau là thư viện tự làm mới
          fetchGuestToken: async () => {
            const t = tokenDau;
            tokenDau = null;
            return t ?? (await xinToken()).token;
          },
          dashboardUiConfig: { hideTitle: true, filters: { visible: false, expanded: false } },
          iframeTitle: "Bảng điều khiển phân tích",
        });
        if (huy) {
          bang.unmount();
          return;
        }
        const dangNhung = bang;
        const theoCong = () => dangNhung.setThemeMode(cheDoToi() ? "dark" : "default");
        theoCong();
        theoDoiCheDo = new MutationObserver(theoCong);
        theoDoiCheDo.observe(document.documentElement, { attributeFilter: ["data-theme"] });

        // Khung nhúng không tự cao theo nội dung: hỏi chiều cao của dashboard rồi đặt cho khung,
        // để trang cuộn một lần thay vì cuộn lồng trong khung
        doCao = window.setInterval(async () => {
          const khung = goc.querySelector("iframe");
          const { height } = await dangNhung.getScrollSize();
          if (khung && height > 0) khung.style.height = `${height}px`;
        }, 1000);
        datTinhTrang("san-sang");
      } catch (loi) {
        if (huy) return;
        const ma = loi instanceof LoiToken ? loi.maHttp : 0;
        datTinhTrang(ma === 401 ? "het-phien" : ma === 403 ? "khong-duoc-xem" : "khong-phan-hoi");
      }
    })();

    return () => {
      huy = true;
      window.clearInterval(doCao);
      theoDoiCheDo?.disconnect();
      bang?.unmount();
    };
  }, [lanThu]);

  if (tinhTrang === "khong-phan-hoi" || tinhTrang === "het-phien" || tinhTrang === "khong-duoc-xem") {
    const noiDung = {
      "khong-phan-hoi": {
        tieuDe: "Nền tảng báo cáo không phản hồi",
        cau: "Bảng điều khiển chưa tải được. Hồ sơ và mọi thao tác vẫn bình thường — thử lại sau ít phút.",
      },
      "het-phien": {
        tieuDe: "Phiên đăng nhập đã hết hạn",
        cau: "Tải lại trang để đăng nhập lại, rồi mở Báo cáo lần nữa.",
      },
      "khong-duoc-xem": {
        tieuDe: "Tài khoản này không xem được báo cáo",
        cau: "Quyền xem báo cáo cấp theo vai trò. Cần xem thì nhờ quản trị hệ thống.",
      },
    }[tinhTrang];
    return (
      <div className="the" style={{ marginTop: "20px" }}>
        <ManRong icon={ServerCrash} loi tieuDe={noiDung.tieuDe} cau={noiDung.cau}>
          {tinhTrang === "khong-phan-hoi" ? (
            <button
              type="button"
              className="nut"
              data-loai="chinh"
              onClick={() => {
                datTinhTrang("dang-tai");
                datLanThu((n) => n + 1);
              }}
            >
              Thử lại
            </button>
          ) : (
            <a className="nut" href="">
              Tải lại trang
            </a>
          )}
        </ManRong>
      </div>
    );
  }

  return (
    <>
      {phamVi ? <DongPhamVi phamVi={phamVi} /> : <p className="bao-cao-pham-vi">&nbsp;</p>}
      <p className="bao-cao-cuon-ngang">Vuốt ngang trong khung để xem đủ các biểu đồ.</p>
      {tinhTrang === "dang-tai" ? <KhungChoBangDieuKhien /> : null}
      {/* Màn hẹp cuộn ngang trong khung: khung nhận tiêu điểm bàn phím để cuộn bằng phím mũi tên (#435) */}
      <div
        key={lanThu}
        ref={choGan}
        className="bao-cao-khung"
        data-an={tinhTrang === "dang-tai" ? "" : undefined}
        role="region"
        aria-label="Bảng điều khiển báo cáo"
        tabIndex={0}
      />
    </>
  );
}
