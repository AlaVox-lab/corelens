# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Hồ sơ đã giải quyết tương tự (#319, ADR-0008 đợt 2).
#
# BA VIỆC
#
# 1. LẬP CHỈ MỤC hồ sơ ĐÃ ĐÓNG ĐẠT — người gửi xác nhận đạt. Nhận ra bằng bộ quy tắc, không mã trạng
#    thái nào: sự kiện cuối của hồ sơ đi một cạnh của NGƯỜI, vào trạng thái kết thúc, xuất phát từ trạng
#    thái mà bước chính của người được giao dẫn tới (`primary_scope = 'assignee'`, #227 — "Hoàn thành xử
#    lý" dẫn tới *Hoàn tất*, từ đó người gửi "Xác nhận đạt"). Tự đóng vì quá hạn chờ là cạnh hệ thống —
#    không tính; hủy không xuất phát từ trạng thái đó — không tính.
#    Mỗi hồ sơ: tiêu đề, mô tả, loại, và cách giải quyết = ghi chú của bước chính người được giao cộng
#    lời nhắn cuối người gửi thấy được của phía xử lý (không bao giờ lời nhắn nội bộ). Tên người và
#    thông tin liên hệ bị ẩn NGAY LÚC GHI — bảng chỉ mục không giữ chúng. Véc-tơ nhúng phần mô tả vấn
#    đề (tiêu đề, mô tả, loại) — cùng bản chất với câu người gửi đang gõ.
#    Bộ lập chỉ mục bù `similar-index` theo khuôn `app/workflow/nhip_quet.py` tự nhặt hồ sơ mới đóng
#    đạt, hồ sơ đóng lại sau khi mở lại, và hồ sơ nhúng bằng mô hình cũ.
#
# 2. TÌM cho biểu mẫu Gửi yêu cầu: nhúng câu đang gõ (kèm lời dặn tác vụ của Qwen3-Embedding), quét
#    chính xác bằng khoảng cách cosine của pgvector, tối đa `similar_max_results` hồ sơ trên ngưỡng.
#    Hạn chót ngắn; mô hình tắt, chậm, hỏng — trả danh sách rỗng, không báo lỗi.
#
# 3. GHI NHẬN: phiên soạn đã thấy gợi ý (`similar_case_views`), phiên đó có gửi hồ sơ không, hay bỏ
#    không gửi — người gửi bấm "không gửi nữa", hoặc quá `similar_abandon_after_minutes` mà không gửi.
#    Bỏ không gửi là một yêu cầu được ngăn chặn; view `bao_cao_ngan_chan` đưa tỷ lệ lên bảng điều khiển.
#
# Tầng I chỉ ghi hai bảng riêng của nó, không chạm hồ sơ hay trường quyết định nào (CLAUDE.md mục 4.3).

from __future__ import annotations

import datetime as dt
import logging
import re
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor
from app.config import get_settings
from app.db import get_session
from app.intelligence import mo_hinh, tri_thuc
from app.workflow.context import Actor

log = logging.getLogger(__name__)

TEN_BO_QUET_TUONG_TU = "similar-index"
NHAN_BO_QUET_TUONG_TU = "Bộ lập chỉ mục hồ sơ tương tự"

# Lý do bỏ không gửi — từ vựng của bảng `similar_case_views`
BO_NGUOI_GUI = "requester"
BO_HET_GIO = "timeout"

# Giá trị `transitions.primary_scope` của bước chính do người được giao đi (#227)
PHAM_VI_NGUOI_DUOC_GIAO = "assignee"

DO_DAI_CACH_GIAI_QUYET = 600
DO_DAI_MO_TA = 600

MoPhien = Callable[[], AbstractContextManager[Session]]


def _mo_phien_that() -> AbstractContextManager[Session]:
    from app.db import SessionLocal

    return SessionLocal()


# ---------------------------------------------------------------------------
# Ẩn tên người và thông tin liên hệ
# ---------------------------------------------------------------------------

AN_EMAIL = "[email đã ẩn]"
AN_SO_DIEN_THOAI = "[số điện thoại đã ẩn]"
AN_TEN = "[tên đã ẩn]"

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.UNICODE)
# Số Việt Nam: 0 hay +84 rồi 8–10 chữ số, cho phép cách bằng dấu cách, chấm, gạch
_SO_DIEN_THOAI = re.compile(r"(?<![\w+])(?:\+84|0)(?:[\s.\-]?\d){8,10}(?!\d)")
# Từ xưng hô đứng trước tên riêng — "anh Cường", "chị Mai". Từ vựng tiếng Việt, không phải nghiệp vụ
_XUNG_HO = r"(?:anh|chị|em|bạn|ông|bà|cô|chú|thầy|cậu|bác)"


def an_lien_he(van_ban: str) -> str:
    return _SO_DIEN_THOAI.sub(AN_SO_DIEN_THOAI, _EMAIL.sub(AN_EMAIL, van_ban))


def an_danh(van_ban: str | None, ten_nguoi: frozenset[str]) -> str:
    """Ẩn email, số điện thoại và tên người. `ten_nguoi` là tên đầy đủ của những người hệ thống biết
    (người gửi, người xử lý, người thao tác, người nhắn — tên lấy từ danh bạ lúc họ thao tác). Thay cả
    tên đầy đủ lẫn tên gọi đứng sau từ xưng hô ("anh Cường"); tên một chữ đứng một mình thì không, vì
    trùng chữ thường quá nhiều ("An", "Bình")."""
    if not van_ban:
        return ""
    ra = an_lien_he(van_ban)
    for ten in sorted(ten_nguoi, key=len, reverse=True):
        ra = re.sub(rf"(?<!\w){re.escape(ten)}(?!\w)", AN_TEN, ra, flags=re.IGNORECASE)
    ten_goi = {ten.split()[-1] for ten in ten_nguoi}
    if ten_goi:
        nhom = "|".join(re.escape(t) for t in sorted(ten_goi, key=len, reverse=True))
        ra = re.sub(
            rf"(?<!\w)({_XUNG_HO})\s+(?:{nhom})(?!\w)", rf"\1 {AN_TEN}", ra, flags=re.IGNORECASE
        )
    return ra


def ten_nguoi_da_biet(phien: Session) -> frozenset[str]:
    """Tên đầy đủ (từ hai chữ trở lên) của mọi người từng xuất hiện trên hồ sơ. Tên của cạnh hệ thống
    không tính — "Hệ thống" không phải tên người."""
    dong = phien.execute(
        text(
            """
            SELECT requester_label FROM requests
            UNION SELECT assignee_label FROM requests
            UNION SELECT author_label FROM case_messages
            UNION SELECT e.actor_label FROM event_log e
                JOIN requests r ON r.id = e.case_id
                JOIN transitions t ON t.rule_set_id = r.rule_set_id AND t.from_state = e.from_state
                    AND t.to_state = e.to_state AND t.activity_code = e.activity
                WHERE NOT t.is_system
            """
        )
    ).scalars()
    return frozenset(t.strip() for t in dong if t and len(t.split()) >= 2)


# ---------------------------------------------------------------------------
# Lập chỉ mục
# ---------------------------------------------------------------------------

# Hồ sơ đóng đạt cần (lại) lập chỉ mục: chưa có, nhúng bằng mô hình khác, hay đã đóng lại sau lần ghi
_SQL_CAN_LAP = """
WITH canh_xong AS (
    SELECT DISTINCT rule_set_id, to_state FROM transitions
    WHERE primary_scope = :pham_vi AND NOT is_system
), canh_dat AS (
    SELECT t.rule_set_id, t.from_state, t.to_state, t.activity_code
    FROM transitions t
    JOIN canh_xong x ON x.rule_set_id = t.rule_set_id AND x.to_state = t.from_state
    JOIN states s ON s.rule_set_id = t.rule_set_id AND s.code = t.to_state AND s.is_terminal
    WHERE NOT t.is_system
), cuoi AS (
    SELECT DISTINCT ON (e.case_id) e.case_id, e.activity, e.from_state, e.to_state, e.timestamp
    FROM event_log e
    JOIN requests r ON r.id = e.case_id
    JOIN states s ON s.rule_set_id = r.rule_set_id AND s.code = r.current_state AND s.is_terminal
    ORDER BY e.case_id, e.timestamp DESC, e.id DESC
)
SELECT r.id, cuoi.timestamp
FROM requests r
JOIN cuoi ON cuoi.case_id = r.id
JOIN canh_dat c ON c.rule_set_id = r.rule_set_id AND c.from_state = cuoi.from_state
    AND c.to_state = cuoi.to_state AND c.activity_code = cuoi.activity
LEFT JOIN similar_case_index i ON i.case_id = r.id
WHERE i.case_id IS NULL OR i.model <> :mo_hinh OR i.closed_at < cuoi.timestamp
ORDER BY cuoi.timestamp, r.id
LIMIT :gioi_han
"""

# Ghi chú của bước chính người được giao, rồi lời nhắn người gửi thấy được của phía xử lý — mới nhất
_SQL_CACH_GIAI_QUYET = """
SELECT * FROM (
    SELECT 1 AS thu_tu, e.note AS chu, e.timestamp AS luc
    FROM event_log e
    JOIN requests r ON r.id = e.case_id
    JOIN transitions t ON t.rule_set_id = r.rule_set_id AND t.from_state = e.from_state
        AND t.to_state = e.to_state AND t.activity_code = e.activity
    WHERE e.case_id = :ma AND t.primary_scope = :pham_vi AND NOT t.is_system
        AND coalesce(btrim(e.note), '') <> ''
    ORDER BY e.timestamp DESC, e.id DESC LIMIT 1
) a
UNION ALL
SELECT * FROM (
    SELECT 2, m.body, m.created_at
    FROM case_messages m
    JOIN requests r ON r.id = m.case_id
    JOIN message_kinds k ON k.code = m.kind
    WHERE m.case_id = :ma AND NOT k.hidden_from_requester AND m.author <> r.requester_id
        AND coalesce(btrim(m.body), '') <> ''
    ORDER BY m.created_at DESC, m.id DESC LIMIT 1
) b
ORDER BY thu_tu
"""


@dataclass(frozen=True)
class TaiLieu:
    case_id: int
    title: str
    description: str
    request_type_code: str | None
    request_type_label: str | None
    resolution: str
    closed_at: dt.datetime

    def doan_nhung(self) -> str:
        """Đoạn đem nhúng: phần mô tả vấn đề — cùng bản chất với câu người gửi đang gõ."""
        dong = [self.title]
        if self.description:
            dong.append(self.description)
        if self.request_type_label:
            dong.append(f"Loại: {self.request_type_label}")
        return "\n".join(dong)


def _cat(chu: str, do_dai: int) -> str:
    chu = " ".join(chu.split())
    return chu if len(chu) <= do_dai else chu[: do_dai - 1].rstrip() + "…"


def doc_tai_lieu(
    phien: Session, ma_ho_so: int, dong_luc: dt.datetime, ten_nguoi: frozenset[str]
) -> TaiLieu:
    dong = phien.execute(
        text(
            "SELECT r.title, r.description, r.request_type_code, t.label FROM requests r"
            " LEFT JOIN request_types t ON t.code = r.request_type_code WHERE r.id = :ma"
        ),
        {"ma": ma_ho_so},
    ).one()
    cach = [
        c
        for (_, c, _) in phien.execute(
            text(_SQL_CACH_GIAI_QUYET), {"ma": ma_ho_so, "pham_vi": PHAM_VI_NGUOI_DUOC_GIAO}
        ).all()
    ]
    # Ghi chú hoàn thành và lời nhắn cuối thường nói cùng một chuyện — bỏ bản trùng
    cach = list(dict.fromkeys(" ".join(c.split()) for c in cach))
    return TaiLieu(
        case_id=ma_ho_so,
        title=_cat(an_danh(dong[0], ten_nguoi), 300),
        description=_cat(an_danh(dong[1], ten_nguoi), DO_DAI_MO_TA),
        request_type_code=dong[2],
        request_type_label=dong[3],
        resolution=_cat(an_danh("\n".join(cach), ten_nguoi), DO_DAI_CACH_GIAI_QUYET),
        closed_at=dong_luc,
    )


def _chu_vec(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.7g}" for x in vec) + "]"


def ho_so_can_lap(phien: Session, gioi_han: int) -> list[tuple[int, dt.datetime]]:
    return [
        (r[0], r[1])
        for r in phien.execute(
            text(_SQL_CAN_LAP),
            {
                "pham_vi": PHAM_VI_NGUOI_DUOC_GIAO,
                "mo_hinh": get_settings().embedding_model,
                "gioi_han": gioi_han,
            },
        ).all()
    ]


def lap_chi_muc(cac_ho_so: list[tuple[int, dt.datetime]], mo_phien: MoPhien = _mo_phien_that) -> int:
    """Nhúng và ghi một lô hồ sơ. Ba bước như `phan_loai.py`: đọc (giao dịch ngắn), hỏi mô hình (không
    giữ gì của cơ sở dữ liệu), ghi (giao dịch ngắn). Ném `LoiMoHinh` khi mô hình không dùng được."""
    if not cac_ho_so:
        return 0
    with mo_phien() as phien:
        ten = ten_nguoi_da_biet(phien)
        tai_lieu = [doc_tai_lieu(phien, ma, luc, ten) for ma, luc in cac_ho_so]
        phien.rollback()

    vec = mo_hinh.hoi_nhung([t.doan_nhung() for t in tai_lieu])

    cau_hinh = get_settings()
    with mo_phien() as phien:
        for t, v in zip(tai_lieu, vec, strict=True):
            phien.execute(
                text(
                    """
                    INSERT INTO similar_case_index (case_id, title, description, request_type_code,
                        resolution, closed_at, model, embedding, updated_at)
                    VALUES (:ma, :tieu_de, :mo_ta, :loai, :cach, :dong, :mo_hinh,
                        CAST(:vec AS vector), now())
                    ON CONFLICT (case_id) DO UPDATE SET title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        request_type_code = EXCLUDED.request_type_code,
                        resolution = EXCLUDED.resolution, closed_at = EXCLUDED.closed_at,
                        model = EXCLUDED.model, embedding = EXCLUDED.embedding, updated_at = now()
                    """
                ),
                {
                    "ma": t.case_id,
                    "tieu_de": t.title,
                    "mo_ta": t.description or None,
                    "loai": t.request_type_code,
                    "cach": t.resolution or None,
                    "dong": t.closed_at,
                    "mo_hinh": cau_hinh.embedding_model,
                    "vec": _chu_vec(v),
                },
            )
        phien.commit()
    return len(tai_lieu)


def danh_dau_bo_khong_gui(phien: Session) -> int:
    """Phiên đã xem gợi ý mà quá hạn chờ không gửi hồ sơ: tính là bỏ không gửi."""
    phut = get_settings().similar_abandon_after_minutes
    return phien.execute(
        text(
            "UPDATE similar_case_views SET abandoned_at = now(), abandon_reason = :ly_do"
            " WHERE submitted_case_id IS NULL AND abandoned_at IS NULL"
            " AND viewed_at < now() - make_interval(mins => :phut)"
        ),
        {"ly_do": BO_HET_GIO, "phut": phut},
    ).rowcount


def quet_chi_muc(phien: Session, mo_phien: MoPhien = _mo_phien_that) -> int:
    """Một lượt của bộ lập chỉ mục bù. `phien` giữ khóa tư vấn của lượt (`nhip_quet.py`). Đánh dấu phiên
    bỏ không gửi luôn chạy; lập chỉ mục chỉ khi mô hình nhúng bật. Trả số hồ sơ đã ghi vào chỉ mục."""
    danh_dau_bo_khong_gui(phien)
    cau_hinh = get_settings()
    if not cau_hinh.embedding_enabled:
        return 0
    lo = ho_so_can_lap(phien, cau_hinh.similar_index_batch_size)
    try:
        so = lap_chi_muc(lo, mo_phien)
    except mo_hinh.LoiMoHinh as loi:
        # Mô hình không dùng được: lượt sau thử lại cả lô, không đánh dấu gì trên hồ sơ
        log.warning("Bộ lập chỉ mục hồ sơ tương tự bỏ lượt: %s", loi)
        return 0
    if so:
        log.info("Đã lập chỉ mục %d hồ sơ đã giải quyết", so)
    return so


# ---------------------------------------------------------------------------
# Tìm
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KetQuaTuongTu:
    case_id: int
    title: str
    request_type_label: str | None
    resolution: str
    closed_at: dt.datetime
    score: float


def cau_hoi(tieu_de: str, mo_ta: str | None) -> str:
    """Câu đem nhúng cho một lần tìm: lời dặn tác vụ kèm nội dung, theo định dạng của Qwen3-Embedding."""
    noi_dung = "\n".join(p for p in (tieu_de.strip(), (mo_ta or "").strip()) if p)
    return f"Instruct: {get_settings().embedding_query_instruction}\nQuery: {noi_dung}"


def tim(
    session: Session,
    tieu_de: str,
    mo_ta: str | None,
    *,
    han_giay: float | None = None,
    so_ket_qua: int | None = None,
    nguong: float | None = None,
) -> list[KetQuaTuongTu]:
    """Hồ sơ đã giải quyết gần nhất với nội dung đang soạn. Ném `LoiMoHinh` khi không nhúng được —
    phía gọi của biểu mẫu đổi nó thành danh sách rỗng."""
    return tim_theo_vec(session, nhung_cau_hoi(tieu_de, mo_ta, han_giay), so_ket_qua=so_ket_qua, nguong=nguong)


def nhung_cau_hoi(tieu_de: str, mo_ta: str | None, han_giay: float | None = None) -> list[float]:
    """Véc-tơ của nội dung đang soạn — một lần nhúng dùng cho cả hồ sơ tương tự lẫn bài kho tri thức (#321)."""
    han = han_giay if han_giay is not None else get_settings().similar_timeout_seconds
    return mo_hinh.hoi_nhung([cau_hoi(tieu_de, mo_ta)], han_giay=han)[0]


def tim_theo_vec(
    session: Session, vec: list[float], *, so_ket_qua: int | None = None, nguong: float | None = None
) -> list[KetQuaTuongTu]:
    cau_hinh = get_settings()
    dong = session.execute(
        text(
            """
            SELECT i.case_id, i.title, t.label, i.resolution, i.closed_at,
                   1 - (i.embedding <=> CAST(:vec AS vector)) AS diem
            FROM similar_case_index i
            JOIN requests r ON r.id = i.case_id
            JOIN states s ON s.rule_set_id = r.rule_set_id AND s.code = r.current_state
                AND s.is_terminal
            LEFT JOIN request_types t ON t.code = i.request_type_code
            WHERE i.model = :mo_hinh AND vector_dims(i.embedding) = :so_chieu
            ORDER BY i.embedding <=> CAST(:vec AS vector), i.case_id
            LIMIT :k
            """
        ),
        {
            "vec": _chu_vec(vec),
            "mo_hinh": cau_hinh.embedding_model,
            "so_chieu": len(vec),
            "k": so_ket_qua if so_ket_qua is not None else cau_hinh.similar_max_results,
        },
    ).all()
    san = nguong if nguong is not None else cau_hinh.similar_min_score
    return [
        KetQuaTuongTu(
            case_id=d[0],
            title=an_lien_he(d[1]),
            request_type_label=d[2],
            resolution=an_lien_he(d[3] or ""),
            closed_at=d[4],
            score=float(d[5]),
        )
        for d in dong
        if float(d[5]) >= san
    ]


# ---------------------------------------------------------------------------
# Ghi nhận xem, gửi, bỏ không gửi
# ---------------------------------------------------------------------------


def ghi_da_xem(session: Session, phien_soan: uuid.UUID, nguoi_gui: str, ket_qua: list[KetQuaTuongTu]) -> None:
    """Một phiên soạn vừa thấy gợi ý. Cùng phiên xem nhiều lần (người gửi gõ tiếp) thì cộng số lần
    và giữ danh sách gợi ý mới nhất. Phiên của người khác thì không đụng."""
    ma = [k.case_id for k in ket_qua]
    session.execute(
        text(
            """
            INSERT INTO similar_case_views (session_id, requester_id, suggested_case_ids, top_case_id)
            VALUES (:phien, :nguoi, :ma, :dau)
            ON CONFLICT (session_id) DO UPDATE SET view_count = similar_case_views.view_count + 1,
                suggested_case_ids = EXCLUDED.suggested_case_ids,
                top_case_id = EXCLUDED.top_case_id
            WHERE similar_case_views.requester_id = EXCLUDED.requester_id
                AND similar_case_views.submitted_case_id IS NULL
                AND similar_case_views.abandoned_at IS NULL
            """
        ),
        {"phien": phien_soan, "nguoi": nguoi_gui, "ma": ma, "dau": ma[0] if ma else None},
    )


def ghi_da_gui(session: Session, phien_soan: uuid.UUID | None, nguoi_gui: str, ma_ho_so: int) -> None:
    """Phiên soạn đã thấy gợi ý mà vẫn gửi hồ sơ. Không có phiên, hay phiên chưa từng thấy gợi ý: không
    ghi gì. Gửi sau khi đã bị tính là bỏ không gửi vì quá hạn thì sửa lại thành đã gửi — người gửi chỉ
    soạn lâu, không phải được ngăn chặn."""
    if phien_soan is None:
        return
    session.execute(
        text(
            "UPDATE similar_case_views SET submitted_case_id = :ma, abandoned_at = NULL,"
            " abandon_reason = NULL"
            " WHERE session_id = :phien AND requester_id = :nguoi AND submitted_case_id IS NULL"
            " AND abandon_reason IS DISTINCT FROM :nguoi_bo"
        ),
        {"ma": ma_ho_so, "phien": phien_soan, "nguoi": nguoi_gui, "nguoi_bo": BO_NGUOI_GUI},
    )


def ghi_bo_khong_gui(session: Session, phien_soan: uuid.UUID, nguoi_gui: str) -> bool:
    return bool(
        session.execute(
            text(
                "UPDATE similar_case_views SET abandoned_at = now(), abandon_reason = :ly_do"
                " WHERE session_id = :phien AND requester_id = :nguoi"
                " AND submitted_case_id IS NULL"
            ),
            {"ly_do": BO_NGUOI_GUI, "phien": phien_soan, "nguoi": nguoi_gui},
        ).rowcount
    )


# ---------------------------------------------------------------------------
# Điểm cuối cho biểu mẫu Gửi yêu cầu
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/similar-cases", tags=["Hồ sơ tương tự"])


class TimTuongTuVao(BaseModel):
    title: str = Field(default="", max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    # Mã phiên soạn do biểu mẫu sinh, để nối "đã xem" với "đã gửi" hay "bỏ không gửi"
    session_id: uuid.UUID | None = None


class HoSoTuongTuRa(BaseModel):
    title: str
    request_type: str | None
    resolution: str
    closed_at: dt.datetime
    score: float


class BaiTriThucRa(BaseModel):
    """Một bài của kho tri thức (#321), mở trên wiki bằng `url`."""

    title: str
    description: str | None
    excerpt: str | None
    url: str
    score: float


class TimTuongTuRa(BaseModel):
    items: list[HoSoTuongTuRa]
    # Bài kho tri thức gần với nội dung đang soạn (#321); rỗng khi kho tri thức tắt
    articles: list[BaiTriThucRa] = Field(default_factory=list)
    # Tên, giấy phép và mã nguồn của nền tảng kho tri thức (AGPL-3.0), để biểu mẫu ghi cạnh bài gợi ý
    articles_source_url: str | None = None
    # Mô hình nhúng tắt — biểu mẫu khỏi gọi nữa trong phiên này
    enabled: bool


class BoKhongGuiVao(BaseModel):
    session_id: uuid.UUID


# Câu quá ngắn chưa đủ nghĩa để so — đỡ một lần gọi mô hình cho mỗi phím gõ đầu tiên
SO_KY_TU_TOI_THIEU = 12


@router.post("/search", response_model=TimTuongTuRa)
def tim_cho_bieu_mau(
    du_lieu: TimTuongTuVao,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[Actor, Depends(current_actor)],
) -> TimTuongTuRa:
    """Tối đa ba hồ sơ đã giải quyết tương tự nội dung đang soạn (#319), đã ẩn tên người và liên hệ, và
    — khi kho tri thức bật (#321) — vài bài hướng dẫn gần nhất, cùng một lần nhúng.

    KHÔNG BAO GIỜ báo lỗi cho biểu mẫu: mô hình tắt, chậm hơn hạn, trả rác — đều là danh sách rỗng, để
    người gửi không chờ và không thấy gì lạ. Bài kho tri thức đọc từ chỉ mục trong cơ sở dữ liệu, không gọi
    sang wiki, nên wiki tắt hay chậm không làm chậm biểu mẫu. Có hồ sơ gợi ý và có mã phiên thì ghi một lượt
    xem (đo ngăn chặn theo hồ sơ như #319).
    """
    cau_hinh = get_settings()
    if not cau_hinh.embedding_enabled:
        return TimTuongTuRa(items=[], enabled=False)
    noi_dung = f"{du_lieu.title} {du_lieu.description or ''}".strip()
    if len(noi_dung) < SO_KY_TU_TOI_THIEU:
        return TimTuongTuRa(items=[], enabled=True)
    try:
        vec = nhung_cau_hoi(du_lieu.title, du_lieu.description)
    except mo_hinh.LoiMoHinh as loi:
        log.info("Không tìm được hồ sơ tương tự: %s", loi)
        return TimTuongTuRa(items=[], enabled=True)
    ket_qua = tim_theo_vec(session, vec)
    bai = tri_thuc.tim_bai(session, vec)
    if ket_qua and du_lieu.session_id is not None:
        try:
            ghi_da_xem(session, du_lieu.session_id, actor.id, ket_qua)
            session.commit()
        except Exception:  # noqa: BLE001 — ghi nhận hỏng không được làm mất gợi ý
            session.rollback()
            log.exception("Không ghi được lượt xem gợi ý tương tự")
    return TimTuongTuRa(
        items=[
            HoSoTuongTuRa(
                title=k.title,
                request_type=k.request_type_label,
                resolution=k.resolution,
                closed_at=k.closed_at,
                score=round(k.score, 3),
            )
            for k in ket_qua
        ],
        articles=[
            BaiTriThucRa(title=b.title, description=b.description, excerpt=b.excerpt, url=b.url,
                         score=round(b.score, 3))
            for b in bai
        ],
        articles_source_url=cau_hinh.wiki_source_url if bai else None,
        enabled=True,
    )


@router.post("/abandon", status_code=204)
def bo_khong_gui(
    du_lieu: BoKhongGuiVao,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[Actor, Depends(current_actor)],
) -> None:
    """Người gửi bấm "Đã giải quyết được, không gửi nữa" sau khi xem gợi ý — một yêu cầu được ngăn
    chặn. Phiên không có, của người khác, hay đã gửi rồi: không ghi gì, vẫn 204."""
    ghi_bo_khong_gui(session, du_lieu.session_id, actor.id)
    session.commit()
