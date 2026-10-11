"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Nhãn trạng thái bấm được trên “Hồ sơ của tôi” (#192): rê chuột, di phím Tab tới hay chạm
// vào nhãn thì hiện một sơ đồ nhỏ — thanh bước rút gọn của đường chính, bước hiện tại tô
// đậm, cộng một dòng khi hồ sơ đang ở nhánh phụ. Thay cho bảng giải thích mười trạng thái
// từng nằm cuối trang: người gửi chỉ muốn biết hồ sơ của mình đang ở đâu.
//
// Thành phần không biết trạng thái nào tồn tại: các bước và dòng nhánh do trang ở máy chủ
// suy sẵn từ dữ liệu (lib/buoc.ts) rồi truyền vào.
//
// Sơ đồ gắn thẳng vào <body> (portal) và đặt `position: fixed` theo vị trí của nút, vì hai
// lý do. Một: khung thẻ danh sách cắt mọi thứ tràn ra ngoài (`overflow: hidden` để giữ góc
// bo), nên đặt `absolute` trong dòng thì sơ đồ của dòng cuối bị cắt. Hai: `fixed` chỉ tính
// theo màn hình khi không khung cha nào có `transform` — mà khung nội dung có hiệu ứng hiện
// trang `.vao`, trong lúc chạy hiệu ứng sơ đồ lệch theo khung đó.
//
// Ba cách mở:
//   - rê chuột: sơ đồ là tooltip thuần — chuột đi xuyên qua nó (`pointer-events: none`), rời
//     nhãn là đóng, cuộn trang cũng đóng. Sơ đồ nằm ngay dưới nhãn nên phủ lên nhãn của dòng
//     kế tiếp; nếu nó bắt chuột thì rê từ nhãn này xuống nhãn dưới sẽ rơi vào sơ đồ cũ
//   - Tab tới: mở khi nút nhận tiêu điểm, đóng khi tiêu điểm rời đi
//   - bấm hay chạm: ghim — sơ đồ ở lại, nhận chạm, bám theo nút khi cuộn; bấm lại nhãn, chạm ra
//     ngoài hay nhấn Esc thì đóng
// Mỗi lúc chỉ một sơ đồ mở trên trang: mở cái mới thì cái đang mở đóng.

import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { NhanTrangThai } from "@/components/nhan-trang-thai";
import type { Buoc } from "@/lib/buoc";

type Props = {
  ma: string;
  nhan: string;
  /** Các bước đường chính. `null` khi không suy được vị trí — chỉ hiện dòng nhánh. */
  buoc: Buoc[] | null;
  /** Dòng cho hồ sơ ở nhánh phụ hay đã kết thúc ngoài đường chính. */
  dong: string | null;
};

/** Khoảng cách tối thiểu giữa sơ đồ và mép màn hình, và giữa sơ đồ với nút. */
const LE = 8;

/** Hàm đóng của sơ đồ đang mở trên trang, nếu có. */
let dangMo: (() => void) | null = null;

export function XemNhanhTrangThai({ ma, nhan, buoc, dong }: Props) {
  const [mo, datMo] = useState(false);
  const [ghim, datGhim] = useState(false);
  const [toaDo, datToaDo] = useState<{ top: number; left: number } | null>(null);
  const goc = useRef<HTMLSpanElement>(null);
  const nut = useRef<HTMLButtonElement>(null);
  const hop = useRef<HTMLDivElement>(null);
  const id = useId();

  const dongLai = useCallback(function dongSoDo() {
    if (dangMo === dongSoDo) dangMo = null;
    datMo(false);
    datGhim(false);
  }, []);

  function moRa(ghimLai: boolean) {
    if (dangMo && dangMo !== dongLai) dangMo();
    dangMo = dongLai;
    datMo(true);
    if (ghimLai) datGhim(true);
  }

  useEffect(
    () => () => {
      if (dangMo === dongLai) dangMo = null;
    },
    [dongLai],
  );

  // Đặt sơ đồ ngay dưới nút; sát đáy màn hình thì lật lên trên; không tràn ngang
  useLayoutEffect(() => {
    if (!mo) return;
    function dat() {
      const n = nut.current?.getBoundingClientRect();
      const h = hop.current;
      if (!n || !h) return;
      const rong = h.offsetWidth;
      const cao = h.offsetHeight;
      const left = Math.max(LE, Math.min(n.left, window.innerWidth - rong - LE));
      const duoi = n.bottom + LE;
      const top = duoi + cao + LE > window.innerHeight ? Math.max(LE, n.top - cao - LE) : duoi;
      datToaDo({ top, left });
    }
    // Mở bằng rê thì cuộn là đóng; đã ghim hay đang giữ tiêu điểm phím thì bám theo nút
    function cuon() {
      if (!ghim && document.activeElement !== nut.current) dongLai();
      else dat();
    }
    dat();
    window.addEventListener("scroll", cuon, { capture: true, passive: true });
    window.addEventListener("resize", dat);
    return () => {
      window.removeEventListener("scroll", cuon, { capture: true });
      window.removeEventListener("resize", dat);
    };
  }, [mo, ghim, dongLai]);

  // Chạm ra ngoài hay nhấn Esc thì đóng
  useEffect(() => {
    if (!mo) return;
    function ngoai(e: PointerEvent) {
      const dich = e.target as Node;
      if (!goc.current?.contains(dich) && !hop.current?.contains(dich)) dongLai();
    }
    function phim(e: KeyboardEvent) {
      if (e.key !== "Escape") return;
      dongLai();
      nut.current?.focus({ preventScroll: true });
    }
    document.addEventListener("pointerdown", ngoai);
    document.addEventListener("keydown", phim);
    return () => {
      document.removeEventListener("pointerdown", ngoai);
      document.removeEventListener("keydown", phim);
    };
  }, [mo, dongLai]);

  const dang = buoc?.findIndex((b) => b.dang) ?? -1;

  return (
    <span
      ref={goc}
      className="xn"
      onPointerEnter={(e) => {
        if (e.pointerType === "mouse" && !mo) moRa(false);
      }}
      onPointerLeave={(e) => {
        if (e.pointerType !== "mouse" || ghim) return;
        if (document.activeElement !== nut.current) dongLai();
      }}
      onBlur={(e) => {
        const toi = e.relatedTarget as Node | null;
        if (!goc.current?.contains(toi) && !hop.current?.contains(toi)) dongLai();
      }}
    >
      <button
        ref={nut}
        type="button"
        className="xn-nut"
        aria-expanded={mo}
        aria-controls={id}
        aria-describedby={mo ? id : undefined}
        onFocus={() => {
          if (!mo) moRa(false);
        }}
        onClick={() => {
          if (mo && ghim) dongLai();
          else moRa(true);
        }}
      >
        <NhanTrangThai ma={ma} nhan={nhan} />
        <span className="an-di">, xem hồ sơ đang ở bước nào</span>
      </button>

      {mo &&
        createPortal(
          <div
            ref={hop}
            id={id}
            className="xn-hop"
            // Nhận tiêu điểm khi bấm vào lúc đã ghim, để `onBlur` của nhãn không coi là rời đi
            tabIndex={-1}
            data-ghim={ghim ? "" : undefined}
            style={toaDo ?? { visibility: "hidden", top: 0, left: 0 }}
          >
            {buoc && buoc.length > 0 && (
              <>
                <ol className="xn-buoc" aria-label="Đường đi của hồ sơ">
                  {buoc.map((b) => (
                    <li
                      key={b.code}
                      data-xong={b.xong ? "" : undefined}
                      data-dang={b.dang ? "" : undefined}
                    >
                      <span className="an-di">
                        {b.label}
                        {b.dang ? " — đang ở bước này" : b.xong ? " — đã qua" : ""}
                      </span>
                    </li>
                  ))}
                </ol>
                {dang >= 0 && (
                  <p className="xn-chu" aria-hidden="true">
                    Bước {dang + 1}/{buoc.length} · <strong>{buoc[dang].label}</strong>
                  </p>
                )}
              </>
            )}
            {dong && <p className="xn-dong">{dong}</p>}
          </div>,
          document.body,
        )}
    </span>
  );
}
