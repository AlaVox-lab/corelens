# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Cập nhật thời gian thực cho cổng người dùng (#387).
#
#     GET /me/stream   → text/event-stream
#
# Server-Sent Events chứ không WebSocket: cổng chỉ cần nhận, không cần gửi ngược trên cùng kết nối; SSE là
# HTTP thường nên đi qua cổng API (APISIX) và máy chủ Next.js mà không thêm dịch vụ, gói hay cổng mạng nào,
# và trình duyệt tự nối lại khi luồng đứt.
#
# Đường đi của một tín hiệu:
#
#   1. Hồ sơ đổi hay có lời nhắn mới → trigger của bản sửa 0029 gửi `pg_notify('ho_so_thay_doi', <mã>)`
#      khi giao dịch commit. Mã ghi hồ sơ không biết gì về việc này.
#   2. Mỗi luồng mở đang `LISTEN` trên một kết nối bất đồng bộ riêng của psycopg — không chiếm luồng
#      xử lý nào của máy chủ trong lúc chờ.
#   3. Nhận được mã thì kiểm người giữ luồng có mở được hồ sơ đó không, bằng ĐÚNG luật cửa của hộp thư
#      (`_Cua.noi_mo`): người gửi của hồ sơ, phòng ban của hồ sơ, điều phối viên. Không mở được thì bỏ qua —
#      người khác không biết được hồ sơ nào vừa đổi.
#   4. Đẩy khung `event: ho-so` chỉ mang mã hồ sơ. Cổng nhận được thì tự tải lại phần máy chủ của trang qua
#      các điểm cuối sẵn có, nên quyền xem nội dung vẫn do chính các điểm cuối đó quyết.
#
# Luồng tự đóng sau `realtime_max_stream_seconds`: trình duyệt nối lại, cổng API và dịch vụ kiểm lại token
# mới — không luồng nào sống lâu hơn token đã mở nó. Số luồng đồng thời có trần (`realtime_max_streams`), quá
# trần trả 503 và cổng quay về hỏi định kỳ như trước #387.

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor
from app.config import get_settings
from app.db import SessionLocal, get_session
from app.models.case import Request
from app.workflow.context import Actor
from app.workflow.inbox import _Cua

log = logging.getLogger(__name__)

router = APIRouter(prefix="/me", tags=["Thời gian thực"])

# Trùng tên kênh trong bản sửa 0029_bao_thay_doi_ho_so
KENH = "ho_so_thay_doi"

# Nguồn tín hiệu: nhận hạn chờ (giây), trả các mã hồ sơ tới trong khoảng đó — rỗng khi hết hạn mà không có
# gì. Kiểm thử thay bằng nguồn giả, không cần commit thật vào cơ sở dữ liệu.
NguonTinHieu = Callable[[float], Awaitable[list[int]]]

_so_luong_dang_mo = 0


def khung(su_kien: str, du_lieu: dict) -> str:
    """Một khung SSE: tên sự kiện và một dòng dữ liệu JSON, kết thúc bằng dòng trống."""
    return f"event: {su_kien}\ndata: {json.dumps(du_lieu, ensure_ascii=False)}\n\n"


def mo_duoc(session: Session, actor: Actor, case_id: int) -> bool:
    """Người này có mở được hồ sơ không — cùng luật với hộp thư chung (#155)."""
    ho_so = session.get(Request, case_id)
    return ho_so is not None and _Cua(session, actor).noi_mo(ho_so) is not None


def _loc_theo_quyen(actor: Actor, cac_ma: list[int]) -> list[int]:
    """Giữ những mã người này mở được, theo thứ tự tới, bỏ trùng. Chạy trong luồng phụ: truy vấn đồng bộ."""
    with SessionLocal() as session:
        return [ma for ma in dict.fromkeys(cac_ma) if mo_duoc(session, actor, ma)]


def _dia_chi_psycopg() -> str:
    """Địa chỉ SQLAlchemy `postgresql+psycopg://…` đổi về dạng psycopg đọc được."""
    return get_settings().database_uri.replace("postgresql+psycopg://", "postgresql://", 1)


async def _mo_nguon_postgres() -> tuple[psycopg.AsyncConnection, NguonTinHieu]:
    ket_noi = await psycopg.AsyncConnection.connect(_dia_chi_psycopg(), autocommit=True)
    await ket_noi.execute(f"LISTEN {KENH}")

    async def cho(han_giay: float) -> list[int]:
        cac_ma: list[int] = []
        # Lấy tín hiệu đầu tiên trong hạn chờ, rồi vét nốt những tín hiệu tới cùng lúc mà không chờ thêm
        async for tb in ket_noi.notifies(timeout=han_giay, stop_after=1):
            cac_ma.append(tb.payload)
        if cac_ma:
            async for tb in ket_noi.notifies(timeout=0.05):
                cac_ma.append(tb.payload)
        return [int(ma) for ma in cac_ma if ma.isdigit()]

    return ket_noi, cho


async def phat_luong(
    actor: Actor,
    nguon: NguonTinHieu,
    *,
    nhip_giu_giay: float,
    han_doi_giay: float,
    loc: Callable[[Actor, list[int]], list[int]] = _loc_theo_quyen,
) -> AsyncIterator[str]:
    """Các khung gửi cho một người: chào, tín hiệu hồ sơ họ mở được, dòng giữ kết nối; dừng khi hết hạn đời."""
    # `retry`: trình duyệt chờ 3 giây trước khi nối lại sau khi luồng đóng
    yield "retry: 3000\n" + khung("san-sang", {})
    het_han = time.monotonic() + han_doi_giay
    while (con_lai := het_han - time.monotonic()) > 0:
        cac_ma = await nguon(min(nhip_giu_giay, con_lai))
        if not cac_ma:
            # Dòng chú thích: trình duyệt bỏ qua, nhưng proxy thấy kết nối còn sống
            yield ": giu-ket-noi\n\n"
            continue
        for ma in await run_in_threadpool(loc, actor, cac_ma):
            yield khung("ho-so", {"case_id": ma})


@router.get(
    "/stream",
    summary="Luồng tín hiệu hồ sơ vừa đổi (Server-Sent Events)",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}, 503: {"description": "Đủ số luồng đồng thời"}},
)
async def luong_thay_doi(
    actor: Annotated[Actor, Depends(current_actor)],
    session: Annotated[Session, Depends(get_session)],
) -> StreamingResponse:
    """Đẩy `event: ho-so` mang `case_id` mỗi khi một hồ sơ người gọi mở được vừa đổi hay có lời nhắn mới.

    Chỉ là tín hiệu: muốn biết đổi gì thì đọc lại hồ sơ qua điểm cuối thường. Luồng tự đóng sau vài phút —
    nối lại là được, kèm token còn hạn.
    """
    global _so_luong_dang_mo
    # Phiên của phụ thuộc chỉ cần để dựng tác nhân; trả kết nối về bể ngay, không giữ suốt đời luồng
    session.close()

    cai_dat = get_settings()
    if _so_luong_dang_mo >= cai_dat.realtime_max_streams:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "realtime-busy", "message": "Đủ số luồng thời gian thực. Cổng tự hỏi định kỳ."},
        )

    _so_luong_dang_mo += 1
    try:
        ket_noi, nguon = await _mo_nguon_postgres()
    except Exception:
        _so_luong_dang_mo -= 1
        raise

    async def luong() -> AsyncIterator[str]:
        global _so_luong_dang_mo
        try:
            async for phan in phat_luong(
                actor,
                nguon,
                nhip_giu_giay=cai_dat.realtime_keepalive_seconds,
                han_doi_giay=cai_dat.realtime_max_stream_seconds,
            ):
                yield phan
        finally:
            _so_luong_dang_mo -= 1
            await ket_noi.close()

    return StreamingResponse(
        luong(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # APISIX (nginx) và proxy khác không gom phản hồi vào bộ đệm — khung phải tới ngay
            "X-Accel-Buffering": "no",
        },
    )
