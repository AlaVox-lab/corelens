# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử thao tác hàng loạt ở buồng lái điều phối (#440).
#
# Điều cốt lõi: hàng loạt là một vòng lặp trên cửa chuyển trạng thái duy nhất, không phải đường vòng.
# Nên bài kiểm đo đúng những thứ cửa đó hứa — mỗi hồ sơ một dòng nhật ký, hồ sơ bị chặn đứng nguyên
# và không để lại dòng nào, lỗi mang đúng mã của engine — và so kết quả với việc bấm lần lượt từng hồ
# sơ ở điểm cuối cũ.
#
# Mọi hồ sơ do bài tự tạo; bài không đọc trang đầu hàng đợi, nên dữ liệu cũ trong cơ sở dữ liệu cụm
# thử không làm bài đỏ. Mã bước và trạng thái tra từ điểm cuối liệt kê bước hàng loạt và bộ quy tắc,
# không chép vào đây.

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth.dependencies import current_actor
from app.config import Settings
from app.db import get_session
from app.main import app
from app.models.case import EventLog, Request
from app.models.workflow_config import Department, Priority, RequestType, Transition
from app.rules.guards import truong_bat_buoc, truong_can_nhap
from app.workflow import coordination
from app.workflow.context import Actor
from app.workflow.coordination import VAI_TRO_DIEU_PHOI
from app.workflow.engine import create_case

NGUOI_GUI = Actor(id="nd-gui-440", name="An Nguyễn", roles=frozenset({"requester"}))
DIEU_PHOI = Actor(id="nd-dp-440", name="Bình Trần", roles=frozenset({VAI_TRO_DIEU_PHOI}))
# Một người mang cả hai vai, như binh.tran: hồ sơ họ gửi thì người khác phải điều phối (#154)
GUI_KIEM_DIEU_PHOI = Actor(
    id="nd-dp-441", name="Cường Lê", roles=frozenset({"requester", VAI_TRO_DIEU_PHOI})
)
TRUONG_PHONG = Actor(id="nd-tp-440", name="Dũng Phạm", roles=frozenset({"approver"}))

DUONG = "/coordination/bulk-transitions"


@pytest.fixture
def client(session):
    dang_goi = {"actor": DIEU_PHOI}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: dang_goi["actor"]
    with TestClient(app) as c:
        c.dang_goi = dang_goi
        yield c
    app.dependency_overrides.clear()


def _loai(session, thu_tu: int = 0) -> str:
    cac_loai = session.scalars(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    ).all()
    return cac_loai[thu_tu % len(cac_loai)]


def _uu_tien(session) -> str:
    return session.scalar(select(Priority.code).where(Priority.is_default))


def _phong(session) -> str:
    return session.scalars(
        select(Department.code).where(Department.is_active).order_by(Department.display_order)
    ).first()


def _tao(session, so: int, *, nguoi: Actor = NGUOI_GUI, loai: str | None = None) -> list[int]:
    ma = [
        create_case(
            session,
            title=f"Hồ sơ hàng loạt số {i + 1}",
            requester_id=nguoi.id,
            requester_label=nguoi.label,
            request_type_code=loai or _loai(session),
        ).id
        for i in range(so)
    ]
    session.commit()
    return ma


def _thao_tac(client) -> dict[str, dict]:
    """Bước hàng loạt theo trường nó đòi: bước có ô mức ưu tiên là phân loại, có ô phòng là chuyển về
    phòng. Tra từ điểm cuối, không viết mã bước."""
    r = client.get(DUONG)
    assert r.status_code == 200, r.text
    cac_buoc = r.json()["actions"]
    theo_truong = {}
    for truong in ("priority_code", "department_code"):
        theo_truong[truong] = next(b for b in cac_buoc if truong in {f["code"] for f in b["fields"]})
    return theo_truong


def _canh(session, rule_set, ma_buoc: str) -> Transition:
    return session.scalars(
        select(Transition).where(
            Transition.rule_set_id == rule_set.id,
            Transition.activity_code == ma_buoc,
            Transition.is_system.is_(False),
        )
    ).one()


def _so_dong(session, cac_ma: list[int]) -> int:
    return session.scalar(select(func.count()).select_from(EventLog).where(EventLog.case_id.in_(cac_ma)))


def _dong_moi(session, cac_ma: list[int], sau_id: int) -> list[EventLog]:
    return list(
        session.scalars(
            select(EventLog)
            .where(EventLog.case_id.in_(cac_ma), EventLog.id > sau_id)
            .order_by(EventLog.id)
        ).all()
    )


def _id_cuoi(session) -> int:
    return session.scalar(select(func.coalesce(func.max(EventLog.id), 0)))


def _phan_loai(client, session, buoc, cac_ma, **them):
    return client.post(
        DUONG,
        json={
            "activity_code": buoc["activity_code"],
            "case_ids": cac_ma,
            "changes": {"priority_code": _uu_tien(session), **them},
        },
    )


# ---------------------------------------------------------------------------
# Danh sách bước
# ---------------------------------------------------------------------------


def test_buoc_hang_loat_suy_tu_bo_quy_tac(client, session, rule_set):
    """Nhãn, trạng thái nguồn, ô bắt buộc hay để trống được — đều tra từ cạnh và ràng buộc."""
    r = client.get(DUONG).json()
    assert r["max_cases"] == coordination.get_settings().bulk_max_cases
    assert r["actions"], "phải có ít nhất một bước hàng loạt"
    for buoc in r["actions"]:
        canh = _canh(session, rule_set, buoc["activity_code"])
        assert buoc["activity_label"] == canh.activity_label
        assert [s["code"] for s in buoc["from_states"]] == [canh.from_state]
        assert {f["code"] for f in buoc["fields"]} == truong_can_nhap(canh.guard_codes)
        assert {f["code"] for f in buoc["fields"] if f["required"]} == truong_bat_buoc(canh.guard_codes)


def test_khong_phai_dieu_phoi_bi_chan_nhu_buong_lai(client, session, rule_set):
    cac_ma = _tao(session, 2)
    buoc = _thao_tac(client)["priority_code"]
    truoc = _so_dong(session, cac_ma)
    for nguoi in (NGUOI_GUI, TRUONG_PHONG):
        client.dang_goi["actor"] = nguoi
        assert client.get(DUONG).status_code == 403
        assert _phan_loai(client, session, buoc, cac_ma).status_code == 403
    assert _so_dong(session, cac_ma) == truoc


def test_diem_cuoi_hang_loat_co_gioi_han_toc_do():
    tuyen = next(
        r for r in coordination.router.routes
        if getattr(r, "path", "").endswith("/bulk-transitions") and "POST" in getattr(r, "methods", ())
    )
    assert "gioi_han_toc_do.<locals>.kiem_tra" in [d.call.__qualname__ for d in tuyen.dependant.dependencies]


# ---------------------------------------------------------------------------
# Định nghĩa hoàn thành: 20 hồ sơ ⇒ đúng 20 sự kiện
# ---------------------------------------------------------------------------


def test_hai_muoi_ho_so_sinh_dung_hai_muoi_dong_nhat_ky(client, session, rule_set):
    cac_ma = _tao(session, 20)
    buoc = _thao_tac(client)
    phan_loai = _canh(session, rule_set, buoc["priority_code"]["activity_code"])
    ve_phong = _canh(session, rule_set, buoc["department_code"]["activity_code"])
    muc = _uu_tien(session)
    phong = _phong(session)

    # 1. Phân loại cả lô
    moc = _id_cuoi(session)
    r = _phan_loai(client, session, buoc["priority_code"], cac_ma)
    assert r.status_code == 200, r.text
    kq = r.json()
    assert (kq["total"], kq["succeeded"]) == (20, 20)
    assert [m["case_id"] for m in kq["items"]] == cac_ma
    assert all(m["ok"] and m["error"] is None and m["to_state"] == phan_loai.to_state for m in kq["items"])
    assert all(m["code"].startswith("YC-") for m in kq["items"])

    dong = _dong_moi(session, cac_ma, moc)
    assert len(dong) == 20
    assert sorted(d.case_id for d in dong) == sorted(cac_ma)
    assert {(d.activity, d.from_state, d.to_state) for d in dong} == {
        (phan_loai.activity_code, phan_loai.from_state, phan_loai.to_state)
    }
    assert {d.actor for d in dong} == {DIEU_PHOI.id}

    # 2. Chuyển cả lô về một phòng
    moc = _id_cuoi(session)
    r = client.post(
        DUONG,
        json={
            "activity_code": ve_phong.activity_code,
            "case_ids": cac_ma,
            "changes": {"department_code": phong},
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["succeeded"] == 20
    dong = _dong_moi(session, cac_ma, moc)
    assert len(dong) == 20
    assert {(d.activity, d.from_state, d.to_state) for d in dong} == {
        (ve_phong.activity_code, ve_phong.from_state, ve_phong.to_state)
    }

    session.expire_all()
    for ma in cac_ma:
        ho_so = session.get(Request, ma)
        assert (ho_so.current_state, ho_so.priority_code, ho_so.department_code) == (
            ve_phong.to_state, muc, phong
        )


def test_lo_lan_ho_so_bi_chan_bao_rieng_tung_ho_so(client, session, rule_set):
    """Hồ sơ hợp lệ vẫn đi; hồ sơ bị chặn đứng nguyên, không dòng nhật ký, kèm đúng mã engine."""
    buoc = _thao_tac(client)["priority_code"]
    hop_le = _tao(session, 2)
    cua_minh = _tao(session, 1, nguoi=GUI_KIEM_DIEU_PHOI)[0]
    da_phan_loai = _tao(session, 1)[0]
    client.dang_goi["actor"] = DIEU_PHOI
    assert _phan_loai(client, session, buoc, [da_phan_loai]).json()["succeeded"] == 1
    khong_co = 999_999_999

    client.dang_goi["actor"] = GUI_KIEM_DIEU_PHOI
    bi_chan = [cua_minh, da_phan_loai, khong_co]
    trang_thai_truoc = {ma: session.get(Request, ma).current_state for ma in bi_chan[:2]}
    dong_truoc = _so_dong(session, bi_chan)
    lo = [hop_le[0], cua_minh, da_phan_loai, khong_co, hop_le[1]]

    r = _phan_loai(client, session, buoc, lo)
    assert r.status_code == 200, r.text
    kq = r.json()
    assert [m["case_id"] for m in kq["items"]] == lo
    assert (kq["total"], kq["succeeded"]) == (5, 2)
    theo_ma = {m["case_id"]: m for m in kq["items"]}
    assert theo_ma[hop_le[0]]["ok"] and theo_ma[hop_le[1]]["ok"]

    # Hồ sơ do chính người bấm gửi: ràng buộc actor-not-requester (#154)
    loi = theo_ma[cua_minh]["error"]
    assert (loi["code"], loi["guard"]) == ("guard-violation", "actor-not-requester")
    assert "điều phối viên khác" in loi["message"]
    # Đã ở trạng thái khác: không có cạnh mang mã bước này từ đó
    assert theo_ma[da_phan_loai]["error"]["code"] == "transition-not-allowed"
    # Không có hồ sơ: không có mã hiển thị
    assert theo_ma[khong_co]["error"]["code"] == "case-not-found"
    assert theo_ma[khong_co]["code"] is None
    assert all(not theo_ma[ma]["ok"] for ma in bi_chan)

    session.expire_all()
    assert {ma: session.get(Request, ma).current_state for ma in bi_chan[:2]} == trang_thai_truoc
    assert session.get(Request, cua_minh).priority_code is None
    assert _so_dong(session, bi_chan) == dong_truoc


# ---------------------------------------------------------------------------
# Lỗi của cả lô — không hồ sơ nào đổi
# ---------------------------------------------------------------------------


def test_vuot_gioi_han_lo_tra_422(client, session, rule_set, monkeypatch):
    monkeypatch.setattr(coordination, "get_settings", lambda: Settings(bulk_max_cases=3))
    buoc = _thao_tac(client)["priority_code"]
    cac_ma = _tao(session, 4)
    r = _phan_loai(client, session, buoc, cac_ma)
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "bulk-too-many-cases"
    assert "3" in r.json()["detail"]["message"]
    assert _so_dong(session, cac_ma) == 0
    assert _phan_loai(client, session, buoc, cac_ma[:3]).json()["succeeded"] == 3


def test_truong_ngoai_canh_bi_tu_choi_nhu_diem_cuoi_mot_ho_so(client, session, rule_set):
    buoc = _thao_tac(client)["priority_code"]
    cac_ma = _tao(session, 2)
    r = _phan_loai(client, session, buoc, cac_ma, department_code=_phong(session))
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "field-not-permitted"
    assert _so_dong(session, cac_ma) == 0

    # Cùng mã như điểm cuối một hồ sơ
    mot = client.post(
        f"/coordination/requests/{cac_ma[0]}/transitions",
        json={
            "to_state": _canh(session, rule_set, buoc["activity_code"]).to_state,
            "changes": {"priority_code": _uu_tien(session), "department_code": _phong(session)},
        },
    )
    assert mot.json()["detail"]["code"] == r.json()["detail"]["code"]


def test_trung_ho_so_hay_buoc_khong_hang_loat_tra_422(client, session, rule_set):
    buoc = _thao_tac(client)["priority_code"]
    ma = _tao(session, 1)[0]
    r = _phan_loai(client, session, buoc, [ma, ma])
    assert (r.status_code, r.json()["detail"]["code"]) == (422, "bulk-duplicate-cases")

    khong_hang_loat = session.scalars(
        select(Transition.activity_code).where(
            Transition.rule_set_id == rule_set.id,
            Transition.activity_code.not_in([b["activity_code"] for b in client.get(DUONG).json()["actions"]]),
        )
    ).first()
    r = client.post(DUONG, json={"activity_code": khong_hang_loat, "case_ids": [ma]})
    assert (r.status_code, r.json()["detail"]["code"]) == (422, "bulk-activity-not-supported")
    assert client.post(DUONG, json={"activity_code": buoc["activity_code"], "case_ids": []}).status_code == 422
    assert _so_dong(session, [ma]) == 0


# ---------------------------------------------------------------------------
# Không có lối "nhận gợi ý cho cả lô" (#440, CLAUDE.md 4.3)
# ---------------------------------------------------------------------------


def test_khong_ghi_truong_goi_y_va_khong_dau_giu_hay_ghi_de(client, session, rule_set):
    buoc = _thao_tac(client)
    cac_ma = _tao(session, 2)
    # Gợi ý của mô hình khác giá trị người chọn: hàng loạt không đụng tới nó
    goi_y = session.scalars(select(Priority.code).where(Priority.code != _uu_tien(session))).first()
    for ma in cac_ma:
        session.get(Request, ma).suggested_priority_code = goi_y
    session.commit()

    # Gợi ý người xử lý (`suggested_assignee_id`) không có ở đây: tác vụ nền sau khi hồ sơ về phòng
    # tính nó ở tầng I, như sau điểm cuối một hồ sơ (#318) — không phải thao tác hàng loạt ghi
    def cot_goi_y() -> list[tuple]:
        session.expire_all()
        return [
            (h.suggested_request_type_code, h.suggested_priority_code, h.suggested_department_code,
             h.suggestion_note)
            for h in (session.get(Request, ma) for ma in cac_ma)
        ]

    truoc = cot_goi_y()
    assert {t[1] for t in truoc} == {goi_y}
    moc = _id_cuoi(session)
    assert _phan_loai(client, session, buoc["priority_code"], cac_ma).json()["succeeded"] == 2
    r = client.post(
        DUONG,
        json={
            "activity_code": buoc["department_code"]["activity_code"],
            "case_ids": cac_ma,
            "changes": {"department_code": _phong(session)},
        },
    )
    assert r.json()["succeeded"] == 2

    assert cot_goi_y() == truoc
    # Bảng ánh xạ vẫn gợi ý phòng cho loại này, nhưng không ai xem thẻ gợi ý của từng hồ sơ
    assert [d.suggestion for d in _dong_moi(session, cac_ma, moc)] == [None] * 4


def test_bo_trong_o_khong_bat_buoc_giu_gia_tri_tung_ho_so(client, session, rule_set):
    """Loại yêu cầu bỏ trống thì mỗi hồ sơ giữ loại người gửi đã chọn; chọn thì áp chung cả lô."""
    buoc = _thao_tac(client)["priority_code"]
    a = _tao(session, 1, loai=_loai(session, 0))[0]
    b = _tao(session, 1, loai=_loai(session, 1))[0]
    assert _phan_loai(client, session, buoc, [a, b]).json()["succeeded"] == 2
    session.expire_all()
    assert [session.get(Request, m).request_type_code for m in (a, b)] == [_loai(session, 0), _loai(session, 1)]

    c, d = _tao(session, 2, loai=_loai(session, 0))
    assert _phan_loai(client, session, buoc, [c, d], request_type_code=_loai(session, 1)).json()["succeeded"] == 2
    session.expire_all()
    assert {session.get(Request, m).request_type_code for m in (c, d)} == {_loai(session, 1)}


# ---------------------------------------------------------------------------
# Bất biến: hàng loạt N hồ sơ = bấm lần lượt N lần ở điểm cuối cũ
# ---------------------------------------------------------------------------


def _anh_chup(session, cac_ma: list[int], sau_id: int) -> list[tuple]:
    """Trạng thái, trường quyết định và nhật ký của từng hồ sơ — bỏ định danh, mốc giờ và dấu gợi ý."""
    session.expire_all()
    ket_qua = []
    for ma in cac_ma:
        h = session.get(Request, ma)
        dong = [
            (d.activity, d.from_state, d.to_state, d.actor, d.actor_label, d.note, d.changes)
            for d in session.scalars(
                select(EventLog).where(EventLog.case_id == ma, EventLog.id > sau_id).order_by(EventLog.id)
            )
        ]
        ket_qua.append(
            (h.current_state, h.request_type_code, h.priority_code, h.department_code, h.assignee_id, dong)
        )
    return ket_qua


def test_hang_loat_giong_het_bam_lan_luot_tung_ho_so(client, session, rule_set):
    buoc = _thao_tac(client)
    so = 5
    hang_loat = _tao(session, so)
    lan_luot = _tao(session, so)
    muc, phong = _uu_tien(session), _phong(session)
    cac_buoc = [
        (buoc["priority_code"]["activity_code"], {"priority_code": muc}),
        (buoc["department_code"]["activity_code"], {"department_code": phong}),
    ]
    moc = _id_cuoi(session)

    for ma_buoc, gia_tri in cac_buoc:
        r = client.post(DUONG, json={"activity_code": ma_buoc, "case_ids": hang_loat, "changes": gia_tri})
        assert r.json()["succeeded"] == so, r.text
        den = _canh(session, rule_set, ma_buoc).to_state
        for ma in lan_luot:
            r = client.post(f"/coordination/requests/{ma}/transitions", json={"to_state": den, "changes": gia_tri})
            assert r.status_code == 200, r.text

    assert _anh_chup(session, hang_loat, moc) == _anh_chup(session, lan_luot, moc)
