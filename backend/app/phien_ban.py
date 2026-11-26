# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
"""Số phiên bản hiển thị của Corelens (#552): một nguồn duy nhất là tệp `VERSION` ở gốc kho.

Trước #552 số này đi từ biến `DXLAB_VERSION` của `.env` — vốn là thẻ ảnh chứa — sang dịch vụ, và nằm yên ở
`0.3.0` qua mười mấy bản phát hành. Giờ biến môi trường không còn ở đường hiển thị: Compose gắn tệp `VERSION`
chỉ đọc vào `/app/VERSION`, chạy thẳng từ mã nguồn thì đọc ở gốc kho. Phát hành là sửa một tệp đó
(`CONTRIBUTING.md`, mục phát hành); `tests/test_phien_ban.py` báo lỗi khi số tụt sau mục mới nhất của
`CHANGELOG.md`. Dịch vụ khai phá đọc cùng tệp theo cùng cách.
"""

from __future__ import annotations

from pathlib import Path

# Không tìm thấy tệp (ví dụ chạy ảnh ngoài Compose) thì ghi rõ là không rõ, không bịa một số
KHONG_RO = "0.0.0+khong-ro"


def doc_phien_ban(tep_mo_dun: Path | None = None) -> str:
    """Đọc dòng đầu của tệp VERSION: cạnh gói `app` (trong ảnh chứa, `/app/VERSION`) hoặc ở gốc kho.

    `tep_mo_dun` là đường dẫn một tệp trong gói `app` — mặc định chính tệp này; bài kiểm truyền chỗ khác.
    """
    noi = (tep_mo_dun or Path(__file__)).resolve()
    for thu_muc in (noi.parents[1], noi.parents[2]):
        tep = thu_muc / "VERSION"
        if tep.is_file():
            dong = tep.read_text(encoding="utf-8").strip().splitlines()
            if dong and dong[0].strip():
                return dong[0].strip()
    return KHONG_RO


PHIEN_BAN = doc_phien_ban()
