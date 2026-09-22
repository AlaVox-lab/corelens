# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Các lỗi mà điểm chuyển trạng thái duy nhất có thể ném ra.
#
# Tách riêng khỏi engine để gói app/rules/ dùng được mà không tạo phụ thuộc vòng.
#
# Mọi lỗi đều mang mã máy đọc được (`code`) bên cạnh thông điệp tiếng Việt. Cổng
# người dùng ở #44 sẽ dựa vào mã để hiển thị đúng chỗ trên giao diện, thay vì so
# khớp chuỗi thông điệp.


class TransitionError(Exception):
    """Gốc của mọi lỗi phát sinh khi cố đổi trạng thái hồ sơ."""

    code = "transition-error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class TransitionNotAllowed(TransitionError):
    """Cạnh này không tồn tại trong bảng quy tắc.

    Không phải "chưa cho phép" mà là "không có đường mà đi". Đây là cách ràng buộc
    Poka-yoke "đã nhận là không trả về" biểu hiện ra lúc chạy: bảng `transitions`
    không có dòng nào đi từ `in-progress` ngược về `awaiting-acceptance`.
    """

    code = "transition-not-allowed"


class RoleNotPermitted(TransitionError):
    """Cạnh có tồn tại nhưng vai trò của người thao tác không đi được."""

    code = "role-not-permitted"


class SystemTransitionOnly(TransitionError):
    """Cạnh chỉ hệ thống tự đi, con người không kích hoạt được.

    Hiện chỉ áp cho cạnh leo thang khi quá hạn SLA.
    """

    code = "system-transition-only"


class GuardViolation(TransitionError):
    """Một ràng buộc Poka-yoke từ chối lần chuyển này."""

    code = "guard-violation"

    def __init__(self, guard_code: str, message: str) -> None:
        super().__init__(message)
        self.guard_code = guard_code


class UnknownGuard(TransitionError):
    """Bảng dữ liệu khai một mã ràng buộc mà mã nguồn chưa cài đặt.

    Engine **từ chối chuyển trạng thái** thay vì bỏ qua ràng buộc lạ. Im lặng cho qua
    sẽ biến một ràng buộc nghiệp vụ thành vô hiệu mà không ai biết — đúng loại lỗi
    chỉ lộ ra khi đã muộn.
    """

    code = "unknown-guard"


class NoteRequired(TransitionError):
    """Cạnh này bắt buộc ghi lý do nhưng người thao tác bỏ trống."""

    code = "note-required"


class FieldNotPermitted(TransitionError):
    """Lần chuyển mang theo một trường mà cạnh đang đi không cho đặt.

    Một trường chỉ đặt được ở cạnh có ràng buộc chịu trách nhiệm về nó — xem
    `GUARD_REGISTRY` trong `app/rules/guards.py`. Nhờ vậy mức ưu tiên chỉ đặt được ở
    cạnh phân loại, người xử lý chỉ giao được ở cạnh nhận việc, và không ai lợi dụng
    một cạnh khác để sửa lén trường quyết định.

    Khác `TransitionNotAllowed`: cạnh vẫn tồn tại và vẫn đi được, chỉ là nội dung gửi
    kèm sai. Vì vậy dịch sang HTTP 422 chứ không phải 409.
    """

    code = "field-not-permitted"

    def __init__(self, fields: set[str], message: str) -> None:
        super().__init__(message)
        self.fields = frozenset(fields)


class InvalidFieldValue(TransitionError):
    """Trường được phép đặt, nhưng giá trị không có trong danh mục tương ứng.

    Không có phép kiểm này thì một mã phòng ban gõ sai đi thẳng xuống cơ sở dữ liệu,
    khóa ngoại nổ ra, và người dùng nhận lỗi 500 không kèm lời giải thích nào. Chặn ở
    đây thì họ nhận 422 kèm tên trường và giá trị bị từ chối.
    """

    code = "invalid-field-value"

    def __init__(self, field: str, value: object, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.value = value


class CaseNotFound(TransitionError):
    """Không có hồ sơ nào mang định danh đó."""

    code = "case-not-found"
