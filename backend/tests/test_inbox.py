# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử hộp thư chung (#155).
#
# Ba điều phải canh bằng kiểm thử:
#
#   Phạm vi  — chỉ hồ sơ người này mở được VÀ đang giữ việc (navigator chốt 05/10/2026):
#              người gửi thấy hồ sơ của mình, phòng ban thấy hồ sơ của phòng — kể cả người
#              mới được giao lại —, điều phối thấy hồ sơ ở hàng đợi điều phối và hồ sơ mình
#              đã nhắn. Phòng khác không thấy (như E7, I4 của kịch bản kiểm thử).
#   Đã đọc  — tin của chính mình không bao giờ chưa đọc; mốc chỉ dời lên.
#   ADR-0005 — đánh dấu đã đọc không đổi hồ sơ: không chạm dòng `requests`, không ghi
#              `event_log`.

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app.auth.dependencies import current_actor
from app.db import get_session
from app.main import app
from app.models.case import CaseMessageRead, EventLog, Request
from app.models.workflow_config import Department, MessageKind, Priority, RequestType
from app.workflow.context import Actor
from app.workflow.engine import create_case, perform_transition
from app.workflow.messages import gui_loi_nhan

NGUOI_GUI = Actor(id="kc-gui-01", name="An Nguyễn", roles=frozenset({"requester"}))
NGUOI_GUI_KHAC = Actor(id="kc-gui-02", name="Chi Lê", roles=frozenset({"requester"}))
PHAN_LOAI = Actor(id="kc-pl-01", name="Bình Trần", roles=frozenset({"classifier"}))


def _truong_phong(phong: str) -> Actor:
    return Actor(id="kc-tp-01", name="Dung Phạm", roles=frozenset({"approver"}),
                 departments=frozenset({phong}))


def _xu_ly(phong: str, so: int = 1) -> Actor:
    return Actor(id=f"kc-xl-0{so}", name=f"Người xử lý {so}", roles=frozenset({"handler"}),
                 departments=frozenset({phong}))


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
def loai_thuong(session) -> MessageKind:
    """Loại lời nhắn hai chiều: không cờ nào thu hẹp, không luật hỏi lại."""
    loai = session.scalars(
        select(MessageKind)
        .where(
            MessageKind.owner_only.is_(False),
            MessageKind.department_stage_only.is_(False),
            MessageKind.reask_after_hours.is_(None),
        )
        .order_by(MessageKind.display_order)
    ).first()
    if loai is None:
        pytest.skip("Dữ liệu khởi tạo chưa khai loại lời nhắn thường.")
    return loai


@pytest.fixture
def client(session, phong_ban):
    """Máy khách HTTP đổi được người gọi. Phần dựng cảnh phải `commit`."""
    trang_thai = {"actor": NGUOI_GUI}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: trang_thai["actor"]
    with TestClient(app) as c:
        c.trang_thai = trang_thai
        yield c
    app.dependency_overrides.clear()


def _goi(client, actor: Actor, phuong_thuc: str, duong: str):
    client.trang_thai["actor"] = actor
    return getattr(client, phuong_thuc)(duong)


def _tao(session, nguoi_gui: Actor = NGUOI_GUI) -> Request:
    loai = session.scalars(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    return create_case(
        session, title="Máy in tầng ba kẹt giấy", requester_id=nguoi_gui.id,
        requester_label=nguoi_gui.label, request_type_code=loai,
    )


def _dang_xu_ly(session, phong: str) -> Request:
    ho_so = _tao(session)
    uu_tien = session.scalars(select(Priority.code).order_by(Priority.display_order)).first()
    perform_transition(session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
                       changes={"priority_code": uu_tien})
    perform_transition(session, case_id=ho_so.id, to_state="awaiting-acceptance",
                       actor=PHAN_LOAI, changes={"department_code": phong})
    perform_transition(session, case_id=ho_so.id, to_state="in-progress",
                       actor=_truong_phong(phong))
    return ho_so


def _nhan(session, ho_so: Request, actor: Actor, loai: MessageKind, noi_dung: str) -> None:
    gui_loi_nhan(session, ho_so, actor, loai.code, noi_dung)


def _cuoc(client, actor: Actor) -> dict[int, dict]:
    tra_ve = _goi(client, actor, "get", "/inbox")
    assert tra_ve.status_code == 200
    return {c["case_id"]: c for c in tra_ve.json()["items"]}


# ---------------------------------------------------------------------------
# Phạm vi
# ---------------------------------------------------------------------------


def test_nguoi_gui_chi_thay_ho_so_cua_minh(client, session, rule_set, phong_ban, loai_thuong):
    cua_an = _dang_xu_ly(session, phong_ban)
    _nhan(session, cua_an, NGUOI_GUI, loai_thuong, "Máy in ở tầng ba")
    session.commit()

    assert cua_an.id in _cuoc(client, NGUOI_GUI)
    assert cua_an.id not in _cuoc(client, NGUOI_GUI_KHAC)
    assert _cuoc(client, NGUOI_GUI)[cua_an.id]["workspace"] == "portal"


def test_ho_so_chua_co_loi_nhan_khong_thanh_cuoc_tro_chuyen(client, session, rule_set,
                                                          phong_ban, loai_thuong):
    ho_so = _dang_xu_ly(session, phong_ban)
    session.commit()
    assert ho_so.id not in _cuoc(client, NGUOI_GUI)
    assert ho_so.id not in _cuoc(client, _xu_ly(phong_ban))


def test_nguoi_moi_trong_phong_doc_duoc_trao_doi_cu(client, session, rule_set, phong_ban,
                                                    loai_thuong):
    """Định nghĩa hoàn thành của #155: người xử lý mới được giao lại hồ sơ thấy đủ tin cũ
    giữa người gửi và người xử lý trước."""
    ho_so = _dang_xu_ly(session, phong_ban)
    _nhan(session, ho_so, NGUOI_GUI, loai_thuong, "Chiều nay em cần in hợp đồng")
    _nhan(session, ho_so, _xu_ly(phong_ban, 1), loai_thuong, "Em đang thay trục kéo giấy")
    session.commit()

    nguoi_moi = _xu_ly(phong_ban, 2)
    cuoc = _cuoc(client, nguoi_moi)
    assert ho_so.id in cuoc
    assert cuoc[ho_so.id]["workspace"] == "department"
    assert cuoc[ho_so.id]["unread"] == 2


def test_phong_khac_khong_thay(client, session, rule_set, phong_ban, phong_khac, loai_thuong):
    ho_so = _dang_xu_ly(session, phong_ban)
    _nhan(session, ho_so, NGUOI_GUI, loai_thuong, "Máy in ở tầng ba")
    session.commit()

    nguoi_phong_khac = _xu_ly(phong_khac)
    assert ho_so.id not in _cuoc(client, nguoi_phong_khac)
    assert _goi(client, nguoi_phong_khac, "get", "/inbox/unread").json()["unread"] == 0
    assert _goi(client, nguoi_phong_khac, "post", f"/inbox/{ho_so.id}/read").status_code == 404


def test_dieu_phoi_chi_thay_ho_so_dang_giu_viec(client, session, rule_set, phong_ban,
                                                loai_thuong):
    """Điều phối viên mở được mọi hồ sơ, nhưng hộp thư chỉ có hồ sơ ở hàng đợi điều phối
    và hồ sơ họ đã nhắn — không phải chuyện máy in giữa người gửi và phòng ban."""
    moi_gui = _tao(session)
    _nhan(session, moi_gui, NGUOI_GUI, loai_thuong, "Hồ sơ gấp")
    o_phong = _dang_xu_ly(session, phong_ban)
    _nhan(session, o_phong, NGUOI_GUI, loai_thuong, "Máy in ở tầng ba")
    session.commit()

    cuoc = _cuoc(client, PHAN_LOAI)
    assert moi_gui.id in cuoc
    assert cuoc[moi_gui.id]["workspace"] == "coordination"
    assert o_phong.id not in cuoc

    # Điều phối viên nhắn vào thì hồ sơ vào hộp thư của họ
    _nhan(session, o_phong, PHAN_LOAI, loai_thuong, "Đã nhắc phòng")
    session.commit()
    assert o_phong.id in _cuoc(client, PHAN_LOAI)


# ---------------------------------------------------------------------------
# Đã đọc
# ---------------------------------------------------------------------------


def test_tin_cua_minh_khong_tinh_chua_doc(client, session, rule_set, phong_ban, loai_thuong):
    ho_so = _dang_xu_ly(session, phong_ban)
    _nhan(session, ho_so, NGUOI_GUI, loai_thuong, "Máy in ở tầng ba")
    session.commit()

    assert _cuoc(client, NGUOI_GUI)[ho_so.id]["unread"] == 0
    assert _cuoc(client, _xu_ly(phong_ban))[ho_so.id]["unread"] == 1


def test_danh_dau_da_doc_roi_tin_moi_lai_dem(client, session, rule_set, phong_ban, loai_thuong):
    ho_so = _dang_xu_ly(session, phong_ban)
    xu_ly = _xu_ly(phong_ban)
    session.commit()
    # Cụm có thể còn hồ sơ khác của phòng đang có lời nhắn: so chênh lệch, không so số tuyệt đối
    truoc = _goi(client, xu_ly, "get", "/inbox/unread").json()["unread"]
    _nhan(session, ho_so, NGUOI_GUI, loai_thuong, "Máy in ở tầng ba")
    _nhan(session, ho_so, NGUOI_GUI, loai_thuong, "Chiều nay em cần in")
    session.commit()

    assert _goi(client, xu_ly, "get", "/inbox/unread").json()["unread"] == truoc + 2
    # Con số trên thanh bên bằng tổng số chưa đọc của danh sách
    assert _goi(client, xu_ly, "get", "/inbox").json()["unread"] == truoc + 2
    assert _goi(client, xu_ly, "post", f"/inbox/{ho_so.id}/read").status_code == 204
    assert _cuoc(client, xu_ly)[ho_so.id]["unread"] == 0
    assert _goi(client, xu_ly, "get", "/inbox/unread").json()["unread"] == truoc

    _nhan(session, ho_so, NGUOI_GUI, loai_thuong, "Anh ơi gấp lắm")
    session.commit()
    assert _cuoc(client, xu_ly)[ho_so.id]["unread"] == 1
    # Người khác trong phòng chưa đọc gì: vẫn thấy đủ ba tin
    assert _cuoc(client, _xu_ly(phong_ban, 2))[ho_so.id]["unread"] == 3


def test_danh_dau_luon_toi_tin_moi_nhat(client, session, rule_set, phong_ban, loai_thuong):
    ho_so = _dang_xu_ly(session, phong_ban)
    xu_ly = _xu_ly(phong_ban)
    _nhan(session, ho_so, NGUOI_GUI, loai_thuong, "Máy in ở tầng ba")
    _nhan(session, ho_so, NGUOI_GUI, loai_thuong, "Chiều nay em cần in")
    session.commit()
    cac_id = session.scalars(
        text("SELECT id FROM case_messages WHERE case_id = :c ORDER BY id"), {"c": ho_so.id}
    ).all()

    _goi(client, xu_ly, "post", f"/inbox/{ho_so.id}/read")
    assert session.get(CaseMessageRead, (ho_so.id, xu_ly.id)).last_read_id == cac_id[-1]

    # Mốc đang thấp (chỉ đọc tới tin đầu) thì lần đánh dấu sau đưa nó lên tin mới nhất
    session.execute(
        text("UPDATE case_message_reads SET last_read_id = :m WHERE case_id = :c AND reader = :r"),
        {"m": cac_id[0], "c": ho_so.id, "r": xu_ly.id},
    )
    session.commit()
    assert _cuoc(client, xu_ly)[ho_so.id]["unread"] == 1
    _goi(client, xu_ly, "post", f"/inbox/{ho_so.id}/read")
    session.expire_all()
    assert session.get(CaseMessageRead, (ho_so.id, xu_ly.id)).last_read_id == cac_id[-1]


def test_dang_cho_toi(client, session, rule_set, phong_ban, loai_thuong):
    ho_so = _dang_xu_ly(session, phong_ban)
    _nhan(session, ho_so, NGUOI_GUI, loai_thuong, "Máy in ở tầng ba")
    session.commit()
    assert _cuoc(client, _xu_ly(phong_ban))[ho_so.id]["waiting_on_me"] is True
    assert _cuoc(client, NGUOI_GUI)[ho_so.id]["waiting_on_me"] is False

    _nhan(session, ho_so, _xu_ly(phong_ban), loai_thuong, "Chiều nay em qua")
    session.commit()
    assert _cuoc(client, _xu_ly(phong_ban))[ho_so.id]["waiting_on_me"] is False
    assert _cuoc(client, NGUOI_GUI)[ho_so.id]["waiting_on_me"] is True
    # Người xử lý khác trong phòng: tin cuối là của nhân viên, không ai chờ họ
    assert _cuoc(client, _xu_ly(phong_ban, 2))[ho_so.id]["waiting_on_me"] is False


# ---------------------------------------------------------------------------
# ADR-0005: đánh dấu đã đọc không đổi hồ sơ
# ---------------------------------------------------------------------------


def test_danh_dau_da_doc_khong_cham_ho_so_khong_ghi_nhat_ky(client, session, rule_set,
                                                            phong_ban, loai_thuong):
    ho_so = _dang_xu_ly(session, phong_ban)
    _nhan(session, ho_so, NGUOI_GUI, loai_thuong, "Máy in ở tầng ba")
    session.commit()

    truoc = dict(session.execute(
        text("SELECT ctid::text AS vi_tri, * FROM requests WHERE id = :id"), {"id": ho_so.id}
    ).mappings().one())
    so_moc = session.scalar(select(func.count()).where(EventLog.case_id == ho_so.id))

    assert _goi(client, _xu_ly(phong_ban), "post", f"/inbox/{ho_so.id}/read").status_code == 204

    session.expire_all()
    sau = dict(session.execute(
        text("SELECT ctid::text AS vi_tri, * FROM requests WHERE id = :id"), {"id": ho_so.id}
    ).mappings().one())
    assert sau == truoc
    assert session.scalar(select(func.count()).where(EventLog.case_id == ho_so.id)) == so_moc
