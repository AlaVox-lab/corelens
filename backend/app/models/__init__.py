# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab

"""Lược đồ dữ liệu dùng chung.

Gom mọi mô hình về một chỗ vì chúng được đọc từ nhiều không gian kiến trúc: `P` đổi
trạng thái, `D` truy vấn chỉ số từ nhật ký sự kiện, `I` đọc nhật ký để khai phá quy
trình. Logic của từng không gian nằm trong thư mục riêng của nó.

Hai nhóm bảng, hai chủ sở hữu khác nhau:

- `workflow_config` — mười ba bảng cấu hình, do lược đồ khởi tạo trong `infra/` tạo
  và nạp. Alembic được cấu hình bỏ qua chúng
- `case` — hồ sơ yêu cầu, nhật ký sự kiện và lời nhắn trên hồ sơ, do Alembic sở hữu
- `van_hanh` — nhịp bộ quét nền và bộ đếm giới hạn tốc độ (#243, #253), do Alembic sở hữu
- `quan_tri` — nhật ký thay đổi cấu hình (#255) và ủy quyền khi vắng mặt (#252), do Alembic sở hữu

Nhập tệp này là đủ để `Base.metadata` biết toàn bộ bảng, nên `alembic/env.py` chỉ cần
một dòng import.
"""

from app.models.case import AttachmentFileType, CaseAttachment, CaseMessage, EventLog, Request
from app.models.quan_tri import ConfigChange, Delegation
from app.models.thong_bao import (
    NotificationDelivery,
    NotificationOutbox,
    NotificationPreference,
    NotificationType,
)
from app.models.van_hanh import RateLimitHit, ScannerHeartbeat
from app.models.workflow_config import (
    Department,
    Guard,
    MessageKind,
    MessageKindRole,
    Priority,
    Process,
    RequestType,
    RequestTypeRouting,
    Role,
    RuleSet,
    State,
    Transition,
    TransitionGuard,
    TransitionRole,
)

__all__ = [
    "AttachmentFileType",
    "CaseAttachment",
    "CaseMessage",
    "ConfigChange",
    "Delegation",
    "Department",
    "EventLog",
    "Guard",
    "MessageKind",
    "MessageKindRole",
    "NotificationDelivery",
    "NotificationOutbox",
    "NotificationPreference",
    "NotificationType",
    "Priority",
    "Process",
    "RateLimitHit",
    "Request",
    "RequestType",
    "RequestTypeRouting",
    "Role",
    "RuleSet",
    "ScannerHeartbeat",
    "State",
    "Transition",
    "TransitionGuard",
    "TransitionRole",
]
