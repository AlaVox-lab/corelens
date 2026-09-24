# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử lời nhắn trên hồ sơ (#128, ADR-0005).
#
# Ranh giới phải canh bằng kiểm thử, không chỉ bằng tài liệu: lời nhắn KHÔNG đổi hồ sơ —
# không trạng thái, không trường, không đồng hồ, không dòng nhật ký. Cộng các luật chốt
# với navigator ngày 24/09/2026: hai chiều, ai mở được hồ sơ thì nhắn được, hồ sơ kết
# thúc thì chỉ đọc, "Hỏi tiến độ" chỉ khi hồ sơ ở phòng ban và hỏi lại phải chờ trả lời.
#
# Loại lời nhắn tìm theo cờ trong bảng, không viết cứng mã loại. Dữ liệu không có loại
# nào như vậy thì bài tự bỏ qua.

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app.auth.dependencies import current_actor
from app.db import get_session
from app.main import app
from app.models.case import CaseMessage, EventLog, Request
from app.models.workflow_config import Department, MessageKind, Priority, RequestType
from app.workflow.assignment import trang_thai_hang_doi_phong_ban
from app.workflow.context import Actor
from app.workflow.engine import create_case, perform_transition
from app.workflow.messages import MessageRejected, gui_loi_nhan, loai_gui_duoc

NGUOI_GUI = Actor(id="kc-gui-01", name="An Nguyễn", roles=frozenset({"requester"}))
NGUOI_GUI_KHAC = Actor(id="kc-gui-02", name="Chi Lê", roles=frozenset({"requester"}))
PHAN_LOAI = Actor(id="kc-pl-01", name="Bình Trần", roles=frozenset({"classifier"}))
QUAN_TRI = Actor(id="kc-qt-01", name="Khánh Võ", roles=frozenset({"administrator"}))


def _truong_phong(phong: str) -> Actor:
    return Actor(id="kc-tp-01", name="Dung Phạm", roles=frozenset({"approver"}),
                 departments=frozenset({phong}))


def _xu_ly(phong: str) -> Actor:
    return Actor(id="kc-xl-01", name="Cường Lê", roles=frozenset({"handler"}),
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
def loai_hoi_tien_do(session) -> MessageKind:
    """Loại của người gửi, chỉ khi hồ sơ ở phòng ban, có luật hỏi lại."""
    loai = session.scalars(
        select(MessageKind)
        .where(
            MessageKind.owner_only.is_(True),
            MessageKind.department_stage_only.is_(True),
            MessageKind.reask_after_hours.is_not(None),
        )
        .order_by(MessageKind.display_order)
    ).first()
    if loai is None:
        pytest.skip("Dữ liệu khởi tạo chưa khai loại hỏi tiến độ.")
    return loai


@pytest.fixture
def client(session, phong_ban):
    """Máy khách HTTP đổi được người gọi. Phần dựng cảnh phải `commit` — lý do ở fixture
    cùng tên trong test_routes.py."""
    trang_thai = {"actor": NGUOI_GUI}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: trang_thai["actor"]
    with TestClient(app) as c:
        c.trang_thai = trang_thai
        yield c
    app.dependency_overrides.clear()


def _goi_bang(client, actor: Actor) -> None:
    client.trang_thai["actor"] = actor


# ---------------------------------------------------------------------------
# Dựng hồ sơ ở từng trạng thái, qua đúng các cạnh hợp lệ
# ---------------------------------------------------------------------------


def _tao(session) -> Request:
    loai = session.scalars(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    return create_case(
        session, title="Máy in tầng ba kẹt giấy", requester_id=NGUOI_GUI.id,
        requester_label=NGUOI_GUI.label, request_type_code=loai,
    )


def _cho_phong_nhan(session, phong: str) -> Request:
    ho_so = _tao(session)
    uu_tien = session.scalars(select(Priority.code).order_by(Priority.display_order)).first()
    perform_transition(session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
                       changes={"priority_code": uu_tien})
    perform_transition(session, case_id=ho_so.id, to_state="awaiting-acceptance",
                       actor=PHAN_LOAI, changes={"department_code": phong})
    return ho_so


def _dang_xu_ly(session, phong: str) -> Request:
    ho_so = _cho_phong_nhan(session, phong)
    perform_transition(session, case_id=ho_so.id, to_state="in-progress",
                       actor=_truong_phong(phong))
    return ho_so


def _anh_dong(session, case_id: int) -> dict:
    """Toàn bộ cột của dòng hồ sơ, đọc thẳng từ cơ sở dữ liệu — kèm `ctid`.

    `ctid` là vị trí vật lý của phiên bản dòng. Mọi lệnh UPDATE, kể cả ghi lại đúng giá trị
    cũ, đều tạo phiên bản mới và đổi `ctid`. So giá trị thôi thì không đủ: trong cùng một
    giao dịch, `now()` không đổi, nên một lệnh chạm `updated_at` vẫn ghi ra đúng giá trị cũ.
    """
    return dict(
        session.execute(
            text("SELECT ctid::text AS vi_tri, * FROM requests WHERE id = :id"), {"id": case_id}
        ).mappings().one()
    )


def _so_dong_nhat_ky(session, case_id: int) -> int:
    return session.scalar(select(func.count()).where(EventLog.case_id == case_id))


def _ma_loai(g) -> set[str]:
    return {x.loai.code for x in g}


# ---------------------------------------------------------------------------
# Ranh giới ADR-0005: lời nhắn không đổi hồ sơ
# ---------------------------------------------------------------------------


def test_loi_nhan_khong_cham_toi_dong_ho_so(session, rule_set, phong_ban, loai_thuong,
                                             loai_hoi_tien_do):
    """Không trạng thái, không trường, không đồng hồ, không dòng nhật ký — và không một
    lệnh UPDATE nào lên dòng hồ sơ."""
    ho_so = _dang_xu_ly(session, phong_ban)
    session.commit()
    truoc = _anh_dong(session, ho_so.id)
    so_nhat_ky = _so_dong_nhat_ky(session, ho_so.id)

    gui_loi_nhan(session, ho_so, NGUOI_GUI, loai_thuong.code, "Máy in ở tầng ba nhé")
    gui_loi_nhan(session, ho_so, NGUOI_GUI, loai_hoi_tien_do.code, None)
    gui_loi_nhan(session, ho_so, _xu_ly(phong_ban), loai_thuong.code, "Chiều nay em qua")
    session.commit()

    assert _anh_dong(session, ho_so.id) == truoc
    assert _so_dong_nhat_ky(session, ho_so.id) == so_nhat_ky


def test_loi_nhan_chi_ghi_them(session, rule_set, phong_ban, loai_thuong):
    ho_so = _dang_xu_ly(session, phong_ban)
    loi_nhan = gui_loi_nhan(session, ho_so, NGUOI_GUI, loai_thuong.code, "Nội dung gốc")

    with pytest.raises(Exception, match="chỉ ghi thêm"):
        with session.begin_nested():
            session.execute(text("UPDATE case_messages SET body = 'đã sửa' WHERE id = :id"),
                            {"id": loi_nhan.id})
    with pytest.raises(Exception, match="chỉ ghi thêm"):
        with session.begin_nested():
            session.execute(text("DELETE FROM case_messages WHERE id = :id"),
                            {"id": loi_nhan.id})


# ---------------------------------------------------------------------------
# Ai mở được hồ sơ thì nhắn được — qua đúng cửa của từng buồng lái
# ---------------------------------------------------------------------------


def test_hai_chieu_qua_ba_cua(client, session, rule_set, phong_ban, loai_thuong):
    ho_so = _dang_xu_ly(session, phong_ban)
    session.commit()
    than = {"kind": loai_thuong.code, "body": "Máy in ở tầng ba nhé"}

    _goi_bang(client, NGUOI_GUI)
    assert client.post(f"/requests/{ho_so.id}/messages", json=than).status_code == 200
    _goi_bang(client, PHAN_LOAI)
    assert client.post(f"/coordination/requests/{ho_so.id}/messages",
                       json={**than, "body": "Đã nhắc phòng"}).status_code == 200
    _goi_bang(client, _xu_ly(phong_ban))
    tra_ve = client.post(f"/department/requests/{ho_so.id}/messages",
                         json={**than, "body": "Chiều nay em qua"})
    assert tra_ve.status_code == 200

    loi_nhan = tra_ve.json()["messages"]
    assert [m["body"] for m in loi_nhan] == [
        "Máy in ở tầng ba nhé", "Đã nhắc phòng", "Chiều nay em qua"
    ]
    assert [m["from_requester"] for m in loi_nhan] == [True, False, False]
    assert loi_nhan[2]["author_label"] == "Cường Lê"
    assert loi_nhan[0]["kind_label"] == loai_thuong.label


def test_khong_mo_duoc_ho_so_thi_khong_nhan_duoc(client, session, rule_set, phong_ban,
                                                 phong_khac, loai_thuong):
    ho_so = _dang_xu_ly(session, phong_ban)
    session.commit()
    than = {"kind": loai_thuong.code, "body": "Chen ngang"}

    _goi_bang(client, NGUOI_GUI_KHAC)
    assert client.post(f"/requests/{ho_so.id}/messages", json=than).status_code == 404
    _goi_bang(client, _xu_ly(phong_khac))
    assert client.post(f"/department/requests/{ho_so.id}/messages", json=than).status_code == 404
    _goi_bang(client, NGUOI_GUI)
    assert client.post("/requests/999999999/messages", json=than).status_code == 404
    assert session.scalar(select(func.count()).where(CaseMessage.case_id == ho_so.id)) == 0


def test_vai_tro_khong_duoc_khai_thi_khong_nhan_duoc(session, rule_set, phong_ban, loai_thuong):
    """Quản trị viên không có trong bảng vai trò gửi của loại nào — kể cả khi đi vòng qua
    cửa nhìn thấy."""
    ho_so = _dang_xu_ly(session, phong_ban)
    assert loai_gui_duoc(session, ho_so, QUAN_TRI) == []
    with pytest.raises(MessageRejected) as loi:
        gui_loi_nhan(session, ho_so, QUAN_TRI, loai_thuong.code, "Tôi là quản trị")
    assert loi.value.code == "message-not-permitted"
    assert loi.value.http_status == 403


def test_loai_khong_co_trong_bang(client, session, rule_set, phong_ban):
    ho_so = _dang_xu_ly(session, phong_ban)
    session.commit()
    tra_ve = client.post(f"/requests/{ho_so.id}/messages", json={"kind": "khong-co", "body": "x"})
    assert tra_ve.status_code == 422
    assert tra_ve.json()["detail"]["code"] == "unknown-message-kind"


# ---------------------------------------------------------------------------
# Hồ sơ kết thúc thì chỉ đọc
# ---------------------------------------------------------------------------


def test_ho_so_ket_thuc_thi_chi_doc(client, session, rule_set, loai_thuong):
    ho_so = _tao(session)
    gui_loi_nhan(session, ho_so, NGUOI_GUI, loai_thuong.code, "Gửi trước khi hủy")
    perform_transition(session, case_id=ho_so.id, to_state="cancelled", actor=NGUOI_GUI)
    session.commit()

    chi_tiet = client.get(f"/requests/{ho_so.id}").json()
    assert chi_tiet["state"]["is_terminal"] is True
    assert chi_tiet["message_kinds"] == []
    assert [m["body"] for m in chi_tiet["messages"]] == ["Gửi trước khi hủy"]

    tra_ve = client.post(f"/requests/{ho_so.id}/messages",
                         json={"kind": loai_thuong.code, "body": "Còn nhắn được không?"})
    assert tra_ve.status_code == 409
    assert tra_ve.json()["detail"]["code"] == "case-closed"


# ---------------------------------------------------------------------------
# Hỏi tiến độ: chỉ người gửi hồ sơ, chỉ khi hồ sơ ở phòng ban
# ---------------------------------------------------------------------------


def test_hoi_tien_do_chi_khi_ho_so_o_phong_ban(session, rule_set, phong_ban, loai_thuong,
                                               loai_hoi_tien_do):
    """Đáp án suy từ bộ quy tắc — cùng hàm với hàng đợi phòng ban — không liệt kê cứng."""
    chang_phong_ban = {s.code for s in trang_thai_hang_doi_phong_ban(session, rule_set.id)}
    ho_so = _tao(session)

    def kiem():
        co = loai_hoi_tien_do.code in _ma_loai(loai_gui_duoc(session, ho_so, NGUOI_GUI))
        assert co == (ho_so.current_state in chang_phong_ban), ho_so.current_state
        # Lời nhắn thường thì ở mọi trạng thái chưa kết thúc
        assert loai_thuong.code in _ma_loai(loai_gui_duoc(session, ho_so, NGUOI_GUI))

    kiem()  # Đã gửi — còn ở tay điều phối
    uu_tien = session.scalars(select(Priority.code).order_by(Priority.display_order)).first()
    perform_transition(session, case_id=ho_so.id, to_state="classified", actor=PHAN_LOAI,
                       changes={"priority_code": uu_tien})
    kiem()
    perform_transition(session, case_id=ho_so.id, to_state="awaiting-acceptance",
                       actor=PHAN_LOAI, changes={"department_code": phong_ban})
    kiem()
    perform_transition(session, case_id=ho_so.id, to_state="in-progress",
                       actor=_truong_phong(phong_ban))
    kiem()
    perform_transition(session, case_id=ho_so.id, to_state="awaiting-info",
                       actor=_xu_ly(phong_ban), note="Máy nào?")
    kiem()  # Đang chờ người gửi trả lời — phòng ban không cầm hồ sơ
    assert {"awaiting-acceptance", "in-progress"} <= chang_phong_ban


def test_hoi_tien_do_chi_nguoi_gui_cua_ho_so(session, rule_set, phong_ban, loai_hoi_tien_do):
    ho_so = _dang_xu_ly(session, phong_ban)
    assert loai_hoi_tien_do.code in _ma_loai(loai_gui_duoc(session, ho_so, NGUOI_GUI))
    # Cùng vai trò người gửi nhưng không phải chủ hồ sơ
    assert loai_hoi_tien_do.code not in _ma_loai(loai_gui_duoc(session, ho_so, NGUOI_GUI_KHAC))
    # Nhân viên không hỏi tiến độ chính mình
    assert loai_hoi_tien_do.code not in _ma_loai(loai_gui_duoc(session, ho_so, _xu_ly(phong_ban)))
    with pytest.raises(MessageRejected) as loi:
        gui_loi_nhan(session, ho_so, NGUOI_GUI_KHAC, loai_hoi_tien_do.code, None)
    assert loi.value.code == "message-not-permitted"


# ---------------------------------------------------------------------------
# Hỏi lại phải chờ trả lời, hoặc chờ đủ giờ
# ---------------------------------------------------------------------------


def _gui_lai_tu(session, ho_so, loai) -> dt.datetime | None:
    for g in loai_gui_duoc(session, ho_so, NGUOI_GUI):
        if g.loai.code == loai.code:
            return g.gui_lai_tu
    raise AssertionError(f"Không thấy loại {loai.code}")


def test_hoi_lai_phai_cho_phong_ban_tra_loi(session, rule_set, phong_ban, loai_thuong,
                                            loai_hoi_tien_do):
    ho_so = _dang_xu_ly(session, phong_ban)
    lan_dau = gui_loi_nhan(session, ho_so, NGUOI_GUI, loai_hoi_tien_do.code, None)
    assert lan_dau.body is None

    # Chưa ai trả lời: nút mờ, kèm đúng mốc hỏi lại được
    assert _gui_lai_tu(session, ho_so, loai_hoi_tien_do) == (
        lan_dau.created_at + dt.timedelta(hours=loai_hoi_tien_do.reask_after_hours)
    )
    with pytest.raises(MessageRejected) as loi:
        gui_loi_nhan(session, ho_so, NGUOI_GUI, loai_hoi_tien_do.code, None)
    assert (loi.value.code, loi.value.http_status) == ("reask-too-soon", 409)

    # Chính người gửi nhắn thêm thì không tính là trả lời
    gui_loi_nhan(session, ho_so, NGUOI_GUI, loai_thuong.code, "Gấp lắm ạ")
    assert _gui_lai_tu(session, ho_so, loai_hoi_tien_do) is not None

    # Phòng ban trả lời: hỏi lại được ngay
    gui_loi_nhan(session, ho_so, _xu_ly(phong_ban), loai_thuong.code, "Đang chờ linh kiện")
    assert _gui_lai_tu(session, ho_so, loai_hoi_tien_do) is None
    gui_loi_nhan(session, ho_so, NGUOI_GUI, loai_hoi_tien_do.code, "Linh kiện về chưa?")

    # Lần hỏi mới lại chờ trả lời mới
    assert _gui_lai_tu(session, ho_so, loai_hoi_tien_do) is not None


def test_giao_dien_nhan_loai_va_moc_hoi_lai(client, session, rule_set, phong_ban, loai_thuong,
                                            loai_hoi_tien_do):
    """Nút lời nhắn dựng từ `message_kinds` — như nút chuyển trạng thái dựng từ
    `allowed_transitions`. Loại đang chờ luật hỏi lại vẫn có mặt, kèm mốc."""
    ho_so = _dang_xu_ly(session, phong_ban)
    session.commit()

    def cac_loai(than_tra_ve: dict) -> dict[str, dict]:
        return {k["code"]: k for k in than_tra_ve["message_kinds"]}

    truoc = cac_loai(client.get(f"/requests/{ho_so.id}").json())
    assert {loai_thuong.code, loai_hoi_tien_do.code} <= set(truoc)
    assert truoc[loai_hoi_tien_do.code]["retry_at"] is None
    assert truoc[loai_hoi_tien_do.code]["body_required"] is False
    assert truoc[loai_thuong.code]["body_required"] is True

    tra_ve = client.post(f"/requests/{ho_so.id}/messages", json={"kind": loai_hoi_tien_do.code})
    assert tra_ve.status_code == 200
    sau = cac_loai(tra_ve.json())
    assert sau[loai_hoi_tien_do.code]["retry_at"] is not None
    assert sau[loai_thuong.code]["retry_at"] is None

    lan_hai = client.post(f"/requests/{ho_so.id}/messages", json={"kind": loai_hoi_tien_do.code})
    assert lan_hai.status_code == 409
    assert lan_hai.json()["detail"]["code"] == "reask-too-soon"


@pytest.mark.parametrize(("gio_truoc", "hoi_lai_duoc"), [(1, False), (-1, True)],
                         ids=["chua-du-gio", "da-qua-gio"])
def test_hoi_lai_duoc_khi_qua_so_gio_khai(session, rule_set, phong_ban, loai_hoi_tien_do,
                                         gio_truoc, hoi_lai_duoc):
    """Lần hỏi trước cách đây (N − 1) giờ thì chưa hỏi lại được; (N + 1) giờ thì được.
    Ghi thẳng mốc thời gian vào bảng — bảng chỉ chặn sửa và xóa, không chặn thêm."""
    ho_so = _dang_xu_ly(session, phong_ban)
    moc = session.scalar(select(func.now())) - dt.timedelta(
        hours=loai_hoi_tien_do.reask_after_hours - gio_truoc
    )
    session.add(CaseMessage(case_id=ho_so.id, kind=loai_hoi_tien_do.code, author=NGUOI_GUI.id,
                            author_label=NGUOI_GUI.label, created_at=moc))
    session.flush()

    assert (_gui_lai_tu(session, ho_so, loai_hoi_tien_do) is None) is hoi_lai_duoc


# ---------------------------------------------------------------------------
# Nội dung
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "noi_dung", [None, "", "   \n  "], ids=["khong-gui", "rong", "khoang-trang"]
)
def test_loai_bat_buoc_noi_dung_thi_khong_gui_rong(client, session, rule_set, phong_ban,
                                                    loai_thuong, noi_dung):
    ho_so = _dang_xu_ly(session, phong_ban)
    session.commit()
    tra_ve = client.post(f"/requests/{ho_so.id}/messages",
                         json={"kind": loai_thuong.code, "body": noi_dung})
    assert tra_ve.status_code == 422
    assert tra_ve.json()["detail"]["code"] == "message-body-required"


def test_noi_dung_qua_dai_bi_tu_choi(client, session, rule_set, phong_ban, loai_thuong):
    ho_so = _dang_xu_ly(session, phong_ban)
    session.commit()
    tra_ve = client.post(f"/requests/{ho_so.id}/messages",
                         json={"kind": loai_thuong.code, "body": "x" * 2001})
    assert tra_ve.status_code == 422


def test_noi_dung_duoc_cat_khoang_trang(session, rule_set, phong_ban, loai_thuong):
    ho_so = _dang_xu_ly(session, phong_ban)
    assert gui_loi_nhan(session, ho_so, NGUOI_GUI, loai_thuong.code, "  Máy in  \n").body == (
        "Máy in"
    )


# ---------------------------------------------------------------------------
# Dấu hiệu trên hàng đợi: ai nhắn sau cùng
# ---------------------------------------------------------------------------


def _muc(danh_sach: list[dict], case_id: int) -> dict:
    return next(m for m in danh_sach if m["id"] == case_id)


def test_dau_hieu_dang_cho_tra_loi(client, session, rule_set, phong_ban, loai_thuong):
    ho_so = _dang_xu_ly(session, phong_ban)
    session.commit()

    def hai_phia():
        _goi_bang(client, _xu_ly(phong_ban))
        hang_doi = client.get("/department/queue").json()["items"]
        _goi_bang(client, NGUOI_GUI)
        cua_toi = client.get("/requests").json()
        return (_muc(hang_doi, ho_so.id)["last_message_from_requester"],
                _muc(cua_toi, ho_so.id)["last_message_from_requester"])

    assert hai_phia() == (None, None)

    gui_loi_nhan(session, ho_so, NGUOI_GUI, loai_thuong.code, "Bao giờ xong ạ?")
    session.commit()
    assert hai_phia() == (True, True)  # phòng ban thấy: người gửi đang chờ trả lời

    gui_loi_nhan(session, ho_so, _xu_ly(phong_ban), loai_thuong.code, "Chiều nay")
    session.commit()
    assert hai_phia() == (False, False)  # người gửi thấy: đã có trả lời
