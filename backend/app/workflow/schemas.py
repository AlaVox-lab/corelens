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
import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.models.case import LOI_NHAN_TOI_DA, MO_TA_TOI_DA, TIEU_DE_TOI_DA, TIEU_DE_TOI_THIEU


class NhanCoMa(BaseModel):
    """Một giá trị danh mục: mã để mã nguồn so sánh, nhãn để người đọc."""

    code: str
    label: str


class TruongRiengRa(BaseModel):
    """Một trường thông tin riêng khai cho loại yêu cầu (#250) — giao diện dựng ô nhập từ đây."""

    code: str
    label: str
    kind: str
    required: bool
    help_text: str | None = None
    unit: str | None = None
    options: list[str] | None = None


class GoiYRa(NhanCoMa):
    """Một gợi ý của hệ thống cho trường quyết định (#239): giá trị, lý do, nguồn.

    `confidence` trống khi nguồn không có con số thật — giao diện chỉ hiện độ tin cậy khi có.
    """

    reason: str
    source: str
    source_label: str
    confidence: float | None = None


class QuyTrinhRa(NhanCoMa):
    """Một quy trình của động cơ luồng công việc (#376)."""

    description: str | None = None
    # Quy trình mà các màn của ứng dụng minh họa dùng — mặc định của mọi tham số `process`
    is_app_default: bool


class LoaiYeuCauRa(NhanCoMa):
    description: str | None = None
    # Quy trình mà hồ sơ của loại này chạy theo (#376)
    process_code: str
    sla_hours: int
    # Trường riêng của loại này, theo thứ tự hiển thị (#250)
    fields: list[TruongRiengRa] = Field(default_factory=list)
    # Phòng mặc định của loại trong bảng ánh xạ (#239): đổi loại trên màn điều phối thì thẻ gợi
    # ý đổi theo ngay, không phải hỏi lại dịch vụ
    suggested_department: GoiYRa | None = None


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
    # Trạng thái đích là trạng thái kết thúc — chỉ cạnh mở lại có cửa sổ thời gian đi ra được
    # (#102), nên coi như không hoàn tác. Giao diện hỏi lại trước khi gửi (#98). Tra từ cột
    # `states.is_terminal`.
    to_state_is_terminal: bool = False
    # Trạng thái kết thúc đích còn cạnh mở lại: số giờ làm việc kể từ lúc vào đó mà người gửi
    # còn mở lại được (#102). None là kết thúc hẳn. Giao diện sửa câu cảnh báo theo giá trị này.
    to_state_reopen_hours: int | None = None
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
    # Cạnh là bước chính đang chờ chính người xem (#227) — ngăn xem nhanh của hàng đợi đặt nó
    # thành nút chính ở đáy, các thao tác còn lại vào menu (#233). Cùng nguồn với cờ
    # `needs_my_action` trên danh sách: `my_primary_steps()`.
    is_primary: bool = False

    # Những trường mà cạnh này cho đặt, lấy thẳng từ `permitted_fields()` — tức từ
    # ràng buộc gắn trên cạnh (#78). Giao diện dựng ô nhập từ danh sách này, cùng lý do
    # nó dựng nút bấm từ danh sách cạnh: không có bảng nào trong mã giao diện nói
    # "Phân loại thì hiện ô mức ưu tiên". Cạnh của người gửi chỉ có trường ở thao tác
    # sửa nội dung (#127). Thứ tự là thứ tự ô trên giao diện, theo biểu mẫu tạo hồ sơ
    # (#152) — xem `THU_TU_O_NHAP` trong `routes.py`.
    fields: list[str] = Field(default_factory=list)


class DieuKienCanhRa(BaseModel):
    """Một dòng của bảng `transition_conditions` (#397) mà hồ sơ chưa thỏa (#424)."""

    id: int
    field: str
    operator: str
    # Giá trị cần so với trường riêng của hồ sơ, đúng như lưu trong bảng (số hay chữ)
    value: Any
    description: str | None = None


class LyDoChanRa(BaseModel):
    """Một lý do tác nhân chưa đi được cạnh (#424).

    `category` là mã lớp lỗi engine sẽ trả nếu cứ gọi bước chuyển: `role-not-permitted`,
    `system-transition-only` hay `guard-violation`. `code` là mã máy đọc được của chính lý do:
    với ràng buộc là mã ràng buộc trong bảng `guards` (điều kiện trên cạnh: `edge-condition`),
    với quyền thì trùng `category`. `message` là thông điệp tiếng Việt của chính lỗi đó.
    """

    code: str
    category: str
    message: str
    condition: DieuKienCanhRa | None = None


class LuaChonCanhRa(BaseModel):
    """Một cạnh rời trạng thái hiện tại của hồ sơ, kèm được đi hay không và vì sao (#424)."""

    activity_code: str
    activity_label: str
    to_state: str
    to_state_label: str
    keeps_state: bool
    # Cạnh hệ thống tự đi (leo thang, tự đóng) — con người nhận lý do `system-transition-only`
    is_system: bool
    # Người gọi đi được cạnh này lúc này, xét theo vai, ràng buộc không cần nhập liệu và điều
    # kiện trên cạnh — trùng hệt tập `allowed_transitions` của chi tiết hồ sơ
    allowed: bool
    # Rỗng khi `allowed`. Sai vai thì chỉ có lý do quyền: ràng buộc không xét, như engine.
    reasons: list[LyDoChanRa] = Field(default_factory=list)
    # Trường nhập liệu của cạnh, gửi trong `changes` khi đi — do ràng buộc CẦN nhập liệu trên
    # cạnh quản (thiếu hay sai do chính ràng buộc đó phán). Ràng buộc này chỉ xét lúc đi thật, nên
    # cạnh vẫn `allowed`; thứ tự theo biểu mẫu như `fields` của `allowed_transitions`.
    requires_input: list[str] = Field(default_factory=list)
    requires_note: bool
    note_label: str | None = None


class LuaChonCanhCuaHoSoRa(BaseModel):
    """Mọi cạnh rời trạng thái hiện tại của một hồ sơ, theo thứ tự hiển thị của bộ quy tắc (#424)."""

    case_id: int
    state: TrangThaiRa
    transitions: list[LuaChonCanhRa]


class ThayDoiTruongRa(BaseModel):
    """Một trường quyết định, hay một trường nội dung (#127), mà lần chuyển đã đổi giá
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
    # Người vắng mà người bấm làm thay (#252); trống khi người bấm dùng vai của chính mình
    on_behalf_of_label: str | None = None
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


class TrangRa(BaseModel):
    """Phần chung của mọi danh sách có phân trang (#232): tổng số dòng khớp bộ lọc, và trang đang
    trả. Số đếm nhóm đi kèm luôn tính trên toàn tập đã lọc, không chỉ trên trang này."""

    total: int
    offset: int
    limit: int


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

    # Hồ sơ đang chờ chính người xem làm bước chính của quy trình (#227), suy từ cột
    # transitions.primary_scope. Chỉ điền ở danh sách hồ sơ và hàng đợi; None ở trang chi tiết.
    needs_my_action: bool | None = None
    # Nhãn của bước chính đang chờ người xem, ví dụ "Phân loại yêu cầu" — chữ trên nút của
    # dòng việc ở trang chủ (#228). None khi hồ sơ không chờ họ, và ở trang chi tiết.
    next_step_label: str | None = None


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


class TepDinhKemRa(BaseModel):
    """Một tệp đính kèm trên hồ sơ (#80). Không có khóa kho: tải về đi qua `id`."""

    id: int
    filename: str
    content_type: str
    size_bytes: int
    uploaded_by_label: str
    created_at: dt.datetime
    # Tệp mang macro (#248) — giao diện cảnh báo "có macro — cẩn thận khi mở"
    has_macro: bool = False
    # `disabled` (quét tắt), `clean`, hay `unscanned` (quét bật mà chưa quét được) — #248
    scan_status: str = "disabled"


class ChinhSachTepRa(BaseModel):
    """Giới hạn tệp đính kèm — giao diện hỏi dịch vụ thay vì tự giữ bản sao (#80)."""

    allowed_extensions: list[str]
    max_mb: int
    max_files: int
    max_files_per_case: int


class HoSoLienQuanRa(BaseModel):
    """Hồ sơ nối với hồ sơ đang xem bằng `parent_request_id` (#102): bản gốc hay bản tạo lại."""

    id: int
    code: str
    title: str
    state: TrangThaiRa


class HoSoChiTietRa(HoSoTomTatRa):
    # Quy trình của hồ sơ — suy từ bộ quy tắc hồ sơ ghim lúc tạo (#376)
    process: NhanCoMa
    description: str | None = None
    # Trường riêng (#250): giá trị đang lưu, và khai báo của loại hiện tại để hiện nhãn — trường
    # khai mà chưa có giá trị (ví dụ sau khi điều phối đổi loại) thì giao diện hiện "chưa có"
    details: dict[str, Any] = Field(default_factory=dict)
    detail_fields: list[TruongRiengRa] = Field(default_factory=list)
    # Hồ sơ này được tạo lại từ hồ sơ nào, và đã có những hồ sơ nào tạo lại từ nó (#102)
    parent: HoSoLienQuanRa | None = None
    children: list[HoSoLienQuanRa] = Field(default_factory=list)
    # Số lần đã mở lại và số lần được mở lại tối đa của loại yêu cầu (#102). Hết lượt thì giao
    # diện mời tạo hồ sơ mới thay cho nút Mở lại.
    reopen_count: int = 0
    reopen_max_count: int | None = None
    # Tệp đính kèm (#80), và người đang xem đính kèm thêm được lúc này không — chỉ người gửi, ở
    # những bước có cạnh mang cờ `accepts_attachments`
    attachments: list[TepDinhKemRa] = Field(default_factory=list)
    can_attach: bool = False
    requester_id: str
    assignee_id: str | None = None
    history: list[SuKienRa]
    allowed_transitions: list[CanhDiDuocRa]
    messages: list[LoiNhanRa] = Field(default_factory=list)
    message_kinds: list[LoaiLoiNhanRa] = Field(default_factory=list)
    # Người đang xem đọc được cuộc nội bộ của hồ sơ này không (#156) — giao diện dựng thẻ
    # "Nội bộ" theo cờ này, kể cả khi chưa có tin nội bộ nào
    sees_internal: bool = False


class CanhNguoiGuiRa(CanhDiDuocRa):
    """Cạnh đi được ở cổng người gửi — thêm cờ chấm điểm (#433). Chỉ ứng dụng; lõi `/core/v1` giữ
    `CanhDiDuocRa` nguyên như cũ."""

    # Cạnh mang cờ `transitions.collects_feedback`: hộp xác nhận hiện ô chấm 1–5 và nhận xét, đều tùy chọn
    collects_feedback: bool = False


class HoSoNguoiGuiRa(HoSoChiTietRa):
    """Chi tiết hồ sơ ở cổng người gửi (#433): như lõi, thêm cờ chấm trên cạnh và các lần mình đã chấm."""

    allowed_transitions: list[CanhNguoiGuiRa]
    # Mỗi lần xác nhận có chấm một mục, theo thời gian
    feedback: list[DanhGiaRa] = Field(default_factory=list)
    # Trần độ dài nhận xét (`DXLAB_FEEDBACK_COMMENT_MAX_CHARS`) — ô nhận xét đếm ký tự theo số này
    feedback_comment_max_chars: int


class TaoHoSoVao(BaseModel):
    """Biểu mẫu gửi yêu cầu.

    Cố ý **không** có `priority_code`: người gửi không tự đặt mức ưu tiên cho yêu cầu
    của mình. Gửi kèm trường đó thì Pydantic bỏ qua, không ghi vào hồ sơ — ràng buộc
    Poka-yoke bằng sự vắng mặt, không phải bằng một câu `if`.

    `request_type_code` thì có, vì người gửi là người biết rõ nhất họ đang cần gì, và
    người phân loại vẫn nắn lại được ở cạnh kế tiếp (`app/models/case.py`).
    """

    title: str = Field(min_length=TIEU_DE_TOI_THIEU, max_length=TIEU_DE_TOI_DA)
    description: str | None = Field(default=None, max_length=MO_TA_TOI_DA)
    request_type_code: str | None = Field(default=None, max_length=64)
    # Tạo lại từ hồ sơ cũ của chính người gửi, đã kết thúc (#102). Chỉ đặt lúc tạo.
    parent_request_id: int | None = Field(default=None, ge=1)
    # Trường riêng theo loại yêu cầu (#250): {mã trường: giá trị}, kiểm theo khai báo của loại
    details: dict[str, Any] = Field(default_factory=dict)
    # Phiên soạn của gợi ý hồ sơ tương tự (#319): nối lượt "đã xem gợi ý" với lần gửi này, để lượt đó
    # không bị tính là bỏ không gửi. Không bắt buộc, không ảnh hưởng gì tới hồ sơ
    similar_session_id: uuid.UUID | None = None


class ChuyenTrangThaiVao(BaseModel):
    """Yêu cầu chuyển trạng thái từ cổng người dùng.

    Có nhận `changes` (#127): cạnh *Sửa nội dung* cho người gửi đặt tiêu đề, mô tả,
    loại yêu cầu khi hồ sơ chưa tới phòng ban (ADR-0005). Trước đó cổng này cố ý không
    nhận, vì không cạnh nào của người gửi cho đặt trường nào.

    Không kiểm trường nào được phép ở đây: engine kiểm theo từng cạnh (#78), nên mức ưu
    tiên hay phòng ban gửi lên từ cổng này vẫn bị từ chối bằng `field-not-permitted` —
    không cạnh nào của người gửi quản hai trường đó.
    """

    to_state: str
    note: str | None = Field(default=None, max_length=2000)
    changes: dict[str, str | None] = Field(default_factory=dict)
    # Mức hài lòng (#433), tùy chọn: chỉ nhận ở cạnh mang cờ `transitions.collects_feedback`
    feedback: DanhGiaVao | None = None


class DanhGiaVao(BaseModel):
    """Điểm hài lòng 1–5 và nhận xét người gửi chấm khi xác nhận hoàn tất (#433).

    Trần độ dài nhận xét là cấu hình (`DXLAB_FEEDBACK_COMMENT_MAX_CHARS`), đọc lúc chạy nên kiểm ở điểm cuối.
    """

    score: int = Field(ge=1, le=5)
    comment: str | None = None


class DanhGiaRa(BaseModel):
    """Một lần chấm — chỉ đọc. Không có tên người: người chấm là người gửi của hồ sơ."""

    score: int
    comment: str | None = None
    created_at: dt.datetime


class BuocChuyenLoiVao(BaseModel):
    """Bước chuyển qua cửa trung lập với vai của nền tảng lõi (#376).

    Như cổng người gửi, nhưng `changes` nhận mọi kiểu giá trị JSON — bộ trường riêng `details` là một đối
    tượng, gia hạn là một số. Không kiểm trường nào được phép ở đây: engine kiểm theo từng cạnh (#78), tra
    danh mục, kiểm trường riêng theo khai báo của loại.
    """

    to_state: str
    note: str | None = Field(default=None, max_length=2000)
    changes: dict[str, Any] = Field(default_factory=dict)


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
    # Trạng thái kết thúc — chỉ "Hồ sơ của tôi" có, để tách hồ sơ đang mở khỏi đã đóng (#232)
    is_terminal: bool = False
    # Số hồ sơ quá hạn và sắp hạn trong nhóm — dòng phụ trên dải lọc của điều phối (#232)
    overdue: int = 0
    due_soon: int = 0


class NhomDoGapRa(NhanCoMa):
    """Một nhóm độ gấp của hàng đợi phòng ban, kèm số hồ sơ và số đã quá hạn, sắp hạn."""

    count: int
    overdue: int = 0
    due_soon: int = 0


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


class HangDoiRa(TrangRa):
    groups: list[NhomHangDoiRa]
    items: list[MucHangDoiRa]
    # Số hồ sơ đang chờ chính người xem, trên cả hàng đợi — thanh bên và trang chủ đọc số này
    waiting_me: int = 0
    urgent: bool = False


class DanhSachHoSoRa(TrangRa):
    """Hồ sơ của người gửi, có phân trang (#232)."""

    items: list[HoSoTomTatRa]
    # Số hồ sơ theo trạng thái trên toàn tập đã lọc — nút lọc và cột tổng quan đọc từ đây
    groups: list[NhomHangDoiRa]
    # Hồ sơ chưa kết thúc của người gửi, không tính bộ lọc — số mờ trên thanh bên
    open_count: int = 0
    # Hồ sơ đang chờ chính người gửi (needs_my_action), trên mọi hồ sơ của họ
    waiting_me: int = 0
    urgent: bool = False


class HoSoDieuPhoiRa(HoSoChiTietRa):
    requester_label: str | None = None
    priority: NhanCoMa | None = None
    state_entered_at: dt.datetime

    # Gợi ý phòng ban (#239): cột `suggested_department_code` nếu tầng I đã ghi, không thì phòng
    # mặc định của loại yêu cầu trong `request_type_routing`. Chỉ điền sẵn ô chọn: điều phối viên
    # được chọn khác, và cửa chuyển trạng thái ghi lại họ giữ hay ghi đè — cùng một hàm sinh gợi
    # ý, nên thứ hiện trên thẻ đúng là thứ được đem so.
    suggested_department: GoiYRa | None = None

    # Gợi ý loại yêu cầu và mức ưu tiên của mô hình ngôn ngữ (#317), cùng khuôn với gợi ý phòng ban.
    # Trống khi mô hình tắt hay chưa trả lời — màn điều phối như trước khi có gợi ý.
    suggested_request_type: GoiYRa | None = None
    suggested_priority: GoiYRa | None = None

    # Hồ sơ do chính người đang xem gửi (#154): bảng thao tác trống vì ràng buộc
    # `actor-not-requester`, không phải vì hồ sơ đã rời hàng đợi.
    requested_by_me: bool = False

    # Đánh giá của người gửi (#433), mỗi lần xác nhận có chấm một mục, theo thời gian — chỉ đọc
    feedback: list[DanhGiaRa] = Field(default_factory=list)


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
# Thao tác hàng loạt ở buồng lái điều phối (#440)
# ---------------------------------------------------------------------------


class TruongHangLoatRa(BaseModel):
    """Một ô của hộp thoại hàng loạt: trường gửi kèm, và có bắt buộc chọn không.

    `required` False là được để trống — "giữ nguyên ở từng hồ sơ": ràng buộc quản trường đó lùi về
    giá trị hồ sơ đang có (`truong_bat_buoc` ở app/rules/guards.py).
    """

    code: str
    required: bool


class ThaoTacHangLoatRa(BaseModel):
    """Một bước làm được cho nhiều hồ sơ một lần — một mã hoạt động của bộ quy tắc."""

    activity_code: str
    activity_label: str
    # Trạng thái có cạnh mang mã này mà vai điều phối đi được: hồ sơ ở trạng thái khác thì bỏ qua
    from_states: list[NhanCoMa]
    # Trường nhập liệu của cạnh (`truong_can_nhap`), theo thứ tự ô như `fields` của `allowed_transitions`
    fields: list[TruongHangLoatRa] = Field(default_factory=list)
    requires_note: bool = False
    note_label: str | None = None


class DanhSachThaoTacHangLoatRa(BaseModel):
    max_cases: int
    actions: list[ThaoTacHangLoatRa]


class ChuyenHangLoatVao(BaseModel):
    """Một bước cho cả lô hồ sơ. Giá trị trong `changes` áp chung cho mọi hồ sơ của lô.

    Chỉ nhận giá trị người dùng chọn — không có lối "nhận gợi ý cho cả lô" (#440). Số hồ sơ tối đa là
    cấu hình (`DXLAB_BULK_MAX_CASES`), kiểm ở điểm cuối vì đọc lúc chạy.
    """

    activity_code: str
    case_ids: list[int] = Field(min_length=1)
    note: str | None = Field(default=None, max_length=2000)
    changes: dict[str, str | None] = Field(default_factory=dict)


class LoiHangLoatRa(BaseModel):
    """Lỗi của một hồ sơ trong lô — mã và thông điệp của chính lỗi engine ném (app/workflow/errors.py).

    `guard` là mã ràng buộc khi `code` là `guard-violation`, ví dụ `actor-not-requester`.
    """

    code: str
    message: str
    guard: str | None = None


class MucHangLoatRa(BaseModel):
    case_id: int
    # Mã hiển thị, ví dụ `YC-2026-0184`; trống khi không có hồ sơ mang định danh này
    code: str | None = None
    ok: bool
    to_state: str | None = None
    to_state_label: str | None = None
    error: LoiHangLoatRa | None = None


class KetQuaHangLoatRa(BaseModel):
    """Kết quả từng hồ sơ, đúng thứ tự gửi lên. Hồ sơ bị chặn đứng nguyên, không có dòng nhật ký."""

    activity_code: str
    total: int
    succeeded: int
    items: list[MucHangLoatRa]


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
    # Gợi ý người xử lý cho hồ sơ `case_id` gửi kèm (#318), tính lại ngay lúc tra — luôn là một người
    # trong `people`. Trống khi không gửi `case_id`, hồ sơ không chờ giao việc, hay phòng không có ai.
    suggestion: GoiYRa | None = None


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
    # Nhóm độ gấp của hồ sơ trên hàng đợi (#232) — mã trong `urgency_groups`
    urgency: str | None = None


class HangDoiPhongBanRa(TrangRa):
    # Phòng của người đang xem — tiêu đề hàng đợi nói rõ đây là việc của phòng nào.
    departments: list[NhanCoMa]
    groups: list[NhomHangDoiRa]
    # Nhóm theo độ gấp (#232): quá hạn, sắp hết hạn, trong hạn, từng trạng thái đồng hồ chưa
    # chạy, chờ người gửi — dịch vụ chia trên toàn hàng đợi để số đếm đúng khi cắt trang
    urgency_groups: list[NhomDoGapRa] = []
    items: list[MucHangDoiPhongBanRa]
    waiting_me: int = 0
    urgent: bool = False


class HoSoPhongBanRa(HoSoChiTietRa):
    requester_label: str | None = None
    priority: NhanCoMa | None = None
    state_entered_at: dt.datetime
    assignee_label: str | None = None
    assigned_to_me: bool
    # Gợi ý người xử lý đã lưu (#318), chỉ khi hồ sơ đang chờ giao việc. Ô chọn người nạp danh sách
    # kèm gợi ý tính lại (`/departments/{code}/assignees?case_id=`); trường này để màn không trống
    # khi danh bạ chưa trả lời kịp — và chính là thứ cửa chuyển trạng thái đem so.
    suggested_assignee: GoiYRa | None = None
    # Đánh giá của người gửi (#433), mỗi lần xác nhận có chấm một mục, theo thời gian — chỉ đọc
    feedback: list[DanhGiaRa] = Field(default_factory=list)


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


class HopThuRa(TrangRa):
    items: list[CuocTroChuyenRa]
    # Tổng số lời nhắn chưa đọc — con số trên thanh bên
    unread: int
    # Số cuộc còn tin chưa đọc và số cuộc nội bộ, trên các cuộc khớp ô tìm — số trên chip lọc
    unread_conversations: int = 0
    internal_conversations: int = 0


class SoChuaDocRa(BaseModel):
    unread: int
