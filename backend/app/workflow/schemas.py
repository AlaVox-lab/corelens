# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Lược đồ dữ liệu vào và ra của các điểm cuối nghiệp vụ.
#
# Nhãn hiển thị luôn đi kèm mã: cổng người dùng không được tự dịch mã trạng thái sang
# tiếng Việt, vì làm thế là chép danh mục trạng thái vào mã nguồn giao diện — đúng thứ
# ARCHITECTURE.md mục 5 cấm. Nhãn nằm trong bảng `states`, và API chở nó đi.

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

from app.models.case import LOI_NHAN_TOI_DA, MO_TA_TOI_DA, TIEU_DE_TOI_DA, TIEU_DE_TOI_THIEU


class NhanCoMa(BaseModel):
    """Một giá trị danh mục: mã để mã nguồn so sánh, nhãn để người đọc."""

    code: str
    label: str


class LoaiYeuCauRa(NhanCoMa):
    description: str | None = None
    sla_hours: int


class TrangThaiRa(NhanCoMa):
    is_terminal: bool


class CanhDiDuocRa(BaseModel):
    """Một thao tác người dùng thực hiện được từ trạng thái hiện tại.

    Danh sách này do `allowed_transitions()` sinh ra từ bảng `transitions` và ma trận
    phân quyền, **không phải** từ một bảng ánh xạ viết cứng trong giao diện. Nhờ vậy
    nút bấm luôn khớp dữ liệu: doanh nghiệp sửa bộ quy tắc thì giao diện đổi theo, và
    không bao giờ hiện ra nút dẫn tới một cạnh không tồn tại.
    """

    to_state: str
    to_state_label: str
    # Trạng thái đích là trạng thái kết thúc — không cạnh nào đi ra, không hoàn tác được.
    # Giao diện hỏi lại trước khi gửi (#98). Tra từ cột `states.is_terminal`.
    to_state_is_terminal: bool = False
    activity_code: str
    activity_label: str
    requires_note: bool
    # Tên ô ghi chú, tra từ `transitions.note_label` (#79). Rỗng thì giao diện gọi nó là
    # "Lý do". Ở cạnh bổ sung thông tin, ô ghi chú là chính câu trả lời của người gửi.
    note_label: str | None = None
    # Cạnh tự trỏ — thao tác đổi hồ sơ mà giữ nguyên trạng thái, như nhận việc về mình
    # hay sửa nội dung (ADR-0005). Giao diện nói "giữ nguyên trạng thái" thay cho "chuyển
    # sang" chính trạng thái hồ sơ đang ở.
    keeps_state: bool = False

    # Những trường mà cạnh này cho đặt, lấy thẳng từ `permitted_fields()` — tức từ
    # ràng buộc gắn trên cạnh (#78). Giao diện dựng ô nhập từ danh sách này, cùng lý do
    # nó dựng nút bấm từ danh sách cạnh: không có bảng nào trong mã giao diện nói
    # "Phân loại thì hiện ô mức ưu tiên". Cạnh của người gửi chỉ có trường ở thao tác
    # sửa nội dung (#127). Thứ tự là thứ tự ô trên giao diện, theo biểu mẫu tạo hồ sơ
    # (#152) — xem `THU_TU_O_NHAP` trong `routes.py`.
    fields: list[str] = Field(default_factory=list)


class ThayDoiTruongRa(BaseModel):
    """Một trường quyết định, hay từ #127 một trường nội dung, mà lần chuyển đã đổi giá
    trị (#100).

    `before` rỗng khi trường chưa có giá trị, ví dụ lần đầu chọn phòng ban. Nhãn tra lúc
    đọc từ danh mục — kể cả mục đã ngừng dùng, để lịch sử cũ vẫn đọc được. Riêng người
    xử lý thì nhãn là tên ghi lúc đổi. Tiêu đề và mô tả không có danh mục, nên nhãn là
    chính nội dung — nhờ vậy bản gốc người gửi viết vẫn đọc được sau khi họ sửa.
    """

    field: str
    before: NhanCoMa | None = None
    after: NhanCoMa | None = None


class SuKienRa(BaseModel):
    """Một mốc trong dòng thời gian, dựng thẳng từ bảng `event_log`."""

    timestamp: dt.datetime
    activity: str
    activity_label: str | None = None
    actor: str
    actor_label: str
    is_system: bool
    from_state: str
    from_state_label: str
    to_state: str
    to_state_label: str
    note: str | None = None
    # Tên của ghi chú, tra từ cạnh đã đi (#79) — cùng tên với ô nhập lúc ghi. Rỗng thì
    # dòng thời gian gọi là "Lý do". Câu hỏi thêm và câu trả lời không phải lý do.
    note_label: str | None = None
    changes: list[ThayDoiTruongRa] = Field(default_factory=list)
    # Mốc đi qua cạnh làm lại (#153), tra từ cột `transitions.is_rework` — dòng thời gian
    # đếm "quay lui" theo cờ này
    is_rework: bool = False


class TuDongRa(BaseModel):
    """Cạnh hệ thống sẽ tự đi từ trạng thái hiện tại khi hết hạn chờ (#142)."""

    activity_label: str
    # Lúc tự đi, theo lịch làm việc (#199)
    at: dt.datetime | None
    # Đã vào khoảng báo trước — màn hình nhấn mạnh
    warn: bool


class HoSoTomTatRa(BaseModel):
    id: int
    code: str
    title: str
    request_type: NhanCoMa | None = None
    department: NhanCoMa | None = None
    state: TrangThaiRa
    created_at: dt.datetime
    updated_at: dt.datetime

    # Đồng hồ SLA — xem app/rules/sla.py. Mọi số giây là giờ làm việc (#199)
    sla_running_seconds: int
    sla_paused_seconds: int
    sla_limit_seconds: int | None = None
    sla_overdue: bool
    # Đã dùng tới ngưỡng "sắp hết hạn" trong dữ liệu mà chưa quá hạn (#175)
    sla_due_soon: bool = False
    # Gia hạn xử lý (#101): tổng giờ đã cộng vào hạn, và đã gia hạn mấy lần
    sla_extension_total_hours: int = 0
    sla_extension_count: int = 0
    sla_paused: bool
    # Đồng hồ đã khởi động — hồ sơ đã từng vào trạng thái đếm giờ (#97)
    sla_started: bool
    # Ân hạn còn lại khi hồ sơ quá hạn vừa được giao lại hay mở lại (#94)
    sla_grace_seconds: int | None = None
    # Mốc hết hạn xử lý khi đồng hồ đang chạy và chưa quá hạn; None khi đang dừng (#199)
    sla_due_at: dt.datetime | None = None
    # Hồ sơ đang nằm ở trạng thái có hạn chờ: hệ thống sẽ tự đi cạnh nào, lúc nào (#142)
    auto_transition: TuDongRa | None = None

    # Lời nhắn sau cùng là của người gửi hồ sơ (True), của nhân viên (False), hay chưa
    # có lời nhắn nào (None) — nguồn của dấu hiệu "đang chờ trả lời" trên hàng đợi (#128)
    last_message_from_requester: bool | None = None


class LoiNhanRa(BaseModel):
    """Một lời nhắn trên hồ sơ (#128).

    Không phải mốc chuyển trạng thái: dòng thời gian trộn lời nhắn với `history` theo
    thời gian, nhưng số lần đổi trạng thái chỉ đếm `history`.
    """

    id: int
    kind: str
    kind_label: str
    author: str
    author_label: str
    # Tác giả là người gửi của chính hồ sơ — so định danh, không lưu thêm cột
    from_requester: bool
    # Của chính người đang xem — cuộc nội bộ toàn nhân viên, nên chia phía theo người viết
    mine: bool = False
    # Lời nhắn nội bộ giữa nhân viên (#156) — người gửi hồ sơ không bao giờ nhận được
    internal: bool = False
    body: str | None = None
    created_at: dt.datetime


class LoaiLoiNhanRa(BaseModel):
    """Một loại lời nhắn người đang xem gửi được trên hồ sơ lúc này (#128).

    Danh sách do bảng `message_kinds` và cửa nhìn thấy quyết, giống `allowed_transitions`
    — giao diện dựng nút từ đây. `retry_at` có giá trị thì loại đó đang chờ luật hỏi lại:
    hiện nút mờ kèm mốc, chưa gửi được trước mốc đó.
    """

    code: str
    label: str
    description: str | None = None
    body_required: bool
    # Loại nội bộ (#156): giao diện đặt nút gửi ở cuộc nội bộ, không ở cuộc với người gửi
    internal: bool = False
    retry_at: dt.datetime | None = None


class HoSoChiTietRa(HoSoTomTatRa):
    description: str | None = None
    requester_id: str
    assignee_id: str | None = None
    history: list[SuKienRa]
    allowed_transitions: list[CanhDiDuocRa]
    messages: list[LoiNhanRa] = Field(default_factory=list)
    message_kinds: list[LoaiLoiNhanRa] = Field(default_factory=list)
    # Người đang xem đọc được cuộc nội bộ của hồ sơ này không (#156) — giao diện dựng thẻ
    # "Nội bộ" theo cờ này, kể cả khi chưa có tin nội bộ nào
    sees_internal: bool = False


class TaoHoSoVao(BaseModel):
    """Biểu mẫu gửi yêu cầu.

    Cố ý **không** có `priority_code`: người gửi không tự đặt mức ưu tiên cho yêu cầu
    của mình. Gửi kèm trường đó thì Pydantic bỏ qua, không ghi vào hồ sơ — ràng buộc
    Poka-yoke bằng sự vắng mặt, không phải bằng một câu `if`.

    `request_type_code` thì có, vì người gửi là người biết rõ nhất họ đang cần gì, và
    người phân loại vẫn nắn lại được ở cạnh kế tiếp. Xem `app/models/case.py`.
    """

    title: str = Field(min_length=TIEU_DE_TOI_THIEU, max_length=TIEU_DE_TOI_DA)
    description: str | None = Field(default=None, max_length=MO_TA_TOI_DA)
    request_type_code: str | None = Field(default=None, max_length=64)


class ChuyenTrangThaiVao(BaseModel):
    """Yêu cầu chuyển trạng thái từ cổng người dùng.

    Có nhận `changes` từ #127: cạnh *Sửa nội dung* cho người gửi đặt tiêu đề, mô tả,
    loại yêu cầu khi hồ sơ chưa tới phòng ban (ADR-0005). Trước đó cổng này cố ý không
    nhận, vì không cạnh nào của người gửi cho đặt trường nào.

    Không kiểm trường nào được phép ở đây: engine kiểm theo từng cạnh (#78), nên mức ưu
    tiên hay phòng ban gửi lên từ cổng này vẫn bị từ chối bằng `field-not-permitted` —
    không cạnh nào của người gửi quản hai trường đó.
    """

    to_state: str
    note: str | None = Field(default=None, max_length=2000)
    changes: dict[str, str | None] = Field(default_factory=dict)


class GuiLoiNhanVao(BaseModel):
    """Gửi một lời nhắn (#128). Nội dung trống được ở loại không bắt buộc nội dung."""

    kind: str = Field(max_length=64)
    body: str | None = Field(default=None, max_length=LOI_NHAN_TOI_DA)


# ---------------------------------------------------------------------------
# Danh mục dùng chung cho ô chọn
# ---------------------------------------------------------------------------


class MucUuTienRa(NhanCoMa):
    is_default: bool


class PhongBanRa(NhanCoMa):
    description: str | None = None


# ---------------------------------------------------------------------------
# Buồng lái điều phối viên (#82)
# ---------------------------------------------------------------------------


class NhomHangDoiRa(NhanCoMa):
    """Một trạng thái trong hàng đợi, kèm số hồ sơ đang nằm ở đó.

    Danh sách trạng thái suy từ bộ quy tắc — trạng thái nào vai trò điều phối có cạnh
    đi ra — nên giao diện dựng nút lọc từ đây, không liệt kê cứng.
    """

    count: int
    # Nhóm chỉ để theo dõi: hồ sơ của phòng đang chờ người gửi, người trong phòng không
    # có thao tác nào lúc này nhưng hồ sơ sẽ quay về (#99). Hàng đợi điều phối luôn False.
    watch_only: bool = False


class MucHangDoiRa(HoSoTomTatRa):
    requester_label: str | None = None
    priority: NhanCoMa | None = None

    # Lúc hồ sơ vào trạng thái hiện tại: mốc của dòng nhật ký cuối cùng, hoặc lúc tạo
    # nếu chưa có dòng nào. Không dùng `updated_at` vì cột đó nhảy ở MỌI lần sửa dòng,
    # không riêng lần chuyển trạng thái.
    state_entered_at: dt.datetime

    # Hồ sơ do chính người đang xem gửi (#154): ở hàng đợi điều phối, người khác phải
    # điều phối nó. Chỉ hàng đợi điều phối đặt cờ này.
    requested_by_me: bool = False


class HangDoiRa(BaseModel):
    groups: list[NhomHangDoiRa]
    items: list[MucHangDoiRa]


class HoSoDieuPhoiRa(HoSoChiTietRa):
    requester_label: str | None = None
    priority: NhanCoMa | None = None
    state_entered_at: dt.datetime

    # Phòng ban mặc định cho loại yêu cầu của hồ sơ, tra từ `request_type_routing`.
    # Chỉ là gợi ý để ô chọn điền sẵn: điều phối viên được chọn khác, và chính những
    # lần chọn khác đó là tín hiệu cho khai phá quy trình biết bảng ánh xạ đang sai.
    suggested_department: NhanCoMa | None = None

    # Hồ sơ do chính người đang xem gửi (#154): bảng thao tác trống vì ràng buộc
    # `actor-not-requester`, không phải vì hồ sơ đã rời hàng đợi.
    requested_by_me: bool = False


class ChuyenTrangThaiCoTruongVao(BaseModel):
    """Thao tác ở buồng lái — điều phối (#82) và phòng ban (#83). Khác cổng người gửi
    ở chỗ CÓ nhận `changes`.

    Không kiểm trường nào được phép ở đây. Engine đã kiểm theo từng cạnh (#78) và tra
    giá trị với danh mục — kiểm lại ở tầng này sẽ thành nguồn sự thật thứ hai.
    """

    to_state: str
    note: str | None = Field(default=None, max_length=2000)
    changes: dict[str, str | None] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Giao việc (#84)
# ---------------------------------------------------------------------------


class NguoiNhanViecRa(BaseModel):
    """Một người nhận được việc trong phòng, tra từ danh bạ Keycloak."""

    # `sub` của Keycloak — đúng giá trị ghi xuống `assignee_id`. Tên bên dưới chỉ để
    # hiển thị, không bao giờ gửi ngược lên thay cho định danh.
    id: str
    name: str
    username: str


class NguoiNhanViecTrongPhongRa(BaseModel):
    department: PhongBanRa
    people: list[NguoiNhanViecRa]


class LienHeNguoiGuiRa(BaseModel):
    """Cách liên hệ người gửi một hồ sơ, tra từ danh bạ Keycloak lúc mở trang (#131).

    Hai trường liên hệ trống nghĩa là người gửi chưa điền. `found` sai nghĩa là tài khoản
    không còn trong Keycloak — hồ sơ cũ vẫn mang tên, chỉ không còn cách liên hệ.
    """

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    found: bool


# ---------------------------------------------------------------------------
# Buồng lái phòng ban (#83)
# ---------------------------------------------------------------------------


class MucHangDoiPhongBanRa(MucHangDoiRa):
    # Người xử lý: định danh để so, tên để đọc. Tên ghi lúc giao việc, không tra lại.
    assignee_id: str | None = None
    assignee_label: str | None = None
    assigned_to_me: bool


class HangDoiPhongBanRa(BaseModel):
    # Phòng của người đang xem — tiêu đề hàng đợi nói rõ đây là việc của phòng nào.
    departments: list[NhanCoMa]
    groups: list[NhomHangDoiRa]
    items: list[MucHangDoiPhongBanRa]


class HoSoPhongBanRa(HoSoChiTietRa):
    requester_label: str | None = None
    priority: NhanCoMa | None = None
    state_entered_at: dt.datetime
    assignee_label: str | None = None
    assigned_to_me: bool


# ---------------------------------------------------------------------------
# Hộp thư chung (#155)
# ---------------------------------------------------------------------------


class LoiNhanCuoiRa(BaseModel):
    """Lời nhắn sau cùng của một cuộc trò chuyện — dòng xem trước trong danh sách."""

    author_label: str
    kind_label: str
    body: str | None = None
    created_at: dt.datetime
    # Của chính người đang xem — giao diện ghi "Bạn: …"
    mine: bool
    from_requester: bool


class CuocTroChuyenRa(BaseModel):
    """Một cuộc trò chuyện trong hộp thư: lời nhắn của MỘT hồ sơ.

    `workspace` là cửa người đang xem mở hồ sơ này — `portal`, `department` hay
    `coordination` — để giao diện biết đọc chi tiết và gửi lời nhắn qua điểm cuối nào. Mỗi
    điểm cuối đó vẫn tự gác cửa của nó; trường này chỉ chỉ đường.
    """

    case_id: int
    code: str
    title: str
    state: TrangThaiRa
    requester_id: str
    requester_label: str | None = None
    workspace: str
    # Cuộc nội bộ giữa nhân viên (#156). Một hồ sơ có thể có hai cuộc: với người gửi và
    # nội bộ, mỗi cuộc số chưa đọc riêng
    internal: bool = False
    last_message: LoiNhanCuoiRa
    unread: int
    # Lời nhắn cuối là của phía bên kia: người gửi đang chờ nhân viên, hoặc ngược lại
    waiting_on_me: bool


class HopThuRa(BaseModel):
    items: list[CuocTroChuyenRa]
    # Tổng số lời nhắn chưa đọc — con số trên thanh bên
    unread: int


class SoChuaDocRa(BaseModel):
    unread: int
