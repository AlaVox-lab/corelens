# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Bộ nạp dữ liệu khởi tạo (#254).
#
# Trước #254, dữ liệu trong infra/seed/ do PostgreSQL nạp đúng một lần lúc tạo thực thể. Lược đồ
# cấu hình nay do Alembic tạo, nên dữ liệu phải nạp SAU Alembic — điểm vào của ảnh dịch vụ chạy
# `alembic upgrade head` rồi tới mô-đun này, rồi mới khởi động máy chủ:
#
#   1. Xin khóa tư vấn mức giao dịch: chạy nhiều bản dịch vụ cùng lúc thì chỉ một bản nạp, các bản
#      kia chờ rồi thấy dữ liệu đã có.
#   2. Chưa có bộ quy tắc nào thì chạy lần lượt mọi tệp `*.sql` trong thư mục dữ liệu khởi tạo, theo
#      tên. Đã có thì KHÔNG nạp lại — dữ liệu cấu hình doanh nghiệp đã sửa được giữ nguyên; đổi cấu
#      hình về sau là việc của bản sửa dữ liệu (bo_quy_tac.py).
#   3. Luôn gọi `kiem_tra_cau_hinh()` — cấu hình hỏng thì mô-đun thoát với mã lỗi và dịch vụ không
#      lên, như cụm cũ từng dừng khởi động ở bước nạp dữ liệu.
#
# Cả ba bước nằm trong một giao dịch: nạp dở hay kiểm hỏng thì không gì được ghi.
#
# Tệp dữ liệu khởi tạo vẫn viết cho psql (`\set ON_ERROR_STOP on`), nên dòng lệnh psql — mở đầu bằng
# dấu gạch chéo ngược — được bỏ trước khi gửi.

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Protocol

import psycopg
from sqlalchemy.engine import make_url

from app.config import get_settings

log = logging.getLogger("dxlab.cau_hinh")

# Cùng không gian khóa với bộ quét nền (app/workflow/nhip_quet.py), số thứ hai riêng cho bộ nạp
KHONG_GIAN_KHOA = 0x44584C42  # "DXLB"
KHOA_NAP_KHOI_TAO = 254


class KetNoi(Protocol):
    """Kết nối psycopg — kiểu tối thiểu bộ nạp cần, để bài kiểm thử truyền kết nối trong giao dịch
    của bài."""

    def execute(self, query: str, params: object = ...) -> psycopg.Cursor: ...


def bo_lenh_psql(noi_dung: str) -> str:
    """Bỏ các dòng lệnh của psql (`\\set …`) — chúng không phải SQL."""
    return "\n".join(d for d in noi_dung.splitlines() if not d.lstrip().startswith("\\"))


def nap_khoi_tao(ket_noi: KetNoi, thu_muc: Path) -> list[str]:
    """Nạp dữ liệu khởi tạo nếu chưa có bộ quy tắc nào. Trả tên các tệp đã nạp — rỗng nghĩa là cơ
    sở dữ liệu đã có cấu hình và không gì được đụng tới."""
    ket_noi.execute(
        "SELECT pg_advisory_xact_lock(%s, %s)", (KHONG_GIAN_KHOA, KHOA_NAP_KHOI_TAO)
    )
    da_co = ket_noi.execute("SELECT EXISTS (SELECT 1 FROM rule_sets)").fetchone()
    if da_co is not None and da_co[0]:
        return []

    cac_tep = sorted(thu_muc.glob("*.sql"))
    if not cac_tep:
        raise RuntimeError(
            f"Cơ sở dữ liệu chưa có bộ quy tắc nào và không thấy dữ liệu khởi tạo ở {thu_muc}. "
            "Dịch vụ cần thư mục infra/seed/ gắn vào (docker-compose.yml) hoặc biến DXLAB_SEED_DIR."
        )
    for tep in cac_tep:
        ket_noi.execute(bo_lenh_psql(tep.read_text(encoding="utf-8")))
    return [tep.name for tep in cac_tep]


def kiem_tra(ket_noi: KetNoi) -> None:
    """Kiểm tính nhất quán mức đồ thị; cấu hình hỏng thì PostgreSQL ném lỗi kèm lý do."""
    ket_noi.execute("SELECT kiem_tra_cau_hinh()")


def chuoi_ket_noi(dia_chi_sqlalchemy: str) -> str:
    """Chuỗi kết nối psycopg từ địa chỉ kiểu SQLAlchemy (`postgresql+psycopg://…`)."""
    return make_url(dia_chi_sqlalchemy).set(drivername="postgresql").render_as_string(
        hide_password=False
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cau_hinh = get_settings()
    thu_muc = Path(cau_hinh.seed_dir)
    try:
        # Thoát khối `with` bình thường thì psycopg commit, có ngoại lệ thì hoàn tác
        with psycopg.connect(chuoi_ket_noi(cau_hinh.database_uri)) as ket_noi:
            da_nap = nap_khoi_tao(ket_noi, thu_muc)
            kiem_tra(ket_noi)
    except Exception as loi:  # noqa: BLE001 — in lý do rồi dừng khởi động
        log.error("==> Cấu hình quy trình không hợp lệ, dịch vụ dừng khởi động: %s", loi)
        return 1
    if da_nap:
        log.info("==> Đã nạp dữ liệu khởi tạo: %s", ", ".join(da_nap))
    else:
        log.info("==> Đã có cấu hình quy trình, không nạp lại dữ liệu khởi tạo")
    log.info("==> Cấu hình quy trình hợp lệ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
