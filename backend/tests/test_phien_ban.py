# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Số phiên bản hiển thị (#552): một nguồn là tệp VERSION ở gốc kho, Compose gắn vào /app/VERSION. Biến môi trường
# cũ (`DXLAB_APP_VERSION`, từng lấy từ `DXLAB_VERSION=0.3.0` của .env) không còn đè được số hiển thị. Việc số
# không tụt sau CHANGELOG.md kiểm ở scripts/kiem_phien_ban.py (CHANGELOG không nằm trong ảnh chứa).

from __future__ import annotations

from pathlib import Path

from app import phien_ban
from app.config import get_settings
from app.main import app


def test_doc_tep_canh_goi_app(tmp_path: Path):
    (tmp_path / "goc" / "app").mkdir(parents=True)
    (tmp_path / "goc" / "VERSION").write_text("2.0.0\n", encoding="utf-8")
    assert phien_ban.doc_phien_ban(tmp_path / "goc" / "app" / "m.py") == "2.0.0"


def test_doc_tep_o_goc_kho_khi_chay_tu_ma_nguon(tmp_path: Path):
    # Trong kho: backend/app/phien_ban.py — tệp ở gốc kho, hai cấp trên gói app
    (tmp_path / "kho" / "backend" / "app").mkdir(parents=True)
    (tmp_path / "kho" / "VERSION").write_text("1.9.3\n", encoding="utf-8")
    assert phien_ban.doc_phien_ban(tmp_path / "kho" / "backend" / "app" / "m.py") == "1.9.3"


def test_thieu_tep_thi_ghi_khong_ro_khong_bia_so(tmp_path: Path):
    (tmp_path / "a" / "b" / "app").mkdir(parents=True)
    assert phien_ban.doc_phien_ban(tmp_path / "a" / "b" / "app" / "m.py") == phien_ban.KHONG_RO


def test_cum_doc_dung_tep_gan_vao():
    tep = Path(phien_ban.__file__).resolve().parents[1] / "VERSION"
    assert tep.is_file(), "Compose phải gắn tệp VERSION ở gốc kho vào /app/VERSION"
    assert phien_ban.PHIEN_BAN == tep.read_text(encoding="utf-8").strip()
    assert phien_ban.PHIEN_BAN != phien_ban.KHONG_RO


def test_bien_moi_truong_cu_khong_de_so_hien_thi(monkeypatch):
    # .env cũ còn DXLAB_VERSION=0.3.0; Compose cũ chuyển nó thành DXLAB_APP_VERSION
    monkeypatch.setenv("DXLAB_APP_VERSION", "0.3.0")
    monkeypatch.setenv("DXLAB_VERSION", "0.3.0")
    get_settings.cache_clear()
    try:
        assert not hasattr(get_settings(), "app_version")
        assert app.openapi()["info"]["version"] == phien_ban.PHIEN_BAN != "0.3.0"
    finally:
        get_settings.cache_clear()
