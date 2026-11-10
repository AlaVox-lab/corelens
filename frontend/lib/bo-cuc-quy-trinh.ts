// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Bố cục sơ đồ quy trình thực tế (#315): đặt các trạng thái vào lưới và vẽ đường cong cho từng cạnh,
// bằng `@dagrejs/dagre` (MIT). Hàm thuần — nhận mã trạng thái và các cạnh, trả toạ độ — nên không
// biết trạng thái nào, và chạy được ngoài trình duyệt.
//
// Dagre trả đường đi của cạnh dưới dạng dãy điểm, kể cả cạnh quay ngược (trả về làm lại, mở lại).
// Vẽ đường cong qua các điểm đó, thay vì để thư viện vẽ sơ đồ nối hai tay cầm, thì cạnh quay ngược
// đi vòng ngoài thay vì cuộn lại trên chính nút.

import dagre from "@dagrejs/dagre";

export type HuongBoCuc = "LR" | "TB";

/** Kích thước một nút trạng thái, điểm ảnh. Phải khớp CSS `.sdq-nut`. */
export const RONG_NUT = 144;
export const CAO_NUT = 88;
/** Cao của chip số trên cạnh; dagre chừa chỗ cho nó giữa hai hàng nút. */
export const CAO_NHAN_CANH = 26;

export type CanhDauVao = {
  tu: string;
  den: string;
  /** Bề rộng chip số đặt giữa cạnh, để dagre chừa chỗ. */
  rongNhan: number;
  /** Bề dày nét vẽ, để cạnh song song ngược chiều không đè lên nhau. */
  beDay: number;
};

export type NutBoCuc = { ma: string; x: number; y: number };

export type CanhBoCuc = {
  tu: string;
  den: string;
  /** Thuộc tính `d` của đường cong SVG. */
  d: string;
  nhanX: number;
  nhanY: number;
};

export type KetQuaBoCuc = {
  /** Góc trên trái của nút, như React Flow đòi. */
  nut: NutBoCuc[];
  canh: CanhBoCuc[];
  rong: number;
  cao: number;
};

type Diem = { x: number; y: number };

/** Đường cong mượt đi qua mọi điểm (Catmull–Rom đổi sang Bézier bậc ba). */
function duongMem(p: Diem[]): string {
  if (p.length < 2) return "";
  const r = (n: number) => Math.round(n * 10) / 10;
  let d = `M${r(p[0].x)},${r(p[0].y)}`;
  if (p.length === 2) return `${d} L${r(p[1].x)},${r(p[1].y)}`;
  for (let i = 0; i < p.length - 1; i++) {
    const p0 = p[i - 1] ?? p[i];
    const p1 = p[i];
    const p2 = p[i + 1];
    const p3 = p[i + 2] ?? p2;
    const c1 = { x: p1.x + (p2.x - p0.x) / 6, y: p1.y + (p2.y - p0.y) / 6 };
    const c2 = { x: p2.x - (p3.x - p1.x) / 6, y: p2.y - (p3.y - p1.y) / 6 };
    d += ` C${r(c1.x)},${r(c1.y)} ${r(c2.x)},${r(c2.y)} ${r(p2.x)},${r(p2.y)}`;
  }
  return d;
}

/**
 * Véc-tơ dịch sang bên phải hướng đi của đường, dài `doi` điểm ảnh — để hai cạnh ngược chiều giữa
 * cùng hai trạng thái nằm cạnh nhau thay vì đè lên nhau.
 */
function dichSangPhai(p: Diem[], doi: number): Diem {
  const dau = p[0];
  const cuoi = p[p.length - 1];
  const dx = cuoi.x - dau.x;
  const dy = cuoi.y - dau.y;
  const dai = Math.hypot(dx, dy) || 1;
  // Pháp tuyến bên phải hướng đi, trong hệ toạ độ màn hình (trục y hướng xuống)
  return { x: (-dy / dai) * doi, y: (dx / dai) * doi };
}

export function boCucSoDo(ma: string[], canh: CanhDauVao[], huong: HuongBoCuc): KetQuaBoCuc {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: huong, nodesep: 36, ranksep: 40, edgesep: 18, marginx: 24, marginy: 28 });
  g.setDefaultEdgeLabel(() => ({}));
  for (const m of ma) g.setNode(m, { width: RONG_NUT, height: CAO_NUT });
  for (const c of canh) {
    // Chip số là một nút giả giữa cạnh trong dagre: kích thước nó khai theo chiều của hàng
    g.setEdge(c.tu, c.den, { width: c.rongNhan, height: CAO_NHAN_CANH, labelpos: "c" });
  }
  dagre.layout(g);

  const nut: NutBoCuc[] = ma.map((m) => {
    const n = g.node(m);
    return { ma: m, x: n.x - RONG_NUT / 2, y: n.y - CAO_NUT / 2 };
  });

  const coNguoc = new Set(canh.map((c) => `${c.tu}\u0000${c.den}`));
  const ketQuaCanh: CanhBoCuc[] = canh.map((c) => {
    const e = g.edge(c.tu, c.den);
    let diem: Diem[] = e.points ?? [];
    const giua = diem[Math.floor(diem.length / 2)];
    let nhan: Diem = { x: e.x ?? giua?.x ?? 0, y: e.y ?? giua?.y ?? 0 };
    // Có cạnh ngược chiều giữa cùng hai trạng thái: mỗi cạnh lệch sang bên phải hướng đi của nó
    if (diem.length >= 2 && coNguoc.has(`${c.den}\u0000${c.tu}`)) {
      const dich = dichSangPhai(diem, c.beDay / 2 + 7);
      diem = diem.map((d) => ({ x: d.x + dich.x, y: d.y + dich.y }));
      nhan = { x: nhan.x + dich.x, y: nhan.y + dich.y };
    }
    return { tu: c.tu, den: c.den, d: duongMem(diem), nhanX: nhan.x, nhanY: nhan.y };
  });

  const dd = g.graph();
  return { nut, canh: ketQuaCanh, rong: dd.width ?? 0, cao: dd.height ?? 0 };
}
