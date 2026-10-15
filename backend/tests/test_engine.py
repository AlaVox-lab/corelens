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
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select, text

from app.models.case import EventLog
from app.models.workflow_config import (
    Department,
    Guard as GuardRow,
    Priority,
    RequestType,
    State,
    Transition,
)
from app.rules.guards import (
    GOVERNED_FIELDS,
    GUARD_REGISTRY,
    Guard,
    apply_effects,
    input_free_guards_pass,
    permitted_fields,
)
from app.workflow.assignment import vai_tro_giao_viec
from app.workflow.context import Actor, TransitionContext
from app.workflow.engine import (
    CHANGEABLE_FIELDS,
    _trang_thai_truoc,
    allowed_transitions,
    case_history,
    create_case,
    perform_transition,
)
from app.workflow.errors import (
    FieldNotPermitted,
    GuardViolation,
    InvalidFieldValue,
    NoteRequired,
    RoleNotPermitted,
    SystemTransitionOnly,
    TransitionNotAllowed,
    UnknownGuard,
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


def _loai_mac_dinh(session) -> str:
    return session.scalars(
        select(RequestType.code)
        .where(RequestType.is_active)
        .order_by(RequestType.display_order)
    ).first()


def _tao_ho_so(session, *, co_loai: bool = True):
    """Một hồ sơ mới, mặc định CÓ loại yêu cầu.

    Mặc định có loại vì đó là trường hợp thường gặp từ #44: người gửi chọn loại ngay
    trên biểu mẫu. Bài nào cần hồ sơ người gửi bỏ trống loại thì truyền `co_loai=False`.
    """
    return create_case(
        session,
        title="Máy in phòng kế toán không nhận lệnh",
        description="Đã thử khởi động lại nhưng không được.",
        requester_id=NGUOI_TAO,
        request_type_code=_loai_mac_dinh(session) if co_loai else None,
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
    # Sửa nội dung (cạnh tự trỏ, #127) hoặc hủy
    assert {c.to_state for c in cua_nguoi_tao} == {"submitted", "cancelled"}

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

    # Phải là một phòng CÓ THẬT. Từ #82 mã phòng bịa bị phép kiểm danh mục chặn trước
    # khi tới ràng buộc này, nên bài sẽ không còn kiểm được điều nó muốn kiểm. Dùng
    # phòng thật thì đây mới đúng là kịch bản đáng lo: đẩy hồ sơ quá hạn sang phòng khác.
    phong_khac = session.scalars(
        select(Department.code).where(Department.is_active, Department.code != phong_ban)
    ).first()
    assert phong_khac is not None, "dữ liệu khởi tạo phải có ít nhất hai phòng ban"

    with pytest.raises(GuardViolation) as loi:
        perform_transition(
            session,
            case_id=ho_so.id,
            to_state="in-progress",
            actor=nguoi_duyet,
            changes={"department_code": phong_khac},
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
    """Lần chuyển trạng thái không được dùng làm cửa sau để sửa trường bất kỳ.

    Thử ở cạnh phân loại — cạnh cho đặt nhiều trường nhất — để chắc ngay cả ở đó trạng
    thái và trường gợi ý của tầng I cũng không lọt. Từ #78 lỗi là `field-not-permitted`
    (422): cạnh vẫn đi được, chỉ nội dung gửi kèm sai.
    """
    ho_so = _tao_ho_so(session)
    nguoi_phan_loai = Actor(id="pl-01", roles=frozenset({"classifier"}))

    for truong in ("current_state", "requester_id", "suggested_priority_code"):
        with pytest.raises(FieldNotPermitted) as loi:
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
        # Chỉ trường lậu bị nêu tên — priority_code hợp lệ ở cạnh này
        assert loi.value.fields == {truong}


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


# ---------------------------------------------------------------------------
# Trường nào đặt được ở cạnh nào — #78
# ---------------------------------------------------------------------------
#
# Trước #78, engine chỉ kiểm trường gửi kèm có thuộc bốn trường quyết định hay không.
# Ai đi được một cạnh bất kỳ cũng sửa được mọi trường quyết định. Giờ trường phải được
# một ràng buộc gắn trên CHÍNH cạnh đó quản — xem GUARD_REGISTRY trong guards.py.

PHAN_LOAI = Actor(id="pl-01", roles=frozenset({"classifier"}))


def _so_dong_nhat_ky(session, case_id: int) -> int:
    return session.scalar(
        select(func.count()).select_from(EventLog).where(EventLog.case_id == case_id)
    )


def _muc_uu_tien_khac(session, khac: str | None) -> str:
    """Một mức ưu tiên hợp lệ khác mức đang có, để phép tấn công trông như thật."""
    ma = session.scalars(
        select(Priority.code)
        .where(Priority.code != khac)
        .order_by(Priority.display_order.desc())
    ).first()
    assert ma is not None, "dữ liệu khởi tạo phải có ít nhất hai mức ưu tiên"
    return ma


def _den_cho_phong_nhan(session, phong_ban: str):
    """Đưa một hồ sơ có loại tới `awaiting-acceptance`."""
    ho_so = _tao_ho_so(session)
    perform_transition(
        session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
        changes={"priority_code": _muc_uu_tien(session)},
    )
    perform_transition(
        session, case_id=ho_so.id, to_state="awaiting-acceptance", actor=PHAN_LOAI,
        changes={"department_code": phong_ban},
    )
    return ho_so


def test_nguoi_xu_ly_khong_tu_nang_duoc_muc_uu_tien(session, rule_set, phong_ban):
    """Đúng lỗ hổng mà #78 vá.

    Người xử lý đi một cạnh hợp lệ của chính họ — `Hoàn thành xử lý` — nhưng lén kèm
    `priority_code`. Cạnh này không mang `set-priority`, nên không được đặt trường đó.
    """
    ho_so = _den_dang_xu_ly(session, phong_ban)
    uu_tien_cu = ho_so.priority_code
    truoc = _so_dong_nhat_ky(session, ho_so.id)
    xl = Actor(id="xl-01", roles=frozenset({"handler"}), departments=frozenset({phong_ban}))

    with pytest.raises(FieldNotPermitted) as loi:
        perform_transition(
            session,
            case_id=ho_so.id,
            to_state="completed",
            actor=xl,
            changes={"priority_code": _muc_uu_tien_khac(session, uu_tien_cu)},
        )

    assert loi.value.code == "field-not-permitted"
    assert loi.value.fields == {"priority_code"}
    # Bị từ chối thì không gì thay đổi, và nhật ký không thêm một dòng nào
    assert ho_so.current_state == "in-progress"
    assert ho_so.priority_code == uu_tien_cu
    assert _so_dong_nhat_ky(session, ho_so.id) == truoc


def test_truong_bi_chan_theo_canh_chu_khong_theo_vai_tro(session, rule_set, phong_ban):
    """Trưởng phòng giao được người xử lý ở cạnh nhận việc, nhưng không đổi được mức
    ưu tiên ở cũng chính cạnh đó. Phép chặn đi theo CẠNH, không theo người."""
    ho_so = _den_cho_phong_nhan(session, phong_ban)
    xd = Actor(id="xd-01", roles=frozenset({"approver"}), departments=frozenset({phong_ban}))

    with pytest.raises(FieldNotPermitted) as loi:
        perform_transition(
            session, case_id=ho_so.id, to_state="in-progress", actor=xd,
            changes={"assignee_id": "xl-01", "priority_code": "urgent"},
        )
    assert loi.value.fields == {"priority_code"}, "assignee_id hợp lệ ở cạnh này"


def test_phan_loai_dat_duoc_uu_tien_va_loai_o_dung_canh(session, rule_set):
    """Chiều ngược lại: trường vẫn đặt được ở cạnh có ràng buộc quản nó."""
    ho_so = _tao_ho_so(session, co_loai=False)
    loai = _loai_mac_dinh(session)

    perform_transition(
        session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
        changes={"priority_code": "high", "request_type_code": loai},
    )
    assert ho_so.priority_code == "high"
    assert ho_so.request_type_code == loai


# --- set-request-type ------------------------------------------------------


def test_phan_loai_bat_buoc_co_loai_khi_nguoi_gui_bo_trong(session, rule_set):
    """Không có loại thì không có ngưỡng SLA, và bộ quét quá hạn bỏ qua hồ sơ đó."""
    ho_so = _tao_ho_so(session, co_loai=False)

    with pytest.raises(GuardViolation) as loi:
        perform_transition(
            session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
            changes={"priority_code": _muc_uu_tien(session)},
        )
    assert loi.value.guard_code == "set-request-type"


def test_phan_loai_giu_loai_nguoi_gui_da_chon(session, rule_set):
    ho_so = _tao_ho_so(session)
    loai_cu = ho_so.request_type_code

    perform_transition(
        session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
        changes={"priority_code": _muc_uu_tien(session)},
    )
    assert ho_so.request_type_code == loai_cu


def test_phan_loai_khong_xoa_duoc_loai(session, rule_set):
    ho_so = _tao_ho_so(session)

    with pytest.raises(GuardViolation) as loi:
        perform_transition(
            session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
            changes={"priority_code": _muc_uu_tien(session), "request_type_code": ""},
        )
    assert loi.value.guard_code == "set-request-type"


def test_hoi_them_o_da_gui_quay_ve_tay_dieu_phoi(session, rule_set):
    """Lối vòng phát hiện ở #78, đóng ở #79.

    Trước #79, `submitted → awaiting-info → classified` tới được `classified` mà không
    đi qua cạnh phân loại, nên hồ sơ vào tận phòng ban mà chưa có mức ưu tiên. Giờ trả
    lời xong thì hồ sơ về lại `submitted`, và muốn đi tiếp phải qua đúng cạnh phân loại
    cùng mọi ràng buộc của nó.
    """
    ho_so = _tao_ho_so(session, co_loai=False)
    _hoi_them(session, ho_so, PHAN_LOAI)
    perform_transition(
        session, case_id=ho_so.id, to_state="submitted", actor=NGUOI_GUI,
        note="Máy in tầng ba, phòng kế toán.",
    )
    assert ho_so.current_state == "submitted"

    with pytest.raises(GuardViolation) as loi:
        perform_transition(
            session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
            changes={"request_type_code": _loai_mac_dinh(session)},
        )
    assert loi.value.guard_code == "set-priority"


def test_cua_phong_ban_van_chan_ho_so_khong_loai(session, rule_set, phong_ban):
    """Lưới an toàn ở cạnh chuyển về phòng ban — cửa duy nhất dẫn tới phòng ban.

    Bộ quy tắc hiện tại không còn đường nào tới `classified` mà thiếu loại, nhưng bộ quy
    tắc là dữ liệu: doanh nghiệp thêm một đường mới thì lưới này phải vẫn đứng. Bài dựng
    thẳng tình huống đó bằng cách xóa loại của một hồ sơ đã phân loại.
    """
    ho_so = _tao_ho_so(session)
    perform_transition(
        session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
        changes={"priority_code": _muc_uu_tien(session)},
    )
    ho_so.request_type_code = None
    session.flush()

    with pytest.raises(GuardViolation) as loi:
        perform_transition(
            session, case_id=ho_so.id, to_state="awaiting-acceptance", actor=PHAN_LOAI,
            changes={"department_code": phong_ban},
        )
    assert loi.value.guard_code == "set-request-type"

    # Đặt loại ngay ở cạnh chuyển về phòng thì đi được
    perform_transition(
        session, case_id=ho_so.id, to_state="awaiting-acceptance", actor=PHAN_LOAI,
        changes={
            "department_code": phong_ban,
            "request_type_code": _loai_mac_dinh(session),
        },
    )
    assert ho_so.current_state == "awaiting-acceptance"


# --- return-to-previous-state — #79 ----------------------------------------
#
# Ai hỏi thêm thì hồ sơ về đúng người đó. Trước #79 người gửi thấy hai nút gần như
# giống hệt nhau và phải tự đoán ai đã hỏi mình.

NGUOI_GUI = Actor(id=NGUOI_TAO, roles=frozenset({"requester"}))
NOI_HOI = ["submitted", "awaiting-acceptance", "in-progress"]


def _nguoi_phong(vai_tro: str, phong_ban: str) -> Actor:
    return Actor(
        id=f"{vai_tro}-01", roles=frozenset({vai_tro}), departments=frozenset({phong_ban})
    )


def _phong_khac(session, phong_ban: str) -> str:
    ma = session.scalars(
        select(Department.code)
        .where(Department.is_active, Department.code != phong_ban)
        .order_by(Department.display_order)
    ).first()
    if ma is None:
        pytest.skip("Cần ít nhất hai phòng ban đang hoạt động.")
    return ma


def _hoi_them(session, ho_so, nguoi_hoi: Actor) -> None:
    perform_transition(
        session, case_id=ho_so.id, to_state="awaiting-info", actor=nguoi_hoi,
        note="Máy in nào, ở tầng mấy?",
    )


def _den_noi_hoi(session, noi_hoi: str, phong_ban: str):
    """Hồ sơ đang ở `noi_hoi`, cùng người hỏi thêm được ở đó."""
    if noi_hoi == "submitted":
        return _tao_ho_so(session), PHAN_LOAI
    if noi_hoi == "awaiting-acceptance":
        return _den_cho_phong_nhan(session, phong_ban), _nguoi_phong("approver", phong_ban)
    return _den_dang_xu_ly(session, phong_ban), _nguoi_phong("handler", phong_ban)


@pytest.mark.parametrize("noi_hoi", NOI_HOI)
def test_bo_sung_xong_ve_dung_cho_da_hoi(session, rule_set, phong_ban, noi_hoi):
    """Định nghĩa hoàn thành của #79: người gửi thấy đúng MỘT nút bổ sung thông tin, và
    nút đó đưa hồ sơ về đúng nơi đã hỏi. Câu trả lời nằm trong nhật ký."""
    ho_so, nguoi_hoi = _den_noi_hoi(session, noi_hoi, phong_ban)
    _hoi_them(session, ho_so, nguoi_hoi)

    nut = {c.to_state for c in allowed_transitions(session, ho_so, NGUOI_GUI)}
    assert nut == {noi_hoi, "cancelled"}

    perform_transition(
        session, case_id=ho_so.id, to_state=noi_hoi, actor=NGUOI_GUI,
        note="Máy in tầng ba, phòng kế toán.",
    )
    assert ho_so.current_state == noi_hoi
    assert case_history(session, ho_so.id)[-1].note == "Máy in tầng ba, phòng kế toán."


@pytest.mark.parametrize("noi_hoi", NOI_HOI)
def test_goi_thang_duong_ve_khac_bi_tu_choi(session, rule_set, phong_ban, noi_hoi):
    """Nửa sau của Poka-yoke: giấu nút chưa đủ, engine vẫn chặn khi gọi thẳng API."""
    ho_so, nguoi_hoi = _den_noi_hoi(session, noi_hoi, phong_ban)
    _hoi_them(session, ho_so, nguoi_hoi)
    truoc = _so_dong_nhat_ky(session, ho_so.id)

    for dich in set(NOI_HOI) - {noi_hoi}:
        with pytest.raises(GuardViolation) as loi:
            perform_transition(
                session, case_id=ho_so.id, to_state=dich, actor=NGUOI_GUI,
                note="Trả lời nhầm chỗ.",
            )
        assert loi.value.guard_code == "return-to-previous-state"

    assert ho_so.current_state == "awaiting-info"
    assert _so_dong_nhat_ky(session, ho_so.id) == truoc


def test_hoi_lai_lan_hai_van_ve_dung_cho(session, rule_set, phong_ban):
    """Chỗ cũ đọc từ dòng nhật ký MỚI NHẤT. Hồ sơ đã từng hỏi ở Đã gửi, lần này hỏi ở
    Đang xử lý — đọc nhầm dòng cũ là hồ sơ đang làm dở bị đẩy về hàng đợi phân loại."""
    ho_so = _tao_ho_so(session)
    _hoi_them(session, ho_so, PHAN_LOAI)
    perform_transition(
        session, case_id=ho_so.id, to_state="submitted", actor=NGUOI_GUI, note="Tầng ba."
    )
    perform_transition(
        session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
        changes={"priority_code": _muc_uu_tien(session)},
    )
    perform_transition(
        session, case_id=ho_so.id, to_state="awaiting-acceptance", actor=PHAN_LOAI,
        changes={"department_code": phong_ban},
    )
    perform_transition(
        session, case_id=ho_so.id, to_state="in-progress",
        actor=_nguoi_phong("approver", phong_ban),
    )
    _hoi_them(session, ho_so, _nguoi_phong("handler", phong_ban))

    nut = {c.to_state for c in allowed_transitions(session, ho_so, NGUOI_GUI)}
    assert nut == {"in-progress", "cancelled"}


def test_bo_sung_thong_tin_bat_buoc_ghi_noi_dung(session, rule_set):
    """Ô ghi chú là chính câu trả lời, nên không được trống. Lỗi gọi ô bằng tên của nó
    trong dữ liệu, không gọi là "lý do"."""
    ho_so = _tao_ho_so(session)
    _hoi_them(session, ho_so, PHAN_LOAI)
    canh = session.scalars(
        select(Transition).where(
            Transition.rule_set_id == rule_set.id,
            Transition.from_state == "awaiting-info",
            Transition.to_state == "submitted",
        )
    ).one()
    assert canh.note_label

    with pytest.raises(NoteRequired) as loi:
        perform_transition(
            session, case_id=ho_so.id, to_state="submitted", actor=NGUOI_GUI, note="  "
        )
    assert canh.note_label in str(loi.value)


def test_truong_phong_hoi_them_duoc_khi_cho_xac_duyet(session, rule_set, phong_ban):
    """Mở rộng phạm vi navigator chốt ngày 23/09: trưởng phòng hỏi thêm trước khi nhận."""
    ho_so = _den_cho_phong_nhan(session, phong_ban)
    truong_phong = _nguoi_phong("approver", phong_ban)

    assert "awaiting-info" in {
        c.to_state for c in allowed_transitions(session, ho_so, truong_phong)
    }
    _hoi_them(session, ho_so, truong_phong)
    assert ho_so.current_state == "awaiting-info"
    assert ho_so.department_code == phong_ban, "hồ sơ vẫn thuộc phòng đã hỏi"


def test_truong_phong_khac_khong_hoi_them_duoc(session, rule_set, phong_ban):
    ho_so = _den_cho_phong_nhan(session, phong_ban)
    nguoi_la = _nguoi_phong("approver", _phong_khac(session, phong_ban))

    assert allowed_transitions(session, ho_so, nguoi_la) == [], (
        "ràng buộc không cần nhập liệu chạy luôn lúc chào nút"
    )
    with pytest.raises(GuardViolation) as loi:
        _hoi_them(session, ho_so, nguoi_la)
    assert loi.value.guard_code == "actor-in-case-department"


def test_nguoi_gui_khac_khong_thay_nut_tren_ho_so_nguoi_khac(session, rule_set):
    ho_so = _tao_ho_so(session)
    nguoi_khac = Actor(id=NGUOI_KHAC, roles=frozenset({"requester"}))
    assert allowed_transitions(session, ho_so, nguoi_khac) == []


def test_quay_ve_khi_chua_co_lich_su_thi_tu_choi():
    """Không biết chỗ cũ thì không cho đi đâu cả — đóng cửa chứ không mở toang."""
    ctx = TransitionContext(
        case=None,
        transition=SimpleNamespace(to_state="submitted"),
        actor=NGUOI_GUI,
        previous_state=None,
    )
    with pytest.raises(GuardViolation):
        GUARD_REGISTRY["return-to-previous-state"].check(ctx)


def test_tac_dong_dat_truong_chua_khai_thi_no_ngay(monkeypatch):
    """Tác động chỉ được đặt đúng trường đã khai ở `sets` — khai một đằng làm một nẻo thì
    biên ngoài kiểm lúc nạp mô-đun thành vô nghĩa (#127)."""
    monkeypatch.setitem(
        GUARD_REGISTRY,
        "tac-dong-sai",
        Guard(lambda ctx: None, sets=frozenset({"assignee_id"}),
              effect=lambda ctx: {"priority_code": "urgent"}),
    )
    ctx = TransitionContext(
        case=None,
        transition=SimpleNamespace(to_state="in-progress", guard_codes=["tac-dong-sai"]),
        actor=NGUOI_GUI,
    )
    with pytest.raises(RuntimeError):
        apply_effects(ctx)


def test_ma_rang_buoc_chua_cai_dat_khong_bi_giau_luc_chao_nut():
    """Chào nút chỉ nuốt lỗi Poka-yoke. Mã ràng buộc chưa cài đặt phải nổ như lúc chuyển
    thật — giấu nút đi thì cấu hình sai trông như "không có thao tác nào"."""
    ctx = TransitionContext(
        case=None,
        transition=SimpleNamespace(to_state="submitted", guard_codes=["chua-cai-dat"]),
        actor=NGUOI_GUI,
    )
    with pytest.raises(UnknownGuard):
        input_free_guards_pass(ctx)


# --- Đổi hồ sơ mà giữ nguyên trạng thái — #127, ADR-0005 ----------------------
#
# Hai thao tác đổi hồ sơ nên đi qua cửa chuyển trạng thái và có dòng nhật ký, dù trạng
# thái có thể không đổi: tự nhận việc, và sửa nội dung trước khi tới phòng ban.


def _nguoi_xu_ly(phong_ban: str, so: int = 1, ten: str | None = None) -> Actor:
    return Actor(
        id=f"handler-0{so}",
        name=ten or f"Người Xử Lý {so}",
        roles=frozenset({"handler"}),
        departments=frozenset({phong_ban}),
    )


def _canh(session, rule_set, tu: str, den: str) -> Transition:
    return session.scalars(
        select(Transition).where(
            Transition.rule_set_id == rule_set.id,
            Transition.from_state == tu,
            Transition.to_state == den,
        )
    ).one()


def test_nhan_viec_ve_minh_dat_nguoi_xu_ly_giu_trang_thai(session, rule_set, phong_ban):
    """Định nghĩa hoàn thành của #127, nửa nhận việc: hồ sơ thành của người bấm, trạng
    thái giữ nguyên, nhật ký có đúng một dòng ghi người xử lý "trống → họ"."""
    ho_so = _den_dang_xu_ly(session, phong_ban)
    toi = _nguoi_xu_ly(phong_ban, ten="Cường Lê")
    truoc = _so_dong_nhat_ky(session, ho_so.id)

    assert "in-progress" in {c.to_state for c in allowed_transitions(session, ho_so, toi)}
    perform_transition(session, case_id=ho_so.id, to_state="in-progress", actor=toi)

    assert ho_so.current_state == "in-progress"
    assert ho_so.assignee_id == toi.id
    assert ho_so.assignee_label == "Cường Lê", "tên lấy từ chính token của người nhận"
    assert _so_dong_nhat_ky(session, ho_so.id) == truoc + 1
    dong = case_history(session, ho_so.id)[-1]
    assert (dong.from_state, dong.to_state) == ("in-progress", "in-progress")
    assert dong.changes == {
        "assignee_id": {
            "from": None, "to": toi.id, "from_label": None, "to_label": "Cường Lê",
        }
    }


def test_ho_so_da_co_nguoi_giu_thi_khong_tu_nhan_duoc(session, rule_set, phong_ban):
    """Tự nhận không phải cách giành việc của đồng nghiệp."""
    ho_so = _den_dang_xu_ly(session, phong_ban)
    nguoi_dau = _nguoi_xu_ly(phong_ban, so=1)
    perform_transition(session, case_id=ho_so.id, to_state="in-progress", actor=nguoi_dau)
    nguoi_sau = _nguoi_xu_ly(phong_ban, so=2)

    assert "in-progress" not in {
        c.to_state for c in allowed_transitions(session, ho_so, nguoi_sau)
    }, "ràng buộc không cần nhập liệu chạy luôn lúc chào nút"
    with pytest.raises(GuardViolation) as loi:
        perform_transition(session, case_id=ho_so.id, to_state="in-progress", actor=nguoi_sau)
    assert loi.value.guard_code == "assign-self"
    assert ho_so.assignee_id == nguoi_dau.id


def test_tu_nhan_viec_khong_co_o_chon_nguoi(session, rule_set, phong_ban):
    """Người được giao là chính người bấm. Gửi kèm người khác thì bị từ chối — cạnh này
    không cho đặt trường nào."""
    assert permitted_fields(_canh(session, rule_set, "in-progress", "in-progress").guard_codes) \
        == frozenset()
    ho_so = _den_dang_xu_ly(session, phong_ban)

    with pytest.raises(FieldNotPermitted):
        perform_transition(
            session, case_id=ho_so.id, to_state="in-progress",
            actor=_nguoi_xu_ly(phong_ban), changes={"assignee_id": "handler-09"},
        )
    assert ho_so.assignee_id is None


def test_nguoi_phong_khac_khong_tu_nhan_duoc(session, rule_set, phong_ban):
    ho_so = _den_dang_xu_ly(session, phong_ban)
    nguoi_la = _nguoi_xu_ly(_phong_khac(session, phong_ban))

    assert allowed_transitions(session, ho_so, nguoi_la) == []
    with pytest.raises(GuardViolation) as loi:
        perform_transition(session, case_id=ho_so.id, to_state="in-progress", actor=nguoi_la)
    assert loi.value.guard_code == "actor-in-case-department"


def test_tu_nhan_viec_khong_bien_nguoi_xu_ly_thanh_vai_tro_giao_viec(session, rule_set):
    """Người xử lý không mở được ô chọn người của cả phòng chỉ vì có nút tự nhận (#84)."""
    assert "handler" not in vai_tro_giao_viec(session, rule_set.id)


def test_dong_tu_tro_khong_lam_lech_cho_cu_cua_79(session, rule_set, phong_ban):
    """"Chỗ cũ" là trạng thái hồ sơ đã ở trước khi VÀO trạng thái hiện tại. Dòng tự trỏ
    không đưa hồ sơ vào đâu, nên bị bỏ qua."""
    ho_so = _den_dang_xu_ly(session, phong_ban)
    perform_transition(
        session, case_id=ho_so.id, to_state="in-progress", actor=_nguoi_xu_ly(phong_ban)
    )
    assert _trang_thai_truoc(session, ho_so.id) == "awaiting-acceptance"


def test_sua_noi_dung_o_da_gui_giu_trang_thai_va_giu_ban_cu(session, rule_set):
    """Định nghĩa hoàn thành của #127, nửa sửa nội dung: hồ sơ mang nội dung mới, nhật
    ký giữ bản cũ. Trường gửi lại y nguyên thì không sinh dòng "A → A"."""
    ho_so = _tao_ho_so(session)
    tieu_de_cu = ho_so.title

    perform_transition(
        session, case_id=ho_so.id, to_state="submitted", actor=NGUOI_GUI,
        changes={"title": "Máy in tầng ba kẹt giấy", "description": ho_so.description},
    )

    assert ho_so.current_state == "submitted"
    assert ho_so.title == "Máy in tầng ba kẹt giấy"
    dong = case_history(session, ho_so.id)[-1]
    assert (dong.from_state, dong.to_state) == ("submitted", "submitted")
    assert dong.changes == {"title": {"from": tieu_de_cu, "to": "Máy in tầng ba kẹt giấy"}}


def test_sua_noi_dung_o_da_phan_loai_thi_ve_phan_loai_lai(session, rule_set):
    """Phân loại cũ dựa trên nội dung cũ, nên sửa xong phải phân loại lại."""
    ho_so = _tao_ho_so(session)
    perform_transition(
        session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
        changes={"priority_code": _muc_uu_tien(session)},
    )

    perform_transition(
        session, case_id=ho_so.id, to_state="submitted", actor=NGUOI_GUI,
        changes={"description": "Máy in ở tầng ba, đèn báo lỗi nhấp nháy màu cam."},
    )

    assert ho_so.current_state == "submitted"
    assert "classified" in {
        c.to_state for c in allowed_transitions(session, ho_so, PHAN_LOAI)
    }


def test_toi_phong_ban_roi_thi_khong_sua_duoc(session, rule_set, phong_ban):
    """Khóa bằng sự vắng mặt: không cạnh sửa nào xuất phát từ trạng thái của phòng ban."""
    for ho_so in (_den_cho_phong_nhan(session, phong_ban), _den_dang_xu_ly(session, phong_ban)):
        assert "submitted" not in {
            c.to_state for c in allowed_transitions(session, ho_so, NGUOI_GUI)
        }
        with pytest.raises(TransitionNotAllowed):
            perform_transition(
                session, case_id=ho_so.id, to_state="submitted", actor=NGUOI_GUI,
                changes={"title": "Tiêu đề sửa sau khi tới phòng"},
            )


def test_sua_noi_dung_khong_dat_duoc_muc_uu_tien(session, rule_set):
    """Ràng buộc Poka-yoke "người tạo không tự đặt mức ưu tiên" vẫn đứng (ADR-0005)."""
    ho_so = _tao_ho_so(session)
    with pytest.raises(FieldNotPermitted):
        perform_transition(
            session, case_id=ho_so.id, to_state="submitted", actor=NGUOI_GUI,
            changes={"priority_code": _muc_uu_tien(session)},
        )


@pytest.mark.parametrize(
    "thay_doi",
    [
        {},
        {"title": "  ab  "},
        {"title": "x" * 201},
        {"description": "x" * 5001},
        {"request_type_code": ""},
        {"title": "Máy in phòng kế toán không nhận lệnh"},
    ],
    ids=["khong-gui-gi", "tieu-de-ngan", "tieu-de-dai", "mo-ta-dai", "xoa-loai", "khong-doi-gi"],
)
def test_sua_noi_dung_sai_bi_tu_choi(session, rule_set, thay_doi):
    ho_so = _tao_ho_so(session)
    truoc = _so_dong_nhat_ky(session, ho_so.id)

    with pytest.raises(GuardViolation) as loi:
        perform_transition(
            session, case_id=ho_so.id, to_state="submitted", actor=NGUOI_GUI,
            changes=thay_doi,
        )
    assert loi.value.guard_code == "edit-content"
    assert _so_dong_nhat_ky(session, ho_so.id) == truoc


def test_nguoi_gui_khac_khong_sua_duoc(session, rule_set):
    ho_so = _tao_ho_so(session)
    nguoi_khac = Actor(id=NGUOI_KHAC, roles=frozenset({"requester"}))
    with pytest.raises(GuardViolation) as loi:
        perform_transition(
            session, case_id=ho_so.id, to_state="submitted", actor=nguoi_khac,
            changes={"title": "Sửa hồ sơ của người khác"},
        )
    assert loi.value.guard_code == "requester-owns-case"


# --- assign-handler --------------------------------------------------------


def test_giao_nguoi_xu_ly_khi_nhan_viec_la_tuy_chon(session, rule_set, phong_ban):
    """Chưa bắt buộc chọn người — việc đó chờ ô chọn người ở buồng lái (#84)."""
    ho_so = _den_dang_xu_ly(session, phong_ban)
    assert ho_so.current_state == "in-progress"
    assert ho_so.assignee_id is None


def test_giao_nguoi_xu_ly_khong_duoc_de_trong(session, rule_set, phong_ban):
    ho_so = _den_cho_phong_nhan(session, phong_ban)
    xd = Actor(id="xd-01", roles=frozenset({"approver"}), departments=frozenset({phong_ban}))

    with pytest.raises(GuardViolation) as loi:
        perform_transition(
            session, case_id=ho_so.id, to_state="in-progress", actor=xd,
            changes={"assignee_id": "   "},
        )
    assert loi.value.guard_code == "assign-handler"

    perform_transition(
        session, case_id=ho_so.id, to_state="in-progress", actor=xd,
        changes={"assignee_id": "xl-01"},
    )
    assert ho_so.assignee_id == "xl-01"


# --- Hợp đồng giữa dữ liệu và mã nguồn ---------------------------------------


def test_bang_guards_va_ma_nguon_khop_khit(session, rule_set):
    """Mọi mã ràng buộc trong bảng đều có hàm, và mọi hàm đều có dòng trong bảng.

    Chiều thứ nhất engine đã canh lúc chạy bằng `UnknownGuard`. Chiều thứ hai thì không
    ai canh: một hàm có trong mã mà không có dòng dữ liệu nào là mã chết.
    """
    trong_bang = set(session.scalars(select(GuardRow.code)).all())
    assert trong_bang == set(GUARD_REGISTRY)


def test_moi_truong_quyet_dinh_deu_dat_duoc_o_it_nhat_mot_canh(session, rule_set):
    """Bắt lỗi cấu hình ngược: gỡ nhầm một ràng buộc khỏi dữ liệu.

    Ai đó xóa dòng `set-request-type` trong infra/seed/ thì không cạnh nào còn đặt được
    loại yêu cầu — trường quyết định thành trường chết mà không có lỗi nào nổ ra.
    """
    cac_ma = {
        g.guard_code
        for t in session.scalars(
            select(Transition).where(Transition.rule_set_id == rule_set.id)
        ).all()
        for g in t.guards
    }
    # Trường chỉ ràng buộc TỰ ĐẶT, không ai nhập — tổng giờ và số lần gia hạn (#101). Chúng
    # không là ô nhập của cạnh nào, nhưng vẫn phải có cạnh trong dữ liệu mang ràng buộc đặt
    # chúng, không thì cũng thành trường chết.
    tu_dat = frozenset().union(*(g.sets for g in GUARD_REGISTRY.values()))
    nhap_duoc = frozenset().union(*(g.governs for g in GUARD_REGISTRY.values()))
    chi_tu_dat = tu_dat - nhap_duoc
    assert permitted_fields(cac_ma) == CHANGEABLE_FIELDS - chi_tu_dat
    assert chi_tu_dat <= frozenset().union(*(GUARD_REGISTRY[m].sets for m in cac_ma))
    assert GOVERNED_FIELDS <= CHANGEABLE_FIELDS


# ---------------------------------------------------------------------------
# Giá trị phải có trong danh mục — #82
# ---------------------------------------------------------------------------
#
# Buồng lái là nơi đầu tiên gửi `changes` qua HTTP, nên là nơi đầu tiên gặp giá trị gõ
# sai. Không kiểm thì khóa ngoại nổ thành lỗi 500 không lời giải thích.


def test_phong_ban_ngung_hoat_dong_bi_tu_choi(session, rule_set):
    """Khóa ngoại không bắt được trường hợp này: dòng vẫn còn, chỉ là đã ngừng dùng."""
    ho_so = _tao_ho_so(session)
    perform_transition(
        session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
        changes={"priority_code": _muc_uu_tien(session)},
    )
    phong = session.scalars(select(Department).where(Department.is_active)).first()
    phong.is_active = False
    session.flush()

    with pytest.raises(InvalidFieldValue) as loi:
        perform_transition(
            session, case_id=ho_so.id, to_state="awaiting-acceptance", actor=PHAN_LOAI,
            changes={"department_code": phong.code},
        )
    assert loi.value.code == "invalid-field-value"
    assert loi.value.field == "department_code"


def test_gia_tri_khong_phai_chuoi_bi_tu_choi(session, rule_set):
    """Gửi số thay vì mã: không để nó xuống tới câu truy vấn so sánh text với integer."""
    ho_so = _tao_ho_so(session)
    with pytest.raises(InvalidFieldValue):
        perform_transition(
            session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
            changes={"priority_code": 3},
        )


def test_phan_cong_lai_khong_xoa_duoc_phong_ban_bang_none(session, rule_set, phong_ban):
    """Lỗ ở `department-unchanged` từ #78, vá ở #82.

    Ràng buộc cũ chỉ chặn khi giá trị khác None. Gửi `department_code: None` thì lọt
    qua, rồi bước cập nhật hồ sơ ghi đè None — hồ sơ đang leo thang mất luôn phòng ban.
    """
    ho_so = _den_dang_xu_ly(session, phong_ban)
    perform_transition(
        session, case_id=ho_so.id, to_state="escalated", actor=Actor.system("sla")
    )
    xd = Actor(id="xd-01", roles=frozenset({"approver"}), departments=frozenset({phong_ban}))

    with pytest.raises(GuardViolation) as loi:
        perform_transition(
            session, case_id=ho_so.id, to_state="in-progress", actor=xd,
            changes={"department_code": None},
        )
    assert loi.value.guard_code == "department-unchanged"
    assert ho_so.department_code == phong_ban
