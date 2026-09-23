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
    activity_code: str
    activity_label: str
    requires_note: bool

    # Những trường mà cạnh này cho đặt, lấy thẳng từ `permitted_fields()` — tức từ
    # ràng buộc gắn trên cạnh (#78). Giao diện dựng ô nhập từ danh sách này, cùng lý do
    # nó dựng nút bấm từ danh sách cạnh: không có bảng nào trong mã giao diện nói
    # "Phân loại thì hiện ô mức ưu tiên". Cạnh của người gửi luôn cho danh sách rỗng.
    fields: list[str] = Field(default_factory=list)


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


class HoSoTomTatRa(BaseModel):
    id: int
    code: str
    title: str
    request_type: NhanCoMa | None = None
    department: NhanCoMa | None = None
    state: TrangThaiRa
    created_at: dt.datetime
    updated_at: dt.datetime

    # Đồng hồ SLA — xem app/rules/sla.py
    sla_running_seconds: int
    sla_paused_seconds: int
    sla_limit_seconds: int | None = None
    sla_overdue: bool
    sla_paused: bool


class HoSoChiTietRa(HoSoTomTatRa):
    description: str | None = None
    requester_id: str
    assignee_id: str | None = None
    history: list[SuKienRa]
    allowed_transitions: list[CanhDiDuocRa]


class TaoHoSoVao(BaseModel):
    """Biểu mẫu gửi yêu cầu.

    Cố ý **không** có `priority_code`: người gửi không tự đặt mức ưu tiên cho yêu cầu
    của mình. Gửi kèm trường đó thì Pydantic bỏ qua, không ghi vào hồ sơ — ràng buộc
    Poka-yoke bằng sự vắng mặt, không phải bằng một câu `if`.

    `request_type_code` thì có, vì người gửi là người biết rõ nhất họ đang cần gì, và
    người phân loại vẫn nắn lại được ở cạnh kế tiếp. Xem `app/models/case.py`.
    """

    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    request_type_code: str | None = Field(default=None, max_length=64)


class ChuyenTrangThaiVao(BaseModel):
    """Yêu cầu chuyển trạng thái từ cổng người dùng.

    Cố ý **không** có trường `changes`. Cổng này phục vụ người tạo yêu cầu, và không
    cạnh nào của vai trò `requester` cho đặt trường quyết định: ràng buộc gắn trên các
    cạnh đó — `requester-owns-case` — không quản trường nào. Mở trường này ra thì mọi
    giá trị gửi lên đều bị engine từ chối bằng `field-not-permitted`, nên nhận vào chỉ
    là mời người dùng gửi thứ chắc chắn hỏng.

    Hai lớp chặn độc lập nhau: lược đồ này không nhận trường, và engine không cho đặt
    trường ở cạnh không quản nó (#78). Gỡ một lớp thì lớp kia vẫn giữ.
    """

    to_state: str
    note: str | None = Field(default=None, max_length=2000)


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


class MucHangDoiRa(HoSoTomTatRa):
    requester_label: str | None = None
    priority: NhanCoMa | None = None

    # Lúc hồ sơ vào trạng thái hiện tại: mốc của dòng nhật ký cuối cùng, hoặc lúc tạo
    # nếu chưa có dòng nào. Không dùng `updated_at` vì cột đó nhảy ở MỌI lần sửa dòng,
    # không riêng lần chuyển trạng thái.
    state_entered_at: dt.datetime


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
