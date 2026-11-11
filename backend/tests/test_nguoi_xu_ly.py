# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử gợi ý người xử lý cho trưởng phòng (#318).
#
# Đáp án biết trước: dựng một phòng có người rảnh và có kinh nghiệm, người bận, người chưa làm loại
# này, một người KHÔNG nhận được việc mà kinh nghiệm dày nhất, và một người phòng khác cũng vậy. Người
# rảnh có kinh nghiệm phải được gợi ý; hai người ngoài danh sách nhận việc không bao giờ được gợi ý.
#
# Mọi mã — trạng thái, cạnh, vai trò, loại — tra từ bộ quy tắc đang bật, không chép vào đây.

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.auth.dependencies import current_actor
from app.auth.directory import DirectoryUnavailable, Person, get_directory
from app.config import get_settings
from app.db import get_session
from app.intelligence.goi_y import NGUON_TAI_VIEC, goi_y_nguoi_xu_ly
from app.intelligence.nguoi_xu_ly import (
    PHAM_VI_NGUOI_DUOC_GIAO,
    goi_y_khi_ve_phong,
    trang_thai_giao_viec,
)
from app.main import app
from app.models.case import EventLog, Request
from app.models.workflow_config import Department, RequestType, Transition
from app.workflow.assignment import (
    _canh_giao_viec,
    trang_thai_hang_doi_phong_ban,
    vai_tro_giao_viec,
    vai_tro_nhan_viec,
)
from app.workflow.context import Actor
from app.workflow.engine import create_case


class DanhBaGia:
    """Thay Keycloak: mỗi phòng một danh sách người; `loi` thì mọi lần tra đều hỏng."""

    def __init__(self, theo_phong: dict[str, list[Person]], loi: str | None = None):
        self.theo_phong = theo_phong
        self.loi = loi

    def department_members(self, department_code: str) -> list[Person]:
        if self.loi:
            raise DirectoryUnavailable(self.loi)
        return self.theo_phong.get(department_code, [])


@pytest.fixture
def canh(session, rule_set):
    """(trạng thái chờ giao việc, cạnh giao việc từ đó, trạng thái đang giữ, cạnh làm xong)."""
    giao = sorted(
        (t for t in _canh_giao_viec(session, rule_set.id) if t.from_state != t.to_state),
        key=lambda t: t.display_order,
    )
    xong = session.scalars(
        select(Transition).where(
            Transition.rule_set_id == rule_set.id,
            Transition.primary_scope == PHAM_VI_NGUOI_DUOC_GIAO,
            Transition.is_system.is_(False),
        )
    ).first()
    if not giao or xong is None:
        pytest.skip("Bộ quy tắc không có cạnh giao việc hay bước chính của người được giao.")
    hang_doi = {t.code for t in trang_thai_hang_doi_phong_ban(session, rule_set.id)}
    assert giao[0].to_state in hang_doi
    return giao[0].from_state, giao[0], giao[0].to_state, xong


@pytest.fixture
def hai_loai(session) -> tuple[str, str]:
    ma = session.scalars(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    ).all()
    if len(ma) < 2:
        pytest.skip("Cần ít nhất hai loại yêu cầu đang bật.")
    return ma[0], ma[1]


@pytest.fixture
def hai_phong(session) -> tuple[str, str]:
    ma = session.scalars(
        select(Department.code).where(Department.is_active).order_by(Department.display_order)
    ).all()
    if len(ma) < 2:
        pytest.skip("Cần ít nhất hai phòng đang hoạt động.")
    return ma[0], ma[1]


def _nguoi(session, rule_set, ma: str, ten: str, nhan_viec: bool = True) -> Person:
    vai = vai_tro_nhan_viec(session, rule_set.id) if nhan_viec else vai_tro_giao_viec(session, rule_set.id)
    return Person(id=ma, username=ma, name=ten, roles=frozenset(vai))


def _ho_so(session, loai: str, phong: str, trang_thai: str, nguoi_xu_ly: str | None = None) -> Request:
    ho_so = create_case(session, title="Hồ sơ dựng cảnh #318", requester_id="nd-gui-318", request_type_code=loai)
    session.flush()
    session.execute(
        update(Request)
        .where(Request.id == ho_so.id)
        .values(department_code=phong, current_state=trang_thai, assignee_id=nguoi_xu_ly)
    )
    session.flush()
    session.refresh(ho_so)
    return ho_so


def _da_lam_xong(session, nguoi: str, loai: str, phong: str, xong: Transition, so: int) -> None:
    """`so` hồ sơ loại `loai` mà `nguoi` đã đi cạnh làm xong — dòng nhật ký như engine ghi."""
    for _ in range(so):
        ho_so = _ho_so(session, loai, phong, xong.to_state)
        session.add(
            EventLog(
                case_id=ho_so.id,
                activity=xong.activity_code,
                actor=nguoi,
                actor_label=nguoi,
                from_state=xong.from_state,
                to_state=xong.to_state,
            )
        )
    session.flush()


@pytest.fixture
def canh_dung(session, rule_set, canh, hai_loai, hai_phong):
    """Phòng P có: An (rảnh, đã làm 3 hồ sơ loại L), Bình (giữ 2 việc, đã làm 5), Chi (rảnh, chưa làm
    loại L — nhưng làm 9 hồ sơ loại khác), Dũng (không nhận được việc, đã làm 20). Phòng Q có Em (rảnh,
    đã làm 30 hồ sơ loại L)."""
    cho_giao, _, dang_giu, xong = canh
    loai, loai_khac = hai_loai
    p, q = hai_phong
    an = _nguoi(session, rule_set, "nd-an-318", "An Lê")
    binh = _nguoi(session, rule_set, "nd-binh-318", "Bình Phạm")
    chi = _nguoi(session, rule_set, "nd-chi-318", "Chi Võ")
    dung = _nguoi(session, rule_set, "nd-dung-318", "Dũng Hồ", nhan_viec=False)
    em = _nguoi(session, rule_set, "nd-em-318", "Em Đỗ")
    _da_lam_xong(session, an.id, loai, p, xong, 3)
    _da_lam_xong(session, binh.id, loai, p, xong, 5)
    _da_lam_xong(session, chi.id, loai_khac, p, xong, 9)
    _da_lam_xong(session, dung.id, loai, p, xong, 20)
    _da_lam_xong(session, em.id, loai, q, xong, 30)
    for _ in range(2):
        _ho_so(session, loai_khac, p, dang_giu, nguoi_xu_ly=binh.id)
    danh_ba = DanhBaGia({p: [an, binh, chi, dung], q: [em]})
    ho_so = _ho_so(session, loai, p, cho_giao)
    session.commit()
    return {"ho_so": ho_so, "danh_ba": danh_ba, "an": an, "binh": binh, "chi": chi, "dung": dung, "em": em, "p": p}


def test_trang_thai_cho_giao_viec_suy_tu_bo_quy_tac(session, rule_set, canh):
    cho_giao, _, dang_giu, _ = canh
    giao_viec = trang_thai_giao_viec(session, rule_set.id)
    assert cho_giao in giao_viec
    # Hồ sơ đã giao người thì không còn chờ giao — trừ khi bộ quy tắc cho giao lại ngay tại đó
    assert dang_giu not in giao_viec or any(
        t.from_state == t.to_state == dang_giu for t in _canh_giao_viec(session, rule_set.id)
    )


def test_nguoi_ranh_co_kinh_nghiem_duoc_goi_y(session, canh_dung):
    ghi_chu = goi_y_khi_ve_phong(session, canh_dung["danh_ba"], canh_dung["ho_so"].id)

    assert ghi_chu["id"] == canh_dung["an"].id
    session.refresh(canh_dung["ho_so"])
    ho_so = canh_dung["ho_so"]
    assert ho_so.suggested_assignee_id == canh_dung["an"].id
    # Trường quyết định không đổi
    assert ho_so.assignee_id is None
    goi_y = goi_y_nguoi_xu_ly(session, ho_so)
    assert goi_y.code == canh_dung["an"].id
    assert goi_y.label == "An Lê"
    assert goi_y.source == NGUON_TAI_VIEC
    assert goi_y.reason == "Chưa giữ việc nào, đã xử lý 3 hồ sơ cùng loại."


def test_nguoi_ngoai_danh_sach_nhan_viec_khong_bao_gio_duoc_goi_y(session, canh_dung):
    """Bỏ hết người nhận được việc khỏi phòng: người không nhận được việc (kinh nghiệm dày nhất) và
    người phòng khác vẫn không được gợi ý — không có gợi ý nào."""
    danh_ba = DanhBaGia({canh_dung["p"]: [canh_dung["dung"]]})
    assert goi_y_khi_ve_phong(session, danh_ba, canh_dung["ho_so"].id) is None
    session.refresh(canh_dung["ho_so"])
    assert canh_dung["ho_so"].suggested_assignee_id is None


def test_trong_so_trong_cau_hinh(session, canh_dung, monkeypatch):
    """Tải việc không tính nữa thì người kinh nghiệm hơn — Bình — được gợi ý."""
    monkeypatch.setattr(get_settings(), "assignee_suggest_load_weight", 0.0)
    ghi_chu = goi_y_khi_ve_phong(session, canh_dung["danh_ba"], canh_dung["ho_so"].id)
    assert ghi_chu["id"] == canh_dung["binh"].id
    assert ghi_chu["reason"] == "Đang giữ 2 việc, đã xử lý 5 hồ sơ cùng loại."


def test_tat_goi_y_thi_khong_ghi_gi(session, canh_dung, monkeypatch):
    monkeypatch.setattr(get_settings(), "assignee_suggest_enabled", False)
    assert goi_y_khi_ve_phong(session, canh_dung["danh_ba"], canh_dung["ho_so"].id) is None
    session.refresh(canh_dung["ho_so"])
    assert canh_dung["ho_so"].suggested_assignee_id is None


def test_danh_ba_khong_tra_loi_thi_khong_goi_y_va_giu_goi_y_cu(session, canh_dung):
    goi_y_khi_ve_phong(session, canh_dung["danh_ba"], canh_dung["ho_so"].id)
    hong = DanhBaGia({}, loi="Keycloak không trả lời")
    assert goi_y_khi_ve_phong(session, hong, canh_dung["ho_so"].id) is None
    session.refresh(canh_dung["ho_so"])
    assert canh_dung["ho_so"].suggested_assignee_id == canh_dung["an"].id


def test_ho_so_khong_cho_giao_viec_thi_khong_tinh(session, canh_dung, canh):
    _, _, dang_giu, _ = canh
    session.execute(update(Request).where(Request.id == canh_dung["ho_so"].id).values(current_state=dang_giu))
    session.commit()
    assert goi_y_khi_ve_phong(session, canh_dung["danh_ba"], canh_dung["ho_so"].id) is None


def test_ghi_goi_y_khong_doi_updated_at(session, canh_dung):
    ho_so = canh_dung["ho_so"]
    truoc = ho_so.updated_at
    goi_y_khi_ve_phong(session, canh_dung["danh_ba"], ho_so.id)
    session.refresh(ho_so)
    assert ho_so.updated_at == truoc


# ---------------------------------------------------------------------------
# Qua HTTP: mở ô chọn tính lại, giữ hay ghi đè ghi nhật ký
# ---------------------------------------------------------------------------


@pytest.fixture
def client(session):
    trang_thai: dict = {"actor": None, "danh_ba": None}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: trang_thai["actor"]
    app.dependency_overrides[get_directory] = lambda: trang_thai["danh_ba"]
    with TestClient(app) as c:
        c.trang_thai = trang_thai
        yield c
    app.dependency_overrides.clear()


def _truong_phong(session, rule_set, phong: str) -> Actor:
    return Actor(
        id="nd-tp-318",
        name="Trưởng Phòng",
        roles=frozenset(vai_tro_giao_viec(session, rule_set.id)),
        departments=frozenset({phong}),
    )


def test_mo_o_chon_tinh_lai_khi_tai_viec_doi(client, session, rule_set, canh, canh_dung):
    _, _, dang_giu, _ = canh
    ho_so, p = canh_dung["ho_so"], canh_dung["p"]
    client.trang_thai.update(actor=_truong_phong(session, rule_set, p), danh_ba=canh_dung["danh_ba"])

    dau = client.get(f"/departments/{p}/assignees", params={"case_id": ho_so.id})
    assert dau.status_code == 200, dau.text
    assert dau.json()["suggestion"]["code"] == canh_dung["an"].id
    assert dau.json()["suggestion"]["source"] == NGUON_TAI_VIEC

    # An nhận thêm ba việc: không còn rảnh nhất
    for _ in range(3):
        _ho_so(session, canh_dung["ho_so"].request_type_code, p, dang_giu, nguoi_xu_ly=canh_dung["an"].id)
    session.commit()
    sau = client.get(f"/departments/{p}/assignees", params={"case_id": ho_so.id}).json()
    assert sau["suggestion"]["code"] != canh_dung["an"].id
    assert sau["suggestion"]["code"] in {nguoi["id"] for nguoi in sau["people"]}
    session.refresh(ho_so)
    assert ho_so.suggested_assignee_id == sau["suggestion"]["code"]

    # Chi tiết hồ sơ mang đúng gợi ý đã lưu
    chi_tiet = client.get(f"/department/requests/{ho_so.id}").json()
    assert chi_tiet["suggested_assignee"]["code"] == sau["suggestion"]["code"]


def test_mo_o_chon_khi_danh_ba_hong_van_503_khong_goi_y(client, session, rule_set, canh_dung):
    p = canh_dung["p"]
    client.trang_thai.update(
        actor=_truong_phong(session, rule_set, p), danh_ba=DanhBaGia({}, loi="Keycloak tắt")
    )
    tra = client.get(f"/departments/{p}/assignees", params={"case_id": canh_dung["ho_so"].id})
    assert tra.status_code == 503


def test_ho_so_phong_khac_khong_xin_duoc_goi_y(client, session, rule_set, canh_dung, hai_phong):
    q = hai_phong[1]
    client.trang_thai.update(actor=_truong_phong(session, rule_set, q), danh_ba=canh_dung["danh_ba"])
    tra = client.get(f"/departments/{q}/assignees", params={"case_id": canh_dung["ho_so"].id})
    assert tra.status_code == 404


@pytest.mark.parametrize("giu", [True, False])
def test_giu_hay_doi_goi_y_deu_co_dong_nhat_ky(client, session, rule_set, canh, canh_dung, giu):
    _, canh_giao, _, _ = canh
    ho_so, p = canh_dung["ho_so"], canh_dung["p"]
    client.trang_thai.update(actor=_truong_phong(session, rule_set, p), danh_ba=canh_dung["danh_ba"])
    client.get(f"/departments/{p}/assignees", params={"case_id": ho_so.id})

    chon = canh_dung["an"].id if giu else canh_dung["chi"].id
    tra = client.post(
        f"/department/requests/{ho_so.id}/transitions",
        json={"to_state": canh_giao.to_state, "changes": {"assignee_id": chon}},
    )
    assert tra.status_code == 200, tra.text
    dong = session.scalars(
        select(EventLog).where(EventLog.case_id == ho_so.id).order_by(EventLog.id.desc())
    ).first()
    dau = dong.suggestion["assignee_id"]
    assert dau == {
        "suggested": canh_dung["an"].id,
        "chosen": chon,
        "overridden": not giu,
        "source": NGUON_TAI_VIEC,
        "confidence": None,
    }
