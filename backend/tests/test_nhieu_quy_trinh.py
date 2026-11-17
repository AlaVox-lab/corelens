# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Nền tảng lõi Mức 2: động cơ luồng công việc chạy nhiều quy trình (#376), và realm mẫu siết bảo mật (#377).
#
# Năm nhóm bài:
#
#   1. Dữ liệu — danh mục quy trình, mỗi quy trình đúng một bộ đang bật (chỉ mục và kiem_tra_cau_hinh), kích
#      hoạt bộ mới của một quy trình không đụng quy trình khác, loại yêu cầu không đổi được sang quy trình khác.
#   2. API lõi — danh mục quy trình, lọc theo quy trình, tạo hồ sơ của quy trình thứ hai bằng loại của nó.
#   3. Cửa bước chuyển trung lập với vai — đúng vai đúng phòng đi được, sai vai bị engine chặn, sai phòng không
#      thấy hồ sơ; chạy trọn quy trình thứ hai tới trạng thái kết thúc chỉ qua /core/v1.
#   4. Không lẫn quy trình — hồ sơ của quy trình thứ hai không vào hàng đợi, buồng lái, cổng người gửi, view
#      báo cáo của quy trình mặc định; nhật ký xuất mang cột quy trình và lọc được.
#   5. Realm — chống dò mật khẩu bật và khóa tạm thật, chính sách mật khẩu chặn mật khẩu ngắn, tài khoản mẫu vẫn
#      đăng nhập được.
#
# Không bài nào viết mã quy trình, trạng thái hay loại: quy trình thứ hai là quy trình đầu tiên không mang cờ
# `is_app_default`, mọi bước là bước chính lõi trả về cho người gọi.

from __future__ import annotations

import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.auth.dependencies import current_actor, current_claims
from app.cau_hinh.bo_quy_tac import kich_hoat, sao_chep
from app.config import get_settings
from app.db import get_session
from app.main import app
from app.models.case import EventLog, Request
from app.models.workflow_config import Department, Process, RequestType, RuleSet
from app.workflow.context import Actor
from app.workflow.engine import (
    create_case,
    get_active_rule_set,
    ma_quy_trinh_ung_dung,
    perform_transition,
    rule_sets_in_use,
)
from app.workflow.errors import InvalidFieldValue
from tests.test_cong_api import MAT_KHAU_MAU, MAT_KHAU_QUAN_TRI, QUAN_TRI, _goi_quan_tri, lay_token
from tests.truong_mau import chi_tiet_mau

LOI = "/core/v1/workflow"


# ---------------------------------------------------------------------------
# Dữ liệu dùng chung
# ---------------------------------------------------------------------------


@pytest.fixture
def quy_trinh_khac(session) -> Process:
    """Quy trình đầu tiên không phải của ứng dụng minh họa — quy trình mẫu thứ hai của dữ liệu khởi tạo."""
    qt = session.scalars(
        select(Process).where(Process.is_app_default.is_(False)).order_by(Process.display_order, Process.code)
    ).first()
    if qt is None:
        pytest.skip("Dữ liệu khởi tạo chưa khai quy trình thứ hai (infra/seed/06-…).")
    return qt


@pytest.fixture
def hai_phong(session) -> tuple[str, str]:
    ma = session.scalars(
        select(Department.code).where(Department.is_active).order_by(Department.display_order)
    ).all()
    if len(ma) < 2:
        pytest.skip("Cần hai phòng ban đang hoạt động.")
    return ma[0], ma[1]


@pytest.fixture
def vai(hai_phong):
    phong, khac = hai_phong
    return {
        "gui": Actor(id="qt2-gui-376", name="Người đề xuất 376", roles=frozenset({"requester"})),
        "gui_khac": Actor(id="qt2-gui-khac-376", name="Người gửi khác 376", roles=frozenset({"requester"})),
        "truong_phong": Actor(id="qt2-tp-376", name="Trưởng phòng 376", roles=frozenset({"approver"}),
                              departments=frozenset({phong})),
        "truong_phong_khac": Actor(id="qt2-tpk-376", name="Trưởng phòng khác 376", roles=frozenset({"approver"}),
                                   departments=frozenset({khac})),
        "dieu_phoi": Actor(id="qt2-dp-376", name="Điều phối 376", roles=frozenset({"classifier"})),
        "quan_tri": Actor(id="qt2-qt-376", name="Quản trị 376", roles=frozenset({"administrator"})),
        "phong": phong,
    }


@pytest.fixture
def client(session, vai):
    tac_nhan = {"actor": vai["gui"]}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: tac_nhan["actor"]
    app.dependency_overrides[current_claims] = lambda: {"sub": tac_nhan["actor"].id, "name": tac_nhan["actor"].name}
    with TestClient(app) as c:
        def la(ai: Actor) -> TestClient:
            tac_nhan["actor"] = ai
            return c

        c.la = la
        yield c
    app.dependency_overrides.clear()


# Số tiền đủ lớn để quy trình mua sắm mẫu đi đủ hai cấp duyệt (#397 rẽ nhánh theo trường số này)
SO_TIEN_LON = 50_000_000


def _tao_qua_loi(client, vai, quy_trinh: Process, so_tien: int = SO_TIEN_LON) -> dict:
    """Người đề xuất tạo một hồ sơ của quy trình thứ hai bằng loại đầu tiên của nó, chỉ qua /core/v1.

    Mọi trường số bắt buộc nhận `so_tien` — không biết tên trường, như ví dụ quy_trinh_mua_sam.py."""
    c = client.la(vai["gui"])
    loai = c.get(f"{LOI}/request-types", params={"process": quy_trinh.code}).json()[0]
    chi_tiet = chi_tiet_mau(loai)
    chi_tiet.update({t["code"]: so_tien for t in loai["fields"] if t["required"] and t["kind"] == "number"})
    tra = c.post(f"{LOI}/requests", json={
        "title": "Đề xuất mua máy chiếu phòng họp", "request_type_code": loai["code"], "details": chi_tiet,
    })
    assert tra.status_code == 201, tra.text
    return tra.json()


def _buoc_chinh(ho_so: dict) -> dict:
    return next(b for b in ho_so["allowed_transitions"] if b["is_primary"])


def _gui_duyet(client, vai, ho_so: dict) -> dict:
    """Người đề xuất đi bước chính, kèm phòng đề xuất nếu bước đó cho đặt phòng."""
    c = client.la(vai["gui"])
    buoc = _buoc_chinh(c.get(f"{LOI}/requests/{ho_so['id']}").json())
    thay_doi = {"department_code": vai["phong"]} if "department_code" in buoc["fields"] else {}
    tra = c.post(f"{LOI}/requests/{ho_so['id']}/transitions", json={"to_state": buoc["to_state"], "changes": thay_doi})
    assert tra.status_code == 200, tra.text
    return tra.json()


# ---------------------------------------------------------------------------
# 1. Dữ liệu
# ---------------------------------------------------------------------------


def test_moi_quy_trinh_dung_mot_bo_dang_bat_va_mot_quy_trinh_cua_ung_dung(session, quy_trinh_khac):
    assert len(session.scalars(select(Process).where(Process.is_app_default)).all()) == 1
    for qt in session.scalars(select(Process)):
        bat = session.scalars(select(RuleSet).where(RuleSet.process_code == qt.code, RuleSet.is_active)).all()
        assert len(bat) == 1, qt.code
        assert get_active_rule_set(session, qt.code).id == bat[0].id
    # Mỗi loại yêu cầu thuộc một quy trình đã khai; quy trình thứ hai có loại riêng
    assert session.scalars(select(RequestType).where(RequestType.process_code == quy_trinh_khac.code)).first()


def test_hai_bo_bat_trong_cung_quy_trinh_bi_chi_muc_chan(session, rule_set):
    with pytest.raises(DBAPIError, match="rule_sets_mot_bo_bat_moi_quy_trinh"):
        with session.begin_nested():
            moi = sao_chep(session, rule_set.id, "thu-376-hai-bo", "Bộ thử #376")
            session.execute(text("UPDATE rule_sets SET is_active = TRUE WHERE id = :id"), {"id": moi})


def test_quy_trinh_khong_bo_nao_bat_bi_ham_kiem_chan(session, quy_trinh_khac):
    with pytest.raises(DBAPIError, match="không có bộ quy tắc nào đang bật"):
        with session.begin_nested():
            session.execute(text("UPDATE rule_sets SET is_active = FALSE WHERE process_code = :q"),
                            {"q": quy_trinh_khac.code})
            session.execute(text("SELECT kiem_tra_cau_hinh()"))


def test_kich_hoat_bo_moi_khong_dung_quy_trinh_khac(session, rule_set, quy_trinh_khac):
    bo_khac = get_active_rule_set(session, quy_trinh_khac.code).id
    moi = sao_chep(session, rule_set.id, "thu-376-kich-hoat", "Bộ thử kích hoạt #376")
    assert session.get(RuleSet, moi).process_code == rule_set.process_code
    kich_hoat(session, moi)
    session.expire_all()
    assert get_active_rule_set(session, rule_set.process_code).id == moi
    assert get_active_rule_set(session, quy_trinh_khac.code).id == bo_khac


def test_ho_so_nhan_bo_cua_quy_trinh_ma_loai_thuoc_ve(session, rule_set, quy_trinh_khac):
    loai = session.scalars(select(RequestType.code).where(RequestType.process_code == quy_trinh_khac.code)).first()
    ho_so = create_case(session, title="Đề xuất thử #376", requester_id="qt2-gui-376", request_type_code=loai)
    assert ho_so.rule_set_id == get_active_rule_set(session, quy_trinh_khac.code).id
    # Lối gọi nội bộ không truyền loại: quy trình mặc định của ứng dụng
    assert create_case(session, title="Không loại #376", requester_id="qt2-gui-376").rule_set_id == rule_set.id


def test_khong_doi_loai_sang_quy_trinh_khac(session, rule_set, quy_trinh_khac):
    """Hồ sơ ghim bộ của quy trình lúc tạo: đổi sang loại của quy trình khác bị từ chối ở cửa engine."""
    loai_khac = session.scalars(
        select(RequestType.code).where(RequestType.process_code == quy_trinh_khac.code)
    ).first()
    ho_so = create_case(session, title="Sửa loại thử #376", requester_id="qt2-gui-376")
    sua = next(t for t in session.scalars(select(RuleSet)).all() if t.id == rule_set.id)  # noqa: F841
    nguoi_gui = Actor(id="qt2-gui-376", roles=frozenset({"requester"}))
    with pytest.raises(InvalidFieldValue, match="quy trình khác"):
        perform_transition(session, case_id=ho_so.id, to_state=ho_so.current_state, actor=nguoi_gui,
                           changes={"request_type_code": loai_khac})


# ---------------------------------------------------------------------------
# 2. API lõi
# ---------------------------------------------------------------------------


def test_danh_muc_quy_trinh_va_loc_theo_quy_trinh(client, session, quy_trinh_khac):
    c = client
    ds = c.get(f"{LOI}/processes").json()
    assert {q["code"] for q in ds} == set(session.scalars(select(Process.code)))
    assert [q["code"] for q in ds if q["is_app_default"]] == [ma_quy_trinh_ung_dung(session)]

    mac_dinh = c.get(f"{LOI}/request-types").json()
    khac = c.get(f"{LOI}/request-types", params={"process": quy_trinh_khac.code}).json()
    assert mac_dinh and khac
    assert {l["process_code"] for l in mac_dinh} == {ma_quy_trinh_ung_dung(session)}
    assert {l["process_code"] for l in khac} == {quy_trinh_khac.code}
    # Đường cũ của cổng người gửi: chỉ loại của quy trình mặc định, như trước
    assert c.get("/request-types").json() == mac_dinh

    trang_thai_khac = {s["code"] for s in c.get(f"{LOI}/states", params={"process": quy_trinh_khac.code}).json()}
    bo_khac = get_active_rule_set(session, quy_trinh_khac.code).id
    assert trang_thai_khac == set(session.scalars(text("SELECT code FROM states WHERE rule_set_id = :b"),
                                                  {"b": bo_khac}))
    assert c.get(f"{LOI}/states", params={"process": "khong-co-376"}).status_code == 422


def test_tao_ho_so_quy_trinh_thu_hai_qua_loi(client, session, vai, quy_trinh_khac):
    ho_so = _tao_qua_loi(client, vai, quy_trinh_khac)
    assert ho_so["process"]["code"] == quy_trinh_khac.code
    assert session.get(Request, ho_so["id"]).rule_set_id == get_active_rule_set(session, quy_trinh_khac.code).id
    # Trường riêng bắt buộc của loại vẫn được kiểm như mọi loại khác
    loai = client.get(f"{LOI}/request-types", params={"process": quy_trinh_khac.code}).json()[0]
    if any(t["required"] for t in loai["fields"]):
        tra = client.post(f"{LOI}/requests", json={"title": "Thiếu trường riêng #376", "request_type_code": loai["code"],
                                                   "details": {}})
        assert tra.status_code == 422


# ---------------------------------------------------------------------------
# 3. Cửa bước chuyển trung lập với vai
# ---------------------------------------------------------------------------


def test_chay_tron_quy_trinh_thu_hai_chi_qua_loi(client, session, vai, quy_trinh_khac):
    """Định nghĩa hoàn thành của #376 trong tiến trình: tạo → gửi duyệt → duyệt cấp một → duyệt cấp hai, mỗi
    bước do đúng vai đi qua cửa của lõi, tới trạng thái kết thúc."""
    ho_so = _gui_duyet(client, vai, _tao_qua_loi(client, vai, quy_trinh_khac))
    assert ho_so["department"]["code"] == vai["phong"]

    for ai in ("truong_phong", "dieu_phoi"):
        c = client.la(vai[ai])
        cho = c.get(f"{LOI}/requests", params={"process": quy_trinh_khac.code, "needs_action": True}).json()
        assert ho_so["id"] in {h["id"] for h in cho["items"]}, ai
        buoc = _buoc_chinh(c.get(f"{LOI}/requests/{ho_so['id']}").json())
        tra = c.post(f"{LOI}/requests/{ho_so['id']}/transitions",
                     json={"to_state": buoc["to_state"], "note": "Duyệt qua lõi." if buoc["requires_note"] else None})
        assert tra.status_code == 200, (ai, tra.text)
        ho_so = tra.json()

    assert ho_so["state"]["is_terminal"]
    nhat_ky = session.scalars(select(EventLog).where(EventLog.case_id == ho_so["id"]).order_by(EventLog.id)).all()
    assert [e.actor for e in nhat_ky] == [vai["gui"].id, vai["truong_phong"].id, vai["dieu_phoi"].id]
    assert len(ho_so["history"]) == 3


def _nguong(session, quy_trinh: Process) -> tuple[str, float]:
    """Trường và ngưỡng của điều kiện "<" trên cạnh rời trạng thái chờ trưởng phòng — đọc từ dữ liệu."""
    dong = session.execute(text(
        "SELECT c.field_code, c.value FROM transition_conditions c "
        "JOIN transitions t ON t.id = c.transition_id JOIN rule_sets b ON b.id = t.rule_set_id "
        "WHERE b.process_code = :q AND b.is_active AND c.operator = '<'"), {"q": quy_trinh.code}).first()
    if dong is None:
        pytest.skip("Quy trình thứ hai chưa khai điều kiện trên cạnh (infra/seed/07).")
    return dong[0], float(dong[1])


def test_duoi_nguong_truong_phong_duyet_la_xong(client, session, vai, quy_trinh_khac):
    """#397: dưới ngưỡng, trưởng phòng chỉ thấy một nút duyệt và đi thẳng tới trạng thái kết thúc."""
    _, nguong = _nguong(session, quy_trinh_khac)
    ho_so = _gui_duyet(client, vai, _tao_qua_loi(client, vai, quy_trinh_khac, so_tien=int(nguong) - 1))

    c = client.la(vai["truong_phong"])
    chi_tiet = c.get(f"{LOI}/requests/{ho_so['id']}").json()
    duyet = [b for b in chi_tiet["allowed_transitions"] if b["is_primary"]]
    assert len(duyet) == 1
    tra = c.post(f"{LOI}/requests/{ho_so['id']}/transitions", json={"to_state": duyet[0]["to_state"]})
    assert tra.status_code == 200, tra.text
    assert tra.json()["state"]["is_terminal"]


def test_dung_nguong_phai_qua_cap_hai(client, session, vai, quy_trinh_khac):
    """Đúng bằng ngưỡng là nhánh trên: hai điều kiện bù nhau, không có số nào lọt giữa hai cạnh."""
    _, nguong = _nguong(session, quy_trinh_khac)
    ho_so = _gui_duyet(client, vai, _tao_qua_loi(client, vai, quy_trinh_khac, so_tien=int(nguong)))

    c = client.la(vai["truong_phong"])
    duyet = [b for b in c.get(f"{LOI}/requests/{ho_so['id']}").json()["allowed_transitions"] if b["is_primary"]]
    assert len(duyet) == 1
    tra = c.post(f"{LOI}/requests/{ho_so['id']}/transitions", json={"to_state": duyet[0]["to_state"]})
    assert tra.status_code == 200, tra.text
    assert not tra.json()["state"]["is_terminal"]


def test_di_canh_khong_thoa_dieu_kien_bi_tu_choi(client, session, vai, quy_trinh_khac):
    """Gọi thẳng cạnh dưới ngưỡng với hồ sơ trên ngưỡng: engine từ chối, hồ sơ không đổi."""
    _, nguong = _nguong(session, quy_trinh_khac)
    ho_so = _gui_duyet(client, vai, _tao_qua_loi(client, vai, quy_trinh_khac, so_tien=int(nguong) * 2))
    dich = session.scalar(text(
        "SELECT t.to_state FROM transition_conditions c JOIN transitions t ON t.id = c.transition_id "
        "JOIN rule_sets b ON b.id = t.rule_set_id WHERE b.process_code = :q AND b.is_active AND c.operator = '<'"),
        {"q": quy_trinh_khac.code})

    c = client.la(vai["truong_phong"])
    tra = c.post(f"{LOI}/requests/{ho_so['id']}/transitions", json={"to_state": dich})
    assert tra.status_code in (403, 409, 422), tra.text
    assert "điều kiện" in tra.text
    assert c.get(f"{LOI}/requests/{ho_so['id']}").json()["state"]["code"] == ho_so["state"]["code"]


def test_sai_phong_khong_thay_sai_vai_bi_chan(client, vai, quy_trinh_khac):
    ho_so = _gui_duyet(client, vai, _tao_qua_loi(client, vai, quy_trinh_khac))
    duong = f"{LOI}/requests/{ho_so['id']}"
    buoc = _buoc_chinh(client.la(vai["truong_phong"]).get(duong).json())

    # Trưởng phòng phòng khác: hồ sơ ngoài phạm vi, 404 ở cả đọc lẫn đi bước — không lộ hồ sơ có thật
    c = client.la(vai["truong_phong_khac"])
    assert c.get(duong).status_code == 404
    assert c.post(f"{duong}/transitions", json={"to_state": buoc["to_state"]}).status_code == 404
    assert ho_so["id"] not in {h["id"] for h in c.get(f"{LOI}/requests", params={
        "process": ho_so["process"]["code"]}).json()["items"]}

    # Người gửi khác: không thấy
    assert client.la(vai["gui_khac"]).get(duong).status_code == 404

    # Chính người đề xuất thấy hồ sơ, nhưng không đi được bước của trưởng phòng: engine trả 403
    c = client.la(vai["gui"])
    assert buoc["to_state"] not in {b["to_state"] for b in c.get(duong).json()["allowed_transitions"]}
    tra = c.post(f"{duong}/transitions", json={"to_state": buoc["to_state"]})
    assert tra.status_code == 403, tra.text
    assert tra.json()["detail"]["code"] == "role-not-permitted"

    # Điều phối viên thấy mọi hồ sơ, nhưng duyệt cấp một là việc của trưởng phòng
    c = client.la(vai["dieu_phoi"])
    assert c.get(duong).status_code == 200
    assert c.post(f"{duong}/transitions", json={"to_state": buoc["to_state"]}).status_code == 403


def test_duong_cu_giu_cua_nguoi_gui(client, vai, quy_trinh_khac):
    """Đường cũ ngoài /core/v1 giữ nguyên: chỉ hồ sơ do chính người gọi tạo."""
    ho_so = _tao_qua_loi(client, vai, quy_trinh_khac)
    assert client.la(vai["dieu_phoi"]).get(f"/requests/{ho_so['id']}").status_code == 404
    assert client.la(vai["dieu_phoi"]).get(f"{LOI}/requests/{ho_so['id']}").status_code == 200


# ---------------------------------------------------------------------------
# 4. Không lẫn quy trình
# ---------------------------------------------------------------------------


def test_ho_so_quy_trinh_thu_hai_khong_lot_vao_man_cua_ung_dung(client, session, vai, quy_trinh_khac):
    ho_so = _gui_duyet(client, vai, _tao_qua_loi(client, vai, quy_trinh_khac))
    ma = ho_so["id"]

    # Bộ quy tắc còn hồ sơ chạy theo của quy trình mặc định không gồm bộ của quy trình thứ hai
    assert session.get(Request, ma).rule_set_id not in rule_sets_in_use(session, ma_quy_trinh_ung_dung(session))

    # Cổng người gửi (đường cũ) và danh sách mặc định của lõi: chỉ quy trình mặc định
    for duong in ("/requests", f"{LOI}/requests"):
        assert ma not in {h["id"] for h in client.la(vai["gui"]).get(duong).json()["items"]}, duong
    assert ma in {h["id"] for h in client.get(f"{LOI}/requests", params={"process": quy_trinh_khac.code})
                  .json()["items"]}

    # Hai buồng lái của ứng dụng minh họa
    assert ma not in {h["id"] for h in client.la(vai["dieu_phoi"]).get("/coordination/queue",
                                                                         params={"limit": 200}).json()["items"]}
    assert ma not in {h["id"] for h in client.la(vai["truong_phong"]).get("/department/queue",
                                                                            params={"limit": 200}).json()["items"]}

    # Lớp báo cáo: bảng điều khiển đọc bao_cao_ho_so — chỉ quy trình mặc định; nhật ký mang cột quy trình
    session.commit()
    assert session.execute(text("SELECT count(*) FROM bao_cao_ho_so WHERE ma_ho_so = :m"), {"m": ma}).scalar() == 0
    assert set(session.scalars(text("SELECT DISTINCT process_code FROM bao_cao_nhat_ky WHERE case_id = :m"),
                               {"m": ma})) == {quy_trinh_khac.code}


def test_xuat_nhat_ky_loc_theo_quy_trinh(client, vai, quy_trinh_khac):
    ho_so = _gui_duyet(client, vai, _tao_qua_loi(client, vai, quy_trinh_khac))
    c = client.la(vai["quan_tri"])
    tat_ca = c.get("/core/v1/events", params={"format": "json"}).json()
    chi_khac = c.get("/core/v1/events", params={"format": "json", "process": quy_trinh_khac.code}).json()
    assert chi_khac and {d["process_code"] for d in chi_khac} == {quy_trinh_khac.code}
    assert ho_so["id"] in {d["case_id"] for d in chi_khac}
    assert {d["case_id"] for d in chi_khac} <= {d["case_id"] for d in tat_ca}
    assert c.get("/core/v1/events", params={"process": "khong-co-376"}).status_code == 422


# ---------------------------------------------------------------------------
# 5. Realm mẫu (#377)
# ---------------------------------------------------------------------------


def _token_quan_tri() -> str:
    cs = get_settings()
    du_lieu = urllib.parse.urlencode(
        {"grant_type": "password", "client_id": "admin-cli", "username": QUAN_TRI, "password": MAT_KHAU_QUAN_TRI}
    ).encode()
    try:
        with urllib.request.urlopen(f"{cs.keycloak_internal_url}/realms/master/protocol/openid-connect/token",
                                    data=du_lieu, timeout=10) as r:
            return json.load(r)["access_token"]
    except (urllib.error.URLError, OSError, KeyError) as loi:
        pytest.skip(f"Không đăng nhập được tài khoản quản trị Keycloak ({loi}).")


def _dang_nhap(ten: str, mat_khau: str) -> int:
    """Mã HTTP của một lần đăng nhập bằng mật khẩu qua client của cổng người dùng."""
    cs = get_settings()
    du_lieu = urllib.parse.urlencode({
        "grant_type": "password", "client_id": "dx-portal", "client_secret": "doi_bi_mat_nay_truoc_khi_trien_khai",
        "username": ten, "password": mat_khau,
    }).encode()
    try:
        with urllib.request.urlopen(
            f"{cs.keycloak_internal_url}/realms/{cs.keycloak_realm}/protocol/openid-connect/token",
            data=du_lieu, timeout=10,
        ) as r:
            return r.status
    except urllib.error.HTTPError as loi:
        return loi.code


def test_realm_chong_do_mat_khau_khoa_tam_va_tai_khoan_mau_van_dang_nhap(session):
    token = _token_quan_tri()
    cs = get_settings()
    goc = f"{cs.keycloak_internal_url}/admin/realms/{cs.keycloak_realm}"
    _, than = _goi_quan_tri(goc, token, phuong_thuc="GET")
    realm = json.loads(than)
    assert realm["bruteForceProtected"] is True
    assert realm["permanentLockout"] is False
    assert "length(8)" in (realm.get("passwordPolicy") or "")

    # Chính sách mật khẩu: tạo tài khoản với mật khẩu ngắn bị từ chối
    ten = f"thu-376-{secrets.token_hex(3)}"
    with pytest.raises(urllib.error.HTTPError) as loi:
        _goi_quan_tri(f"{goc}/users", token, than={
            "username": ten, "enabled": True,
            "credentials": [{"type": "password", "value": "ngan", "temporary": False}],
        })
    assert loi.value.code == 400

    # Tài khoản thử với mật khẩu hợp lệ: sai liên tiếp tới ngưỡng thì bị khóa tạm, mật khẩu đúng cũng không vào
    mat_khau = secrets.token_urlsafe(12)
    _goi_quan_tri(f"{goc}/users", token, than={
        "username": ten, "enabled": True, "firstName": "Thử", "lastName": "Khóa", "email": f"{ten}@dx-os-lab.test",
        "emailVerified": True, "credentials": [{"type": "password", "value": mat_khau, "temporary": False}],
    })
    _, than = _goi_quan_tri(f"{goc}/users?username={ten}&exact=true", token, phuong_thuc="GET")
    id_tk = json.loads(than)[0]["id"]
    trang_thai_khoa = f"{goc}/attack-detection/brute-force/users/{id_tk}"
    # Hai lần sai cách nhau dưới `quickLoginCheckMilliSeconds` là "dò quá nhanh", Keycloak khóa ngay — giãn ra
    # để đo đúng ngưỡng `failureFactor`
    gian = realm["quickLoginCheckMilliSeconds"] / 1000 + 0.2
    try:
        assert _dang_nhap(ten, mat_khau) == 200
        for lan in range(1, realm["failureFactor"] + 1):
            time.sleep(gian)
            assert _dang_nhap(ten, mat_khau + "sai") in (400, 401)
            _, than = _goi_quan_tri(trang_thai_khoa, token, phuong_thuc="GET")
            # Chưa tới ngưỡng thì chưa khóa; lần thứ `failureFactor` thì khóa
            assert json.loads(than)["disabled"] is (lan == realm["failureFactor"]), lan
        assert _dang_nhap(ten, mat_khau) != 200
    finally:
        _goi_quan_tri(f"{goc}/attack-detection/brute-force/users/{id_tk}", _token_quan_tri(), phuong_thuc="DELETE")
        _goi_quan_tri(f"{goc}/users/{id_tk}", _token_quan_tri(), phuong_thuc="DELETE")

    # Tài khoản mẫu vẫn đạt chính sách và đăng nhập được trong trình diễn
    assert lay_token("an.nguyen")
    assert _dang_nhap("an.nguyen", MAT_KHAU_MAU) == 200
