// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Thẻ liên hệ người gửi trên trang chi tiết của hai buồng lái (#131, bố cục #169): tên,
// email, số điện thoại. Bấm email mở ứng dụng thư; bấm số trên điện thoại thì gọi được.
//
// Bốn trường hợp phải nói khác nhau, không gộp làm một: có liên hệ, chưa điền số, tài
// khoản không còn, và danh bạ không trả lời. Ba trường hợp sau đều "không có số", nhưng
// người đọc cần biết nên làm gì tiếp — nhắn trên hồ sơ, hay thử lại sau.
//
// Thành phần chạy phía máy chủ, không có trạng thái: trang tra danh bạ rồi truyền kết quả
// xuống. Danh bạ hỏng thì chỉ chỗ này báo lỗi, phần còn lại của trang vẫn mở.

import type { KetQua } from "@/lib/api";
import type { LienHeNguoiGui as LienHe } from "@/lib/kieu";
import { chuCaiDau, mauTheo } from "@/lib/nguoi";

/** Số để quay: bỏ dấu cách, dấu chấm, ngoặc — `tel:` chỉ cần chữ số và dấu cộng. */
function soDeGoi(so: string): string {
  return so.replace(/[^\d+]/g, "");
}

function DongLoi({ cau }: { cau: string }) {
  return (
    <div>
      <dt>Liên hệ</dt>
      <dd>{cau}</dd>
    </div>
  );
}

export function TheLienHe({
  ten,
  dinhDanh,
  ketQua,
}: {
  /** Tên người gửi ghi trên hồ sơ. */
  ten: string;
  /** Định danh người gửi, để ô chữ cái cùng màu ở mọi chỗ. */
  dinhDanh: string;
  ketQua: KetQua<LienHe>;
}) {
  return (
    <div className="the khoi">
      <div className="khoi-dau">Liên hệ người gửi</div>
      <dl className="ds-mt">
        <div>
          <dt>Người gửi</dt>
          <dd>
            <span className="av av-nho" data-c={mauTheo(dinhDanh)} aria-hidden>
              {chuCaiDau(ten)}
            </span>
            <b style={{ fontWeight: 600 }}>{ten}</b>
          </dd>
        </div>

        {!ketQua.ok ? (
          <DongLoi
            cau={
              ketQua.ma === "directory-unavailable"
                ? "Không tra được liên hệ: danh bạ không trả lời. Thử tải lại trang sau ít phút."
                : "Không tra được liên hệ của người gửi."
            }
          />
        ) : !ketQua.duLieu.found ? (
          <DongLoi cau="Tài khoản không còn trong danh bạ. Nhắn qua thẻ Trao đổi trên hồ sơ." />
        ) : (
          <>
            <div>
              <dt>Email</dt>
              <dd>
                {ketQua.duLieu.email ? (
                  <a href={`mailto:${ketQua.duLieu.email}`}>{ketQua.duLieu.email}</a>
                ) : (
                  "Chưa có email"
                )}
              </dd>
            </div>
            <div>
              <dt>Điện thoại</dt>
              <dd>
                {ketQua.duLieu.phone ? (
                  <a href={`tel:${soDeGoi(ketQua.duLieu.phone)}`} className="mono">
                    {ketQua.duLieu.phone}
                  </a>
                ) : (
                  "Chưa có số điện thoại"
                )}
              </dd>
            </div>
          </>
        )}
      </dl>
    </div>
  );
}
