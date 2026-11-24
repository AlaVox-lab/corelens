# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kho tri thức làm nguồn gợi ý thứ hai (#321). Wiki.js thay bằng một GraphQL giả trong bộ nhớ, mô hình
# nhúng bằng máy chủ giả của test_tuong_tu.py (véc-tơ túi từ). Định nghĩa hoàn thành của issue: một bài
# hướng dẫn mới xuất hiện trong gợi ý khi người gửi gõ đúng vấn đề đó.

from __future__ import annotations

import contextlib
import datetime as dt
import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth.dependencies import current_actor, current_claims
from app.config import Settings
from app.db import get_session
from app.intelligence import mo_hinh, tri_thuc, tuong_tu
from app.main import app
from app.workflow.context import Actor
from tests.test_tuong_tu import HAN_CHOT, NhungGia, _cong_dong

NGUOI_GUI = Actor(id="ng-321", roles=frozenset({"requester"}), name="Người gửi 321")
WIKI = "http://wiki.thu"


class WikiGia:
    """Wiki.js trong bộ nhớ: danh sách bài qua GraphQL, và nội dung bài như trang mã nguồn trả."""

    def __init__(self) -> None:
        self.bai: dict[int, dict] = {}
        self.hong = False
        self.so_lan_doc_noi_dung = 0

    def dat(self, ma: int, tieu_de: str, noi_dung: str, *, luc: str = "2026-11-14T01:00:00.000Z",
            xuat_ban: bool = True, rieng_tu: bool = False, mo_ta: str = "", duong: str | None = None) -> None:
        self.bai[ma] = {
            "id": ma, "path": duong or f"huong-dan/bai-{ma}", "locale": "vi", "title": tieu_de, "description": mo_ta,
            "isPublished": xuat_ban, "isPrivate": rieng_tu, "updatedAt": luc, "content": noi_dung,
        }

    def noi_dung(self, bai: tri_thuc.Bai) -> str:
        if self.hong:
            raise tri_thuc.LoiKhoTriThuc("wiki không phản hồi")
        self.so_lan_doc_noi_dung += 1
        return self.bai[bai.page_id]["content"]

    def __call__(self, truy_van: str, bien: dict | None) -> dict:
        if self.hong:
            raise tri_thuc.LoiKhoTriThuc("wiki không phản hồi")
        return {"pages": {"list": [{k: v for k, v in b.items() if k != "content"} for b in self.bai.values()]}}


def dat_cau_hinh(monkeypatch, **gia_tri) -> Settings:
    cau_hinh = Settings(**{"similar_min_score": 0.2, "wiki_min_score": 0.2, **gia_tri})
    for tep in (mo_hinh, tuong_tu, tri_thuc):
        monkeypatch.setattr(tep, "get_settings", lambda: cau_hinh)
    return cau_hinh


@pytest.fixture
def nhung_gia():
    gia = NhungGia()
    luong = threading.Thread(target=gia.may_chu.serve_forever, daemon=True)
    luong.start()
    try:
        yield gia
    finally:
        gia.may_chu.shutdown()
        gia.may_chu.server_close()


@pytest.fixture
def bat(monkeypatch, nhung_gia):
    """Kho tri thức và mô hình nhúng cùng bật."""
    return dat_cau_hinh(
        monkeypatch,
        embedding_url=nhung_gia.url,
        embedding_timeout_seconds=HAN_CHOT,
        similar_timeout_seconds=HAN_CHOT,
        wiki_public_url=WIKI,
    )


def _quet(session, wiki: WikiGia) -> int:
    return tri_thuc.quet_kho_tri_thuc(
        session, hoi=wiki, doc=wiki.noi_dung, mo_phien=lambda: contextlib.nullcontext(session)
    )


def _bai_trong_chi_muc(session) -> dict[int, tuple[str, str | None]]:
    return {r[0]: (r[1], r[2]) for r in session.execute(text("SELECT page_id, title, excerpt FROM knowledge_articles"))}


@pytest.fixture
def chi_muc_trong(session):
    """Bảng chỉ mục của cụm thử có thể đã có bài từ wiki thật; mỗi bài bắt đầu từ bảng trống."""
    session.execute(text("DELETE FROM knowledge_articles"))
    session.flush()


# ---------------------------------------------------------------------------
# Bộ lập chỉ mục
# ---------------------------------------------------------------------------


def test_lap_chi_muc_bai_xuat_ban_bo_bai_rieng_tu(session, bat, chi_muc_trong):
    wiki = WikiGia()
    wiki.dat(1, "Máy in không in được", "Hết giấy, kẹt giấy, lệnh in bị treo")
    wiki.dat(2, "Bản nháp", "Chưa xuất bản", xuat_ban=False)
    wiki.dat(3, "Ghi chú riêng", "Riêng tư", rieng_tu=True)
    assert _quet(session, wiki) == 1
    assert set(_bai_trong_chi_muc(session)) == {1}
    # Không đổi gì thì lượt sau không nhúng lại
    assert _quet(session, wiki) == 0


def test_trang_chu_wiki_khong_vao_chi_muc(session, bat, chi_muc_trong):
    """Trang chủ là mục lục, gần với mọi câu hỏi — đưa vào chỉ mục thì nó chen vào gợi ý (#535)."""
    wiki = WikiGia()
    wiki.dat(1, "Máy in không in được", "Hết giấy, kẹt giấy, lệnh in bị treo")
    wiki.dat(2, "Kho tri thức", "Máy in, mật khẩu, cấp quyền phần mềm", duong=tri_thuc.TRANG_CHU_WIKI)
    assert _quet(session, wiki) == 1
    assert set(_bai_trong_chi_muc(session)) == {1}


def test_bai_sua_thi_nhung_lai_bai_xoa_thi_bo(session, bat, chi_muc_trong):
    wiki = WikiGia()
    wiki.dat(1, "Máy in không in được", "Bản cũ")
    wiki.dat(2, "Đặt lại mật khẩu", "Trang tài khoản")
    _quet(session, wiki)
    wiki.dat(1, "Máy in không in được", "Bản mới: tắt máy in mười giây", luc="2026-11-14T02:00:00.000Z")
    del wiki.bai[2]
    assert _quet(session, wiki) == 2
    con = _bai_trong_chi_muc(session)
    assert set(con) == {1}
    assert "Bản mới" in con[1][1]


def test_lo_gioi_han_moi_luot(session, monkeypatch, nhung_gia, chi_muc_trong):
    dat_cau_hinh(monkeypatch, embedding_url=nhung_gia.url, embedding_timeout_seconds=HAN_CHOT,
                 wiki_public_url=WIKI, wiki_index_batch_size=2)
    wiki = WikiGia()
    for ma in range(1, 6):
        wiki.dat(ma, f"Bài {ma}", f"Nội dung {ma}")
    assert _quet(session, wiki) == 2
    assert _quet(session, wiki) == 2
    assert _quet(session, wiki) == 1
    assert len(_bai_trong_chi_muc(session)) == 5


@pytest.mark.parametrize("tat", ["wiki", "nhung"])
def test_mot_trong_hai_tat_thi_khong_lam_gi(session, monkeypatch, nhung_gia, chi_muc_trong, tat):
    dat_cau_hinh(
        monkeypatch,
        embedding_url="" if tat == "nhung" else nhung_gia.url,
        wiki_public_url="" if tat == "wiki" else WIKI,
    )
    wiki = WikiGia()
    wiki.dat(1, "Máy in", "Kẹt giấy")
    assert _quet(session, wiki) == 0
    assert _bai_trong_chi_muc(session) == {}
    assert wiki.so_lan_doc_noi_dung == 0


def test_wiki_hong_hay_nhung_hong_thi_bo_luot_khong_mat_chi_muc(session, monkeypatch, bat, chi_muc_trong):
    wiki = WikiGia()
    wiki.dat(1, "Máy in", "Kẹt giấy")
    _quet(session, wiki)
    wiki.hong = True
    assert _quet(session, wiki) == 0
    wiki.hong = False
    wiki.dat(2, "Bài mới", "Nội dung")
    dat_cau_hinh(monkeypatch, embedding_url=_cong_dong(), embedding_timeout_seconds=HAN_CHOT, wiki_public_url=WIKI)
    assert _quet(session, wiki) == 0
    assert set(_bai_trong_chi_muc(session)) == {1}


def test_khoa_api_thieu_hay_wiki_khong_toi_duoc(monkeypatch, tmp_path):
    dat_cau_hinh(monkeypatch, wiki_public_url=WIKI, wiki_api_key_file=str(tmp_path / "khong-co"))
    with pytest.raises(tri_thuc.LoiKhoTriThuc, match="chưa có khóa"):
        tri_thuc.hoi_wiki("{ __typename }")
    tep = tmp_path / "khoa"
    tep.write_text("khoa-thu", encoding="utf-8")
    dat_cau_hinh(monkeypatch, wiki_public_url=WIKI, wiki_api_key_file=str(tep), wiki_internal_url=_cong_dong(),
                 wiki_timeout_seconds=HAN_CHOT)
    with pytest.raises(tri_thuc.LoiKhoTriThuc, match="không gọi được"):
        tri_thuc.hoi_wiki("{ __typename }")


# Đoạn cuối của trang mã nguồn Wiki.js 2.5.315 (views/source.pug), ký tự đặc biệt đã thoát HTML
TRANG_MA_NGUON = (
    '<div id="root"><page-source :page-id="3" locale="vi" path="huong-dan/may-in">'
    "<code v-pre># Máy in không in được\n\n1. **Kẹt giấy** &amp; hết mực &lt;đèn cam&gt;</code>"
    "</page-source></div>"
)


def test_doc_noi_dung_tu_trang_ma_nguon():
    assert tri_thuc.noi_dung_tu_trang(TRANG_MA_NGUON, "huong-dan/may-in") == (
        "# Máy in không in được\n\n1. **Kẹt giấy** & hết mực <đèn cam>"
    )
    with pytest.raises(tri_thuc.LoiKhoTriThuc, match="định dạng"):
        tri_thuc.noi_dung_tu_trang("<html>Unauthorized</html>", "huong-dan/may-in")


def test_chu_tron_bo_ky_hieu_markdown():
    assert tri_thuc.chu_tron("# Tiêu đề\n\n1. **Hết giấy** — `mở khay`\n![ảnh](http://x/y.png)") == (
        "Tiêu đề 1. Hết giấy — mở khay"
    )


# ---------------------------------------------------------------------------
# Gợi ý khi soạn: hồ sơ và bài trong cùng một lần nhúng
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _may_khach(session):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: NGUOI_GUI
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def test_bai_moi_xuat_hien_trong_goi_y_khi_go_dung_van_de(session, bat, chi_muc_trong, nhung_gia):
    wiki = WikiGia()
    wiki.dat(7, "Máy in không in được", "Máy in kẹt giấy hết giấy lệnh in treo", mo_ta="Năm bước tự kiểm")
    wiki.dat(8, "Đặt lại mật khẩu", "Quên mật khẩu tài khoản công ty")
    _quet(session, wiki)
    so_lan_truoc = nhung_gia.so_lan

    with _may_khach(session) as c:
        ra = c.post("/similar-cases/search", json={"title": "Máy in kẹt giấy", "description": "máy in không in được"})
    assert ra.status_code == 200
    than = ra.json()
    assert [b["title"] for b in than["articles"]][0] == "Máy in không in được"
    assert than["articles"][0]["url"] == f"{WIKI}/huong-dan/bai-7"
    assert than["articles"][0]["description"] == "Năm bước tự kiểm"
    assert than["articles_source_url"].startswith("https://github.com/requarks/wiki")
    # Một lần nhúng cho cả hồ sơ lẫn bài
    assert nhung_gia.so_lan == so_lan_truoc + 1


def test_kho_tri_thuc_tat_thi_goi_y_khong_co_bai(session, monkeypatch, nhung_gia, chi_muc_trong):
    bat_ca = dat_cau_hinh(monkeypatch, embedding_url=nhung_gia.url, embedding_timeout_seconds=HAN_CHOT,
                          similar_timeout_seconds=HAN_CHOT, wiki_public_url=WIKI)
    wiki = WikiGia()
    wiki.dat(7, "Máy in không in được", "Máy in kẹt giấy")
    _quet(session, wiki)
    dat_cau_hinh(monkeypatch, embedding_url=bat_ca.embedding_url, similar_timeout_seconds=HAN_CHOT, wiki_public_url="")
    with _may_khach(session) as c:
        than = c.post("/similar-cases/search", json={"title": "Máy in kẹt giấy", "description": "máy in"}).json()
    assert than["articles"] == [] and than["articles_source_url"] is None


def test_me_tra_loi_vao_kho_tri_thuc_khi_bat(session, monkeypatch):
    import app.main as chinh

    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: NGUOI_GUI
    app.dependency_overrides[current_claims] = lambda: {"sub": NGUOI_GUI.id}
    try:
        with TestClient(app) as c:
            monkeypatch.setattr(chinh, "settings", Settings(wiki_public_url=f"{WIKI}/"))
            bat_kb = c.get("/me").json()["knowledge_base"]
            monkeypatch.setattr(chinh, "settings", Settings(wiki_public_url=""))
            tat_kb = c.get("/me").json()["knowledge_base"]
    finally:
        app.dependency_overrides.clear()
    assert bat_kb["url"] == f"{WIKI}/login/keycloak"
    assert bat_kb["source_url"].startswith("https://github.com/requarks/wiki")
    assert tat_kb is None


def test_moc_cap_nhat_doc_dung_mui_gio():
    assert tri_thuc._thoi_diem("2026-11-14T02:07:16.911Z") == dt.datetime(
        2026, 11, 14, 2, 7, 16, 911000, tzinfo=dt.timezone.utc
    )
