# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 AlaVox-lab
"""Số phiên bản của dịch vụ khai phá (#552): cùng tệp `VERSION` ở gốc kho với dịch vụ ứng dụng.

Compose gắn tệp chỉ đọc vào `/app/VERSION`; chạy thẳng từ mã nguồn thì đọc ở gốc kho. Không tìm thấy thì ghi rõ là
không rõ, không bịa một số — trước #552 dịch vụ ghi cứng `0.11.0` trong mã.
"""

from __future__ import annotations

from pathlib import Path

KHONG_RO = "0.0.0+khong-ro"


def doc_phien_ban(tep_mo_dun: Path | None = None) -> str:
    """Dòng đầu của VERSION cạnh gói `app` (`/app/VERSION` trong ảnh chứa) hoặc ở gốc kho (services/khai-pha/../..)."""
    noi = (tep_mo_dun or Path(__file__)).resolve()
    cho_tim = [noi.parents[1]] + ([noi.parents[3]] if len(noi.parents) > 3 else [])
    for thu_muc in cho_tim:
        tep = thu_muc / "VERSION"
        if tep.is_file():
            dong = tep.read_text(encoding="utf-8").strip().splitlines()
            if dong and dong[0].strip():
                return dong[0].strip()
    return KHONG_RO


PHIEN_BAN = doc_phien_ban()
