# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Sổ các bản lưu trữ lạnh đã xuất (#378, nguyên lý (i) của đề thi).
#
# Mỗi tháng đã khép có đúng một bản lưu trong kho đối tượng: nhật ký sự kiện và hồ sơ đã kết thúc của tháng
# đó, kèm `manifest.json` ghi số dòng và mã băm từng tệp. Bảng này là sổ ghi những bản đã niêm phong — API
# lõi liệt kê từ đây mà không phải hỏi kho, và bộ quét biết tháng nào đã xong. Chỉ ghi thêm (trigger của bản
# sửa 0029): bản lưu là bất biến thì dòng ghi sổ của nó cũng vậy.

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Integer, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ColdArchive(Base):
    """Một bản lưu trữ lạnh đã niêm phong: một tháng UTC, mọi quy trình."""

    __tablename__ = "cold_archives"

    # Kỳ dạng `YYYY-MM`, tính theo UTC như mốc trong nhật ký
    period: Mapped[str] = mapped_column(Text, primary_key=True)
    # Thùng và tiền tố khóa trong kho đối tượng lúc xuất — đổi cấu hình về sau không làm mất dấu bản cũ
    bucket: Mapped[str] = mapped_column(Text)
    object_prefix: Mapped[str] = mapped_column(Text)
    schema_version: Mapped[int] = mapped_column(SmallInteger)
    event_rows: Mapped[int] = mapped_column(Integer)
    case_rows: Mapped[int] = mapped_column(Integer)
    # Bản sao nguyên văn của manifest.json trong kho, và mã băm của chính tệp đó
    manifest: Mapped[dict] = mapped_column(JSONB)
    manifest_sha256: Mapped[str] = mapped_column(Text)
    exported_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    def __repr__(self) -> str:
        return f"<ColdArchive {self.period} events={self.event_rows} cases={self.case_rows}>"
