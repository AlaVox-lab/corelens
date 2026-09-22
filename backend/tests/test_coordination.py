# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử buồng lái điều phối viên (#82).
#
# Ba điều quan trọng nhất, theo thứ tự:
#
#   1. Cửa: người không mang vai trò điều phối không nhìn thấy gì — kể cả không biết
#      hồ sơ nào có thật.
#   2. Mọi thứ suy từ dữ liệu: trạng thái nào vào hàng đợi, trường nào có ô nhập. Bài
#      kiểm thử tự tra bộ quy tắc để lấy đáp án, không chép đáp án vào đây — chép vào
#      thì bài kiểm thử thành bản sao thứ hai của bộ quy tắc.
#   3. Vòng trọn vẹn trong định nghĩa hoàn thành: điều phối viên phân loại và chuyển
#      hồ sơ về phòng ban, và người gửi thấy đúng trạng thái mới trên cổng của mình.

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.auth.dependencies import current_actor
from app.db import get_session
from app.main import app, me
from app.models.case import Request
from app.models.workflow_config import (
    Priority,
    RequestType,
    RequestTypeRouting,
    State,
    Transition,
    TransitionRole,
)
from app.rules.guards import permitted_fields
from app.workflow.context import Actor
from app.workflow.coordination import VAI_TRO_DIEU_PHOI
from app.workflow.engine import create_case

NGUOI_GUI = Actor(id="nd-gui-001", name="An Nguyễn", roles=frozenset({"requester"}))
DIEU_PHOI = Actor(id="nd-dp-001", name="Bình Trần", roles=frozenset({VAI_TRO_DIEU_PHOI}))


@pytest.fixture
def client(session):
    """Máy khách HTTP dùng chung phiên của bài kiểm thử, đổi được người đang gọi.

    Phần dựng cảnh phải `commit`, không dừng ở `flush` — lý do ở fixture cùng tên trong
    test_routes.py.
    """
    dang_goi = {"actor": DIEU_PHOI}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: dang_goi["actor"]
    with TestClient(app) as c:
        c.dang_goi = dang_goi
        yield c
    app.dependency_overrides.clear()


def _goi_bang(client, actor: Actor) -> None:
    client.dang_goi["actor"] = actor


def _loai(session, ma: str | None = None) -> RequestType:
    truy_van = select(RequestType).where(RequestType.is_active)
    if ma:
        truy_van = truy_van.where(RequestType.code == ma)
    return session.scalars(truy_van.order_by(RequestType.display_order)).first()


def _tao(session, tieu_de: str = "Máy chiếu phòng họp không lên hình", *, loai=True):
    ho_so = create_case(
        session,
        title=tieu_de,
        requester_id=NGUOI_GUI.id,
        requester_label=NGUOI_GUI.label,
        request_type_code=_loai(session).code if loai else None,
    )
    session.commit()
    return ho_so


def _trang_thai_cua_dieu_phoi(session, rule_set) -> list[str]:
    """Đáp án tra từ bộ quy tắc: trạng thái nào vai trò điều phối có cạnh đi ra."""
    nguon = (
        select(Transition.from_state)
        .join(TransitionRole, TransitionRole.transition_id == Transition.id)
        .where(
            Transition.rule_set_id == rule_set.id,
            Transition.is_system.is_(False),
            TransitionRole.role_code == VAI_TRO_DIEU_PHOI,
        )
    )
    return list(
        session.scalars(
            select(State.code)
            .where(State.rule_set_id == rule_set.id, State.code.in_(nguon))
            .order_by(State.display_order)
        ).all()
    )


# ---------------------------------------------------------------------------
# Cửa
# ---------------------------------------------------------------------------


def test_nguoi_khong_phai_dieu_phoi_bi_chan_o_ca_ba_diem_cuoi(client, session, rule_set):
    """Chặn bằng 403 trước khi tra hồ sơ, nên người dò số không biết hồ sơ nào có thật."""
    ho_so = _tao(session)
    _goi_bang(client, NGUOI_GUI)

    assert client.get("/coordination/queue").status_code == 403
    assert client.get(f"/coordination/requests/{ho_so.id}").status_code == 403

    # Hồ sơ có thật và hồ sơ không tồn tại trả CÙNG một mã
    for ma in (ho_so.id, 999_999_999):
        r = client.post(
            f"/coordination/requests/{ma}/transitions", json={"to_state": "classified"}
        )
        assert r.status_code == 403


def test_me_bao_khong_gian_lam_viec_theo_vai_tro():
    """Giao diện dựng thanh điều hướng từ đây, không tự đọc tên vai trò."""
    assert me(DIEU_PHOI, {})["workspaces"] == ["portal", "coordination"]
    assert me(NGUOI_GUI, {})["workspaces"] == ["portal"]


# ---------------------------------------------------------------------------
# Hàng đợi
# ---------------------------------------------------------------------------


def test_nhom_hang_doi_suy_tu_bo_quy_tac(client, session, rule_set):
    r = client.get("/coordination/queue")
    assert r.status_code == 200

    assert [g["code"] for g in r.json()["groups"]] == _trang_thai_cua_dieu_phoi(
        session, rule_set
    )
    for g in r.json()["groups"]:
        assert g["label"], "nhãn trạng thái đi kèm mã"


def test_hang_doi_co_ho_so_moi_gui_kem_ten_nguoi_gui(client, session, rule_set):
    ho_so = _tao(session)

    muc = {m["id"]: m for m in client.get("/coordination/queue").json()["items"]}
    assert ho_so.id in muc
    assert muc[ho_so.id]["requester_label"] == "An Nguyễn"
    assert muc[ho_so.id]["priority"] is None, "chưa phân loại thì chưa có mức ưu tiên"


def test_ho_so_gui_qua_cong_mang_ten_nguoi_gui_toi_hang_doi(client, session, rule_set):
    """Chỗ ghép nối giữa hai cổng: gửi qua #44, điều phối viên thấy tên ở #82.

    Các bài khác tạo hồ sơ thẳng qua engine nên không chạm tới điểm cuối gửi yêu cầu.
    Phép thử đột biến lộ ra khe đó: gỡ việc ghi tên ở cổng #44 mà không bài nào đổ.
    """
    _goi_bang(client, NGUOI_GUI)
    loai = client.get("/request-types").json()[0]["code"]
    r = client.post(
        "/requests",
        json={"title": "Wi-Fi tầng 3 mất kết nối buổi chiều", "request_type_code": loai},
    )
    assert r.status_code == 201, r.text

    _goi_bang(client, DIEU_PHOI)
    muc = {m["id"]: m for m in client.get("/coordination/queue").json()["items"]}
    assert muc[r.json()["id"]]["requester_label"] == NGUOI_GUI.label


def test_hang_doi_cho_lau_nhat_len_dau(client, session, rule_set):
    """Xếp theo lúc vào trạng thái hiện tại, không theo mã hồ sơ.

    Hồ sơ tạo sau nhưng lùi mốc tạo về hai giờ trước phải đứng trên hồ sơ tạo trước.
    """
    truoc = _tao(session, "Tạo trước")
    sau = _tao(session, "Tạo sau nhưng đã chờ lâu hơn")
    session.execute(
        update(Request)
        .where(Request.id == sau.id)
        .values(created_at=Request.created_at - dt.timedelta(hours=2))
    )
    session.commit()

    thu_tu = [m["id"] for m in client.get("/coordination/queue").json()["items"]]
    assert thu_tu.index(sau.id) < thu_tu.index(truoc.id)


def test_hang_doi_loc_theo_trang_thai(client, session, rule_set):
    ho_so = _tao(session)
    trang_thai_dau = ho_so.current_state

    r = client.get("/coordination/queue", params={"state": trang_thai_dau})
    assert r.status_code == 200
    assert all(m["state"]["code"] == trang_thai_dau for m in r.json()["items"])
    assert ho_so.id in {m["id"] for m in r.json()["items"]}


def test_loc_theo_trang_thai_ngoai_hang_doi_bi_tu_choi(client, session, rule_set):
    ngoai = session.scalars(
        select(State.code).where(
            State.rule_set_id == rule_set.id,
            State.code.not_in(_trang_thai_cua_dieu_phoi(session, rule_set)),
        )
    ).first()

    r = client.get("/coordination/queue", params={"state": ngoai})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "state-not-in-queue"


# ---------------------------------------------------------------------------
# Chi tiết: ô nhập lấy từ dữ liệu, như nút bấm
# ---------------------------------------------------------------------------


def test_moi_canh_mang_dung_truong_ma_rang_buoc_cua_no_cho_dat(client, session, rule_set):
    """Khuôn mẫu ARCHITECTURE.md mục 7.2 kéo dài từ nút bấm sang ô nhập.

    Đáp án tra từ bộ quy tắc — `permitted_fields()` của chính cạnh đó — không chép
    danh sách trường vào đây.
    """
    ho_so = _tao(session)
    r = client.get(f"/coordination/requests/{ho_so.id}")
    assert r.status_code == 200

    canh_trong_bang = {
        t.to_state: t
        for t in session.scalars(
            select(Transition).where(
                Transition.rule_set_id == rule_set.id,
                Transition.from_state == ho_so.current_state,
            )
        ).all()
    }
    di_duoc = r.json()["allowed_transitions"]
    assert di_duoc, "điều phối viên phải có việc để làm ở trạng thái đầu"
    for canh in di_duoc:
        mong_doi = sorted(permitted_fields(canh_trong_bang[canh["to_state"]].guard_codes))
        assert canh["fields"] == mong_doi, canh["to_state"]

    # Và cụ thể, để người đọc bài kiểm thử thấy ngay nghĩa của nó
    phan_loai = next(c for c in di_duoc if "priority_code" in c["fields"])
    assert "request_type_code" in phan_loai["fields"]


def test_chi_tiet_goi_y_phong_ban_theo_loai_yeu_cau(client, session, rule_set):
    ho_so = _tao(session)
    mong_doi = session.scalar(
        select(RequestTypeRouting.department_code).where(
            RequestTypeRouting.request_type_code == ho_so.request_type_code,
            RequestTypeRouting.is_default,
        )
    )

    r = client.get(f"/coordination/requests/{ho_so.id}")
    assert r.json()["suggested_department"]["code"] == mong_doi


def test_ho_so_chua_co_loai_thi_khong_goi_y_phong(client, session, rule_set):
    ho_so = _tao(session, loai=False)
    assert client.get(f"/coordination/requests/{ho_so.id}").json()["suggested_department"] is None


def test_chi_tiet_ho_so_khong_ton_tai_tra_404(client, rule_set):
    r = client.get("/coordination/requests/999999999")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "case-not-found"


# ---------------------------------------------------------------------------
# Vòng trọn vẹn — định nghĩa hoàn thành của #82
# ---------------------------------------------------------------------------


def test_phan_loai_roi_chuyen_ve_phong_ban_nguoi_gui_thay_ngay(client, session, rule_set):
    ho_so = _tao(session)
    mac_dinh = session.scalar(select(Priority.code).where(Priority.is_default))

    # 1. Phân loại
    chi_tiet = client.get(f"/coordination/requests/{ho_so.id}").json()
    phan_loai = next(c for c in chi_tiet["allowed_transitions"] if "priority_code" in c["fields"])
    r = client.post(
        f"/coordination/requests/{ho_so.id}/transitions",
        json={"to_state": phan_loai["to_state"], "changes": {"priority_code": mac_dinh}},
    )
    assert r.status_code == 200, r.text
    assert r.json()["priority"]["code"] == mac_dinh

    # 2. Chuyển về phòng gợi ý
    ve_phong = next(
        c for c in r.json()["allowed_transitions"] if "department_code" in c["fields"]
    )
    phong = r.json()["suggested_department"]["code"]
    r = client.post(
        f"/coordination/requests/{ho_so.id}/transitions",
        json={"to_state": ve_phong["to_state"], "changes": {"department_code": phong}},
    )
    assert r.status_code == 200, r.text
    trang_thai_moi = r.json()["state"]["code"]

    # 3. Hồ sơ rời hàng đợi...
    con_trong_hang = {m["id"] for m in client.get("/coordination/queue").json()["items"]}
    assert ho_so.id not in con_trong_hang

    # ...và người gửi thấy đúng trạng thái mới trên cổng của mình
    _goi_bang(client, NGUOI_GUI)
    cong = client.get(f"/requests/{ho_so.id}").json()
    assert cong["state"]["code"] == trang_thai_moi
    assert cong["department"]["code"] == phong
    assert [e["actor_label"] for e in cong["history"]] == ["Bình Trần", "Bình Trần"]


def test_ma_danh_muc_go_sai_tra_422_chu_khong_500(client, session, rule_set):
    """Lỗ mà đột biến ở #78 lộ ra: không kiểm thì khóa ngoại nổ thành 500."""
    ho_so = _tao(session)
    mac_dinh = session.scalar(select(Priority.code).where(Priority.is_default))
    r = client.post(
        f"/coordination/requests/{ho_so.id}/transitions",
        json={"to_state": "classified", "changes": {"priority_code": "khong-co-that"}},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "invalid-field-value"

    # Bị từ chối thì hồ sơ vẫn nguyên chỗ cũ, gửi lại đúng thì đi được
    r = client.post(
        f"/coordination/requests/{ho_so.id}/transitions",
        json={"to_state": "classified", "changes": {"priority_code": mac_dinh}},
    )
    assert r.status_code == 200, r.text


def test_truong_canh_khong_cho_dat_bi_tu_choi_qua_http(client, session, rule_set):
    """#78 nhìn từ phía HTTP: cổng nhận `changes`, engine vẫn kiểm theo cạnh."""
    ho_so = _tao(session)
    r = client.post(
        f"/coordination/requests/{ho_so.id}/transitions",
        json={
            "to_state": "awaiting-info",
            "note": "Máy chiếu phòng nào?",
            "changes": {"priority_code": "urgent"},
        },
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "field-not-permitted"
