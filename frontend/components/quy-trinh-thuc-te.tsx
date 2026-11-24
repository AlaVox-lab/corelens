"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn Quy trình thực tế (#315): vòng phản hồi tự soi quy trình của CLAUDE.md mục 4.1. Từ nhật ký sự
// kiện, dịch vụ khai phá (#314) vẽ lại quy trình đang thật sự chạy; màn này trình bày kết quả:
//
//   câu kết luận → điểm nghẽn → nhánh lệch → đường đi phổ biến → sơ đồ (màn hẹp)
//   câu kết luận → sơ đồ → ba khối trên cạnh nhau                 (màn rộng)
//
// Bấm một trạng thái, một nhánh lệch hay một đường đi thì danh sách hồ sơ tương ứng mở ở ngăn bên
// phải; mỗi mã hồ sơ là liên kết tới trang hồ sơ của buồng lái mà người xem vào được.
//
// Số liệu lấy qua `/api/bao-cao/quy-trinh` (Route Handler, token Keycloak không tới trình duyệt).
// Khoảng ngày nằm trên địa chỉ trang: tải lại hay gửi đường dẫn thì giữ khoảng. Tên trạng thái, loại
// yêu cầu, phòng ban đều đọc từ JSON — tệp này không biết trạng thái nào (CLAUDE.md mục 1.2).
//
// "Hệ thống không phản hồi" khi dịch vụ khai phá tắt (mục 8.3): cổng, hồ sơ và bảng điều khiển vẫn chạy.
//
// Mã nguồn của dịch vụ khai phá (AGPL-3.0-or-later, điều 13 — #340) dẫn từ trang Mã nguồn và giấy phép ở
// chân thanh bên (#540), không lặp trên màn này.

import { FileSearch, Lightbulb, ServerCrash } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useId, useRef, useState } from "react";

import { ManRong } from "@/components/man-rong";
import { NganHoSoQuyTrinh } from "@/components/ngan-ho-so-quy-trinh";
import { SoDoQuyTrinh, type ChonMuc } from "@/components/so-do-quy-trinh";
import { thoiLuongLamViec } from "@/lib/dinh-dang";
import {
  NUT_NHANH,
  docNgay,
  khoangGanNhat,
  soNgayCua,
  type KhoangNgay,
} from "@/lib/khoang-ngay";
import { duongDanHoSo } from "@/lib/khong-gian";
import {
  canhThietKeChuaDi,
  chuPhamVi,
  coNhieuPhong,
  ketLuanQuyTrinh,
  maHienThi,
  nhanLoaiYeuCau,
  nhanPhong,
  nhanTrangThai,
  phanTram,
  soThapPhan,
  soVN,
  tenLoaiCanh,
  tenNhanhLech,
} from "@/lib/ket-luan-quy-trinh";
import type { KhuyenNghiQuyTrinh, NhomChoKhaiPha, NhomDemKhaiPha, QuyTrinhThucTe } from "@/lib/kieu";

type TinhTrang = "dang-tai" | "san-sang" | "khong-phan-hoi" | "het-phien" | "khong-duoc-xem";

/** Số đường đi phổ biến hiện ở khối; từ đường thứ sáu trở đi gộp vào dòng "còn lại". */
const SO_BIEN_THE_HIEN = 5;

/** Mã danh sách hồ sơ đang mở, để ngăn biết khi nào đổi sang danh sách khác. */
function khoaChon(chon: ChonMuc): string {
  return chon.loai === "trang-thai" ? `tt:${chon.ma}` : chon.loai === "nhanh-lech" ? `nl:${chon.kind}` : `bt:${chon.chiSo}`;
}

// ---------------------------------------------------------------------------
// Mã hồ sơ và các khối nhỏ
// ---------------------------------------------------------------------------

/** Mã hồ sơ: liên kết tới trang hồ sơ nếu người xem vào được buồng lái nào, không thì chữ thường. */
function MaHoSo({ ma, ten, khongGian }: { ma: number; ten: string; khongGian: string[] }) {
  const href = duongDanHoSo(ma, khongGian);
  return href ? (
    <Link className="qt-ma" href={href} aria-label={`Hồ sơ ${ten}`}>
      {ten}
    </Link>
  ) : (
    <span className="qt-ma" data-khong-lien-ket="">
      {ten}
    </span>
  );
}

/** Dòng ghi chú khi danh sách bị cắt: "hiện 200 trên 315 hồ sơ". */
function GhiChuCat({ hien, tong }: { hien: number; tong: number }) {
  if (hien >= tong) return null;
  return (
    <p className="qt-ghi-chu">
      Hiện {soVN(hien)} trên {soVN(tong)} hồ sơ.
    </p>
  );
}

function LuoiMaHoSo({ d, cacMa, khongGian }: { d: QuyTrinhThucTe; cacMa: number[]; khongGian: string[] }) {
  return (
    <ul className="qt-luoi-ma">
      {cacMa.map((ma) => (
        <li key={ma}>
          <MaHoSo ma={ma} ten={maHienThi(d, ma)} khongGian={khongGian} />
        </li>
      ))}
    </ul>
  );
}

function TachNhom({
  tieuDe,
  muc,
}: {
  tieuDe: string;
  muc: { ten: string; chu: string }[];
}) {
  if (muc.length === 0) return null;
  return (
    <div className="qt-tach">
      <h3>{tieuDe}</h3>
      <ul>
        {muc.map((m) => (
          <li key={m.ten}>
            <span>{m.ten}</span> <strong>{m.chu}</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Tách số hồ sơ theo loại yêu cầu và phòng; theo phòng chỉ khi so sánh được giữa các phòng. */
function TachDem({
  d,
  theoLoai,
  theoPhong,
}: {
  d: QuyTrinhThucTe;
  theoLoai: NhomDemKhaiPha[];
  theoPhong: NhomDemKhaiPha[];
}) {
  return (
    <>
      <TachNhom
        tieuDe="Theo loại yêu cầu"
        muc={theoLoai.map((n) => ({ ten: nhanLoaiYeuCau(d, n.code), chu: soVN(n.cases_count) }))}
      />
      {coNhieuPhong(d) ? (
        <TachNhom
          tieuDe="Theo phòng"
          muc={theoPhong.map((n) => ({ ten: nhanPhong(d, n.code), chu: soVN(n.cases_count) }))}
        />
      ) : null}
    </>
  );
}

function TachCho({
  d,
  theoLoai,
  theoPhong,
}: {
  d: QuyTrinhThucTe;
  theoLoai: NhomChoKhaiPha[];
  theoPhong: NhomChoKhaiPha[];
}) {
  return (
    <>
      <TachNhom
        tieuDe="Chờ trung vị theo loại yêu cầu"
        muc={theoLoai.map((n) => ({ ten: nhanLoaiYeuCau(d, n.code), chu: thoiLuongLamViec(n.median_wait_seconds) }))}
      />
      {coNhieuPhong(d) ? (
        <TachNhom
          tieuDe="Chờ trung vị theo phòng"
          muc={theoPhong.map((n) => ({ ten: nhanPhong(d, n.code), chu: thoiLuongLamViec(n.median_wait_seconds) }))}
        />
      ) : null}
    </>
  );
}

// ---------------------------------------------------------------------------
// Nội dung ngăn danh sách hồ sơ
// ---------------------------------------------------------------------------

function NoiDungNgan({
  d,
  chon,
  khongGian,
}: {
  d: QuyTrinhThucTe;
  chon: ChonMuc;
  khongGian: string[];
}) {
  if (chon.loai === "trang-thai") {
    const tt = d.states.find((t) => t.code === chon.ma);
    if (!tt) return null;
    return (
      <>
        <p className="qt-ngan-tom-tat">
          {tt.median_wait_seconds !== null
            ? `Chờ trung vị ${thoiLuongLamViec(tt.median_wait_seconds)}`
            : "Không có thời gian chờ"}
          {" · "}
          {soVN(tt.visits)} lượt vào, {soVN(tt.cases)} hồ sơ
          {tt.is_bottleneck ? " · " : null}
          {tt.is_bottleneck ? <span className="qt-the-nghen">Nghẽn</span> : null}
        </p>
        <TachCho d={d} theoLoai={tt.by_request_type} theoPhong={tt.by_department} />
        <GhiChuCat hien={tt.longest_waits.length} tong={tt.cases} />
        <ol className="qt-ds-cho">
          {tt.longest_waits.map((h) => (
            <li key={h.case}>
              <MaHoSo ma={h.case} ten={maHienThi(d, h.case)} khongGian={khongGian} />
              <span className="qt-cho-giay">{thoiLuongLamViec(h.seconds)}</span>
              <span className="qt-cho-luot">{soVN(h.visits)} lượt</span>
              {h.current ? <span className="qt-the-dang-cho">đang chờ</span> : null}
            </li>
          ))}
        </ol>
      </>
    );
  }

  if (chon.loai === "nhanh-lech") {
    const n = d.deviations.find((x) => x.kind === chon.kind);
    if (!n) return null;
    return (
      <>
        <p className="qt-ngan-tom-tat">
          {phanTram(n.ratio)} hồ sơ trong khoảng ({soVN(n.cases_count)} hồ sơ)
        </p>
        <TachDem d={d} theoLoai={n.by_request_type} theoPhong={n.by_department} />
        <GhiChuCat hien={n.cases.length} tong={n.cases_count} />
        <LuoiMaHoSo d={d} cacMa={n.cases} khongGian={khongGian} />
      </>
    );
  }

  const bt = d.variants[chon.chiSo];
  if (!bt) return null;
  return (
    <>
      <p className="qt-ngan-tom-tat">
        {bt.sequence.map((m) => nhanTrangThai(d, m)).join(" → ")}
      </p>
      <p className="qt-ngan-tom-tat">
        {phanTram(bt.ratio)} hồ sơ ({soVN(bt.cases_count)} hồ sơ)
      </p>
      <GhiChuCat hien={bt.cases.length} tong={bt.cases_count} />
      <LuoiMaHoSo d={d} cacMa={bt.cases} khongGian={khongGian} />
    </>
  );
}

function tieuDeNgan(d: QuyTrinhThucTe, chon: ChonMuc): string {
  if (chon.loai === "trang-thai") return `Hồ sơ chờ lâu nhất ở “${nhanTrangThai(d, chon.ma)}”`;
  if (chon.loai === "nhanh-lech") return `Nhánh lệch: ${tenNhanhLech(chon.kind)}`;
  return "Hồ sơ đi theo đường này";
}

// ---------------------------------------------------------------------------
// Các khối của màn
// ---------------------------------------------------------------------------

/** Hỏi lại khuyến nghị đang sinh sau chừng này mili giây, tối đa chừng này lần (#320). */
const HOI_LAI_KHUYEN_NGHI_MS = 3000;
const SO_LAN_HOI_KHUYEN_NGHI = 60;

/**
 * Khuyến nghị cải tiến của mô hình ngôn ngữ (#320), dưới câu kết luận. Màn KHÔNG chờ nó: kết quả khai
 * phá và câu kết luận tất định hiện trước; khuyến nghị đến sau thì hiện thêm, mô hình tắt hay hỏng thì
 * khối này không hiện gì. Dịch vụ đã bỏ mọi câu có con số không tra được trong kết quả khai phá.
 */
function KhuyenNghi({ tu, den }: { tu: string; den: string }) {
  const [cau, datCau] = useState<string[]>([]);

  useEffect(() => {
    datCau([]);
    const huy = new AbortController();
    let hen: ReturnType<typeof setTimeout> | undefined;
    let lan = 0;
    async function hoi() {
      lan += 1;
      try {
        const ph = await fetch(`/api/bao-cao/quy-trinh/khuyen-nghi?tu=${tu}&den=${den}`, {
          cache: "no-store",
          signal: huy.signal,
        });
        const kq = (await ph.json()) as KhuyenNghiQuyTrinh;
        if (kq.status === "pending" && lan < SO_LAN_HOI_KHUYEN_NGHI) {
          hen = setTimeout(hoi, HOI_LAI_KHUYEN_NGHI_MS);
        } else if (kq.status === "ready") {
          datCau(kq.sentences);
        }
      } catch {
        // Hủy vì đổi khoảng ngày, mất mạng: không hiện gì, câu kết luận vẫn đủ
      }
    }
    void hoi();
    return () => {
      clearTimeout(hen);
      huy.abort();
    };
  }, [tu, den]);

  if (cau.length === 0) return null;
  return (
    <div className="qt-khuyen-nghi" data-testid="qt-khuyen-nghi">
      <p className="the-goi-y-dau">
        <Lightbulb aria-hidden />
        <strong>Khuyến nghị cải tiến</strong>
      </p>
      <ul className="qt-cau">
        {cau.map((c, i) => (
          <li key={i}>{c}</li>
        ))}
      </ul>
      <p className="the-goi-y-nguon">
        Gợi ý của hệ thống, do mô hình ngôn ngữ viết từ các con số ở trên — mọi con số đã được đối chiếu
        với kết quả khai phá. Chỉ để tham khảo, hệ thống không tự đổi cấu hình nào.
      </p>
    </div>
  );
}

function KhoiKetLuan({ d }: { d: QuyTrinhThucTe }) {
  const cau = ketLuanQuyTrinh(d);
  return (
    <section className="the qt-khoi qt-ket-luan" aria-labelledby="qt-h-ket-luan">
      <h2 id="qt-h-ket-luan" className="qt-khoi-dau">
        Kết luận
      </h2>
      <ul className="qt-cau">
        {cau.map((c) => (
          <li key={c.id}>{c.chu}</li>
        ))}
      </ul>
      {d.cases_count > 0 ? <KhuyenNghi tu={d.range.from} den={d.range.to} /> : null}
    </section>
  );
}

function KhoiDiemNghen({
  d,
  chon,
  onChon,
}: {
  d: QuyTrinhThucTe;
  chon: ChonMuc | null;
  onChon: (ma: string) => void;
}) {
  const { ranking, factor, overall_median_wait_seconds: chung } = d.bottlenecks;
  return (
    <section className="the qt-khoi" aria-labelledby="qt-h-nghen">
      <h2 id="qt-h-nghen" className="qt-khoi-dau">
        Điểm nghẽn
      </h2>
      <p className="qt-ghi-chu">
        Trạng thái xếp theo thời gian hồ sơ chờ (trung vị, giờ làm việc).
        {chung !== null
          ? ` Nghẽn khi chờ gấp từ ${soThapPhan(factor)} lần mức chung (${thoiLuongLamViec(chung)}).`
          : ""}
      </p>
      {ranking.length === 0 ? (
        <p className="qt-rong">Chưa có thời gian chờ nào để xếp hạng.</p>
      ) : (
        <ol className="qt-ds">
          {ranking.map((r, i) => {
            const bam = d.states.some((t) => t.code === r.code && t.longest_waits.length > 0);
            const noiDung = (
              <>
                <span className="qt-hang">{i + 1}</span>
                <span className="qt-dong-ten">
                  {r.label}
                  {r.is_bottleneck ? <span className="qt-the-nghen">Nghẽn</span> : null}
                </span>
                <span className="qt-dong-so">{thoiLuongLamViec(r.median_wait_seconds)}</span>
              </>
            );
            return (
              <li key={r.code}>
                {bam ? (
                  <button
                    type="button"
                    className="qt-dong"
                    aria-pressed={chon?.loai === "trang-thai" && chon.ma === r.code}
                    onClick={() => onChon(r.code)}
                  >
                    {noiDung}
                  </button>
                ) : (
                  <div className="qt-dong">{noiDung}</div>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

function KhoiNhanhLech({
  d,
  chon,
  onChon,
}: {
  d: QuyTrinhThucTe;
  chon: ChonMuc | null;
  onChon: (kind: string) => void;
}) {
  return (
    <section className="the qt-khoi" aria-labelledby="qt-h-lech">
      <h2 id="qt-h-lech" className="qt-khoi-dau">
        Nhánh lệch
      </h2>
      <p className="qt-ghi-chu">Hồ sơ đi ra ngoài luồng chính, tính trên tổng số hồ sơ trong khoảng.</p>
      <ul className="qt-ds">
        {d.deviations.map((n) => {
          const noiDung = (
            <>
              <span className="qt-cham" data-kenh={n.kind} aria-hidden />
              <span className="qt-dong-ten">{tenNhanhLech(n.kind)}</span>
              <span className="qt-dong-so">
                {n.cases_count > 0 ? `${phanTram(n.ratio)} · ${soVN(n.cases_count)} hồ sơ` : "không có hồ sơ"}
              </span>
            </>
          );
          return (
            <li key={n.kind}>
              {n.cases_count > 0 ? (
                <button
                  type="button"
                  className="qt-dong"
                  aria-pressed={chon?.loai === "nhanh-lech" && chon.kind === n.kind}
                  onClick={() => onChon(n.kind)}
                >
                  {noiDung}
                </button>
              ) : (
                <div className="qt-dong" data-trong="">
                  {noiDung}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function KhoiBienThe({
  d,
  chon,
  onChon,
  onBoChon,
}: {
  d: QuyTrinhThucTe;
  chon: ChonMuc | null;
  onChon: (chiSo: number) => void;
  onBoChon: () => void;
}) {
  const hien = d.variants.slice(0, SO_BIEN_THE_HIEN);
  const conLai = d.variants.slice(SO_BIEN_THE_HIEN).reduce((t, v) => t + v.cases_count, 0) + d.other_variants_cases;
  const dangChon = chon?.loai === "bien-the";
  return (
    <section className="the qt-khoi" aria-labelledby="qt-h-bien-the">
      <div className="qt-khoi-hang">
        <h2 id="qt-h-bien-the" className="qt-khoi-dau">
          Các đường đi phổ biến
        </h2>
        {dangChon ? (
          <button type="button" className="nut nut-nho" onClick={onBoChon}>
            Bỏ chọn
          </button>
        ) : null}
      </div>
      <p className="qt-ghi-chu">Chuỗi trạng thái hồ sơ đã đi qua. Bấm một đường để tô sáng nó trên sơ đồ.</p>
      {hien.length === 0 ? (
        <p className="qt-rong">Chưa có đường đi nào.</p>
      ) : (
        <ol className="qt-ds">
          {hien.map((v, i) => (
            <li key={i}>
              <button
                type="button"
                className="qt-dong qt-dong-chuoi"
                aria-pressed={chon?.loai === "bien-the" && chon.chiSo === i}
                onClick={() => onChon(i)}
              >
                <span className="qt-chuoi">{v.sequence.map((m) => nhanTrangThai(d, m)).join(" → ")}</span>
                <span className="qt-dong-so">
                  {phanTram(v.ratio)} · {soVN(v.cases_count)} hồ sơ
                </span>
              </button>
            </li>
          ))}
        </ol>
      )}
      {conLai > 0 ? <p className="qt-ghi-chu qt-con-lai">Còn lại: {soVN(conLai)} hồ sơ</p> : null}
    </section>
  );
}

function ChuGiai({ d }: { d: QuyTrinhThucTe }) {
  // Chú giải theo dữ liệu: chỉ những loại cạnh thật sự có trên sơ đồ
  const loai = new Set<string>();
  for (const c of d.edges) for (const k of Object.keys(c.kinds)) loai.add(k);
  const thuTu = ["main", ...d.deviations.map((n) => n.kind).filter((k) => loai.has(k) && k !== "main")];
  const conLai = [...loai].filter((k) => !thuTu.includes(k));
  const coChuaDi = canhThietKeChuaDi(d).length > 0;
  const coNghen = d.states.some((t) => t.is_bottleneck);
  return (
    <ul className="qt-chu-giai" aria-label="Chú giải sơ đồ">
      {[...thuTu, ...conLai].map((k) => (
        <li key={k}>
          <span className="qt-net" data-kenh={k} aria-hidden />
          {tenLoaiCanh(k)}
        </li>
      ))}
      {coChuaDi ? (
        <li>
          <span className="qt-net" data-chua-di="" aria-hidden />
          Chưa có hồ sơ đi qua
        </li>
      ) : null}
      {coNghen ? (
        <li>
          <span className="qt-the-nghen">Nghẽn</span> Điểm nghẽn
        </li>
      ) : null}
      <li className="qt-chu-giai-ghi">Nét càng dày càng nhiều lượt đi qua.</li>
    </ul>
  );
}

function KhungChoQuyTrinh() {
  return (
    <div className="qt-ket-qua" role="status" aria-label="Đang tải quy trình thực tế">
      <div className="the qt-khoi">
        <span className="khung-cho-vach" style={{ width: "120px", height: "16px" }} />
        <span className="khung-cho-vach" style={{ width: "92%", height: "14px", marginTop: "14px" }} />
        <span className="khung-cho-vach" style={{ width: "78%", height: "14px", marginTop: "10px" }} />
        <span className="khung-cho-vach" style={{ width: "84%", height: "14px", marginTop: "10px" }} />
      </div>
      <div className="the qt-khung-cho-so-do">
        <span className="khung-cho-vach" style={{ width: "100%", height: "100%", borderRadius: 0 }} />
      </div>
      <div className="qt-luoi">
        {[0, 1, 2].map((i) => (
          <div key={i} className="the qt-khoi">
            <span className="khung-cho-vach" style={{ width: "50%", height: "16px" }} />
            <span className="khung-cho-vach" style={{ width: "100%", height: "36px", marginTop: "14px" }} />
            <span className="khung-cho-vach" style={{ width: "100%", height: "36px", marginTop: "8px" }} />
            <span className="khung-cho-vach" style={{ width: "100%", height: "36px", marginTop: "8px" }} />
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Màn
// ---------------------------------------------------------------------------

export function QuyTrinhThucTe({
  khoangBanDau,
  khongGian,
}: {
  khoangBanDau: KhoangNgay;
  /** Không gian làm việc của người xem (`/me`), để biết mã hồ sơ dẫn tới buồng lái nào. */
  khongGian: string[];
}) {
  const [khoang, datKhoang] = useState<KhoangNgay>(khoangBanDau);
  const [duLieu, datDuLieu] = useState<QuyTrinhThucTe | null>(null);
  const [tinhTrang, datTinhTrang] = useState<TinhTrang>("dang-tai");
  const [loiNgay, datLoiNgay] = useState<string | null>(null);
  // Điều đang chọn (tô sáng trên sơ đồ) tách khỏi việc ngăn danh sách có đang mở: đóng ngăn rồi mà
  // đường đi vừa chọn vẫn sáng trên sơ đồ, cho tới khi bấm lại hay bấm "Bỏ chọn"
  const [lua, datLua] = useState<{ chon: ChonMuc | null; nganMo: boolean }>({ chon: null, nganMo: false });
  const { chon, nganMo } = lua;
  // Tăng lên mỗi lần bấm Thử lại để tải lại đúng khoảng đang xem
  const [lanThu, datLanThu] = useState(0);
  const daTaiLanDau = useRef(false);
  const idLoiNgay = useId();
  const idTieuDeNgan = useId();

  useEffect(() => {
    const tu = docNgay(khoang.tu);
    const den = docNgay(khoang.den);
    if (!tu || !den) {
      datLoiNgay("Chọn đủ hai ngày, theo dạng ngày/tháng/năm.");
      return;
    }
    // Khoảng ghi lên địa chỉ: tải lại hay gửi đường dẫn thì giữ khoảng
    const diaChi = new URL(window.location.href);
    diaChi.searchParams.set("tu", tu);
    diaChi.searchParams.set("den", den);
    window.history.replaceState(null, "", diaChi);

    const huy = new AbortController();
    // Gõ tay vào ô ngày sinh ra nhiều giá trị hợp lệ liên tiếp: đợi một nhịp rồi mới hỏi dịch vụ
    const hen = setTimeout(
      async () => {
        datTinhTrang("dang-tai");
        try {
          const phanHoi = await fetch(`/api/bao-cao/quy-trinh?tu=${tu}&den=${den}`, {
            cache: "no-store",
            signal: huy.signal,
          });
          if (phanHoi.ok) {
            datDuLieu((await phanHoi.json()) as QuyTrinhThucTe);
            datLoiNgay(null);
            datLua({ chon: null, nganMo: false });
            datTinhTrang("san-sang");
          } else if (phanHoi.status === 422) {
            const than = (await phanHoi.json().catch(() => null)) as { thongDiep?: string } | null;
            datLoiNgay(than?.thongDiep ?? "Khoảng ngày không hợp lệ.");
            datTinhTrang("san-sang");
          } else {
            datTinhTrang(phanHoi.status === 401 ? "het-phien" : phanHoi.status === 403 ? "khong-duoc-xem" : "khong-phan-hoi");
          }
        } catch {
          if (!huy.signal.aborted) datTinhTrang("khong-phan-hoi");
        }
      },
      daTaiLanDau.current ? 250 : 0,
    );
    daTaiLanDau.current = true;
    datLoiNgay(null);
    return () => {
      clearTimeout(hen);
      huy.abort();
    };
  }, [khoang.tu, khoang.den, lanThu]);

  // Bấm một điều: chọn và mở ngăn. Bấm lại đúng điều đang chọn khi ngăn đang mở thì bỏ chọn; ngăn đã
  // đóng thì mở lại
  const chonMuc = useCallback(
    (m: ChonMuc) =>
      datLua((c) =>
        c.chon && c.nganMo && khoaChon(c.chon) === khoaChon(m)
          ? { chon: null, nganMo: false }
          : { chon: m, nganMo: true },
      ),
    [],
  );
  const chonTrangThai = useCallback((ma: string) => chonMuc({ loai: "trang-thai", ma }), [chonMuc]);
  const chonNhanh = useCallback((kind: string) => chonMuc({ loai: "nhanh-lech", kind }), [chonMuc]);
  const chonBienThe = useCallback((chiSo: number) => chonMuc({ loai: "bien-the", chiSo }), [chonMuc]);
  const boChon = useCallback(() => datLua({ chon: null, nganMo: false }), []);
  const dongNgan = useCallback(() => datLua((c) => ({ ...c, nganMo: false })), []);

  // Mốc "hôm nay" cho các nút nhanh; dựng lại mỗi lần vẽ là đủ, chỉ lệch khi qua nửa đêm giữa chừng
  const soNgay = soNgayCua(khoang);
  const homNay = khoangGanNhat(1, new Date()).den;

  if (tinhTrang === "het-phien" || tinhTrang === "khong-duoc-xem" || (tinhTrang === "khong-phan-hoi" && !duLieu)) {
    const noiDung = {
      "khong-phan-hoi": {
        tieuDe: "Hệ thống không phản hồi",
        cau: "Quy trình thực tế chưa tải được. Hồ sơ và mọi thao tác vẫn bình thường — thử lại sau ít phút.",
      },
      "het-phien": {
        tieuDe: "Phiên đăng nhập đã hết hạn",
        cau: "Tải lại trang để đăng nhập lại, rồi mở Quy trình thực tế lần nữa.",
      },
      "khong-duoc-xem": {
        tieuDe: "Tài khoản này không xem được báo cáo",
        cau: "Quyền xem báo cáo cấp theo vai trò. Cần xem thì nhờ quản trị hệ thống.",
      },
    }[tinhTrang as "khong-phan-hoi" | "het-phien" | "khong-duoc-xem"];
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

  const phamVi = duLieu ? chuPhamVi(duLieu) : null;

  return (
    <>
      <div className="qt-cong-cu khong-in">
        <div className="qt-nut-nhanh" role="group" aria-label="Chọn nhanh khoảng ngày">
          {NUT_NHANH.map((n) => (
            <button
              key={n.soNgay}
              type="button"
              className="chip"
              aria-pressed={khoang.den === homNay && soNgay === n.soNgay}
              onClick={() => datKhoang(khoangGanNhat(n.soNgay, new Date()))}
            >
              {n.nhan}
            </button>
          ))}
        </div>
        <div className="qt-o-ngay">
          <label>
            <span>Từ ngày</span>
            <input
              type="date"
              className="o-nhap"
              value={khoang.tu}
              max={khoang.den || undefined}
              aria-invalid={loiNgay ? true : undefined}
              aria-describedby={loiNgay ? idLoiNgay : undefined}
              onChange={(e) => datKhoang((k) => ({ ...k, tu: e.target.value }))}
            />
          </label>
          <label>
            <span>Đến ngày</span>
            <input
              type="date"
              className="o-nhap"
              value={khoang.den}
              min={khoang.tu || undefined}
              aria-invalid={loiNgay ? true : undefined}
              aria-describedby={loiNgay ? idLoiNgay : undefined}
              onChange={(e) => datKhoang((k) => ({ ...k, den: e.target.value }))}
            />
          </label>
        </div>
      </div>
      {loiNgay ? (
        <p id={idLoiNgay} role="alert" className="qt-loi-ngay">
          {loiNgay}
        </p>
      ) : null}
      <p className="bao-cao-pham-vi">
        {phamVi ? (
          <>
            Phạm vi số liệu: <strong>{duLieu!.scope.all ? "toàn công ty" : duLieu!.scope.departments.map((p) => p.label).join(", ")}</strong>
          </>
        ) : (
          <>&nbsp;</>
        )}
      </p>

      {loiNgay ? null : !duLieu ? (
        <KhungChoQuyTrinh />
      ) : duLieu.cases_count === 0 ? (
        <div className="the" style={{ marginTop: "16px" }} aria-busy={tinhTrang === "dang-tai"}>
          <ManRong
            icon={FileSearch}
            tieuDe="Không có hồ sơ nào gửi trong khoảng này"
            cau="Thử chọn khoảng ngày dài hơn, hoặc kiểm tra lại phạm vi số liệu bạn được xem."
          />
        </div>
      ) : (
        <div className="qt-ket-qua" aria-busy={tinhTrang === "dang-tai"} data-dang-tai={tinhTrang === "dang-tai" ? "" : undefined}>
          {tinhTrang === "khong-phan-hoi" ? (
            <div className="the qt-bao-loi" role="alert">
              <span>Hệ thống không phản hồi. Đang hiện số liệu của lần tải trước.</span>
              <button type="button" className="nut nut-nho" onClick={() => datLanThu((n) => n + 1)}>
                Thử lại
              </button>
            </div>
          ) : null}
          <KhoiKetLuan d={duLieu} />
          <section className="the qt-so-do" aria-labelledby="qt-h-so-do">
            <div className="qt-so-do-dau">
              <div className="qt-khoi-hang">
                <h2 id="qt-h-so-do" className="qt-khoi-dau">
                  Sơ đồ quy trình
                </h2>
                {/* Đường đi có nút "Bỏ chọn" riêng ở khối của nó; các lựa chọn khác dùng nút này */}
                {chon && chon.loai !== "bien-the" ? (
                  <button type="button" className="nut nut-nho" onClick={boChon}>
                    Bỏ chọn
                  </button>
                ) : null}
              </div>
              <ChuGiai d={duLieu} />
            </div>
            <SoDoQuyTrinh duLieu={duLieu} chon={chon} onChonTrangThai={chonTrangThai} onChonNhanh={chonNhanh} />
          </section>
          <div className="qt-luoi">
            <KhoiDiemNghen d={duLieu} chon={chon} onChon={chonTrangThai} />
            <KhoiNhanhLech d={duLieu} chon={chon} onChon={chonNhanh} />
            <KhoiBienThe d={duLieu} chon={chon} onChon={chonBienThe} onBoChon={boChon} />
          </div>
          <p className="qt-chan">
            Tính từ {soVN(duLieu.cases_count)} hồ sơ, {soVN(duLieu.events_count)} sự kiện.
          </p>
        </div>
      )}

      {chon && nganMo && duLieu ? (
        <NganHoSoQuyTrinh
          idTieuDe={idTieuDeNgan}
          tieuDe={tieuDeNgan(duLieu, chon)}
          khoaNoiDung={khoaChon(chon)}
          onDong={dongNgan}
        >
          <NoiDungNgan d={duLieu} chon={chon} khongGian={khongGian} />
        </NganHoSoQuyTrinh>
      ) : null}
    </>
  );
}
