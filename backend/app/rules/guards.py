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
#
# MỖI RÀNG BUỘC CÒN KHAI TRƯỜNG MÀ NÓ QUẢN — xem `GUARD_REGISTRY` cuối tệp. Một lần
# chuyển trạng thái chỉ đặt được những trường mà ràng buộc gắn trên cạnh đó quản. Đây
# là cách mức ưu tiên chỉ đặt được ở cạnh phân loại, chứ không ở bất kỳ cạnh nào mà
# người thao tác tình cờ đi qua.

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from app.workflow.context import TransitionContext
from app.workflow.errors import GuardViolation, UnknownGuard

GuardFunc = Callable[[TransitionContext], None]


@dataclass(frozen=True, slots=True)
class Guard:
    """Một ràng buộc: hàm kiểm tra, cùng tập trường mà ràng buộc đó chịu trách nhiệm.

    Tập trường nằm ở đây, cạnh hàm, chứ không trong bảng dữ liệu. Lý do: mối liên hệ
    là bản chất của chính hàm — `set_priority` đọc `changes["priority_code"]`. Nếu
    khai trong bảng thì dữ liệu có thể nói `set-priority` quản `department_code` trong
    khi mã lại kiểm `priority_code`, và hai nơi âm thầm nói hai điều khác nhau.

    Ràng buộc chỉ đối chiếu người thao tác với hồ sơ — như `requester-owns-case` — thì
    không quản trường nào, và tập để trống.

    `input_free` đánh dấu ràng buộc KHÔNG cần biết người dùng định nhập gì: nó chỉ đối
    chiếu người thao tác, hồ sơ và lịch sử hồ sơ. Loại này chạy được ngay lúc dựng danh
    sách nút (`allowed_transitions`), nên cạnh chắc chắn bị từ chối không hiện ra (#79).
    Ràng buộc đọc `changes` thì để False — lúc chào nút chưa ai biết người dùng sẽ chọn
    gì, và chạy nó với `changes` rỗng sẽ giấu mất những cạnh hoàn toàn đi được.
    """

    check: GuardFunc
    governs: frozenset[str] = frozenset()
    input_free: bool = False


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
    # Kiểm theo sự CÓ MẶT của khóa, không theo giá trị khác None. Gửi kèm
    # `department_code: None` cũng là một lần đổi — thành không thuộc phòng nào — và
    # nếu chỉ kiểm `is not None` thì nó lọt qua, rồi bước cập nhật hồ sơ ghi đè `None`.
    if (
        "department_code" in ctx.changes
        and ctx.changes["department_code"] != ctx.case.department_code
    ):
        raise GuardViolation(
            "department-unchanged",
            "Không được đổi phòng ban ở bước này, chỉ đổi người phụ trách.",
        )


def set_request_type(ctx: TransitionContext) -> None:
    """Hồ sơ phải có loại yêu cầu khi rời khỏi tay người phân loại.

    Người gửi có thể đã chọn loại ngay trên biểu mẫu — khi đó người phân loại giữ
    nguyên hoặc sửa lại. Nếu người gửi bỏ trống thì người phân loại bắt buộc đặt.

    Gắn ở HAI cạnh: `submitted → classified`, và `classified → awaiting-acceptance` —
    cửa duy nhất dẫn tới phòng ban. Cạnh thứ hai là lưới an toàn: trước #79, hồ sơ đi
    vòng qua `awaiting-info` tới `classified` mà không qua cạnh thứ nhất. Từ #79 đường
    vòng đó quay về `submitted` nên phải đi lại cạnh phân loại, nhưng bộ quy tắc là dữ
    liệu — doanh nghiệp thêm một đường mới vào `classified` thì lưới này vẫn đứng.

    Vì sao bắt buộc: loại yêu cầu quyết định ngưỡng SLA, và bộ quét hồ sơ quá hạn nối
    bảng `request_types` bằng phép nối trong. Hồ sơ không có loại sẽ lọt khỏi phép
    quét — **không bao giờ leo thang, và không báo gì cả**. Chặn ở đây là chặn tại
    điểm chạm đầu vào, thay vì phát hiện khi hồ sơ đã trễ hạn cả tuần mà không ai hay.
    """
    if "request_type_code" in ctx.changes:
        if not ctx.changes["request_type_code"]:
            raise GuardViolation(
                "set-request-type",
                "Không được xóa loại yêu cầu khi phân loại.",
            )
        return

    if not ctx.case.request_type_code:
        raise GuardViolation(
            "set-request-type",
            "Người gửi chưa chọn loại yêu cầu, nên phải chọn khi phân loại.",
        )


def assign_handler(ctx: TransitionContext) -> None:
    """Cạnh này cho phép giao hồ sơ cho một người xử lý cụ thể.

    Chưa **bắt buộc** chọn người: hồ sơ vẫn thuộc về cả phòng ban, và mọi người xử lý
    trong phòng đều thao tác được qua ràng buộc `actor-in-case-department`. Bắt buộc
    chỉ có nghĩa khi buồng lái có ô chọn người dùng được — mà ô đó cần tra tên người
    từ Keycloak, việc của #84.

    Nhưng đã gửi thì phải có giá trị. Một chuỗi rỗng ghi xuống cột `assignee_id` sẽ
    trông như "đã giao" trong khi thực ra không giao cho ai.
    """
    if "assignee_id" not in ctx.changes:
        return

    moi = ctx.changes["assignee_id"]
    if not isinstance(moi, str) or not moi.strip():
        raise GuardViolation(
            "assign-handler",
            "Người được giao xử lý không được để trống.",
        )


def return_to_previous_state(ctx: TransitionContext) -> None:
    """Hồ sơ chỉ quay về đúng trạng thái nó đã ở ngay trước trạng thái hiện tại.

    Gắn vào mọi cạnh "trả lời" ra khỏi một trạng thái chờ (#79): ai hỏi thêm thì hồ sơ
    về lại đúng người đó. Hỏi ở *Đã gửi* thì về điều phối để phân loại, hỏi ở *Đang xử
    lý* thì về người xử lý. Không có bảng ánh xạ nào — quy tắc chỉ là "về chỗ cũ", và
    chỗ cũ đọc từ nhật ký sự kiện qua `ctx.previous_state`.

    Không cần giá trị người dùng nhập, nên ràng buộc chạy luôn lúc chào nút: người gửi
    chỉ thấy đúng một nút "Bổ sung thông tin" thay vì phải đoán ai đã hỏi mình. Trước
    #79 họ thấy hai nút gần như giống hệt nhau, và đoán sai là đẩy một hồ sơ đang xử lý
    ngược về hàng đợi phân loại.
    """
    if ctx.transition.to_state != ctx.previous_state:
        raise GuardViolation(
            "return-to-previous-state",
            "Hồ sơ chỉ quay về được đúng bước trước đó, nơi vừa chuyển nó sang đây.",
        )


# Hợp đồng giữa dữ liệu và mã nguồn. Khóa phải trùng khít cột `code` của bảng `guards`.
#
# Cột thứ hai quyết định trường nào đặt được ở cạnh nào. `department-unchanged` quản
# `department_code` dù không cho đổi nó: nó là ràng buộc phán xử trường đó ở cạnh
# phân công lại, nên phải được nhìn thấy trường đó thì mới phán được.
GUARD_REGISTRY: dict[str, Guard] = {
    "requester-owns-case": Guard(requester_owns_case, input_free=True),
    "actor-in-case-department": Guard(actor_in_case_department, input_free=True),
    "set-priority": Guard(set_priority, frozenset({"priority_code"})),
    "select-department": Guard(select_department, frozenset({"department_code"})),
    "department-unchanged": Guard(department_unchanged, frozenset({"department_code"})),
    "set-request-type": Guard(set_request_type, frozenset({"request_type_code"})),
    "assign-handler": Guard(assign_handler, frozenset({"assignee_id"})),
    "return-to-previous-state": Guard(return_to_previous_state, input_free=True),
}

# Mọi trường mà ít nhất một ràng buộc quản. Engine đối chiếu tập này với danh sách
# trường quyết định của nó ngay lúc nạp mô-đun — xem `app/workflow/engine.py`.
GOVERNED_FIELDS: frozenset[str] = frozenset().union(
    *(g.governs for g in GUARD_REGISTRY.values())
)


def _tra_rang_buoc(ma: str) -> Guard:
    """Tra một mã ràng buộc, ném `UnknownGuard` nếu mã nguồn chưa cài đặt.

    Cố ý **không** bỏ qua âm thầm: một quản trị viên gắn nhầm mã ràng buộc phải biết
    ngay, chứ không phải phát hiện sau vài tháng rằng ràng buộc đó chưa từng chạy.
    """
    rang_buoc = GUARD_REGISTRY.get(ma)
    if rang_buoc is None:
        raise UnknownGuard(
            f"Bảng dữ liệu khai ràng buộc '{ma}' nhưng mã nguồn chưa cài đặt. "
            f"Bổ sung hàm vào app/rules/guards.py hoặc gỡ dòng khai báo trong "
            f"infra/seed/."
        )
    return rang_buoc


def permitted_fields(guard_codes: Iterable[str]) -> frozenset[str]:
    """Những trường mà một cạnh mang các ràng buộc này cho phép đặt.

    Cạnh không mang ràng buộc nào quản trường nào thì trả tập rỗng — lần chuyển đó
    không được kèm trường quyết định nào cả.
    """
    return frozenset().union(*(_tra_rang_buoc(ma).governs for ma in guard_codes))


def run_guards(ctx: TransitionContext) -> None:
    """Chạy lần lượt mọi ràng buộc gắn với cạnh đang đi."""
    for ma in ctx.transition.guard_codes:
        _tra_rang_buoc(ma).check(ctx)


def input_free_guards_pass(ctx: TransitionContext) -> bool:
    """Cạnh có qua được mọi ràng buộc không cần nhập liệu không. Dùng lúc chào nút.

    Chỉ nuốt `GuardViolation`. Mã ràng buộc chưa cài đặt vẫn ném `UnknownGuard` như ở
    `run_guards`: giấu nút đi thì cấu hình sai sẽ trông như "không có thao tác nào".
    """
    try:
        for ma in ctx.transition.guard_codes:
            rang_buoc = _tra_rang_buoc(ma)
            if rang_buoc.input_free:
                rang_buoc.check(ctx)
    except GuardViolation:
        return False
    return True
