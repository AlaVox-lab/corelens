// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khối xuất nhật ký sự kiện trên màn Hệ thống (#306). Biểu mẫu GET thường, không cần JavaScript:
// trình duyệt mở route handler, tệp tải về và trang vẫn đứng yên.

import { Download } from "lucide-react";

export function XuatNhatKy() {
  return (
    <section className="the" aria-labelledby="xuat-nhat-ky">
      <div className="khoi-dau">
        <h2 id="xuat-nhat-ky">Xuất nhật ký sự kiện</h2>
      </div>
      <div className="xuat-nhat-ky-than">
        <p className="xuat-nhat-ky-giai-thich">
          Mỗi dòng một sự kiện: mã hồ sơ, hoạt động, thời điểm (UTC), mã người thao tác, trạng thái
          trước và sau, cùng loại yêu cầu, phòng ban, mức ưu tiên của hồ sơ. Không có tên người và
          ghi chú. Bỏ trống ngày là lấy toàn bộ.
        </p>
        <form action="/api/xuat/nhat-ky" method="get" className="xuat-nhat-ky">
          <label className="o-truong">
            <span className="o-truong-nhan">Từ ngày</span>
            <input type="date" name="tu" className="o-nhap" />
          </label>
          <label className="o-truong">
            <span className="o-truong-nhan">Đến hết ngày</span>
            <input type="date" name="den" className="o-nhap" />
          </label>
          <div className="xuat-nhat-ky-nut">
            <button type="submit" name="dinh-dang" value="csv" className="nut" data-loai="chinh">
              <Download aria-hidden />
              Tải CSV
            </button>
            <button type="submit" name="dinh-dang" value="json" className="nut">
              <Download aria-hidden />
              Tải JSON
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
