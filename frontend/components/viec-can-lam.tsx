"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khối "Cần bạn xử lý" trên trang chủ (#228): mọi hồ sơ đang chờ chính người xem làm bước
// chính, gộp từ các vai họ có. Máy chủ dựng sẵn từng dòng và khóa sắp xếp; tệp này chỉ giữ
// thứ thuộc về trình duyệt — cách xếp đang chọn, nhớ cho lần sau, và menu chọn cách xếp.
//
// Nút trên dòng mở trang hồ sơ ở khối thao tác: bước chính thường cần nhập thêm (mức ưu
// tiên, người xử lý, lý do), nên làm ở trang hồ sơ, nơi bảng thao tác dựng từ dữ liệu.

import { ArrowDownUp, Check, ChevronDown, Clock, AlarmClock } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { NhanTrangThai } from "@/components/nhan-trang-thai";

export type DongViec = {
  khoa: string;
  href: string;
  ma: string;
  tieuDe: string;
  trangThai: { ma: string; nhan: string };
  /** Câu hạn đã dựng sẵn — "Quá hạn 3 giờ làm việc", "Tự trả về điều phối lúc …". */
  han: string | null;
  /** 0 quá hạn, 1 sắp hạn hay sắp tự đi, 2 bình thường. */
  gap: 0 | 1 | 2;
  phu: string | null;
  /** Vai mà dòng này thuộc về — chỉ hiện khi người xem có hơn một vai. */
  vai: string | null;
  buoc: string;
  xep: { han: number; cho: number; moi: number };
};

const CACH_XEP = [
  { ma: "gap", ten: "Độ gấp", moTa: "Quá hạn → sắp hạn → chờ lâu nhất" },
  { ma: "han", ten: "Hạn gần nhất", moTa: "Việc sắp tới hạn lên trước" },
  { ma: "cho", ten: "Chờ lâu nhất", moTa: "Việc nằm im lâu nhất lên trước" },
  { ma: "moi", ten: "Mới nhất", moTa: "Hồ sơ vừa tạo lên trước" },
] as const;
type MaXep = (typeof CACH_XEP)[number]["ma"];

const KHOA_XEP = "dxlab-xep-viec";

const SO_SANH: Record<MaXep, (a: DongViec, b: DongViec) => number> = {
  gap: (a, b) => a.gap - b.gap || a.xep.cho - b.xep.cho,
  han: (a, b) => a.xep.han - b.xep.han,
  cho: (a, b) => a.xep.cho - b.xep.cho,
  moi: (a, b) => b.xep.moi - a.xep.moi,
};

function MenuXep({ dang, chon }: { dang: MaXep; chon: (m: MaXep) => void }) {
  const [mo, setMo] = useState(false);
  const goc = useRef<HTMLDivElement>(null);
  const nut = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!mo) return;
    goc.current?.querySelector<HTMLButtonElement>('[aria-checked="true"]')?.focus();
    const ngoai = (e: MouseEvent) => !goc.current?.contains(e.target as Node) && setMo(false);
    const phim = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMo(false);
        nut.current?.focus();
      }
    };
    document.addEventListener("mousedown", ngoai);
    document.addEventListener("keydown", phim);
    return () => {
      document.removeEventListener("mousedown", ngoai);
      document.removeEventListener("keydown", phim);
    };
  }, [mo]);

  const diChuyen = (e: React.KeyboardEvent) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const cac = [...(goc.current?.querySelectorAll<HTMLButtonElement>("[role=menuitemradio]") ?? [])];
    const i = cac.indexOf(document.activeElement as HTMLButtonElement);
    cac[(i + (e.key === "ArrowDown" ? 1 : cac.length - 1)) % cac.length]?.focus();
  };

  return (
    <div className="sx" ref={goc}>
      <button
        ref={nut}
        className="nut-sx"
        type="button"
        aria-haspopup="menu"
        aria-expanded={mo}
        onClick={() => setMo((m) => !m)}
      >
        <ArrowDownUp aria-hidden />
        <span>
          Sắp xếp: <b>{CACH_XEP.find((c) => c.ma === dang)?.ten}</b>
        </span>
        <ChevronDown aria-hidden />
      </button>
      {mo ? (
        <div className="sx-menu" role="menu" aria-label="Cách sắp xếp" onKeyDown={diChuyen}>
          {CACH_XEP.map((c) => (
            <button
              key={c.ma}
              type="button"
              role="menuitemradio"
              aria-checked={c.ma === dang}
              onClick={() => {
                chon(c.ma);
                setMo(false);
                nut.current?.focus();
              }}
            >
              <span>
                <b>{c.ten}</b>
                <small>{c.moTa}</small>
              </span>
              <Check aria-hidden />
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function ViecCanLam({ dong }: { dong: DongViec[] }) {
  const [xep, setXep] = useState<MaXep>("gap");
  useEffect(() => {
    try {
      const luu = localStorage.getItem(KHOA_XEP) as MaXep | null;
      if (luu && luu in SO_SANH) setXep(luu);
    } catch {
      // Trình duyệt chặn lưu trữ: giữ cách xếp mặc định
    }
  }, []);
  const chon = (m: MaXep) => {
    setXep(m);
    try {
      localStorage.setItem(KHOA_XEP, m);
    } catch {
      // Vẫn xếp được trong lần mở này, chỉ không nhớ
    }
  };
  const daXep = useMemo(() => [...dong].sort(SO_SANH[xep]), [dong, xep]);

  return (
    <section className="the khoi-viec" aria-labelledby="tieu-de-viec">
      <div className="khoi-dau">
        <h2 id="tieu-de-viec">Cần bạn xử lý</h2>
        {dong.length > 1 ? <MenuXep dang={xep} chon={chon} /> : null}
      </div>
      <ul className="ds-viec">
        {daXep.map((d) => (
          <li key={d.khoa} className="dong-viec">
            <span className="cham-gap" data-gap={d.gap} aria-hidden />
            <div className="dv-than">
              <Link className="dv-tieu-de" href={d.href} title={d.tieuDe}>
                {d.tieuDe}
              </Link>
              <div className="dv-meta">
                <span className="mono">{d.ma}</span>
                <NhanTrangThai ma={d.trangThai.ma} nhan={d.trangThai.nhan} />
                {d.han ? (
                  <span className="dv-han" data-gap={d.gap}>
                    {d.gap === 0 ? <AlarmClock aria-hidden /> : d.gap === 1 ? <Clock aria-hidden /> : null}
                    {d.han}
                  </span>
                ) : null}
                {d.vai ? <span className="dv-vai">{d.vai}</span> : null}
                {d.phu ? <span>{d.phu}</span> : null}
              </div>
            </div>
            <Link className="nut" href={`${d.href}#thao-tac`}>
              {d.buoc} →
            </Link>
          </li>
        ))}
      </ul>
      <p className="khoi-chan">
        {dong.length} việc · bấm tiêu đề để mở hồ sơ, nút mở đúng khối thao tác của bước đó
      </p>
    </section>
  );
}
