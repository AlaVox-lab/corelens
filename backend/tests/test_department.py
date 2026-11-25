# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử buồng lái phòng ban (#83).
#
# Danh bạ Keycloak thay bằng danh bạ giả, như test_assignment.py. Phần gọi Keycloak
# thật đã kiểm ở đó; ở đây kiểm cửa, hàng đợi, và việc giao người phải đi qua danh bạ.

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.dependencies import current_actor
from app.auth.directory import DirectoryUnavailable, Person, get_directory
from app.db import get_session
from app.main import app, me
from app.models.case import EventLog, Request
from app.models.workflow_config import (
    Department,
    Priority,
    RequestType,
    State,
    Transition,
    TransitionRole,
)
from app.rules.sla import gioi_han_giay
from app.workflow.assignment import vai_tro_giao_viec, vai_tro_nhan_viec
from app.workflow.context import Actor
from app.workflow.engine import create_case, perform_transition
from tests.truong_mau import chi_tiet_mau

NGUOI_GUI = Actor(id="kc-gui-01", name="An Nguyễn", roles=frozenset({"requester"}))
PHAN_LOAI = Actor(id="kc-pl-01", name="Bình Trần", roles=frozenset({"classifier"}))


def _truong_phong(phong: str) -> Actor:
    return Actor(id="kc-tp-01", name="Dung Phạm", roles=frozenset({"approver"}),
                 departments=frozenset({phong}))


def _xu_ly(phong: str, so: int = 1) -> Actor:
    return Actor(id=f"kc-xl-0{so}", name=f"Người Xử Lý {so}", roles=frozenset({"handler"}),
                 departments=frozenset({phong}))


class DanhBaGia:
    def __init__(self, nguoi: list[Person] | None = None, loi: str | None = None):
        self.nguoi = nguoi or []
        self.loi = loi
        self.da_hoi: list[str] = []

    def department_members(self, department_code: str) -> list[Person]:
        self.da_hoi.append(department_code)
        if self.loi:
            raise DirectoryUnavailable(self.loi)
        return self.nguoi


def _danh_ba_cua(phong: str) -> DanhBaGia:
    """Phòng có hai người xử lý và một trưởng phòng — trưởng phòng không nhận việc."""
    return DanhBaGia([
        Person(_xu_ly(phong).id, "xu.ly.1", "Người Xử Lý 1", frozenset({"handler"})),
        Person(_xu_ly(phong, 2).id, "xu.ly.2", "Người Xử Lý 2", frozenset({"handler"})),
        Person(_truong_phong(phong).id, "truong.phong", "Dung Phạm", frozenset({"approver"})),
    ])


@pytest.fixture
def phong_khac(session, phong_ban) -> str:
    ma = session.scalars(
        select(Department.code)
        .where(Department.is_active, Department.code != phong_ban)
        .order_by(Department.display_order)
    ).first()
    if ma is None:
        pytest.skip("Cần ít nhất hai phòng ban đang hoạt động.")
    return ma


@pytest.fixture
def client(session, phong_ban):
    """Máy khách HTTP đổi được người gọi và danh bạ.

    Phần dựng cảnh phải `commit`, không dừng ở `flush` — lý do ở fixture cùng tên trong
    test_routes.py.
    """
    trang_thai = {"actor": _truong_phong(phong_ban), "danh_ba": _danh_ba_cua(phong_ban)}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: trang_thai["actor"]
    app.dependency_overrides[get_directory] = lambda: trang_thai["danh_ba"]
    with TestClient(app) as c:
        c.trang_thai = trang_thai
        yield c
    app.dependency_overrides.clear()


def _goi_bang(client, actor: Actor, danh_ba: DanhBaGia | None = None) -> None:
    client.trang_thai["actor"] = actor
    if danh_ba is not None:
        client.trang_thai["danh_ba"] = danh_ba


# ---------------------------------------------------------------------------
# Dựng hồ sơ ở từng trạng thái, qua đúng các cạnh hợp lệ
# ---------------------------------------------------------------------------


def _tao(session, tieu_de: str = "Máy in tầng ba kẹt giấy") -> Request:
    loai = session.scalars(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    return create_case(
        session, title=tieu_de, requester_id=NGUOI_GUI.id,
        requester_label=NGUOI_GUI.label, request_type_code=loai,
    )


def _cho_phong_nhan(session, phong: str, tieu_de: str = "Máy in tầng ba kẹt giấy") -> Request:
    ho_so = _tao(session, tieu_de)
    uu_tien = session.scalars(select(Priority.code).order_by(Priority.display_order)).first()
    perform_transition(session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
                       changes={"priority_code": uu_tien})
    perform_transition(session, case_id=ho_so.id, to_state="awaiting-acceptance",
                       actor=PHAN_LOAI, changes={"department_code": phong})
    return ho_so


def _dang_xu_ly(session, phong: str, tieu_de: str = "Máy in tầng ba kẹt giấy",
                giao_cho: Actor | None = None) -> Request:
    ho_so = _cho_phong_nhan(session, phong, tieu_de)
    perform_transition(
        session, case_id=ho_so.id, to_state="in-progress", actor=_truong_phong(phong),
        changes={"assignee_id": giao_cho.id} if giao_cho else None,
        assignee_label=giao_cho.name if giao_cho else None,
    )
    return ho_so


def _da_leo_thang(session, phong: str) -> Request:
    ho_so = _dang_xu_ly(session, phong, giao_cho=_xu_ly(phong))
    perform_transition(session, case_id=ho_so.id, to_state="escalated", actor=Actor.system())
    return ho_so


def _dem_nhom(client, duong_dan: str = "/department/queue") -> dict[str, int]:
    """Số hồ sơ của từng nhóm trong hàng đợi phòng ban, theo người đang gọi.

    Bài nào so số đếm thì so chênh lệch trước và sau, không so số tuyệt đối: cụm dùng để
    chạy bài có thể đã sẵn hồ sơ của phòng này từ lúc thử tay.
    """
    return {g["code"]: g["count"] for g in client.get(duong_dan).json()["groups"]}


def _canh_cua_vai_tro(session, rule_set, tu: str, vai_tro: str) -> set[str]:
    """Đáp án tra thẳng từ ma trận phân quyền."""
    return set(
        session.scalars(
            select(Transition.to_state)
            .join(TransitionRole, TransitionRole.transition_id == Transition.id)
            .where(
                Transition.rule_set_id == rule_set.id,
                Transition.from_state == tu,
                TransitionRole.role_code == vai_tro,
            )
        ).all()
    )


# ---------------------------------------------------------------------------
# Cửa
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nguoi", "vao_duoc"),
    [
        (NGUOI_GUI, False),
        (PHAN_LOAI, False),
        (Actor(id="kc-tp-99", roles=frozenset({"approver"})), False),  # chưa thuộc phòng nào
        ("truong-phong", True),
        ("xu-ly", True),
    ],
)
def test_cua_chi_mo_cho_nguoi_giao_va_nhan_viec_co_phong(client, rule_set, phong_ban, nguoi, vao_duoc):
    if nguoi == "truong-phong":
        nguoi = _truong_phong(phong_ban)
    elif nguoi == "xu-ly":
        nguoi = _xu_ly(phong_ban)
    _goi_bang(client, nguoi)
    assert client.get("/department/queue").status_code == (200 if vao_duoc else 403)


def test_me_bao_khong_gian_phong_ban(session, rule_set, phong_ban):
    assert "department" in me(_truong_phong(phong_ban), {}, session)["workspaces"]
    assert "department" in me(_xu_ly(phong_ban), {}, session)["workspaces"]
    chua_co_phong = Actor(id="kc-tp-99", roles=frozenset({"approver"}))
    assert "department" not in me(chua_co_phong, {}, session)["workspaces"]


# ---------------------------------------------------------------------------
# Hàng đợi
# ---------------------------------------------------------------------------


def test_nhom_hang_doi_suy_tu_bo_quy_tac(client, session, rule_set):
    vai_tro = vai_tro_giao_viec(session, rule_set.id) | vai_tro_nhan_viec(session, rule_set.id)
    mong_doi = set(
        session.scalars(
            select(Transition.from_state)
            .join(TransitionRole, TransitionRole.transition_id == Transition.id)
            .where(
                Transition.rule_set_id == rule_set.id,
                Transition.is_system.is_(False),
                TransitionRole.role_code.in_(vai_tro),
            )
        ).all()
    )
    nhom = {g["code"] for g in client.get("/department/queue").json()["groups"] if not g["watch_only"]}
    assert nhom == mong_doi


def test_nhom_theo_doi_suy_tu_bo_quy_tac(client, session, rule_set):
    """Nhóm chỉ để theo dõi (#99): trạng thái mà cạnh của phòng ban dẫn tới, không phải
    trạng thái kết thúc, và từ đó có đường quay về hàng đợi. Đáp án tra bằng truy vấn
    riêng trên ma trận phân quyền."""
    vai_tro = vai_tro_giao_viec(session, rule_set.id) | vai_tro_nhan_viec(session, rule_set.id)
    canh = session.execute(
        select(Transition.from_state, Transition.to_state, TransitionRole.role_code)
        .outerjoin(TransitionRole, TransitionRole.transition_id == Transition.id)
        .where(Transition.rule_set_id == rule_set.id, Transition.is_system.is_(False))
    ).all()
    hang_doi = {tu for tu, _, vai in canh if vai in vai_tro}
    dich = {den for tu, den, vai in canh if tu in hang_doi and vai in vai_tro} - hang_doi
    quay_ve = {tu for tu, den, _ in canh if den in hang_doi}
    ket_thuc = set(session.scalars(
        select(State.code).where(State.rule_set_id == rule_set.id, State.is_terminal)
    ).all())
    mong_doi = (dich & quay_ve) - ket_thuc

    nhom = client.get("/department/queue").json()["groups"]
    assert {g["code"] for g in nhom if g["watch_only"]} == mong_doi
    assert "awaiting-info" in mong_doi, "đúng trường hợp #99 phải có mặt"
    assert "rejected-by-department" not in mong_doi, "hồ sơ bị trả thuộc điều phối, không về phòng"


def test_ho_so_cho_bo_sung_van_hien_trong_hang_doi(client, session, rule_set, phong_ban, phong_khac):
    """Định nghĩa hoàn thành của #99: người xử lý hỏi thêm xong, hồ sơ vẫn nằm trong
    hàng đợi của họ — ở nhóm theo dõi, xếp sau việc phải làm, kể cả bộ lọc "của tôi"."""
    toi = _xu_ly(phong_ban)
    _goi_bang(client, toi)
    duong_dan_thu = ("/department/queue", "/department/queue?mine=true")
    truoc = {d: _dem_nhom(client, d)["awaiting-info"] for d in duong_dan_thu}
    dang_lam = _dang_xu_ly(session, phong_ban, "Việc đang làm", giao_cho=toi)
    cho_bo_sung = _dang_xu_ly(session, phong_ban, "Đã hỏi thêm", giao_cho=toi)
    perform_transition(session, case_id=cho_bo_sung.id, to_state="awaiting-info",
                       actor=toi, note="Máy nào, ở phòng nào?")
    # Quá hạn từ trước khi hỏi: thiếu quy tắc xếp nhóm theo dõi xuống sau thì hồ sơ này
    # sẽ nhảy lên đầu vì "quá hạn lên trước"
    cho_bo_sung.sla_running_seconds = gioi_han_giay(session, cho_bo_sung) + 60
    phong_kia = _dang_xu_ly(session, phong_khac, "Phòng khác hỏi thêm", giao_cho=_xu_ly(phong_khac))
    perform_transition(session, case_id=phong_kia.id, to_state="awaiting-info",
                       actor=_xu_ly(phong_khac), note="?")
    session.commit()

    for duong_dan in duong_dan_thu:
        than = client.get(duong_dan).json()
        ids = [m["id"] for m in than["items"]]
        assert cho_bo_sung.id in ids, duong_dan
        assert phong_kia.id not in ids, duong_dan
        assert ids.index(dang_lam.id) < ids.index(cho_bo_sung.id), "việc phải làm lên trước"
        nhom = next(g for g in than["groups"] if g["code"] == "awaiting-info")
        assert nhom["watch_only"] is True
        assert nhom["count"] == truoc[duong_dan] + 1, duong_dan

    assert client.get("/department/queue?state=awaiting-info").status_code == 200


def test_truong_phong_hoi_them_roi_ho_so_ve_lai_cho_nhan(client, session, rule_set, phong_ban):
    """#79: trưởng phòng hỏi thêm trước khi nhận việc. Trong lúc chờ, hồ sơ nằm ở nhóm
    theo dõi; người gửi trả lời xong thì hồ sơ về đúng hàng chờ nhận của phòng."""
    _goi_bang(client, _truong_phong(phong_ban))
    truoc = _dem_nhom(client)
    ho_so = _cho_phong_nhan(session, phong_ban)
    session.commit()

    hoi = next(
        c for c in client.get(f"/department/requests/{ho_so.id}").json()["allowed_transitions"]
        if c["to_state"] == "awaiting-info"
    )
    assert hoi["requires_note"] is True and hoi["note_label"]

    r = client.post(f"/department/requests/{ho_so.id}/transitions",
                    json={"to_state": "awaiting-info", "note": "Máy in tầng mấy?"})
    assert r.status_code == 200, r.text
    nhom = {g["code"]: g for g in client.get("/department/queue").json()["groups"]}
    assert nhom["awaiting-info"]["watch_only"] is True
    assert _dem_nhom(client) == {
        **truoc, "awaiting-info": truoc["awaiting-info"] + 1,
    }

    perform_transition(session, case_id=ho_so.id, to_state="awaiting-acceptance",
                       actor=NGUOI_GUI, note="Tầng ba.")
    session.commit()
    assert _dem_nhom(client) == {
        **truoc, "awaiting-acceptance": truoc["awaiting-acceptance"] + 1,
    }


def test_nguoi_xu_ly_tu_nhan_ho_so_chua_giao_ai(client, session, rule_set, phong_ban):
    """#127 nhìn từ buồng lái: nút tự nhận không có ô chọn người, giữ nguyên trạng thái;
    nhận xong thì hồ sơ vào bộ lọc "Giao cho tôi" và nút biến mất."""
    ho_so = _dang_xu_ly(session, phong_ban, "Chưa giao ai")
    session.commit()
    toi = _xu_ly(phong_ban)
    _goi_bang(client, toi)
    truoc = {m["id"] for m in client.get("/department/queue?mine=true").json()["items"]}
    assert ho_so.id not in truoc

    nhan = next(
        c for c in client.get(f"/department/requests/{ho_so.id}").json()["allowed_transitions"]
        if c["keeps_state"]
    )
    assert nhan["to_state"] == "in-progress" and nhan["fields"] == []

    r = client.post(f"/department/requests/{ho_so.id}/transitions",
                    json={"to_state": "in-progress"})
    assert r.status_code == 200, r.text
    than = r.json()
    assert than["state"]["code"] == "in-progress"
    assert than["assignee_id"] == toi.id
    assert than["assignee_label"] == "Người Xử Lý 1"
    assert not any(c["keeps_state"] for c in than["allowed_transitions"])
    sau = {m["id"] for m in client.get("/department/queue?mine=true").json()["items"]}
    assert ho_so.id in sau
    # Tự nhận không tra danh bạ: người được giao là chính người đã qua cửa phòng ban
    assert client.trang_thai["danh_ba"].da_hoi == []


def test_hang_doi_chi_co_ho_so_cua_phong_minh(client, session, rule_set, phong_ban, phong_khac):
    cua_minh = _cho_phong_nhan(session, phong_ban, "Hồ sơ của phòng mình")
    cua_nguoi = _cho_phong_nhan(session, phong_khac, "Hồ sơ của phòng khác")
    session.commit()

    than = client.get("/department/queue").json()
    ids = {m["id"] for m in than["items"]}

    assert cua_minh.id in ids
    assert cua_nguoi.id not in ids
    assert [p["code"] for p in than["departments"]] == [phong_ban]


def test_ho_so_qua_han_len_dau(client, session, rule_set, phong_ban):
    dung_han = _dang_xu_ly(session, phong_ban, "Còn trong hạn")
    qua_han = _dang_xu_ly(session, phong_ban, "Đã quá hạn")
    qua_han.sla_running_seconds = gioi_han_giay(session, qua_han) + 60
    session.commit()

    cac_muc = client.get("/department/queue?state=in-progress").json()["items"]
    thu_tu = [m["id"] for m in cac_muc if m["id"] in (dung_han.id, qua_han.id)]

    assert thu_tu == [qua_han.id, dung_han.id]
    assert next(m for m in cac_muc if m["id"] == qua_han.id)["sla_overdue"] is True


def test_loc_ho_so_giao_cho_toi(client, session, rule_set, phong_ban):
    toi = _xu_ly(phong_ban)
    cua_toi = _dang_xu_ly(session, phong_ban, "Giao cho tôi", giao_cho=toi)
    cua_nguoi_khac = _dang_xu_ly(session, phong_ban, "Giao cho người khác", giao_cho=_xu_ly(phong_ban, 2))
    session.commit()
    _goi_bang(client, toi)

    than = client.get("/department/queue?mine=true").json()
    ids = {m["id"] for m in than["items"]}

    assert cua_toi.id in ids and cua_nguoi_khac.id not in ids
    assert all(m["assigned_to_me"] for m in than["items"])
    assert sum(g["count"] for g in than["groups"]) == len(than["items"]), \
        "số đếm trên nút lọc phải đi theo cùng bộ lọc với danh sách"
    muc = next(m for m in than["items"] if m["id"] == cua_toi.id)
    assert muc["assignee_label"] == toi.name


# ---------------------------------------------------------------------------
# Hồ sơ của phòng khác
# ---------------------------------------------------------------------------


def test_nguoi_phong_khac_khong_xem_khong_thao_tac_duoc(client, session, rule_set, phong_ban, phong_khac):
    """Hồ sơ của phòng khác trả 404 ở cả hai cửa, để không ai dò được hồ sơ nào có thật."""
    ho_so = _cho_phong_nhan(session, phong_khac)
    session.commit()

    assert client.get(f"/department/requests/{ho_so.id}").status_code == 404
    r = client.post(f"/department/requests/{ho_so.id}/transitions", json={"to_state": "in-progress"})
    assert r.status_code == 404
    session.refresh(ho_so)
    assert ho_so.current_state == "awaiting-acceptance"


# ---------------------------------------------------------------------------
# Nút bấm
# ---------------------------------------------------------------------------


def test_nut_bam_khop_ma_tran_phan_quyen(client, session, rule_set, phong_ban):
    cho_nhan = _cho_phong_nhan(session, phong_ban, "Chờ nhận")
    dang_lam = _dang_xu_ly(session, phong_ban, "Đang làm")
    session.commit()

    def nut(ho_so) -> set[str]:
        r = client.get(f"/department/requests/{ho_so.id}")
        assert r.status_code == 200
        return {c["to_state"] for c in r.json()["allowed_transitions"]}

    _goi_bang(client, _truong_phong(phong_ban))
    assert nut(cho_nhan) == _canh_cua_vai_tro(session, rule_set, "awaiting-acceptance", "approver")
    assert nut(dang_lam) == _canh_cua_vai_tro(session, rule_set, "in-progress", "approver")

    _goi_bang(client, _xu_ly(phong_ban))
    assert nut(cho_nhan) == _canh_cua_vai_tro(session, rule_set, "awaiting-acceptance", "handler")
    assert nut(dang_lam) == _canh_cua_vai_tro(session, rule_set, "in-progress", "handler")


# ---------------------------------------------------------------------------
# Giao việc — người được giao phải đi qua danh bạ
# ---------------------------------------------------------------------------


def test_nhan_viec_va_giao_nguoi(client, session, rule_set, phong_ban):
    ho_so = _cho_phong_nhan(session, phong_ban)
    session.commit()
    nguoi = _xu_ly(phong_ban)

    r = client.post(f"/department/requests/{ho_so.id}/transitions",
                    json={"to_state": "in-progress", "changes": {"assignee_id": nguoi.id}})

    assert r.status_code == 200, r.text
    than = r.json()
    assert than["state"]["code"] == "in-progress"
    assert than["assignee_id"] == nguoi.id, "ghi xuống là định danh, không phải tên"
    assert than["assignee_label"] == "Người Xử Lý 1", "tên lấy từ danh bạ"
    assert client.trang_thai["danh_ba"].da_hoi == [phong_ban]


@pytest.mark.parametrize("ai", ["kc-tp-01", "ai-do-bia-ra"])
def test_giao_cho_nguoi_khong_nhan_duoc_viec_bi_tu_choi(client, session, rule_set, phong_ban, ai):
    """Trưởng phòng có trong danh bạ nhưng không nhận việc; chuỗi bịa thì không có ở đâu."""
    ho_so = _cho_phong_nhan(session, phong_ban)
    session.commit()

    r = client.post(f"/department/requests/{ho_so.id}/transitions",
                    json={"to_state": "in-progress", "changes": {"assignee_id": ai}})

    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "invalid-field-value"
    session.refresh(ho_so)
    assert ho_so.current_state == "awaiting-acceptance"
    assert ho_so.assignee_id is None


def test_danh_ba_hong_thi_khong_giao_duoc_nhung_van_nhan_duoc(client, session, rule_set, phong_ban):
    ho_so = _cho_phong_nhan(session, phong_ban)
    session.commit()
    _goi_bang(client, _truong_phong(phong_ban), DanhBaGia(loi="Không gọi được Keycloak"))

    r = client.post(f"/department/requests/{ho_so.id}/transitions",
                    json={"to_state": "in-progress", "changes": {"assignee_id": _xu_ly(phong_ban).id}})
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "directory-unavailable"
    session.refresh(ho_so)
    assert ho_so.current_state == "awaiting-acceptance"

    r = client.post(f"/department/requests/{ho_so.id}/transitions", json={"to_state": "in-progress"})
    assert r.status_code == 200, "không chọn người thì không cần danh bạ"
    assert r.json()["assignee_id"] is None


def test_loi_quyen_that_khong_bi_loi_danh_ba_che_mat(client, session, rule_set, phong_ban):
    """Người xử lý thử nhận việc kèm người được giao, lúc danh bạ đang hỏng: phải nhận
    403 của engine, không phải 503 — và danh bạ không bị hỏi tới."""
    ho_so = _cho_phong_nhan(session, phong_ban)
    session.commit()
    danh_ba = DanhBaGia(loi="Không gọi được Keycloak")
    _goi_bang(client, _xu_ly(phong_ban), danh_ba)

    r = client.post(f"/department/requests/{ho_so.id}/transitions",
                    json={"to_state": "in-progress", "changes": {"assignee_id": _xu_ly(phong_ban).id}})

    assert r.status_code == 403
    assert danh_ba.da_hoi == []


def test_dieu_phoi_kiem_giao_viec_khong_vong_qua_danh_ba_duoc(client, session, rule_set, phong_ban):
    """Một người mang cả vai trò điều phối lẫn trưởng phòng đi được cạnh nhận việc qua
    cửa điều phối. Cửa đó cũng phải kiểm người được giao."""
    ho_so = _cho_phong_nhan(session, phong_ban)
    session.commit()
    hai_vai = Actor(id="kc-hai-vai", roles=frozenset({"classifier", "approver"}),
                    departments=frozenset({phong_ban}))
    _goi_bang(client, hai_vai)

    r = client.post(f"/coordination/requests/{ho_so.id}/transitions",
                    json={"to_state": "in-progress", "changes": {"assignee_id": "ai-do-bia-ra"}})

    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "invalid-field-value"


def test_nguoi_phong_khac_khong_dung_duoc_danh_ba_de_do_nguoi(
    client, session, rule_set, phong_ban, phong_khac
):
    """Trưởng phòng khác kiêm điều phối, gửi người được giao qua cửa điều phối: engine
    phải chặn bằng ràng buộc phòng ban, và danh bạ không được hỏi — không thì lời đáp
    422 hay 200 sẽ tiết lộ ai thuộc phòng nào."""
    ho_so = _cho_phong_nhan(session, phong_ban)
    session.commit()
    danh_ba = _danh_ba_cua(phong_ban)
    hai_vai_phong_khac = Actor(id="kc-hai-vai", roles=frozenset({"classifier", "approver"}),
                               departments=frozenset({phong_khac}))
    _goi_bang(client, hai_vai_phong_khac, danh_ba)

    r = client.post(f"/coordination/requests/{ho_so.id}/transitions",
                    json={"to_state": "in-progress", "changes": {"assignee_id": _xu_ly(phong_ban).id}})

    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "guard-violation"
    assert danh_ba.da_hoi == []


def test_dong_ho_chi_khoi_dong_khi_phong_ban_nhan_viec(client, session, rule_set, phong_ban):
    """Cờ `sla_started` cho giao diện biết có được nói "còn …" hay chưa (#97): trước khi
    phòng nhận việc thì hạn chưa đếm, dù hồ sơ đã có ngưỡng từ lúc phân loại."""
    ho_so = _cho_phong_nhan(session, phong_ban)
    session.commit()

    truoc = client.get(f"/department/requests/{ho_so.id}").json()
    assert truoc["sla_limit_seconds"] is not None
    assert truoc["sla_started"] is False

    sau = client.post(f"/department/requests/{ho_so.id}/transitions",
                      json={"to_state": "in-progress"}).json()
    assert sau["sla_started"] is True

    _goi_bang(client, _xu_ly(phong_ban))
    xong = client.post(f"/department/requests/{ho_so.id}/transitions",
                       json={"to_state": "completed"}).json()
    assert (xong["sla_started"], xong["sla_paused"]) == (True, True), \
        "hoàn tất thì đồng hồ đứng, nhưng vẫn là đồng hồ đã khởi động"


def test_ho_so_dong_xu_ly_ngoai_gio_van_la_da_khoi_dong(session, rule_set, phong_ban):
    """Hồ sơ đã đóng mất mốc đoạn đang mở; xử lý trọn ngoài giờ làm việc thì số giây đã chạy là 0 — cổng từng
    ghi "Đồng hồ xử lý chưa từng chạy" (#557). Đã từng vào trạng thái đếm giờ thì vẫn là đã khởi động; hủy
    trước khi phòng nhận thì không."""
    from app.rules.sla import da_khoi_dong

    ho_so = _dang_xu_ly(session, phong_ban, giao_cho=_xu_ly(phong_ban))
    perform_transition(session, case_id=ho_so.id, to_state="completed", actor=_xu_ly(phong_ban))
    perform_transition(session, case_id=ho_so.id, to_state="closed", actor=NGUOI_GUI)
    ho_so.sla_running_seconds = 0  # như xử lý trọn ngoài giờ làm việc
    session.flush()
    assert ho_so.sla_segment_since is None
    assert da_khoi_dong(session, ho_so) is True

    huy = _tao(session, "Hủy trước khi phòng nhận")
    perform_transition(session, case_id=huy.id, to_state="cancelled", actor=NGUOI_GUI)
    assert da_khoi_dong(session, huy) is False


# ---------------------------------------------------------------------------
# Leo thang và phân công lại
# ---------------------------------------------------------------------------


def test_phan_cong_lai_khong_doi_duoc_phong_ban(client, session, rule_set, phong_ban, phong_khac):
    ho_so = _da_leo_thang(session, phong_ban)
    session.commit()

    r = client.post(f"/department/requests/{ho_so.id}/transitions",
                    json={"to_state": "in-progress", "changes": {"department_code": phong_khac}})

    assert r.status_code == 422
    session.refresh(ho_so)
    assert ho_so.current_state == "escalated"
    assert ho_so.department_code == phong_ban


def test_phan_cong_lai_cho_nguoi_khac_doi_ca_ten(client, session, rule_set, phong_ban):
    ho_so = _da_leo_thang(session, phong_ban)
    session.commit()
    nguoi_moi = _xu_ly(phong_ban, 2)

    r = client.post(f"/department/requests/{ho_so.id}/transitions",
                    json={"to_state": "in-progress", "changes": {"assignee_id": nguoi_moi.id}})

    assert r.status_code == 200, r.text
    assert (r.json()["assignee_id"], r.json()["assignee_label"]) == (nguoi_moi.id, "Người Xử Lý 2")


# ---------------------------------------------------------------------------
# Thao tác không hoàn tác được (#98)
# ---------------------------------------------------------------------------


def test_moi_canh_bao_dung_trang_thai_dich_co_phai_ket_thuc(client, session, rule_set, phong_ban):
    """Giao diện hỏi lại trước thao tác không hoàn tác được dựa vào cờ này — nên nó phải
    khớp cột `states.is_terminal`, ở cả cổng người gửi lẫn buồng lái."""
    ket_thuc = dict(
        session.execute(
            select(State.code, State.is_terminal).where(State.rule_set_id == rule_set.id)
        ).all()
    )
    ho_so = _tao(session)
    uu_tien = session.scalars(select(Priority.code).order_by(Priority.display_order)).first()
    perform_transition(session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
                       changes={"priority_code": uu_tien})
    session.commit()

    da_thay_ket_thuc = False
    for actor, duong_dan in [
        (PHAN_LOAI, f"/coordination/requests/{ho_so.id}"),
        (NGUOI_GUI, f"/requests/{ho_so.id}"),
    ]:
        _goi_bang(client, actor)
        for canh in client.get(duong_dan).json()["allowed_transitions"]:
            assert canh["to_state_is_terminal"] is ket_thuc[canh["to_state"]], canh["to_state"]
            da_thay_ket_thuc |= canh["to_state_is_terminal"]
    assert da_thay_ket_thuc, "ở Đã phân loại phải có ít nhất một cạnh kết thúc để bài có nghĩa"


@pytest.mark.parametrize("ly_do", ["Gửi nhầm, đã tự sửa được máy", None])
def test_huy_kem_ly_do_tuy_chon(client, session, rule_set, ly_do):
    """Lý do khi hủy là tùy chọn: ghi thì vào nhật ký, bỏ trống vẫn hủy được."""
    ho_so = _tao(session)
    session.commit()
    _goi_bang(client, NGUOI_GUI)

    r = client.post(f"/requests/{ho_so.id}/transitions",
                    json={"to_state": "cancelled", "note": ly_do})

    assert r.status_code == 200, r.text
    assert r.json()["state"]["is_terminal"] is True
    assert r.json()["history"][-1]["note"] == ly_do


# ---------------------------------------------------------------------------
# Nhật ký giữ lịch sử thay đổi của trường quyết định (#100)
# ---------------------------------------------------------------------------


def _hai_loai(session) -> tuple[RequestType, RequestType]:
    cac_loai = session.scalars(
        select(RequestType).where(RequestType.is_active).order_by(RequestType.display_order)
    ).all()
    if len(cac_loai) < 2:
        pytest.skip("Cần ít nhất hai loại yêu cầu đang hoạt động.")
    return cac_loai[0], cac_loai[1]


def _moc_cuoi(session, ho_so) -> EventLog:
    return session.scalars(
        select(EventLog).where(EventLog.case_id == ho_so.id).order_by(EventLog.id.desc())
    ).first()


def test_sua_loai_yeu_cau_ghi_ca_gia_tri_cu_lan_moi(session, rule_set):
    """Đúng tình huống của #100: người gửi chọn loại A, điều phối sửa sang B. Hồ sơ mang
    B, nhật ký giữ "A → B" — không còn ghi đè mất dấu."""
    a, b = _hai_loai(session)
    ho_so = _tao(session)
    assert ho_so.request_type_code == a.code
    uu_tien = session.scalars(select(Priority.code).order_by(Priority.display_order)).first()

    perform_transition(session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
                       changes={"priority_code": uu_tien, "request_type_code": b.code})

    assert ho_so.request_type_code == b.code
    assert _moc_cuoi(session, ho_so).changes == {
        "priority_code": {"from": None, "to": uu_tien},
        "request_type_code": {"from": a.code, "to": b.code},
    }


def test_giu_nguyen_gia_tri_thi_khong_ghi_thay_doi(session, rule_set, phong_ban):
    """Gửi lại đúng giá trị đang có không sinh ra dòng "A → A"; không đổi gì thì cột rỗng."""
    a, _ = _hai_loai(session)
    ho_so = _tao(session)
    uu_tien = session.scalars(select(Priority.code).order_by(Priority.display_order)).first()
    perform_transition(session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
                       changes={"priority_code": uu_tien, "request_type_code": a.code})
    assert set(_moc_cuoi(session, ho_so).changes) == {"priority_code"}

    perform_transition(session, case_id=ho_so.id, to_state="awaiting-acceptance",
                       actor=PHAN_LOAI, changes={"department_code": phong_ban})
    perform_transition(session, case_id=ho_so.id, to_state="in-progress",
                       actor=_truong_phong(phong_ban))
    assert _moc_cuoi(session, ho_so).changes is None


def test_doi_phong_sau_khi_bi_tra_ghi_ca_hai_phong(session, rule_set, phong_ban, phong_khac):
    """Hồ sơ bị phòng A trả, điều phối chọn lại phòng B: nhật ký ghi "phòng: A → B"."""
    ho_so = _cho_phong_nhan(session, phong_ban)
    perform_transition(session, case_id=ho_so.id, to_state="rejected-by-department",
                       actor=_truong_phong(phong_ban), note="Sai chuyên môn")
    perform_transition(session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI)
    perform_transition(session, case_id=ho_so.id, to_state="awaiting-acceptance",
                       actor=PHAN_LOAI, changes={"department_code": phong_khac})

    assert _moc_cuoi(session, ho_so).changes == {
        "department_code": {"from": phong_ban, "to": phong_khac}
    }


def test_doi_nguoi_xu_ly_ghi_ca_ten_luc_doi(session, rule_set, phong_ban):
    """Định danh Keycloak không tự nói lên người nào — nhật ký ghi kèm tên cũ và mới."""
    cu, moi = _xu_ly(phong_ban), _xu_ly(phong_ban, 2)
    ho_so = _dang_xu_ly(session, phong_ban, giao_cho=cu)
    assert _moc_cuoi(session, ho_so).changes == {
        "assignee_id": {"from": None, "to": cu.id, "from_label": None, "to_label": cu.name}
    }

    perform_transition(session, case_id=ho_so.id, to_state="escalated", actor=Actor.system())
    perform_transition(session, case_id=ho_so.id, to_state="in-progress",
                       actor=_truong_phong(phong_ban), changes={"assignee_id": moi.id},
                       assignee_label=moi.name)
    assert _moc_cuoi(session, ho_so).changes == {
        "assignee_id": {"from": cu.id, "to": moi.id, "from_label": cu.name, "to_label": moi.name}
    }


def test_dong_thoi_gian_hien_thay_doi_kem_nhan(client, session, rule_set):
    """Người gửi đọc được loại của mình đã được sửa thành gì — bằng tên, không bằng mã,
    kể cả khi loại cũ về sau bị gỡ khỏi danh mục."""
    a, b = _hai_loai(session)
    ho_so = _tao(session)
    uu_tien = session.get(Priority, session.scalars(
        select(Priority.code).order_by(Priority.display_order)).first())
    perform_transition(session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
                       changes={"priority_code": uu_tien.code, "request_type_code": b.code})
    a.is_active = False
    session.commit()
    _goi_bang(client, NGUOI_GUI)

    moc = client.get(f"/requests/{ho_so.id}").json()["history"][0]
    thay_doi = {t["field"]: t for t in moc["changes"]}

    assert thay_doi["request_type_code"] == {
        "field": "request_type_code",
        "before": {"code": a.code, "label": a.label},
        "after": {"code": b.code, "label": b.label},
    }
    assert thay_doi["priority_code"]["before"] is None
    assert thay_doi["priority_code"]["after"] == {"code": uu_tien.code, "label": uu_tien.label}


# ---------------------------------------------------------------------------
# Trọn vòng qua ba buồng lái
# ---------------------------------------------------------------------------


def test_tron_vong_tu_luc_gui_toi_luc_dong(client, session, rule_set, phong_ban):
    """Định nghĩa hoàn thành của #83 ở tầng dịch vụ: một hồ sơ đi hết vòng đời qua cổng
    người gửi, buồng lái điều phối và buồng lái phòng ban, không bước nào gọi engine
    trực tiếp."""
    loai = session.scalars(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    uu_tien = session.scalars(select(Priority.code).order_by(Priority.display_order)).first()
    nguoi_xu_ly = _xu_ly(phong_ban)

    def buoc(actor, duong_dan, than, mong_doi=200):
        _goi_bang(client, actor)
        r = client.post(duong_dan, json=than)
        assert r.status_code == mong_doi, (duong_dan, r.text)
        return r.json()

    mau = next(l for l in client.get("/request-types").json() if l["code"] == loai)
    ho_so = buoc(NGUOI_GUI, "/requests",
                 {"title": "Laptop không nhận sạc", "request_type_code": loai,
                  "details": chi_tiet_mau(mau)}, 201)
    ma = ho_so["id"]
    buoc(PHAN_LOAI, f"/coordination/requests/{ma}/transitions",
         {"to_state": "classified", "changes": {"priority_code": uu_tien}})
    buoc(PHAN_LOAI, f"/coordination/requests/{ma}/transitions",
         {"to_state": "awaiting-acceptance", "changes": {"department_code": phong_ban}})
    buoc(_truong_phong(phong_ban), f"/department/requests/{ma}/transitions",
         {"to_state": "in-progress", "changes": {"assignee_id": nguoi_xu_ly.id}})
    buoc(nguoi_xu_ly, f"/department/requests/{ma}/transitions", {"to_state": "completed"})
    cuoi = buoc(NGUOI_GUI, f"/requests/{ma}/transitions", {"to_state": "closed"})

    assert cuoi["state"]["code"] == "closed"
    assert [e["to_state"] for e in cuoi["history"]] == [
        "classified", "awaiting-acceptance", "in-progress", "completed", "closed",
    ]
    session.expire_all()
    assert session.get(Request, ma).assignee_label == "Người Xử Lý 1"
