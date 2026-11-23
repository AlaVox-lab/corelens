# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Điểm vào của dịch vụ ứng dụng.
#
# Điểm cuối nghiệp vụ thuộc #44. Tệp này hiện có kiểm tra sức khỏe và điểm cuối
# danh tính — cổng người dùng gọi nó để biết mình đang đăng nhập bằng ai.
#
# Ranh giới nền tảng lõi và ứng dụng minh họa (#365): API của lõi được gắn thêm dưới `/core/v1` ở cuối
# tệp — xem mục "Nền tảng lõi" và ARCHITECTURE.md mục 2.3.

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Response, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.analytics.bang_dieu_khien import pham_vi_cua
from app.analytics.bang_dieu_khien import router as router_bang_dieu_khien
from app.analytics.khai_pha import router as router_khai_pha
from app.analytics.luu_tru_lanh import NHAN_BO_QUET_LUU_TRU, TEN_BO_QUET_LUU_TRU, quet_luu_tru
from app.analytics.luu_tru_lanh import router as router_luu_tru
from app.analytics.xuat_du_lieu import router as router_du_lieu_mo
from app.auth.dependencies import VAI_TRO_QUAN_TRI, current_actor, current_claims, require_roles
from app.cau_hinh.quan_tri import router as router_quan_tri
from app.config import get_settings
from app.db import SessionLocal, get_session
from app.models.quan_tri import Delegation
from app.models.van_hanh import ScannerHeartbeat
from app.models.workflow_config import Department, Role
from app.quan_sat import LopQuanSat, bo_dem, cau_hinh_nhat_ky
from app.rate_limit import don_dong_cu
from app.storage import quet_ma_doc
from app.thong_bao import thu as may_thu
from app.thong_bao.bo_gui import NHAN_BO_QUET_THU, TEN_BO_QUET_THU, do_dai_hang_doi, quet_gui
from app.thong_bao.routes import router as router_thong_bao
from app.workflow.assignment import router as router_giao_viec
from app.workflow.attachment_routes import router as router_tep
from app.workflow.attachment_routes import router_tai_len as router_tai_tep
from app.workflow.context import Actor
from app.workflow.coordination import router as router_dieu_phoi
from app.workflow.coordination import vao_duoc_buong_lai
from app.workflow.department import router as router_phong_ban
from app.workflow.department import vao_duoc_phong_ban
from app.workflow.escalation import (
    BO_QUET,
    TEN_BO_QUET_HAN_CHO,
    TEN_BO_QUET_SLA,
)
from app.intelligence import mo_hinh
from app.intelligence.phan_loai import NHAN_BO_QUET_GOI_Y, TEN_BO_QUET_GOI_Y, quet_goi_y
from app.intelligence.tuong_tu import NHAN_BO_QUET_TUONG_TU, TEN_BO_QUET_TUONG_TU, quet_chi_muc
from app.intelligence.tuong_tu import router as router_tuong_tu
from app.intelligence.tri_thuc import NHAN_BO_QUET_TRI_THUC, TEN_BO_QUET_TRI_THUC, quet_kho_tri_thuc
from app.workflow.inbox import router as router_hop_thu
from app.workflow.nhip_quet import chay_luot_quet, co_bo_quet_xau, danh_gia_bo_quet
from app.workflow.routes import router as router_yeu_cau_ung_dung
from app.workflow.routes import router_loi as router_yeu_cau
from app.workflow.routes import router_nguoi_gui as router_yeu_cau_nguoi_gui
from app.workflow.loi import router_loi_rieng as router_yeu_cau_loi
from app.workflow.khoa_trung_lap import don_khoa_het_han
from app.workflow.khoa_trung_lap import them_vao_dac_ta as them_khoa_trung_lap_vao_dac_ta
from app.workflow.uy_quyen import ngay_cua_khoang
from app.workflow.uy_quyen_routes import router as router_uy_quyen
from app.thoi_gian_thuc import router as router_thoi_gian_thuc
from app.workflow.bpmn import router as router_bpmn
from app.webhook import NHAN_BO_QUET_WEBHOOK, TEN_BO_QUET_WEBHOOK, co_dang_ky_dang_bat, quet_webhook
from app.webhook import router as router_webhook

logger = logging.getLogger(__name__)

# Cấu hình nhật ký cho chính ứng dụng.
#
# Uvicorn chỉ cấu hình bộ ghi của riêng nó, nên nếu không có dòng này thì mọi thông
# điệp của dịch vụ đều biến mất — kể cả `logger.exception` trong vòng quét SLA. Một
# tác vụ nền chạy âm thầm và không báo được lỗi là thứ chỉ phát hiện ra khi đã muộn.
# Từ #247 mỗi dòng là JSON mang mã yêu cầu (DXLAB_LOG_FORMAT=text để đọc tay) — app/quan_sat.py.
settings = get_settings()
cau_hinh_nhat_ky(settings.log_format, settings.log_level)

# Mốc khởi động của tiến trình, để `/health` biết bộ quét chưa có lượt thành công là vì chưa
# kịp chạy hay vì đã chết (#253)
THOI_DIEM_KHOI_DONG = time.monotonic()


def _quet_mot_lan() -> tuple[list[int], list[int], list[str]]:
    """Một lượt quét hồ sơ quá hạn SLA rồi hồ sơ hết hạn chờ (#142), mỗi bộ quét một giao
    dịch riêng. Trả về (hồ sơ đã leo thang, hồ sơ đã tự đi, tên các bộ quét bỏ lượt).

    Mỗi bộ quét xin khóa tư vấn của riêng nó (#253): chạy nhiều bản dịch vụ thì bản nào giành
    được khóa mới quét, bản kia bỏ lượt và danh sách hồ sơ của bộ đó trống. Một bộ hỏng không
    cản bộ kia chạy — lỗi đầu tiên được ném lại sau khi cả hai đã thử.
    """
    ket_qua: dict[str, list[int]] = {bo.ten: [] for bo in BO_QUET}
    bo_qua: list[str] = []
    loi_dau: Exception | None = None

    for bo in BO_QUET:
        try:
            with SessionLocal() as phien:
                luot = chay_luot_quet(phien, bo.ten, bo.ham)
        except Exception as loi:  # noqa: BLE001 — bộ kia vẫn phải được chạy
            logger.error("Bộ quét '%s' thất bại: %s", bo.ten, loi)
            loi_dau = loi_dau or loi
            continue
        if luot.da_chay:
            ket_qua[bo.ten] = luot.ket_qua
        else:
            bo_qua.append(bo.ten)

    if loi_dau is not None:
        raise loi_dau
    return ket_qua[TEN_BO_QUET_SLA], ket_qua[TEN_BO_QUET_HAN_CHO], bo_qua


def _don_dong_cu_gioi_han() -> None:
    """Dọn các dòng đếm giới hạn tốc độ của những cửa sổ đã qua (#243)."""
    with SessionLocal() as phien:
        so_dong = don_dong_cu(phien)
        phien.commit()
    if so_dong:
        logger.info("Đã dọn %d dòng đếm giới hạn tốc độ cũ", so_dong)


def _don_khoa_trung_lap_het_han() -> None:
    """Dọn các khóa trùng lặp `Idempotency-Key` đã quá hạn sống (#426)."""
    with SessionLocal() as phien:
        so_dong = don_khoa_het_han(phien)
        phien.commit()
    if so_dong:
        logger.info("Đã dọn %d khóa trùng lặp hết hạn", so_dong)


async def _vong_quet_sla() -> None:
    """Chạy bộ quét theo chu kỳ cho tới khi ứng dụng dừng.

    Chạy trong luồng riêng bằng `to_thread` vì bộ quét dùng SQLAlchemy đồng bộ; gọi
    thẳng trong vòng lặp sự kiện sẽ chặn mọi yêu cầu HTTP khác trong lúc quét.

    Một lượt quét hỏng không được làm chết vòng lặp — ghi nhật ký rồi đợi lượt sau.
    """
    while True:
        await asyncio.sleep(settings.sla_scan_interval_seconds)
        try:
            await asyncio.to_thread(_quet_mot_lan)
        except Exception:  # noqa: BLE001 — vòng lặp nền phải sống sót qua mọi lỗi
            logger.exception("Lượt quét SLA thất bại, sẽ thử lại ở lượt sau")
        try:
            await asyncio.to_thread(_don_dong_cu_gioi_han)
        except Exception:  # noqa: BLE001 — dọn dẹp hỏng không được cản lượt quét kế tiếp
            logger.exception("Dọn dòng đếm giới hạn tốc độ thất bại")
        try:
            await asyncio.to_thread(_don_khoa_trung_lap_het_han)
        except Exception:  # noqa: BLE001 — dọn dẹp hỏng không được cản lượt quét kế tiếp
            logger.exception("Dọn khóa trùng lặp hết hạn thất bại")


def bo_quet_goi_y_bat() -> bool:
    """Bộ quét gợi ý (#317) chỉ có việc khi mô hình bật; tắt thì màn Hệ thống ghi "đã tắt"."""
    return settings.suggest_scan_enabled and settings.llm_enabled


def _quet_goi_y_mot_lan() -> list[int]:
    """Một lượt bộ quét bù gợi ý, có khóa tư vấn và dòng nhịp như bộ quét hạn (#253)."""
    with SessionLocal() as phien:
        luot = chay_luot_quet(phien, TEN_BO_QUET_GOI_Y, quet_goi_y)
    return (luot.ket_qua or []) if luot.da_chay else []


async def _vong_quet_goi_y() -> None:
    """Vòng riêng, không chung với bộ quét hạn: một lượt có thể chờ mô hình vài chục giây, và hồ
    sơ quá hạn không được leo thang muộn vì thế. Mô hình hỏng thì lượt vẫn thành công — từng hồ sơ
    được đánh dấu đã thử — nên nhịp chỉ báo hỏng khi chính bộ quét hỏng (cơ sở dữ liệu chẳng hạn)."""
    while True:
        await asyncio.sleep(settings.suggest_scan_interval_seconds)
        try:
            await asyncio.to_thread(_quet_goi_y_mot_lan)
        except Exception:  # noqa: BLE001 — vòng lặp nền phải sống sót qua mọi lỗi
            logger.exception("Lượt quét gợi ý thất bại, sẽ thử lại ở lượt sau")


def _quet_tuong_tu_mot_lan() -> int:
    """Một lượt bộ lập chỉ mục hồ sơ tương tự (#319), có khóa tư vấn và dòng nhịp (#253)."""
    with SessionLocal() as phien:
        luot = chay_luot_quet(phien, TEN_BO_QUET_TUONG_TU, quet_chi_muc)
    return (luot.ket_qua or 0) if luot.da_chay else 0


async def _vong_quet_tuong_tu() -> None:
    """Vòng riêng như bộ quét gợi ý: một lượt có thể chờ mô hình nhúng. Chạy cả khi mô hình nhúng tắt —
    phiên đã xem gợi ý mà quá hạn không gửi vẫn phải được tính là bỏ không gửi."""
    while True:
        await asyncio.sleep(settings.similar_index_interval_seconds)
        try:
            await asyncio.to_thread(_quet_tuong_tu_mot_lan)
        except Exception:  # noqa: BLE001 — vòng lặp nền phải sống sót qua mọi lỗi
            logger.exception("Lượt lập chỉ mục hồ sơ tương tự thất bại, sẽ thử lại ở lượt sau")


def bo_quet_tri_thuc_bat() -> bool:
    """Bộ lập chỉ mục kho tri thức (#321) chỉ có việc khi cả kho tri thức lẫn mô hình nhúng bật."""
    return settings.wiki_enabled and settings.embedding_enabled


def _quet_tri_thuc_mot_lan() -> int:
    """Một lượt bộ lập chỉ mục kho tri thức (#321), có khóa tư vấn và dòng nhịp (#253)."""
    with SessionLocal() as phien:
        luot = chay_luot_quet(phien, TEN_BO_QUET_TRI_THUC, quet_kho_tri_thuc)
    return (luot.ket_qua or 0) if luot.da_chay else 0


async def _vong_quet_tri_thuc() -> None:
    """Vòng riêng: một lượt có thể chờ wiki và mô hình nhúng, không được làm trễ bộ quét hạn."""
    while True:
        await asyncio.sleep(settings.wiki_index_interval_seconds)
        try:
            await asyncio.to_thread(_quet_tri_thuc_mot_lan)
        except Exception:  # noqa: BLE001 — vòng lặp nền phải sống sót qua mọi lỗi
            logger.exception("Lượt lập chỉ mục kho tri thức thất bại, sẽ thử lại ở lượt sau")


def _gui_thu_mot_lan() -> int:
    """Một lượt bộ gửi thư thông báo (#251), có khóa tư vấn và dòng nhịp (#253)."""
    with SessionLocal() as phien:
        luot = chay_luot_quet(phien, TEN_BO_QUET_THU, quet_gui)
    return (luot.ket_qua or 0) if luot.da_chay else 0


async def _vong_gui_thu() -> None:
    """Vòng riêng: một lượt có thể chờ máy chủ thư tới hạn chót, không được làm trễ bộ quét hạn."""
    while True:
        await asyncio.sleep(settings.notify_scan_interval_seconds)
        try:
            await asyncio.to_thread(_gui_thu_mot_lan)
        except Exception:  # noqa: BLE001 — vòng lặp nền phải sống sót qua mọi lỗi
            logger.exception("Lượt gửi thư thông báo thất bại, sẽ thử lại ở lượt sau")


def _luu_tru_mot_lan() -> list[str]:
    """Một lượt bộ lưu trữ lạnh (#378), có khóa tư vấn và dòng nhịp (#253). Trả về các kỳ vừa niêm phong."""
    with SessionLocal() as phien:
        luot = chay_luot_quet(phien, TEN_BO_QUET_LUU_TRU, quet_luu_tru)
    return (luot.ket_qua or []) if luot.da_chay else []


async def _vong_luu_tru() -> None:
    """Vòng riêng: lần đầu bật trên cụm nhiều năm dữ liệu, một lượt ghi kho vài tháng — không được làm trễ
    bộ quét hạn. Muốn chạy ngay (trình diễn, kiểm chứng) thì `POST /archive/scan`."""
    while True:
        await asyncio.sleep(settings.archive_interval_seconds)
        try:
            await asyncio.to_thread(_luu_tru_mot_lan)
        except Exception:  # noqa: BLE001 — vòng lặp nền phải sống sót qua mọi lỗi
            logger.exception("Lượt lưu trữ lạnh thất bại, sẽ thử lại ở lượt sau")


def _gui_webhook_mot_lan() -> int:
    """Một lượt bộ gửi webhook (#390), có khóa tư vấn và dòng nhịp (#253)."""
    with SessionLocal() as phien:
        luot = chay_luot_quet(phien, TEN_BO_QUET_WEBHOOK, quet_webhook)
    return (luot.ket_qua or 0) if luot.da_chay else 0


async def _vong_gui_webhook() -> None:
    """Vòng riêng như bộ gửi thư: một bên nhận chậm không được làm trễ bộ quét hạn."""
    while True:
        await asyncio.sleep(settings.webhook_scan_interval_seconds)
        try:
            await asyncio.to_thread(_gui_webhook_mot_lan)
        except Exception:  # noqa: BLE001 — vòng lặp nền phải sống sót qua mọi lỗi
            logger.exception("Lượt gửi webhook thất bại, sẽ thử lại ở lượt sau")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Bật bộ quét SLA và bộ quét gợi ý lúc khởi động, tắt gọn lúc dừng."""
    cac_tac_vu = []
    if settings.sla_scan_enabled:
        cac_tac_vu.append(asyncio.create_task(_vong_quet_sla()))
        logger.info(
            "Bộ quét SLA chạy mỗi %d giây", settings.sla_scan_interval_seconds
        )
    if bo_quet_goi_y_bat():
        cac_tac_vu.append(asyncio.create_task(_vong_quet_goi_y()))
        logger.info(
            "Mô hình ngôn ngữ bật; bộ quét gợi ý chạy mỗi %d giây",
            settings.suggest_scan_interval_seconds,
        )

    if settings.similar_index_enabled:
        cac_tac_vu.append(asyncio.create_task(_vong_quet_tuong_tu()))

    # Kho tri thức (#321): cần cả địa chỉ wiki lẫn mô hình nhúng
    if bo_quet_tri_thuc_bat():
        cac_tac_vu.append(asyncio.create_task(_vong_quet_tri_thuc()))
        logger.info("Kho tri thức bật; bộ lập chỉ mục bài chạy mỗi %d giây", settings.wiki_index_interval_seconds)

    # Thông báo thư (#251): máy chủ thư không cấu hình thì không có bộ gửi
    if settings.notify_enabled:
        cac_tac_vu.append(asyncio.create_task(_vong_gui_thu()))
        logger.info(
            "Thông báo thư bật (%s:%d); bộ gửi chạy mỗi %d giây",
            settings.smtp_host,
            settings.smtp_port,
            settings.notify_scan_interval_seconds,
        )

    # Lưu trữ lạnh (#378): mặc định bật, chu kỳ trong cấu hình
    if settings.archive_enabled:
        cac_tac_vu.append(asyncio.create_task(_vong_luu_tru()))
        logger.info("Lưu trữ lạnh bật; bộ quét chạy mỗi %d giây", settings.archive_interval_seconds)

    # Webhook (#390): luôn chạy trừ khi đặt chu kỳ 0 — không đăng ký nào thì lượt gần như không tốn gì
    if settings.webhook_enabled:
        cac_tac_vu.append(asyncio.create_task(_vong_gui_webhook()))
        logger.info("Bộ gửi webhook chạy mỗi %d giây", settings.webhook_scan_interval_seconds)

    yield

    for tac_vu in cac_tac_vu:
        tac_vu.cancel()


# Sáu nhóm API của nền tảng lõi (#365; lưu trữ lạnh #378), mỗi nhóm một nhãn OpenAPI kèm mô tả hiện ở /docs. Khai trong
# `openapi_tags` nên sáu nhóm này đứng đầu trang tài liệu, trước các nhóm của ứng dụng minh họa. Khóa là
# đoạn đường ngay sau `/core/v1`.
NHOM_LOI: dict[str, dict[str, str]] = {
    "workflow": {
        "name": "Lõi — Luồng công việc",
        "description": "Động cơ luồng công việc: danh mục cấu hình, tạo và đọc hồ sơ, bước chuyển được "
        "phép và thực hiện bước chuyển, lịch sử. Mọi bước chuyển qua cùng một cửa của engine và ghi nhật "
        "ký sự kiện.",
    },
    "files": {
        "name": "Lõi — Tệp",
        "description": "Dữ liệu phi cấu trúc: chính sách tệp, tải tệp lên một hồ sơ, tải tệp về. Tệp nằm "
        "trong kho đối tượng SeaweedFS, quyền kiểm ở mỗi lần.",
    },
    "events": {
        "name": "Lõi — Nhật ký sự kiện",
        "description": "Dữ liệu có cấu trúc: xuất nhật ký sự kiện chuẩn hóa dạng CSV hoặc JSON. Chỉ quản "
        "trị viên.",
    },
    "archive": {
        "name": "Lõi — Lưu trữ lạnh",
        "description": "Dữ liệu lịch sử ở tầng lạnh: mỗi tháng đã khép một bản lưu bất biến trong kho đối "
        "tượng — nhật ký sự kiện và hồ sơ đã kết thúc (CSV gzip) kèm bản kê có mã băm SHA-256. Liệt kê, đọc "
        "bản kê, tải từng tệp. Chỉ quản trị viên.",
    },
    "notifications": {
        "name": "Lõi — Thông báo",
        "description": "Tùy chọn nhận thông báo thư của chính người gọi.",
    },
    "webhooks": {
        "name": "Lõi — Webhook",
        "description": "Truyền phát sự kiện ra ngoài: đăng ký một địa chỉ nhận, mỗi bản ghi mới của nhật ký sự "
        "kiện khớp bộ lọc được POST tới đó, ký HMAC-SHA256, thử lại khi hỏng. Chỉ quản trị viên.",
    },
    "identity": {
        "name": "Lõi — Định danh",
        "description": "Người gọi là ai theo token Keycloak: vai trò, phòng ban.",
    },
}

app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Dịch vụ ứng dụng của Corelens. Toàn bộ quy trình nghiệp vụ nằm trong bảng "
        "dữ liệu, không mã cứng trong mã nguồn.\n\n"
        "**Nền tảng lõi (Tầng 1)**: mọi điểm cuối dưới `/core/v1`, nhóm theo dịch vụ lõi (nhãn "
        "\"Lõi — …\"), dành cho mọi ứng dụng tầng trên. Ứng dụng khác gọi bằng token của tài khoản "
        "dịch vụ (client credentials). Các đường còn lại thuộc ứng dụng minh họa — cổng vận hành "
        "yêu cầu nội bộ."
    ),
    openapi_tags=list(NHOM_LOI.values()),
)

# Mã yêu cầu, dòng truy cập JSON, bộ đếm số đo (#247)
app.add_middleware(LopQuanSat)

# Đường cũ. Nhãn OpenAPI gắn ở đây chứ không ở router, vì router của lõi còn được gắn lần nữa dưới
# /core/v1 với nhãn riêng (cuối tệp) — nhãn của router thì cộng dồn vào mọi lần gắn.
app.include_router(router_yeu_cau, tags=["Yêu cầu"])
app.include_router(router_yeu_cau_nguoi_gui, tags=["Yêu cầu"])
app.include_router(router_yeu_cau_ung_dung, tags=["Yêu cầu"])
app.include_router(router_dieu_phoi)
app.include_router(router_giao_viec)
app.include_router(router_phong_ban)
app.include_router(router_hop_thu)
app.include_router(router_tep, prefix="/attachments", tags=["Tệp đính kèm"])
app.include_router(router_tai_tep, tags=["Tệp đính kèm"])
app.include_router(router_du_lieu_mo, prefix="/analytics/event-log", tags=["Dữ liệu mở"])
app.include_router(router_bang_dieu_khien)
app.include_router(router_khai_pha)
app.include_router(router_tuong_tu)
app.include_router(router_thong_bao, prefix="/me/notifications", tags=["Thông báo"])
app.include_router(router_quan_tri)
app.include_router(router_uy_quyen)
app.include_router(router_thoi_gian_thuc)


def _do_suc_khoe(session: Session) -> dict:
    """Đo sức khỏe của dịch vụ, đủ chi tiết. Phía gọi quyết định lộ ra bao nhiêu.

    Hai bậc suy giảm, khác nhau ở chỗ có làm dịch vụ ngừng phục vụ hay không:
    - `unavailable` — cơ sở dữ liệu không dùng được, hoặc lược đồ quy trình chưa nạp: dịch vụ
      không làm được việc. `/health` trả 503.
    - `degraded` mà không `unavailable` — bộ quét nền im quá lâu hoặc hỏng liên tiếp (#253).
      Dịch vụ vẫn phục vụ yêu cầu bình thường; chỉ hồ sơ quá hạn không tự leo thang. `/health`
      vẫn trả 200: container healthcheck của Docker và các dịch vụ chờ `service_healthy` (cổng
      người dùng, Superset) không được bị chặn hay đánh dấu hỏng vì một bộ quét trượt, mà phải
      đọc `status` để biết.

    Chi tiết lỗi (`detail`) chỉ ghi vào nhật ký và trả cho quản trị viên ở `/system/health`;
    câu lỗi của trình điều khiển có thể mang tên máy chủ, tên cơ sở dữ liệu, tên tài khoản.
    """
    ket_qua: dict = {"status": "ok", "database": "ok", "unavailable": False}

    try:
        session.execute(text("SELECT 1"))
    except Exception as loi:  # noqa: BLE001 — cần bắt mọi lỗi kết nối để báo 503
        logger.warning("Kiểm tra sức khỏe: cơ sở dữ liệu không dùng được: %s", loi)
        ket_qua.update(
            status="degraded", database="unreachable", unavailable=True, detail=str(loi)[:200]
        )
        return ket_qua

    # Đếm trạng thái của bộ quy tắc đang kích hoạt. Con số này chứng minh cả chuỗi
    # khởi tạo đã chạy: lược đồ được tạo, dữ liệu khởi tạo được nạp, các phép kiểm
    # tra tính nhất quán đều qua. Bằng không thì cụm dựng lên nhưng rỗng ruột.
    try:
        ket_qua["active_rule_set_states"] = session.execute(
            text(
                "SELECT count(*) FROM states s"
                " JOIN rule_sets r ON r.id = s.rule_set_id"
                " WHERE r.is_active"
            )
        ).scalar_one()
    except Exception as loi:  # noqa: BLE001 — lược đồ chưa nạp thì vẫn coi là suy giảm
        logger.warning("Kiểm tra sức khỏe: chưa nạp được lược đồ quy trình: %s", loi)
        ket_qua.update(
            status="degraded", unavailable=True, detail="Chưa nạp được lược đồ quy trình"
        )
        return ket_qua

    # Nhịp bộ quét (#253). Bộ quét tắt bằng cấu hình là chủ ý, không phải sự cố
    try:
        ket_qua["scanners"] = danh_gia_bo_quet(
            session,
            {bo.ten: bo.nhan for bo in BO_QUET},
            nguong_qua_lau_giay=settings.sla_scan_stale_threshold_seconds,
            loi_lien_tiep_toi_da=settings.sla_scan_max_consecutive_errors,
            da_chay_giay=time.monotonic() - THOI_DIEM_KHOI_DONG,
            dang_bat=settings.sla_scan_enabled,
        )
        # Bộ quét gợi ý (#317) chỉ có mặt khi chạy: mô hình tắt thì dòng "Mô hình ngôn ngữ: tắt"
        # đã nói đủ, thêm một dòng "bộ quét đã tắt" chỉ là nhiễu
        if bo_quet_goi_y_bat():
            ket_qua["scanners"] += danh_gia_bo_quet(
                session,
                {TEN_BO_QUET_GOI_Y: NHAN_BO_QUET_GOI_Y},
                nguong_qua_lau_giay=settings.suggest_scan_stale_threshold_seconds,
                loi_lien_tiep_toi_da=settings.sla_scan_max_consecutive_errors,
                da_chay_giay=time.monotonic() - THOI_DIEM_KHOI_DONG,
            )
        # Bộ lập chỉ mục hồ sơ tương tự (#319): cùng cách, chỉ hiện khi mô hình nhúng bật
        if settings.similar_index_enabled and settings.embedding_enabled:
            ket_qua["scanners"] += danh_gia_bo_quet(
                session,
                {TEN_BO_QUET_TUONG_TU: NHAN_BO_QUET_TUONG_TU},
                nguong_qua_lau_giay=settings.similar_index_stale_threshold_seconds,
                loi_lien_tiep_toi_da=settings.sla_scan_max_consecutive_errors,
                da_chay_giay=time.monotonic() - THOI_DIEM_KHOI_DONG,
            )
        # Bộ lập chỉ mục kho tri thức (#321): chỉ hiện khi chạy
        if bo_quet_tri_thuc_bat():
            ket_qua["scanners"] += danh_gia_bo_quet(
                session,
                {TEN_BO_QUET_TRI_THUC: NHAN_BO_QUET_TRI_THUC},
                nguong_qua_lau_giay=settings.wiki_index_stale_threshold_seconds,
                loi_lien_tiep_toi_da=settings.sla_scan_max_consecutive_errors,
                da_chay_giay=time.monotonic() - THOI_DIEM_KHOI_DONG,
            )
        # Bộ lưu trữ lạnh (#378): mặc định bật; như các bộ quét tùy chọn khác, tắt thì không có dòng
        if settings.archive_enabled:
            ket_qua["scanners"] += danh_gia_bo_quet(
                session,
                {TEN_BO_QUET_LUU_TRU: NHAN_BO_QUET_LUU_TRU},
                nguong_qua_lau_giay=settings.archive_stale_threshold_seconds,
                loi_lien_tiep_toi_da=settings.sla_scan_max_consecutive_errors,
                da_chay_giay=time.monotonic() - THOI_DIEM_KHOI_DONG,
            )
        # Bộ gửi thư (#251): chỉ hiện khi máy chủ thư được cấu hình
        if settings.notify_enabled:
            ket_qua["scanners"] += danh_gia_bo_quet(
                session,
                {TEN_BO_QUET_THU: NHAN_BO_QUET_THU},
                nguong_qua_lau_giay=settings.notify_scan_stale_threshold_seconds,
                loi_lien_tiep_toi_da=settings.sla_scan_max_consecutive_errors,
                da_chay_giay=time.monotonic() - THOI_DIEM_KHOI_DONG,
            )
        # Bộ gửi webhook (#390): chỉ hiện khi có đăng ký đang bật — không ai nghe thì nhịp không nói lên gì
        if settings.webhook_enabled and co_dang_ky_dang_bat(session):
            ket_qua["scanners"] += danh_gia_bo_quet(
                session,
                {TEN_BO_QUET_WEBHOOK: NHAN_BO_QUET_WEBHOOK},
                nguong_qua_lau_giay=settings.webhook_scan_stale_threshold_seconds,
                loi_lien_tiep_toi_da=settings.sla_scan_max_consecutive_errors,
                da_chay_giay=time.monotonic() - THOI_DIEM_KHOI_DONG,
            )
    except Exception as loi:  # noqa: BLE001 — không đọc được nhịp thì không dám nói là khỏe
        logger.warning("Kiểm tra sức khỏe: không đọc được nhịp bộ quét: %s", loi)
        ket_qua.update(status="degraded", scanners=None, detail="Không đọc được nhịp bộ quét")
        return ket_qua

    if co_bo_quet_xau(ket_qua["scanners"]):
        ket_qua["status"] = "degraded"
    return ket_qua


@app.get("/health", tags=["Vận hành"])
def health(response: Response, session: Session = Depends(get_session)) -> dict:
    """Báo trạng thái chung của dịch vụ: `ok` hoặc `degraded`. Công khai, không cần đăng nhập.

    Trả về 503 khi cơ sở dữ liệu không dùng được. Điểm này quan trọng: một điểm cuối
    kiểm tra sức khỏe luôn trả 200 thì vô dụng. Nhóm đã vấp đúng bẫy đó với Apache
    Superset ở #38 — container báo `healthy` trong khi không ai đăng nhập được.

    Chỉ trả đúng trạng thái chung (#243): điểm cuối này mở cho cả người chưa đăng nhập, nên không
    có phiên bản, không tên cơ sở dữ liệu, không câu lỗi nào. Chi tiết ở `/system/health`.
    """
    suc_khoe = _do_suc_khoe(session)
    if suc_khoe["unavailable"]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"service": "dx-os-lab-backend", "status": suc_khoe["status"]}


@app.get("/health/live", tags=["Vận hành"])
def health_live() -> dict:
    """Tiến trình còn sống và vòng sự kiện còn trả lời (#247). Không chạm cơ sở dữ liệu hay dịch vụ
    nào khác: cơ sở dữ liệu chậm không được khiến bộ điều phối giết một tiến trình vẫn khỏe."""
    return {"service": "dx-os-lab-backend", "status": "ok"}


@app.get("/health/ready", tags=["Vận hành"])
def health_ready(response: Response, session: Session = Depends(get_session)) -> dict:
    """Sẵn sàng nhận việc (#247): cơ sở dữ liệu dùng được và bộ quy tắc đã nạp — phụ thuộc BẮT BUỘC.
    503 khi chưa. Dịch vụ tùy chọn (mô hình, quét mã độc, máy chủ thư, Superset) không tính: thiếu
    chúng thì dịch vụ vẫn phục vụ. Healthcheck của ảnh (backend/Dockerfile) gọi điểm cuối này, nên
    cổng và Superset chờ `service_healthy` là chờ đúng lúc dịch vụ làm được việc. Cùng nội dung với
    `/health` — giữ `/health` cho bộ giám sát và tài liệu cũ."""
    return health(response, session)


@app.get("/metrics", tags=["Vận hành"])
def metrics(
    actor: Annotated[Actor, Depends(require_roles(VAI_TRO_QUAN_TRI))],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    """Số đo cơ bản, dạng văn bản Prometheus (#247). CHỈ QUẢN TRỊ VIÊN.

    Không mở công khai và không dựa vào "chỉ trong mạng Compose": từ #364 cổng dịch vụ không mở ra máy ở
    cấu hình mặc định, nhưng tệp phát triển mở lại được, và ranh giới mạng không thay được kiểm quyền; mẫu
    đường dẫn và độ dài hàng đợi là thông tin vận hành không cho người ngoài. Bộ thu số đo đi qua cổng API
    bằng token của một tài khoản quản trị.

    Phần trong bộ nhớ là của RIÊNG bản dịch vụ trả lời; phần đọc từ cơ sở dữ liệu — hàng đợi thư, lượt
    quét cuối — là chung cả cụm.
    """
    dong = bo_dem.xuat()
    try:
        hang_doi = do_dai_hang_doi(session)
        dong += [
            "# HELP dxlab_email_queue Thư thông báo theo trạng thái hàng đợi (#251).",
            "# TYPE dxlab_email_queue gauge",
            f'dxlab_email_queue{{state="events_pending"}} {hang_doi["events_pending"]}',
            f'dxlab_email_queue{{state="deliveries_pending"}} {hang_doi["deliveries_pending"]}',
            f'dxlab_email_queue{{state="deliveries_failed"}} {hang_doi["deliveries_failed"]}',
        ]
        nhip = session.scalars(select(ScannerHeartbeat).order_by(ScannerHeartbeat.name)).all()
        dong += [
            "# HELP dxlab_scanner_last_success_timestamp_seconds Lượt quét thành công cuối của từng bộ quét (Unix).",
            "# TYPE dxlab_scanner_last_success_timestamp_seconds gauge",
        ]
        dong += [
            f'dxlab_scanner_last_success_timestamp_seconds{{scanner="{h.name}"}} {h.last_success_at.timestamp():.0f}'
            for h in nhip
            if h.last_success_at is not None
        ]
        dong += [
            "# HELP dxlab_scanner_consecutive_errors Số lượt hỏng liên tiếp của từng bộ quét.",
            "# TYPE dxlab_scanner_consecutive_errors gauge",
        ]
        dong += [
            f'dxlab_scanner_consecutive_errors{{scanner="{h.name}"}} {h.consecutive_errors}' for h in nhip
        ]
        dong += ["# TYPE dxlab_database_up gauge", "dxlab_database_up 1"]
    except Exception as loi:  # noqa: BLE001 — phần trong bộ nhớ vẫn phải xuất được khi CSDL hỏng
        logger.warning("Số đo: không đọc được cơ sở dữ liệu: %s", loi)
        _hoan_tac_im_lang(session)
        dong += ["# TYPE dxlab_database_up gauge", "dxlab_database_up 0"]
    return Response("\n".join(dong) + "\n", media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/system/health", tags=["Vận hành"])
def system_health(
    actor: Annotated[Actor, Depends(require_roles(VAI_TRO_QUAN_TRI))],
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    """Sức khỏe chi tiết cho màn Hệ thống (#229, #243, #253): phiên bản, cơ sở dữ liệu, bộ quy
    tắc đã nạp, nhịp từng bộ quét và ngưỡng cảnh báo. Chỉ quản trị viên.

    Luôn trả 200 kể cả khi cơ sở dữ liệu hỏng — đây là điểm cuối dữ liệu cho màn hình, không phải
    điểm cuối cho bộ giám sát; `/health` mới là cái đổi mã trạng thái. Cùng một hàm đo với
    `/health`, nên hai nơi không thể kể hai chuyện khác nhau.
    """
    suc_khoe = _do_suc_khoe(session)
    suc_khoe.pop("unavailable")
    return {
        "service": "dx-os-lab-backend",
        "version": settings.app_version,
        **suc_khoe,
        # Mô hình ngôn ngữ (#316): tùy chọn, nên không bao giờ làm `status` xấu đi — chỉ báo riêng.
        # Hỏi ở đây chứ không ở `_do_suc_khoe`: `/health` công khai không được gọi ra dịch vụ khác.
        "language_model": mo_hinh.tinh_trang(),
        # Mô hình nhúng cho hồ sơ tương tự (#319), cùng nguyên tắc
        "embedding_model": mo_hinh.tinh_trang_nhung(),
        # Dịch vụ quét mã độc tệp đính kèm (#248), tùy chọn, cùng ba mức
        "malware_scan": quet_ma_doc.tinh_trang(),
        # Máy chủ thư thông báo (#251), tùy chọn, cùng ba mức; kèm độ dài hàng đợi để đối soát
        "email": {
            **may_thu.tinh_trang(),
            **(_hang_doi_thu(session) if suc_khoe.get("database") == "ok" else {}),
        },
        "scan_settings": {
            "enabled": settings.sla_scan_enabled,
            "interval_seconds": settings.sla_scan_interval_seconds,
            "stale_after_seconds": settings.sla_scan_stale_threshold_seconds,
            "max_consecutive_errors": settings.sla_scan_max_consecutive_errors,
        },
    }


def _hang_doi_thu(session: Session) -> dict:
    """Độ dài hàng đợi thư, hoặc rỗng khi chưa có bảng (cơ sở dữ liệu hỏng đã được báo ở trên)."""
    try:
        return {"queue": do_dai_hang_doi(session)}
    except Exception:  # noqa: BLE001 — màn Hệ thống vẫn phải hiện các phần còn lại
        _hoan_tac_im_lang(session)
        return {}


def _hoan_tac_im_lang(session: Session) -> None:
    """Hoàn tác sau một truy vấn hỏng, không để lỗi của chính lần hoàn tác làm hỏng điểm cuối."""
    try:
        session.rollback()
    except Exception:  # noqa: BLE001
        logger.debug("Không hoàn tác được phiên sau truy vấn hỏng", exc_info=True)


@app.get("/", tags=["Vận hành"])
def root() -> dict:
    """Chỉ đường tới tài liệu API tự sinh."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


# Router riêng cho `/me` để gắn được cả ở đường cũ lẫn dưới /core/v1/identity (#365) mà không chép hàm
router_dinh_danh = APIRouter()


@router_dinh_danh.get("/me")
def me(
    actor: Annotated[Actor, Depends(current_actor)],
    claims: Annotated[dict, Depends(current_claims)],
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    """Danh tính của người đang gọi, dịch từ token sang ngôn ngữ của engine.

    Cổng người dùng gọi điểm cuối này sau khi đăng nhập để biết hiển thị những gì.
    Nó cũng là cách nhanh nhất để kiểm tra chuỗi định danh có thông không: gọi được
    nghĩa là chữ ký, hạn dùng, nơi phát và người nhận đều đã qua.

    Chỉ trả về những claim cần cho giao diện. Không trả nguyên token lẫn các claim
    nội bộ của Keycloak — cổng không cần chúng, và lộ ra chỉ thêm bề mặt tấn công.

    `workspaces` cho giao diện biết dựng mục điều hướng nào. Dịch vụ quyết, dựa trên
    vai trò, để mã giao diện không phải chứa tên vai trò nào cả. Đây chỉ là chuyện hiển
    thị: mỗi điểm cuối vẫn tự gác cửa của nó.
    """
    khong_gian = ["portal"]
    if vao_duoc_buong_lai(actor):
        khong_gian.append("coordination")
    if vao_duoc_phong_ban(session, actor):
        khong_gian.append("department")
    # Báo cáo (#305): vai trò nào xem được là cột `roles.report_scope`, tra cùng một hàm với
    # điểm cuối cấp token — mục trên thanh bên và quyền mở bảng điều khiển không lệch nhau.
    if pham_vi_cua(session, actor) is not None:
        khong_gian.append("reports")
    # Màn Hệ thống (#229): tình trạng các dịch vụ chỉ có nghĩa với người vận hành cụm, nên
    # chỉ quản trị viên thấy — cùng vai trò gác điểm cuối /sla/scan ngay dưới.
    if VAI_TRO_QUAN_TRI in actor.roles:
        khong_gian.append("system")

    # Ủy quyền đang hiệu lực mà người này nhận (#252): trang chủ hiện dải "Bạn đang làm thay …"
    lam_thay = []
    if actor.lam_thay:
        nhan_vai = {r.code: r.label for r in session.scalars(select(Role))}
        nhan_phong = {p.code: p.label for p in session.scalars(select(Department))}
        for u in actor.lam_thay:
            ban_ghi = session.get(Delegation, u.ma)
            lam_thay.append(
                {
                    "delegator_label": u.nguoi_vang_label,
                    "department_label": nhan_phong.get(u.phong, u.phong),
                    "roles": [nhan_vai.get(v, v) for v in sorted(u.vai)],
                    "ends_on": ngay_cua_khoang(session, ban_ghi.starts_at, ban_ghi.ends_at)[1],
                }
            )

    return {
        "id": actor.id,
        "username": claims.get("preferred_username"),
        "name": claims.get("name"),
        "email": claims.get("email"),
        "roles": sorted(actor.roles),
        "departments": sorted(actor.departments),
        "workspaces": khong_gian,
        "acting_for": lam_thay,
        # Lối vào kho tri thức (#321): mở thẳng chiến lược đăng nhập qua Keycloak, nên người đã đăng nhập
        # cổng không phải nhập mật khẩu lần hai. Kho tri thức tắt thì không có, thanh bên không hiện lối vào
        "knowledge_base": (
            {
                "url": f"{settings.wiki_public_url.rstrip('/')}/login/{settings.wiki_strategy_key}",
                "source_url": settings.wiki_source_url,
            }
            if settings.wiki_enabled
            else None
        ),
    }


app.include_router(router_dinh_danh, tags=["Định danh"])


@app.post("/sla/scan", tags=["Vận hành"])
def sla_scan(
    actor: Annotated[Actor, Depends(require_roles(VAI_TRO_QUAN_TRI))],
) -> dict:
    """Chạy ngay một lượt quét hồ sơ quá hạn SLA và hết hạn chờ, không đợi chu kỳ.

    Có hai lý do tồn tại: kiểm chứng cơ chế mà không phải ngồi chờ, và trình diễn
    việc tự leo thang trước người xem.

    Chỉ quản trị viên gọi được. Việc leo thang vẫn đi qua điểm chuyển trạng thái duy
    nhất, nên người bấm nút không ghi đè được luật nào — nhật ký vẫn ghi tác nhân là
    hệ thống, không phải người này.
    """
    da_leo_thang, da_tu_di, bo_qua = _quet_mot_lan()
    return {
        "escalated_count": len(da_leo_thang),
        "escalated_case_ids": da_leo_thang,
        # Hồ sơ hết hạn chờ đã được hệ thống tự đi thay (#142)
        "auto_moved_case_ids": da_tu_di,
        # Bộ quét mà bản dịch vụ khác đang giữ khóa nên lượt này bỏ qua (#253); trống khi chạy một bản
        "skipped_scanners": bo_qua,
        "triggered_by": actor.id,
    }


@app.post("/archive/scan", tags=["Vận hành"])
def archive_scan(
    actor: Annotated[Actor, Depends(require_roles(VAI_TRO_QUAN_TRI))],
) -> dict:
    """Chạy ngay một lượt lưu trữ lạnh (#378), không đợi chu kỳ — để trình diễn và kiểm chứng.

    Chỉ niêm phong tháng đã khép chưa có bản lưu; bản đã có không bao giờ bị ghi đè, nên bấm bao nhiêu lần
    cũng an toàn. Bản dịch vụ khác đang giữ khóa thì lượt này bỏ qua (`skipped`). Chạy cả khi bộ quét định kỳ
    tắt bằng cấu hình: tắt là tắt lịch, không tắt khả năng xuất."""
    with SessionLocal() as phien:
        luot = chay_luot_quet(phien, TEN_BO_QUET_LUU_TRU, quet_luu_tru)
    return {"exported_periods": luot.ket_qua or [], "skipped": not luot.da_chay, "triggered_by": actor.id}


# ---------------------------------------------------------------------------
# Nền tảng lõi — Tầng 1 của đề thi (#365, ARCHITECTURE.md mục 2.3)
# ---------------------------------------------------------------------------
# Mức 1 giảng viên chốt: một dịch vụ, ranh giới vẽ bằng không gian địa chỉ. API của lõi được gắn THÊM một
# lần dưới `/core/v1/<nhóm>` — cùng router, cùng hàm xử lý, cùng phụ thuộc với đường cũ (kiểm token, phân
# quyền, giới hạn tốc độ theo người dùng), không chép mã nào. Đường cũ giữ nguyên cho cổng người dùng.
#
# Điểm cuối của ứng dụng minh họa KHÔNG gắn ở đây: buồng lái điều phối và phòng ban, hộp thư và lời nhắn,
# ủy quyền, giao việc và danh bạ, báo cáo nhúng, khai phá quy trình, hồ sơ tương tự, quản trị cấu hình, vận
# hành (`/system/health`, `/sla/scan`, `/metrics`). Mã thao tác OpenAPI FastAPI tự sinh từ tên hàm và
# đường dẫn, nên bản dưới /core/v1 không trùng bản ở đường cũ. Tại cổng API, `/core/v1/*` rơi vào tuyến cần
# token như mọi đường không công khai (infra/cong-api/apisix.yaml).
TIEN_TO_LOI = "/core/v1"


def _gan_loi(router: APIRouter, nhom: str, duong: str = "") -> None:
    """Gắn một router thêm một lần dưới `/core/v1/<nhóm><đường>`, mang đúng một nhãn "Lõi — …"."""
    app.include_router(router, prefix=f"{TIEN_TO_LOI}/{nhom}{duong}", tags=[NHOM_LOI[nhom]["name"]])


_gan_loi(router_yeu_cau, "workflow")
# Danh sách, chi tiết, bước chuyển của lõi: phạm vi theo vai (#376), khác cửa "hồ sơ của mình" ở đường cũ
_gan_loi(router_yeu_cau_loi, "workflow")
# Quy trình dạng BPMN 2.0 (#405): chỉ có ở lõi, cổng người dùng không dùng
_gan_loi(router_bpmn, "workflow")
_gan_loi(router_tep, "files")
_gan_loi(router_tai_tep, "files")
_gan_loi(router_du_lieu_mo, "events")
# Lưu trữ lạnh (#378): chỉ có ở lõi, không có đường cũ — cổng người dùng không dùng
_gan_loi(router_luu_tru, "archive")
_gan_loi(router_thong_bao, "notifications", "/preferences")
_gan_loi(router_dinh_danh, "identity")
_gan_loi(router_webhook, "webhooks")

# Khóa trùng lặp `Idempotency-Key` (#426): chỉ hai lệnh của lõi. Lệnh tạo hồ sơ dùng chung một tuyến với cổng
# người dùng (router gắn hai lần, FastAPI không chép tuyến), nên `openapi_extra` của tuyến sẽ hiện ở cả hai
# đường. Tiêu đề khai vào đặc tả ở đây, sau khi FastAPI sinh, trên đúng hai thao tác dưới /core/v1 — cách mở
# rộng OpenAPI FastAPI chỉ dẫn (thay `app.openapi`). Lúc chạy, phụ thuộc `khoa_trung_lap` cũng chỉ bật ở lõi.
LENH_CO_KHOA_TRUNG_LAP = (
    ("post", f"{TIEN_TO_LOI}/workflow/requests"),
    ("post", f"{TIEN_TO_LOI}/workflow/requests/{{case_id}}/transitions"),
)


def _openapi_co_khoa_trung_lap() -> dict:
    if app.openapi_schema is None:
        dac_ta = FastAPI.openapi(app)
        for phuong_thuc, duong in LENH_CO_KHOA_TRUNG_LAP:
            them_khoa_trung_lap_vao_dac_ta(dac_ta["paths"][duong][phuong_thuc])
    return app.openapi_schema


app.openapi = _openapi_co_khoa_trung_lap
