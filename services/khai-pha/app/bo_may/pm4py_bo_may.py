# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Bộ máy khai phá dùng PM4Py (AGPL-3.0-or-later, ADR-0007).
#
# Tệp này là nơi DUY NHẤT trong kho `import pm4py`. Dịch vụ ứng dụng và cổng không bao giờ nhập
# thư viện này: chúng chỉ nhận JSON qua HTTP từ dịch vụ khai phá (ranh giới ở ADR-0007 và
# docs/ARCHITECTURE.md mục 3.3). Tệp của nhóm vẫn mang giấy phép MIT; khi chạy, cả dịch vụ khai phá là
# một chương trình dùng thư viện AGPL, mã nguồn công khai trong kho đáp ứng điều 13.
#
# Không sửa mã thư viện, chỉ gọi hàm cấp cao: `discover_dfg` cho đồ thị trực tiếp,
# `split_by_process_variant` cho biến thể kèm hồ sơ của từng biến thể.

from __future__ import annotations

import pandas as pd
import pm4py

from . import LuotVao

COT_HO_SO = "case:concept:name"
COT_HOAT_DONG = "concept:name"
COT_THOI_DIEM = "time:timestamp"


def _bang(luot: list[LuotVao]) -> pd.DataFrame:
    # Thứ tự trong bảng là thứ tự PM4Py dùng khi hai lượt trùng thời điểm, nên xếp trước theo thứ tự
    # của nhật ký — cùng quy ước với bộ máy dự phòng
    xep = sorted(luot, key=lambda l: (l.ho_so, l.luc, l.thu_tu))
    bang = pd.DataFrame(
        {
            COT_HO_SO: [str(l.ho_so) for l in xep],
            COT_HOAT_DONG: [l.trang_thai for l in xep],
            COT_THOI_DIEM: pd.to_datetime([l.luc for l in xep], utc=True),
        }
    )
    return pm4py.format_dataframe(
        bang, case_id=COT_HO_SO, activity_key=COT_HOAT_DONG, timestamp_key=COT_THOI_DIEM
    )


class BoMayPm4py:
    ten = "pm4py"

    def do_thi(self, luot: list[LuotVao]) -> dict[tuple[str, str], int]:
        if not luot:
            return {}
        dfg, _bat_dau, _ket_thuc = pm4py.discover_dfg(_bang(luot))
        return {(a, b): int(so) for (a, b), so in dfg.items()}

    def bien_the(self, luot: list[LuotVao]) -> dict[tuple[str, ...], list[int]]:
        if not luot:
            return {}
        ket_qua: dict[tuple[str, ...], list[int]] = {}
        for chuoi, bang_con in pm4py.split_by_process_variant(_bang(luot)):
            ho_so = sorted(int(x) for x in bang_con[COT_HO_SO].unique())
            ket_qua[tuple(chuoi)] = ho_so
        return ket_qua
