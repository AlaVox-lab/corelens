# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ba bảng vận hành do ứng dụng sở hữu (#243, #253, #426): nhịp của các bộ quét nền, bộ đếm giới
# hạn tốc độ, và khóa trùng lặp của lệnh lõi.
#
# Không bảng nào là dữ liệu nghiệp vụ, không bảng nào vào nhật ký sự kiện. Chúng nằm trong cơ sở
# dữ liệu chứ không trong bộ nhớ tiến trình vì dịch vụ ứng dụng có thể chạy nhiều bản: nhịp phải
# thấy được từ mọi bản (và từ màn Hệ thống), còn bộ đếm phải cộng dồn chung — hai bản mà mỗi bản
# tự đếm thì giới hạn thực tế thành gấp đôi.

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    BigInteger,
    DateTime,
    Identity,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ScannerHeartbeat(Base):
    """Nhịp của một bộ quét nền: lần chạy cuối, lần thành công cuối, lần lỗi cuối (#253).

    Một dòng mỗi bộ quét. Bản dịch vụ nào giành được khóa tư vấn thì ghi dòng này trong chính
    giao dịch quét; lượt quét hỏng ghi ở giao dịch riêng sau khi hoàn tác, nên dấu vết lỗi không
    mất theo lượt hỏng. `/health` và màn Hệ thống đọc bảng này để biết bộ quét còn sống không.
    """

    __tablename__ = "scanner_heartbeats"

    name: Mapped[str] = mapped_column(Text, primary_key=True)
    last_started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_success_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_error_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    # Câu lỗi ngắn của lần hỏng gần nhất. Chỉ quản trị viên đọc được (màn Hệ thống), không bao giờ
    # nằm trong `/health` công khai
    last_error: Mapped[str | None] = mapped_column(Text, default=None)
    # Số lượt hỏng liên tiếp tính từ lần thành công cuối; một lượt thành công đặt về 0
    consecutive_errors: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    # Bản dịch vụ chạy lượt gần nhất — tên máy chủ (trong Docker là mã container) và mã tiến trình
    runner_host: Mapped[str | None] = mapped_column(Text, default=None)
    runner_pid: Mapped[int | None] = mapped_column(Integer, default=None)

    def __repr__(self) -> str:
        return f"<ScannerHeartbeat {self.name} errors={self.consecutive_errors}>"


class RateLimitHit(Base):
    """Số lần gọi trong một cửa sổ thời gian cố định, theo khóa (#243).

    Khóa là `<tên giới hạn>:<định danh người dùng>`. Cửa sổ cố định (không trượt) vì bộ đếm chỉ cần
    một phép `INSERT ... ON CONFLICT DO UPDATE` nguyên tử — đúng khi nhiều bản dịch vụ cùng ghi.
    Dòng cũ được dọn trong vòng của bộ quét (`app/rate_limit.py`).
    """

    __tablename__ = "rate_limit_hits"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    window_start: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    hits: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (Index("rate_limit_hits_theo_cua_so", "window_start"),)

    def __repr__(self) -> str:
        return f"<RateLimitHit {self.key} {self.window_start:%H:%M:%S} x{self.hits}>"


class IdempotencyKey(Base):
    """Khóa trùng lặp `Idempotency-Key` của lệnh tạo hồ sơ và bước chuyển ở lõi `/core/v1` (#426).

    Một dòng mỗi (người gọi, điểm cuối, khóa). Sinh ở `in_progress` trong giao dịch riêng, đổi sang `completed`
    trong CÙNG giao dịch với lần tạo hay lần chuyển, nên gọi lặp sau khi máy chết giữa chừng vẫn không chạy
    lệnh lần hai. Chỉ lần thành công được giữ. Dòng hết hạn được dọn trong vòng của bộ quét nền
    (`app/workflow/khoa_trung_lap.py`).
    """

    __tablename__ = "idempotency_keys"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    # Mã người gọi trong token (`sub`) — tài khoản dịch vụ hay người. Không lưu tên
    actor: Mapped[str] = mapped_column(Text)
    # Phương thức và mẫu đường, ví dụ `POST /core/v1/workflow/requests/{case_id}/transitions`
    endpoint: Mapped[str] = mapped_column(Text)
    # Giá trị tiêu đề `Idempotency-Key` người gọi gửi: 1–255 ký tự ASCII in được
    key: Mapped[str] = mapped_column(Text)
    # sha256 của thân yêu cầu chuẩn hóa cộng tham số đường: cùng khóa mà khác lệnh thì bị từ chối
    request_hash: Mapped[str] = mapped_column(Text)
    # `in_progress` khi lần gọi đang chạy, `completed` khi lệnh đã commit
    status: Mapped[str] = mapped_column(Text)
    # Hồ sơ lệnh đã tạo hay đã chuyển, đặt cùng giao dịch với lệnh
    case_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
    # Mã HTTP của lần thành công, trả lại nguyên cho lần gọi lặp. Ghi sau commit, giao dịch riêng
    response_status: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    # Thân phản hồi JSON của lần thành công. Trống nếu ghi sau commit hỏng: lần lặp dựng lại chi tiết hồ sơ
    # `case_id`
    response_body: Mapped[dict | None] = mapped_column(JSONB, default=None)
    # Lúc lần gọi đầu giữ khóa
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Lần đang chạy giữ khóa tới mốc này (`IDEMPOTENCY_LOCK_SECONDS`); quá mốc thì coi là bỏ dở, lần sau chiếm lại
    locked_until: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    # Khóa sống tới mốc này (`IDEMPOTENCY_TTL_HOURS`); quá mốc thì gọi lại cùng khóa là lệnh mới
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("actor", "endpoint", "key", name="idempotency_keys_mot_khoa_moi_nguoi_goi"),
        Index("idempotency_keys_theo_han", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<IdempotencyKey {self.endpoint} {self.status} case={self.case_id}>"
