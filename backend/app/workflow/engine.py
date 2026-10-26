# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# ĐIỂM CHUYỂN TRẠNG THÁI DUY NHẤT.
#
# Mọi lần đổi trạng thái hồ sơ trong toàn hệ thống đi qua đúng hàm
# `perform_transition` dưới đây. Không tồn tại đường nào khác.
#
# Vì sao chặt tới mức đó: nhật ký sự kiện chỉ có giá trị nếu KHÔNG BAO GIỜ thiếu bản
# ghi. Một nhật ký thủng làm sai lệch kết quả khai phá quy trình, và khi đó điểm sáng
# tạo của đề tài mất giá trị. Xem ARCHITECTURE.md mục 6.1 và ADR-0004.
#
# Gán thẳng vào `request.current_state` ở bất kỳ chỗ nào khác là vi phạm khuôn mẫu,
# kể cả khi nó "chỉ sửa một trường".

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.log import record_event
from app.models.case import EventLog, Request
from app.models.workflow_config import (
    Department,
    Priority,
    RequestType,
    Role,
    RuleSet,
    State,
    Transition,
)
from app.rules.guards import (
    GOVERNED_FIELDS,
    apply_effects,
    input_free_guards_pass,
    permitted_fields,
    run_guards,
)
from app.rules.sla import cap_nhat_dong_ho
from app.workflow.context import Actor, TransitionContext
from app.workflow.errors import (
    CaseNotFound,
    FieldNotPermitted,
    InvalidFieldValue,
    NoteRequired,
    RoleNotPermitted,
    SystemTransitionOnly,
    TransitionNotAllowed,
)

# Biên NGOÀI của những trường một lần chuyển trạng thái có thể đặt: bốn trường quyết
# định, và từ #127 hai trường nội dung mà người gửi sửa được khi hồ sơ chưa tới phòng
# ban (ADR-0005). Biên trong — trường nào đặt được ở cạnh nào — do ràng buộc gắn trên
# cạnh quyết định, xem `permitted_fields` trong `app/rules/guards.py`.
#
# Nội dung đi qua đúng cửa này, không qua một điểm cuối "sửa hồ sơ" riêng, để mọi lần
# sửa đều có dòng nhật ký giữ giá trị cũ — nội dung gốc không bị ghi đè mất dấu.
#
# Biên ngoài được giữ LÚC NẠP MÔ-ĐUN chứ không lúc chạy: nếu mọi trường mà ràng buộc
# quản đều nằm trong biên, thì mọi trường mà một cạnh cho đặt cũng nằm trong biên.
# Cấu hình sai thì dịch vụ không khởi động; dữ liệu gửi sai thì lần chuyển bị từ chối.
#
# `current_state` cố ý KHÔNG có mặt: nó do engine tự đặt sau khi đã ghi nhật ký. Các
# trường `suggested_*` cũng không: tầng I ghi vào chúng theo đường riêng, và nguyên
# tắc bất di dịch là AI không bao giờ chạm vào trường quyết định — CLAUDE.md mục 4.3.
CHANGEABLE_FIELDS = frozenset(
    {
        "request_type_code",
        "department_code",
        "priority_code",
        "assignee_id",
        "title",
        "description",
        # Gia hạn xử lý (#101): số giờ lần này do người nhập; tổng và số lần do ràng buộc
        # `extend-deadline` tự đặt
        "sla_extension_hours",
        "sla_extension_total_hours",
        "sla_extension_count",
        # Mở lại có giới hạn (#102): số lần do ràng buộc `reopen-limit` tự đặt
        "reopen_count",
    }
)

# Kiểm ngay lúc nạp mô-đun: không ràng buộc nào được quản một trường nằm ngoài biên.
#
# Ai đó thêm vào `GUARD_REGISTRY` một ràng buộc quản `current_state` hay
# `suggested_priority_code` thì dịch vụ **không khởi động được**, thay vì chạy tiếp với
# một đường ghi lén vào trường không được phép.
#
# Đây là chỗ DUY NHẤT giữ biên ngoài. Đừng gỡ nó với ý nghĩ "phép kiểm theo cạnh đã
# chặn rồi" — phép kiểm theo cạnh chỉ chặn trường mà ràng buộc không quản, còn chính
# phép kiểm này mới bảo đảm ràng buộc không quản trường cấm.
_VUOT_BIEN = GOVERNED_FIELDS - CHANGEABLE_FIELDS
if _VUOT_BIEN:
    raise RuntimeError(
        "Ràng buộc trong app/rules/guards.py quản trường nằm ngoài CHANGEABLE_FIELDS: "
        f"{', '.join(sorted(_VUOT_BIEN))}"
    )


# Trường quyết định nào phải tra danh mục nào. Cùng bản chất với khóa ngoại trong lược
# đồ — đây là cấu trúc dữ liệu, không phải quy tắc nghiệp vụ — nhưng kiểm ở tầng ứng
# dụng để trả lời bằng 422 kèm tên trường, thay vì để khóa ngoại nổ thành 500.
#
# `assignee_id` không có mặt: nó là định danh Keycloak, và danh mục của nó nằm trong
# Keycloak chứ không trong cơ sở dữ liệu. Engine không gọi ra ngoài, nên việc kiểm
# người được giao nằm ở tầng điểm cuối — `kiem_nguoi_duoc_giao` trong
# app/workflow/assignment.py — và MỌI điểm cuối nhận `changes` đều gọi qua đó (#83).
DANH_MUC_CUA_TRUONG = {
    "department_code": Department,
    "priority_code": Priority,
    "request_type_code": RequestType,
}


def _kiem_gia_tri_danh_muc(session: Session, thay_doi: dict) -> None:
    """Mọi giá trị gửi kèm phải có trong danh mục, và danh mục đó còn hoạt động.

    Giá trị rỗng thì bỏ qua ở đây: ràng buộc Poka-yoke gắn trên cạnh mới là nơi quyết
    định rỗng có được phép hay không — `set-priority` thì không, còn ở cạnh phân công
    lại thì phòng ban vốn không được đổi.
    """
    for truong, gia_tri in thay_doi.items():
        mo_hinh = DANH_MUC_CUA_TRUONG.get(truong)
        if mo_hinh is None or gia_tri is None or gia_tri == "":
            continue

        if not isinstance(gia_tri, str):
            raise InvalidFieldValue(
                truong, gia_tri, f"Giá trị của {truong} phải là một mã dạng chuỗi."
            )

        ban_ghi = session.get(mo_hinh, gia_tri)
        # Danh mục mức ưu tiên không có cột is_active: mọi mức đều luôn dùng được.
        if ban_ghi is None or not getattr(ban_ghi, "is_active", True):
            raise InvalidFieldValue(
                truong,
                gia_tri,
                f"'{gia_tri}' không có trong danh mục đang dùng của {truong}.",
            )


def _nhan_trang_thai(session: Session, rule_set_id: int, ma: str) -> str:
    """Nhãn tiếng Việt của một trạng thái, để thông báo lỗi không lộ mã tiếng Anh (#157)."""
    trang_thai = session.get(State, (rule_set_id, ma))
    return trang_thai.label if trang_thai is not None else ma


def _nhan_vai_tro(session: Session, ma: str) -> str:
    """Nhãn tiếng Việt của một vai trò, cùng lý do với `_nhan_trang_thai`."""
    vai_tro = session.get(Role, ma)
    return vai_tro.label if vai_tro is not None else ma


def get_active_rule_set(session: Session) -> RuleSet:
    """Bộ quy tắc đang kích hoạt. Hồ sơ mới luôn nhận bộ này."""
    bo = session.scalars(select(RuleSet).where(RuleSet.is_active)).one()
    return bo


def kiem_loai_yeu_cau(session: Session, ma: str | None) -> str | None:
    """Đối chiếu một mã loại yêu cầu với danh mục đang hoạt động.

    Trả lại chính mã đó khi hợp lệ, `None` khi người gọi không truyền gì. Ném
    `ValueError` khi mã không có trong danh mục hoặc đã ngừng dùng.

    Tách thành hàm riêng để điểm cuối và engine dùng chung đúng một phép kiểm. Nếu mỗi
    nơi tự kiểm lấy, hai nơi sẽ lệch nhau ngay lần đầu danh mục đổi — mà danh mục thì
    chắc chắn đổi, vì mỗi doanh nghiệp khai lại danh mục của họ.
    """
    if ma is None:
        return None

    loai = session.get(RequestType, ma)
    if loai is None or not loai.is_active:
        raise ValueError(f"Loại yêu cầu không có trong danh mục: {ma!r}")
    return ma


def kiem_ho_so_goc(session: Session, ma: int | None, requester_id: str) -> int | None:
    """Đối chiếu hồ sơ cũ mà hồ sơ mới tạo lại (#102). Trả lại chính mã đó khi hợp lệ.

    Ném `ValueError` khi hồ sơ không có, không phải của người gửi này, hay chưa ở trạng thái kết
    thúc — hồ sơ đang chạy thì mở lại hay chờ xử lý tiếp, không tạo bản sao. Nội dung lỗi giống
    nhau cho "không có" và "của người khác", để không lộ hồ sơ của người khác có tồn tại.

    Cố ý không đòi hết lượt mở lại hay quá cửa sổ: người gửi muốn tạo lại hồ sơ Không tiếp
    nhận hay hồ sơ đã đóng với thông tin khác thì không có gì sai. Giao diện chỉ mời tạo mới ở
    đúng những chỗ hết đường mở lại.
    """
    if ma is None:
        return None

    goc = session.get(Request, ma)
    trang_thai = (
        session.get(State, (goc.rule_set_id, goc.current_state)) if goc is not None else None
    )
    if (
        goc is None
        or goc.requester_id != requester_id
        or trang_thai is None
        or not trang_thai.is_terminal
    ):
        raise ValueError(f"Hồ sơ gốc không hợp lệ: {ma!r}")
    return ma


def create_case(
    session: Session,
    *,
    title: str,
    requester_id: str,
    description: str | None = None,
    request_type_code: str | None = None,
    requester_label: str | None = None,
    parent_request_id: int | None = None,
) -> Request:
    """Tạo một hồ sơ mới ở trạng thái bắt đầu của bộ quy tắc đang kích hoạt.

    Trạng thái bắt đầu **tra từ bảng** qua cờ `is_initial`, không viết cứng tên trạng
    thái nào vào mã nguồn. Đổi điểm vào của luồng chỉ là sửa dữ liệu khởi tạo.

    `request_type_code` là trường quyết định duy nhất người gửi tự đặt được, và vẫn
    phải nằm trong danh mục đang hoạt động. Mức ưu tiên, phòng ban và người xử lý thì
    không — xem chú thích ở `app/models/case.py`.

    `parent_request_id` là hồ sơ cũ mà hồ sơ này tạo lại (#102). Engine không kiểm nó: người
    gọi kiểm hồ sơ cũ có tồn tại, của chính người gửi và đã kết thúc bằng `kiem_ho_so_goc`.

    **Việc tạo hồ sơ không sinh bản ghi nhật ký**, vì nó không phải một lần *chuyển*
    trạng thái — không có trạng thái nào trước nó. Mốc bắt đầu của hồ sơ là cột
    `created_at`. Khi xuất dữ liệu cho khai phá quy trình, tầng `D` dựng thêm một sự
    kiện mở đầu từ cột đó nếu công cụ phân tích cần.
    """
    bo_quy_tac = get_active_rule_set(session)

    trang_thai_dau = session.scalars(
        select(State).where(
            State.rule_set_id == bo_quy_tac.id,
            State.is_initial,
        )
    ).one()

    ho_so = Request(
        rule_set_id=bo_quy_tac.id,
        current_state=trang_thai_dau.code,
        title=title,
        description=description,
        requester_id=requester_id,
        requester_label=requester_label,
        request_type_code=kiem_loai_yeu_cau(session, request_type_code),
        parent_request_id=parent_request_id,
    )
    session.add(ho_so)
    session.flush()
    return ho_so


def allowed_transitions(
    session: Session, case: Request, actor: Actor
) -> list[Transition]:
    """Những cạnh mà tác nhân này đi được từ trạng thái hiện tại của hồ sơ.

    Dùng để dựng danh sách nút bấm trên giao diện ở #44 và #45. Giao diện chỉ hiển
    thị thứ đi được là nửa đầu của Poka-yoke; nửa sau là engine vẫn kiểm lại khi
    yêu cầu thật gửi lên. Chặn ở giao diện thôi thì không đủ.

    Hàm chạy những ràng buộc **không cần nhập liệu** (`input_free`, #79) — người thao
    tác có phải người tạo hồ sơ không, có thuộc phòng đang giữ hồ sơ không, cạnh có
    quay về đúng chỗ cũ không. Cạnh chắc chắn bị từ chối thì không hiện ra. Ràng buộc
    cần biết người dùng định đặt giá trị gì thì chưa chạy được ở đây, nên một cạnh hiện
    ra vẫn có thể bị từ chối lúc thực hiện.
    """
    cac_canh = session.scalars(
        select(Transition)
        .where(
            Transition.rule_set_id == case.rule_set_id,
            Transition.from_state == case.current_state,
        )
        .order_by(Transition.display_order)
    ).all()

    truoc = _trang_thai_truoc(session, case.id)
    return [
        c
        for c in cac_canh
        if _actor_can_traverse(actor, c)
        and input_free_guards_pass(
            TransitionContext(case=case, transition=c, actor=actor, previous_state=truoc)
        )
    ]


def perform_transition(
    session: Session,
    *,
    case_id: int,
    to_state: str,
    actor: Actor,
    note: str | None = None,
    changes: dict | None = None,
    assignee_label: str | None = None,
) -> Request:
    """Đổi trạng thái một hồ sơ. Đây là cánh cửa duy nhất.

    Năm bước, đúng thứ tự quy định ở ARCHITECTURE.md mục 6.1:

    1. Tra bảng quy tắc — cạnh không có trong bảng thì không đi được
    2. Kiểm quyền theo vai trò
    3. Chạy ràng buộc Poka-yoke
    4. Ghi nhật ký sự kiện
    5. Cập nhật hồ sơ

    Toàn bộ nằm trong giao dịch của phiên đang mở, nên hoặc nhật ký và trạng thái
    cùng thay đổi, hoặc cả hai cùng không. Không có khe nào để nhật ký thủng.

    Hàm **không tự commit**: phía gọi quyết định ranh giới giao dịch. Nhờ vậy một
    yêu cầu HTTP gói được nhiều thao tác, và bộ kiểm thử hoàn tác sạch sau mỗi bài.

    `assignee_label` là tên của người được giao, chỉ được ghi khi lần chuyển này đặt
    `assignee_id`. Engine không tự tra tên — nó không biết Keycloak tồn tại. Phía gọi
    tra danh bạ và kiểm người đó nhận được việc trước khi gọi vào đây (#83), cùng cách
    `create_case` nhận `requester_label`.
    """
    # Khóa dòng hồ sơ tới cuối giao dịch. Không có bước này, hai yêu cầu đồng thời
    # cùng đọc trạng thái cũ rồi cùng ghi nhật ký — sinh ra hai bản ghi cho một lần
    # chuyển, hoặc tệ hơn là hai lần chuyển từ cùng một trạng thái nguồn.
    ho_so = session.get(Request, case_id, with_for_update=True)
    if ho_so is None:
        raise CaseNotFound(f"Không tìm thấy hồ sơ mang định danh {case_id}.")

    # --- Bước 1: tra bảng quy tắc -----------------------------------------
    # Một cặp trạng thái có thể có cả cạnh người lẫn cạnh hệ thống (#142) — chọn theo loại
    # tác nhân. Người gọi nhầm loại thì không thấy cạnh của mình và nhận lỗi quyền ở bước 2
    # qua cạnh kia, như trước khi có cặp đôi.
    canh = session.scalars(
        select(Transition)
        .where(
            Transition.rule_set_id == ho_so.rule_set_id,
            Transition.from_state == ho_so.current_state,
            Transition.to_state == to_state,
        )
        .order_by(Transition.is_system != actor.is_system)
        .limit(1)
    ).one_or_none()

    if canh is None:
        # Nhãn chứ không phải mã: người gặp lỗi này thường là người bấm một nút của trang đã cũ
        # — hồ sơ vừa được người khác chuyển đi — và họ đọc được nhãn, không đọc được mã
        tu = _nhan_trang_thai(session, ho_so.rule_set_id, ho_so.current_state)
        den = _nhan_trang_thai(session, ho_so.rule_set_id, to_state)
        raise TransitionNotAllowed(
            f"Từ “{tu}” không đi được sang “{den}”. Hồ sơ có thể vừa đổi trạng thái — "
            f"tải lại trang để xem trạng thái mới nhất."
        )

    # --- Bước 2: kiểm quyền ------------------------------------------------
    if canh.is_system and not actor.is_system:
        raise SystemTransitionOnly(
            f"Bước “{canh.activity_label}” do hệ thống tự thực hiện, người dùng không "
            f"bấm được."
        )
    if not canh.is_system and actor.is_system:
        raise RoleNotPermitted(
            f"Tác nhân hệ thống không thực hiện được “{canh.activity_label}” — "
            f"bước này thuộc về con người."
        )
    if not canh.is_system and not (actor.roles & canh.role_codes):
        danh_cho = ", ".join(sorted(_nhan_vai_tro(session, ma) for ma in canh.role_codes))
        raise RoleNotPermitted(
            f"Vai trò hiện tại không thực hiện được “{canh.activity_label}”. "
            f"Bước này dành cho: {danh_cho or 'không ai'}."
        )

    if canh.requires_note and not (note and note.strip()):
        # Ô ghi chú không phải lúc nào cũng là "lý do": ở cạnh bổ sung thông tin nó là
        # chính thông tin người gửi trả lời. Tên ô lấy từ dữ liệu của cạnh (#79).
        ghi_gi = f"'{canh.note_label}'" if canh.note_label else "lý do"
        raise NoteRequired(
            f"Thao tác '{canh.activity_label}' bắt buộc ghi {ghi_gi}."
        )

    # Trường gửi kèm phải được một ràng buộc gắn trên CẠNH NÀY quản. Mức ưu tiên chỉ
    # đặt được ở cạnh phân loại, không ở cạnh hoàn thành xử lý. Thiếu phép kiểm này thì
    # ai đi được một cạnh bất kỳ cũng sửa được mọi trường quyết định — người xử lý tự
    # nâng mức ưu tiên việc của mình. Đó là lỗ hổng mà #78 vá.
    #
    # Không cần kiểm riêng `CHANGEABLE_FIELDS` ở đây. Trường được phép là tập con của
    # trường được ràng buộc quản, mà tập đó đã được kiểm nằm trong `CHANGEABLE_FIELDS`
    # ngay lúc nạp mô-đun — xem đầu tệp. Nên `current_state` hay `suggested_*` không
    # bao giờ lọt qua phép kiểm dưới đây. Phép thử đột biến ở #78 xác nhận điều này:
    # thêm một phép kiểm biên ngoài lúc chạy thì gỡ nó đi cũng không bài nào đổ, vì nó
    # không bao giờ tự mình chặn được gì.
    thay_doi = dict(changes or {})
    ngoai_canh = set(thay_doi) - permitted_fields(canh.guard_codes)
    if ngoai_canh:
        raise FieldNotPermitted(
            ngoai_canh,
            f"Thao tác '{canh.activity_label}' không đặt được "
            f"{', '.join(sorted(ngoai_canh))}.",
        )

    _kiem_gia_tri_danh_muc(session, thay_doi)

    ctx = TransitionContext(
        case=ho_so,
        transition=canh,
        actor=actor,
        note=note,
        changes=thay_doi,
        previous_state=_trang_thai_truoc(session, ho_so.id),
    )

    # --- Bước 3: ràng buộc Poka-yoke ---------------------------------------
    run_guards(ctx)

    # Tác động của ràng buộc — ví dụ tự nhận việc đặt người xử lý bằng chính người thao
    # tác (#127). Làm sau khi MỌI ràng buộc đã qua, và trước bước ghi nhật ký, để dòng
    # nhật ký có đủ phần "từ → sang" như mọi thay đổi khác. `ctx.changes` là chính dict
    # `thay_doi`, nên bước 4 và bước 5 cùng thấy trường vừa đặt.
    tac_dong = apply_effects(ctx)
    if tac_dong:
        thay_doi.update(tac_dong)
        # Người tự nhận việc thì tên người xử lý là tên của chính họ trong token
        if "assignee_id" in tac_dong and assignee_label is None:
            assignee_label = actor.label

    # --- Bước 4: ghi nhật ký TRƯỚC -----------------------------------------
    # Lúc này hồ sơ chưa bị ghi đè, nên nhật ký còn đọc được giá trị cũ để ghi phần
    # "từ → sang" (#100). Sau bước 5 thì giá trị cũ mất.
    record_event(session, ctx, assignee_label=assignee_label)

    # --- Bước 5: rồi mới cập nhật hồ sơ ------------------------------------
    for truong, gia_tri in thay_doi.items():
        setattr(ho_so, truong, gia_tri)
    # Tên đi cùng định danh: đổi người thì đổi tên, kể cả về rỗng, để hai cột không
    # bao giờ kể hai người khác nhau.
    if "assignee_id" in thay_doi:
        ho_so.assignee_label = assignee_label if thay_doi["assignee_id"] else None

    # Chốt đoạn đồng hồ SLA đang mở rồi mở đoạn mới. Phải gọi TRƯỚC khi đổi
    # `current_state`, vì hàm cần biết hồ sơ đang rời khỏi trạng thái nào.
    # Kế toán thời gian là một phần của việc cập nhật hồ sơ, nên nó nằm trong bước 5
    # chứ không thành bước thứ sáu — năm bước ở ARCHITECTURE.md mục 6.1 giữ nguyên.
    cap_nhat_dong_ho(session, ho_so, canh)

    ho_so.current_state = canh.to_state

    session.flush()
    return ho_so


def case_history(session: Session, case_id: int) -> list[EventLog]:
    """Toàn bộ nhật ký của một hồ sơ, theo đúng thứ tự thời gian."""
    return list(
        session.scalars(
            select(EventLog)
            .where(EventLog.case_id == case_id)
            .order_by(EventLog.timestamp, EventLog.id)
        ).all()
    )


def _trang_thai_truoc(session: Session, case_id: int) -> str | None:
    """Trạng thái hồ sơ đã ở ngay trước trạng thái hiện tại, đọc từ nhật ký sự kiện.

    Là `from_state` của dòng nhật ký mới nhất **có đổi trạng thái**. Mọi lần đổi trạng
    thái ghi đúng một dòng — mục 6.1 của ARCHITECTURE.md — nên dòng đó là lần hồ sơ bước
    vào trạng thái hiện tại. Dòng tự trỏ (ADR-0005) — nhận việc, sửa nội dung — không đưa
    hồ sơ vào trạng thái nào, nên bị bỏ qua. Sắp xếp giống hệt `case_history` để hai nơi
    không bao giờ kể khác nhau về thứ tự.
    """
    return session.scalars(
        select(EventLog.from_state)
        .where(EventLog.case_id == case_id, EventLog.from_state != EventLog.to_state)
        .order_by(EventLog.timestamp.desc(), EventLog.id.desc())
        .limit(1)
    ).first()


def _actor_can_traverse(actor: Actor, transition: Transition) -> bool:
    """Kiểm quyền thuần túy, chưa xét ràng buộc Poka-yoke."""
    if transition.is_system:
        return actor.is_system
    if actor.is_system:
        return False
    return bool(actor.roles & transition.role_codes)
