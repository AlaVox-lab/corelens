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
from sqlalchemy.exc import IntegrityError

from app.models.workflow_config import Priority, RequestType, State
from app.rules.sla import (
    an_han_con_lai_giay,
    bay_gio,
    da_chay_giay,
    gioi_han_giay,
    ho_so_qua_han,
)
from app.workflow.context import Actor
from app.workflow.engine import case_history, create_case, perform_transition
from app.workflow.escalation import TAC_NHAN_SLA, quet_va_leo_thang

NGUOI_TAO = "nguoi-tao-sla"

# Các bài ở đây lùi đồng hồ theo giờ lịch; lịch cả ngày cả tuần giữ đáp án không đổi theo
# lúc chạy. Lịch làm việc thật kiểm ở test_lich_lam_viec.py (#199).
pytestmark = pytest.mark.usefixtures("lich_ca_ngay")


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
        note="Mã tài sản MI-0342.",
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


def test_ho_so_qua_han_tu_leo_thang(session, loc_cua_bai, rule_set, phong_ban):
    loai = _loai_yeu_cau(session)
    ho_so = _den_dang_xu_ly(session, phong_ban, loai)

    _lui_dong_ho(session, ho_so, gio=loai.sla_hours + 1)

    assert ho_so in ho_so_qua_han(session)

    da_leo_thang = loc_cua_bai(quet_va_leo_thang(session))

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


def test_chua_qua_han_thi_khong_dong_toi(session, loc_cua_bai, rule_set, phong_ban):
    loai = _loai_yeu_cau(session)
    ho_so = _den_dang_xu_ly(session, phong_ban, loai)

    _lui_dong_ho(session, ho_so, gio=loai.sla_hours - 1)

    assert ho_so not in ho_so_qua_han(session)
    assert loc_cua_bai(quet_va_leo_thang(session)) == []
    assert ho_so.current_state == "in-progress"


def test_da_leo_thang_roi_thi_khong_nhat_lai(session, loc_cua_bai, rule_set, phong_ban):
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
    assert loc_cua_bai(quet_va_leo_thang(session)) == []


def test_ho_so_dang_dung_dong_ho_khong_qua_han_duoc(session, loc_cua_bai, rule_set, phong_ban):
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
    assert loc_cua_bai(quet_va_leo_thang(session)) == []


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

    # Ân hạn không được dài hơn hạn xử lý (ràng buộc CHECK, #94), nên hạ cả hai
    loai.sla_grace_hours = 0
    loai.sla_hours = 1
    session.flush()

    assert ho_so in ho_so_qua_han(session), "Hạ ngưỡng trong dữ liệu là đủ"
    assert gioi_han_giay(session, ho_so) == 3600


def test_da_chay_giay_gom_ca_doan_dang_mo(session, rule_set, phong_ban):
    ho_so = _den_dang_xu_ly(session, phong_ban, _loai_yeu_cau(session))
    _lui_dong_ho(session, ho_so, gio=1.5)

    assert 5300 < da_chay_giay(session, ho_so) < 5500


# ---------------------------------------------------------------------------
# Ân hạn sau khi vào lại trạng thái đếm giờ (#94)
# ---------------------------------------------------------------------------


def _truong_phong(phong_ban: str) -> Actor:
    return Actor(id="xd-sla", roles=frozenset({"approver"}), departments=frozenset({phong_ban}))


def _loai_co_an_han(session) -> RequestType:
    loai = _loai_yeu_cau(session)
    if loai.sla_grace_hours <= 0:
        pytest.skip("Loại yêu cầu đầu tiên không khai ân hạn.")
    return loai


def _da_leo_thang_vi_qua_han(session, phong_ban: str, loai: RequestType):
    ho_so = _den_dang_xu_ly(session, phong_ban, loai)
    _lui_dong_ho(session, ho_so, gio=loai.sla_hours + 1)
    quet_va_leo_thang(session)
    assert ho_so.current_state == "escalated"
    return ho_so


def test_phan_cong_lai_thi_co_an_han(session, loc_cua_bai, rule_set, phong_ban):
    """Đúng lỗi của #94: phân công lại xong, lượt quét kế tiếp KHÔNG leo thang lại."""
    loai = _loai_co_an_han(session)
    ho_so = _da_leo_thang_vi_qua_han(session, phong_ban, loai)

    perform_transition(session, case_id=ho_so.id, to_state="in-progress",
                       actor=_truong_phong(phong_ban))

    assert da_chay_giay(session, ho_so) > gioi_han_giay(session, ho_so),         "đồng hồ tổng không đặt lại — hồ sơ vẫn quá hạn"
    assert ho_so not in ho_so_qua_han(session)
    assert loc_cua_bai(quet_va_leo_thang(session)) == []
    assert ho_so.current_state == "in-progress"

    con = an_han_con_lai_giay(session, ho_so)
    assert con is not None and 0 < con <= loai.sla_grace_hours * 3600

    # Nửa khoảng ân hạn trôi qua vẫn phải yên — bắt lỗi nhầm đơn vị giờ với phút
    _lui_dong_ho(session, ho_so, gio=loai.sla_grace_hours / 2)
    assert loc_cua_bai(quet_va_leo_thang(session)) == []
    assert ho_so.current_state == "in-progress"


def test_chua_qua_han_thi_khong_noi_ve_an_han(session, rule_set, phong_ban):
    """Ân hạn chỉ có nghĩa với hồ sơ đã quá hạn. Hồ sơ vừa được nhận việc mà hiện
    "ân hạn còn 2 giờ" thì người đọc tưởng hạn xử lý chỉ còn 2 giờ."""
    loai = _loai_co_an_han(session)
    ho_so = _den_dang_xu_ly(session, phong_ban, loai)
    assert an_han_con_lai_giay(session, ho_so) is None


def test_het_an_han_thi_leo_thang_lai(session, loc_cua_bai, rule_set, phong_ban):
    """Ân hạn không che việc bị bỏ bê lần hai: hết ân hạn mà chưa xong thì leo thang."""
    loai = _loai_co_an_han(session)
    ho_so = _da_leo_thang_vi_qua_han(session, phong_ban, loai)
    perform_transition(session, case_id=ho_so.id, to_state="in-progress",
                       actor=_truong_phong(phong_ban))

    _lui_dong_ho(session, ho_so, gio=loai.sla_grace_hours + 0.1)

    assert an_han_con_lai_giay(session, ho_so) is None
    assert ho_so.id in loc_cua_bai(quet_va_leo_thang(session))
    assert ho_so.current_state == "escalated"


def test_mo_lai_ho_so_da_qua_han_duoc_cap_han_moi(session, loc_cua_bai, rule_set, phong_ban):
    """Lối vào thứ hai: người gửi mở lại một hồ sơ đã quá hạn. Từ #102 (giảng viên chốt 08/10,
    thay quyết định 23/09 "không cấp hạn mới") mở lại là chu kỳ xử lý mới: đồng hồ đếm lại từ
    0, nên hồ sơ không còn quá hạn và không cần ân hạn để cứu."""
    loai = _loai_co_an_han(session)
    ho_so = _den_dang_xu_ly(session, phong_ban, loai)
    _lui_dong_ho(session, ho_so, gio=loai.sla_hours + 1)

    xu_ly = Actor(id="xl-sla", roles=frozenset({"handler"}), departments=frozenset({phong_ban}))
    perform_transition(session, case_id=ho_so.id, to_state="completed", actor=xu_ly)
    nguoi_gui = Actor(id=NGUOI_TAO, roles=frozenset({"requester"}))
    perform_transition(session, case_id=ho_so.id, to_state="in-progress",
                       actor=nguoi_gui, note="Vẫn chưa được.")

    assert ho_so not in ho_so_qua_han(session)
    assert loc_cua_bai(quet_va_leo_thang(session)) == []
    # Hạn mới, không kế thừa hạn đã hết của chu kỳ cũ — ân hạn không phải dùng tới
    assert ho_so.sla_running_seconds == 0
    assert an_han_con_lai_giay(session, ho_so) is None


def test_an_han_bang_khong_thi_leo_thang_ngay(session, loc_cua_bai, rule_set, phong_ban):
    """Ân hạn là dữ liệu: đặt về 0 thì hành vi cũ trở lại, không sửa mã."""
    loai = _loai_co_an_han(session)
    ho_so = _da_leo_thang_vi_qua_han(session, phong_ban, loai)

    loai.sla_grace_hours = 0
    session.flush()
    perform_transition(session, case_id=ho_so.id, to_state="in-progress",
                       actor=_truong_phong(phong_ban))

    assert ho_so.id in loc_cua_bai(quet_va_leo_thang(session))


def test_an_han_khong_duoc_dai_hon_han_xu_ly(session, rule_set):
    """Ân hạn dài hơn hạn thì lần leo thang ĐẦU TIÊN cũng bị hoãn — lược đồ chặn."""
    loai = _loai_yeu_cau(session)
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            loai.sla_grace_hours = loai.sla_hours + 1
            session.flush()
    session.expire_all()


# ---------------------------------------------------------------------------
# Ngưỡng "sắp hết hạn" trong dữ liệu (#175)
# ---------------------------------------------------------------------------


def test_nguong_sap_het_han_nam_trong_du_lieu(session, rule_set):
    """Mẫu 75% cho mọi loại yêu cầu (navigator chốt 15/10)."""
    cac = session.scalars(select(RequestType).where(RequestType.is_active)).all()
    assert cac and {loai.sla_warn_percent for loai in cac} == {75}


@pytest.mark.parametrize(
    ("phan", "sap"),
    [
        # Sự cố thiết bị: 8 giờ, ngưỡng 75% = 6 giờ
        (5.9 / 8, False),
        (6 / 8, True),
        (1.0, True),  # đúng mốc hạn vẫn là sắp hạn — quá hạn là vượt hẳn
        (8.02 / 8, False),
    ],
)
def test_ranh_gioi_sap_het_han(session, rule_set, phong_ban, phan, sap):
    from app.rules.sla import sap_het_han

    loai = _loai_yeu_cau(session)
    assert loai.sla_hours == 8 and loai.sla_warn_percent == 75
    ho_so = _den_dang_xu_ly(session, phong_ban, loai)
    _lui_dong_ho(session, ho_so, gio=loai.sla_hours * phan)
    assert sap_het_han(session, ho_so) is sap


def test_doi_nguong_sap_het_han_chi_can_sua_du_lieu(session, rule_set, phong_ban):
    """Định nghĩa hoàn thành của #175: đổi ngưỡng trong dữ liệu đổi hồ sơ nào sắp hạn."""
    from app.rules.sla import sap_het_han

    loai = _loai_yeu_cau(session)
    ho_so = _den_dang_xu_ly(session, phong_ban, loai)
    _lui_dong_ho(session, ho_so, gio=4)
    assert not sap_het_han(session, ho_so)

    loai.sla_warn_percent = 50
    session.flush()
    assert sap_het_han(session, ho_so)


def test_chua_phan_loai_thi_khong_sap_het_han(session, rule_set):
    from app.rules.sla import sap_het_han

    ho_so = create_case(session, title="Chưa phân loại", requester_id=NGUOI_TAO)
    assert not sap_het_han(session, ho_so)


@pytest.mark.parametrize("phan_tram", [0, 100])
def test_nguong_sap_het_han_phai_nam_giua_0_va_100(session, rule_set, phan_tram):
    loai = _loai_yeu_cau(session)
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            loai.sla_warn_percent = phan_tram
            session.flush()
    session.expire_all()


def test_tom_tat_ho_so_tra_co_sap_het_han(session, rule_set, phong_ban):
    from app.workflow.routes import _tom_tat

    states = {s.code: s for s in session.scalars(select(State)).all()}
    ho_so = _den_dang_xu_ly(session, phong_ban, _loai_yeu_cau(session))
    assert _tom_tat(session, ho_so, states)["sla_due_soon"] is False

    _lui_dong_ho(session, ho_so, gio=7)
    tom_tat = _tom_tat(session, ho_so, states)
    assert tom_tat["sla_due_soon"] is True and tom_tat["sla_overdue"] is False

    _lui_dong_ho(session, ho_so, gio=9)
    tom_tat = _tom_tat(session, ho_so, states)
    assert tom_tat["sla_due_soon"] is False and tom_tat["sla_overdue"] is True
