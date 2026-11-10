"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Sơ đồ quy trình thực tế (#315), dựng bằng `@xyflow/react` (MIT) với bố cục của `@dagrejs/dagre`
// (MIT, lib/bo-cuc-quy-trinh.ts). Hai thư viện chỉ lo vẽ, kéo, phóng; mọi con số và mọi nhãn đến
// từ JSON của dịch vụ khai phá — tệp này không biết trạng thái nào.
//
//   Nút   = một trạng thái: nhãn, số lượt vào, trung vị chờ. Trạng thái nghẽn tô nổi và mang chữ "Nghẽn"
//           (không chỉ dựa vào màu). Bấm → hồ sơ chờ lâu nhất ở đó.
//   Cạnh  = một lần chuyển: nét dày theo số lượt (có chặn trên và dưới). Luồng chính một màu, nhánh
//           lệch màu khác theo loại. Cạnh của luồng thiết kế mà không hồ sơ nào đi qua vẽ nét đứt mờ.
//           Chip số trên cạnh: bấm cạnh lệch → hồ sơ của nhánh đó.
//
// Màu lấy từ biến CSS của cổng (`var(--f-…)`), nên tự theo chế độ sáng/tối. Mọi điều khiển là nút
// thật: dùng được bằng bàn phím, đọc được bằng trình đọc màn hình. Chú thích khi rê chuột hay lấy
// tiêu điểm vẽ trong khung của sơ đồ (không phải thuộc tính `title`), nên cảm ứng và bàn phím cùng thấy.
//
// Màn hẹp (dưới 768 px): sơ đồ trong khung cao cố định, kéo và phóng hai ngón; nút "Xem toàn màn
// hình" mở lớp phủ (Esc đóng, trả tiêu điểm về nút).

import "@xyflow/react/dist/base.css";

import {
  BaseEdge,
  EdgeLabelRenderer,
  Handle,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { LocateFixed, Maximize2, Minus, Plus, X } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import { createPortal } from "react-dom";

import { CAO_NUT, RONG_NUT, boCucSoDo, type HuongBoCuc } from "@/lib/bo-cuc-quy-trinh";
import { giamChuyenDong } from "@/lib/chuyen-dong";
import { thoiLuongLamViec } from "@/lib/dinh-dang";
import {
  canhThietKeChuaDi,
  nhanTrangThai,
  soThapPhan,
  soVN,
  tenLoaiCanh,
  tenNhanhLech,
  thoiGianNgan,
} from "@/lib/ket-luan-quy-trinh";
import type { CanhKhaiPha, QuyTrinhThucTe, TrangThaiKhaiPha } from "@/lib/kieu";

/** Điều đang được chọn ở màn quy trình thực tế: một trạng thái, một nhánh lệch, hay một đường đi. */
export type ChonMuc =
  | { loai: "trang-thai"; ma: string }
  | { loai: "nhanh-lech"; kind: string }
  | { loai: "bien-the"; chiSo: number };

// ---------------------------------------------------------------------------
// Dữ liệu từng nút và cạnh
// ---------------------------------------------------------------------------

type DuLieuNut = {
  nhan: string;
  dong2: string;
  dong3: string;
  nghen: boolean;
  batDau: boolean;
  ketThuc: boolean;
  chuaCoSo: boolean;
  coTheBam: boolean;
  daChon: boolean;
  mo: boolean;
  huong: HuongBoCuc;
  ariaLabel: string;
  tieuDeTip: string;
  dongTip: string[];
  onBam: () => void;
};

type DuLieuCanh = {
  d: string;
  nhanX: number;
  nhanY: number;
  beDay: number;
  kenh: string;
  chuaDi: boolean;
  mo: boolean;
  daChon: boolean;
  chuNhan: string;
  dauMui: string;
  ariaLabel: string;
  tieuDeTip: string;
  dongTip: string[];
  /** Có hành động khi bấm: chỉ cạnh lệch. */
  onBam?: () => void;
};

type NutRF = Node<DuLieuNut, "trangThai">;
type CanhRF = Edge<DuLieuCanh, "quyTrinh">;

// Nét vẽ: dày theo căn bậc hai của số lượt, chặn dưới và trên
const BE_DAY_TOI_THIEU = 1.6;
const BE_DAY_TOI_DA = 8;

function beDayCanh(count: number, lonNhat: number): number {
  if (lonNhat <= 0) return BE_DAY_TOI_THIEU;
  return BE_DAY_TOI_THIEU + (BE_DAY_TOI_DA - BE_DAY_TOI_THIEU) * Math.sqrt(Math.max(0, count) / lonNhat);
}

/** Loại nhánh lệch chiếm nhiều nhất trong một cạnh (bỏ luồng chính); bằng nhau thì theo thứ tự dịch vụ. */
export function nhanhLechChinhCuaCanh(kinds: Record<string, number>): string | null {
  let tot: [string, number] | null = null;
  for (const [loai, so] of Object.entries(kinds)) {
    if (loai !== "main" && so > (tot?.[1] ?? 0)) tot = [loai, so];
  }
  return tot?.[0] ?? null;
}

function kenhCuaCanh(c: CanhKhaiPha): string {
  return c.is_main ? "main" : (nhanhLechChinhCuaCanh(c.kinds) ?? "main");
}

function khoaCanh(tu: string, den: string): string {
  return `${tu}>${den}`;
}

// ---------------------------------------------------------------------------
// Chú thích khi rê chuột / lấy tiêu điểm
// ---------------------------------------------------------------------------

type ChuThich = { x: number; y: number; rong: number; duoi: boolean; tieuDe: string; dong: string[] };

type NguCanhChuThich = {
  hien: (el: HTMLElement, tieuDe: string, dong: string[]) => void;
  an: () => void;
};

const NguCanhTip = createContext<NguCanhChuThich>({ hien: () => {}, an: () => {} });

// ---------------------------------------------------------------------------
// Nút trạng thái và cạnh
// ---------------------------------------------------------------------------

function NutTrangThai({ data }: NodeProps<NutRF>) {
  const tip = useContext(NguCanhTip);
  const nut = useRef<HTMLButtonElement>(null);
  const hien = () => nut.current && tip.hien(nut.current, data.tieuDeTip, data.dongTip);
  const viTriVao = data.huong === "LR" ? Position.Left : Position.Top;
  const viTriRa = data.huong === "LR" ? Position.Right : Position.Bottom;
  return (
    <>
      <Handle type="target" position={viTriVao} isConnectable={false} className="sdq-tay" />
      <button
        ref={nut}
        type="button"
        className="sdq-nut"
        aria-pressed={data.coTheBam ? data.daChon : undefined}
        aria-disabled={data.coTheBam ? undefined : true}
        aria-label={data.ariaLabel}
        data-nghen={data.nghen ? "" : undefined}
        data-mo={data.mo ? "" : undefined}
        data-ket-thuc={data.ketThuc ? "" : undefined}
        data-chua-co-so={data.chuaCoSo ? "" : undefined}
        onClick={() => {
          tip.an();
          if (data.coTheBam) data.onBam();
        }}
        onMouseEnter={hien}
        onMouseLeave={tip.an}
        onFocus={hien}
        onBlur={tip.an}
      >
        {data.nghen ? <span className="sdq-the-nghen">Nghẽn</span> : null}
        {data.batDau || data.ketThuc ? (
          <span className="sdq-the-moc">{data.batDau ? "Bắt đầu" : "Kết thúc"}</span>
        ) : null}
        <span className="sdq-nut-ten">{data.nhan}</span>
        <span className="sdq-nut-so">{data.dong2}</span>
        <span className="sdq-nut-so">{data.dong3}</span>
      </button>
      <Handle type="source" position={viTriRa} isConnectable={false} className="sdq-tay" />
    </>
  );
}

function CanhQuyTrinh({ id, data }: EdgeProps<CanhRF>) {
  const tip = useContext(NguCanhTip);
  const nhan = useRef<HTMLButtonElement & HTMLSpanElement>(null);
  if (!data) return null;
  const hien = () => nhan.current && tip.hien(nhan.current, data.tieuDeTip, data.dongTip);
  const chung = {
    ref: nhan,
    className: "sdq-chip",
    "aria-label": data.ariaLabel,
    onMouseEnter: hien,
    onMouseLeave: tip.an,
    onFocus: hien,
    onBlur: tip.an,
  };
  return (
    <>
      <BaseEdge
        id={id}
        path={data.d}
        markerEnd={`url(#${data.dauMui})`}
        interactionWidth={16}
        className={[
          "sdq-canh",
          `sdq-canh-${data.kenh}`,
          data.chuaDi ? "sdq-canh-chua-di" : "",
          data.mo ? "sdq-mo" : "",
          data.daChon ? "sdq-chon" : "",
        ]
          .filter(Boolean)
          .join(" ")}
        style={{ strokeWidth: data.beDay }}
      />
      <EdgeLabelRenderer>
        <div
          className="sdq-nhan-canh nodrag nopan"
          data-kenh={data.kenh}
          data-mo={data.mo ? "" : undefined}
          data-chua-di={data.chuaDi ? "" : undefined}
          data-chon={data.daChon ? "" : undefined}
          style={{ transform: `translate(-50%, -50%) translate(${data.nhanX}px, ${data.nhanY}px)` }}
        >
          {data.onBam ? (
            <button
              {...chung}
              type="button"
              aria-pressed={data.daChon}
              onClick={() => {
                tip.an();
                data.onBam?.();
              }}
            >
              {data.chuNhan}
            </button>
          ) : (
            // Không có hành động khi bấm: chỉ nhận tiêu điểm để bàn phím cũng đọc được chú thích
            <span {...chung} role="img" tabIndex={0}>
              {data.chuNhan}
            </span>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

const NODE_TYPES = { trangThai: NutTrangThai };
const EDGE_TYPES = { quyTrinh: CanhQuyTrinh };

// ---------------------------------------------------------------------------
// Dựng nút và cạnh từ JSON
// ---------------------------------------------------------------------------

function useManHep(): boolean {
  return useSyncExternalStore(
    (xong) => {
      const m = window.matchMedia("(max-width: 767px)");
      m.addEventListener("change", xong);
      return () => m.removeEventListener("change", xong);
    },
    () => window.matchMedia("(max-width: 767px)").matches,
    () => false,
  );
}

type CauTruc = {
  khoa: string;
  huong: HuongBoCuc;
  nut: {
    ma: string;
    x: number;
    y: number;
    tt: TrangThaiKhaiPha | null;
  }[];
  canh: {
    khoa: string;
    tu: string;
    den: string;
    d: string;
    nhanX: number;
    nhanY: number;
    beDay: number;
    kenh: string;
    chuaDi: boolean;
    thongTin: CanhKhaiPha | null;
  }[];
};

/** Phần của sơ đồ chỉ phụ thuộc dữ liệu và chiều bố cục — không phụ thuộc cái đang chọn. */
function dungCauTruc(d: QuyTrinhThucTe, huong: HuongBoCuc): CauTruc {
  const trangThai = new Map(d.states.map((t) => [t.code, t]));
  const chuaDi = canhThietKeChuaDi(d);
  const lonNhat = Math.max(0, ...d.edges.map((c) => c.count));

  const ma = new Set<string>(d.states.map((t) => t.code));
  for (const c of chuaDi) {
    ma.add(c.from);
    ma.add(c.to);
  }

  // Cạnh luồng chính vẽ trước, nhánh lệch vẽ sau để nằm trên
  const canhCoSo = [...d.edges].sort((a, b) => Number(b.is_main) - Number(a.is_main) || b.count - a.count);
  const dauVao = [
    ...canhCoSo.map((c) => ({
      tu: c.from,
      den: c.to,
      rongNhan: Math.max(34, soVN(c.count).length * 8 + 18),
      beDay: beDayCanh(c.count, lonNhat),
    })),
    ...chuaDi.map((c) => ({ tu: c.from, den: c.to, rongNhan: 30, beDay: BE_DAY_TOI_THIEU })),
  ];
  const bo = boCucSoDo([...ma], dauVao, huong);
  const duongTheoKhoa = new Map(bo.canh.map((c) => [khoaCanh(c.tu, c.den), c]));

  type CanhCoSo = { tu: string; den: string; thongTin: CanhKhaiPha | null; beDay: number };
  const moi: CanhCoSo[] = [
    ...canhCoSo.map((c) => ({ tu: c.from, den: c.to, thongTin: c, beDay: beDayCanh(c.count, lonNhat) })),
    ...chuaDi.map((c) => ({ tu: c.from, den: c.to, thongTin: null, beDay: BE_DAY_TOI_THIEU })),
  ];
  const canh: CauTruc["canh"] = moi.map((e) => {
    const duong = duongTheoKhoa.get(khoaCanh(e.tu, e.den));
    return {
      khoa: khoaCanh(e.tu, e.den),
      tu: e.tu,
      den: e.den,
      d: duong?.d ?? "",
      nhanX: duong?.nhanX ?? 0,
      nhanY: duong?.nhanY ?? 0,
      beDay: e.beDay,
      kenh: e.thongTin ? kenhCuaCanh(e.thongTin) : "main",
      chuaDi: e.thongTin === null,
      thongTin: e.thongTin,
    };
  });

  return {
    khoa: `${huong}|${[...ma].sort().join(",")}|${canh.map((c) => c.khoa).join(",")}`,
    huong,
    nut: bo.nut.map((n) => ({ ma: n.ma, x: n.x, y: n.y, tt: trangThai.get(n.ma) ?? null })),
    canh,
  };
}

/** Phần nổi bật khi chọn một đường đi hay một nhánh lệch: nút và cạnh còn lại làm mờ. */
function tinhNoiBat(
  d: QuyTrinhThucTe,
  chon: ChonMuc | null,
): { nut: Set<string>; canh: Set<string> } | null {
  if (!chon || chon.loai === "trang-thai") return null;
  if (chon.loai === "bien-the") {
    const chuoi = d.variants[chon.chiSo]?.sequence ?? [];
    const nut = new Set(chuoi);
    const canh = new Set<string>();
    for (let i = 0; i + 1 < chuoi.length; i++) {
      if (chuoi[i] !== chuoi[i + 1]) canh.add(khoaCanh(chuoi[i], chuoi[i + 1]));
    }
    return { nut, canh };
  }
  const canh = new Set<string>();
  const nut = new Set<string>();
  for (const c of d.edges) {
    if ((c.kinds[chon.kind] ?? 0) > 0) {
      canh.add(khoaCanh(c.from, c.to));
      nut.add(c.from);
      nut.add(c.to);
    }
  }
  // Nhánh không đi qua cạnh nào (chuyển phòng nhiều lần) thì không có gì để nổi bật
  return canh.size > 0 ? { nut, canh } : null;
}

// ---------------------------------------------------------------------------
// Khung sơ đồ
// ---------------------------------------------------------------------------

type DauVaoSoDo = {
  duLieu: QuyTrinhThucTe;
  chon: ChonMuc | null;
  onChonTrangThai: (ma: string) => void;
  onChonNhanh: (kind: string) => void;
};

/** Cách đưa sơ đồ về vừa khung. Chừa rìa rộng vì đường quay ngược đi vòng ngoài các nút. */
const VUA_KHUNG = { padding: 0.14, maxZoom: 1.1 };

function dongHoLuc(): number {
  return giamChuyenDong() ? 0 : 200;
}

function ThanhCongCu({ toanMan, onMoToanMan, nutToanMan, khung }: {
  toanMan: boolean;
  onMoToanMan?: () => void;
  nutToanMan?: React.RefObject<HTMLButtonElement | null>;
  khung: React.RefObject<HTMLDivElement | null>;
}) {
  const { zoomIn, zoomOut, fitView } = useReactFlow();

  // Khung đổi bề rộng (ngăn danh sách hồ sơ mở hay đóng, xoay màn hình): đưa sơ đồ về vừa khung,
  // không thì nửa sơ đồ nằm ngoài khung
  useEffect(() => {
    const el = khung.current;
    if (!el) return;
    let rongCu = el.clientWidth;
    const theoDoi = new ResizeObserver(() => {
      if (Math.abs(el.clientWidth - rongCu) < 2) return;
      rongCu = el.clientWidth;
      fitView({ ...VUA_KHUNG, duration: 0 });
    });
    theoDoi.observe(el);
    return () => theoDoi.disconnect();
  }, [khung, fitView]);

  return (
    <div className="sdq-cong-cu khong-in" role="group" aria-label="Phóng to, thu nhỏ sơ đồ">
      <button type="button" className="sdq-cong-cu-nut" aria-label="Phóng to" onClick={() => zoomIn({ duration: dongHoLuc() })}>
        <Plus aria-hidden />
      </button>
      <button type="button" className="sdq-cong-cu-nut" aria-label="Thu nhỏ" onClick={() => zoomOut({ duration: dongHoLuc() })}>
        <Minus aria-hidden />
      </button>
      <button
        type="button"
        className="sdq-cong-cu-nut"
        aria-label="Về giữa"
        title="Về giữa"
        onClick={() => fitView({ ...VUA_KHUNG, duration: dongHoLuc() })}
      >
        <LocateFixed aria-hidden />
      </button>
      {!toanMan && onMoToanMan ? (
        <button ref={nutToanMan} type="button" className="sdq-cong-cu-nut sdq-chi-man-hep" onClick={onMoToanMan}>
          <Maximize2 aria-hidden /> Xem toàn màn hình
        </button>
      ) : null}
    </div>
  );
}

function KhungBen({
  duLieu,
  chon,
  onChonTrangThai,
  onChonNhanh,
  toanMan = false,
  onMoToanMan,
  nutToanMan,
}: DauVaoSoDo & {
  toanMan?: boolean;
  onMoToanMan?: () => void;
  nutToanMan?: React.RefObject<HTMLButtonElement | null>;
}) {
  const hep = useManHep();
  const huong: HuongBoCuc = hep ? "TB" : "LR";
  const idDinh = useId().replace(/[^a-zA-Z0-9]/g, "");
  const khung = useRef<HTMLDivElement>(null);
  const [chuThich, datChuThich] = useState<ChuThich | null>(null);

  const nguCanh = useMemo<NguCanhChuThich>(
    () => ({
      hien: (el, tieuDe, dong) => {
        const k = khung.current?.getBoundingClientRect();
        if (!k) return;
        const r = el.getBoundingClientRect();
        const rong = Math.min(300, k.width - 16);
        const giua = r.left + r.width / 2 - k.left;
        const x = Math.max(rong / 2 + 8, Math.min(k.width - rong / 2 - 8, giua));
        // Phần tử nằm nửa trên của khung thì chú thích hiện phía dưới nó, không thì phía trên
        const duoi = r.top - k.top < k.height * 0.45;
        datChuThich({ x, y: duoi ? r.bottom - k.top + 8 : r.top - k.top - 8, rong, duoi, tieuDe, dong });
      },
      an: () => datChuThich(null),
    }),
    [],
  );

  const cauTruc = useMemo(() => dungCauTruc(duLieu, huong), [duLieu, huong]);
  const noiBat = useMemo(() => tinhNoiBat(duLieu, chon), [duLieu, chon]);

  const { nodes, edges } = useMemo(() => {
    const chung = duLieu.bottlenecks.overall_median_wait_seconds;
    const nodes: NutRF[] = cauTruc.nut.map(({ ma, x, y, tt }) => {
      const nhan = nhanTrangThai(duLieu, ma);
      const coTheBam = !!tt && tt.longest_waits.length > 0;
      const trungVi = tt?.median_wait_seconds ?? null;
      const dong2 = !tt ? "chưa có hồ sơ vào" : `${soVN(tt.visits)} lượt`;
      const dong3 = !tt ? "" : trungVi !== null ? `chờ ${thoiGianNgan(trungVi)}` : tt.is_terminal ? "không chờ ở đây" : "";
      const heSo = tt?.is_bottleneck && trungVi !== null && chung ? trungVi / chung : null;
      const dongTip: string[] = [];
      if (!tt) {
        dongTip.push("Chưa có hồ sơ nào vào trạng thái này trong khoảng đã chọn.");
      } else {
        dongTip.push(`${soVN(tt.visits)} lượt vào, ${soVN(tt.cases)} hồ sơ`);
        if (trungVi !== null) dongTip.push(`Chờ trung vị: ${thoiLuongLamViec(trungVi)}`);
        if (heSo !== null && chung) {
          dongTip.push(`Nghẽn: gấp ${soThapPhan(heSo)} lần mức chung (${thoiLuongLamViec(chung)})`);
        }
        if (tt.is_terminal) dongTip.push("Trạng thái kết thúc: hồ sơ không chờ ở đây.");
        if (coTheBam) dongTip.push("Bấm để xem hồ sơ chờ lâu nhất ở đây.");
      }
      return {
        id: ma,
        type: "trangThai",
        position: { x, y },
        width: RONG_NUT,
        height: CAO_NUT,
        draggable: false,
        selectable: false,
        focusable: false,
        data: {
          nhan,
          dong2,
          dong3,
          nghen: !!tt?.is_bottleneck,
          batDau: !!tt?.is_initial,
          ketThuc: !!tt?.is_terminal,
          chuaCoSo: !tt,
          coTheBam,
          daChon: chon?.loai === "trang-thai" && chon.ma === ma,
          mo: !!noiBat && !noiBat.nut.has(ma),
          huong,
          ariaLabel: [
            nhan,
            tt ? `${soVN(tt.visits)} lượt vào` : "chưa có hồ sơ vào",
            tt?.is_bottleneck ? "điểm nghẽn" : null,
            trungVi !== null ? `chờ trung vị ${thoiLuongLamViec(trungVi)}` : null,
            coTheBam ? "bấm để xem hồ sơ chờ lâu nhất" : null,
          ]
            .filter(Boolean)
            .join(", "),
          tieuDeTip: nhan,
          dongTip,
          onBam: () => onChonTrangThai(ma),
        },
      };
    });

    const edges: CanhRF[] = cauTruc.canh.map((c) => {
      const nhanTu = nhanTrangThai(duLieu, c.tu);
      const nhanDen = nhanTrangThai(duLieu, c.den);
      const tt = c.thongTin;
      const kindBam = tt && !tt.is_main ? nhanhLechChinhCuaCanh(tt.kinds) : null;
      const dongTip: string[] = [];
      if (!tt) {
        dongTip.push("Chưa có hồ sơ đi qua bước này (bước của luồng thiết kế).");
      } else {
        dongTip.push(`${soVN(tt.count)} lần đi qua, ${soVN(tt.cases)} hồ sơ`);
        for (const [loai, so] of Object.entries(tt.kinds)) dongTip.push(`${tenLoaiCanh(loai)}: ${soVN(so)} lần`);
        if (kindBam) dongTip.push(`Bấm để xem hồ sơ của nhánh “${tenNhanhLech(kindBam)}”.`);
      }
      // Cạnh của luồng thiết kế chưa ai đi: chip "0" nét đứt; lời giải thích ở chú giải, chú thích và nhãn đọc màn hình
      const chuNhan = tt ? soVN(tt.count) : "0";
      return {
        id: c.khoa,
        source: c.tu,
        target: c.den,
        type: "quyTrinh",
        focusable: false,
        selectable: false,
        data: {
          d: c.d,
          nhanX: c.nhanX,
          nhanY: c.nhanY,
          beDay: c.beDay,
          kenh: c.kenh,
          chuaDi: c.chuaDi,
          mo: !!noiBat && !noiBat.canh.has(c.khoa),
          daChon: chon?.loai === "nhanh-lech" && !!tt && (tt.kinds[chon.kind] ?? 0) > 0,
          chuNhan,
          dauMui: `${idDinh}-mui-${c.chuaDi ? "chua-di" : c.kenh}`,
          ariaLabel: `Từ ${nhanTu} sang ${nhanDen}: ${dongTip.join(". ")}`,
          tieuDeTip: `${nhanTu} → ${nhanDen}`,
          dongTip,
          onBam: kindBam ? () => onChonNhanh(kindBam) : undefined,
        },
      };
    });
    return { nodes, edges };
  }, [cauTruc, duLieu, chon, noiBat, huong, idDinh, onChonTrangThai, onChonNhanh]);

  // Các loại mũi tên cần định nghĩa: mỗi kênh màu một mũi, cộng một mũi cho nét đứt
  const kenhMui = useMemo(() => [...new Set(cauTruc.canh.map((c) => (c.chuaDi ? "chua-di" : c.kenh)))], [cauTruc]);

  return (
    <div
      ref={khung}
      className="sdq-khung"
      data-toan-man={toanMan ? "" : undefined}
      // React Flow ẩn phần tràn; tiêu điểm vào phần tử ngoài khung có thể làm khung cuộn lệch
      onScrollCapture={(e) => (e.target as HTMLElement).scrollTo?.(0, 0)}
    >
      <svg className="sdq-mui-dinh" aria-hidden focusable="false">
        <defs>
          {kenhMui.map((k) => (
            <marker
              key={k}
              id={`${idDinh}-mui-${k}`}
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="9"
              markerHeight="9"
              markerUnits="userSpaceOnUse"
              orient="auto-start-reverse"
            >
              <path d="M0,0 L10,5 L0,10 z" className={`sdq-mui sdq-mui-${k}`} />
            </marker>
          ))}
        </defs>
      </svg>
      <NguCanhTip.Provider value={nguCanh}>
        <ReactFlow
          key={cauTruc.khoa}
          nodes={nodes}
          edges={edges}
          nodeTypes={NODE_TYPES}
          edgeTypes={EDGE_TYPES}
          fitView
          fitViewOptions={VUA_KHUNG}
          minZoom={0.15}
          maxZoom={2.5}
          nodesDraggable={false}
          nodesConnectable={false}
          nodesFocusable={false}
          edgesFocusable={false}
          elementsSelectable={false}
          deleteKeyCode={null}
          selectionKeyCode={null}
          multiSelectionKeyCode={null}
          zoomOnScroll={false}
          zoomOnDoubleClick={false}
          preventScrolling={false}
          onMoveStart={nguCanh.an}
          ariaLabelConfig={{
            "node.a11yDescription.default": "",
            "node.a11yDescription.keyboardDisabled": "",
            "edge.a11yDescription.default": "",
            "controls.ariaLabel": "Điều khiển sơ đồ",
            "controls.zoomIn.ariaLabel": "Phóng to",
            "controls.zoomOut.ariaLabel": "Thu nhỏ",
            "controls.fitView.ariaLabel": "Về giữa",
            "controls.interactive.ariaLabel": "Bật tắt tương tác",
            "minimap.ariaLabel": "Bản đồ thu nhỏ",
            "handle.ariaLabel": "Điểm nối",
          }}
        >
          <ThanhCongCu toanMan={toanMan} onMoToanMan={onMoToanMan} nutToanMan={nutToanMan} khung={khung} />
        </ReactFlow>
      </NguCanhTip.Provider>
      {chuThich ? (
        <div
          className="sdq-chu-thich"
          aria-hidden
          style={{
            left: chuThich.x,
            top: chuThich.y,
            width: chuThich.rong,
            transform: chuThich.duoi ? "translateX(-50%)" : "translate(-50%, -100%)",
          }}
        >
          <strong>{chuThich.tieuDe}</strong>
          {chuThich.dong.map((d, i) => (
            <span key={i}>{d}</span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Lớp phủ toàn màn hình (màn hẹp)
// ---------------------------------------------------------------------------

const CO_THE_LAY_NET = 'button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])';

function LopToanMan({ onDong, children }: { onDong: () => void; children: React.ReactNode }) {
  const lop = useRef<HTMLDivElement>(null);
  const [daGan, datDaGan] = useState(false);
  useEffect(() => datDaGan(true), []);

  useEffect(() => {
    if (!daGan) return;
    const truoc = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const cuonCu = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    lop.current?.querySelector<HTMLElement>("[data-dong-toan-man]")?.focus();

    const phim = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        // Bắt ở pha chặn để các phím tắt khác của trang (ngăn danh sách hồ sơ) không nhận cùng Esc
        e.preventDefault();
        e.stopPropagation();
        onDong();
      } else if (e.key === "Tab" && lop.current) {
        // Giữ tiêu điểm trong lớp phủ: Tab ở phần tử cuối quay lại phần tử đầu
        const dsl = [...lop.current.querySelectorAll<HTMLElement>(CO_THE_LAY_NET)].filter((el) => el.offsetParent !== null);
        if (dsl.length === 0) return;
        const dau = dsl[0];
        const cuoi = dsl[dsl.length - 1];
        if (e.shiftKey && document.activeElement === dau) {
          e.preventDefault();
          cuoi.focus();
        } else if (!e.shiftKey && document.activeElement === cuoi) {
          e.preventDefault();
          dau.focus();
        }
      }
    };
    document.addEventListener("keydown", phim, true);
    return () => {
      document.removeEventListener("keydown", phim, true);
      document.body.style.overflow = cuonCu;
      truoc?.focus({ preventScroll: true });
    };
    // onDong đổi theo từng lần dựng của phía gọi; chỉ cần bản mới nhất lúc bấm
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [daGan]);

  if (!daGan) return null;
  return createPortal(
    <div ref={lop} className="sdq-toan-man" role="dialog" aria-modal="true" aria-label="Sơ đồ quy trình thực tế, toàn màn hình">
      <div className="sdq-toan-man-dau">
        <strong>Sơ đồ quy trình thực tế</strong>
        <button type="button" className="nut nut-nho" data-dong-toan-man onClick={onDong}>
          <X aria-hidden /> Đóng
        </button>
      </div>
      <div className="sdq-toan-man-than">{children}</div>
    </div>,
    document.body,
  );
}

// ---------------------------------------------------------------------------
// Thành phần xuất ra
// ---------------------------------------------------------------------------

export function SoDoQuyTrinh(dauVao: DauVaoSoDo) {
  const [toanMan, datToanMan] = useState(false);
  const nutMo = useRef<HTMLButtonElement>(null);
  const dong = useCallback(() => datToanMan(false), []);

  return (
    <>
      <ReactFlowProvider>
        <KhungBen {...dauVao} onMoToanMan={() => datToanMan(true)} nutToanMan={nutMo} />
      </ReactFlowProvider>
      {toanMan ? (
        <LopToanMan onDong={dong}>
          <ReactFlowProvider>
            <KhungBen
              {...dauVao}
              toanMan
              // Chọn một điều trong lớp phủ thì đóng lớp phủ: danh sách hồ sơ mở ở dưới nó sẽ bị che
              onChonTrangThai={(ma) => {
                dong();
                dauVao.onChonTrangThai(ma);
              }}
              onChonNhanh={(kind) => {
                dong();
                dauVao.onChonNhanh(kind);
              }}
            />
          </ReactFlowProvider>
        </LopToanMan>
      ) : null}
    </>
  );
}
