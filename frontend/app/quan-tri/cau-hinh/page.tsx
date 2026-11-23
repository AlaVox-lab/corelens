// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn quản trị cấu hình quy trình (#255), chỉ quản trị viên (không gian `system` của `/me`).
//
// Xem: luồng xử lý của bộ quy tắc đang chạy (trạng thái và cạnh, vai trò, ràng buộc), lịch làm việc,
// nhật ký các lần sửa. Sửa: loại yêu cầu, mức ưu tiên, phòng ban — áp ngay cho mọi hồ sơ, không dựng
// lại cụm. Mọi tên, giá trị và nhãn trường đến từ `GET /admin/config`; trang không giữ bản sao nào của
// cấu hình. Đồ thị quy trình chỉ đổi bằng bộ quy tắc phiên bản mới (docs/ARCHITECTURE.md mục 5.4).

import { KhungLamViec } from "@/components/khung-lam-viec";
import { goiDichVu } from "@/lib/api";
import { ngayGio } from "@/lib/dinh-dang";
import type { CauHinhQuanTri } from "@/lib/kieu";

import { DongDanhMuc, type TruongO } from "./dong-danh-muc";

export const dynamic = "force-dynamic";

const THU = ["", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ nhật"];

function nhanTruong(cauHinh: CauHinhQuanTri, danhMuc: string, ten: string): string {
  return cauHinh.fields[danhMuc]?.[ten]?.label ?? ten;
}

function hienGiaTri(gt: unknown): string {
  if (gt === null || gt === undefined || gt === "") return "(trống)";
  if (typeof gt === "boolean") return gt ? "Có" : "Không";
  return String(gt);
}

function Muc({ tieuDe, moTa, children }: Readonly<{ tieuDe: string; moTa?: string; children: React.ReactNode }>) {
  // Bảng rộng cuộn ngang trong thẻ trên màn hẹp: thẻ nhận tiêu điểm bàn phím để cuộn bằng phím mũi tên,
  // và mang tên của mục cho trình đọc màn hình (#435)
  return (
    <section
      className="the"
      style={{ marginTop: "20px", padding: "16px 20px", overflowX: "auto" }}
      aria-label={tieuDe}
      tabIndex={0}
    >
      <h2 style={{ fontSize: "16px", margin: "0 0 4px" }}>{tieuDe}</h2>
      {moTa ? (
        <p className="nhat" style={{ fontSize: "13px", margin: "0 0 12px" }}>
          {moTa}
        </p>
      ) : null}
      {children}
    </section>
  );
}

export default async function ManCauHinh() {
  const cauHinh = await goiDichVu<CauHinhQuanTri>("/admin/config");

  return (
    <KhungLamViec canKhongGian="system">
      <h1 className="tieu-de-trang">Cấu hình quy trình</h1>
      {cauHinh === null ? (
        <p className="cau-chao">Chưa đọc được cấu hình. Thử tải lại trang sau ít phút.</p>
      ) : (
        <NoiDung cauHinh={cauHinh} />
      )}
    </KhungLamViec>
  );
}

function NoiDung({ cauHinh }: Readonly<{ cauHinh: CauHinhQuanTri }>) {
  const phongDangDung = cauHinh.departments
    .filter((p) => p.is_active)
    .map((p) => ({ code: p.code, label: p.label }));
  const tenPhong = Object.fromEntries(cauHinh.departments.map((p) => [p.code, p.label]));
  const canhTheoNguon = new Map<string, CauHinhQuanTri["transitions"]>();
  for (const t of cauHinh.transitions) {
    canhTheoNguon.set(t.from_state, [...(canhTheoNguon.get(t.from_state) ?? []), t]);
  }
  const f = (danhMuc: string, ten: string) => nhanTruong(cauHinh, danhMuc, ten);

  return (
    <>
      <p className="cau-chao">
        Bộ quy tắc đang chạy: <b>{cauHinh.rule_set.label}</b> (phiên bản {cauHinh.rule_set.version}, hiệu lực từ{" "}
        {ngayGio(cauHinh.rule_set.effective_from)}). Sửa ở đây áp ngay cho mọi hồ sơ, kể cả hồ sơ đang mở; mỗi lần
        sửa được kiểm tra trước khi lưu và ghi vào nhật ký bên dưới.
      </p>

      <Muc tieuDe="Loại yêu cầu" moTa="Hạn tính bằng giờ làm việc theo lịch bên dưới. Hạn của hồ sơ = hạn chuẩn × hệ số của mức ưu tiên.">
        <table className="bang bang-cau-hinh">
          <thead>
            <tr>
              <th>{f("request-types", "label")}</th>
              <th>{f("request-types", "sla_hours")}</th>
              <th>{f("request-types", "sla_grace_hours")}</th>
              <th>{f("request-types", "sla_warn_percent")}</th>
              <th>{f("request-types", "default_department")}</th>
              <th>{f("request-types", "is_active")}</th>
              <th>Hồ sơ đang mở</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {cauHinh.request_types.map((l) => {
              const truong: TruongO[] = [
                { ten: "label", nhan: f("request-types", "label"), giaTri: l.label, kieu: "chu" },
                { ten: "description", nhan: f("request-types", "description"), giaTri: l.description, kieu: "chu" },
                { ten: "sla_hours", nhan: f("request-types", "sla_hours"), giaTri: l.sla_hours, kieu: "so", toiThieu: 1 },
                { ten: "sla_grace_hours", nhan: f("request-types", "sla_grace_hours"), giaTri: l.sla_grace_hours, kieu: "so", toiThieu: 0 },
                { ten: "sla_warn_percent", nhan: f("request-types", "sla_warn_percent"), giaTri: l.sla_warn_percent, kieu: "so", toiThieu: 1, toiDa: 99 },
                {
                  ten: "default_department",
                  nhan: f("request-types", "default_department"),
                  giaTri: l.default_department,
                  kieu: "chon",
                  luaChon: phongDangDung,
                },
                { ten: "is_active", nhan: f("request-types", "is_active"), giaTri: l.is_active, kieu: "bat-tat" },
              ];
              return (
                <DongDanhMuc
                  key={l.code}
                  danhMuc="request-types"
                  ma={l.code}
                  ten={l.label}
                  truong={truong}
                  soCot={8}
                  o={[
                    <b key="t">{l.label}</b>,
                    l.sla_hours,
                    l.sla_grace_hours,
                    `${l.sla_warn_percent}%`,
                    l.default_department ? (tenPhong[l.default_department] ?? l.default_department) : "(chưa có)",
                    l.is_active ? "Có" : "Không",
                    l.open_cases,
                  ]}
                />
              );
            })}
          </tbody>
        </table>
      </Muc>

      <Muc tieuDe="Mức ưu tiên" moTa="Hệ số nhân vào hạn chuẩn của loại yêu cầu: 50% là hạn còn một nửa, 200% là hạn dài gấp đôi.">
        <table className="bang bang-cau-hinh">
          <thead>
            <tr>
              <th>{f("priorities", "label")}</th>
              <th>{f("priorities", "sla_factor_percent")}</th>
              <th>Hồ sơ đang mở</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {cauHinh.priorities.map((m) => (
              <DongDanhMuc
                key={m.code}
                danhMuc="priorities"
                ma={m.code}
                ten={m.label}
                soCot={4}
                truong={[
                  { ten: "label", nhan: f("priorities", "label"), giaTri: m.label, kieu: "chu" },
                  { ten: "sla_factor_percent", nhan: f("priorities", "sla_factor_percent"), giaTri: m.sla_factor_percent, kieu: "so", toiThieu: 1, toiDa: 1000 },
                ]}
                o={[
                  <b key="t">
                    {m.label}
                    {m.is_default ? <span className="nhat"> · mặc định</span> : null}
                  </b>,
                  `${m.sla_factor_percent}%`,
                  m.open_cases,
                ]}
              />
            ))}
          </tbody>
        </table>
      </Muc>

      <Muc
        tieuDe="Phòng ban"
        moTa="Người trong phòng khai ở hệ thống định danh. Phòng đang là phòng mặc định của một loại yêu cầu thì phải đổi phòng mặc định trước khi ngưng."
      >
        <table className="bang bang-cau-hinh">
          <thead>
            <tr>
              <th>{f("departments", "label")}</th>
              <th>{f("departments", "description")}</th>
              <th>{f("departments", "is_active")}</th>
              <th>Hồ sơ đang mở</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {cauHinh.departments.map((p) => (
              <DongDanhMuc
                key={p.code}
                danhMuc="departments"
                ma={p.code}
                ten={p.label}
                soCot={5}
                truong={[
                  { ten: "label", nhan: f("departments", "label"), giaTri: p.label, kieu: "chu" },
                  { ten: "description", nhan: f("departments", "description"), giaTri: p.description, kieu: "chu" },
                  { ten: "is_active", nhan: f("departments", "is_active"), giaTri: p.is_active, kieu: "bat-tat" },
                ]}
                o={[<b key="t">{p.label}</b>, p.description ?? "", p.is_active ? "Có" : "Không", p.open_cases]}
              />
            ))}
          </tbody>
        </table>
      </Muc>

      <Muc
        tieuDe="Luồng xử lý"
        moTa="Chỉ xem. Thêm, bớt trạng thái hay bước chuyển là phát hành một bộ quy tắc phiên bản mới — hồ sơ đang chạy giữ luật cũ."
      >
        <table className="bang bang-cau-hinh">
          <thead>
            <tr>
              <th>Trạng thái</th>
              <th>Bước tiếp theo</th>
              <th>Ai làm</th>
              <th>Ràng buộc</th>
            </tr>
          </thead>
          {cauHinh.states.map((s) => {
            const canh = canhTheoNguon.get(s.code) ?? [];
            const dauDong = (
              <td rowSpan={Math.max(canh.length, 1)} style={{ verticalAlign: "top" }}>
                <b>{s.label}</b>
                <span className="nhat" style={{ display: "block", fontSize: "12px" }}>
                  {[
                    s.is_initial ? "bắt đầu" : null,
                    s.is_terminal ? "kết thúc" : null,
                    s.sla_running ? "đồng hồ hạn chạy" : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              </td>
            );
            return (
              <tbody key={s.code} data-trang-thai={s.code}>
                {canh.length === 0 ? (
                  <tr>
                    {dauDong}
                    <td colSpan={3} className="nhat">
                      Không có bước tiếp theo
                    </td>
                  </tr>
                ) : (
                  canh.map((t, i) => (
                    <tr key={`${t.to_state}-${t.is_system}`}>
                      {i === 0 ? dauDong : null}
                      <td>
                        {t.activity_label} → <b>{t.to_label}</b>
                        {t.auto_after_hours !== null ? (
                          <span className="nhat"> · tự đi sau {t.auto_after_hours} giờ làm việc</span>
                        ) : null}
                        {t.reopen_window_hours !== null ? (
                          <span className="nhat"> · trong {t.reopen_window_hours} giờ làm việc sau khi đóng</span>
                        ) : null}
                        {t.is_rework ? <span className="nhat"> · làm lại</span> : null}
                      </td>
                      <td>{t.is_system ? "Hệ thống" : t.roles.join(", ")}</td>
                      <td className="nhat">{t.guards.join(", ")}</td>
                    </tr>
                  ))
                )}
              </tbody>
            );
          })}
        </table>
      </Muc>

      {cauHinh.calendar ? (
        <Muc tieuDe={`Lịch làm việc: ${cauHinh.calendar.label}`} moTa={`Múi giờ ${cauHinh.calendar.time_zone}. Chỉ xem.`}>
          <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "13.5px" }}>
            {[1, 2, 3, 4, 5, 6, 7].map((thu) => {
              const khung = cauHinh.calendar!.hours.filter((h) => h.weekday === thu);
              return (
                <li key={thu}>
                  {THU[thu]}: {khung.length ? khung.map((k) => `${k.start}–${k.end}`).join(", ") : "nghỉ"}
                </li>
              );
            })}
          </ul>
          {cauHinh.calendar.holidays.length ? (
            <p className="nhat" style={{ fontSize: "13px", marginTop: "8px" }}>
              Ngày nghỉ sắp tới:{" "}
              {cauHinh.calendar.holidays.map((h) => `${h.label} (${h.day.split("-").reverse().join("/")})`).join("; ")}
            </p>
          ) : null}
        </Muc>
      ) : null}

      <Muc tieuDe="Nhật ký thay đổi cấu hình" moTa="Chỉ ghi thêm, không sửa hay xóa được.">
        {cauHinh.changes.length === 0 ? (
          <p className="nhat" style={{ fontSize: "13.5px" }}>
            Chưa có lần sửa nào.
          </p>
        ) : (
          <table className="bang bang-cau-hinh" data-nhat-ky-cau-hinh>
            <thead>
              <tr>
                <th>Lúc</th>
                <th>Người sửa</th>
                <th>Mục</th>
                <th>Trường</th>
                <th>Từ</th>
                <th>Thành</th>
              </tr>
            </thead>
            <tbody>
              {cauHinh.changes.map((c, i) => (
                <tr key={i}>
                  <td style={{ whiteSpace: "nowrap" }}>{ngayGio(c.changed_at)}</td>
                  <td>{c.actor_label}</td>
                  <td>
                    {c.entity_label} <span className="mono nhat">{c.entity_code}</span>
                  </td>
                  <td>{c.field_label}</td>
                  <td>{hienGiaTri(c.old_value)}</td>
                  <td>
                    <b>{hienGiaTri(c.new_value)}</b>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Muc>
    </>
  );
}
