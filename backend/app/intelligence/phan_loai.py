# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Sinh gợi ý loại yêu cầu, mức ưu tiên, phòng ban bằng mô hình ngôn ngữ (#317).
#
# HAI ĐƯỜNG VÀO, MỘT ĐƯỜNG GHI
#
# - Tác vụ nền ngay sau khi hồ sơ được gửi (`goi_y_sau_khi_gui`, gắn ở điểm cuối gửi hồ sơ). Chạy sau
#   khi phản hồi đã về trình duyệt, nên người gửi không chờ mô hình.
# - Bộ quét bù (`quet_goi_y`), theo khuôn `app/workflow/nhip_quet.py`: khóa tư vấn, dòng nhịp, có mặt
#   trong `scanners` của sức khỏe hệ thống. Nó nhặt hồ sơ CÒN Ở CHỖ ĐIỀU PHỐI mà chưa có gợi ý — tác
#   vụ nền rơi khi dịch vụ khởi động lại, mô hình bật muộn, lần trước mô hình trả rác — và xử lý lần
#   lượt từng cái.
#
# Cả hai đi qua `thu_goi_y`, gồm ba bước, mỗi bước một giao dịch NGẮN:
#
#   1. Giành hồ sơ: một câu UPDATE có điều kiện đặt mốc thử và cộng số lần thử. Hai đường cùng nhắm
#      một hồ sơ thì chỉ một đường giành được — không hỏi mô hình hai lần.
#   2. Hỏi mô hình qua `mo_hinh.py` — KHÔNG giữ giao dịch, khóa dòng hay kết nối nào trong lúc chờ.
#      Giữ khóa dòng ở đây thì điều phối viên bấm phân loại đúng lúc đó sẽ phải chờ mô hình.
#   3. Ghi trường GỢI Ý qua đường riêng này, không qua cửa chuyển trạng thái — mã kiểm lại với danh
#      mục đang bật, và chỉ ghi khi hồ sơ còn ở trạng thái lúc giành. Không bao giờ chạm trường quyết
#      định (CLAUDE.md mục 4.3), không đổi `updated_at`: gợi ý tới giữa lúc điều phối viên đang chọn
#      thì biểu mẫu của họ không bị dựng lại.
#
# Mô hình không tới được (tắt, cổng đóng) thì lần thử không tính và lượt quét dừng sớm; mô hình trả
# lời mà hỏng (quá hạn, rác, mã lạ) thì tính — tới `suggest_max_attempts` lần thì thôi.

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from sqlalchemy import and_, func, literal, or_, select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.intelligence import mo_hinh
from app.models.case import Request
from app.models.workflow_config import Department, Priority, RequestType

log = logging.getLogger(__name__)

TEN_BO_QUET_GOI_Y = "suggestion-backfill"
NHAN_BO_QUET_GOI_Y = "Bộ quét gợi ý phân loại"

# Kết quả của một lần `thu_goi_y`, ngoài các mã lỗi `mo_hinh.LOI_*`
DA_GHI = "ok"
BO_QUA = "skipped"  # đường khác đã giành, hoặc hồ sơ không còn cần gợi ý
DA_ROI_DI = "moved-on"  # hồ sơ đã rời trạng thái lúc giành khi mô hình trả lời

# Trường gợi ý tương ứng với từng trường quyết định mô hình gợi ý
COT_GOI_Y = {
    mo_hinh.TRUONG_LOAI: "suggested_request_type_code",
    mo_hinh.TRUONG_MUC: "suggested_priority_code",
    mo_hinh.TRUONG_PHONG: "suggested_department_code",
}

MoPhien = Callable[[], AbstractContextManager[Session]]


def _mo_phien_that() -> AbstractContextManager[Session]:
    from app.db import SessionLocal

    return SessionLocal()


def _chua_co_goi_y():
    """Chưa có lần thử nào thành công."""
    return func.coalesce(Request.suggestion_note["ok"].as_boolean(), False).is_(False)


def _duoc_thu_lai():
    """Điều kiện bộ quét bù được hỏi lại: chưa thành công, còn lượt, và đã đủ lâu từ lần trước."""
    cau_hinh = get_settings()
    return and_(
        _chua_co_goi_y(),
        or_(
            Request.suggestion_attempts == 0,
            and_(
                Request.suggestion_attempts < cau_hinh.suggest_max_attempts,
                Request.suggestion_attempted_at
                < func.now() - literal(dt.timedelta(seconds=cau_hinh.suggest_retry_after_seconds)),
            ),
        ),
    )


def _ghi_chu_loi(ma: str) -> dict[str, Any]:
    return {"ok": False, "error": ma, "at": dt.datetime.now(dt.UTC).isoformat()}


def _ghi_ket_thuc(phien: Session, ma_ho_so: int, gia_tri: dict[str, Any], *, dieu_kien=None) -> int:
    """UPDATE trường gợi ý của một hồ sơ, giữ nguyên `updated_at`. Trả số dòng đã ghi."""
    cau = update(Request).where(Request.id == ma_ho_so)
    if dieu_kien is not None:
        cau = cau.where(dieu_kien)
    # Đặt `updated_at` bằng chính nó để `onupdate` không chạy: gợi ý không phải một lần đổi hồ sơ
    ket_qua = phien.execute(
        cau.values(**gia_tri, updated_at=Request.updated_at).execution_options(
            synchronize_session=False
        )
    )
    return ket_qua.rowcount


def _ma_dang_bat(phien: Session) -> dict[str, set[str]]:
    return {
        mo_hinh.TRUONG_LOAI: set(phien.scalars(select(RequestType.code).where(RequestType.is_active))),
        mo_hinh.TRUONG_MUC: set(phien.scalars(select(Priority.code))),
        mo_hinh.TRUONG_PHONG: set(phien.scalars(select(Department.code).where(Department.is_active))),
    }


def thu_goi_y(ma_ho_so: int, *, lan_dau: bool, mo_phien: MoPhien = _mo_phien_that) -> str:
    """Một lần sinh gợi ý cho một hồ sơ. Không bao giờ ném lỗi của mô hình; trả mã kết quả.

    `lan_dau` — đường tác vụ nền: chỉ giành hồ sơ chưa từng thử. Bộ quét bù gọi với `lan_dau=False`
    và điều kiện thử lại theo cấu hình.
    """
    cau_hinh = get_settings()
    if not cau_hinh.llm_enabled:
        return mo_hinh.LOI_TAT

    # --- 1. Giành hồ sơ, đọc đề bài --------------------------------------------
    with mo_phien() as phien:
        dieu_kien = Request.suggestion_attempts == 0 if lan_dau else _duoc_thu_lai()
        dong = phien.execute(
            update(Request)
            .where(Request.id == ma_ho_so, dieu_kien)
            .values(
                suggestion_attempted_at=func.now(),
                suggestion_attempts=Request.suggestion_attempts + 1,
                updated_at=Request.updated_at,
            )
            .returning(Request.current_state)
            .execution_options(synchronize_session=False)
        ).first()
        if dong is None:
            phien.rollback()
            return BO_QUA
        trang_thai = dong[0]
        ho_so = phien.get(Request, ma_ho_so, populate_existing=True)
        try:
            de_bai = mo_hinh.de_bai_cua_ho_so(phien, ho_so)
        except mo_hinh.LoiMoHinh as loi:
            _ghi_ket_thuc(phien, ma_ho_so, {"suggestion_note": _ghi_chu_loi(loi.ma)})
            phien.commit()
            return loi.ma
        phien.commit()

    # --- 2. Hỏi mô hình, không giữ gì của cơ sở dữ liệu ------------------------
    try:
        ket_qua = mo_hinh.hoi_phan_loai(de_bai)
    except mo_hinh.LoiMoHinh as loi:
        log.warning("Không sinh được gợi ý cho hồ sơ %s: %s", ma_ho_so, loi)
        gia_tri: dict[str, Any] = {"suggestion_note": _ghi_chu_loi(loi.ma)}
        if loi.khong_toi_duoc:
            # Không phải lỗi của hồ sơ này: trả lại lượt thử
            gia_tri["suggestion_attempts"] = func.greatest(Request.suggestion_attempts - 1, 0)
        with mo_phien() as phien:
            _ghi_ket_thuc(phien, ma_ho_so, gia_tri)
            phien.commit()
        return loi.ma

    # --- 3. Ghi trường gợi ý qua đường riêng ------------------------------------
    with mo_phien() as phien:
        dang_bat = _ma_dang_bat(phien)
        # Danh mục có thể đổi trong lúc chờ mô hình: kiểm lại trước khi ghi
        if any(ket_qua.ma(t) not in dang_bat[t] for t in mo_hinh.CAC_TRUONG):
            _ghi_ket_thuc(phien, ma_ho_so, {"suggestion_note": _ghi_chu_loi(mo_hinh.LOI_NGOAI_DANH_MUC)})
            phien.commit()
            return mo_hinh.LOI_NGOAI_DANH_MUC

        ghi_chu = {
            "ok": True,
            "model": ket_qua.model,
            "at": dt.datetime.now(dt.UTC).isoformat(),
            "elapsed_ms": ket_qua.elapsed_ms,
            "reasons": ket_qua.reasons,
            # Phòng mô hình đoán — giữ cả khi cờ tắt, để đo được trước khi bật
            "model_department": ket_qua.department_code,
        }
        gia_tri = {
            COT_GOI_Y[mo_hinh.TRUONG_LOAI]: ket_qua.request_type_code,
            COT_GOI_Y[mo_hinh.TRUONG_MUC]: ket_qua.priority_code,
            "suggestion_note": ghi_chu,
        }
        # Ngưỡng 80 % (#317): phòng của mô hình chỉ thay bảng ánh xạ khi người vận hành bật cờ
        if cau_hinh.suggest_department_from_model:
            gia_tri[COT_GOI_Y[mo_hinh.TRUONG_PHONG]] = ket_qua.department_code

        da_ghi = _ghi_ket_thuc(
            phien, ma_ho_so, gia_tri, dieu_kien=Request.current_state == trang_thai
        )
        if not da_ghi:
            # Điều phối viên đã đi tiếp trong lúc chờ: gợi ý không còn ai dùng, chỉ đánh dấu đã thử
            _ghi_ket_thuc(phien, ma_ho_so, {"suggestion_note": _ghi_chu_loi(DA_ROI_DI)})
        phien.commit()
    return DA_GHI if da_ghi else DA_ROI_DI


def goi_y_sau_khi_gui(ma_ho_so: int) -> None:
    """Tác vụ nền của điểm cuối gửi hồ sơ. Lỗi nào cũng chỉ ghi nhật ký — bộ quét bù sẽ thử lại."""
    try:
        thu_goi_y(ma_ho_so, lan_dau=True)
    except Exception:  # noqa: BLE001 — tác vụ nền không được làm hỏng gì của người gửi
        log.exception("Tác vụ sinh gợi ý cho hồ sơ %s thất bại", ma_ho_so)


def ho_so_can_goi_y(phien: Session, gioi_han: int) -> list[int]:
    """Hồ sơ đang ở trạng thái của điều phối viên, chưa có gợi ý và được phép hỏi lại, cũ trước."""
    # Nhập muộn: `coordination` nhập cả chuỗi điểm cuối, còn tệp này được `routes` nhập lúc gửi hồ sơ
    from app.workflow.coordination import trang_thai_hang_doi_dieu_phoi
    from app.workflow.engine import ma_quy_trinh_ung_dung, rule_sets_in_use

    dieu_kien_trang_thai = [
        and_(
            Request.rule_set_id == bo,
            Request.current_state.in_([t.code for t in trang_thai_hang_doi_dieu_phoi(phien, bo)]),
        )
        for bo in rule_sets_in_use(phien, ma_quy_trinh_ung_dung(phien))
    ]
    if not dieu_kien_trang_thai:
        return []
    return list(
        phien.scalars(
            select(Request.id)
            .where(or_(*dieu_kien_trang_thai), _duoc_thu_lai())
            .order_by(Request.created_at, Request.id)
            .limit(gioi_han)
        )
    )


def quet_goi_y(phien: Session, mo_phien: MoPhien = _mo_phien_that) -> list[int]:
    """Một lượt của bộ quét bù. `phien` là phiên giữ khóa tư vấn của lượt (xem `nhip_quet.py`) — chỉ
    dùng để đọc danh sách; mỗi hồ sơ xử lý trong các giao dịch ngắn riêng. Trả hồ sơ đã có gợi ý."""
    cau_hinh = get_settings()
    if not cau_hinh.llm_enabled:
        return []
    da_ghi: list[int] = []
    for ma in ho_so_can_goi_y(phien, cau_hinh.suggest_scan_batch_size):
        ket_qua = thu_goi_y(ma, lan_dau=False, mo_phien=mo_phien)
        if ket_qua == DA_GHI:
            da_ghi.append(ma)
        elif ket_qua in (mo_hinh.LOI_TAT, mo_hinh.LOI_KHONG_KET_NOI):
            # Mô hình không tới được: hỏi tiếp các hồ sơ sau cũng vô ích
            break
    if da_ghi:
        log.info("Bộ quét gợi ý đã gợi ý cho %d hồ sơ", len(da_ghi))
    return da_ghi
