# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Cấu hình của dịch vụ khai phá, đọc từ biến môi trường mang tiền tố KHAI_PHA_.
#
# Mọi con số chi phối kết quả — bội số xác định điểm nghẽn, số biến thể trả về — nằm ở đây chứ không
# nằm trong mã phân tích, để doanh nghiệp chỉnh được mà không sửa mã.

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class CauHinh:
    # Chuỗi kết nối psycopg của tài khoản chỉ đọc riêng (migration 0019 của dịch vụ ứng dụng)
    database_uri: str
    # `pm4py` (mặc định) hay `noi_bo` — mô-đun dự phòng không dùng thư viện khai phá (ADR-0007)
    bo_may: str
    # Trạng thái nghẽn khi thời gian chờ trung vị ở đó gấp từ chừng này lần trung vị chung
    boi_so_nghen: float
    # Số biến thể (chuỗi trạng thái) phổ biến nhất trả về
    so_bien_the: int
    # Số mã hồ sơ tối đa kèm mỗi nhánh lệch, mỗi biến thể — tổng số vẫn đếm đủ
    so_ho_so_moi_nhom: int


@lru_cache
def cau_hinh() -> CauHinh:
    return CauHinh(
        database_uri=os.environ.get(
            "KHAI_PHA_DATABASE_URI", "postgresql://khai_pha_readonly:khai_pha@localhost:5432/dxlab"
        ),
        bo_may=os.environ.get("KHAI_PHA_BO_MAY", "pm4py").strip().lower(),
        boi_so_nghen=float(os.environ.get("KHAI_PHA_BOI_SO_NGHEN", "2")),
        so_bien_the=int(os.environ.get("KHAI_PHA_SO_BIEN_THE", "10")),
        so_ho_so_moi_nhom=int(os.environ.get("KHAI_PHA_SO_HO_SO_MOI_NHOM", "200")),
    )
