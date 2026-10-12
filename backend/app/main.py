# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Điểm vào của dịch vụ ứng dụng.
#
# Điểm cuối nghiệp vụ thuộc #44. Tệp này hiện có kiểm tra sức khỏe và điểm cuối
# danh tính — cổng người dùng gọi nó để biết mình đang đăng nhập bằng ai.

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor, current_claims, require_roles
from app.config import get_settings
from app.db import SessionLocal, get_session
from app.workflow.assignment import router as router_giao_viec
from app.workflow.context import Actor
from app.workflow.coordination import router as router_dieu_phoi
from app.workflow.coordination import vao_duoc_buong_lai
from app.workflow.department import router as router_phong_ban
from app.workflow.department import vao_duoc_phong_ban
from app.workflow.escalation import quet_het_han_cho, quet_va_leo_thang
from app.workflow.inbox import router as router_hop_thu
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

def _quet_mot_lan() -> tuple[list[int], list[int]]:
    """Một lượt quét hồ sơ quá hạn SLA rồi hồ sơ hết hạn chờ (#142), mỗi bộ quét một giao
    dịch riêng. Trả về (hồ sơ đã leo thang, hồ sơ đã tự đi)."""
    with SessionLocal() as phien:
        da_leo_thang = quet_va_leo_thang(phien)
        phien.commit()
    with SessionLocal() as phien:
        da_tu_di = quet_het_han_cho(phien)
        phien.commit()
    return da_leo_thang, da_tu_di


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Bật bộ quét SLA lúc khởi động, tắt gọn lúc dừng."""
    tac_vu = None
    if settings.sla_scan_enabled:
        tac_vu = asyncio.create_task(_vong_quet_sla())
        logger.info(
            "Bộ quét SLA chạy mỗi %d giây", settings.sla_scan_interval_seconds
        )

    yield

    if tac_vu is not None:
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


app.include_router(router_yeu_cau)
app.include_router(router_dieu_phoi)
app.include_router(router_giao_viec)
app.include_router(router_phong_ban)
app.include_router(router_hop_thu)


@app.get("/health", tags=["Vận hành"])
def health(response: Response, session: Session = Depends(get_session)) -> dict:
    """Báo trạng thái dịch vụ và kết nối cơ sở dữ liệu.

    Trả về 503 khi cơ sở dữ liệu không dùng được. Điểm này quan trọng: một điểm cuối
    kiểm tra sức khỏe luôn trả 200 thì vô dụng. Nhóm đã vấp đúng bẫy đó với Apache
    Superset ở #38 — container báo `healthy` trong khi không ai đăng nhập được.
    """
    thong_tin: dict = {
        "service": "dx-os-lab-backend",
        "version": settings.app_version,
    }

    try:
        session.execute(text("SELECT 1"))
    except Exception as loi:  # noqa: BLE001 — cần bắt mọi lỗi kết nối để báo 503
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        thong_tin["status"] = "degraded"
        thong_tin["database"] = "unreachable"
        thong_tin["detail"] = str(loi)[:200]
        return thong_tin

    thong_tin["status"] = "ok"
    thong_tin["database"] = "ok"

    # Đếm trạng thái của bộ quy tắc đang kích hoạt. Con số này chứng minh cả chuỗi
    # khởi tạo đã chạy: lược đồ được tạo, dữ liệu khởi tạo được nạp, các phép kiểm
    # tra tính nhất quán đều qua. Bằng không thì cụm dựng lên nhưng rỗng ruột.
    try:
        so_trang_thai = session.execute(
            text(
                "SELECT count(*) FROM states s"
                " JOIN rule_sets r ON r.id = s.rule_set_id"
                " WHERE r.is_active"
            )
        ).scalar_one()
        thong_tin["active_rule_set_states"] = so_trang_thai
    except Exception:  # noqa: BLE001 — lược đồ chưa nạp thì vẫn coi là suy giảm
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        thong_tin["status"] = "degraded"
        thong_tin["detail"] = "Chưa nạp được lược đồ quy trình"

    return thong_tin


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
    actor: Annotated[Actor, Depends(require_roles("administrator"))],
) -> dict:
    """Chạy ngay một lượt quét hồ sơ quá hạn SLA và hết hạn chờ, không đợi chu kỳ.

    Có hai lý do tồn tại: kiểm chứng cơ chế mà không phải ngồi chờ, và trình diễn
    việc tự leo thang trước người xem.

    Chỉ quản trị viên gọi được. Việc leo thang vẫn đi qua điểm chuyển trạng thái duy
    nhất, nên người bấm nút không ghi đè được luật nào — nhật ký vẫn ghi tác nhân là
    hệ thống, không phải người này.
    """
    da_leo_thang, da_tu_di = _quet_mot_lan()
    return {
        "escalated_count": len(da_leo_thang),
        "escalated_case_ids": da_leo_thang,
        # Hồ sơ hết hạn chờ đã được hệ thống tự đi thay (#142)
        "auto_moved_case_ids": da_tu_di,
        "triggered_by": actor.id,
    }
