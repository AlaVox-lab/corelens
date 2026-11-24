# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Nhật ký kiểm toán truy cập dữ liệu cá nhân (#431): bảng `access_audit_log`, app/kiem_toan.py.
#
# Định nghĩa hoàn thành của issue: mở một hồ sơ sinh bản ghi kiểm toán; có API tra cứu cho quản trị viên. Các bài:
#
#   Ghi — bốn loại (xem chi tiết ở hai buồng lái và lõi, xem liên hệ, tải tệp, xuất CSV/JSON/XES), mỗi loại đúng
#     một dòng, đúng tác nhân, đúng kênh; không ghi người gửi xem hồ sơ của mình, không ghi bước chuyển, danh sách,
#     hàng đợi, lần bị 403/404; ghi hỏng thì trang vẫn trả.
#   Lược đồ — chỉ ghi thêm (UPDATE, DELETE bị từ chối); xóa hồ sơ thì vết ở lại, `case_id` thành NULL.
#   Tra cứu — chỉ quản trị viên; lọc từng tham số; phân trang; mới nhất trước; `at` UTC; không tự sinh dòng.
#
# Dòng ghi đi qua `kiem_toan.mo_phien`; bài thay bằng phiên của bài để dòng thấy được hồ sơ bài vừa tạo và hoàn
# tác ở cuối bài (conftest.py).

from __future__ import annotations

import datetime as dt
import uuid
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app import kiem_toan
from app.auth.dependencies import current_actor, current_claims
from app.auth.directory import Contact, get_directory
from app.db import get_session
from app.main import app
from app.models.case import CaseAttachment, Request
from app.models.quan_tri import AccessAuditLog
from app.models.workflow_config import Priority, RequestType
from app.storage import objects
from app.workflow.context import Actor
from app.workflow.coordination import VAI_TRO_DIEU_PHOI
from app.workflow.engine import create_case, perform_transition

DUOI = uuid.uuid4().hex[:6]
NGUOI_GUI = Actor(id=f"kt-gui-{DUOI}", name="An Nguyễn", roles=frozenset({"requester"}))
DIEU_PHOI = Actor(id=f"kt-dp-{DUOI}", name="Bình Trần", roles=frozenset({VAI_TRO_DIEU_PHOI}))
QUAN_TRI = Actor(id=f"kt-qt-{DUOI}", name="Quản Trị", roles=frozenset({"administrator"}))


def _truong_phong(phong: str, ma: str = "kt-tp") -> Actor:
    return Actor(id=f"{ma}-{DUOI}", name="Dung Phạm", roles=frozenset({"approver"}), departments=frozenset({phong}))


class DanhBaGia:
    def contact(self, user_id: str) -> Contact | None:
        return Contact(email="an.nguyen@corelens.test", phone="0900 000 001")

    def department_members(self, department_code: str) -> list:
        return []


@pytest.fixture
def client(session, monkeypatch):
    """Máy khách đổi được người gọi; dòng kiểm toán ghi vào phiên của bài."""

    @contextmanager
    def mo():
        yield session

    monkeypatch.setattr(kiem_toan, "mo_phien", mo)
    tac_nhan = {"actor": DIEU_PHOI}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: tac_nhan["actor"]
    app.dependency_overrides[current_claims] = lambda: {"sub": tac_nhan["actor"].id}
    app.dependency_overrides[get_directory] = lambda: DanhBaGia()
    with TestClient(app) as c:
        c.tac_nhan = tac_nhan
        yield c
    app.dependency_overrides.clear()


def _goi(client, actor: Actor):
    client.tac_nhan["actor"] = actor
    return client


def _dong(session, **loc) -> list[AccessAuditLog]:
    cau = select(AccessAuditLog).order_by(AccessAuditLog.id)
    for cot, gia_tri in loc.items():
        cau = cau.where(getattr(AccessAuditLog, cot) == gia_tri)
    session.expire_all()
    return list(session.scalars(cau))


def _cua_bai(session) -> list[AccessAuditLog]:
    """Dòng của các tác nhân trong bài — cụm thử có thể đã có dòng của người khác."""
    session.expire_all()
    return list(session.scalars(
        select(AccessAuditLog).where(AccessAuditLog.actor.like(f"%-{DUOI}")).order_by(AccessAuditLog.id)
    ))


def _ho_so(session, phong: str | None = None) -> Request:
    """Hồ sơ của NGUOI_GUI; có `phong` thì phân loại rồi chuyển về phòng đó."""
    loai = session.scalars(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    ho_so = create_case(session, title="Cấp quyền phần mềm kế toán", description="Thử #431.",
                        requester_id=NGUOI_GUI.id, requester_label=NGUOI_GUI.label, request_type_code=loai)
    if phong is not None:
        uu_tien = session.scalars(select(Priority.code).order_by(Priority.display_order)).first()
        perform_transition(session, case_id=ho_so.id, to_state="classified", actor=DIEU_PHOI,
                           changes={"priority_code": uu_tien})
        perform_transition(session, case_id=ho_so.id, to_state="awaiting-acceptance", actor=DIEU_PHOI,
                           changes={"department_code": phong})
    session.commit()
    return ho_so


def _tep(session, ho_so: Request) -> CaseAttachment:
    tep = CaseAttachment(case_id=ho_so.id, filename="giay-xac-nhan.pdf", content_type="application/pdf",
                         size_bytes=4, storage_key=f"kiem-thu-431/{uuid.uuid4()}", uploaded_by=NGUOI_GUI.id,
                         uploaded_by_label=NGUOI_GUI.label)
    session.add(tep)
    session.commit()
    return tep


# ---------------------------------------------------------------------------
# Xem chi tiết hồ sơ
# ---------------------------------------------------------------------------


def test_dieu_phoi_mo_chi_tiet_ghi_mot_dong(client, session, rule_set):
    ho_so = _ho_so(session)
    tra = _goi(client, DIEU_PHOI).get(f"/coordination/requests/{ho_so.id}")
    assert tra.status_code == 200

    dong = _dong(session, case_id=ho_so.id)
    assert [(d.access_kind, d.actor, d.actor_label, d.channel) for d in dong] == [
        ("case-view", DIEU_PHOI.id, DIEU_PHOI.label, "ung-dung")
    ]
    assert dong[0].attachment_id is None
    assert dong[0].at.utcoffset() == dt.timedelta(0)


def test_phong_ban_mo_chi_tiet_ghi_mot_dong(client, session, rule_set, phong_ban):
    ho_so = _ho_so(session, phong_ban)
    truong_phong = _truong_phong(phong_ban)
    assert _goi(client, truong_phong).get(f"/department/requests/{ho_so.id}").status_code == 200
    assert [(d.access_kind, d.actor, d.channel) for d in _dong(session, case_id=ho_so.id)] == [
        ("case-view", truong_phong.id, "ung-dung")
    ]


def test_tai_khoan_dich_vu_qua_loi_ghi_kenh_loi(client, session, rule_set, phong_ban):
    """Tài khoản dịch vụ mang vai trưởng phòng (như dx-integration-truong-phong) mở hồ sơ của phòng qua lõi."""
    ho_so = _ho_so(session, phong_ban)
    dich_vu = _truong_phong(phong_ban, "kt-dx-integration-truong-phong")
    assert _goi(client, dich_vu).get(f"/core/v1/workflow/requests/{ho_so.id}").status_code == 200
    assert [(d.access_kind, d.actor, d.channel) for d in _dong(session, case_id=ho_so.id)] == [
        ("case-view", dich_vu.id, "loi")
    ]


def test_nguoi_gui_xem_ho_so_cua_minh_khong_ghi(client, session, rule_set):
    ho_so = _ho_so(session)
    _goi(client, NGUOI_GUI)
    assert client.get(f"/requests/{ho_so.id}").status_code == 200
    assert client.get(f"/core/v1/workflow/requests/{ho_so.id}").status_code == 200
    assert _dong(session, case_id=ho_so.id) == []


def test_buoc_chuyen_tra_chi_tiet_nhung_khong_ghi_xem(client, session, rule_set):
    ho_so = _ho_so(session)
    uu_tien = session.scalars(select(Priority.code).order_by(Priority.display_order)).first()
    tra = _goi(client, DIEU_PHOI).post(
        f"/coordination/requests/{ho_so.id}/transitions",
        json={"to_state": "classified", "changes": {"priority_code": uu_tien}},
    )
    assert tra.status_code == 200, tra.text
    assert _dong(session, case_id=ho_so.id) == []


def test_danh_sach_va_hang_doi_khong_ghi(client, session, rule_set, phong_ban):
    _ho_so(session, phong_ban)
    _goi(client, DIEU_PHOI)
    assert client.get("/coordination/queue").status_code == 200
    assert client.get("/core/v1/workflow/requests?q=ke%20toan").status_code == 200
    _goi(client, _truong_phong(phong_ban))
    assert client.get("/department/queue").status_code == 200
    assert _cua_bai(session) == []


def test_bi_403_hay_404_khong_ghi(client, session, rule_set, phong_ban):
    ho_so = _ho_so(session)  # chưa về phòng nào
    _goi(client, _truong_phong(phong_ban))
    assert client.get(f"/department/requests/{ho_so.id}").status_code == 404
    assert client.get(f"/core/v1/workflow/requests/{ho_so.id}").status_code == 404
    assert client.get(f"/department/requests/{ho_so.id}/requester-contact").status_code == 404
    _goi(client, Actor(id=f"kt-khac-{DUOI}", roles=frozenset({"requester"})))
    assert client.get(f"/coordination/requests/{ho_so.id}").status_code == 403
    assert client.get("/analytics/event-log").status_code == 403
    _goi(client, DIEU_PHOI)
    assert client.get("/coordination/requests/999999999").status_code == 404
    assert _cua_bai(session) == []


# ---------------------------------------------------------------------------
# Liên hệ, tệp, xuất
# ---------------------------------------------------------------------------


def test_xem_lien_he_ghi_mot_dong(client, session, rule_set, phong_ban):
    ho_so = _ho_so(session, phong_ban)
    assert _goi(client, DIEU_PHOI).get(f"/coordination/requests/{ho_so.id}/requester-contact").status_code == 200
    truong_phong = _truong_phong(phong_ban)
    assert _goi(client, truong_phong).get(f"/department/requests/{ho_so.id}/requester-contact").status_code == 200
    assert [(d.access_kind, d.actor) for d in _dong(session, case_id=ho_so.id)] == [
        ("requester-contact", DIEU_PHOI.id), ("requester-contact", truong_phong.id)
    ]


def test_tai_tep_ghi_ma_tep_va_kenh(client, session, rule_set, monkeypatch):
    ho_so = _ho_so(session)
    tep = _tep(session, ho_so)
    monkeypatch.setattr(objects, "doc_tep", lambda khoa: b"%PDF")
    _goi(client, DIEU_PHOI)
    assert client.get(f"/attachments/{tep.id}").status_code == 200
    assert client.get(f"/core/v1/files/{tep.id}").status_code == 200
    _goi(client, NGUOI_GUI)
    assert client.get(f"/attachments/{tep.id}").status_code == 200  # tệp trên hồ sơ của chính mình: không ghi

    assert [(d.access_kind, d.attachment_id, d.case_id, d.channel) for d in _dong(session, case_id=ho_so.id)] == [
        ("attachment-download", tep.id, ho_so.id, "ung-dung"),
        ("attachment-download", tep.id, ho_so.id, "loi"),
    ]


@pytest.mark.parametrize("dinh_dang", ["csv", "json", "xes"])
def test_xuat_nhat_ky_ghi_tham_so(client, session, rule_set, dinh_dang):
    _goi(client, QUAN_TRI)
    tra = client.get(f"/analytics/event-log?format={dinh_dang}&from=2026-11-01&to=2026-11-30")
    assert tra.status_code == 200
    dong = _dong(session, actor=QUAN_TRI.id)
    assert len(dong) == 1
    assert (dong[0].access_kind, dong[0].case_id, dong[0].channel) == ("event-log-export", None, "ung-dung")
    assert {k: dong[0].details[k] for k in ("format", "from", "to", "process")} == {
        "format": dinh_dang, "from": "2026-11-01", "to": "2026-11-30", "process": None,
    }
    assert isinstance(dong[0].details["rows"], int)


def test_xuat_qua_loi_ghi_kenh_loi(client, session, rule_set):
    assert _goi(client, QUAN_TRI).get("/core/v1/events?format=json").status_code == 200
    assert [(d.access_kind, d.channel) for d in _dong(session, actor=QUAN_TRI.id)] == [("event-log-export", "loi")]


def test_ghi_hong_thi_trang_van_tra(client, session, rule_set, monkeypatch, caplog):
    ho_so = _ho_so(session)

    @contextmanager
    def hong():
        raise RuntimeError("cơ sở dữ liệu kiểm toán không trả lời")
        yield  # pragma: no cover

    monkeypatch.setattr(kiem_toan, "mo_phien", hong)
    tra = _goi(client, DIEU_PHOI).get(f"/coordination/requests/{ho_so.id}")
    assert tra.status_code == 200
    assert tra.json()["id"] == ho_so.id
    assert any(r.getMessage() == "Không ghi được nhật ký truy cập" for r in caplog.records)


# ---------------------------------------------------------------------------
# Lược đồ: chỉ ghi thêm, xóa hồ sơ giữ vết
# ---------------------------------------------------------------------------


def test_sua_hay_xoa_dong_bi_tu_choi(client, session, rule_set):
    ho_so = _ho_so(session)
    _goi(client, DIEU_PHOI).get(f"/coordination/requests/{ho_so.id}")
    ma = _dong(session, case_id=ho_so.id)[0].id
    for cau in (
        "UPDATE access_audit_log SET actor = 'ai-do' WHERE id = :id",
        "UPDATE access_audit_log SET case_id = NULL WHERE id = :id",
        "DELETE FROM access_audit_log WHERE id = :id",
    ):
        with pytest.raises(Exception, match="chỉ ghi thêm"):
            with session.begin_nested():
                session.execute(text(cau), {"id": ma})


def test_xoa_ho_so_thi_vet_o_lai_case_id_null(client, session, rule_set):
    ho_so = _ho_so(session)
    _goi(client, DIEU_PHOI).get(f"/coordination/requests/{ho_so.id}")
    ma = _dong(session, case_id=ho_so.id)[0].id

    session.execute(text("DELETE FROM requests WHERE id = :id"), {"id": ho_so.id})
    session.commit()
    con = session.execute(
        text("SELECT case_id, actor, access_kind FROM access_audit_log WHERE id = :id"), {"id": ma}
    ).one()
    assert tuple(con) == (None, DIEU_PHOI.id, "case-view")


# ---------------------------------------------------------------------------
# Tra cứu cho quản trị viên
# ---------------------------------------------------------------------------


def _ghi_mau(session) -> list[Request]:
    """Ba hồ sơ, bốn lần xem của hai người — mốc `at` định sẵn qua chèn thẳng (bảng chỉ cho chèn)."""
    mot, hai, ba = _ho_so(session), _ho_so(session), _ho_so(session)
    goc = dt.datetime(2026, 1, 20, 3, 0, tzinfo=dt.UTC)
    for luc, nguoi, ho_so, loai in [
        (goc, DIEU_PHOI, mot, "case-view"),
        (goc + dt.timedelta(hours=1), DIEU_PHOI, hai, "requester-contact"),
        (goc + dt.timedelta(days=1), QUAN_TRI, mot, "case-view"),
        (goc + dt.timedelta(days=2), DIEU_PHOI, ba, "case-view"),
    ]:
        session.add(AccessAuditLog(at=luc, actor=nguoi.id, actor_label=nguoi.label, access_kind=loai,
                                   case_id=ho_so.id, channel="ung-dung"))
    session.commit()
    return [mot, hai, ba]


def _tra(client, **tham_so):
    """Tra trong tháng 1/2026 — trước khi có bảng này, nên chỉ có dòng mẫu của bài, không có dòng thật nào."""
    khoang = {"from": "2026-01-01T00:00:00Z", "to": "2026-02-01T00:00:00Z"}
    tra = _goi(client, QUAN_TRI).get("/admin/access-audit", params={**khoang, **tham_so})
    assert tra.status_code == 200, tra.text
    return tra.json()


def test_tra_cuu_chi_quan_tri_vien(client, session, rule_set, phong_ban):
    for nguoi in (DIEU_PHOI, NGUOI_GUI, _truong_phong(phong_ban)):
        assert _goi(client, nguoi).get("/admin/access-audit").status_code == 403
        assert _goi(client, nguoi).get("/admin/access-audit/kinds").status_code == 403
    loai = _goi(client, QUAN_TRI).get("/admin/access-audit/kinds").json()
    assert [k["code"] for k in loai] == ["case-view", "requester-contact", "attachment-download", "event-log-export"]
    assert all(k["label"] for k in loai)


def test_tra_cuu_moi_nhat_truoc_at_utc_va_ma_hien_thi(client, session, rule_set):
    mot, hai, ba = _ghi_mau(session)
    ket_qua = _tra(client)
    assert ket_qua["total"] == 4
    assert [d["case_id"] for d in ket_qua["items"]] == [ba.id, mot.id, hai.id, mot.id]
    dau = ket_qua["items"][0]
    assert dau["at"] == "2026-01-22T03:00:00Z"
    assert dau["case_code"] == f"YC-{ba.created_at.year}-{ba.id:04d}"
    assert dau["access_kind_label"] and dau["actor_label"] == DIEU_PHOI.label


def test_tra_cuu_loc_tung_tham_so(client, session, rule_set):
    mot, hai, _ = _ghi_mau(session)
    assert [d["case_id"] for d in _tra(client, case_id=mot.id)["items"]] == [mot.id, mot.id]
    assert {d["actor"] for d in _tra(client, actor=QUAN_TRI.id)["items"]} == {QUAN_TRI.id}
    # Một phần tên, không dấu
    assert {d["actor"] for d in _tra(client, actor="binh tran")["items"] if d["actor"].endswith(DUOI)} == {
        DIEU_PHOI.id}
    assert [d["case_id"] for d in _tra(client, access_kind="requester-contact")["items"]] == [hai.id]
    trong_ngay = _tra(client, **{"from": "2026-01-20T00:00:00Z", "to": "2026-01-21T00:00:00Z"})
    assert [d["case_id"] for d in trong_ngay["items"]] == [hai.id, mot.id]
    # Mốc không ghi múi coi là UTC; `to` không gồm chính mốc đó
    assert _tra(client, **{"from": "2026-01-20T04:00:00", "to": "2026-01-22T03:00:00"})["total"] == 2


def test_tra_cuu_phan_trang(client, session, rule_set):
    _ghi_mau(session)
    trang_mot = _tra(client, limit=3, offset=0)
    trang_hai = _tra(client, limit=3, offset=3)
    assert (trang_mot["total"], len(trang_mot["items"]), trang_mot["limit"]) == (4, 3, 3)
    assert (len(trang_hai["items"]), trang_hai["offset"]) == (1, 3)
    assert {d["id"] for d in trang_mot["items"]}.isdisjoint({d["id"] for d in trang_hai["items"]})


def test_tra_cuu_khong_tu_sinh_dong(client, session, rule_set):
    _ghi_mau(session)
    truoc = len(_cua_bai(session))
    _tra(client)
    _goi(client, QUAN_TRI).get("/admin/access-audit/kinds")
    assert len(_cua_bai(session)) == truoc


def test_tra_cuu_khong_thuoc_loi():
    duong = app.openapi()["paths"]
    assert "/admin/access-audit" in duong
    assert not any(d.startswith("/core/v1/admin") for d in duong)
