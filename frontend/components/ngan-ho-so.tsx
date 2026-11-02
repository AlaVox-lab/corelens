// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Nội dung ngăn xem nhanh của hàng đợi (#233), dựng ở máy chủ từ đúng các khối của trang chi
// tiết — đầu hồ sơ, hạn, nội dung, dòng thời gian (mặc định thu gọn về bước hiện tại), liên hệ
// người gửi. Trao đổi và tệp đính kèm ở lại trang đầy đủ. Khối thao tác do trang truyền vào, vì
// mỗi buồng lái gửi qua cửa riêng của nó.

import { DongThoiGian } from "@/components/dong-thoi-gian";
import { KhungNgan, type DieuHuongNgan } from "@/components/khung-ngan";
import { TheLienHe } from "@/components/lien-he-nguoi-gui";
import { DauHoSo, TheHan, TheNoiDung, type MucMeta } from "@/components/trang-ho-so";
import type { KetQua } from "@/lib/api";
import type { HoSoChiTiet, LienHeNguoiGui } from "@/lib/kieu";

const ID_TIEU_DE = "ngan-tieu-de";

export function NganHoSo({
  ho_so,
  meta,
  lienHe,
  thaoTac,
  dieuHuong,
}: {
  ho_so: HoSoChiTiet & { requester_label: string | null; requester_id: string };
  meta: MucMeta[];
  lienHe: KetQua<LienHeNguoiGui>;
  thaoTac: React.ReactNode;
  dieuHuong: DieuHuongNgan;
}) {
  return (
    <KhungNgan maHoSo={ho_so.id} idTieuDe={ID_TIEU_DE} dieuHuong={dieuHuong} chan={thaoTac}>
      <DauHoSo ho_so={ho_so} meta={meta} trongNgan={{ idTieuDe: ID_TIEU_DE }} />
      <TheHan ho_so={ho_so} />
      <TheNoiDung ho_so={ho_so} />
      <div className="the khoi">
        <div className="khoi-dau">Dòng thời gian</div>
        <DongThoiGian
          cacSuKien={ho_so.history}
          bayGio={new Date()}
          khiTrong="Hồ sơ chưa đổi trạng thái lần nào."
          trongThe
        />
      </div>
      <TheLienHe ten={ho_so.requester_label ?? "Không rõ người gửi"} dinhDanh={ho_so.requester_id} ketQua={lienHe} />
    </KhungNgan>
  );
}

/** Ngăn khi không mở được hồ sơ — đã rời phạm vi của người xem, hay dịch vụ không phản hồi. */
export function NganLoi({ cau, dieuHuong, maHoSo }: { cau: string; dieuHuong: DieuHuongNgan; maHoSo: number }) {
  return (
    <KhungNgan maHoSo={maHoSo} idTieuDe={ID_TIEU_DE} dieuHuong={dieuHuong}>
      <div className="rong" data-loi="">
        <h2 id={ID_TIEU_DE} tabIndex={-1}>
          Không mở được hồ sơ này
        </h2>
        <p>{cau}</p>
      </div>
    </KhungNgan>
  );
}
