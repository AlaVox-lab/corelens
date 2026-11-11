# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Điểm vào của dịch vụ ứng dụng.
#
# Điểm cuối nghiệp vụ thuộc #44. Tệp này hiện có kiểm tra sức khỏe và điểm cuối
# danh tính — cổng người dùng gọi nó để biết mình đang đăng nhập bằng ai.

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.analytics.bang_dieu_khien import pham_vi_cua
from app.analytics.bang_dieu_khien import router as router_bang_dieu_khien
from app.analytics.khai_pha import router as router_khai_pha
from app.analytics.xuat_du_lieu import router as router_du_lieu_mo
from app.auth.dependencies import current_actor, current_claims, require_roles
from app.config import get_settings
from app.db import SessionLocal, get_session
from app.rate_limit import don_dong_cu
from app.workflow.assignment import router as router_giao_viec
from app.workflow.attachment_routes import router as router_tep
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
from app.workflow.inbox import router as router_hop_thu
from app.workflow.nhip_quet import chay_luot_quet, co_bo_quet_xau, danh_gia_bo_quet
from app.workflow.routes import router as router_yeu_cau

logger = logging.getLogger(__name__)

# Cấu hình nhật ký cho chính ứng dụng.
#
# Uvicorn chỉ cấu hình bộ ghi của riêng nó, nên nếu không có dòng này thì mọi thông
# điệp của dịch vụ đều biến mất — kể cả `logger.exception` trong vòng quét SLA. Một
# tác vụ nền chạy âm thầm và không báo được lỗi là thứ chỉ phát hiện ra khi đã muộn.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
)

settings = get_settings()

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

    yield

    for tac_vu in cac_tac_vu:
        tac_vu.cancel()


app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Dịch vụ ứng dụng của DX-OS Lab. Toàn bộ quy trình nghiệp vụ nằm trong bảng "
        "dữ liệu, không mã cứng trong mã nguồn."
    ),
)


# Vai trò vận hành cụm: gác màn Hệ thống và lệnh quét SLA bằng tay
VAI_TRO_QUAN_TRI = "administrator"

app.include_router(router_yeu_cau)
app.include_router(router_dieu_phoi)
app.include_router(router_giao_viec)
app.include_router(router_phong_ban)
app.include_router(router_hop_thu)
app.include_router(router_tep)
app.include_router(router_du_lieu_mo)
app.include_router(router_bang_dieu_khien)
app.include_router(router_khai_pha)
app.include_router(router_tuong_tu)


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
        "scan_settings": {
            "enabled": settings.sla_scan_enabled,
            "interval_seconds": settings.sla_scan_interval_seconds,
            "stale_after_seconds": settings.sla_scan_stale_threshold_seconds,
            "max_consecutive_errors": settings.sla_scan_max_consecutive_errors,
        },
    }


@app.get("/", tags=["Vận hành"])
def root() -> dict:
    """Chỉ đường tới tài liệu API tự sinh."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/me", tags=["Định danh"])
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

    return {
        "id": actor.id,
        "username": claims.get("preferred_username"),
        "name": claims.get("name"),
        "email": claims.get("email"),
        "roles": sorted(actor.roles),
        "departments": sorted(actor.departments),
        "workspaces": khong_gian,
    }


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
