// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Hộp thư chung (#155): mọi cuộc trò chuyện người này đang giữ, mỗi cuộc là lời nhắn của
// MỘT hồ sơ. Không phải kho tin nhắn thứ hai — đọc đúng lời nhắn trên hồ sơ (#128).
//
// Cột trái gom theo người gửi hồ sơ (nhân viên xem), hoặc một danh sách theo hồ sơ (người
// chỉ gửi yêu cầu). Cột phải mở cuộc đang chọn qua ĐÚNG cửa dịch vụ trả về cho hồ sơ đó —
// cổng người gửi, buồng lái phòng ban hay điều phối — và gửi lời nhắn bằng thao tác của
// chính cửa đó, nên mọi luật của #128 chỉ có một nơi.
//
// Từ #156 một hồ sơ có thể có hai cuộc: với người gửi, và nội bộ giữa nhân viên. Cuộc nội
// bộ vào nhóm "Nội bộ nhân viên" có ổ khóa; đầu khung chat có nút chuyển giữa hai cuộc của
// cùng hồ sơ, mở được cả khi cuộc kia chưa có tin nào.

import { ArrowLeft, ArrowRight, EyeOff, Lock, MessagesSquare } from "lucide-react";
import Link from "next/link";
import { redirect } from "next/navigation";

import { guiLoiNhanDieuPhoi } from "@/app/dieu-phoi/thao-tac";
import { guiLoiNhanPhongBan } from "@/app/phong-ban/thao-tac";
import { guiLoiNhan } from "@/app/yeu-cau/thao-tac";
import { ChanTrang } from "@/components/chan-trang";
import { DanhDauDaDoc } from "@/components/danh-dau-da-doc";
import { DanhSachHopThu, type MucCuoc, type NhomCuoc } from "@/components/danh-sach-hop-thu";
import { KhungChat } from "@/components/khung-chat";
import { ManRong } from "@/components/man-rong";
import { KhungLoiNhan } from "@/components/khung-loi-nhan";
import { NutThanhDau } from "@/components/khung-ung-dung";
import { NhanTrangThai } from "@/components/nhan-trang-thai";
import { TuLamMoi } from "@/components/tu-lam-moi";
import { docDichVu, goiDichVu } from "@/lib/api";
import { chiGio, khoaNgay } from "@/lib/dinh-dang";
import { duongCuoc, KENH_NOI_BO, LOC_CHUA_DOC, LOC_NOI_BO } from "@/lib/hop-thu";
import type { CuaMoHoSo, CuocTroChuyen, HoSoChiTiet, HopThu } from "@/lib/kieu";
import { chuCaiDau, mauTheo } from "@/lib/nguoi";
import { docDongHo } from "@/lib/sla";
import { docThamSo, duongTrang, quaTrangCuoi, soTrang, truyVan, type ThamSo } from "@/lib/trang";

export const dynamic = "force-dynamic";

/** Mỗi cửa: đọc chi tiết ở đâu, gửi lời nhắn bằng thao tác nào, trang hồ sơ nằm đâu. */
const CUA: Record<
  CuaMoHoSo,
  { chiTiet: string; trang: string; gui: typeof guiLoiNhan }
> = {
  portal: { chiTiet: "/requests", trang: "/yeu-cau", gui: guiLoiNhan },
  department: { chiTiet: "/department/requests", trang: "/phong-ban", gui: guiLoiNhanPhongBan },
  coordination: { chiTiet: "/coordination/requests", trang: "/dieu-phoi", gui: guiLoiNhanDieuPhoi },
};

/** Giờ ở danh sách: "11:02" hôm nay, "Hôm qua", hoặc ngày tháng. */
function lucNgan(iso: string, bayGio: Date): string {
  if (khoaNgay(iso) === khoaNgay(bayGio.toISOString())) return chiGio(iso);
  const homQua = new Date(bayGio.getTime() - 86_400_000);
  if (khoaNgay(iso) === khoaNgay(homQua.toISOString())) return "Hôm qua";
  const d = new Date(iso);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function thanhMuc(c: CuocTroChuyen, bayGio: Date): MucCuoc {
  const tin = c.last_message;
  const noiDung = tin.body ?? tin.kind_label;
  // Nhân viên xem cuộc với người gửi: tin của người gửi khỏi ghi tên — nhóm đã mang tên đó
  const bo = c.workspace !== "portal" && !c.internal && tin.from_requester;
  return {
    maHoSo: c.case_id,
    noiBo: c.internal,
    tieuDe: c.title,
    ma: c.code,
    xemTruoc: tin.mine ? `Bạn: ${noiDung}` : bo ? noiDung : `${tin.author_label}: ${noiDung}`,
    luc: lucNgan(tin.created_at, bayGio),
    chuaDoc: c.unread,
    choBan: c.waiting_on_me,
  };
}

/** Gom theo người gửi hồ sơ; hồ sơ của chính mình và các cuộc nội bộ vào nhóm riêng. */
function gomNhom(cacCuoc: CuocTroChuyen[], bayGio: Date): NhomCuoc[] {
  const chiCuaMinh = cacCuoc.every((c) => c.workspace === "portal");
  const nhom = new Map<string, NhomCuoc>();
  for (const c of cacCuoc) {
    if (c.internal) {
      if (!nhom.has(KENH_NOI_BO)) {
        nhom.set(KENH_NOI_BO, { ma: KENH_NOI_BO, ten: "Nội bộ nhân viên", noiBo: true, cuoc: [] });
      }
      nhom.get(KENH_NOI_BO)!.cuoc.push(thanhMuc(c, bayGio));
      continue;
    }
    const cuaMinh = c.workspace === "portal";
    const ma = cuaMinh ? "cua-toi" : c.requester_id;
    if (!nhom.has(ma)) {
      const ten = c.requester_label ?? "Không rõ người gửi";
      nhom.set(ma, {
        ma,
        ten: chiCuaMinh ? null : cuaMinh ? "Hồ sơ bạn gửi" : ten,
        anh: cuaMinh ? undefined : { chuCai: chuCaiDau(ten), mau: mauTheo(c.requester_id) },
        cuoc: [],
      });
    }
    nhom.get(ma)!.cuoc.push(thanhMuc(c, bayGio));
  }
  // Dịch vụ đã xếp cuộc mới nhất lên đầu, nên Map giữ thứ tự nhóm theo tin mới nhất
  return [...nhom.values()];
}

/**
 * Cuộc đang mở theo địa chỉ trang. Cuộc chưa có tin nào thì chưa có trong hộp thư, nhưng
 * nút chuyển vẫn mở được nó khi cuộc kia của cùng hồ sơ đã có — để bắt đầu nhắn nội bộ
 * ngay từ hộp thư. Người gửi của hồ sơ không bao giờ mở được cuộc nội bộ; dịch vụ gác lại
 * lần nữa khi đọc chi tiết.
 */
function chonCuoc(cacCuoc: CuocTroChuyen[], hoSo: string, noiBo: boolean): CuocTroChuyen | null {
  const dung = cacCuoc.find((c) => String(c.case_id) === hoSo && c.internal === noiBo);
  if (dung) return dung;
  const cungHoSo = cacCuoc.find((c) => String(c.case_id) === hoSo);
  if (!cungHoSo || (noiBo && cungHoSo.workspace === "portal")) return null;
  return { ...cungHoSo, internal: noiBo, unread: 0, waiting_on_me: false };
}

function Rong({ tieuDe, cau }: { tieuDe: string; cau: string }) {
  return (
    <div style={{ alignSelf: "center" }}>
      <ManRong icon={MessagesSquare} tieuDe={tieuDe} cau={cau} />
    </div>
  );
}

async function CuocDangMo({ cuoc, bayGio }: { cuoc: CuocTroChuyen; bayGio: Date }) {
  const cua = CUA[cuoc.workspace];
  const ketQua = await docDichVu<HoSoChiTiet>(`${cua.chiTiet}/${cuoc.case_id}`);
  if (!ketQua.ok) {
    return <Rong tieuDe="Không mở được cuộc trò chuyện" cau={ketQua.thongDiep} />;
  }
  const ho_so = ketQua.duLieu;
  const noiBo = cuoc.internal;
  if (noiBo && !ho_so.sees_internal) {
    return <Rong tieuDe="Không mở được cuộc trò chuyện này" cau="Bạn không đọc được cuộc nội bộ của hồ sơ này." />;
  }
  // Chỉ lời nhắn và loại lời nhắn của đúng cuộc đang mở
  const cacTin = ho_so.messages.filter((m) => m.internal === noiBo);
  const cacLoai = ho_so.message_kinds.filter((k) => k.internal === noiBo);
  const laNguoiGui = cuoc.workspace === "portal";
  const ten = noiBo
    ? `Nội bộ · ${[...new Set(cacTin.map((m) => m.author_label))].join(", ") || "nhân viên"}`
    : laNguoiGui
      ? "Các bên xử lý hồ sơ"
      : (cuoc.requester_label ?? "Người gửi");
  const dongHo = docDongHo(ho_so, laNguoiGui ? "nguoi-gui" : "noi-bo");

  return (
    <>
      <div className="ht-dau">
        <Link className="nut-icon nut-lui" href="/hop-thu" aria-label="Quay lại danh sách">
          <ArrowLeft aria-hidden />
        </Link>
        {noiBo ? (
          <span className="icon-o" data-noi-bo="" aria-hidden>
            <Lock />
          </span>
        ) : laNguoiGui ? (
          <span className="icon-o" aria-hidden>
            <MessagesSquare />
          </span>
        ) : (
          <span className="av" data-c={mauTheo(cuoc.requester_id)} aria-hidden>
            {chuCaiDau(ten)}
          </span>
        )}
        <div className="than">
          <b>{ten}</b>
          <span className="phu" style={noiBo ? { flexWrap: "nowrap", gap: "6px" } : undefined}>
            {noiBo ? (
              <>
                <EyeOff aria-hidden style={{ width: "13px", height: "13px", flex: "none" }} />
                <span>Người gửi không thấy cuộc trò chuyện này</span>
              </>
            ) : laNguoiGui ? (
              "Điều phối và phòng ban đang giữ hồ sơ trả lời ở đây"
            ) : (
              "Người gửi"
            )}
          </span>
        </div>
        {ho_so.sees_internal && (
          <nav className="seg" aria-label="Cuộc trò chuyện của hồ sơ">
            <Link href={duongCuoc(ho_so.id, false)} scroll={false} aria-current={noiBo ? undefined : "page"}>
              Với người gửi
            </Link>
            <Link href={duongCuoc(ho_so.id, true)} scroll={false} aria-current={noiBo ? "page" : undefined}>
              <Lock aria-hidden />
              Nội bộ
            </Link>
          </nav>
        )}
      </div>

      <div className="the-hs">
        <NhanTrangThai ma={ho_so.state.code} nhan={ho_so.state.label} />
        <div className="than">
          <b title={ho_so.title}>{ho_so.title}</b>
          <small>
            <span className="mono">{ho_so.code}</span>· Hạn:{" "}
            <span className="chu-han" data-muc={dongHo.canhBao ? "qua" : undefined}>
              {dongHo.cau}
            </span>
          </small>
        </div>
        <Link className="nut nut-nho" href={`${cua.trang}/${ho_so.id}`}>
          Mở hồ sơ
          <ArrowRight aria-hidden />
        </Link>
      </div>

      <KhungChat
        cacLoiNhan={cacTin}
        bayGio={bayGio}
        noiBo={noiBo}
        soan={
          <KhungLoiNhan
            // Khóa theo cuộc, không theo số lời nhắn: tin mới tới trong lúc đang gõ thì ô
            // soạn không bị dựng lại, chữ gõ dở không mất
            key={`${ho_so.id}-${noiBo}`}
            maHoSo={ho_so.id}
            cacLoai={cacLoai}
            daKetThuc={ho_so.state.is_terminal}
            hanhDong={cua.gui}
            kieu="chat"
            noiBo={noiBo}
            goiY={
              noiBo
                ? "Nhắn nội bộ — người gửi không thấy"
                : laNguoiGui
                  ? "Nhắn cho bên xử lý"
                  : `Nhắn cho ${ten}`
            }
          />
        }
      />
      <DanhDauDaDoc maHoSo={ho_so.id} soTin={cacTin.length} noiBo={noiBo} />
      <TuLamMoi key={`${ho_so.id}-${noiBo}`} soTin={cacTin.length} />
    </>
  );
}

export default async function TrangHopThu({ searchParams }: { searchParams: Promise<ThamSo> }) {
  const sp = await searchParams;
  const hoSo = docThamSo(sp, "ho-so");
  const kenh = docThamSo(sp, "kenh");
  const loc = docThamSo(sp, "loc");
  const trang = soTrang(sp);
  const coLoc = Boolean(docThamSo(sp, "q") || loc);
  const hopThu = await goiDichVu<HopThu>(
    `/inbox?${truyVan(trang, {
      q: docThamSo(sp, "q"),
      unread: loc === LOC_CHUA_DOC,
      internal: loc === LOC_NOI_BO,
    })}`,
  );
  const bayGio = new Date();
  const tieuDe = <h1 className="an-di">Hộp thư</h1>;

  if (hopThu === null) {
    return (
      <>
        {tieuDe}
        <div className="the" style={{ margin: "24px" }}>
          <div className="rong" data-loi="">
            <h2>Không tải được hộp thư</h2>
            <p>Hệ thống không phản hồi. Lời nhắn đã gửi vẫn còn nguyên trên hồ sơ.</p>
            <Link href="/hop-thu" className="nut nut-nho">
              Thử lại
            </Link>
          </div>
        </div>
      </>
    );
  }

  const cuoi = quaTrangCuoi("/hop-thu", sp, hopThu);
  if (cuoi) redirect(cuoi);

  if (hopThu.items.length === 0 && !coLoc) {
    return (
      <>
        {tieuDe}
        <div className="hop-thu" style={{ gridTemplateColumns: "minmax(0, 1fr)" }}>
          <Rong
            tieuDe="Chưa có cuộc trò chuyện nào"
            cau="Lời nhắn trên hồ sơ bạn đang giữ sẽ hiện ở đây. Mở một hồ sơ để nhắn cho các bên."
          />
          <TuLamMoi soTin={0} />
        </div>
      </>
    );
  }

  // Có `?ho-so=` thì mở đúng cuộc đó — cuộc không nằm ở trang đang xem (mở từ trang hồ sơ,
  // hay đã sang trang khác) thì hỏi riêng các cuộc của hồ sơ đó. Không có thì mở cuộc mới
  // nhất (trên màn rộng).
  let cacCuocCuaHoSo = hopThu.items;
  if (hoSo && /^\d+$/.test(hoSo) && !hopThu.items.some((c) => String(c.case_id) === hoSo)) {
    cacCuocCuaHoSo = (await goiDichVu<HopThu>(`/inbox?case_id=${hoSo}`))?.items ?? [];
  }
  const chon = hoSo ? chonCuoc(cacCuocCuaHoSo, hoSo, kenh === KENH_NOI_BO) : (hopThu.items[0] ?? null);

  return (
    <>
      {tieuDe}
      {hopThu.unread > 0 && (
        <NutThanhDau>
          <span className="nhat" style={{ fontSize: "12.5px" }}>
            {hopThu.unread} chưa đọc
          </span>
        </NutThanhDau>
      )}
      <div className="hop-thu" data-dang-xem={hoSo ? "chat" : "ds"}>
        <DanhSachHopThu
          nhom={gomNhom(hopThu.items, bayGio)}
          chon={chon ? { maHoSo: chon.case_id, noiBo: chon.internal } : null}
          soChuaDoc={hopThu.unread_conversations}
          soNoiBo={hopThu.internal_conversations}
          chan={
            <ChanTrang
              tong={hopThu.total}
              tu={hopThu.offset}
              soDong={hopThu.limit}
              donVi="cuộc"
              truoc={trang > 1 ? duongTrang("/hop-thu", sp, trang - 1) : null}
              sau={hopThu.offset + hopThu.limit < hopThu.total ? duongTrang("/hop-thu", sp, trang + 1) : null}
            />
          }
        />
        <section className="ht-chat" aria-label="Cuộc trò chuyện">
          {chon ? (
            <CuocDangMo cuoc={chon} bayGio={bayGio} />
          ) : !hoSo ? (
            // Bộ lọc không còn cuộc nào: chưa có gì để mở
            <Rong tieuDe="Không có cuộc trò chuyện nào khớp" cau="Đổi ô tìm hay bỏ bộ lọc để xem các cuộc khác." />
          ) : (
            <>
              <Rong
                tieuDe="Không mở được cuộc trò chuyện này"
                cau="Hồ sơ không còn trong hộp thư của bạn, hoặc chưa có lời nhắn nào."
              />
              <TuLamMoi soTin={0} />
            </>
          )}
        </section>
      </div>
    </>
  );
}
