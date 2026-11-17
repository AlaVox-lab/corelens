# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Gợi ý người xử lý cho trưởng phòng (#318). Không cần mô hình ngôn ngữ.
#
# ỨNG VIÊN là đúng danh sách của ô chọn người xử lý: người trong phòng đang giữ hồ sơ, nhận được việc
# (`assignment.nguoi_nhan_viec` — cùng hàm, cùng danh bạ). Người phòng khác hay không nhận được việc
# không bao giờ vào danh sách, nên không bao giờ được gợi ý.
#
# ĐIỂM, từ nhật ký và hồ sơ, không mã trạng thái nào trong tệp:
#
#   đang giữ    — số hồ sơ giao cho người đó đang ở trạng thái của hàng đợi phòng ban (suy từ bộ quy
#                 tắc như buồng lái phòng ban, `trang_thai_hang_doi_phong_ban`)
#   kinh nghiệm — số hồ sơ CÙNG LOẠI người đó đã làm xong: đã đi một cạnh khai `primary_scope` là
#                 người được giao (bước chính của người xử lý, #227 — "Hoàn thành xử lý" ở bộ quy tắc
#                 mẫu), trong `assignee_suggest_history_days` ngày gần nhất
#
#   điểm = w_kn × ln(1 + kinh nghiệm) − w_tải × đang giữ       (trọng số trong `app/config.py`)
#
# Logarit vì hồ sơ thứ hai mươi cùng loại không dạy thêm bằng hồ sơ thứ hai. Hòa điểm thì ít việc hơn,
# rồi nhiều kinh nghiệm hơn, rồi tên — cùng dữ liệu luôn cùng gợi ý.
#
# HAI LÚC TÍNH, cùng một đường ghi (`cap_nhat_goi_y`):
#
#   - Hồ sơ VỀ PHÒNG — vào trạng thái mà từ đó có cạnh cho đặt `assignee_id` (Chờ phòng ban xác duyệt,
#     Leo thang ở bộ quy tắc mẫu): tác vụ nền sau khi phản hồi chuyển trạng thái đã về trình duyệt.
#   - Trưởng phòng MỞ ô chọn người: điểm cuối danh sách người nhận việc đã gọi danh bạ, tính lại ngay
#     ở đó; tải việc đổi từ lúc về phòng thì gợi ý đổi theo.
#
# Ghi `suggested_assignee_id` và `assignee_suggestion` bằng một câu UPDATE riêng, giữ `updated_at` —
# không qua cửa chuyển trạng thái, không chạm `assignee_id` (CLAUDE.md mục 4.3). Danh bạ không trả
# lời thì không gợi ý gì và không xóa gợi ý cũ; ô chọn tay vẫn dùng được như trước.

from __future__ import annotations

import datetime as dt
import logging
import math
from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from app.auth.directory import DirectoryUnavailable, KeycloakDirectory, Person, get_directory
from app.config import get_settings
from app.models.case import EventLog, Request
from app.models.workflow_config import Transition
from app.workflow.assignment import _canh_giao_viec, nguoi_nhan_viec, trang_thai_hang_doi_phong_ban
from app.workflow.engine import ma_quy_trinh_ung_dung, rule_sets_in_use

log = logging.getLogger(__name__)

# Giá trị `transitions.primary_scope` của bước chính do người được giao đi — từ vựng của lược đồ
# (#227, cùng chữ engine dùng), không phải mã trạng thái hay hoạt động
PHAM_VI_NGUOI_DUOC_GIAO = "assignee"


@dataclass(frozen=True)
class UngVien:
    nguoi: Person
    dang_giu: int
    kinh_nghiem: int
    diem: float


def trang_thai_giao_viec(session: Session, rule_set_id: int) -> set[str]:
    """Trạng thái mà từ đó có cạnh cho đặt người xử lý — hồ sơ ở đây là đang chờ giao việc."""
    return {t.from_state for t in _canh_giao_viec(session, rule_set_id)}


def _dang_giu(session: Session, ma_nguoi: list[str]) -> dict[str, int]:
    dieu_kien = [
        and_(
            Request.rule_set_id == bo,
            Request.current_state.in_([t.code for t in trang_thai_hang_doi_phong_ban(session, bo)]),
        )
        for bo in rule_sets_in_use(session, ma_quy_trinh_ung_dung(session))
    ]
    if not ma_nguoi or not dieu_kien:
        return {}
    return dict(
        session.execute(
            select(Request.assignee_id, func.count())
            .where(Request.assignee_id.in_(ma_nguoi), or_(*dieu_kien))
            .group_by(Request.assignee_id)
        ).all()
    )


def _kinh_nghiem(session: Session, ma_nguoi: list[str], ma_loai: str | None) -> dict[str, int]:
    if not ma_nguoi or not ma_loai:
        return {}
    tu_ngay = dt.datetime.now(dt.UTC) - dt.timedelta(days=get_settings().assignee_suggest_history_days)
    return dict(
        session.execute(
            select(EventLog.actor, func.count(func.distinct(EventLog.case_id)))
            .join(Request, Request.id == EventLog.case_id)
            .join(
                Transition,
                and_(
                    Transition.rule_set_id == Request.rule_set_id,
                    Transition.from_state == EventLog.from_state,
                    Transition.to_state == EventLog.to_state,
                    Transition.activity_code == EventLog.activity,
                    Transition.is_system.is_(False),
                ),
            )
            .where(
                Transition.primary_scope == PHAM_VI_NGUOI_DUOC_GIAO,
                EventLog.actor.in_(ma_nguoi),
                Request.request_type_code == ma_loai,
                EventLog.timestamp >= tu_ngay,
            )
            .group_by(EventLog.actor)
        ).all()
    )


def xep_hang(session: Session, ho_so: Request, ung_vien: list[Person]) -> list[UngVien]:
    """Ứng viên kèm số liệu và điểm, tốt nhất trước. Hàm thuần trên dữ liệu đã có — không gọi danh bạ."""
    cau_hinh = get_settings()
    ma = [p.id for p in ung_vien]
    giu = _dang_giu(session, ma)
    kn = _kinh_nghiem(session, ma, ho_so.request_type_code)
    ds = [
        UngVien(
            nguoi=p,
            dang_giu=giu.get(p.id, 0),
            kinh_nghiem=kn.get(p.id, 0),
            diem=cau_hinh.assignee_suggest_experience_weight * math.log1p(kn.get(p.id, 0))
            - cau_hinh.assignee_suggest_load_weight * giu.get(p.id, 0),
        )
        for p in ung_vien
    ]
    ds.sort(key=lambda u: (-u.diem, u.dang_giu, -u.kinh_nghiem, u.nguoi.name, u.nguoi.id))
    return ds


def ly_do(u: UngVien) -> str:
    giu = f"đang giữ {u.dang_giu} việc" if u.dang_giu else "chưa giữ việc nào"
    kn = (
        f"đã xử lý {u.kinh_nghiem} hồ sơ cùng loại"
        if u.kinh_nghiem
        else "chưa xử lý hồ sơ cùng loại nào"
    )
    return f"{giu[0].upper()}{giu[1:]}, {kn}."


def ghi_chu(u: UngVien) -> dict:
    return {
        "id": u.nguoi.id,
        "label": u.nguoi.name,
        "reason": ly_do(u),
        "load": u.dang_giu,
        "experience": u.kinh_nghiem,
        "score": round(u.diem, 4),
        "at": dt.datetime.now(dt.UTC).isoformat(),
    }


def cap_nhat_goi_y(session: Session, ho_so: Request, ung_vien: list[Person]) -> dict | None:
    """Tính gợi ý cho hồ sơ từ danh sách ứng viên đã tra, ghi nếu khác gợi ý đang lưu. Trả ghi chú
    của gợi ý (hay `None` khi không có ứng viên nào). Không commit — phía gọi quyết định giao dịch.

    Chỉ ghi khi người hay số liệu đổi: mở hồ sơ hai lần liền không sinh hai lần ghi.
    """
    if not get_settings().assignee_suggest_enabled:
        return None
    ds = xep_hang(session, ho_so, ung_vien)
    moi = ghi_chu(ds[0]) if ds else None
    cu = ho_so.assignee_suggestion if isinstance(ho_so.assignee_suggestion, dict) else None

    def cot_loi(g: dict | None) -> tuple | None:
        return None if g is None else (g.get("id"), g.get("label"), g.get("load"), g.get("experience"))

    if cot_loi(moi) == cot_loi(cu) and ho_so.suggested_assignee_id == (moi or {}).get("id"):
        return cu
    session.execute(
        update(Request)
        .where(Request.id == ho_so.id)
        .values(
            suggested_assignee_id=moi["id"] if moi else None,
            assignee_suggestion=moi,
            # Gợi ý không phải một lần đổi hồ sơ: biểu mẫu đang mở không bị dựng lại
            updated_at=Request.updated_at,
        )
        .execution_options(synchronize_session=False)
    )
    # Đặt giá trị như đã đọc từ cơ sở dữ liệu, không đánh dấu đối tượng là đã sửa: lần flush sau
    # không được phát thêm một UPDATE kèm `updated_at` mới
    set_committed_value(ho_so, "suggested_assignee_id", moi["id"] if moi else None)
    set_committed_value(ho_so, "assignee_suggestion", moi)
    return moi


def dang_cho_giao_viec(session: Session, ho_so: Request) -> bool:
    return bool(ho_so.department_code) and ho_so.current_state in trang_thai_giao_viec(
        session, ho_so.rule_set_id
    )


def goi_y_khi_ve_phong(
    session: Session, danh_ba: KeycloakDirectory, ma_ho_so: int
) -> dict | None:
    """Tính và ghi gợi ý cho một hồ sơ vừa về phòng. Danh bạ hỏng thì không làm gì."""
    ho_so = session.get(Request, ma_ho_so)
    if ho_so is None or not dang_cho_giao_viec(session, ho_so):
        return None
    try:
        ung_vien = nguoi_nhan_viec(session, danh_ba, ho_so.rule_set_id, ho_so.department_code)
    except DirectoryUnavailable as loi:
        log.warning("Không gợi ý người xử lý cho hồ sơ %s: %s", ma_ho_so, loi.message)
        return None
    ket_qua = cap_nhat_goi_y(session, ho_so, ung_vien)
    session.commit()
    return ket_qua


def hen_goi_y_neu_ve_phong(tac_vu_nen, session: Session, ho_so: Request) -> None:
    """Gọi ở điểm cuối chuyển trạng thái, sau commit: hồ sơ vừa vào trạng thái chờ giao việc thì hẹn
    tác vụ nền tính gợi ý. Chỉ đọc bộ quy tắc — không gọi danh bạ trên đường của người bấm."""
    if get_settings().assignee_suggest_enabled and dang_cho_giao_viec(session, ho_so):
        tac_vu_nen.add_task(goi_y_sau_khi_chuyen, ho_so.id)


def goi_y_sau_khi_chuyen(ma_ho_so: int) -> None:
    """Tác vụ nền của các điểm cuối chuyển trạng thái. Không bao giờ làm hỏng gì của người dùng."""
    if not get_settings().assignee_suggest_enabled:
        return
    from app.db import SessionLocal

    try:
        with SessionLocal() as phien:
            goi_y_khi_ve_phong(phien, get_directory(), ma_ho_so)
    except Exception:  # noqa: BLE001 — tác vụ nền: lần mở hồ sơ sau sẽ tính lại
        log.exception("Tác vụ gợi ý người xử lý cho hồ sơ %s thất bại", ma_ho_so)
