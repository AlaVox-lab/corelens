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
from typing import Any

from app.models.case import MO_TA_TOI_DA, TIEU_DE_TOI_DA, TIEU_DE_TOI_THIEU
from app.workflow.context import TransitionContext
from app.workflow.errors import GuardViolation, UnknownGuard

GuardFunc = Callable[[TransitionContext], None]
EffectFunc = Callable[[TransitionContext], dict[str, Any]]


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

    `effect` là **tác động** của ràng buộc (ADR-0005, #127): những trường nó TỰ ĐẶT sau
    khi mọi ràng buộc đã qua, với giá trị suy từ bối cảnh chứ không do người dùng gửi —
    ví dụ tự nhận việc đặt người xử lý bằng chính người thao tác. `sets` khai những
    trường đó. Trường trong `sets` KHÔNG nằm trong `governs`: người dùng không gửi được
    chúng, nên cạnh mang ràng buộc này không có ô nhập, và không biến người đi cạnh
    thành "vai trò giao việc" (#84 suy vai trò đó từ những cạnh cho đặt người xử lý).
    """

    check: GuardFunc
    governs: frozenset[str] = frozenset()
    input_free: bool = False
    sets: frozenset[str] = frozenset()
    effect: EffectFunc | None = None


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


def actor_not_requester(ctx: TransitionContext) -> None:
    """Người thao tác không được là người đã gửi hồ sơ (#154).

    Gắn vào các cạnh của vai điều phối. Một người vừa gửi yêu cầu vừa là điều phối viên
    thì không tự phân loại, tự đặt mức ưu tiên, tự chuyển phòng hay tự đóng hồ sơ của
    chính mình — ràng buộc "người tạo không tự đặt mức ưu tiên" sẽ bị vòng qua nếu một
    người giữ cả hai vai. Phòng ban thì không gắn: nhân viên tự sửa máy của mình là
    chuyện bình thường. Cạnh nào mang ràng buộc này là chuyện của dữ liệu khởi tạo.
    """
    if ctx.actor.id == ctx.case.requester_id:
        raise GuardViolation(
            "actor-not-requester",
            "Đây là hồ sơ bạn gửi — một điều phối viên khác sẽ phân loại và chuyển phòng.",
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


def edit_content(ctx: TransitionContext) -> None:
    """Người gửi sửa nội dung hồ sơ khi hồ sơ chưa tới phòng ban (#127, ADR-0005).

    Chỉ ĐƯỢC sửa ở đâu là chuyện của dữ liệu: ràng buộc này gắn vào cạnh nào thì sửa
    được ở đó. Tới phòng ban rồi thì không còn cạnh sửa nào — khóa bằng sự vắng mặt, như
    ràng buộc "chỉ hủy trước khi vào xử lý".

    Nội dung gốc không bị ghi đè: hồ sơ mang giá trị mới, còn cột `changes` của nhật ký
    giữ giá trị cũ (#100) — tầng `I` vẫn dựng lại được văn bản lúc điều phối viên phân
    loại.

    Cùng giới hạn độ dài với lúc gửi, để một hồ sơ không lọt qua bằng đường sửa những gì
    biểu mẫu gửi đã chặn. Và phải thật sự đổi một thứ gì đó: một dòng nhật ký "sửa nội
    dung" mà không có gì đổi chỉ là nhiễu cho khai phá quy trình. Không gửi trường nào
    cũng rơi vào đúng phép kiểm đó, vì `all()` của một tập rỗng là đúng.
    """
    if "title" in ctx.changes:
        tieu_de = ctx.changes["title"]
        if not isinstance(tieu_de, str) or not (
            TIEU_DE_TOI_THIEU <= len(tieu_de.strip()) and len(tieu_de) <= TIEU_DE_TOI_DA
        ):
            raise GuardViolation(
                "edit-content",
                f"Tiêu đề phải dài từ {TIEU_DE_TOI_THIEU} tới {TIEU_DE_TOI_DA} ký tự.",
            )

    if "description" in ctx.changes:
        mo_ta = ctx.changes["description"]
        if mo_ta is not None and (not isinstance(mo_ta, str) or len(mo_ta) > MO_TA_TOI_DA):
            raise GuardViolation(
                "edit-content", f"Mô tả dài tối đa {MO_TA_TOI_DA} ký tự."
            )

    # Cùng lý do với set-request-type: hồ sơ không có loại thì không có ngưỡng SLA
    if "request_type_code" in ctx.changes and not ctx.changes["request_type_code"]:
        raise GuardViolation("edit-content", "Không được xóa loại yêu cầu khi sửa nội dung.")

    if all(ctx.changes[truong] == getattr(ctx.case, truong) for truong in ctx.changes):
        raise GuardViolation(
            "edit-content", "Chưa có gì thay đổi so với nội dung đang có."
        )


def assign_self(ctx: TransitionContext) -> None:
    """Người xử lý nhận về mình một hồ sơ chưa giao cho ai (#127, ADR-0005).

    Giữ việc giao người là tùy chọn — ngoài đời người trong phòng hay tự chia việc — mà
    vẫn cho hồ sơ một người giữ: có tên trong bộ lọc "Giao cho tôi", không hai người làm
    trùng, leo thang biết hỏi ai.

    Chỉ khi hồ sơ CHƯA giao ai. Hồ sơ đã có người thì phải nhờ trưởng phòng phân công lại
    — tự nhận không phải cách giành việc của đồng nghiệp. Không cần nhập liệu nên chạy
    luôn lúc chào nút: hồ sơ đã có người giữ thì nút không hiện.
    """
    if ctx.case.assignee_id:
        raise GuardViolation(
            "assign-self",
            "Hồ sơ đã giao cho người khác. Muốn đổi người thì nhờ trưởng phòng phân công lại.",
        )


def _giao_cho_nguoi_thao_tac(ctx: TransitionContext) -> dict[str, Any]:
    """Tác động của `assign-self`: người xử lý là chính người thao tác."""
    return {"assignee_id": ctx.actor.id}


# Hợp đồng giữa dữ liệu và mã nguồn. Khóa phải trùng khít cột `code` của bảng `guards`.
#
# Cột thứ hai quyết định trường nào đặt được ở cạnh nào. `department-unchanged` quản
# `department_code` dù không cho đổi nó: nó là ràng buộc phán xử trường đó ở cạnh
# phân công lại, nên phải được nhìn thấy trường đó thì mới phán được.
GUARD_REGISTRY: dict[str, Guard] = {
    "requester-owns-case": Guard(requester_owns_case, input_free=True),
    "actor-in-case-department": Guard(actor_in_case_department, input_free=True),
    "actor-not-requester": Guard(actor_not_requester, input_free=True),
    "set-priority": Guard(set_priority, frozenset({"priority_code"})),
    "select-department": Guard(select_department, frozenset({"department_code"})),
    "department-unchanged": Guard(department_unchanged, frozenset({"department_code"})),
    "set-request-type": Guard(set_request_type, frozenset({"request_type_code"})),
    "assign-handler": Guard(assign_handler, frozenset({"assignee_id"})),
    "return-to-previous-state": Guard(return_to_previous_state, input_free=True),
    "edit-content": Guard(
        edit_content, frozenset({"title", "description", "request_type_code"})
    ),
    "assign-self": Guard(
        assign_self,
        input_free=True,
        sets=frozenset({"assignee_id"}),
        effect=_giao_cho_nguoi_thao_tac,
    ),
}

# Mọi trường mà ít nhất một ràng buộc quản hoặc tự đặt. Engine đối chiếu tập này với
# biên ngoài của nó ngay lúc nạp mô-đun — xem `app/workflow/engine.py`.
GOVERNED_FIELDS: frozenset[str] = frozenset().union(
    *(g.governs | g.sets for g in GUARD_REGISTRY.values())
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


def apply_effects(ctx: TransitionContext) -> dict[str, Any]:
    """Những trường mà ràng buộc trên cạnh này tự đặt. Gọi SAU `run_guards`.

    Tác động chỉ được đặt đúng trường nó đã khai ở `sets`. Khai một đằng làm một nẻo thì
    biên ngoài kiểm lúc nạp mô-đun trở nên vô nghĩa, nên lệch là nổ ngay.
    """
    tac_dong: dict[str, Any] = {}
    for ma in ctx.transition.guard_codes:
        rang_buoc = _tra_rang_buoc(ma)
        if rang_buoc.effect is None:
            continue
        ket_qua = rang_buoc.effect(ctx)
        ngoai_khai_bao = set(ket_qua) - rang_buoc.sets
        if ngoai_khai_bao:
            raise RuntimeError(
                f"Ràng buộc '{ma}' đặt trường chưa khai trong `sets`: "
                f"{', '.join(sorted(ngoai_khai_bao))}"
            )
        tac_dong.update(ket_qua)
    return tac_dong


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
