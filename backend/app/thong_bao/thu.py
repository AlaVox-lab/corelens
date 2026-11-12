# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Gửi thư qua SMTP bằng `smtplib` của thư viện chuẩn (#251) — không thêm gói nào.
#
# Một kết nối cho cả một lượt gửi: mở lúc gặp thư đầu tiên, đóng khi lượt xong. Mở không được
# (máy chủ thư sập, sai cổng) thì ném `ThuLoi` ngay — bộ quét hoãn cả lượt thay vì chờ hết hạn chót
# cho từng thư một.

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.config import get_settings


class ThuLoi(Exception):
    """Không gửi được một thư, hay không mở được kết nối tới máy chủ thư."""


class KetNoiThu:
    """Kết nối SMTP mở lười, dùng trong `with`."""

    def __init__(self, han_chot: float | None = None) -> None:
        self._may_chu: smtplib.SMTP | None = None
        self._han_chot = han_chot

    @property
    def da_mo(self) -> bool:
        """Kết nối đang mở và dùng được — sai sau một lần mở hỏng hay gửi hỏng."""
        return self._may_chu is not None

    def __enter__(self) -> KetNoiThu:
        return self

    def __exit__(self, *_: object) -> None:
        if self._may_chu is not None:
            try:
                self._may_chu.quit()
            except (smtplib.SMTPException, OSError):
                pass
            self._may_chu = None

    def _mo(self) -> smtplib.SMTP:
        if self._may_chu is not None:
            return self._may_chu
        ch = get_settings()
        han_chot = self._han_chot or ch.smtp_timeout_seconds
        try:
            if ch.smtp_security == "ssl":
                may = smtplib.SMTP_SSL(
                    ch.smtp_host,
                    ch.smtp_port,
                    timeout=han_chot,
                    context=ssl.create_default_context(),
                )
            else:
                may = smtplib.SMTP(ch.smtp_host, ch.smtp_port, timeout=han_chot)
                if ch.smtp_security == "starttls":
                    may.starttls(context=ssl.create_default_context())
            if ch.smtp_username:
                may.login(ch.smtp_username, ch.smtp_password)
        except (smtplib.SMTPException, OSError) as loi:
            raise ThuLoi(f"Không kết nối được máy chủ thư: {type(loi).__name__}: {loi}") from loi
        self._may_chu = may
        return may

    def gui(self, den: str, ten_nguoi_nhan: str, tieu_de: str, noi_dung: str) -> None:
        ch = get_settings()
        thu = EmailMessage()
        thu["From"] = ch.smtp_from
        thu["To"] = formataddr((ten_nguoi_nhan, den))
        thu["Subject"] = tieu_de
        thu["Message-ID"] = make_msgid(domain="dx-os-lab")
        thu.set_content(noi_dung)
        may = self._mo()
        try:
            may.send_message(thu)
        except (smtplib.SMTPException, OSError) as loi:
            # Kết nối có thể đã hỏng: lần gửi sau mở lại
            self._may_chu = None
            raise ThuLoi(f"{type(loi).__name__}: {loi}") from loi


def tinh_trang() -> dict:
    """Cho màn Hệ thống: `disabled`, `ready` hoặc `unreachable` — thử mở rồi đóng một kết nối."""
    ch = get_settings()
    if not ch.notify_enabled:
        return {"status": "disabled"}
    try:
        # Hạn chót ngắn: màn Hệ thống không được treo theo một dịch vụ tùy chọn
        with KetNoiThu(han_chot=min(3.0, ch.smtp_timeout_seconds)) as k:
            k._mo().noop()
    except (ThuLoi, smtplib.SMTPException, OSError) as loi:
        return {"status": "unreachable", "detail": str(loi)[:160]}
    return {"status": "ready"}
