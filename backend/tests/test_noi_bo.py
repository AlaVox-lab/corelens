# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử trò chuyện nội bộ giữa nhân viên (#156).
#
# Định nghĩa hoàn thành: Bình Trần nhắn nội bộ "phòng chị nhận hồ sơ này không?", Dung
# Phạm thấy và trả lời được trong hộp thư; An Nguyễn — người gửi hồ sơ — không thấy hai tin
# đó ở trang hồ sơ, hộp thư hay BẤT KỲ điểm cuối nào. Bài quét dưới đây gọi mọi điểm cuối
# GET của dịch vụ với tư cách người gửi, nên điểm cuối mới thêm sau này cũng bị canh.
#
# Ràng buộc theo HỒ SƠ, không theo vai trò: điều phối viên mở hồ sơ chính mình gửi cũng
# không thấy tin nội bộ của hồ sơ đó. Tin nội bộ không làm lệch các luật của lời nhắn
# thường: "ai nhắn sau cùng", luật hỏi lại của "Hỏi tiến độ", "đang chờ bạn".

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.dependencies import current_actor
from app.db import get_session
from app.main import app
from app.models.case import Request
from app.models.workflow_config import MessageKind, Priority, RequestType
from app.workflow.context import Actor
from app.workflow.engine import create_case, perform_transition
from app.workflow.messages import MessageRejected, gui_loi_nhan

NGUOI_GUI = Actor(id="nb-gui-01", name="An Nguyễn", roles=frozenset({"requester"}))
PHAN_LOAI = Actor(id="nb-pl-01", name="Bình Trần", roles=frozenset({"classifier"}))
PHAN_LOAI_KHAC = Actor(id="nb-pl-02", name="Giang Đỗ", roles=frozenset({"classifier"}))
# Bình Trần vừa gửi yêu cầu vừa điều phối — như tài khoản mẫu binh.tran
BINH_GUI = Actor(id="nb-pl-01", name="Bình Trần", roles=frozenset({"requester", "classifier"}))

HOI = "Phòng chị nhận hồ sơ này không?"
DAP = "Phòng chị nhận, chuyển qua đi em."


def _truong_phong(phong: str) -> Actor:
    return Actor(id="nb-tp-01", name="Dung Phạm", roles=frozenset({"approver"}),
                 departments=frozenset({phong}))


def _xu_ly(phong: str) -> Actor:
    return Actor(id="nb-xl-01", name="Cường Lê", roles=frozenset({"handler"}),
                 departments=frozenset({phong}))


@pytest.fixture
def loai_noi_bo(session) -> MessageKind:
    loai = session.scalars(
        select(MessageKind)
        .where(MessageKind.hidden_from_requester.is_(True))
        .order_by(MessageKind.display_order)
    ).first()
    if loai is None:
        pytest.skip("Dữ liệu khởi tạo chưa khai loại lời nhắn nội bộ — cần down -v.")
    return loai


@pytest.fixture
def loai_thuong(session) -> MessageKind:
    return session.scalars(
        select(MessageKind)
        .where(
            MessageKind.owner_only.is_(False),
            MessageKind.department_stage_only.is_(False),
            MessageKind.reask_after_hours.is_(None),
            MessageKind.hidden_from_requester.is_(False),
        )
        .order_by(MessageKind.display_order)
    ).first()


@pytest.fixture
def loai_hoi_tien_do(session) -> MessageKind:
    return session.scalars(
        select(MessageKind)
        .where(MessageKind.owner_only.is_(True), MessageKind.reask_after_hours.is_not(None))
        .order_by(MessageKind.display_order)
    ).first()


@pytest.fixture
def client(session, phong_ban):
    trang_thai = {"actor": NGUOI_GUI}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: trang_thai["actor"]
    with TestClient(app) as c:
        c.trang_thai = trang_thai
        yield c
    app.dependency_overrides.clear()


def _goi(client, actor: Actor, phuong_thuc: str, duong: str, **kem):
    client.trang_thai["actor"] = actor
    return getattr(client, phuong_thuc)(duong, **kem)


def _tao(session, nguoi_gui: Actor = NGUOI_GUI) -> Request:
    loai = session.scalars(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    return create_case(session, title="Xác nhận công tác cho nhân viên mới",
                       requester_id=nguoi_gui.id, requester_label=nguoi_gui.label,
                       request_type_code=loai)


def _cho_phong_nhan(session, phong: str, nguoi_gui: Actor = NGUOI_GUI) -> Request:
    """Hồ sơ vừa chuyển về phòng, chờ trưởng phòng xác duyệt — lúc điều phối viên hỏi
    "phòng chị nhận không?"."""
    ho_so = _tao(session, nguoi_gui)
    uu_tien = session.scalars(select(Priority.code).order_by(Priority.display_order)).first()
    perform_transition(session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI_KHAC,
                       changes={"priority_code": uu_tien})
    perform_transition(session, case_id=ho_so.id, to_state="awaiting-acceptance",
                       actor=PHAN_LOAI_KHAC, changes={"department_code": phong})
    return ho_so


def _cuoc(client, actor: Actor) -> list[dict]:
    tra_ve = _goi(client, actor, "get", "/inbox")
    assert tra_ve.status_code == 200
    return tra_ve.json()["items"]


def _cuoc_cua(client, actor: Actor, ho_so: Request, noi_bo: bool) -> dict | None:
    return next(
        (c for c in _cuoc(client, actor) if c["case_id"] == ho_so.id and c["internal"] == noi_bo),
        None,
    )


def _moi_diem_cuoi_get(case_id: int) -> list[str]:
    """Đường dẫn của mọi điểm cuối GET mà tham số đường dẫn chỉ có mã hồ sơ.

    Đọc từ lược đồ OpenAPI chứ không từ `app.routes`: router con được gói lại nên danh sách
    tuyến không liệt kê thẳng điểm cuối của chúng.
    """
    ket_qua = []
    for duong, cac_cach in app.openapi()["paths"].items():
        if "get" not in cac_cach:
            continue
        if set(re.findall(r"{(\w+)}", duong)) <= {"case_id"}:
            ket_qua.append(duong.replace("{case_id}", str(case_id)))
    return ket_qua


# ---------------------------------------------------------------------------
# Định nghĩa hoàn thành
# ---------------------------------------------------------------------------


def test_dieu_phoi_hoi_truong_phong_tra_loi_trong_hop_thu(client, session, rule_set, phong_ban,
                                                         loai_noi_bo):
    ho_so = _cho_phong_nhan(session, phong_ban)
    session.commit()

    tra_ve = _goi(client, PHAN_LOAI, "post", f"/coordination/requests/{ho_so.id}/messages",
                  json={"kind": loai_noi_bo.code, "body": HOI})
    assert tra_ve.status_code == 200, tra_ve.text

    dung = _truong_phong(phong_ban)
    cuoc = _cuoc_cua(client, dung, ho_so, noi_bo=True)
    assert cuoc is not None
    assert cuoc["last_message"]["body"] == HOI
    assert cuoc["unread"] == 1
    assert cuoc["waiting_on_me"] is False  # cuộc nội bộ không có "đang chờ bạn"
    # Chưa có tin với người gửi thì không có cuộc với người gửi
    assert _cuoc_cua(client, dung, ho_so, noi_bo=False) is None

    tra_ve = _goi(client, dung, "post", f"/department/requests/{ho_so.id}/messages",
                  json={"kind": loai_noi_bo.code, "body": DAP})
    assert tra_ve.status_code == 200, tra_ve.text
    chi_tiet = tra_ve.json()
    assert chi_tiet["sees_internal"] is True
    assert [m["body"] for m in chi_tiet["messages"] if m["internal"]] == [HOI, DAP]
    assert _cuoc_cua(client, PHAN_LOAI, ho_so, noi_bo=True)["unread"] == 1


def test_nguoi_gui_khong_doc_duoc_tin_noi_bo_o_bat_ky_diem_cuoi_nao(
    client, session, rule_set, phong_ban, loai_noi_bo, loai_thuong
):
    ho_so = _cho_phong_nhan(session, phong_ban)
    session.commit()
    # Cụm thử có thể còn hồ sơ khác: so chênh lệch, không so số tuyệt đối
    chua_doc_truoc = _goi(client, NGUOI_GUI, "get", "/inbox/unread").json()["unread"]
    gui_loi_nhan(session, ho_so, PHAN_LOAI, loai_noi_bo.code, HOI)
    gui_loi_nhan(session, ho_so, _truong_phong(phong_ban), loai_noi_bo.code, DAP)
    session.commit()

    # Con số trên thanh bên không chứa chữ nào, nên phải so riêng
    assert _goi(client, NGUOI_GUI, "get", "/inbox/unread").json()["unread"] == chua_doc_truoc

    # Đủ hai cách đọc: quét mọi điểm cuối GET, rồi các điểm cuối ghi trả về chi tiết hồ sơ
    da_goi = 0
    for duong in _moi_diem_cuoi_get(ho_so.id):
        tra_ve = _goi(client, NGUOI_GUI, "get", duong)
        assert HOI not in tra_ve.text and DAP not in tra_ve.text, duong
        da_goi += 1
    assert da_goi >= 5  # /requests, /requests/{id}, /inbox, /inbox/unread, …

    tra_ve = _goi(client, NGUOI_GUI, "post", f"/requests/{ho_so.id}/messages",
                  json={"kind": loai_thuong.code, "body": "Em cần gấp trong tuần"})
    assert tra_ve.status_code == 200
    assert HOI not in tra_ve.text and DAP not in tra_ve.text
    chi_tiet = tra_ve.json()
    assert chi_tiet["sees_internal"] is False
    assert all(not m["internal"] for m in chi_tiet["messages"])
    assert all(not k["internal"] for k in chi_tiet["message_kinds"])

    # Không gửi được, không đánh dấu đọc được cuộc nội bộ — 404, không xác nhận nó tồn tại
    tra_ve = _goi(client, NGUOI_GUI, "post", f"/requests/{ho_so.id}/messages",
                  json={"kind": loai_noi_bo.code, "body": "Thử nhắn nội bộ"})
    assert tra_ve.status_code == 403
    tra_ve = _goi(client, NGUOI_GUI, "post", f"/inbox/{ho_so.id}/read",
                  params={"internal": "true"})
    assert tra_ve.status_code == 404
    assert _cuoc_cua(client, NGUOI_GUI, ho_so, noi_bo=True) is None


def test_dieu_phoi_vien_gui_ho_so_cua_minh_cung_khong_thay(client, session, rule_set, phong_ban,
                                                          loai_noi_bo):
    """Ràng buộc theo hồ sơ, không theo vai trò: Bình Trần mở hồ sơ chính mình gửi ở buồng
    lái điều phối cũng không thấy tin nội bộ của hồ sơ đó."""
    ho_so = _cho_phong_nhan(session, phong_ban, nguoi_gui=BINH_GUI)
    gui_loi_nhan(session, ho_so, PHAN_LOAI_KHAC, loai_noi_bo.code, HOI)
    session.commit()

    chi_tiet = _goi(client, BINH_GUI, "get", f"/coordination/requests/{ho_so.id}")
    assert chi_tiet.status_code == 200
    assert HOI not in chi_tiet.text
    assert chi_tiet.json()["sees_internal"] is False
    assert all(not k["internal"] for k in chi_tiet.json()["message_kinds"])

    tra_ve = _goi(client, BINH_GUI, "post", f"/coordination/requests/{ho_so.id}/messages",
                  json={"kind": loai_noi_bo.code, "body": "Thử nhắn nội bộ"})
    assert tra_ve.status_code == 403
    assert HOI not in _goi(client, BINH_GUI, "get", "/inbox").text
    with pytest.raises(MessageRejected):
        gui_loi_nhan(session, ho_so, BINH_GUI, loai_noi_bo.code, "Thử nhắn nội bộ")


# ---------------------------------------------------------------------------
# Tin nội bộ không làm lệch luật của lời nhắn thường
# ---------------------------------------------------------------------------


def test_tin_noi_bo_khong_phai_tra_loi_nguoi_gui(client, session, rule_set, phong_ban,
                                                loai_noi_bo, loai_thuong):
    ho_so = _cho_phong_nhan(session, phong_ban)
    gui_loi_nhan(session, ho_so, NGUOI_GUI, loai_thuong.code, "Em cần gấp trong tuần")
    gui_loi_nhan(session, ho_so, _truong_phong(phong_ban), loai_noi_bo.code, DAP)
    session.commit()

    dung = _truong_phong(phong_ban)
    chi_tiet = _goi(client, dung, "get", f"/department/requests/{ho_so.id}").json()
    # Người gửi vẫn đang chờ nhân viên trả lời — tin nội bộ không tính
    assert chi_tiet["last_message_from_requester"] is True
    assert _cuoc_cua(client, dung, ho_so, noi_bo=False)["waiting_on_me"] is True


def test_tin_noi_bo_khong_mo_khoa_hoi_lai(client, session, rule_set, phong_ban, loai_noi_bo,
                                         loai_hoi_tien_do):
    if loai_hoi_tien_do is None:
        pytest.skip("Dữ liệu khởi tạo chưa khai loại hỏi tiến độ.")
    ho_so = _cho_phong_nhan(session, phong_ban)
    gui_loi_nhan(session, ho_so, NGUOI_GUI, loai_hoi_tien_do.code, None)
    gui_loi_nhan(session, ho_so, _truong_phong(phong_ban), loai_noi_bo.code, DAP)
    session.commit()

    chi_tiet = _goi(client, NGUOI_GUI, "get", f"/requests/{ho_so.id}").json()
    hoi = next(k for k in chi_tiet["message_kinds"] if k["code"] == loai_hoi_tien_do.code)
    assert hoi["retry_at"] is not None


# ---------------------------------------------------------------------------
# Hai cuộc, hai mốc đã đọc
# ---------------------------------------------------------------------------


def test_doc_cuoc_nay_khong_lam_cuoc_kia_da_doc(client, session, rule_set, phong_ban,
                                               loai_noi_bo, loai_thuong):
    ho_so = _cho_phong_nhan(session, phong_ban)
    gui_loi_nhan(session, ho_so, NGUOI_GUI, loai_thuong.code, "Em cần gấp trong tuần")
    gui_loi_nhan(session, ho_so, PHAN_LOAI, loai_noi_bo.code, HOI)
    session.commit()

    dung = _truong_phong(phong_ban)
    truoc = _goi(client, dung, "get", "/inbox/unread").json()["unread"]
    assert _goi(client, dung, "post", f"/inbox/{ho_so.id}/read").status_code == 204
    assert _cuoc_cua(client, dung, ho_so, noi_bo=False)["unread"] == 0
    assert _cuoc_cua(client, dung, ho_so, noi_bo=True)["unread"] == 1
    assert _goi(client, dung, "get", "/inbox/unread").json()["unread"] == truoc - 1

    tra_ve = _goi(client, dung, "post", f"/inbox/{ho_so.id}/read", params={"internal": "true"})
    assert tra_ve.status_code == 204
    assert _cuoc_cua(client, dung, ho_so, noi_bo=True)["unread"] == 0
    assert _goi(client, dung, "get", "/inbox/unread").json()["unread"] == truoc - 2


def test_ho_so_ket_thuc_cuoc_noi_bo_chi_doc(client, session, rule_set, phong_ban, loai_noi_bo):
    ho_so = _cho_phong_nhan(session, phong_ban)
    gui_loi_nhan(session, ho_so, PHAN_LOAI, loai_noi_bo.code, HOI)
    perform_transition(session, case_id=ho_so.id, to_state="cancelled", actor=NGUOI_GUI,
                       note="Không cần nữa")
    session.commit()

    chi_tiet = _goi(client, PHAN_LOAI, "get", f"/coordination/requests/{ho_so.id}").json()
    assert chi_tiet["state"]["is_terminal"] is True
    assert [m["body"] for m in chi_tiet["messages"] if m["internal"]] == [HOI]
    assert chi_tiet["message_kinds"] == []
