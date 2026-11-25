# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Tài liệu API tự sinh ở /docs viết cho người gọi API, không cho người đọc mã (#552): mỗi điểm cuối có tóm tắt
# tiếng Việt đặt tay — không để FastAPI tự ghép tên hàm thành "Danh Muc Quy Trinh" — và mô tả không lọt số issue
# hay đường dẫn tệp mã của nhóm.

from __future__ import annotations

import re

from fastapi.routing import APIRoute

from app.main import app
from app.tai_lieu_api import lam_sach

SO_ISSUE = re.compile(r"#\d+")
DUONG_DAN_MA = re.compile(r"(?:app|backend|frontend|infra|scripts|services)/[\w/.-]+\.(?:py|tsx?|sql)")


def _cac_tuyen() -> list[APIRoute]:
    return [r for r in app.routes if isinstance(r, APIRoute) and r.include_in_schema]


def test_moi_diem_cuoi_co_tom_tat_dat_tay():
    thieu = [f"{','.join(sorted(r.methods))} {r.path} ({r.name})" for r in _cac_tuyen() if not r.summary]
    assert not thieu, "Điểm cuối thiếu summary= — /docs sẽ hiện tên hàm không dấu:\n" + "\n".join(thieu)


def test_tom_tat_khong_phai_ten_ham_ghep():
    # Phòng khi ai đó gõ lại đúng chuỗi FastAPI tự sinh
    trung = [r.path for r in _cac_tuyen() if r.summary == r.name.replace("_", " ").title()]
    assert not trung, f"Tóm tắt trùng tên hàm tự ghép: {trung}"


def _moi_mo_ta(nut, ra: list[str]) -> list[str]:
    if isinstance(nut, dict):
        for khoa, gia_tri in nut.items():
            if khoa == "description" and isinstance(gia_tri, str):
                ra.append(gia_tri)
            else:
                _moi_mo_ta(gia_tri, ra)
    elif isinstance(nut, list):
        for gia_tri in nut:
            _moi_mo_ta(gia_tri, ra)
    return ra


def test_dac_ta_khong_lot_so_issue_hay_duong_dan_ma():
    loi = [
        m[:120]
        for m in _moi_mo_ta(app.openapi(), [])
        if SO_ISSUE.search(m) or DUONG_DAN_MA.search(m)
    ]
    assert not loi, (
        "Mô tả trong /docs còn số issue hay đường dẫn tệp mã. Đặt tham chiếu trong ngoặc riêng, ví dụ "
        "\"đang chạy (#376).\", để app/tai_lieu_api.py bỏ được:\n" + "\n".join(loi)
    )


def test_lam_sach_bo_ngoac_chi_chua_tham_chieu():
    assert lam_sach("Các quy trình đang chạy (#376).") == "Các quy trình đang chạy."
    assert lam_sach("Mã lỗi (#376, app/workflow/errors.py).") == "Mã lỗi."
    assert lam_sach("Xem (`chon_quy_trinh` ở app/workflow/routes.py)") == "Xem"


def test_lam_sach_giu_ngoac_co_chu_khac():
    giu = "Hạn tính theo giờ làm việc (lịch khai trong dữ liệu, #261)."
    assert lam_sach(giu) == giu
    assert lam_sach("Trả 404 (không có hồ sơ).") == "Trả 404 (không có hồ sơ)."
