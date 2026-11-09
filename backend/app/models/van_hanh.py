# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Hai bảng vận hành do ứng dụng sở hữu (#243, #253): nhịp của các bộ quét nền, và bộ đếm giới
# hạn tốc độ.
#
# Không bảng nào là dữ liệu nghiệp vụ, không bảng nào vào nhật ký sự kiện. Chúng nằm trong cơ sở
# dữ liệu chứ không trong bộ nhớ tiến trình vì dịch vụ ứng dụng có thể chạy nhiều bản: nhịp phải
# thấy được từ mọi bản (và từ màn Hệ thống), còn bộ đếm phải cộng dồn chung — hai bản mà mỗi bản
# tự đếm thì giới hạn thực tế thành gấp đôi.

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Index, Integer, Text, text
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
