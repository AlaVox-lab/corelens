# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử sinh gợi ý loại, mức ưu tiên, phòng ban bằng mô hình (#317) — `app/intelligence/phan_loai.py`.
#
# Điều phải đúng:
#
#   1. Gợi ý chỉ ghi trường `suggested_*` và ghi chú gợi ý — không chạm trường quyết định, không đổi
#      trạng thái, không ghi nhật ký sự kiện, không đổi `updated_at`; không đi qua cửa chuyển trạng thái.
#   2. Cờ "phòng ban theo mô hình" tắt (mặc định) thì gợi ý phòng vẫn theo bảng ánh xạ.
#   3. Lần thử được đánh dấu (thành công hay không) để không hỏi lại mãi; mô hình không tới được thì
#      không tính lượt; hết lượt thì thôi; chưa đủ lâu thì chưa hỏi lại.
#   4. Bộ quét bù chạy dưới khóa tư vấn — hai bản không quét cùng lúc — và chỉ nhặt hồ sơ còn ở chỗ
#      điều phối.
#   5. Mô hình tắt: gửi và phân loại tay chạy đủ, màn điều phối như trước khi có gợi ý.

from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from app.auth.dependencies import current_actor
from app.db import get_session
from app.intelligence import mo_hinh, phan_loai
from app.intelligence.goi_y import NGUON_BANG_ANH_XA, NGUON_MO_HINH, goi_y_phong
from app.main import app
from app.models.case import EventLog, Request
from app.models.workflow_config import Priority, RequestType, State
from app.workflow.context import Actor
from app.workflow.coordination import VAI_TRO_DIEU_PHOI
from app.workflow.engine import create_case
from app.workflow.nhip_quet import chay_luot_quet
from tests.test_goi_y import _loai_co_anh_xa, _phong_khac
from tests.test_mo_hinh import MoHinhGia, _cong_dong, dap_an_hop_le, dat_cau_hinh
from tests.test_nhip_quet import hai_phien  # noqa: F401 — fixture dùng lại

NGUOI_GUI = Actor(id="nd-gui-317", name="An Nguyễn", roles=frozenset({"requester"}))
DIEU_PHOI = Actor(id="nd-dp-317", name="Bình Trần", roles=frozenset({VAI_TRO_DIEU_PHOI}))


@pytest.fixture
def mo_hinh_gia(monkeypatch):
    import threading

    gia = MoHinhGia()
    threading.Thread(target=gia.may_chu.serve_forever, daemon=True).start()
    dat_cau_hinh(monkeypatch, llm_url=gia.url, llm_timeout_seconds=1.0)
    try:
        yield gia
    finally:
        gia.may_chu.shutdown()
        gia.may_chu.server_close()


def _mo_phien(session):
    """Đưa phiên của bài cho `thu_goi_y`: mỗi `commit` chỉ nhả một điểm lưu, cuối bài vẫn hoàn tác."""

    @contextmanager
    def mo():
        yield session

    return mo


def _tao(session, ma_loai: str | None = None) -> Request:
    ma_loai = ma_loai or session.scalar(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    )
    h = create_case(
        session,
        title="Wifi tầng 3 chập chờn cả buổi sáng",
        description="Cả phòng kế toán không vào được phần mềm hóa đơn.",
        requester_id=NGUOI_GUI.id,
        requester_label=NGUOI_GUI.label,
        request_type_code=ma_loai,
    )
    session.commit()
    return h


def _anh_quyet_dinh(ho_so: Request) -> tuple:
    return (
        ho_so.request_type_code,
        ho_so.priority_code,
        ho_so.department_code,
        ho_so.assignee_id,
        ho_so.current_state,
        ho_so.updated_at,
    )


def _so_su_kien(session, ma: int) -> int:
    return session.scalar(select(func.count()).select_from(EventLog).where(EventLog.case_id == ma))


# ---------------------------------------------------------------------------
# Ghi gợi ý: chỉ trường gợi ý
# ---------------------------------------------------------------------------


def test_goi_y_chi_ghi_truong_goi_y_khong_cham_truong_quyet_dinh(session, rule_set, mo_hinh_gia):
    ho_so = _tao(session)
    truoc = _anh_quyet_dinh(ho_so)
    su_kien_truoc = _so_su_kien(session, ho_so.id)
    dap_an = dap_an_hop_le(session)
    mo_hinh_gia.tra_dap_an(dap_an)

    ket_qua = phan_loai.thu_goi_y(ho_so.id, lan_dau=True, mo_phien=_mo_phien(session))

    assert ket_qua == phan_loai.DA_GHI
    session.expire_all()
    ho_so = session.get(Request, ho_so.id)
    assert ho_so.suggested_request_type_code == dap_an["request_type_code"]
    assert ho_so.suggested_priority_code == dap_an["priority_code"]
    assert _anh_quyet_dinh(ho_so) == truoc, "gợi ý không được đổi trường quyết định hay updated_at"
    assert _so_su_kien(session, ho_so.id) == su_kien_truoc, "gợi ý không đi qua cửa chuyển trạng thái"
    assert ho_so.suggestion_attempts == 1
    ghi_chu = ho_so.suggestion_note
    assert ghi_chu["ok"] is True and ghi_chu["reasons"]["priority_code"] == dap_an["priority_reason"]
    assert ghi_chu["model_department"] == dap_an["department_code"]


def test_co_phong_tat_thi_goi_y_phong_van_theo_bang_anh_xa(session, rule_set, mo_hinh_gia):
    ma_loai, ma_phong = _loai_co_anh_xa(session)
    ho_so = _tao(session, ma_loai)
    dap_an = {**dap_an_hop_le(session), "department_code": _phong_khac(session, ma_phong)}
    mo_hinh_gia.tra_dap_an(dap_an)

    phan_loai.thu_goi_y(ho_so.id, lan_dau=True, mo_phien=_mo_phien(session))

    session.expire_all()
    ho_so = session.get(Request, ho_so.id)
    assert ho_so.suggested_department_code is None
    goi_y = goi_y_phong(session, ho_so, ho_so.request_type_code)
    assert goi_y.code == ma_phong and goi_y.source == NGUON_BANG_ANH_XA


def test_co_phong_bat_thi_dung_phong_cua_mo_hinh(session, rule_set, mo_hinh_gia, monkeypatch):
    dat_cau_hinh(
        monkeypatch, llm_url=mo_hinh_gia.url, llm_timeout_seconds=1.0, suggest_department_from_model=True
    )
    ma_loai, ma_phong = _loai_co_anh_xa(session)
    ho_so = _tao(session, ma_loai)
    phong_mo_hinh = _phong_khac(session, ma_phong)
    mo_hinh_gia.tra_dap_an({**dap_an_hop_le(session), "department_code": phong_mo_hinh})

    phan_loai.thu_goi_y(ho_so.id, lan_dau=True, mo_phien=_mo_phien(session))

    session.expire_all()
    ho_so = session.get(Request, ho_so.id)
    goi_y = goi_y_phong(session, ho_so, ho_so.request_type_code)
    assert goi_y.code == phong_mo_hinh and goi_y.source == NGUON_MO_HINH
    assert goi_y.reason == "Đúng phần việc của phòng này."


def test_ho_so_da_roi_trang_thai_luc_mo_hinh_tra_loi_thi_khong_ghi(
    session, rule_set, mo_hinh_gia, monkeypatch
):
    ho_so = _tao(session)
    mo_hinh_gia.tra_dap_an(dap_an_hop_le(session))
    trang_thai_khac = session.scalar(
        select(State.code).where(
            State.rule_set_id == ho_so.rule_set_id, State.code != ho_so.current_state
        )
    )
    goc_hoi = mo_hinh.hoi_phan_loai

    def hoi_roi_doi(de_bai, **kw):
        # Điều phối viên đi tiếp đúng lúc mô hình đang nghĩ. Bài giả lập bằng cách gán thẳng —
        # chỉ để thử đường ghi của tầng I, không phải một lần chuyển trạng thái thật
        ket_qua = goc_hoi(de_bai, **kw)
        session.execute(
            update(Request).where(Request.id == ho_so.id).values(current_state=trang_thai_khac)
        )
        return ket_qua

    monkeypatch.setattr(mo_hinh, "hoi_phan_loai", hoi_roi_doi)
    ket_qua = phan_loai.thu_goi_y(ho_so.id, lan_dau=True, mo_phien=_mo_phien(session))

    assert ket_qua == phan_loai.DA_ROI_DI
    session.expire_all()
    ho_so = session.get(Request, ho_so.id)
    assert ho_so.suggested_request_type_code is None
    assert ho_so.suggestion_note["ok"] is False


# ---------------------------------------------------------------------------
# Đánh dấu đã thử, số lần thử, thử lại
# ---------------------------------------------------------------------------


def test_mo_hinh_tra_rac_thi_danh_dau_da_thu_va_khong_hoi_lai_ngay(session, rule_set, mo_hinh_gia):
    ho_so = _tao(session)
    mo_hinh_gia.tra_loi = lambda _: (200, b'{"choices":[{"message":{"content":"rac"}}]}')
    mo = _mo_phien(session)

    assert phan_loai.thu_goi_y(ho_so.id, lan_dau=True, mo_phien=mo) == mo_hinh.LOI_SAI_DINH_DANG
    session.expire_all()
    ho_so = session.get(Request, ho_so.id)
    assert ho_so.suggestion_attempts == 1 and ho_so.suggestion_attempted_at is not None
    assert ho_so.suggestion_note == {**ho_so.suggestion_note, "ok": False, "error": "invalid-output"}
    so_lan_hoi = len(mo_hinh_gia.cac_yeu_cau)

    # Tác vụ nền thứ hai và bộ quét bù trước hạn thử lại: không hỏi nữa
    assert phan_loai.thu_goi_y(ho_so.id, lan_dau=True, mo_phien=mo) == phan_loai.BO_QUA
    assert phan_loai.thu_goi_y(ho_so.id, lan_dau=False, mo_phien=mo) == phan_loai.BO_QUA
    assert ho_so.id not in phan_loai.ho_so_can_goi_y(session, 100)
    assert len(mo_hinh_gia.cac_yeu_cau) == so_lan_hoi


def test_het_han_thu_lai_thi_hoi_lai_toi_khi_het_luot(session, rule_set, mo_hinh_gia, monkeypatch):
    dat_cau_hinh(
        monkeypatch,
        llm_url=mo_hinh_gia.url,
        llm_timeout_seconds=1.0,
        suggest_max_attempts=2,
        suggest_retry_after_seconds=0,
    )
    ho_so = _tao(session)
    mo_hinh_gia.tra_loi = lambda _: (500, b"{}")
    mo = _mo_phien(session)

    def lui_moc():
        session.execute(
            update(Request)
            .where(Request.id == ho_so.id)
            .values(suggestion_attempted_at=func.now() - func.make_interval(0, 0, 0, 0, 1))
        )

    phan_loai.thu_goi_y(ho_so.id, lan_dau=True, mo_phien=mo)
    lui_moc()
    assert ho_so.id in phan_loai.ho_so_can_goi_y(session, 100)
    assert phan_loai.thu_goi_y(ho_so.id, lan_dau=False, mo_phien=mo) == mo_hinh.LOI_MAY_CHU
    lui_moc()
    # Hai lần đã dùng hết lượt
    assert ho_so.id not in phan_loai.ho_so_can_goi_y(session, 100)
    assert phan_loai.thu_goi_y(ho_so.id, lan_dau=False, mo_phien=mo) == phan_loai.BO_QUA


def test_mo_hinh_khong_toi_duoc_thi_khong_tinh_luot(session, rule_set, monkeypatch):
    dat_cau_hinh(monkeypatch, llm_url=_cong_dong(), llm_timeout_seconds=1.0)
    ho_so = _tao(session)

    ket_qua = phan_loai.thu_goi_y(ho_so.id, lan_dau=True, mo_phien=_mo_phien(session))

    assert ket_qua == mo_hinh.LOI_KHONG_KET_NOI
    session.expire_all()
    assert session.get(Request, ho_so.id).suggestion_attempts == 0
    # Bộ quét bù vẫn thấy hồ sơ: mô hình lên lại thì nó được gợi ý
    assert ho_so.id in phan_loai.ho_so_can_goi_y(session, 100)


def test_mo_hinh_tat_thi_khong_lam_gi(session, rule_set, monkeypatch):
    dat_cau_hinh(monkeypatch, llm_url="")
    ho_so = _tao(session)
    assert phan_loai.thu_goi_y(ho_so.id, lan_dau=True, mo_phien=_mo_phien(session)) == mo_hinh.LOI_TAT
    assert phan_loai.quet_goi_y(session, mo_phien=_mo_phien(session)) == []
    session.expire_all()
    assert session.get(Request, ho_so.id).suggestion_attempts == 0


# ---------------------------------------------------------------------------
# Bộ quét bù
# ---------------------------------------------------------------------------


def test_bo_quet_bu_goi_y_ho_so_dang_cho_dieu_phoi(session, rule_set, mo_hinh_gia, monkeypatch):
    ho_so = _tao(session)
    mo_hinh_gia.tra_dap_an(dap_an_hop_le(session))
    # Một lượt chỉ xử lý suggest_scan_batch_size hồ sơ cũ nhất; cụm có hồ sơ trình diễn đang chờ điều phối
    # thì hồ sơ của bài nằm sau chúng (#442) — nới cỡ lượt cho đủ mọi hồ sơ đang chờ
    can = phan_loai.ho_so_can_goi_y(session, 100_000)
    dat_cau_hinh(monkeypatch, llm_url=mo_hinh_gia.url, llm_timeout_seconds=1.0, suggest_scan_batch_size=len(can))

    assert ho_so.id in can
    da_ghi = phan_loai.quet_goi_y(session, mo_phien=_mo_phien(session))

    assert ho_so.id in da_ghi
    session.expire_all()
    assert session.get(Request, ho_so.id).suggested_request_type_code is not None
    assert ho_so.id not in phan_loai.ho_so_can_goi_y(session, 1000)


def test_bo_quet_bu_dung_som_khi_mo_hinh_khong_toi_duoc(session, rule_set, monkeypatch):
    dat_cau_hinh(monkeypatch, llm_url=_cong_dong(), llm_timeout_seconds=1.0, suggest_scan_batch_size=5)
    for _ in range(3):
        _tao(session)
    goi: list[int] = []
    goc = phan_loai.thu_goi_y

    def dem(ma, **kw):
        goi.append(ma)
        return goc(ma, **kw)

    monkeypatch.setattr(phan_loai, "thu_goi_y", dem)
    assert phan_loai.quet_goi_y(session, mo_phien=_mo_phien(session)) == []
    assert len(goi) == 1, "mô hình không tới được thì hỏi tiếp hồ sơ sau cũng vô ích"


def test_bo_quet_bu_co_khoa_hai_ban_khong_chay_cung_luc(hai_phien):  # noqa: F811
    ban_a, ban_b = hai_phien
    da_goi: list[str] = []

    def quet_a(phien):
        da_goi.append("a")
        luot_b = chay_luot_quet(ban_b, phan_loai.TEN_BO_QUET_GOI_Y, lambda p: da_goi.append("b"))
        assert luot_b.da_chay is False
        return []

    luot_a = chay_luot_quet(ban_a, phan_loai.TEN_BO_QUET_GOI_Y, quet_a)

    assert luot_a.da_chay is True
    assert da_goi == ["a"]


def test_suc_khoe_he_thong_co_dong_bo_quet_goi_y_va_mo_hinh_khi_bat(session, monkeypatch):
    import app.main as main_mod
    from app.config import Settings

    monkeypatch.setattr(main_mod, "settings", Settings(llm_url="http://mo-hinh-khong-co:8080"))
    dat_cau_hinh(monkeypatch, llm_url=_cong_dong(), llm_health_timeout_seconds=0.5)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: Actor(
        id="qt-317", roles=frozenset({"administrator"})
    )
    try:
        with TestClient(app) as c:
            than = c.get("/system/health").json()
    finally:
        app.dependency_overrides.clear()
    assert phan_loai.TEN_BO_QUET_GOI_Y in {b["name"] for b in than["scanners"]}
    assert than["language_model"]["status"] == mo_hinh.KHONG_PHAN_HOI
    # Mô hình là tùy chọn: không phản hồi không làm hệ thống "hỏng"
    assert than["status"] in ("ok", "degraded")


# ---------------------------------------------------------------------------
# Mô hình tắt: luồng thủ công đủ
# ---------------------------------------------------------------------------


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: DIEU_PHOI
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_mo_hinh_tat_phan_loai_tay_van_du(client, session, rule_set, monkeypatch):
    dat_cau_hinh(monkeypatch, llm_url="")
    ho_so = _tao(session)

    chi_tiet = client.get(f"/coordination/requests/{ho_so.id}").json()
    assert chi_tiet["suggested_request_type"] is None
    assert chi_tiet["suggested_priority"] is None

    mac_dinh = session.scalar(select(Priority.code).where(Priority.is_default))
    canh = next(c for c in chi_tiet["allowed_transitions"] if "priority_code" in c["fields"])
    r = client.post(
        f"/coordination/requests/{ho_so.id}/transitions",
        json={"to_state": canh["to_state"], "changes": {"priority_code": mac_dinh}},
    )
    assert r.status_code == 200, r.text
    session.expire_all()
    assert session.get(Request, ho_so.id).priority_code == mac_dinh


def test_man_dieu_phoi_tra_ba_goi_y_va_ghi_giu_hay_ghi_de(client, session, rule_set, mo_hinh_gia):
    ho_so = _tao(session)
    dap_an = dap_an_hop_le(session)
    mo_hinh_gia.tra_dap_an(dap_an)
    phan_loai.thu_goi_y(ho_so.id, lan_dau=True, mo_phien=_mo_phien(session))

    chi_tiet = client.get(f"/coordination/requests/{ho_so.id}").json()
    assert chi_tiet["suggested_request_type"]["code"] == dap_an["request_type_code"]
    assert chi_tiet["suggested_request_type"]["source"] == NGUON_MO_HINH
    assert chi_tiet["suggested_request_type"]["reason"] == dap_an["request_type_reason"]
    assert chi_tiet["suggested_priority"]["code"] == dap_an["priority_code"]

    # Phân loại bằng đúng thao tác hiện có, chọn mức khác gợi ý: nhật ký ghi "ghi đè"
    muc_khac = session.scalar(
        select(Priority.code).where(Priority.code != dap_an["priority_code"]).limit(1)
    )
    canh = next(c for c in chi_tiet["allowed_transitions"] if "priority_code" in c["fields"])
    r = client.post(
        f"/coordination/requests/{ho_so.id}/transitions",
        json={"to_state": canh["to_state"], "changes": {"priority_code": muc_khac}},
    )
    assert r.status_code == 200, r.text
    session.expire_all()
    su_kien = session.scalars(
        select(EventLog).where(EventLog.case_id == ho_so.id).order_by(EventLog.id.desc()).limit(1)
    ).one()
    dau = su_kien.suggestion["priority_code"]
    assert dau["suggested"] == dap_an["priority_code"] and dau["chosen"] == muc_khac
    assert dau["overridden"] is True and dau["source"] == NGUON_MO_HINH
