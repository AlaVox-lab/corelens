# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ghi nhật ký sự kiện.
#
# Đây là NƠI DUY NHẤT trong toàn bộ mã nguồn được phép chèn vào bảng `event_log`.
# Chèn từ chỗ khác không sai về kỹ thuật, nhưng sẽ phá vỡ bảo đảm rằng mỗi bản ghi
# nhật ký tương ứng với đúng một lần chuyển trạng thái đã qua kiểm quyền.
#
# Bảng chỉ ghi thêm: một trigger ở tầng cơ sở dữ liệu chặn mọi UPDATE và DELETE.

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.case import EventLog
from app.workflow.context import TransitionContext


def record_event(session: Session, ctx: TransitionContext) -> EventLog:
    """Ghi một bản ghi nhật ký cho lần chuyển trạng thái đang diễn ra.

    Sáu trường bắt buộc theo ARCHITECTURE.md mục 6 đều lấy từ bối cảnh, không trường
    nào do phía gọi tự điền — nhờ vậy không có cách nào ghi một bản ghi nhật ký lệch
    với lần chuyển thật sự đã xảy ra.

    Mốc thời gian **không đặt từ phía Python**: để PostgreSQL tự điền bằng `now()`.
    Một đồng hồ duy nhất cho cả cụm, thay vì mỗi tiến trình một đồng hồ lệch nhau vài
    giây. Kiểu cột là TIMESTAMPTZ nên giá trị luôn được quy về UTC lúc lưu.
    """
    su_kien = EventLog(
        case_id=ctx.case.id,
        activity=ctx.transition.activity_code,
        actor=ctx.actor.id,
        actor_label=ctx.actor.label,
        from_state=ctx.transition.from_state,
        to_state=ctx.transition.to_state,
        note=ctx.note,
    )
    session.add(su_kien)

    # Đẩy xuống cơ sở dữ liệu ngay để bản ghi nhật ký có mặt TRƯỚC khi hồ sơ đổi
    # trạng thái, đúng thứ tự quy định ở ARCHITECTURE.md mục 6.1. Cả hai vẫn nằm
    # trong một giao dịch nên hoặc cùng thành công, hoặc cùng bị hoàn tác.
    session.flush()

    return su_kien
