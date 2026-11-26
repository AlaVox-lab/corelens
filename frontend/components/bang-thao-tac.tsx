"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Bảng thao tác trên một hồ sơ, dùng chung cho buồng lái điều phối (#82) và buồng lái
// phòng ban (#83). Mỗi buồng lái truyền vào thao tác gửi đi của riêng nó, vì mỗi nơi có
// một cửa riêng ở phía dịch vụ.
//
// KHUÔN MẪU ARCHITECTURE.md MỤC 7.2, KÉO DÀI TỪ NÚT SANG Ô NHẬP. Nút bấm dựng từ
// `allowed_transitions`; ô nhập của mỗi thao tác dựng từ `fields` của cạnh đó — tức từ
// ràng buộc gắn trên cạnh (#78). Không có bảng nào trong tệp này nói "Phân loại thì hiện
// ô mức ưu tiên" hay "Nhận việc thì hiện ô người xử lý".
//
// Mỗi thao tác đều mở một bảng xác nhận, kể cả thao tác không cần nhập gì. Hai lý do:
// người bấm thấy rõ hồ sơ sẽ chuyển sang trạng thái nào trước khi bấm, và chỉ ô nhập
// của đúng thao tác đang mở nằm trong biểu mẫu — không có chuyện ô của thao tác này lọt
// vào lần gửi của thao tác kia.
//
// Trang hồ sơ đầy đủ (#561): bảng tự dựng tiêu đề "Bạn có thể làm gì lúc này" và một hàng nút ngang
// cạnh nó; khung nhập mở ngay dưới, không in lại tên thao tác (nút xác nhận đã mang tên đó), ô có gợi ý
// xếp lưới hai cột — một cột khi khung hẹp dưới 560 px.
//
// Ở đáy ngăn xem nhanh của hàng đợi (#233, `ngan`), bước chính đang chờ người xem
// (`is_primary`, dịch vụ đánh dấu từ dữ liệu quy tắc) thành nút chính chiếm trọn hàng, các
// thao tác còn lại vào menu "Thao tác khác". Mở một thao tác thì nội dung hồ sơ trong ngăn thu thành
// đoạn tóm tắt, khung nhập ở dưới, hàng nút xác nhận / Hủy thao tác / Thao tác khác dính đáy ngăn (#561).
// Gửi xong thì chuyển sang hồ sơ kế của danh sách.

import { ChevronDown } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type ReactNode, useActionState, useEffect, useId, useRef, useState } from "react";

import { CHUA_CO_LOI, type KetQuaThaoTac } from "@/app/yeu-cau/ket-qua";
import { CanhBaoKetThuc } from "@/components/canh-bao-ket-thuc";
import { NhanTrangThai } from "@/components/nhan-trang-thai";
import { CanCuTuongTu } from "@/components/can-cu-tuong-tu";
import { TheGoiY } from "@/components/the-goi-y";
import { TIEN_TO_TRUONG } from "@/lib/bieu-mau";
import { useAnCham } from "@/lib/chuyen-dong";
import { nhanNutXacNhan } from "@/lib/dinh-dang";
import type { CanhDiDuoc, GoiY, LoaiYeuCau, NhanCoMa } from "@/lib/kieu";
import { kieuTruong, type KieuTruong, type NguonDanhMuc } from "@/lib/truong";

/** Lựa chọn cho một ô chọn, hoặc lý do không nạp được chúng. */
export type NguonLuaChon = NhanCoMa[] | { loi: string };

type Props = {
  maHoSo: number;
  cacCanh: CanhDiDuoc[];
  /** Giá trị điền sẵn cho từng trường: giá trị hồ sơ đang có, hoặc gợi ý. */
  giaTriDau: Record<string, string>;
  /** Gợi ý của hệ thống theo trường (#239): hiện thành thẻ ngay trên ô chọn của trường đó. */
  goiY: Record<string, GoiY>;
  /**
   * Danh mục loại yêu cầu kèm gợi ý của từng loại. Có thì thẻ gợi ý của ô phụ thuộc loại đổi theo
   * khi người dùng đổi loại trong cùng biểu mẫu; không có thì thẻ đứng yên.
   */
  cacLoai?: LoaiYeuCau[];
  danhMuc: Partial<Record<NguonDanhMuc, NguonLuaChon>>;
  /** Thao tác gửi đi — một server action của buồng lái đang dùng bảng này. */
  hanhDong: (truoc: KetQuaThaoTac, duLieu: FormData) => Promise<KetQuaThaoTac>;
  /** Khi không còn thao tác nào: câu giải thích và đường về hàng đợi. */
  khiHet: { cau: string; veHangDoi: string };
  /**
   * Bảng nằm ở đáy ngăn xem nhanh (#233): gửi xong thì sang `sauKhiXong`. `tomTat`: đoạn tóm tắt nội dung hồ sơ hiện
   * thay thẻ Nội dung và Dòng thời gian khi một thao tác đang mở (#561).
   */
  ngan?: { sauKhiXong: string; tomTat?: string };
  /** Một câu dưới hàng nút — ví dụ hồ sơ của chính điều phối viên (#154). */
  ghiChu?: string;
  /**
   * Trường mà thẻ gợi ý kèm hồ sơ đã giải quyết tương tự làm căn cứ (#450) — chỉ màn điều phối truyền. Mỗi
   * bảng chỉ một khối, ở thẻ của trường đầu tiên có gợi ý (#559), để danh sách không lặp lại dưới mọi thẻ.
   */
  canCuTuongTu?: readonly string[];
};

const KIEU_NHAN: React.CSSProperties = { fontSize: "13px", fontWeight: 600 };

/**
 * Một ô nhập cho một trường mà cạnh cho đặt. Dùng chung cho buồng lái và cho cổng người
 * gửi — ở cổng, chỉ thao tác sửa nội dung có trường (#127).
 */
export function OTruong({
  truong,
  giaTriDau,
  goiY,
  cacLoai,
  nguon,
  canCu,
}: {
  truong: string;
  giaTriDau: string;
  goiY?: GoiY;
  /** Xem `Props.cacLoai`. */
  cacLoai?: LoaiYeuCau[];
  nguon?: NguonLuaChon;
  canCu?: ReactNode;
}) {
  const kieu = kieuTruong(truong);
  const ten = `${TIEN_TO_TRUONG}${truong}`;

  // Danh mục không nạp được — ví dụ danh bạ Keycloak không trả lời. Khóa ô lại và nói
  // lý do. Ô bị khóa thì trình duyệt không gửi nó đi, nên thao tác vẫn làm được nếu
  // trường này không bắt buộc; nếu bắt buộc, ràng buộc trên cạnh sẽ nói rõ.
  if (nguon && !Array.isArray(nguon)) {
    return (
      <label style={{ display: "grid", gap: "6px" }}>
        <span style={KIEU_NHAN}>{kieu.nhan}</span>
        <select disabled className="o-nhap">
          <option>Không nạp được danh sách</option>
        </select>
        <span role="status" style={{ fontSize: "12.5px", color: "var(--f-r-ink)", lineHeight: 1.55 }}>
          {nguon.loi}
        </span>
      </label>
    );
  }

  if (!nguon) {
    return (
      <label style={{ display: "grid", gap: "6px" }}>
        <span style={KIEU_NHAN}>{kieu.nhan}</span>
        {kieu.dai ? (
          <textarea name={ten} defaultValue={giaTriDau} className="o-nhap" rows={5} />
        ) : kieu.so ? (
          <input
            name={ten}
            defaultValue={giaTriDau}
            className="o-nhap"
            type="number"
            min={1}
            step={1}
            inputMode="numeric"
          />
        ) : (
          <input name={ten} defaultValue={giaTriDau} className="o-nhap" />
        )}
      </label>
    );
  }

  return (
    <OChon
      ten={ten}
      kieu={kieu}
      giaTriDau={giaTriDau}
      goiY={goiY}
      cacLoai={cacLoai}
      lua={nguon}
      canCu={canCu}
    />
  );
}

/**
 * Ô chọn, kèm thẻ gợi ý khi trường có gợi ý (#239).
 *
 * Gợi ý điền sẵn ô; người dùng đổi tùy ý và xác nhận bằng nút của bảng. Hai quy tắc của thẻ:
 * - Thẻ nói "bạn đang chọn khác gợi ý" khi giá trị ô khác giá trị gợi ý — không chặn gì.
 * - Nếu trường có gợi ý theo loại (`goiYTheoLoai`) và gợi ý đang có không phải của mô hình, đổi ô
 *   loại trong cùng biểu mẫu thì thẻ và giá trị điền sẵn đổi theo loại mới. Người dùng đã tự đổi
 *   ô này, hay hồ sơ đã có sẵn giá trị khác gợi ý, thì chỉ thẻ đổi, giá trị của họ giữ nguyên.
 *   Gợi ý của mô hình đọc từ nội dung hồ sơ chứ không từ loại nên không đổi theo loại.
 */
function OChon({
  ten,
  kieu,
  giaTriDau,
  goiY,
  cacLoai,
  lua,
  canCu,
}: {
  ten: string;
  kieu: KieuTruong;
  giaTriDau: string;
  goiY?: GoiY;
  cacLoai?: LoaiYeuCau[];
  lua: NhanCoMa[];
  canCu?: ReactNode;
}) {
  const id = useId();
  const idThe = `${id}-goi-y`;
  const oChon = useRef<HTMLSelectElement>(null);

  // Giá trị đang có mà không còn trong danh sách — người xử lý đã rời phòng chẳng hạn —
  // thì để trống. Không có ô trống, trình duyệt sẽ âm thầm chọn mục đầu tiên, và một
  // cú bấm xác nhận vội sẽ giao hồ sơ cho người không ai chọn.
  const [chon, datChon] = useState(lua.some((m) => m.code === giaTriDau) ? giaTriDau : "");
  const [goiYHienTai, datGoiY] = useState<GoiY | null>(goiY ?? null);
  // Người dùng đã tự quyết ô này: đã đổi tay, hoặc hồ sơ vào đây với một giá trị khác gợi ý
  const daTuQuyet = useRef(giaTriDau !== "" && giaTriDau !== goiY?.code);

  const theoLoai = kieu.goiYTheoLoai;
  const gocGoiY = goiY?.source;
  useEffect(() => {
    if (!theoLoai || !cacLoai || gocGoiY === "model") return;
    const oLoai = oChon.current?.form?.elements.namedItem(`${TIEN_TO_TRUONG}${theoLoai.truong}`);
    if (!(oLoai instanceof HTMLSelectElement)) return;
    const doi = () => {
      const loai = cacLoai.find((l) => l.code === oLoai.value);
      const moi = (loai && theoLoai.lay(loai)) ?? null;
      datGoiY(moi);
      if (!daTuQuyet.current) datChon(moi && lua.some((m) => m.code === moi.code) ? moi.code : "");
    };
    oLoai.addEventListener("change", doi);
    return () => oLoai.removeEventListener("change", doi);
  }, [theoLoai, cacLoai, gocGoiY, lua]);

  return (
    <div style={{ display: "grid", gap: "6px" }}>
      <label htmlFor={id} style={KIEU_NHAN}>
        {kieu.nhan}
      </label>
      {goiYHienTai && <TheGoiY id={idThe} goiY={goiYHienTai} dangChon={chon} canCu={canCu} />}
      <select
        id={id}
        ref={oChon}
        name={ten}
        value={chon}
        onChange={(e) => {
          daTuQuyet.current = true;
          datChon(e.target.value);
        }}
        aria-describedby={goiYHienTai ? idThe : undefined}
        className="o-nhap"
      >
        {/* Không có giá trị sẵn thì để trống. Gửi đi trống thì ràng buộc trên cạnh
            sẽ nói rõ phải chọn gì — không đoán hộ người dùng. */}
        {chon === "" && <option value="">— Chọn {kieu.nhan.toLowerCase()} —</option>}
        {lua.map((m) => (
          <option key={m.code} value={m.code}>
            {m.label}
            {m.code === goiYHienTai?.code ? " · gợi ý" : ""}
          </option>
        ))}
      </select>
    </div>
  );
}

export function BangThaoTac({
  maHoSo,
  cacCanh,
  giaTriDau,
  goiY,
  cacLoai,
  danhMuc,
  hanhDong,
  khiHet,
  ngan,
  canCuTuongTu,
  ghiChu,
}: Props) {
  const router = useRouter();
  // Trong ngăn: thao tác thành công thì sang hồ sơ kế. Server Action trả `CHUA_CO_LOI` cả khi
  // chưa gửi lẫn khi gửi xong, nên bắt thành công ngay tại lần gọi.
  const [ketQua, thucHien, dangChay] = useActionState(
    ngan
      ? async (truoc: KetQuaThaoTac, duLieu: FormData) => {
          const kq = await hanhDong(truoc, duLieu);
          if (!kq.loi) router.replace(ngan.sauKhiXong, { scroll: false });
          return kq;
        }
      : hanhDong,
    CHUA_CO_LOI,
  );
  const [dangMo, datDangMo] = useState<CanhDiDuoc | null>(null);
  // Khung xác nhận trượt ra rồi mới gỡ (#237)
  const [dangAn, an] = useAnCham();
  const dongKhung = () => an(() => datDangMo(null));
  const menu = useRef<HTMLDetailsElement>(null);
  // Một khối hồ sơ tương tự mỗi bảng (#559): bảng Chuyển về phòng ban có cả ô loại lẫn ô phòng, mỗi ô một thẻ
  // gợi ý — khối gắn ở thẻ của trường đầu tiên có gợi ý, không lặp dưới thẻ sau
  const truongCanCu = dangMo?.fields.find((t) => canCuTuongTu?.includes(t) && goiY[t]);

  // Ngăn (#561): mở thao tác thì nút vừa bấm rời hàng nút — tiêu điểm vào chính khung (nhóm mang tên thao tác: trình
  // đọc màn hình nói đang mở gì, Tab đi tiếp vào ô đầu, Esc vẫn đóng ngăn — vào thẳng ô chọn thì ngăn coi là đang gõ
  // và giữ phím Esc); đóng khung thì trả về nút ở đáy ngăn, để người dùng bàn phím không rơi về đầu trang
  const bieuMau = useRef<HTMLFormElement>(null);
  const daMoKhung = useRef(false);
  // Cờ chứ không phải đối tượng `ngan` — trang dựng đối tượng mới mỗi lần, hiệu ứng sẽ chạy lại và giật tiêu điểm
  const laNgan = Boolean(ngan);
  useEffect(() => {
    if (!laNgan) return;
    const f = bieuMau.current;
    if (dangMo) {
      f?.querySelector<HTMLElement>(".khung-xac-nhan")?.focus();
    } else if (daMoKhung.current) {
      f?.querySelector<HTMLElement>(".hang-nut-ngan .nut, .hang-nut-ngan summary")?.focus();
    }
    daMoKhung.current = dangMo !== null;
  }, [dangMo, laNgan]);

  if (cacCanh.length === 0) {
    // Trong ngăn, danh sách đã ở ngay bên cạnh: chỉ còn câu
    if (ngan) {
      return (
        <div id="thao-tac" className="thao-tac-het">
          <p>{khiHet.cau}</p>
        </div>
      );
    }
    return (
      <div id="thao-tac" className="bang-thao-tac">
        <div className="thao-tac-dau">
          <h2 className="tua-thao-tac" id="tua-thao-tac">
            Bạn có thể làm gì lúc này
          </h2>
        </div>
        <div className="thao-tac-het">
          <p>{khiHet.cau}</p>
          <Link href={khiHet.veHangDoi} className="nut" data-loai="chinh">
            ← Về hàng đợi
          </Link>
        </div>
      </div>
    );
  }

  /** Nút mở một thao tác. Trong menu của ngăn kèm dấu +/− và trải hết hàng; ở trang đầy đủ là nút ngang gọn. */
  const nutCanh = (canh: CanhDiDuoc, chinh: boolean, trongMenu = false) => {
    const mo = dangMo?.to_state === canh.to_state;
    return (
      <button
        key={canh.to_state}
        type="button"
        className="nut"
        // Nút tô màu chính là bước chính đang chờ người xem (`is_primary`, từ dữ liệu quy tắc) — không phải
        // "thao tác có ô nhập": trước #557 điều phối viên ở Chờ phòng ban xác duyệt thấy Gia hạn xử lý tô đậm
        // chỉ vì nó có ô số giờ.
        data-loai={chinh ? "chinh" : undefined}
        aria-expanded={mo}
        onClick={() => {
          if (mo) dongKhung();
          else datDangMo(canh);
          if (menu.current) menu.current.open = false;
        }}
        style={trongMenu ? { justifyContent: "space-between", width: "100%" } : undefined}
      >
        <span>{canh.activity_label}</span>
        {trongMenu && <span aria-hidden="true">{mo ? "−" : "+"}</span>}
      </button>
    );
  };

  /** Menu "Thao tác khác" của ngăn: mọi thao tác trừ `tru` — bước chính đã có nút riêng, hay thao tác đang mở. */
  const menuThaoTac = (tru: CanhDiDuoc | undefined, nhan: string) => {
    const ds = cacCanh.filter((c) => c.to_state !== tru?.to_state);
    if (ds.length === 0) return null;
    return (
      <details
        className="menu-thao-tac"
        ref={menu}
        // Thẻ gốc không tự đóng bằng Esc: đóng và trả tiêu điểm về nút mở menu. Ngăn
        // xem nhanh thấy phím đã được dùng nên không đóng theo.
        onKeyDown={(e) => {
          if (e.key !== "Escape" || !menu.current?.open) return;
          e.preventDefault();
          menu.current.open = false;
          menu.current.querySelector("summary")?.focus();
        }}
      >
        <summary className="nut">
          {nhan}
          <ChevronDown aria-hidden />
        </summary>
        <div className="menu-thao-tac-ds">{ds.map((c) => nutCanh(c, false, true))}</div>
      </details>
    );
  };

  const nutXacNhan = dangMo && (
    <>
      <button
        type="submit"
        name="to_state"
        value={dangMo.to_state}
        className="nut"
        data-loai="chinh"
        disabled={dangChay}
      >
        {dangChay ? "Đang gửi…" : nhanNutXacNhan(dangMo.activity_label)}
      </button>
      <button type="button" className="nut" onClick={dongKhung}>
        Hủy thao tác
      </button>
    </>
  );

  // Ô có gợi ý xếp lưới hai cột (#561) — thẻ gợi ý nằm ngay trên ô của nó, nên hai thẻ đứng cạnh nhau thay vì
  // chồng thành một cột dài; ô không có gợi ý trải trọn hàng như trước
  const cacO = (dangMo?.fields ?? []).map((truong) => {
    const nguonMa = kieuTruong(truong).nguon;
    return {
      coGoiY: Boolean(goiY[truong]),
      o: (
        <OTruong
          key={truong}
          truong={truong}
          giaTriDau={giaTriDau[truong] ?? ""}
          goiY={goiY[truong]}
          cacLoai={cacLoai}
          nguon={nguonMa ? danhMuc[nguonMa] : undefined}
          canCu={truong === truongCanCu ? <CanCuTuongTu maHoSo={maHoSo} /> : undefined}
        />
      ),
    };
  });
  const oGoiY = cacO.filter((o) => o.coGoiY);

  const buocChinh = ngan ? cacCanh.find((c) => c.is_primary) : undefined;

  return (
    <form id="thao-tac" ref={bieuMau} action={thucHien} className={ngan ? "bang-thao-tac-ngan" : "bang-thao-tac"}>
      <input type="hidden" name="case_id" value={maHoSo} />

      {ngan ? (
        // Ngăn xem nhanh (#233): chưa mở thao tác nào thì bước chính là nút chính chiếm trọn hàng, còn lại vào menu
        !dangMo && (
          <div className="hang-nut-ngan">
            {buocChinh && nutCanh(buocChinh, true)}
            {menuThaoTac(buocChinh, buocChinh ? "Thao tác khác" : "Thao tác")}
          </div>
        )
      ) : (
        // Trang đầy đủ (#561): tiêu đề và các nút thao tác một hàng ở đầu thẻ, theo thứ tự dịch vụ trả về
        <div className="thao-tac-dau">
          <h2 className="tua-thao-tac" id="tua-thao-tac">
            Bạn có thể làm gì lúc này
          </h2>
          <div className="hang-nut-trang">{cacCanh.map((canh) => nutCanh(canh, canh.is_primary === true))}</div>
        </div>
      )}

      {ghiChu && <p className="thao-tac-ghi">{ghiChu}</p>}

      {/* Ngăn, đang mở thao tác (#561): nội dung hồ sơ thu thành một đoạn ngay trên khung nhập — người phân loại
          vẫn đọc được mô tả. Nút đóng khung để thẻ Nội dung và Dòng thời gian trở lại. */}
      {ngan && dangMo && ngan.tomTat && (
        <div className="ngan-tom-tat">
          <p className="ngan-tom-tat-tua">Tóm tắt nội dung</p>
          <p className="ngan-tom-tat-chu">{ngan.tomTat}</p>
          <button type="button" className="nut-lien-ket" onClick={dongKhung}>
            Xem đủ nội dung và dòng thời gian
          </button>
        </div>
      )}

      {dangMo && (
        <div
          // Đổi thao tác thì dựng lại ô nhập, để giá trị điền sẵn không mang từ thao
          // tác trước sang.
          key={dangMo.to_state}
          className="khung-xac-nhan hien-ra"
          data-an={dangAn ? "" : undefined}
          // Khung không in tên thao tác (#561): nhóm mang tên đó cho trình đọc màn hình; nhận tiêu điểm khi mở trong ngăn
          role="group"
          aria-label={dangMo.activity_label}
          tabIndex={-1}
        >
          {/* Không in lại tên thao tác (#561): nút vừa bấm và nút xác nhận đã mang tên đó */}
          <p className="khung-dich">
            {/* Cạnh tự trỏ đổi hồ sơ mà không đổi trạng thái (ADR-0005) */}
            {dangMo.keeps_state ? "Trạng thái giữ nguyên" : "Hồ sơ sẽ chuyển sang"}
            <NhanTrangThai ma={dangMo.to_state} nhan={dangMo.to_state_label} />
          </p>

          {oGoiY.length > 0 && <div className="luoi-goi-y">{oGoiY.map((o) => o.o)}</div>}
          {cacO.filter((o) => !o.coGoiY).map((o) => o.o)}

          {dangMo.to_state_is_terminal && (
            <CanhBaoKetThuc
              nhanTrangThai={dangMo.to_state_label}
              moLaiGio={dangMo.to_state_reopen_hours}
            />
          )}

          {/* Lý do: bắt buộc khi cạnh đòi (`requires_note`); tùy chọn khi cạnh dẫn tới
              trạng thái kết thúc — ai đóng một hồ sơ cũng nên được để lại một dòng (#98) —
              hay khi cạnh đặt tên ô (#556: "Cách giải quyết" ở Hoàn thành xử lý, không bắt buộc).
              Tên ô lấy từ cạnh khi có (#79): khi hỏi thêm, ô này là câu hỏi chứ không
              phải lý do. */}
          {(dangMo.requires_note || dangMo.to_state_is_terminal || Boolean(dangMo.note_label)) && (
            <label style={{ display: "grid", gap: "6px" }}>
              <span style={KIEU_NHAN}>
                {dangMo.note_label ?? "Lý do"}
                {!dangMo.requires_note && (
                  <span style={{ fontWeight: 400, color: "var(--ink-3)" }}> — không bắt buộc</span>
                )}
              </span>
              <textarea
                name="note"
                className="o-nhap"
                rows={3}
                maxLength={2000}
                required={dangMo.requires_note}
                placeholder="Ghi vào dòng thời gian, người gửi và người xử lý đều đọc được."
              />
            </label>
          )}

          {!ngan && <div className="hang-xac-nhan">{nutXacNhan}</div>}
        </div>
      )}

      {ketQua.loi && (
        <p role="alert" className="thao-tac-loi">
          {ketQua.loi}
        </p>
      )}

      {/* Ngăn, đang mở thao tác (#561): xác nhận, hủy và các thao tác khác dính ở đáy ngăn */}
      {ngan && dangMo && (
        <div className="hang-nut-ngan hang-xac-nhan-ngan">
          {nutXacNhan}
          {menuThaoTac(dangMo, "Thao tác khác")}
        </div>
      )}
    </form>
  );
}
