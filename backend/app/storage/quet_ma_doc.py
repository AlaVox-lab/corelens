# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Lớp gọi dịch vụ quét mã độc (#248).
#
# ClamAV chạy như một dịch vụ ĐỘC LẬP (ảnh `clamav/clamav`, GPL-2.0, hồ sơ Compose `quet-tep`) và
# dịch vụ ứng dụng nói chuyện với nó qua giao thức mạng của clamd — lệnh `INSTREAM`, viết bằng
# `socket` của thư viện chuẩn. Không nhúng, không liên kết thư viện nào của ClamAV: ranh giới giấy
# phép là ranh giới mạng, như Keycloak hay SeaweedFS (LICENSES.md).
#
# Giao thức (tài liệu clamd, mục INSTREAM): gửi `zINSTREAM\0`, rồi từng khúc `<độ dài 4 byte big-endian>
# <dữ liệu>`, kết thúc bằng khúc độ dài 0; clamd trả một dòng kết thúc bằng `\0`:
#   `stream: OK`                       sạch
#   `stream: <tên mẫu> FOUND`          nhiễm
#   `... ERROR`                        clamd không quét được (tệp vượt StreamMaxLength chẳng hạn)
# `zPING\0` → `PONG\0` để màn Hệ thống biết dịch vụ còn sống.
#
# Địa chỉ rỗng là TẮT — mặc định của cụm: không quét gì, tệp đi như trước #248. Mọi lời gọi có hạn
# chót; lỗi mạng, hết giờ, câu trả lời lạ đều thành `KHONG_PHAN_HOI` để phía gọi áp chính sách cấu
# hình — không lỗi nào của dịch vụ quét được thoát ra thành lỗi 500 của lần tải tệp.

from __future__ import annotations

import logging
import socket
import struct
from dataclasses import dataclass

from app.config import get_settings

logger = logging.getLogger(__name__)

# Kết quả một lần quét
SACH = "clean"
NHIEM = "infected"
KHONG_PHAN_HOI = "unavailable"
DA_TAT = "disabled"

# Khúc gửi sang clamd. Nhỏ hơn mặc định StreamMaxLength rất xa, đủ lớn để không tốn nhiều vòng
KHUC = 64 * 1024
# Câu trả lời của clamd chỉ một dòng ngắn
TRA_LOI_TOI_DA = 4096


@dataclass(frozen=True, slots=True)
class KetQuaQuet:
    trang_thai: str
    # Tên mẫu mã độc khi nhiễm, hay lý do ngắn khi không phản hồi
    chi_tiet: str | None = None


def dang_bat() -> bool:
    return bool(get_settings().clamav_host.strip())


def _goi(lenh: bytes, du_lieu: bytes | None = None, han_chot: float | None = None) -> str:
    """Mở một kết nối, gửi một lệnh (kèm dữ liệu cho INSTREAM), đọc câu trả lời tới `\\0`."""
    cau_hinh = get_settings()
    with socket.create_connection(
        (cau_hinh.clamav_host.strip(), cau_hinh.clamav_port),
        timeout=han_chot or cau_hinh.clamav_timeout_seconds,
    ) as ket_noi:
        ket_noi.sendall(lenh)
        if du_lieu is not None:
            for dau in range(0, len(du_lieu), KHUC):
                khuc = du_lieu[dau : dau + KHUC]
                ket_noi.sendall(struct.pack(">I", len(khuc)) + khuc)
            ket_noi.sendall(struct.pack(">I", 0))
        tra_loi = b""
        while b"\0" not in tra_loi and len(tra_loi) < TRA_LOI_TOI_DA:
            phan = ket_noi.recv(1024)
            if not phan:
                break
            tra_loi += phan
    return tra_loi.split(b"\0", 1)[0].decode("utf-8", "replace").strip()


def quet(noi_dung: bytes) -> KetQuaQuet:
    """Quét một tệp. Không bao giờ ném lỗi: dịch vụ quét hỏng thì trả `KHONG_PHAN_HOI`."""
    if not dang_bat():
        return KetQuaQuet(DA_TAT)
    try:
        tra_loi = _goi(b"zINSTREAM\0", noi_dung)
    except (OSError, TimeoutError) as loi:
        logger.warning("Dịch vụ quét mã độc không phản hồi: %s", loi)
        return KetQuaQuet(KHONG_PHAN_HOI, type(loi).__name__)

    # `stream: OK` / `stream: Eicar-Test-Signature FOUND` — phần sau dấu hai chấm đầu tiên
    ket_luan = tra_loi.split(":", 1)[-1].strip()
    if ket_luan == "OK":
        return KetQuaQuet(SACH)
    if ket_luan.endswith(" FOUND"):
        return KetQuaQuet(NHIEM, ket_luan[: -len(" FOUND")].strip() or None)
    logger.warning("Dịch vụ quét mã độc trả lời không quét được: %s", tra_loi[:200])
    return KetQuaQuet(KHONG_PHAN_HOI, tra_loi[:120] or "câu trả lời rỗng")


def tinh_trang() -> dict:
    """Cho màn Hệ thống: `disabled`, `ready` hoặc `unreachable` — cùng ba mức với mô hình ngôn ngữ."""
    if not dang_bat():
        return {"status": "disabled"}
    # Chính sách khi không phản hồi đi kèm để màn hình nói được tệp mới đang bị xử lý thế nào
    chinh_sach = get_settings().clamav_on_unavailable
    try:
        # Hạn chót ngắn: màn Hệ thống không được treo theo một dịch vụ tùy chọn
        tra_loi = _goi(b"zPING\0", han_chot=min(3.0, get_settings().clamav_timeout_seconds))
    except (OSError, TimeoutError) as loi:
        return {"status": "unreachable", "detail": type(loi).__name__, "on_unavailable": chinh_sach}
    if tra_loi == "PONG":
        return {"status": "ready", "on_unavailable": chinh_sach}
    return {
        "status": "unreachable",
        "detail": tra_loi[:120] or "câu trả lời rỗng",
        "on_unavailable": chinh_sach,
    }
