# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Khóa và nhịp của các bộ quét nền (#253).
#
# Hai việc, cùng một lý do tồn tại: dịch vụ ứng dụng chạy được nhiều bản, và một bộ quét im lặng
# là thứ chỉ phát hiện ra khi đã muộn.
#
# 1. KHÓA. Mỗi lượt quét xin khóa tư vấn mức giao dịch của PostgreSQL (`pg_try_advisory_xact_lock`)
#    theo tên bộ quét. Bản nào xin được thì quét, bản kia BỎ LƯỢT — không chờ, không tính là lỗi.
#    Khóa gắn với giao dịch của lượt quét nên tự nhả khi giao dịch kết thúc, kể cả khi tiến trình
#    chết giữa chừng; không có khóa treo nào cần ai dọn. Dữ liệu vốn không hỏng khi hai bản cùng
#    quét (cổng chuyển trạng thái khóa dòng hồ sơ), nhưng làm việc trùng và sinh nhiễu nhật ký.
#
# 2. NHỊP. Lượt xong thì ghi `scanner_heartbeats`: thành công thì đặt số lỗi liên tiếp về 0, hỏng
#    thì cộng một. Ghi lỗi nằm ở giao dịch RIÊNG, sau khi hoàn tác lượt hỏng — nếu ghi chung thì
#    chính dấu vết của lượt hỏng bị hoàn tác theo. `/health` và màn Hệ thống đọc bảng này.
#
# Hàm nhận sẵn một phiên thay vì tự mở: người gọi quyết định phiên thật hay phiên của bài kiểm
# thử, và hai phiên trên hai kết nối riêng là cách duy nhất thử được tranh khóa.

from __future__ import annotations

import os
import socket
import zlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.van_hanh import ScannerHeartbeat

# Khóa tư vấn gồm hai số nguyên 32 bit. Số đầu là "không gian tên" của dự án, để khóa của bộ quét
# không đụng khóa tư vấn nào khác dùng chung cơ sở dữ liệu; số sau suy từ tên bộ quét.
KHONG_GIAN_KHOA = 0x44584C42  # "DXLB"

# Câu lỗi lưu lại cho quản trị viên chỉ cần đủ nhận ra nguyên nhân
DO_DAI_CAU_LOI = 300

# Trạng thái từng bộ quét, theo thứ tự từ tốt tới xấu
TOT = "ok"
DANG_KHOI_DONG = "starting"
QUA_LAU = "stale"
DANG_HONG = "failing"
DA_TAT = "disabled"


@dataclass(frozen=True, slots=True)
class LuotQuet:
    """Kết quả một lượt: `da_chay` sai nghĩa là bản khác đang giữ khóa nên lượt này bị bỏ."""

    da_chay: bool
    ket_qua: Any = None


def khoa_cua(ten: str) -> tuple[int, int]:
    """Cặp số của khóa tư vấn ứng với tên bộ quét — ổn định giữa các tiến trình và phiên bản
    Python (băm bằng CRC32, không dùng `hash()` vốn đổi mỗi lần chạy)."""
    so = zlib.crc32(ten.encode("utf-8"))
    # PostgreSQL đọc int4 có dấu
    if so >= 2**31:
        so -= 2**32
    return KHONG_GIAN_KHOA, so


def _danh_tinh_ban_chay() -> dict[str, Any]:
    return {"host": socket.gethostname(), "pid": os.getpid()}


def chay_luot_quet(
    phien: Session, ten: str, ham_quet: Callable[[Session], Any]
) -> LuotQuet:
    """Chạy một lượt của bộ quét `ten` nếu giành được khóa; ngược lại bỏ lượt.

    `ham_quet(phien)` làm việc quét và KHÔNG tự commit, như `quet_va_leo_thang`. Hàm này lo ranh
    giới giao dịch: thành công thì commit cả kết quả quét lẫn nhịp; hỏng thì hoàn tác, ghi lỗi ở
    giao dịch riêng, rồi ném lại lỗi cho phía gọi ghi nhật ký.
    """
    so_1, so_2 = khoa_cua(ten)
    giu_khoa = phien.execute(
        text("SELECT pg_try_advisory_xact_lock(CAST(:a AS integer), CAST(:b AS integer))"),
        {"a": so_1, "b": so_2},
    ).scalar_one()
    if not giu_khoa:
        # Bản khác đang quét. Kết thúc giao dịch rỗng để trả kết nối về hồ chứa
        phien.rollback()
        return LuotQuet(da_chay=False)

    bat_dau = phien.execute(text("SELECT clock_timestamp()")).scalar_one()
    try:
        ket_qua = ham_quet(phien)
        _ghi_thanh_cong(phien, ten, bat_dau)
        phien.commit()
    except Exception as loi:
        phien.rollback()
        _ghi_loi(phien, ten, bat_dau, loi)
        phien.commit()
        raise
    return LuotQuet(da_chay=True, ket_qua=ket_qua)


def _ghi_thanh_cong(phien: Session, ten: str, bat_dau) -> None:
    phien.execute(
        text(
            """
            INSERT INTO scanner_heartbeats
                (name, last_started_at, last_success_at, consecutive_errors, runner_host, runner_pid)
            VALUES (:ten, :bat_dau, clock_timestamp(), 0, :host, :pid)
            ON CONFLICT (name) DO UPDATE SET
                last_started_at = EXCLUDED.last_started_at,
                last_success_at = EXCLUDED.last_success_at,
                consecutive_errors = 0,
                runner_host = EXCLUDED.runner_host,
                runner_pid = EXCLUDED.runner_pid
            """
        ),
        {"ten": ten, "bat_dau": bat_dau, **_danh_tinh_ban_chay()},
    )


def _ghi_loi(phien: Session, ten: str, bat_dau, loi: Exception) -> None:
    cau_loi = f"{type(loi).__name__}: {loi}"[:DO_DAI_CAU_LOI]
    phien.execute(
        text(
            """
            INSERT INTO scanner_heartbeats
                (name, last_started_at, last_error_at, last_error, consecutive_errors,
                 runner_host, runner_pid)
            VALUES (:ten, :bat_dau, clock_timestamp(), :cau_loi, 1, :host, :pid)
            ON CONFLICT (name) DO UPDATE SET
                last_started_at = EXCLUDED.last_started_at,
                last_error_at = EXCLUDED.last_error_at,
                last_error = EXCLUDED.last_error,
                consecutive_errors = scanner_heartbeats.consecutive_errors + 1,
                runner_host = EXCLUDED.runner_host,
                runner_pid = EXCLUDED.runner_pid
            """
        ),
        {"ten": ten, "bat_dau": bat_dau, "cau_loi": cau_loi, **_danh_tinh_ban_chay()},
    )


def danh_gia_bo_quet(
    phien: Session,
    cac_bo_quet: dict[str, str],
    *,
    nguong_qua_lau_giay: int,
    loi_lien_tiep_toi_da: int,
    da_chay_giay: float,
    dang_bat: bool = True,
) -> list[dict[str, Any]]:
    """Tình trạng từng bộ quét, đọc từ bảng nhịp. `cac_bo_quet` ánh xạ tên sang nhãn hiển thị.

    Một bộ quét là xấu (`stale`, `failing`) khi:
    - hỏng liên tiếp tới `loi_lien_tiep_toi_da` lượt; hoặc
    - lần thành công cuối đã quá `nguong_qua_lau_giay` VÀ tiến trình này cũng chạy quá chừng ấy.
      Vế sau để một lần khởi động lại sau thời gian dừng dài không báo đỏ ngay: bộ quét chưa có
      cơ hội chạy. Tiến trình chạy đủ lâu mà vẫn chưa có lượt thành công — kể cả khi chưa từng có
      dòng nhịp nào — mới là bộ quét chết.

    Tắt bộ quét bằng cấu hình (`dang_bat=False`) là chủ ý của người vận hành, không phải sự cố.
    """
    hang = {
        h.name: h
        for h in phien.scalars(
            select(ScannerHeartbeat).where(ScannerHeartbeat.name.in_(list(cac_bo_quet)))
        )
    }
    bay_gio = phien.execute(text("SELECT clock_timestamp()")).scalar_one()

    ket_qua: list[dict[str, Any]] = []
    for ten, nhan in cac_bo_quet.items():
        h = hang.get(ten)
        giay_tu_thanh_cong = (
            (bay_gio - h.last_success_at).total_seconds()
            if h is not None and h.last_success_at is not None
            else None
        )

        if not dang_bat:
            tinh_trang = DA_TAT
        elif h is not None and h.consecutive_errors >= loi_lien_tiep_toi_da:
            tinh_trang = DANG_HONG
        elif da_chay_giay <= nguong_qua_lau_giay:
            tinh_trang = DANG_KHOI_DONG if giay_tu_thanh_cong is None else TOT
        elif giay_tu_thanh_cong is None or giay_tu_thanh_cong > nguong_qua_lau_giay:
            tinh_trang = QUA_LAU
        else:
            tinh_trang = TOT

        ket_qua.append(
            {
                "name": ten,
                "label": nhan,
                "status": tinh_trang,
                "last_started_at": h.last_started_at if h else None,
                "last_success_at": h.last_success_at if h else None,
                "last_error_at": h.last_error_at if h else None,
                "last_error": h.last_error if h else None,
                "consecutive_errors": h.consecutive_errors if h else 0,
                "seconds_since_success": (
                    round(giay_tu_thanh_cong) if giay_tu_thanh_cong is not None else None
                ),
                "runner_host": h.runner_host if h else None,
                "runner_pid": h.runner_pid if h else None,
            }
        )
    return ket_qua


def co_bo_quet_xau(cac_tinh_trang: list[dict[str, Any]]) -> bool:
    """Có bộ quét nào đang ở tình trạng cần chú ý không."""
    return any(t["status"] in (QUA_LAU, DANG_HONG) for t in cac_tinh_trang)
