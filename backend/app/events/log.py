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


# Trường quyết định nào có cột tên đi kèm trên hồ sơ. Định danh Keycloak không tự nói
# lên người nào, nên nhật ký ghi thêm tên của người cũ và người mới tại thời điểm đổi —
# cùng lý do với `actor_label`.
_TEN_DI_KEM = {"assignee_id": "assignee_label"}


def _thay_doi_truong(ctx: TransitionContext, assignee_label: str | None) -> dict | None:
    """Những trường mà lần chuyển này thật sự đổi giá trị, kèm giá trị cũ và mới (#100).

    Gửi lại đúng giá trị đang có thì không tính là đổi: điều phối viên giữ nguyên loại
    người gửi đã chọn không được sinh ra một dòng "A → A".
    """
    doi: dict = {}
    for truong, moi in ctx.changes.items():
        cu = getattr(ctx.case, truong)
        if cu == moi:
            continue
        muc = {"from": cu, "to": moi}
        cot_ten = _TEN_DI_KEM.get(truong)
        if cot_ten:
            muc["from_label"] = getattr(ctx.case, cot_ten)
            muc["to_label"] = assignee_label if moi else None
        doi[truong] = muc
    return doi or None


def record_event(
    session: Session,
    ctx: TransitionContext,
    *,
    assignee_label: str | None = None,
    suggestion: dict | None = None,
) -> EventLog:
    """Ghi một bản ghi nhật ký cho lần chuyển trạng thái đang diễn ra.

    Sáu trường bắt buộc theo ARCHITECTURE.md mục 6 đều lấy từ bối cảnh, không trường
    nào do phía gọi tự điền — nhờ vậy không có cách nào ghi một bản ghi nhật ký lệch
    với lần chuyển thật sự đã xảy ra.

    Mốc thời gian **không đặt từ phía Python**: để PostgreSQL tự điền bằng `now()`.
    Một đồng hồ duy nhất cho cả cụm, thay vì mỗi tiến trình một đồng hồ lệch nhau vài
    giây. Kiểu cột là TIMESTAMPTZ nên giá trị luôn được quy về UTC lúc lưu.

    Phải gọi TRƯỚC khi hồ sơ được cập nhật: phần "từ → sang" đọc giá trị cũ từ chính
    hồ sơ. `assignee_label` là tên người được giao mới, do phía gọi tra từ danh bạ.
    `suggestion` là dấu giữ hay ghi đè gợi ý (#239), do cửa chuyển trạng thái tính bằng
    `app.intelligence.goi_y.ghi_nhan_goi_y` — đi vào cột riêng, không trộn vào `changes`.
    """
    su_kien = EventLog(
        case_id=ctx.case.id,
        activity=ctx.transition.activity_code,
        actor=ctx.actor.id,
        actor_label=ctx.actor.label,
        from_state=ctx.transition.from_state,
        to_state=ctx.transition.to_state,
        note=ctx.note,
        changes=_thay_doi_truong(ctx, assignee_label),
        suggestion=suggestion,
    )
    session.add(su_kien)

    # Đẩy xuống cơ sở dữ liệu ngay để bản ghi nhật ký có mặt TRƯỚC khi hồ sơ đổi
    # trạng thái, đúng thứ tự quy định ở ARCHITECTURE.md mục 6.1. Cả hai vẫn nằm
    # trong một giao dịch nên hoặc cùng thành công, hoặc cùng bị hoàn tác.
    session.flush()

    return su_kien
