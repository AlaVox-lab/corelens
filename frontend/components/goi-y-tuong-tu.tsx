"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Hồ sơ đã giải quyết tương tự, ngay dưới ô mô tả của biểu mẫu Gửi yêu cầu (#319).
//
// BA LỜI HỨA VỚI NGƯỜI GỬI
//
// 1. Không chậm thêm. Hỏi sau khi người gửi ngừng gõ một lúc, hủy lời hỏi cũ khi họ gõ tiếp, và tự bỏ
//    sau hạn chót ngắn. Nút Tiếp tục, Gửi yêu cầu không bao giờ chờ khối này.
// 2. Không báo lỗi. Mô hình tắt, chậm, hỏng — khối đơn giản là không hiện. Dịch vụ báo mô hình nhúng
//    tắt thì thôi hỏi trong phiên này.
// 3. Không lộ ai. Dịch vụ đã ẩn tên người và thông tin liên hệ; khối không hiện mã hồ sơ, không dẫn
//    tới hồ sơ của người khác.
//
// Người gửi vẫn gửi bình thường. Nếu cách giải quyết cũ đủ dùng, họ bấm "không gửi nữa" — một yêu cầu
// được ngăn chặn, ghi lại để đo trên bảng điều khiển.

import { Lightbulb } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import type { HoSoTuongTu, KetQuaTuongTu } from "@/lib/kieu";

/** Chờ người gửi ngừng gõ chừng này mili giây rồi mới hỏi. */
const CHO_NGUNG_GO_MS = 700;
/** Hạn chót phía trình duyệt — dịch vụ có hạn riêng ngắn hơn. Quá hạn thì không hiện gì. */
const HAN_CHOT_MS = 4000;
/** Ngắn hơn chừng này thì chưa đủ nghĩa để tìm. */
const TOI_THIEU_KY_TU = 12;

export function GoiYTuongTu({ tieuDe, moTa, phien }: { tieuDe: string; moTa: string; phien: string }) {
  const chuyenTrang = useRouter();
  const [cacHoSo, datCacHoSo] = useState<HoSoTuongTu[]>([]);
  const [dangBo, datDangBo] = useState(false);
  const tat = useRef(false);

  useEffect(() => {
    const noiDung = `${tieuDe} ${moTa}`.trim();
    if (tat.current || noiDung.length < TOI_THIEU_KY_TU) {
      datCacHoSo([]);
      return;
    }
    const huy = new AbortController();
    const hen = setTimeout(async () => {
      try {
        const ph = await fetch("/api/yeu-cau/tuong-tu", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: tieuDe, description: moTa, session_id: phien }),
          signal: AbortSignal.any([huy.signal, AbortSignal.timeout(HAN_CHOT_MS)]),
        });
        if (!ph.ok) return;
        const kq = (await ph.json()) as KetQuaTuongTu;
        if (!kq.enabled) tat.current = true;
        datCacHoSo(kq.items ?? []);
      } catch {
        // Hủy vì gõ tiếp, quá hạn, mất mạng: giữ nguyên, không báo gì
      }
    }, CHO_NGUNG_GO_MS);
    return () => {
      clearTimeout(hen);
      huy.abort();
    };
  }, [tieuDe, moTa, phien]);

  if (cacHoSo.length === 0) return null;

  async function boKhongGui() {
    datDangBo(true);
    try {
      await fetch("/api/yeu-cau/tuong-tu/bo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: phien }),
        signal: AbortSignal.timeout(HAN_CHOT_MS),
      });
    } catch {
      // Ghi hỏng thì bộ quét tính phiên này là bỏ không gửi khi quá hạn chờ
    }
    chuyenTrang.push("/yeu-cau");
  }

  return (
    <section className="goi-y-tuong-tu" aria-labelledby="goi-y-tuong-tu-dau" data-testid="goi-y-tuong-tu">
      <p id="goi-y-tuong-tu-dau" className="the-goi-y-dau">
        <Lightbulb aria-hidden />
        <span>
          <strong>Có thể đã có cách giải quyết</strong> — {cacHoSo.length} hồ sơ tương tự đã được giải
          quyết
        </span>
      </p>
      <ul>
        {cacHoSo.map((h, i) => (
          <li key={i}>
            <p className="goi-y-tuong-tu-tieu-de">
              {h.title}
              {h.request_type && <span className="nhat"> · {h.request_type}</span>}
            </p>
            {h.resolution ? (
              <p>
                <span className="nhat">Cách đã giải quyết: </span>
                {h.resolution}
              </p>
            ) : (
              <p className="nhat">Hồ sơ không ghi lại cách giải quyết.</p>
            )}
          </li>
        ))}
      </ul>
      <p className="the-goi-y-nguon">
        Gợi ý của hệ thống từ hồ sơ đã đóng, đã ẩn tên người và thông tin liên hệ. Bạn vẫn gửi yêu cầu
        bình thường nếu chưa giải quyết được.
      </p>
      <div>
        <button type="button" className="nut nut-nho" onClick={boKhongGui} disabled={dangBo}>
          {dangBo ? "Đang ghi nhận…" : "Đã giải quyết được, không gửi nữa"}
        </button>
      </div>
    </section>
  );
}
