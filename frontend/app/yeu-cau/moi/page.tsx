// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Màn “Gửi yêu cầu”.
//
// Danh mục loại yêu cầu nạp từ dịch vụ ứng dụng, KHÔNG viết cứng bốn lựa chọn vào mã
// nguồn. Doanh nghiệp triển khai khai lại danh mục của họ trong `infra/seed/` và giao
// diện đổi theo mà không ai phải sửa một dòng TypeScript nào — xem CLAUDE.md mục 1.2.

import { BieuMauGuiYeuCau } from "@/app/yeu-cau/moi/bieu-mau";
import { goiDichVu } from "@/lib/api";
import type { ChinhSachTep, HoSoChiTiet, LoaiYeuCau } from "@/lib/kieu";

export const dynamic = "force-dynamic";

export default async function GuiYeuCau({
  searchParams,
}: {
  searchParams: Promise<{ tu?: string; loai?: string }>;
}) {
  const cacLoai = await goiDichVu<LoaiYeuCau[]>("/request-types");
  // Giới hạn tệp đính kèm (#80). Không nạp được thì biểu mẫu vẫn gửi được, chỉ không có ô tệp
  const chinhSachTep = await goiDichVu<ChinhSachTep>("/attachments/policy");

  // Tạo lại từ một hồ sơ cũ của chính mình (#102): `?tu=<mã hồ sơ>`. Dịch vụ trả 404 cho hồ
  // sơ của người khác, nên mã lạ chỉ làm biểu mẫu trống như thường. Cái dịch vụ kiểm lại lúc
  // gửi mới là cái quyết định — chép sẵn ở đây chỉ để người gửi đỡ gõ lại.
  const { tu, loai } = await searchParams;
  const maGoc = tu && /^\d+$/.test(tu) ? Number(tu) : null;
  const goc = maGoc ? await goiDichVu<HoSoChiTiet>(`/requests/${maGoc}`) : null;

  // Mở thẳng một loại (#434): `?loai=<mã loại>` để trang tri thức hay thư thông báo dẫn vào đúng
  // biểu mẫu. Mã chỉ được dùng khi khớp một loại trong danh mục vừa nạp — kiểm ở biểu mẫu

  return (
    <>
      <h1
        style={{
          margin: 0,
          fontSize: "clamp(22px,3.4vw,28px)",
          fontWeight: 600,
          letterSpacing: "-.02em",
          lineHeight: 1.25,
        }}
      >
        Gửi yêu cầu
      </h1>
      <p
        style={{
          margin: "7px 0 0",
          fontSize: "14.5px",
          color: "var(--ink-2)",
          maxWidth: "62ch",
          lineHeight: 1.6,
        }}
      >
        Một biểu mẫu cho mọi loại yêu cầu nội bộ. Điền xong, hồ sơ tự chạy tới đúng
        phòng ban và bạn theo dõi được từng bước nó đi.
      </p>

      {cacLoai === null ? (
        <div
          className="the"
          style={{ marginTop: "20px", padding: "24px", textAlign: "center" }}
        >
          <p style={{ margin: 0, fontSize: "14.5px", fontWeight: 600 }}>
            Chưa nạp được danh mục loại yêu cầu
          </p>
          <p
            style={{
              margin: "6px 0 0",
              fontSize: "13.5px",
              color: "var(--ink-2)",
              lineHeight: 1.6,
            }}
          >
            Hệ thống không phản hồi. Tải lại trang sau ít phút; nếu vẫn vậy thì
            báo quản trị hệ thống.
          </p>
        </div>
      ) : (
        <BieuMauGuiYeuCau
          chinhSach={chinhSachTep}
          cacLoai={cacLoai}
          loaiSan={loai ?? null}
          goc={
            goc && goc.state.is_terminal
              ? {
                  id: goc.id,
                  code: goc.code,
                  title: goc.title,
                  description: goc.description ?? "",
                  request_type_code: goc.request_type?.code ?? null,
                }
              : null
          }
        />
      )}
    </>
  );
}
