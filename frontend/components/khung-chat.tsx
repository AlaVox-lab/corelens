// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Lời nhắn trên hồ sơ dưới dạng hội thoại (#169) — thẻ "Trao đổi" của trang hồ sơ phía
// nhân viên. Cùng dữ liệu `messages` mà dòng thời gian từng trộn vào (#128); lời nhắn
// vẫn không đổi trạng thái, không dừng đồng hồ (ADR-0005).
//
// Phía phải là "phía mình" như mọi ứng dụng chat: nhân viên xem thì nhân viên bên phải,
// người gửi bên trái; người gửi xem trong hộp thư (#155) thì ngược lại. Trên mỗi bong bóng
// ghi tên người viết, vì nhiều người cùng giữ một hồ sơ: điều phối, trưởng phòng, người
// xử lý. Lời nhắn không có nội dung (như "Hỏi tiến độ") hiện thành một dòng sự kiện ở
// giữa, không thành bong bóng rỗng.
//
// Cuộc nội bộ (#156) toàn nhân viên, nên phía phải là tin của CHÍNH người đang xem; nền vàng
// nhạt viền đứt (CSS `.chat[data-noi-bo]`) để không lẫn với cuộc có người gửi đọc.

import { CircleHelp } from "lucide-react";

import { chiGio, khoaNgay, nhanNgay } from "@/lib/dinh-dang";
import type { LoiNhan } from "@/lib/kieu";
import { chuCaiDau, mauTheo } from "@/lib/nguoi";

export function KhungChat({
  cacLoiNhan,
  bayGio,
  soan,
  phiaMinh = "nhan-vien",
  noiBo = false,
}: {
  cacLoiNhan: LoiNhan[];
  bayGio: Date;
  /** Người đang xem đứng phía nào — phía đó nằm bên phải. */
  phiaMinh?: "nhan-vien" | "nguoi-gui";
  /** Ô soạn đặt dưới khung — thành phần phía trình duyệt của nơi đang dùng. */
  soan: React.ReactNode;
  /** Cuộc nội bộ giữa nhân viên (#156). */
  noiBo?: boolean;
}) {
  // Cũ trên, mới dưới như mọi khung chat. `sort` ổn định: cùng mốc giờ giữ thứ tự dịch vụ trả
  const theoGio = [...cacLoiNhan].sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at));

  return (
    <div className="chat" data-noi-bo={noiBo ? "" : undefined}>
      <div className="chat-cuon" data-cuon>
        {theoGio.length === 0 ? (
          <span className="su-kien-chat">
            {noiBo
              ? "Chưa có tin nội bộ nào. Người gửi hồ sơ không thấy cuộc này."
              : "Chưa có lời nhắn nào trên hồ sơ này."}
          </span>
        ) : (
          theoGio.map((m, i) => {
            const ngayMoi = i === 0 || khoaNgay(m.created_at) !== khoaNgay(theoGio[i - 1].created_at);
            const benPhai = noiBo ? m.mine : m.from_requester === (phiaMinh === "nguoi-gui");
            return (
              <div key={m.id} style={{ display: "contents" }}>
                {ngayMoi && <span className="ngay">{nhanNgay(m.created_at, bayGio)}</span>}
                {m.body === null ? (
                  <span className="su-kien-chat">
                    <CircleHelp aria-hidden />
                    {m.author_label} · {m.kind_label} · {chiGio(m.created_at)}
                  </span>
                ) : (
                  <div className="bong-hang" data-minh={benPhai ? "" : undefined}>
                    {!benPhai && (
                      <span className="av av-nho" data-c={mauTheo(m.author)} aria-hidden>
                        {chuCaiDau(m.author_label)}
                      </span>
                    )}
                    <div>
                      <div className="bong-tg" style={{ margin: "0 0 2px" }}>
                        {m.author_label}
                        {m.from_requester ? " · Người gửi hồ sơ" : ""}
                      </div>
                      <div className="bong">{m.body}</div>
                      <div className="bong-tg">{chiGio(m.created_at)}</div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
      {soan}
    </div>
  );
}
