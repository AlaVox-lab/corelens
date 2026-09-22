# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Hồ sơ yêu cầu và nhật ký sự kiện.
#
# Khác với các bảng cấu hình ở workflow_config.py, hai bảng này do Alembic sở hữu
# và chứa dữ liệu vận hành thật.

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Request(Base):
    """Một hồ sơ yêu cầu nội bộ.

    Trạng thái của hồ sơ **chỉ được đổi qua app.workflow.engine.perform_transition**.
    Gán thẳng vào `current_state` ở bất kỳ chỗ nào khác là vi phạm khuôn mẫu một cửa
    duy nhất, vì nó tạo ra một lần chuyển không có bản ghi nhật ký — xem
    ARCHITECTURE.md mục 6.1.
    """

    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    # Bộ quy tắc hồ sơ này chạy theo, ghi lại lúc tạo và giữ nguyên tới khi đóng.
    # Nhờ cột này, quản trị viên sửa luồng giữa chừng không làm hồ sơ đang dở đổi
    # luật giữa đường.
    rule_set_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("rule_sets.id"))
    current_state: Mapped[str] = mapped_column(Text)

    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, default=None)

    # Định danh người dùng lấy từ claim `sub` của token Keycloak — xem #43.
    requester_id: Mapped[str] = mapped_column(Text)

    # Tên người gửi tại thời điểm gửi, cùng lý do với `event_log.actor_label`: tra
    # ngược từ Keycloak lúc đọc thì người nghỉ việc mất tên, người đổi tên thì hồ sơ cũ
    # hiện tên mới. Việc tạo hồ sơ không sinh dòng nhật ký nào, nên tên phải nằm ở đây.
    # NULL với hồ sơ có trước #82 — giao diện lùi về hiển thị mã định danh.
    requester_label: Mapped[str | None] = mapped_column(Text, default=None)

    # --- Trường QUYẾT ĐỊNH: chỉ con người ghi ------------------------------
    # Người gửi đặt loại yêu cầu ngay lúc tạo hồ sơ — họ là người biết rõ nhất mình
    # đang cần gì, và người phân loại vẫn sửa lại được ở cạnh `submitted -> classified`
    # nếu chọn sai. Ba trường còn lại rỗng cho tới khi người có thẩm quyền đi cạnh
    # tương ứng: người phân loại đặt mức ưu tiên và phòng ban, người xét duyệt đặt
    # người xử lý.
    #
    # Vì sao loại yêu cầu mở cho người gửi mà mức ưu tiên thì không: chọn sai loại chỉ
    # làm hồ sơ đi chậm một nhịp và người phân loại nắn lại ngay, còn ai cũng đánh dấu
    # yêu cầu của mình là khẩn thì thứ tự ưu tiên mất hết ý nghĩa. Đây là ràng buộc
    # Poka-yoke *người gửi không tự đặt mức ưu tiên*.
    request_type_code: Mapped[str | None] = mapped_column(
        Text, ForeignKey("request_types.code"), default=None
    )
    department_code: Mapped[str | None] = mapped_column(
        Text, ForeignKey("departments.code"), default=None
    )
    priority_code: Mapped[str | None] = mapped_column(
        Text, ForeignKey("priorities.code"), default=None
    )
    assignee_id: Mapped[str | None] = mapped_column(Text, default=None)

    # --- Trường GỢI Ý: chỉ tầng I ghi --------------------------------------
    # NGUYÊN TẮC BẤT DI DỊCH của đề tài: AI chỉ gợi ý, con người quyết định. Tầng I
    # không bao giờ được ghi vào bốn trường quyết định ở trên — xem CLAUDE.md mục 4.3.
    #
    # Không có cột riêng ghi "người dùng có ghi đè gợi ý hay không": con số đó tính
    # được bằng truy vấn `WHERE suggested_x IS DISTINCT FROM x`. Một cột lưu sẵn sẽ
    # lệch khỏi sự thật ngay lần đầu ai đó quên cập nhật nó.
    suggested_request_type_code: Mapped[str | None] = mapped_column(Text, default=None)
    suggested_department_code: Mapped[str | None] = mapped_column(Text, default=None)
    suggested_priority_code: Mapped[str | None] = mapped_column(Text, default=None)
    suggested_assignee_id: Mapped[str | None] = mapped_column(Text, default=None)

    # --- Đồng hồ SLA -------------------------------------------------------
    # Ba cột thay cho một cột hạn chót cố định, vì đồng hồ có thể dừng rồi chạy lại
    # nhiều lần. Trạng thái nào làm đồng hồ chạy do cột `states.sla_running` quyết
    # định — xem app/rules/sla.py.
    sla_running_seconds: Mapped[int] = mapped_column(Integer, default=0)
    sla_paused_seconds: Mapped[int] = mapped_column(Integer, default=0)

    # Mốc bắt đầu của đoạn đang tính. NULL nghĩa là đồng hồ chưa từng khởi động,
    # hoặc hồ sơ đã đóng.
    sla_segment_since: Mapped[dt.datetime | None] = mapped_column(default=None)

    # --- Mốc thời gian, luôn UTC -------------------------------------------
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list[EventLog]] = relationship(
        back_populates="case", order_by="EventLog.timestamp, EventLog.id"
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["rule_set_id", "current_state"], ["states.rule_set_id", "states.code"]
        ),
        Index("requests_tra_theo_trang_thai", "current_state"),
        Index("requests_tra_theo_phong_ban", "department_code"),
    )

    def __repr__(self) -> str:
        return f"<Request {self.id} [{self.current_state}]>"


class EventLog(Base):
    """Nhật ký sự kiện — tài sản quý nhất của hệ thống.

    Sáu trường bắt buộc theo ARCHITECTURE.md mục 6: `case_id`, `activity`,
    `timestamp`, `actor`, `from_state`, `to_state`. Cột `note` thêm vào để chứa lý do
    của những cạnh có `requires_note`, ví dụ từ chối vì sai chuyên môn.

    Nhật ký này nuôi bảng điều khiển ở không gian `D` và thuật toán khai phá quy
    trình ở `I`. Một nhật ký thủng làm sai lệch kết quả khai phá, và khi đó điểm
    sáng tạo của đề tài mất giá trị.

    **Bảng này chỉ ghi thêm, không sửa, không xóa.** Một trigger ở tầng cơ sở dữ
    liệu chặn mọi UPDATE và DELETE — xem migration tạo bảng. Lịch sử sửa được thì
    không còn là lịch sử.
    """

    __tablename__ = "event_log"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    case_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("requests.id"))
    activity: Mapped[str] = mapped_column(Text)

    # Kiểu TIMESTAMPTZ: PostgreSQL luôn quy về UTC lúc lưu, bất kể múi giờ của phía
    # ghi vào. Lưu giờ cục bộ sẽ làm sai lệch khai phá quy trình khi so sánh giữa
    # các bản ghi sinh ra ở nhiều máy.
    timestamp: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    actor: Mapped[str] = mapped_column(Text)

    # Tên hiển thị của người thực hiện, ghi lại tại thời điểm hành động. Cố ý lưu
    # kèm thay vì tra ngược từ Keycloak lúc đọc: người nghỉ việc thì tài khoản bị
    # xóa, người đổi tên thì lịch sử sẽ kể sai.
    actor_label: Mapped[str | None] = mapped_column(Text, default=None)

    from_state: Mapped[str] = mapped_column(Text)
    to_state: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text, default=None)

    case: Mapped[Request] = relationship(back_populates="events")

    __table_args__ = (
        # Khai phá quy trình luôn đọc theo hồ sơ và theo thứ tự thời gian
        Index("event_log_tra_theo_ho_so", "case_id", "timestamp"),
        Index("event_log_tra_theo_hoat_dong", "activity"),
    )

    def __repr__(self) -> str:
        return (
            f"<EventLog {self.case_id} {self.activity}: "
            f"{self.from_state} -> {self.to_state}>"
        )
