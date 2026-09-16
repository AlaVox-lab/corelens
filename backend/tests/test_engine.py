# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử điểm chuyển trạng thái duy nhất.
#
# Hai nhóm bài, và nhóm thứ hai mới là nhóm quan trọng:
#
#   Đường hợp lệ — một hồ sơ đi trọn vòng, nhật ký sinh đủ và đúng thứ tự
#   Đường bị chặn — mọi lối tắt đều đóng
#
# Nhóm thứ hai quan trọng hơn vì đề tài đặt cược vào chất lượng nhật ký sự kiện. Một
# lối tắt lọt qua nghĩa là nhật ký thủng, và kết quả khai phá quy trình mất cơ sở.

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import func, select, text

from app.models.case import EventLog
from app.models.workflow_config import Priority, State
from app.workflow.context import Actor
from app.workflow.engine import (
    allowed_transitions,
    case_history,
    create_case,
    perform_transition,
)
from app.workflow.errors import (
    GuardViolation,
    NoteRequired,
    RoleNotPermitted,
    SystemTransitionOnly,
    TransitionNotAllowed,
)

NGUOI_TAO = "nguoi-tao-001"
NGUOI_KHAC = "nguoi-tao-002"


# ---------------------------------------------------------------------------
# Tiện ích dựng dữ liệu
# ---------------------------------------------------------------------------


def _muc_uu_tien(session) -> str:
    return session.scalars(
        select(Priority.code).where(Priority.is_default)
    ).one()


def _tao_ho_so(session):
    return create_case(
        session,
        title="Máy in phòng kế toán không nhận lệnh",
        description="Đã thử khởi động lại nhưng không được.",
        requester_id=NGUOI_TAO,
    )


def _den_dang_xu_ly(session, phong_ban: str):
    """Đưa một hồ sơ mới tới trạng thái đang xử lý, qua đúng ba cạnh hợp lệ."""
    ho_so = _tao_ho_so(session)
    nguoi_phan_loai = Actor(id="pl-01", roles=frozenset({"classifier"}))
    nguoi_duyet = Actor(
        id="xd-01",
        roles=frozenset({"approver"}),
        departments=frozenset({phong_ban}),
    )

    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=nguoi_phan_loai,
        changes={"priority_code": _muc_uu_tien(session)},
    )
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="awaiting-acceptance",
        actor=nguoi_phan_loai,
        changes={"department_code": phong_ban},
    )
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="in-progress",
        actor=nguoi_duyet,
    )
    return ho_so


# ---------------------------------------------------------------------------
# Đường hợp lệ
# ---------------------------------------------------------------------------


def test_trang_thai_bat_dau_tra_tu_bang_khong_ma_cung(session, rule_set):
    """Hồ sơ mới nhận trạng thái mang cờ is_initial, không phải chuỗi viết cứng."""
    ho_so = _tao_ho_so(session)

    trang_thai_dau = session.scalars(
        select(State).where(State.rule_set_id == rule_set.id, State.is_initial)
    ).one()

    assert ho_so.current_state == trang_thai_dau.code
    assert ho_so.rule_set_id == rule_set.id


def test_tao_ho_so_khong_sinh_ban_ghi_nhat_ky(session, rule_set):
    """Tạo hồ sơ không phải một lần CHUYỂN trạng thái nên không có sự kiện nào."""
    ho_so = _tao_ho_so(session)
    assert case_history(session, ho_so.id) == []


def test_ho_so_di_tron_vong_va_nhat_ky_dung_thu_tu(session, rule_set, phong_ban):
    """Một hồ sơ đi hết vòng đời, nhật ký sinh đủ năm bản ghi nối liền nhau."""
    ho_so = _den_dang_xu_ly(session, phong_ban)

    nguoi_xu_ly = Actor(
        id="xl-01",
        roles=frozenset({"handler"}),
        departments=frozenset({phong_ban}),
    )
    nguoi_tao = Actor(id=NGUOI_TAO, roles=frozenset({"requester"}))

    perform_transition(
        session, case_id=ho_so.id, to_state="completed", actor=nguoi_xu_ly
    )
    perform_transition(
        session, case_id=ho_so.id, to_state="closed", actor=nguoi_tao
    )

    assert ho_so.current_state == "closed"

    nhat_ky = case_history(session, ho_so.id)
    assert len(nhat_ky) == 5

    duong_di = [(e.from_state, e.to_state) for e in nhat_ky]
    assert duong_di == [
        ("submitted", "classified"),
        ("classified", "awaiting-acceptance"),
        ("awaiting-acceptance", "in-progress"),
        ("in-progress", "completed"),
        ("completed", "closed"),
    ]

    # Nhật ký phải nối liền: trạng thái đích của bản ghi trước là trạng thái nguồn
    # của bản ghi sau. Đứt đoạn nghĩa là có lần chuyển nào đó không đi qua engine.
    for truoc, sau in zip(nhat_ky, nhat_ky[1:]):
        assert truoc.to_state == sau.from_state

    assert [e.actor for e in nhat_ky] == ["pl-01", "pl-01", "xd-01", "xl-01", NGUOI_TAO]


def test_moi_lan_chuyen_sinh_dung_mot_ban_ghi(session, rule_set, phong_ban):
    ho_so = _tao_ho_so(session)
    nguoi_phan_loai = Actor(id="pl-01", roles=frozenset({"classifier"}))

    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=nguoi_phan_loai,
        changes={"priority_code": _muc_uu_tien(session)},
    )

    assert len(case_history(session, ho_so.id)) == 1


def test_hoat_dong_trong_nhat_ky_lay_tu_bang_quy_tac(session, rule_set, phong_ban):
    """Trường `activity` phải khớp `activity_code` của cạnh, không do phía gọi tự đặt."""
    ho_so = _den_dang_xu_ly(session, phong_ban)
    nhat_ky = case_history(session, ho_so.id)

    assert [e.activity for e in nhat_ky] == [
        "classify",
        "route-to-department",
        "accept",
    ]


def test_moc_thoi_gian_co_mui_gio(session, rule_set):
    """Mốc thời gian phải mang múi giờ, để quy về UTC không mơ hồ.

    Kiểu cột là TIMESTAMPTZ nên PostgreSQL luôn lưu theo UTC. Bài này kiểm rằng giá
    trị đọc ra vẫn giữ thông tin múi giờ thay vì trở thành mốc trôi nổi.
    """
    ho_so = _tao_ho_so(session)
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=Actor(id="pl-01", roles=frozenset({"classifier"})),
        changes={"priority_code": _muc_uu_tien(session)},
    )

    su_kien = case_history(session, ho_so.id)[0]
    assert su_kien.timestamp.tzinfo is not None

    khoang_lech = abs(
        su_kien.timestamp.astimezone(dt.UTC) - dt.datetime.now(dt.UTC)
    )
    assert khoang_lech < dt.timedelta(minutes=5)


def test_liet_ke_canh_di_duoc_theo_vai_tro(session, rule_set):
    ho_so = _tao_ho_so(session)

    cua_nguoi_phan_loai = allowed_transitions(
        session, ho_so, Actor(id="pl-01", roles=frozenset({"classifier"}))
    )
    assert {c.to_state for c in cua_nguoi_phan_loai} == {"classified", "awaiting-info"}

    cua_nguoi_tao = allowed_transitions(
        session, ho_so, Actor(id=NGUOI_TAO, roles=frozenset({"requester"}))
    )
    assert {c.to_state for c in cua_nguoi_tao} == {"cancelled"}

    # Quản trị viên không đi cạnh nào — họ sửa cấu hình, không đẩy hồ sơ
    cua_quan_tri = allowed_transitions(
        session, ho_so, Actor(id="qt-01", roles=frozenset({"administrator"}))
    )
    assert cua_quan_tri == []


# ---------------------------------------------------------------------------
# Đường bị chặn
# ---------------------------------------------------------------------------


def test_canh_khong_co_trong_bang_thi_khong_di_duoc(session, rule_set):
    ho_so = _tao_ho_so(session)

    with pytest.raises(TransitionNotAllowed):
        perform_transition(
            session,
            case_id=ho_so.id,
            to_state="in-progress",
            actor=Actor(id="xl-01", roles=frozenset({"handler"})),
        )

    assert case_history(session, ho_so.id) == []


def test_da_nhan_thi_khong_tra_ve(session, rule_set, phong_ban):
    """Ràng buộc Poka-yoke quan trọng nhất: cánh cửa một chiều.

    Không phải "không nên đi" mà là "không có đường mà đi" — bảng `transitions` không
    có dòng nào từ `in-progress` ngược về phía trước.
    """
    ho_so = _den_dang_xu_ly(session, phong_ban)
    nguoi_duyet = Actor(
        id="xd-01",
        roles=frozenset({"approver"}),
        departments=frozenset({phong_ban}),
    )

    for lui_ve in ("awaiting-acceptance", "classified", "submitted"):
        with pytest.raises(TransitionNotAllowed):
            perform_transition(
                session, case_id=ho_so.id, to_state=lui_ve, actor=nguoi_duyet
            )

    assert ho_so.current_state == "in-progress"


def test_khong_huy_duoc_sau_khi_vao_xu_ly(session, rule_set, phong_ban):
    """Poka-yoke: chỉ hủy được TRƯỚC khi hồ sơ vào xử lý."""
    ho_so = _den_dang_xu_ly(session, phong_ban)

    with pytest.raises(TransitionNotAllowed):
        perform_transition(
            session,
            case_id=ho_so.id,
            to_state="cancelled",
            actor=Actor(id=NGUOI_TAO, roles=frozenset({"requester"})),
        )


def test_sai_vai_tro_bi_chan(session, rule_set):
    ho_so = _tao_ho_so(session)

    with pytest.raises(RoleNotPermitted):
        perform_transition(
            session,
            case_id=ho_so.id,
            to_state="classified",
            actor=Actor(id=NGUOI_TAO, roles=frozenset({"requester"})),
            changes={"priority_code": _muc_uu_tien(session)},
        )


def test_canh_he_thong_nguoi_khong_kich_hoat_duoc(session, rule_set, phong_ban):
    """Leo thang do quá hạn SLA là việc của hệ thống, không ai bấm tay được."""
    ho_so = _den_dang_xu_ly(session, phong_ban)

    with pytest.raises(SystemTransitionOnly):
        perform_transition(
            session,
            case_id=ho_so.id,
            to_state="escalated",
            actor=Actor(
                id="xd-01",
                roles=frozenset({"approver"}),
                departments=frozenset({phong_ban}),
            ),
        )

    # Còn hệ thống thì đi được
    perform_transition(
        session, case_id=ho_so.id, to_state="escalated", actor=Actor.system()
    )
    assert ho_so.current_state == "escalated"


def test_tac_nhan_he_thong_khong_di_canh_cua_nguoi(session, rule_set):
    ho_so = _tao_ho_so(session)

    with pytest.raises(RoleNotPermitted):
        perform_transition(
            session,
            case_id=ho_so.id,
            to_state="classified",
            actor=Actor.system(),
            changes={"priority_code": _muc_uu_tien(session)},
        )


def test_nguoi_tao_khong_tu_dat_muc_uu_tien(session, rule_set):
    """Ràng buộc `set-priority` gắn vào cạnh của người phân loại, không của người tạo.

    Người tạo yêu cầu không có cạnh nào mang ràng buộc này, nên không có đường nào
    để họ đặt mức ưu tiên.
    """
    ho_so = _tao_ho_so(session)

    with pytest.raises(GuardViolation) as loi:
        perform_transition(
            session,
            case_id=ho_so.id,
            to_state="classified",
            actor=Actor(id="pl-01", roles=frozenset({"classifier"})),
        )
    assert loi.value.guard_code == "set-priority"


def test_chuyen_ve_phong_ban_bat_buoc_chon_phong(session, rule_set):
    ho_so = _tao_ho_so(session)
    nguoi_phan_loai = Actor(id="pl-01", roles=frozenset({"classifier"}))

    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=nguoi_phan_loai,
        changes={"priority_code": _muc_uu_tien(session)},
    )

    with pytest.raises(GuardViolation) as loi:
        perform_transition(
            session,
            case_id=ho_so.id,
            to_state="awaiting-acceptance",
            actor=nguoi_phan_loai,
        )
    assert loi.value.guard_code == "select-department"


def test_nguoi_khac_khong_huy_duoc_ho_so_cua_ta(session, rule_set):
    ho_so = _tao_ho_so(session)

    with pytest.raises(GuardViolation) as loi:
        perform_transition(
            session,
            case_id=ho_so.id,
            to_state="cancelled",
            actor=Actor(id=NGUOI_KHAC, roles=frozenset({"requester"})),
        )
    assert loi.value.guard_code == "requester-owns-case"


def test_khac_phong_ban_khong_thao_tac_duoc(session, rule_set, phong_ban):
    ho_so = _den_dang_xu_ly(session, phong_ban)

    with pytest.raises(GuardViolation) as loi:
        perform_transition(
            session,
            case_id=ho_so.id,
            to_state="completed",
            actor=Actor(
                id="xl-99",
                roles=frozenset({"handler"}),
                departments=frozenset({"phong-ban-khac"}),
            ),
        )
    assert loi.value.guard_code == "actor-in-case-department"


def test_leo_thang_khong_duoc_doi_phong_ban(session, rule_set, phong_ban):
    """Leo thang là chuyện nội bộ một phòng, chỉ đổi người phụ trách."""
    ho_so = _den_dang_xu_ly(session, phong_ban)
    perform_transition(
        session, case_id=ho_so.id, to_state="escalated", actor=Actor.system()
    )

    nguoi_duyet = Actor(
        id="xd-01",
        roles=frozenset({"approver"}),
        departments=frozenset({phong_ban}),
    )

    with pytest.raises(GuardViolation) as loi:
        perform_transition(
            session,
            case_id=ho_so.id,
            to_state="in-progress",
            actor=nguoi_duyet,
            changes={"department_code": "phong-ban-khac"},
        )
    assert loi.value.guard_code == "department-unchanged"

    # Không đổi phòng thì đi được, và người phụ trách đổi sang người mới
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="in-progress",
        actor=nguoi_duyet,
        changes={"assignee_id": "xl-02"},
    )
    assert ho_so.current_state == "in-progress"
    assert ho_so.assignee_id == "xl-02"
    assert ho_so.department_code == phong_ban


def test_canh_bat_buoc_ly_do_thi_thieu_ly_do_bi_chan(session, rule_set):
    """Đóng hồ sơ vì không phòng nào nhận thì phải ghi lý do."""
    ho_so = _tao_ho_so(session)
    nguoi_phan_loai = Actor(id="pl-01", roles=frozenset({"classifier"}))

    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=nguoi_phan_loai,
        changes={"priority_code": _muc_uu_tien(session)},
    )

    with pytest.raises(NoteRequired):
        perform_transition(
            session, case_id=ho_so.id, to_state="closed", actor=nguoi_phan_loai
        )

    # Khoảng trắng không tính là lý do
    with pytest.raises(NoteRequired):
        perform_transition(
            session,
            case_id=ho_so.id,
            to_state="closed",
            actor=nguoi_phan_loai,
            note="   ",
        )

    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="closed",
        actor=nguoi_phan_loai,
        note="Không phòng ban nào nhận sau hai lần định tuyến.",
    )
    assert case_history(session, ho_so.id)[-1].note.startswith("Không phòng ban")


def test_khong_dat_duoc_truong_ngoai_danh_sach_cho_phep(session, rule_set):
    """Lần chuyển trạng thái không được dùng làm cửa sau để sửa trường bất kỳ."""
    ho_so = _tao_ho_so(session)
    nguoi_phan_loai = Actor(id="pl-01", roles=frozenset({"classifier"}))

    for truong in ("current_state", "requester_id", "suggested_priority_code"):
        with pytest.raises(TransitionNotAllowed):
            perform_transition(
                session,
                case_id=ho_so.id,
                to_state="classified",
                actor=nguoi_phan_loai,
                changes={
                    "priority_code": _muc_uu_tien(session),
                    truong: "gia-tri-lau",
                },
            )


def test_that_bai_khong_de_lai_dau_vet(session, rule_set):
    """Lần chuyển bị từ chối không được ghi nhật ký lẫn đổi trạng thái."""
    ho_so = _tao_ho_so(session)
    truoc = ho_so.current_state

    with pytest.raises(GuardViolation):
        perform_transition(
            session,
            case_id=ho_so.id,
            to_state="cancelled",
            actor=Actor(id=NGUOI_KHAC, roles=frozenset({"requester"})),
        )

    assert ho_so.current_state == truoc
    assert case_history(session, ho_so.id) == []


# ---------------------------------------------------------------------------
# Nhật ký chỉ ghi thêm
# ---------------------------------------------------------------------------


def test_nhat_ky_khong_sua_duoc(session, rule_set):
    """Trigger ở tầng cơ sở dữ liệu chặn UPDATE, kể cả khi đi vòng qua ứng dụng."""
    ho_so = _tao_ho_so(session)
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=Actor(id="pl-01", roles=frozenset({"classifier"})),
        changes={"priority_code": _muc_uu_tien(session)},
    )
    su_kien = case_history(session, ho_so.id)[0]

    with pytest.raises(Exception, match="chỉ ghi thêm"):
        session.execute(
            text("UPDATE event_log SET actor = 'ke-gian' WHERE id = :id"),
            {"id": su_kien.id},
        )


def test_nhat_ky_khong_xoa_duoc(session, rule_set):
    ho_so = _tao_ho_so(session)
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=Actor(id="pl-01", roles=frozenset({"classifier"})),
        changes={"priority_code": _muc_uu_tien(session)},
    )
    su_kien = case_history(session, ho_so.id)[0]

    with pytest.raises(Exception, match="chỉ ghi thêm"):
        session.execute(
            text("DELETE FROM event_log WHERE id = :id"), {"id": su_kien.id}
        )


def test_nhat_ky_khop_so_luong_voi_so_lan_chuyen(session, rule_set, phong_ban):
    """Bảo đảm cốt lõi: số bản ghi nhật ký bằng đúng số lần chuyển thành công.

    Đếm thẳng trong cơ sở dữ liệu thay vì qua quan hệ đã nạp sẵn, để bắt được cả
    trường hợp có ai đó ghi thêm bản ghi ngoài đường chính.
    """
    ho_so = _den_dang_xu_ly(session, phong_ban)

    tong = session.scalar(
        select(func.count()).select_from(EventLog).where(EventLog.case_id == ho_so.id)
    )
    assert tong == 3
    assert len(case_history(session, ho_so.id)) == 3
