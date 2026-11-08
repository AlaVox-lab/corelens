# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Hồ sơ yêu cầu, nhật ký sự kiện và lời nhắn trên hồ sơ.
#
# Khác với các bảng cấu hình ở workflow_config.py, ba bảng này do Alembic sở hữu
# và chứa dữ liệu vận hành thật.

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# Giới hạn nội dung hồ sơ. Một nơi duy nhất cho cả lúc gửi (lược đồ biểu mẫu ở
# app/workflow/schemas.py) lẫn lúc người gửi sửa nội dung (ràng buộc `edit-content` ở
# app/rules/guards.py, #127) — hai nơi tự đặt số riêng thì sớm muộn sẽ lệch nhau.
TIEU_DE_TOI_THIEU = 3
TIEU_DE_TOI_DA = 200
MO_TA_TOI_DA = 5000

# Cùng giới hạn với ô ghi chú của lần chuyển trạng thái. Bảng `case_messages` giữ cùng
# con số ở ràng buộc CHECK (migration 0007).
LOI_NHAN_TOI_DA = 2000


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

    # Tên người được giao tại thời điểm giao, cùng lý do với `requester_label`. Không
    # phải trường quyết định — trường quyết định là `assignee_id` ở trên — mà là nhãn
    # đi kèm nó: engine ghi hai cột cùng lúc, và tên lấy từ danh bạ Keycloak chứ không
    # từ trình duyệt (#83). NULL khi chưa giao cho ai.
    assignee_label: Mapped[str | None] = mapped_column(Text, default=None)

    # --- Trường GỢI Ý: chỉ tầng I ghi --------------------------------------
    # NGUYÊN TẮC BẤT DI DỊCH của đề tài: AI chỉ gợi ý, con người quyết định. Tầng I
    # không bao giờ được ghi vào bốn trường quyết định ở trên — xem CLAUDE.md mục 4.3.
    #
    # Không có cột nào trên hồ sơ ghi "người dùng có ghi đè gợi ý hay không": một cột lưu
    # sẵn sẽ lệch khỏi sự thật ngay lần đầu ai đó quên cập nhật nó, và một hồ sơ có thể được
    # xác nhận nhiều lần. Mỗi lần xác nhận là một sự kiện — dấu giữ hay ghi đè nằm ở
    # `EventLog.suggestion`, do cửa chuyển trạng thái ghi (#239).
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

    # Gia hạn xử lý (#101). Hạn của hồ sơ = hạn gốc (loại yêu cầu nhân hệ số ưu tiên) cộng
    # tổng số giờ đã gia hạn. Ô người dùng nhập là số giờ của lần này; tổng và số lần do
    # ràng buộc `extend-deadline` tự đặt — xem app/rules/guards.py.
    sla_extension_hours: Mapped[int] = mapped_column(Integer, default=0)
    sla_extension_total_hours: Mapped[int] = mapped_column(Integer, default=0)
    sla_extension_count: Mapped[int] = mapped_column(SmallInteger, default=0)

    # Mở lại có giới hạn (#102): đã mở lại mấy lần, tính cả mở lại từ Hoàn tất lẫn từ Đã đóng.
    # Do ràng buộc `reopen-limit` tự đặt, người dùng không gửi được.
    reopen_count: Mapped[int] = mapped_column(SmallInteger, default=0)

    # Hồ sơ này được tạo lại từ hồ sơ nào (#102): hết lượt mở lại, quá cửa sổ mở lại hay bị
    # Không tiếp nhận thì người gửi tạo hồ sơ mới và liên kết hồ sơ cũ. Chỉ đặt lúc tạo.
    parent_request_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("requests.id"), default=None
    )

    # Trường thông tin riêng theo loại yêu cầu (#250): {mã trường: giá trị}, mã khai ở bảng
    # cấu hình `request_type_fields`. Kiểm ở `app/rules/truong_rieng.py`, đổi qua cạnh Sửa
    # nội dung như tiêu đề và mô tả — nhật ký giữ giá trị cũ.
    details: Mapped[dict] = mapped_column(JSONB, default=dict)

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
        Index("requests_tra_theo_ho_so_goc", "parent_request_id"),
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

    # Trường quyết định mà lần chuyển này ĐỔI giá trị, dạng {trường: {"from", "to"}} —
    # người xử lý kèm thêm "from_label", "to_label" là tên tại thời điểm đổi (#100).
    # Hồ sơ chỉ mang giá trị hiện tại; lịch sử đổi nằm ở đây. NULL khi không đổi gì.
    changes: Mapped[dict | None] = mapped_column(JSONB, default=None)

    # Người giữ hay ghi đè gợi ý của hệ thống ở lần chuyển này (#239), dạng {trường:
    # {"suggested", "chosen", "overridden", "source", "confidence"}} — xem
    # `app/intelligence/goi_y.py`. Cột riêng chứ không nằm trong `changes`, để `changes` giữ
    # đúng một nghĩa "trường nào đổi từ gì sang gì". NULL khi lần chuyển không gửi trường nào
    # có gợi ý, hoặc không nguồn gợi ý nào có giá trị.
    #
    # `none_as_null`: không có nó, SQLAlchemy ghi `None` thành giá trị JSON `null` chứ không phải
    # SQL NULL, và `jsonb_each` của lớp báo cáo nổ "non-object" trên mọi dòng không có gợi ý.
    suggestion: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), default=None)

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


class CaseMessage(Base):
    """Một lời nhắn trên hồ sơ (#128, ADR-0005).

    Lời nhắn **không đổi hồ sơ**: không đổi trạng thái, không đổi trường nào, không chạm
    đồng hồ SLA. Vì vậy nó không đi qua `perform_transition` và không vào nhật ký sự
    kiện — nhật ký chỉ ghi những lần hồ sơ đổi. Ghi lời nhắn cũng không được đụng tới
    dòng `requests`, kể cả cột `updated_at`.

    **Chỉ ghi thêm**, như `event_log`: trigger ở tầng cơ sở dữ liệu chặn UPDATE và
    DELETE — xem migration 0007. Tác giả là người gửi hồ sơ hay nhân viên thì so `author`
    với `requests.requester_id`, không lưu thêm cột.
    """

    __tablename__ = "case_messages"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    case_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("requests.id"))
    kind: Mapped[str] = mapped_column(Text, ForeignKey("message_kinds.code"))

    author: Mapped[str] = mapped_column(Text)
    author_label: Mapped[str] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text, default=None)

    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    __table_args__ = (Index("case_messages_tra_theo_ho_so", "case_id", "created_at"),)

    def __repr__(self) -> str:
        return f"<CaseMessage {self.case_id} {self.kind} by {self.author}>"


class CaseAttachment(Base):
    """Một tệp đính kèm trên hồ sơ (#80).

    Dòng này chỉ giữ siêu dữ liệu — tên, loại, kích thước, ai đính kèm — còn nội dung nhị phân
    nằm trong SeaweedFS dưới khóa `storage_key` (ADR-0002). Khóa là chuỗi ngẫu nhiên, không
    mang tên tệp: tên do người dùng đặt không bao giờ đi vào đường dẫn của kho.

    Đính kèm không đổi hồ sơ nên không đi qua `perform_transition` và không vào nhật ký sự
    kiện (ADR-0005). **Chỉ ghi thêm**, như `case_messages`: trigger ở tầng cơ sở dữ liệu chặn
    UPDATE và DELETE — hồ sơ hủy vẫn giữ tệp để truy vết, giữ lại là quyết định ngày 26/10.
    """

    __tablename__ = "case_attachments"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    case_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("requests.id"))

    # Tên người dùng đặt, đã làm sạch. Chỉ để hiển thị và đặt tên tệp lúc tải về
    filename: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_key: Mapped[str] = mapped_column(Text, unique=True)

    # Định danh `sub` và tên tại thời điểm đính kèm — cùng lý do với `author_label`
    uploaded_by: Mapped[str] = mapped_column(Text)
    uploaded_by_label: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    __table_args__ = (Index("case_attachments_tra_theo_ho_so", "case_id", "created_at"),)

    def __repr__(self) -> str:
        return f"<CaseAttachment {self.case_id} {self.filename} ({self.size_bytes} B)>"


class CaseMessageRead(Base):
    """Một người đã đọc lời nhắn của một hồ sơ tới đâu — cho hộp thư chung (#155).

    Khác `CaseMessage`, dòng này được sửa: đọc thêm thì `last_read_id` dời lên. Nó là
    trạng thái hiển thị của từng người, không phải dấu vết của cuộc trao đổi, nên không vào
    nhật ký sự kiện và không chạm `requests` (ADR-0005). Xem migration 0008.

    Mỗi hồ sơ có hai cuộc trò chuyện — với người gửi và nội bộ (#156) — nên mốc đã đọc
    tính riêng từng cuộc: đọc bên này không làm bên kia thành đã đọc. Xem migration 0009.
    """

    __tablename__ = "case_message_reads"

    case_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("requests.id"), primary_key=True)
    reader: Mapped[str] = mapped_column(Text, primary_key=True)
    # Mốc của cuộc nội bộ — lời nhắn thuộc loại `hidden_from_requester`
    internal: Mapped[bool] = mapped_column(Boolean, primary_key=True, default=False)
    last_read_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("case_messages.id"))
    read_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
