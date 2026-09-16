# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Cài đặt các ràng buộc Poka-yoke kiểm tra lúc chạy.
#
# Bảng `guards` trong cơ sở dữ liệu khai MÃ ràng buộc, tệp này cài đặt HÀM tương ứng.
# Bảng `transition_guards` nối mã với từng cạnh. Nhờ tách như vậy, gắn thêm một ràng
# buộc đã có cho một cạnh khác chỉ là thêm một dòng dữ liệu; chỉ khi cần một LOẠI
# ràng buộc mới mới phải viết mã.
#
# Hai trong bốn ràng buộc ở docs/process-flow.md mục 5 KHÔNG có mặt ở đây, vì chúng
# được thực thi bằng cấu trúc chứ không bằng kiểm tra lúc chạy:
#
#   "Đã nhận là không trả về"     — không tồn tại cạnh nào đi ngược
#   "Chỉ hủy trước khi vào xử lý" — cạnh hủy chỉ xuất phát từ bốn trạng thái đầu
#
# Không có đường mà đi thì không cần hàm nào canh cửa.

from __future__ import annotations

from collections.abc import Callable

from app.workflow.context import TransitionContext
from app.workflow.errors import GuardViolation, UnknownGuard

GuardFunc = Callable[[TransitionContext], None]


def requester_owns_case(ctx: TransitionContext) -> None:
    """Người thao tác phải chính là người đã gửi yêu cầu.

    Không có ràng buộc này thì bất kỳ ai mang vai trò `requester` — tức mọi nhân
    viên trong công ty — cũng hủy được hồ sơ của người khác.
    """
    if ctx.actor.id != ctx.case.requester_id:
        raise GuardViolation(
            "requester-owns-case",
            "Chỉ người tạo hồ sơ mới thực hiện được thao tác này.",
        )


def actor_in_case_department(ctx: TransitionContext) -> None:
    """Người thao tác phải thuộc phòng ban đang giữ hồ sơ.

    Chặn việc phòng này can thiệp vào hồ sơ của phòng khác.
    """
    if ctx.case.department_code is None:
        raise GuardViolation(
            "actor-in-case-department",
            "Hồ sơ chưa được chuyển về phòng ban nào.",
        )
    if ctx.case.department_code not in ctx.actor.departments:
        raise GuardViolation(
            "actor-in-case-department",
            "Chỉ người thuộc phòng ban đang giữ hồ sơ mới thao tác được.",
        )


def set_priority(ctx: TransitionContext) -> None:
    """Cạnh này bắt buộc đặt mức ưu tiên.

    Ràng buộc "người tạo yêu cầu không tự đặt mức ưu tiên" được thực thi bằng chỗ
    ĐẶT chứ không bằng chỗ CẤM: ràng buộc này chỉ gắn vào cạnh `submitted → classified`
    của vai trò `classifier`, và không cạnh nào của `requester` mang nó.
    """
    if not ctx.changes.get("priority_code"):
        raise GuardViolation(
            "set-priority",
            "Phải chọn mức ưu tiên khi phân loại yêu cầu.",
        )


def select_department(ctx: TransitionContext) -> None:
    """Cạnh này bắt buộc chọn phòng ban phụ trách.

    Danh sách gợi ý lấy từ bảng `request_type_routing`, nhưng người phân loại được
    chọn khác — và chính những lần chọn khác mặc định là dữ liệu quý cho khai phá
    quy trình: nếu một loại yêu cầu liên tục bị định tuyến khác mặc định thì bảng
    ánh xạ đang sai.
    """
    if not ctx.changes.get("department_code"):
        raise GuardViolation(
            "select-department",
            "Phải chọn phòng ban phụ trách khi chuyển hồ sơ đi.",
        )


def department_unchanged(ctx: TransitionContext) -> None:
    """Cạnh này giữ nguyên phòng ban, chỉ đổi người phụ trách.

    Leo thang là chuyện nội bộ một phòng: quá hạn thì đẩy lên cấp trên trong cùng
    phòng ban, không đá sang phòng khác.
    """
    moi = ctx.changes.get("department_code")
    if moi is not None and moi != ctx.case.department_code:
        raise GuardViolation(
            "department-unchanged",
            "Không được đổi phòng ban ở bước này, chỉ đổi người phụ trách.",
        )


# Hợp đồng giữa dữ liệu và mã nguồn. Khóa phải trùng khít cột `code` của bảng `guards`.
GUARD_REGISTRY: dict[str, GuardFunc] = {
    "requester-owns-case": requester_owns_case,
    "actor-in-case-department": actor_in_case_department,
    "set-priority": set_priority,
    "select-department": select_department,
    "department-unchanged": department_unchanged,
}


def run_guards(ctx: TransitionContext) -> None:
    """Chạy lần lượt mọi ràng buộc gắn với cạnh đang đi.

    Ném `UnknownGuard` nếu bảng dữ liệu khai một mã chưa được cài đặt. Cố ý **không**
    bỏ qua âm thầm: một quản trị viên gắn nhầm mã ràng buộc phải biết ngay, chứ không
    phải phát hiện sau vài tháng rằng ràng buộc đó chưa từng chạy.
    """
    for ma in ctx.transition.guard_codes:
        ham = GUARD_REGISTRY.get(ma)
        if ham is None:
            raise UnknownGuard(
                f"Bảng dữ liệu khai ràng buộc '{ma}' nhưng mã nguồn chưa cài đặt. "
                f"Bổ sung hàm vào app/rules/guards.py hoặc gỡ dòng khai báo trong "
                f"infra/seed/."
            )
        ham(ctx)
