# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử đồng hồ SLA và cơ chế tự leo thang.
#
# Không bài nào ngồi chờ thật. Thời gian trôi được mô phỏng bằng cách đẩy mốc đoạn
# đang tính về quá khứ — nhờ vậy phép tính thật vẫn được kiểm, khác với việc gán
# thẳng số giây đã chạy.

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import select

from app.models.workflow_config import Priority, RequestType, State
from app.rules.sla import bay_gio, da_chay_giay, gioi_han_giay, ho_so_qua_han
from app.workflow.context import Actor
from app.workflow.engine import case_history, create_case, perform_transition
from app.workflow.escalation import TAC_NHAN_SLA, quet_va_leo_thang

NGUOI_TAO = "nguoi-tao-sla"


# ---------------------------------------------------------------------------
# Tiện ích
# ---------------------------------------------------------------------------


def _loai_yeu_cau(session) -> RequestType:
    return session.scalars(
        select(RequestType).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()


def _den_dang_xu_ly(session, phong_ban: str, loai: RequestType):
    """Đưa hồ sơ tới `in-progress` — nơi đồng hồ bắt đầu chạy."""
    ho_so = create_case(
        session, title="Hồ sơ thử SLA", requester_id=NGUOI_TAO
    )
    pl = Actor(id="pl-sla", roles=frozenset({"classifier"}))
    xd = Actor(
        id="xd-sla", roles=frozenset({"approver"}), departments=frozenset({phong_ban})
    )
    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()

    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=pl,
        changes={"priority_code": uu_tien, "request_type_code": loai.code},
    )
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="awaiting-acceptance",
        actor=pl,
        changes={"department_code": phong_ban},
    )
    perform_transition(
        session, case_id=ho_so.id, to_state="in-progress", actor=xd
    )
    return ho_so


def _lui_dong_ho(session, ho_so, gio: float) -> None:
    """Đẩy mốc đoạn đang tính về quá khứ, như thể đã trôi qua chừng ấy giờ."""
    ho_so.sla_segment_since = bay_gio(session) - dt.timedelta(hours=gio)
    session.flush()


# ---------------------------------------------------------------------------
# Đồng hồ khởi động và dừng đúng chỗ
# ---------------------------------------------------------------------------


def test_cot_sla_running_tra_tu_bang_khong_ma_cung(session, rule_set):
    """Trạng thái nào chạy đồng hồ là dữ liệu, và dữ liệu phải nhất quán."""
    dang_chay = set(
        session.scalars(
            select(State.code).where(
                State.rule_set_id == rule_set.id, State.sla_running
            )
        ).all()
    )

    assert dang_chay, "Phải có ít nhất một trạng thái chạy đồng hồ"

    ket_thuc = set(
        session.scalars(
            select(State.code).where(
                State.rule_set_id == rule_set.id, State.is_terminal
            )
        ).all()
    )
    assert not (dang_chay & ket_thuc), "Trạng thái đóng không được chạy đồng hồ"


def test_dong_ho_chua_chay_truoc_khi_vao_xu_ly(session, rule_set):
    """Quãng chờ phân loại không tính vào SLA của người xử lý."""
    ho_so = create_case(
        session,
        title="Chưa phân loại",
        requester_id=NGUOI_TAO,
        request_type_code=_loai_yeu_cau(session).code,
    )
    assert ho_so.sla_segment_since is None
    assert ho_so.sla_running_seconds == 0

    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=Actor(id="pl-sla", roles=frozenset({"classifier"})),
        changes={"priority_code": uu_tien},
    )

    assert ho_so.sla_segment_since is None
    assert ho_so.sla_running_seconds == 0


def test_dong_ho_khoi_dong_khi_vao_xu_ly(session, rule_set, phong_ban):
    ho_so = _den_dang_xu_ly(session, phong_ban, _loai_yeu_cau(session))

    assert ho_so.sla_segment_since is not None
    assert ho_so.sla_running_seconds == 0
    assert ho_so.sla_paused_seconds == 0


def test_cho_bo_sung_thong_tin_lam_dung_dong_ho(session, rule_set, phong_ban):
    """Quyết định nghiệp vụ: thời gian chờ người tạo trả lời KHÔNG tính vào SLA.

    Người xử lý không nên bị phạt vì người tạo chậm. Nhưng tổng thời gian dừng vẫn
    được cộng dồn, để khai phá quy trình phát hiện ai lạm dụng cách này.
    """
    xl = Actor(
        id="xl-sla", roles=frozenset({"handler"}), departments=frozenset({phong_ban})
    )
    ho_so = _den_dang_xu_ly(session, phong_ban, _loai_yeu_cau(session))

    _lui_dong_ho(session, ho_so, gio=2)
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="awaiting-info",
        actor=xl,
        note="Cho xin mã tài sản của máy in.",
    )

    # Hai giờ vừa qua là thời gian chạy
    assert 7100 < ho_so.sla_running_seconds < 7300
    assert ho_so.sla_paused_seconds == 0

    # Ba giờ tiếp theo là thời gian dừng
    _lui_dong_ho(session, ho_so, gio=3)
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="in-progress",
        actor=Actor(id=NGUOI_TAO, roles=frozenset({"requester"})),
    )

    assert 7100 < ho_so.sla_running_seconds < 7300, "Đồng hồ không được chạy khi dừng"
    assert 10700 < ho_so.sla_paused_seconds < 10900, "Thời gian dừng phải được ghi lại"


def test_ho_so_dong_thi_dong_ho_dung_han(session, rule_set, phong_ban):
    xl = Actor(
        id="xl-sla", roles=frozenset({"handler"}), departments=frozenset({phong_ban})
    )
    ho_so = _den_dang_xu_ly(session, phong_ban, _loai_yeu_cau(session))

    # Khẳng định đồng hồ ĐANG chạy trước đã. Thiếu dòng này thì bài kiểm thử đậu cả
    # khi phần kế toán bị gỡ bỏ, vì lúc đó mốc đoạn vốn chưa bao giờ được đặt.
    assert ho_so.sla_segment_since is not None

    _lui_dong_ho(session, ho_so, gio=1)
    perform_transition(session, case_id=ho_so.id, to_state="completed", actor=xl)
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="closed",
        actor=Actor(id=NGUOI_TAO, roles=frozenset({"requester"})),
    )

    assert ho_so.sla_segment_since is None
    assert 3500 < ho_so.sla_running_seconds < 3700


# ---------------------------------------------------------------------------
# Tự leo thang
# ---------------------------------------------------------------------------


def test_ho_so_qua_han_tu_leo_thang(session, rule_set, phong_ban):
    loai = _loai_yeu_cau(session)
    ho_so = _den_dang_xu_ly(session, phong_ban, loai)

    _lui_dong_ho(session, ho_so, gio=loai.sla_hours + 1)

    assert ho_so in ho_so_qua_han(session)

    da_leo_thang = quet_va_leo_thang(session)

    assert ho_so.id in da_leo_thang
    assert ho_so.current_state == "escalated"


def test_leo_thang_sinh_nhat_ky_voi_tac_nhan_he_thong(session, rule_set, phong_ban):
    """Leo thang đi qua điểm chuyển trạng thái duy nhất, không đi tắt."""
    loai = _loai_yeu_cau(session)
    ho_so = _den_dang_xu_ly(session, phong_ban, loai)
    truoc = len(case_history(session, ho_so.id))

    _lui_dong_ho(session, ho_so, gio=loai.sla_hours + 1)
    quet_va_leo_thang(session)

    nhat_ky = case_history(session, ho_so.id)
    assert len(nhat_ky) == truoc + 1

    cuoi = nhat_ky[-1]
    assert cuoi.actor == TAC_NHAN_SLA
    assert cuoi.from_state == "in-progress"
    assert cuoi.to_state == "escalated"
    assert cuoi.activity == "escalate"


def test_chua_qua_han_thi_khong_dong_toi(session, rule_set, phong_ban):
    loai = _loai_yeu_cau(session)
    ho_so = _den_dang_xu_ly(session, phong_ban, loai)

    _lui_dong_ho(session, ho_so, gio=loai.sla_hours - 1)

    assert ho_so not in ho_so_qua_han(session)
    assert quet_va_leo_thang(session) == []
    assert ho_so.current_state == "in-progress"


def test_da_leo_thang_roi_thi_khong_nhat_lai(session, rule_set, phong_ban):
    """Từ `escalated` không có cạnh hệ thống nào nữa, nên bộ quét tự bỏ qua.

    Cơ chế tự giới hạn bằng dữ liệu, không cần cột "đã leo thang chưa".
    """
    loai = _loai_yeu_cau(session)
    ho_so = _den_dang_xu_ly(session, phong_ban, loai)

    _lui_dong_ho(session, ho_so, gio=loai.sla_hours + 1)
    quet_va_leo_thang(session)
    assert ho_so.current_state == "escalated"

    _lui_dong_ho(session, ho_so, gio=loai.sla_hours * 5)
    assert ho_so not in ho_so_qua_han(session)
    assert quet_va_leo_thang(session) == []


def test_ho_so_dang_dung_dong_ho_khong_qua_han_duoc(session, rule_set, phong_ban):
    """Hồ sơ đang chờ người tạo trả lời thì không bị leo thang, dù chờ bao lâu."""
    loai = _loai_yeu_cau(session)
    ho_so = _den_dang_xu_ly(session, phong_ban, loai)

    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="awaiting-info",
        actor=Actor(
            id="xl-sla",
            roles=frozenset({"handler"}),
            departments=frozenset({phong_ban}),
        ),
        note="Cho xin thêm thông tin.",
    )
    _lui_dong_ho(session, ho_so, gio=loai.sla_hours * 10)

    assert ho_so not in ho_so_qua_han(session)
    assert quet_va_leo_thang(session) == []


def test_chua_phan_loai_thi_khong_co_nguong(session, rule_set):
    ho_so = create_case(session, title="Chưa phân loại", requester_id=NGUOI_TAO)
    assert gioi_han_giay(session, ho_so) is None


def test_doi_nguong_sla_chi_can_sua_du_lieu(session, rule_set, phong_ban):
    """Định nghĩa hoàn thành của issue: đổi ngưỡng không phải sửa mã.

    Bài này hạ ngưỡng xuống một giờ ngay trong giao dịch kiểm thử, rồi xác nhận một
    hồ sơ mới chạy được hai giờ lập tức thành quá hạn.
    """
    loai = _loai_yeu_cau(session)
    ho_so = _den_dang_xu_ly(session, phong_ban, loai)

    _lui_dong_ho(session, ho_so, gio=2)
    assert ho_so not in ho_so_qua_han(session), "Ngưỡng gốc chưa bị vượt"

    loai.sla_hours = 1
    session.flush()

    assert ho_so in ho_so_qua_han(session), "Hạ ngưỡng trong dữ liệu là đủ"
    assert gioi_han_giay(session, ho_so) == 3600


def test_da_chay_giay_gom_ca_doan_dang_mo(session, rule_set, phong_ban):
    ho_so = _den_dang_xu_ly(session, phong_ban, _loai_yeu_cau(session))
    _lui_dong_ho(session, ho_so, gio=1.5)

    assert 5300 < da_chay_giay(session, ho_so) < 5500
