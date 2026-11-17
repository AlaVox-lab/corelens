"use client";

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khối Webhook trên màn Hệ thống (#401): quản trị viên đăng ký, theo dõi và hủy webhook của nền tảng lõi
// (#390) mà không cần dòng lệnh. Danh sách và lần gửi do trang đọc ở máy chủ rồi truyền xuống; tạo và hủy
// đi qua hành động máy chủ — token không tới trình duyệt.
//
// Bí mật ký HMAC chỉ hiện ngay sau khi tạo, giữ trong trạng thái của khối: tải lại trang là mất, đúng như
// API chỉ trả nó một lần.

import { Copy, Plus, Trash2 } from "lucide-react";
import { useState, useTransition } from "react";

import { ngayGio } from "@/lib/dinh-dang";
import type { DangKyWebhook, LanGuiWebhook } from "@/lib/kieu";
import { bienHoMau } from "@/lib/trang-thai";

import { huyWebhook, taoWebhook } from "./thao-tac-webhook";

/** Trạng thái lần gửi → họ màu và nhãn. Ba giá trị là hợp đồng của API lõi, không phải nghiệp vụ. */
const NHAN_LAN_GUI: Record<LanGuiWebhook["status"], { ho: string; nhan: string }> = {
  delivered: { ho: "g", nhan: "Đã gửi" },
  pending: { ho: "a", nhan: "Chờ thử lại" },
  failed: { ho: "r", nhan: "Hỏng hẳn" },
};

/** Cùng múi giờ cố định với mọi màn khác — máy chủ và trình duyệt ra cùng một chuỗi. */
function gio(iso: string | null): string {
  return iso ? ngayGio(iso) : "—";
}

function DongLanGui({ lg }: { lg: LanGuiWebhook }) {
  const kieu = NHAN_LAN_GUI[lg.status] ?? { ho: "n", nhan: lg.status };
  const chiTiet =
    lg.status === "delivered"
      ? `${gio(lg.delivered_at)} · HTTP ${lg.last_status_code ?? "—"}`
      : lg.status === "pending" && lg.attempts > 0
        ? `lần ${lg.attempts}, thử lại ${gio(lg.next_attempt_at)} · ${lg.last_error ?? ""}`
        : lg.status === "pending"
          ? "chờ lượt gửi kế"
          : `${lg.attempts} lần · ${lg.last_error ?? ""}`;
  return (
    <li className="wh-lan-gui">
      <span className="mono">#{lg.event_id}</span>
      <span className="nhan-tt" style={{ ...bienHoMau(kieu.ho), fontSize: "12px" }}>
        {kieu.nhan}
      </span>
      <span className="wh-phu">{chiTiet}</span>
    </li>
  );
}

function TheDangKy({ dk, lanGui }: { dk: DangKyWebhook; lanGui: LanGuiWebhook[] | null }) {
  const [dangHuy, batDauHuy] = useTransition();
  const [loi, datLoi] = useState<string | null>(null);

  const huy = () => {
    if (!window.confirm(`Hủy đăng ký webhook gửi tới ${dk.url}? Các lần gửi đang chờ cũng bỏ theo.`)) return;
    datLoi(null);
    batDauHuy(async () => {
      const kq = await huyWebhook(dk.id);
      if (!kq.ok) datLoi(kq.thongDiep);
    });
  };

  const boLoc = [
    dk.activities?.length ? `hoạt động: ${dk.activities.join(", ")}` : "mọi hoạt động",
    dk.process ? `quy trình: ${dk.process}` : "mọi quy trình",
  ].join(" · ");

  return (
    <li className="wh-dang-ky">
      <div className="wh-dau-dong">
        <div className="wh-dia-chi">
          <span className="mono">{dk.url}</span>
          <span className="wh-phu">
            {dk.description ? `${dk.description} · ` : ""}
            {boLoc} · tạo {gio(dk.created_at)}
          </span>
        </div>
        <button type="button" className="nut" data-loai="nguy" onClick={huy} disabled={dangHuy}>
          <Trash2 aria-hidden />
          {dangHuy ? "Đang hủy…" : "Hủy"}
        </button>
      </div>
      {loi && (
        <p className="wh-loi" role="alert">
          {loi}
        </p>
      )}
      {lanGui === null ? (
        <p className="wh-phu">Không đọc được các lần gửi.</p>
      ) : lanGui.length === 0 ? (
        <p className="wh-phu">Chưa có sự kiện nào từ lúc đăng ký.</p>
      ) : (
        <ul className="wh-ds-lan-gui" aria-label="Các lần gửi gần nhất">
          {lanGui.map((lg) => (
            <DongLanGui key={lg.event_id} lg={lg} />
          ))}
        </ul>
      )}
    </li>
  );
}

function BieuMauDangKy() {
  const [dangGui, batDauGui] = useTransition();
  const [loi, datLoi] = useState<string | null>(null);
  const [biMat, datBiMat] = useState<{ url: string; secret: string } | null>(null);

  const gui = (duLieu: FormData) => {
    datLoi(null);
    datBiMat(null);
    batDauGui(async () => {
      const kq = await taoWebhook(
        String(duLieu.get("url") ?? ""),
        String(duLieu.get("mo-ta") ?? ""),
        String(duLieu.get("hoat-dong") ?? ""),
      );
      if (!kq.ok) {
        datLoi(kq.thongDiep);
        return;
      }
      datBiMat({ url: kq.dangKy.url, secret: kq.dangKy.secret });
    });
  };

  return (
    <>
      <form action={gui} className="wh-bieu-mau">
        <label className="o-truong wh-rong">
          <span className="o-truong-nhan">Địa chỉ nhận</span>
          <input
            type="url"
            name="url"
            required
            placeholder="https://ung-dung-khac.example/su-kien"
            className="o-nhap"
          />
        </label>
        <label className="o-truong">
          <span className="o-truong-nhan">Mô tả — không bắt buộc</span>
          <input type="text" name="mo-ta" maxLength={200} placeholder="Bot chat phòng CNTT" className="o-nhap" />
        </label>
        <label className="o-truong">
          <span className="o-truong-nhan">Chỉ các mã hoạt động — bỏ trống là tất cả</span>
          <input type="text" name="hoat-dong" placeholder="cancel, confirm-done" className="o-nhap" />
        </label>
        <div className="wh-rong">
          <button type="submit" className="nut" data-loai="chinh" disabled={dangGui}>
            <Plus aria-hidden />
            {dangGui ? "Đang đăng ký…" : "Đăng ký webhook"}
          </button>
        </div>
      </form>
      {loi && (
        <p className="wh-loi" role="alert">
          {loi}
        </p>
      )}
      {biMat && (
        <div className="wh-bi-mat" role="status">
          <p>
            Đã đăng ký <span className="mono">{biMat.url}</span>. Bí mật ký HMAC dưới đây{" "}
            <strong>chỉ hiện lần này</strong> — chép sang bên nhận để kiểm tiêu đề <span className="mono">X-DXOS-Signature</span>.
          </p>
          <div className="wh-bi-mat-dong">
            <code className="mono">{biMat.secret}</code>
            <button
              type="button"
              className="nut"
              onClick={() => navigator.clipboard?.writeText(biMat.secret)}
            >
              <Copy aria-hidden />
              Chép
            </button>
          </div>
        </div>
      )}
    </>
  );
}

export function QuanLyWebhook({
  dangKy,
  lanGui,
}: {
  /** `null` khi không đọc được danh sách — dịch vụ lỗi hay phiên hết hạn. */
  dangKy: DangKyWebhook[] | null;
  lanGui: Record<number, LanGuiWebhook[] | null>;
}) {
  return (
    <section className="the" aria-labelledby="quan-ly-webhook">
      <div className="khoi-dau">
        <h2 id="quan-ly-webhook">Webhook</h2>
      </div>
      <div className="xuat-nhat-ky-than">
        <p className="xuat-nhat-ky-giai-thich">
          Ứng dụng khác nhận sự kiện của nhật ký ngay khi hồ sơ chuyển bước: lõi gửi <span className="mono">POST</span>{" "}
          JSON tới địa chỉ đã đăng ký, ký HMAC-SHA256, tự thử lại khi bên nhận lỗi. Chỉ nhận sự kiện xảy ra sau lúc
          đăng ký.
        </p>
        {dangKy === null ? (
          <p className="wh-loi" role="alert">
            Không đọc được danh sách webhook. Tải lại trang sau ít phút.
          </p>
        ) : dangKy.length === 0 ? (
          <p className="wh-phu">Chưa có đăng ký nào.</p>
        ) : (
          <ul className="wh-ds-dang-ky">
            {dangKy.map((dk) => (
              <TheDangKy key={dk.id} dk={dk} lanGui={lanGui[dk.id] ?? null} />
            ))}
          </ul>
        )}
        <BieuMauDangKy />
      </div>
    </section>
  );
}
