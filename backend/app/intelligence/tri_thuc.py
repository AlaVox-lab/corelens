# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Bài viết của kho tri thức làm nguồn thứ hai cho gợi ý khi soạn yêu cầu (#321, ADR-0006).
#
# HAI VIỆC
#
# 1. LẬP CHỈ MỤC — bộ quét `wiki-index` theo khuôn `app/workflow/nhip_quet.py` (khóa tư vấn, nhịp sức
#    khỏe trên màn Hệ thống). Mỗi lượt đọc danh sách bài qua GraphQL của Wiki.js bằng khóa API CHỈ ĐỌC, so
#    với bảng `knowledge_articles`: bài mới hay vừa sửa (mốc `updatedAt` khác, hay nhúng bằng mô hình cũ)
#    thì đọc nội dung, nhúng, ghi lại; bài đã xóa, thôi xuất bản, chuyển riêng tư thì xóa khỏi chỉ mục.
#    Một lượt nhúng tối đa `wiki_index_batch_size` bài; phần còn lại để lượt sau.
#
# 2. TÌM — `tim_bai` nhận đúng véc-tơ câu hỏi mà hồ sơ tương tự (#319) đã nhúng, quét chính xác bằng
#    khoảng cách cosine của pgvector, tối đa `wiki_max_results` bài trên ngưỡng.
#
# Ranh giới AGPL (LICENSES.md): Wiki.js là chương trình khác, chỉ được gọi qua HTTP/GraphQL. Không mã nào
# của Wiki.js ở đây. Kho tri thức tắt, khóa chưa có, wiki không phản hồi, mô hình nhúng tắt — bộ quét bỏ
# lượt hay không có việc, biểu mẫu Gửi yêu cầu không có bài, không gì khác hỏng.
#
# Chỉ ghi bảng riêng `knowledge_articles`, không chạm hồ sơ hay trường quyết định nào (CLAUDE.md mục 4.3).

from __future__ import annotations

import datetime as dt
import html
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.intelligence import mo_hinh

log = logging.getLogger(__name__)

TEN_BO_QUET_TRI_THUC = "wiki-index"
NHAN_BO_QUET_TRI_THUC = "Bộ lập chỉ mục kho tri thức"

DO_DAI_DOAN_DAU = 300

MoPhien = Callable[[], AbstractContextManager[Session]]
HoiWiki = Callable[[str, dict | None], dict]
DocNoiDung = Callable[["Bai"], str]


class LoiKhoTriThuc(Exception):
    """Kho tri thức không dùng được lượt này: chưa có khóa, không phản hồi, trả lỗi."""


def _mo_phien_that() -> AbstractContextManager[Session]:
    from app.db import SessionLocal

    return SessionLocal()


# ---------------------------------------------------------------------------
# GraphQL của Wiki.js
# ---------------------------------------------------------------------------


def doc_khoa() -> str:
    tep = Path(get_settings().wiki_api_key_file)
    try:
        khoa = tep.read_text(encoding="utf-8").strip()
    except OSError as loi:
        raise LoiKhoTriThuc(f"chưa có khóa API ({tep}) — bước khởi tạo kho tri thức đã chạy chưa?") from loi
    if not khoa:
        raise LoiKhoTriThuc(f"tệp khóa API {tep} rỗng")
    return khoa


def hoi_wiki(truy_van: str, bien: dict | None = None) -> dict:
    """Một truy vấn GraphQL tới Wiki.js bằng khóa API chỉ đọc. Ném `LoiKhoTriThuc` với mọi trục trặc."""
    cau_hinh = get_settings()
    yeu_cau = urllib.request.Request(
        cau_hinh.wiki_internal_url.rstrip("/") + "/graphql",
        data=json.dumps({"query": truy_van, "variables": bien or {}}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {doc_khoa()}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(yeu_cau, timeout=cau_hinh.wiki_timeout_seconds) as tl:
            ket_qua = json.loads(tl.read())
    except (urllib.error.URLError, OSError, ValueError) as loi:
        raise LoiKhoTriThuc(f"không gọi được kho tri thức: {loi}") from loi
    if ket_qua.get("errors"):
        raise LoiKhoTriThuc(f"kho tri thức báo lỗi: {ket_qua['errors'][0].get('message')}")
    return ket_qua["data"]


_KHOI_MA_NGUON = re.compile(r"<code v-pre>(.*?)</code>", re.S)


def doc_noi_dung(bai: Bai) -> str:
    """Nội dung Markdown của một bài, đọc từ trang mã nguồn `/s/<ngôn ngữ>/<đường dẫn>` của Wiki.js.

    Vì sao không dùng GraphQL: ở Wiki.js 2.5, `pages.single` đòi quyền `manage:pages` hoặc `delete:pages`
    — quyền sửa, xóa bài — chỉ để đọc nội dung, còn khóa của dịch vụ ứng dụng chỉ mang quyền đọc. Trang mã
    nguồn chỉ cần `read:source` và nhận cùng khóa API (Bearer). Định dạng của trang ổn định vì ảnh Wiki.js
    ghim phiên bản; nâng Wiki.js thì kiểm lại hàm này (bài test_tri_thuc.py có mẫu trang)."""
    cau_hinh = get_settings()
    duong = urllib.parse.quote(f"/s/{bai.locale}/{bai.path}")
    yeu_cau = urllib.request.Request(
        cau_hinh.wiki_internal_url.rstrip("/") + duong, headers={"Authorization": f"Bearer {doc_khoa()}"}
    )
    try:
        with urllib.request.urlopen(yeu_cau, timeout=cau_hinh.wiki_timeout_seconds) as tl:
            trang = tl.read().decode("utf-8")
    except (urllib.error.URLError, OSError, UnicodeDecodeError) as loi:
        raise LoiKhoTriThuc(f"không đọc được bài {bai.path}: {loi}") from loi
    return noi_dung_tu_trang(trang, bai.path)


def noi_dung_tu_trang(trang: str, duong: str) -> str:
    khop = _KHOI_MA_NGUON.search(trang)
    if khop is None:
        raise LoiKhoTriThuc(f"trang mã nguồn của bài {duong} không đúng định dạng mong đợi")
    return html.unescape(khop.group(1))


# ---------------------------------------------------------------------------
# Lập chỉ mục
# ---------------------------------------------------------------------------


_DANH_DAU = re.compile(r"[#*_`>|\[\]]+|!\[[^\]]*\]\([^)]*\)|\(https?://[^)]*\)")


def chu_tron(markdown: str) -> str:
    """Bỏ phần lớn ký hiệu Markdown để đoạn nhúng và đoạn đầu là chữ người đọc được."""
    return re.sub(r"\s+", " ", _DANH_DAU.sub(" ", markdown)).strip()


@dataclass(frozen=True)
class Bai:
    page_id: int
    path: str
    locale: str
    title: str
    description: str
    updated_at: dt.datetime

    def doan_nhung(self, noi_dung: str) -> str:
        """Đoạn đem nhúng: tiêu đề, mô tả, rồi đầu bài — phần nói bài giải quyết vấn đề gì."""
        dong = [self.title, self.description, chu_tron(noi_dung)]
        return "\n".join(d for d in dong if d)[: get_settings().wiki_embed_chars]


def _thoi_diem(chu: str) -> dt.datetime:
    return dt.datetime.fromisoformat(chu.replace("Z", "+00:00"))


def doc_danh_sach(hoi: HoiWiki) -> list[Bai]:
    """Bài đã xuất bản, không riêng tư — đúng phần mọi nhân viên đọc được trên wiki."""
    d = hoi(
        "{ pages { list(orderBy: ID) { id path locale title description isPublished isPrivate updatedAt } } }",
        None,
    )
    return [
        Bai(
            page_id=p["id"],
            path=p["path"],
            locale=p["locale"],
            title=p.get("title") or p["path"],
            description=p.get("description") or "",
            updated_at=_thoi_diem(p["updatedAt"]),
        )
        for p in d["pages"]["list"]
        if p["isPublished"] and not p["isPrivate"]
    ]


def quet_kho_tri_thuc(
    phien: Session, hoi: HoiWiki = hoi_wiki, doc: DocNoiDung | None = None, mo_phien: MoPhien = _mo_phien_that
) -> int:
    """Một lượt của bộ lập chỉ mục. `phien` giữ khóa tư vấn của lượt (`nhip_quet.py`). Trả số bài đã
    ghi hay xóa khỏi chỉ mục. Kho tri thức hay mô hình nhúng không dùng được: bỏ lượt, không ném lỗi —
    nhịp vẫn ghi lượt thành công, vì bộ quét không hỏng, chỉ không có gì để làm."""
    cau_hinh = get_settings()
    if not (cau_hinh.wiki_enabled and cau_hinh.embedding_enabled):
        return 0
    try:
        cac_bai = doc_danh_sach(hoi)
    except LoiKhoTriThuc as loi:
        log.warning("Bộ lập chỉ mục kho tri thức bỏ lượt: %s", loi)
        return 0

    da_co = {
        r[0]: (r[1], r[2])
        for r in phien.execute(text("SELECT page_id, wiki_updated_at, model FROM knowledge_articles")).all()
    }
    con = {b.page_id for b in cac_bai}
    bo = [ma for ma in da_co if ma not in con]
    if bo:
        # Cùng giao dịch của lượt: `chay_luot_quet` commit lúc lượt xong, cùng lúc ghi nhịp
        phien.execute(text("DELETE FROM knowledge_articles WHERE page_id = ANY(:ma)"), {"ma": bo})

    can = [
        b
        for b in cac_bai
        if b.page_id not in da_co or da_co[b.page_id] != (b.updated_at, cau_hinh.embedding_model)
    ][: cau_hinh.wiki_index_batch_size]
    if not can:
        return len(bo)

    try:
        noi_dung = [(doc or doc_noi_dung)(b) for b in can]
        vec = mo_hinh.hoi_nhung([b.doan_nhung(c) for b, c in zip(can, noi_dung, strict=True)])
    except (LoiKhoTriThuc, mo_hinh.LoiMoHinh) as loi:
        log.warning("Bộ lập chỉ mục kho tri thức bỏ lượt: %s", loi)
        return len(bo)

    with mo_phien() as ghi:
        for b, c, v in zip(can, noi_dung, vec, strict=True):
            ghi.execute(
                text(
                    """
                    INSERT INTO knowledge_articles (page_id, path, locale, title, description, excerpt,
                        wiki_updated_at, model, embedding, indexed_at)
                    VALUES (:ma, :duong, :ngon_ngu, :tieu_de, :mo_ta, :doan, :luc, :mo_hinh,
                        CAST(:vec AS vector), now())
                    ON CONFLICT (page_id) DO UPDATE SET path = EXCLUDED.path, locale = EXCLUDED.locale,
                        title = EXCLUDED.title, description = EXCLUDED.description,
                        excerpt = EXCLUDED.excerpt, wiki_updated_at = EXCLUDED.wiki_updated_at,
                        model = EXCLUDED.model, embedding = EXCLUDED.embedding, indexed_at = now()
                    """
                ),
                {
                    "ma": b.page_id,
                    "duong": b.path,
                    "ngon_ngu": b.locale,
                    "tieu_de": b.title,
                    "mo_ta": b.description or None,
                    "doan": chu_tron(c)[:DO_DAI_DOAN_DAU] or None,
                    "luc": b.updated_at,
                    "mo_hinh": cau_hinh.embedding_model,
                    "vec": "[" + ",".join(f"{x:.7g}" for x in v) + "]",
                },
            )
        ghi.commit()
    log.info("Kho tri thức: đã lập chỉ mục %d bài, bỏ %d bài", len(can), len(bo))
    return len(can) + len(bo)


# ---------------------------------------------------------------------------
# Tìm
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BaiTimThay:
    title: str
    description: str | None
    excerpt: str | None
    url: str
    score: float


def dia_chi_bai(duong_dan: str) -> str:
    """Đường dẫn mở bài trên wiki. Người chưa đăng nhập wiki tự đi qua Keycloak rồi quay về đúng bài —
    bước khởi tạo bật tự đăng nhập (`authAutoLogin`) của Wiki.js."""
    goc = get_settings().wiki_public_url.rstrip("/")
    return f"{goc}/{urllib.parse.quote(duong_dan)}"


def tim_bai(session: Session, vec: list[float], *, so_ket_qua: int | None = None,
            nguong: float | None = None) -> list[BaiTimThay]:
    """Bài gần nhất với véc-tơ câu hỏi đã nhúng. Kho tri thức tắt thì không tìm."""
    cau_hinh = get_settings()
    if not cau_hinh.wiki_enabled:
        return []
    dong = session.execute(
        text(
            """
            SELECT path, title, description, excerpt, 1 - (embedding <=> CAST(:vec AS vector)) AS diem
            FROM knowledge_articles
            WHERE model = :mo_hinh AND vector_dims(embedding) = :so_chieu
            ORDER BY embedding <=> CAST(:vec AS vector), page_id
            LIMIT :k
            """
        ),
        {
            "vec": "[" + ",".join(f"{x:.7g}" for x in vec) + "]",
            "mo_hinh": cau_hinh.embedding_model,
            "so_chieu": len(vec),
            "k": so_ket_qua if so_ket_qua is not None else cau_hinh.wiki_max_results,
        },
    ).all()
    san = nguong if nguong is not None else cau_hinh.wiki_min_score
    return [
        BaiTimThay(title=d[1], description=d[2], excerpt=d[3], url=dia_chi_bai(d[0]), score=float(d[4]))
        for d in dong
        if float(d[4]) >= san
    ]
