# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Cờ "cần tôi xử lý" trên danh sách hồ sơ (#227).
#
# Mỗi bài ứng với một dòng của bảng kỳ vọng trong issue. Cờ suy từ cột
# transitions.primary_scope, nên hai bài cuối đổi dữ liệu quy tắc ngay trong giao dịch
# của bài (hoàn tác khi xong) để chứng minh cờ đi theo dữ liệu chứ không theo mã.

from __future__ import annotations

from sqlalchemy import event, select

from app.models.case import Request
from app.models.workflow_config import Priority, RequestType, Transition
from app.workflow.context import Actor
from app.workflow.engine import create_case, needs_my_action, perform_transition

NGUOI_GUI = Actor(id="ct-gui-01", name="An Nguyễn", roles=frozenset({"requester"}))
DIEU_PHOI = Actor(id="ct-dp-01", name="Bình Trần", roles=frozenset({"classifier"}))
HE_THONG = Actor.system()


def _truong_phong(phong: str) -> Actor:
    return Actor(id="ct-tp-01", name="Dung Phạm", roles=frozenset({"approver"}),
                 departments=frozenset({phong}))


def _xu_ly(phong: str, ma: str = "ct-xl-01") -> Actor:
    return Actor(id=ma, name="Cường Lê", roles=frozenset({"handler"}),
                 departments=frozenset({phong}))


def _chuyen(session, ho_so: Request, den: str, actor: Actor, **kem) -> None:
    perform_transition(session, case_id=ho_so.id, to_state=den, actor=actor, **kem)


def _cho(session, ho_so: Request, actor: Actor) -> bool:
    return needs_my_action(session, [ho_so], actor)[ho_so.id]


def _moi(session, nguoi_gui: Actor = NGUOI_GUI) -> Request:
    loai = session.scalars(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    return create_case(session, title="Máy chiếu phòng họp không lên hình",
                       requester_id=nguoi_gui.id, requester_label=nguoi_gui.label,
                       request_type_code=loai)


def _da_phan_loai(session) -> Request:
    ho_so = _moi(session)
    uu_tien = session.scalars(select(Priority.code).order_by(Priority.display_order)).first()
    _chuyen(session, ho_so, "classified", DIEU_PHOI, changes={"priority_code": uu_tien})
    return ho_so


def _cho_phong(session, phong: str) -> Request:
    ho_so = _da_phan_loai(session)
    _chuyen(session, ho_so, "awaiting-acceptance", DIEU_PHOI, changes={"department_code": phong})
    return ho_so


def _dang_xu_ly(session, phong: str, giao_cho: Actor | None = None) -> Request:
    ho_so = _cho_phong(session, phong)
    _chuyen(session, ho_so, "in-progress", _truong_phong(phong),
            changes={"assignee_id": giao_cho.id} if giao_cho else None,
            assignee_label=giao_cho.name if giao_cho else None)
    return ho_so


# --- Người gửi -----------------------------------------------------------------------


def test_nguoi_gui_khong_bi_cho_khi_ho_so_dang_o_noi_khac(session, rule_set, phong_ban):
    """Đã gửi, Đã phân loại, Chờ phòng ban xác duyệt: sửa/hủy được nhưng không phải việc."""
    da_gui = _moi(session)
    da_phan_loai = _da_phan_loai(session)
    cho_phong = _cho_phong(session, phong_ban)
    dang_xu_ly = _dang_xu_ly(session, phong_ban)

    co = needs_my_action(session, [da_gui, da_phan_loai, cho_phong, dang_xu_ly], NGUOI_GUI)
    assert co == dict.fromkeys([da_gui.id, da_phan_loai.id, cho_phong.id, dang_xu_ly.id], False)


def test_nguoi_gui_bi_cho_khi_duoc_hoi_them(session, rule_set, phong_ban):
    ho_so = _moi(session)
    _chuyen(session, ho_so, "awaiting-info", DIEU_PHOI, note="Máy chiếu ở phòng nào?")
    assert _cho(session, ho_so, NGUOI_GUI) is True


def test_nguoi_gui_bi_cho_khi_ho_so_hoan_tat(session, rule_set, phong_ban):
    xu_ly = _xu_ly(phong_ban)
    ho_so = _dang_xu_ly(session, phong_ban, giao_cho=xu_ly)
    _chuyen(session, ho_so, "completed", xu_ly, note="Đã thay cáp HDMI")
    assert _cho(session, ho_so, NGUOI_GUI) is True


# --- Điều phối viên ------------------------------------------------------------------


def test_dieu_phoi_bi_cho_o_ba_trang_thai_cua_minh(session, rule_set, phong_ban):
    da_gui = _moi(session)
    da_phan_loai = _da_phan_loai(session)
    bi_tra = _cho_phong(session, phong_ban)
    _chuyen(session, bi_tra, "rejected-by-department", _truong_phong(phong_ban),
            note="Việc này thuộc phòng khác")

    co = needs_my_action(session, [da_gui, da_phan_loai, bi_tra], DIEU_PHOI)
    assert co == dict.fromkeys([da_gui.id, da_phan_loai.id, bi_tra.id], True)


def test_dieu_phoi_chi_cho_khi_ho_so_o_phong_ban(session, rule_set, phong_ban):
    """Chờ phòng ban xác duyệt: điều phối rút về hay gia hạn được, nhưng hồ sơ chờ phòng."""
    ho_so = _cho_phong(session, phong_ban)
    assert _cho(session, ho_so, DIEU_PHOI) is False


def test_dieu_phoi_khong_bi_cho_voi_ho_so_minh_gui(session, rule_set, phong_ban):
    """Ràng buộc cấm tự điều phối (#154) cũng chặn cờ, như nó chặn nút."""
    nguoi_kiem_nhiem = Actor(id="ct-kn-01", name="Hà Võ",
                             roles=frozenset({"requester", "classifier"}))
    ho_so = _moi(session, nguoi_gui=nguoi_kiem_nhiem)
    assert _cho(session, ho_so, nguoi_kiem_nhiem) is False


# --- Trưởng phòng --------------------------------------------------------------------


def test_truong_phong_bi_cho_khi_ho_so_ve_phong_minh(session, rule_set, phong_ban):
    ho_so = _cho_phong(session, phong_ban)
    assert _cho(session, ho_so, _truong_phong(phong_ban)) is True
    assert _cho(session, ho_so, _truong_phong("phong-khac-khong-co")) is False


def test_truong_phong_bi_cho_khi_ho_so_leo_thang(session, rule_set, phong_ban):
    ho_so = _dang_xu_ly(session, phong_ban, giao_cho=_xu_ly(phong_ban))
    _chuyen(session, ho_so, "escalated", HE_THONG)
    assert _cho(session, ho_so, _truong_phong(phong_ban)) is True


# --- Người xử lý ---------------------------------------------------------------------


def test_nguoi_xu_ly_bi_cho_khi_duoc_giao(session, rule_set, phong_ban):
    toi = _xu_ly(phong_ban)
    nguoi_khac = _xu_ly(phong_ban, ma="ct-xl-02")
    ho_so = _dang_xu_ly(session, phong_ban, giao_cho=toi)

    assert _cho(session, ho_so, toi) is True
    assert _cho(session, ho_so, nguoi_khac) is False, "giao người khác thì không chờ tôi"


def test_ho_so_chua_giao_ai_cho_ca_phong(session, rule_set, phong_ban):
    ho_so = _dang_xu_ly(session, phong_ban)
    assert _cho(session, ho_so, _xu_ly(phong_ban)) is True


# --- Đi theo dữ liệu, không theo mã ------------------------------------------------


def _canh(session, rule_set, ma_hoat_dong: str, tu: str) -> Transition:
    return session.scalars(
        select(Transition).where(
            Transition.rule_set_id == rule_set.id,
            Transition.activity_code == ma_hoat_dong,
            Transition.from_state == tu,
            Transition.is_system.is_(False),
        )
    ).one()


def test_go_buoc_chinh_trong_du_lieu_thi_co_tat(session, rule_set, phong_ban):
    ho_so = _moi(session)
    assert _cho(session, ho_so, DIEU_PHOI) is True

    _canh(session, rule_set, "classify", "submitted").primary_scope = None
    session.flush()
    assert _cho(session, ho_so, DIEU_PHOI) is False


def test_danh_dau_buoc_chinh_moi_thi_co_bat(session, rule_set, phong_ban):
    ho_so = _moi(session)
    assert _cho(session, ho_so, NGUOI_GUI) is False

    _canh(session, rule_set, "cancel", "submitted").primary_scope = "role"
    session.flush()
    assert _cho(session, ho_so, NGUOI_GUI) is True


# --- Qua điểm cuối -------------------------------------------------------------------


def test_danh_sach_ho_so_cua_toi_tra_co(session, rule_set, phong_ban):
    from fastapi.testclient import TestClient

    from app.auth.dependencies import current_actor
    from app.db import get_session
    from app.main import app

    cho_toi = _moi(session)
    _chuyen(session, cho_toi, "awaiting-info", DIEU_PHOI, note="Ở phòng nào?")
    khong_cho = _moi(session)

    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: NGUOI_GUI
    try:
        with TestClient(app) as client:
            ds = client.get("/requests").json()["items"]
            dong = {d["id"]: d["needs_my_action"] for d in ds}
            nhan = {d["id"]: d["next_step_label"] for d in ds}
            chi_tiet = client.get(f"/requests/{cho_toi.id}").json()
    finally:
        app.dependency_overrides.clear()

    assert dong[cho_toi.id] is True
    assert dong[khong_cho.id] is False
    assert chi_tiet["needs_my_action"] is None, "trang chi tiết không điền cờ"
    assert nhan[cho_toi.id] == "Bổ sung thông tin", "nút trên dòng việc lấy nhãn của bước chính"
    assert nhan[khong_cho.id] is None


def test_canh_di_duoc_danh_dau_buoc_chinh(session, rule_set, phong_ban):
    """Ngăn xem nhanh (#233) đặt bước chính thành nút ở đáy: đúng một cạnh mang cờ khi hồ sơ
    chờ người xem, cùng cạnh với nhãn trên dòng danh sách; không chờ thì không cạnh nào."""
    from fastapi.testclient import TestClient

    from app.auth.dependencies import current_actor
    from app.db import get_session
    from app.main import app

    cho_toi = _moi(session)
    _chuyen(session, cho_toi, "awaiting-info", DIEU_PHOI, note="Ở phòng nào?")
    khong_cho = _moi(session)

    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: NGUOI_GUI
    try:
        with TestClient(app) as client:
            nhan = {d["id"]: d["next_step_label"] for d in client.get("/requests").json()["items"]}
            canh_cho = client.get(f"/requests/{cho_toi.id}").json()["allowed_transitions"]
            canh_khong = client.get(f"/requests/{khong_cho.id}").json()["allowed_transitions"]
    finally:
        app.dependency_overrides.clear()

    chinh = [c for c in canh_cho if c["is_primary"]]
    assert [c["activity_label"] for c in chinh] == [nhan[cho_toi.id]]
    assert len(canh_cho) > len(chinh), "các thao tác khác vẫn còn, chỉ không phải bước chính"
    assert canh_khong and not any(c["is_primary"] for c in canh_khong)


# --- Hiệu năng -----------------------------------------------------------------------


def _dem_truy_van(session, cac_ho_so: list[Request]) -> int:
    dem = []
    may = session.get_bind()
    nghe = lambda *_: dem.append(1)  # noqa: E731
    event.listen(may, "before_cursor_execute", nghe)
    try:
        needs_my_action(session, cac_ho_so, NGUOI_GUI)
    finally:
        event.remove(may, "before_cursor_execute", nghe)
    return len(dem)


def test_so_truy_van_khong_tang_theo_so_dong(session, rule_set, phong_ban):
    cac_ho_so = [_moi(session) for _ in range(6)]
    for ho_so in cac_ho_so[:3]:
        _chuyen(session, ho_so, "awaiting-info", DIEU_PHOI, note="Ở phòng nào?")
    session.flush()

    # Đếm 1 dòng trước: lần này còn phải nạp cạnh, nên là lần tốn nhất nếu số truy vấn
    # không phụ thuộc số dòng.
    mot_dong = _dem_truy_van(session, cac_ho_so[:1])
    sau_dong = _dem_truy_van(session, cac_ho_so)
    assert sau_dong <= mot_dong, f"1 hồ sơ: {mot_dong} truy vấn, 6 hồ sơ: {sau_dong}"


def test_quan_tri_vien_co_khong_gian_he_thong(session):
    """Màn Hệ thống (#229) chỉ hiện với quản trị viên, qua danh sách không gian của /me."""
    from fastapi.testclient import TestClient

    from app.auth.dependencies import current_actor, current_claims
    from app.db import get_session
    from app.main import app

    quan_tri = Actor(id="ct-qt-01", name="Quản trị", roles=frozenset({"administrator"}))
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_claims] = lambda: {}
    try:
        with TestClient(app) as client:
            app.dependency_overrides[current_actor] = lambda: quan_tri
            cua_qt = client.get("/me").json()["workspaces"]
            app.dependency_overrides[current_actor] = lambda: NGUOI_GUI
            cua_gui = client.get("/me").json()["workspaces"]
    finally:
        app.dependency_overrides.clear()

    assert "system" in cua_qt
    assert "system" not in cua_gui
