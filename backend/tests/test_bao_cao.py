# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Lớp báo cáo của không gian D (#304): các view `bao_cao_*` của migration 0014.
#
# Mỗi bài dựng một loại yêu cầu và một phòng ban riêng ngay trong giao dịch của bài, nên con số
# của view không lẫn dữ liệu sẵn có trong cụm và đáp án biết trước. Thời gian: trong một giao
# dịch `now()` đứng yên, mọi dòng nhật ký mang cùng mốc đó — lùi `created_at` của hồ sơ chừng
# nào thì thời gian xử lý ra đúng chừng ấy giờ, với lịch làm việc cả ngày của `lich_ca_ngay`.
from __future__ import annotations

import datetime as dt
import os

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import ProgrammingError

from app.models.workflow_config import Priority
from app.rules.sla import bay_gio
from app.workflow.context import Actor
from app.workflow.engine import create_case, perform_transition

pytestmark = pytest.mark.usefixtures("lich_ca_ngay")

LOAI = "bc-thu-304"
PHONG = "bc-phong-304"
HAN_GIO = 10
NGUOI_GUI = Actor(id="nguoi-gui-304", roles=frozenset({"requester"}))
DIEU_PHOI = Actor(id="dp-304", roles=frozenset({"classifier"}))
TRUONG_PHONG = Actor(id="tp-304", roles=frozenset({"approver"}), departments=frozenset({PHONG}))
XU_LY = Actor(id="xl-304", roles=frozenset({"handler"}), departments=frozenset({PHONG}))


@pytest.fixture(autouse=True)
def danh_muc_rieng(session, rule_set):
    session.execute(
        text(
            "INSERT INTO request_types (code, process_code, label, sla_hours) "
            "VALUES (:ma, :quy_trinh, 'Loại thử báo cáo', :han)"
        ),
        # Loại thuộc quy trình của bộ đang bật — báo cáo chỉ đếm hồ sơ của quy trình mặc định (#376)
        {"ma": LOAI, "quy_trinh": rule_set.process_code, "han": HAN_GIO},
    )
    session.execute(
        text("INSERT INTO departments (code, label) VALUES (:ma, 'Phòng thử báo cáo')"), {"ma": PHONG}
    )
    session.flush()


def _nguong_gio(session, uu_tien: str | None = None) -> float:
    """Ngưỡng hạn theo mức ưu tiên (mặc định nếu bỏ trống) — hệ số lấy từ dữ liệu, không giả định 100."""
    dieu_kien = Priority.code == uu_tien if uu_tien else Priority.is_default
    he_so = session.scalars(select(Priority.sla_factor_percent).where(dieu_kien)).one()
    return HAN_GIO * 3600 * he_so // 100 / 3600


def _uu_tien_co_he_so(session) -> str:
    """Mức ưu tiên có hệ số hạn khác 100 nhất — để bài lộ ra khi view quên nhân hệ số."""
    muc = session.scalars(select(Priority)).all()
    return max(muc, key=lambda m: abs(m.sla_factor_percent - 100)).code


def _lui(session, ho_so, *, cot: str, gio: float) -> None:
    setattr(ho_so, cot, bay_gio(session) - dt.timedelta(hours=gio))
    session.flush()


def _tao(session, *, lui_ngay: float = 0):
    ho_so = create_case(
        session, title="Máy chiếu phòng họp không lên hình", requester_id=NGUOI_GUI.id,
        request_type_code=LOAI,
    )
    if lui_ngay:
        _lui(session, ho_so, cot="created_at", gio=lui_ngay * 24)
    return ho_so


def _toi_phong(session, ho_so, uu_tien: str | None = None) -> None:
    uu_tien = uu_tien or session.scalars(select(Priority.code).where(Priority.is_default)).one()
    perform_transition(
        session, case_id=ho_so.id, to_state="classified", actor=DIEU_PHOI,
        changes={"priority_code": uu_tien},
    )
    perform_transition(
        session, case_id=ho_so.id, to_state="awaiting-acceptance", actor=DIEU_PHOI,
        changes={"department_code": PHONG},
    )


def _xong(session, *, gio_xu_ly: float, gio_dong_ho: float, uu_tien: str | None = None):
    """Một hồ sơ đi hết đường chính: đồng hồ chạy `gio_dong_ho`, từ lúc gửi tới lúc đóng `gio_xu_ly`."""
    ho_so = _tao(session)
    _toi_phong(session, ho_so, uu_tien)
    perform_transition(session, case_id=ho_so.id, to_state="in-progress", actor=TRUONG_PHONG)
    _lui(session, ho_so, cot="sla_segment_since", gio=gio_dong_ho)
    perform_transition(session, case_id=ho_so.id, to_state="completed", actor=XU_LY)
    perform_transition(session, case_id=ho_so.id, to_state="closed", actor=NGUOI_GUI)
    _lui(session, ho_so, cot="created_at", gio=gio_xu_ly)
    return ho_so


def _dong(session, view: str, **dieu_kien) -> list[dict]:
    loc = " AND ".join(f"{cot} = :{cot}" for cot in dieu_kien) or "TRUE"
    return [
        dict(d._mapping)
        for d in session.execute(text(f"SELECT * FROM {view} WHERE {loc}"), dieu_kien)
    ]


# ---------------------------------------------------------------------------


def test_ho_so_da_xong_co_gio_xu_ly_dong_ho_va_vi_pham(session):
    uu_tien = _uu_tien_co_he_so(session)
    nguong = _nguong_gio(session, uu_tien)
    ho_so = _xong(session, gio_xu_ly=30, gio_dong_ho=nguong + 1, uu_tien=uu_tien)

    [dong] = _dong(session, "bao_cao_ho_so", ma_ho_so=ho_so.id)
    assert dong["da_ket_thuc"] and dong["da_qua_phong_ban"]
    assert float(dong["gio_xu_ly"]) == 30
    assert float(dong["gio_dong_ho"]) == pytest.approx(nguong + 1, abs=0.01)
    # Ngưỡng nhân hệ số của mức ưu tiên, như app/rules/sla.py
    assert float(dong["gio_nguong"]) == pytest.approx(nguong, abs=0.01)
    assert dong["vi_pham"] is True


def test_gia_han_cong_vao_nguong(session):
    nguong = _nguong_gio(session)
    ho_so = _xong(session, gio_xu_ly=30, gio_dong_ho=nguong + 1)
    ho_so.sla_extension_total_hours = 3
    session.flush()

    [dong] = _dong(session, "bao_cao_ho_so", ma_ho_so=ho_so.id)
    assert float(dong["gio_nguong"]) == pytest.approx(nguong + 3, abs=0.01)
    assert dong["vi_pham"] is False
    assert dong["loai_yeu_cau"] == "Loại thử báo cáo"
    assert dong["phong_ban"] == "Phòng thử báo cáo"


def test_ho_so_dang_mo_chua_co_gio_xu_ly(session):
    ho_so = _tao(session, lui_ngay=2)

    [dong] = _dong(session, "bao_cao_ho_so", ma_ho_so=ho_so.id)
    assert not dong["da_ket_thuc"]
    assert dong["luc_ket_thuc"] is None and dong["gio_xu_ly"] is None
    assert dong["phong_ban"] == "Chưa chuyển phòng"
    assert dong["vi_pham"] is False


def test_trung_vi_va_ty_le_vi_pham_theo_loai(session):
    nguong = _nguong_gio(session)
    dong_ho = [nguong / 2, nguong + 2, nguong + 5]
    for gio_xu_ly, gio_dong_ho in zip((10, 20, 60), dong_ho):
        _xong(session, gio_xu_ly=gio_xu_ly, gio_dong_ho=gio_dong_ho)
    # Hồ sơ hủy trước khi tới phòng: không tính vào thời gian xử lý
    huy = _tao(session, lui_ngay=5)
    perform_transition(session, case_id=huy.id, to_state="cancelled", actor=NGUOI_GUI)

    [dong] = _dong(session, "bao_cao_thoi_gian_xu_ly", ma_loai=LOAI)
    assert dong["so_ho_so"] == 3
    assert float(dong["gio_xu_ly_trung_vi"]) == 20
    assert dong["gio_han_chuan"] == HAN_GIO
    assert dong["so_vi_pham"] == 2
    assert float(dong["ty_le_vi_pham"]) == 66.7


def test_doi_nguong_trong_du_lieu_thi_vi_pham_doi_theo(session):
    """Ngưỡng là dữ liệu: nâng hạn chuẩn của loại thì hồ sơ cũ hết vi phạm, không sửa mã nào."""
    nguong = _nguong_gio(session)
    _xong(session, gio_xu_ly=20, gio_dong_ho=nguong + 2)
    assert _dong(session, "bao_cao_thoi_gian_xu_ly", ma_loai=LOAI)[0]["so_vi_pham"] == 1

    session.execute(text("UPDATE request_types SET sla_hours = :h WHERE code = :ma"), {"h": HAN_GIO * 2, "ma": LOAI})
    assert _dong(session, "bao_cao_thoi_gian_xu_ly", ma_loai=LOAI)[0]["so_vi_pham"] == 0


def test_vi_pham_theo_phong_va_loai(session):
    nguong = _nguong_gio(session)
    _xong(session, gio_xu_ly=20, gio_dong_ho=nguong + 1)
    _xong(session, gio_xu_ly=20, gio_dong_ho=nguong / 2)

    [dong] = _dong(session, "bao_cao_vi_pham", ma_phong=PHONG)
    assert (dong["ma_loai"], dong["so_ho_so"], dong["so_vi_pham"]) == (LOAI, 2, 1)


def test_ton_dong_theo_phong_va_trang_thai(session):
    for _ in range(2):
        _toi_phong(session, _tao(session))
    dang_lam = _tao(session)
    _toi_phong(session, dang_lam)
    perform_transition(session, case_id=dang_lam.id, to_state="in-progress", actor=TRUONG_PHONG)
    _xong(session, gio_xu_ly=5, gio_dong_ho=1)  # đã đóng: không tồn đọng
    huy = _tao(session)  # đã hủy sau khi tới phòng: kết thúc theo cờ của trạng thái, không tồn đọng
    _toi_phong(session, huy)
    perform_transition(session, case_id=huy.id, to_state="cancelled", actor=NGUOI_GUI)

    ton = {d["ma_trang_thai"]: d["so_ho_so"] for d in _dong(session, "bao_cao_ton_dong", ma_phong=PHONG)}
    assert ton == {"awaiting-acceptance": 2, "in-progress": 1}


def test_phan_bo_loai_theo_tuan_gui(session):
    _tao(session)
    _tao(session)
    _tao(session, lui_ngay=8)  # tám ngày trước: chắc chắn khác tuần

    so = sorted(d["so_ho_so"] for d in _dong(session, "bao_cao_phan_bo_loai", ma_loai=LOAI))
    assert so == [1, 2]


def test_da_qua_phong_ban_tra_co_dong_ho_cua_bo_quy_tac(session, rule_set):
    """Không tra mã trạng thái: bật đồng hồ ở trạng thái chờ phòng nhận thì hồ sơ dừng ở đó rồi
    hủy được tính là đã qua phòng ban, và vào thời gian xử lý."""
    ho_so = _tao(session, lui_ngay=1)
    _toi_phong(session, ho_so)
    perform_transition(session, case_id=ho_so.id, to_state="cancelled", actor=NGUOI_GUI)
    assert _dong(session, "bao_cao_ho_so", ma_ho_so=ho_so.id)[0]["da_qua_phong_ban"] is False
    assert _dong(session, "bao_cao_thoi_gian_xu_ly", ma_loai=LOAI) == []

    session.execute(
        text("UPDATE states SET sla_running = TRUE WHERE rule_set_id = :bo AND code = 'awaiting-acceptance'"),
        {"bo": rule_set.id},
    )
    assert _dong(session, "bao_cao_ho_so", ma_ho_so=ho_so.id)[0]["da_qua_phong_ban"] is True
    assert _dong(session, "bao_cao_thoi_gian_xu_ly", ma_loai=LOAI)[0]["so_ho_so"] == 1


def test_tai_khoan_chi_doc_doc_duoc_bao_cao_khong_ghi_duoc(session):
    """Tài khoản của nền tảng báo cáo đọc được view mà không ghi được gì — ràng buộc của ADR-0003."""
    vai = os.environ.get("SUPERSET_READONLY_USER", "superset_readonly")
    if session.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :v"), {"v": vai}).first() is None:
        pytest.skip(f"Cụm không có tài khoản chỉ đọc {vai}.")
    _xong(session, gio_xu_ly=5, gio_dong_ho=1)

    session.execute(text(f'SET LOCAL ROLE "{vai}"'))
    for view in ("bao_cao_ho_so", "bao_cao_ton_dong", "bao_cao_thoi_gian_xu_ly", "bao_cao_vi_pham",
                 "bao_cao_phan_bo_loai", "bao_cao_nhat_ky"):
        session.execute(text(f"SELECT count(*) FROM {view}")).scalar_one()
    with pytest.raises(ProgrammingError, match="permission denied"), session.begin_nested():
        session.execute(text("UPDATE requests SET title = title WHERE id = 0"))
    session.execute(text("RESET ROLE"))
