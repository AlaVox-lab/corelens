# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ngày nghỉ lễ năm 2027 cho lịch mặc định (#439).
#
# Mã bản sửa    : 0033_ngay_le_2027
# Sửa đổi từ    : 0032_dieu_kien_tren_canh
#
# Đồng hồ SLA đã bỏ qua ngày trong bảng `holidays` (#199), nhưng dữ liệu mẫu mới có đủ năm 2026. Không thêm
# năm 2027 thì từ 01/2027 hạn xử lý tính cả ngày Tết. Chỉ là dữ liệu, không đổi lược đồ.
#
# Dữ liệu cho cụm cũ, khuôn 0028/0032: cụm đã có lịch `mac-dinh` thì chạy tệp 08 của dữ liệu khởi tạo. Cụm mới
# chưa có lịch lúc bản sửa này chạy, để bộ nạp chạy tệp 08 sau tệp 03. Tệp dùng ON CONFLICT nên ngày đã thêm tay
# qua màn cấu hình giữ nguyên. Hồ sơ, nhật ký, tệp giữ nguyên: nâng cấp bằng `up -d --build`, không `down -v`.

import logging
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

from app.cau_hinh.khoi_tao import bo_lenh_psql
from app.config import get_settings

revision: str = "0033_ngay_le_2027"
down_revision: str | None = "0032_dieu_kien_tren_canh"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TEP_NGAY_LE = "08-ngay-le-2027.sql"

log = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    ket_noi = op.get_bind()
    co_lich = ket_noi.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM work_calendars WHERE code = 'mac-dinh')")
    ).scalar_one()
    if not co_lich:
        return
    tep = Path(get_settings().seed_dir) / TEP_NGAY_LE
    if not tep.is_file():
        raise RuntimeError(
            f"Không thấy {TEP_NGAY_LE} trong {get_settings().seed_dir} — bản sửa 0033 cần nó để thêm ngày nghỉ "
            "lễ 2027 (infra/seed/ gắn vào container ở /seed)."
        )
    ket_noi.connection.driver_connection.execute(bo_lenh_psql(tep.read_text(encoding="utf-8")))
    log.info("0033: đã thêm ngày nghỉ lễ 2027 vào lịch mặc định")


def downgrade() -> None:
    # Chỉ gỡ ngày do tệp 08 thêm, trừ 01/01/2027 vốn đã có trong tệp 03
    op.execute(
        "DELETE FROM holidays WHERE calendar_code = 'mac-dinh' AND day BETWEEN DATE '2027-01-02' AND DATE '2027-12-31'"
    )
