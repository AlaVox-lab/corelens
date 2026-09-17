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

    Cố ý **không** có trường `changes`. Cổng này phục vụ người tạo yêu cầu, và họ không
    đặt loại yêu cầu, phòng ban, mức ưu tiên hay người xử lý — đó là việc của người
    phân loại và người xét duyệt ở buồng lái (#45).

    Không mở trường đó ra cũng đóng luôn một lỗ hổng của engine: `CHANGEABLE_FIELDS`
    cho phép đặt `priority_code` ở **mọi** cạnh, nên nếu cổng nhận `changes` thì người
    tạo yêu cầu có thể tự đặt mức ưu tiên khi đi một cạnh của mình. Xem ghi chú ở cuối
    `routes.py`.
    """

    to_state: str
    note: str | None = Field(default=None, max_length=2000)
