# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Xếp sự kiện thông báo vào hàng đợi (#251).
#
# Gọi từ bên trong giao dịch nghiệp vụ — cổng chuyển trạng thái, bộ quét hạn chờ — nên phải rẻ và
# không bao giờ gọi mạng: chỉ một câu INSERT. Ai nhận, địa chỉ nào, lời thư ra sao là việc của bộ
# quét gửi (bo_gui.py), chạy sau, ngoài giao dịch nghiệp vụ. Máy chủ thư không cấu hình thì không
# xếp gì: bảng hàng đợi không phình lên ở cụm không bao giờ gửi thư.
#
# Mô-đun này không nhập engine — engine nhập nó.

from __future__ import annotations

from sqlalchemy import exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.case import Request
from app.models.thong_bao import NotificationOutbox, NotificationType

# Ba cơ chế kích hoạt mã biết; loại thông báo nào dùng cơ chế nào là dữ liệu (infra/seed/05)
TRIGGER_VAO_TRANG_THAI = "state-entered"
TRIGGER_BAO_TRUOC = "auto-warning"
TRIGGER_DA_TU_DI = "auto-done"


def xep_hang(
    session: Session,
    trigger: str,
    ho_so: Request,
    *,
    context: dict | None = None,
    actor_id: str | None = None,
    dedupe_key: str | None = None,
) -> None:
    """Ghi một sự kiện vào hàng đợi, trong giao dịch của phiên. Không tự commit.

    Không làm gì khi máy chủ thư tắt, hay khi không loại thông báo nào đang bật dùng cơ chế này.
    `dedupe_key` trùng thì bỏ qua lặng lẽ — mốc báo trước chỉ báo một lần.
    """
    if not get_settings().notify_enabled:
        return
    co_loai = session.scalar(
        select(
            exists().where(NotificationType.trigger == trigger, NotificationType.is_active)
        )
    )
    if not co_loai:
        return
    cau_lenh = insert(NotificationOutbox).values(
        trigger=trigger,
        case_id=ho_so.id,
        context=context or {},
        actor_id=actor_id,
        dedupe_key=dedupe_key,
    )
    session.execute(cau_lenh.on_conflict_do_nothing(index_elements=["dedupe_key"]))
