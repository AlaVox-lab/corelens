# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 AlaVox-lab
#
# Phiên bản của dịch vụ khai phá (#552) đọc cùng tệp VERSION ở gốc kho với dịch vụ ứng dụng (Compose gắn vào
# /app/VERSION), không ghi cứng trong mã.

from __future__ import annotations

from pathlib import Path

from app import main, phien_ban


def test_doc_tep_canh_goi_app(tmp_path: Path):
    (tmp_path / "goc" / "app").mkdir(parents=True)
    (tmp_path / "goc" / "VERSION").write_text("2.0.0\n", encoding="utf-8")
    assert phien_ban.doc_phien_ban(tmp_path / "goc" / "app" / "m.py") == "2.0.0"


def test_doc_tep_o_goc_kho(tmp_path: Path):
    # Trong kho: services/khai-pha/app/phien_ban.py — tệp ở gốc kho, ba cấp trên gói app
    (tmp_path / "kho" / "services" / "khai-pha" / "app").mkdir(parents=True)
    (tmp_path / "kho" / "VERSION").write_text("1.9.3\n", encoding="utf-8")
    assert phien_ban.doc_phien_ban(tmp_path / "kho" / "services" / "khai-pha" / "app" / "m.py") == "1.9.3"


def test_thieu_tep_thi_ghi_khong_ro(tmp_path: Path):
    (tmp_path / "a" / "b" / "c" / "app").mkdir(parents=True)
    assert phien_ban.doc_phien_ban(tmp_path / "a" / "b" / "c" / "app" / "m.py") == phien_ban.KHONG_RO


def test_dich_vu_dung_so_cua_tep_gan_vao():
    tep = Path(phien_ban.__file__).resolve().parents[1] / "VERSION"
    assert tep.is_file(), "Compose phải gắn tệp VERSION ở gốc kho vào /app/VERSION"
    assert main.app.version == phien_ban.PHIEN_BAN == tep.read_text(encoding="utf-8").strip()
