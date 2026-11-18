# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử lịch làm việc (#199): hai hàm đo thời gian của lược đồ khởi tạo, lịch mẫu nạp
# từ infra/seed/, và đồng hồ SLA đo bằng giờ làm việc.
#
# Mọi đáp án tính tay trước từ một lịch biết rõ: thứ Hai–thứ Sáu 08:00–12:00 và
# 13:00–17:00 giờ Việt Nam, nghỉ 24/11/2026. Mốc mẫu: 16/10/2026 là thứ Sáu, 19/10 là
# thứ Hai, 24/11 là thứ Ba.

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import select, text

from app.models.workflow_config import Priority, RequestType
from app.rules.sla import (
    an_han_con_lai_giay,
    bay_gio,
    da_chay_giay,
    gioi_han_giay,
    han_chot,
    ho_so_qua_han,
)
from app.workflow.context import Actor
from app.workflow.engine import create_case, perform_transition

LICH = "lich-thu-199"
VN = dt.timezone(dt.timedelta(hours=7))
GIO = 3600


def _moc(thang: int, ngay: int, gio: int, phut: int = 0, giay: int = 0) -> dt.datetime:
    return dt.datetime(2026, thang, ngay, gio, phut, giay, tzinfo=VN)


@pytest.fixture
def lich(session) -> str:
    """Một lịch thử riêng, không đụng lịch mặc định."""
    session.execute(
        text(
            "INSERT INTO work_calendars (code, label, time_zone) "
            "VALUES (:c, 'Lịch thử', 'Asia/Ho_Chi_Minh')"
        ),
        {"c": LICH},
    )
    session.execute(
        text(
            "INSERT INTO work_hours (calendar_code, iso_weekday, start_time, end_time) "
            "SELECT :c, thu, k.bat, k.ket FROM generate_series(1, 5) AS thu, "
            "(VALUES (TIME '08:00', TIME '12:00'), (TIME '13:00', TIME '17:00')) AS k (bat, ket)"
        ),
        {"c": LICH},
    )
    session.execute(
        text("INSERT INTO holidays VALUES (:c, DATE '2026-11-24', 'Ngày Văn hóa Việt Nam')"),
        {"c": LICH},
    )
    session.flush()
    return LICH


def _giay(session, tu, den, lich=LICH) -> int:
    return session.scalar(
        text("SELECT so_giay_lam_viec(:tu, :den, :lich)"), {"tu": tu, "den": den, "lich": lich}
    )


def _moc_sau(session, tu, giay, lich=LICH) -> dt.datetime | None:
    return session.scalar(
        text("SELECT moc_sau_giay_lam_viec(:tu, :giay, :lich)"),
        {"tu": tu, "giay": giay, "lich": lich},
    )


# ---------------------------------------------------------------------------
# Số giây làm việc giữa hai mốc
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tu", "den", "dap_an"),
    [
        # Ví dụ của issue: chiều thứ Sáu 2 giờ, sáng thứ Hai 4 giờ, chiều thứ Hai 2 giờ
        (_moc(10, 16, 15), _moc(10, 19, 15), 8 * GIO),
        # Qua giờ nghỉ trưa: 11–12 và 13–14
        (_moc(10, 19, 11), _moc(10, 19, 14), 2 * GIO),
        # Trọn cuối tuần
        (_moc(10, 17, 10), _moc(10, 18, 18), 0),
        # Qua đêm, ngoài giờ cả hai đầu
        (_moc(10, 19, 18), _moc(10, 20, 7), 0),
        # Nằm gọn trong giờ nghỉ trưa
        (_moc(10, 19, 12, 15), _moc(10, 19, 12, 45), 0),
        # Trọn một tuần làm việc
        (_moc(10, 19, 8), _moc(10, 23, 17), 40 * GIO),
        # Qua ngày nghỉ 24/11: thứ Hai 16–17, thứ Tư 8–9
        (_moc(11, 23, 16), _moc(11, 25, 9), 2 * GIO),
        # Mốc đảo ngược thì không có thời gian nào
        (_moc(10, 19, 15), _moc(10, 16, 15), 0),
        # Giữ được giây lẻ
        (_moc(10, 19, 9), _moc(10, 19, 9, 0, 30), 30),
    ],
)
def test_so_giay_lam_viec(session, lich, tu, den, dap_an):
    assert _giay(session, tu, den) == dap_an


# ---------------------------------------------------------------------------
# Mốc sau một số giây làm việc — hạn chót để hiển thị
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tu", "giay", "dap_an"),
    [
        (_moc(10, 16, 15), 8 * GIO, _moc(10, 19, 15)),
        # Bắt đầu giữa giờ nghỉ trưa: giờ đầu tiên chạy từ 13:00
        (_moc(10, 19, 12, 30), 1 * GIO, _moc(10, 19, 14)),
        # Bắt đầu thứ Bảy: giờ đầu tiên chạy từ 08:00 thứ Hai
        (_moc(10, 17, 10), 1 * GIO, _moc(10, 19, 9)),
        # Hết đúng cuối khung thì hạn là cuối khung, không nhảy sang khung sau
        (_moc(10, 19, 8), 4 * GIO, _moc(10, 19, 12)),
        # Bỏ qua ngày nghỉ
        (_moc(11, 23, 16), 2 * GIO, _moc(11, 25, 9)),
        (_moc(10, 19, 15), 0, _moc(10, 19, 15)),
    ],
)
def test_moc_sau_giay_lam_viec(session, lich, tu, giay, dap_an):
    assert _moc_sau(session, tu, giay) == dap_an


@pytest.mark.parametrize("giay", [1, 1799, 4 * GIO, 4 * GIO + 1, 8 * GIO, 27 * GIO + 17])
@pytest.mark.parametrize("tu", [_moc(10, 16, 15), _moc(10, 17, 3), _moc(11, 23, 12, 10)])
def test_hai_ham_la_phep_nguoc_cua_nhau(session, lich, tu, giay):
    assert _giay(session, tu, _moc_sau(session, tu, giay)) == giay


def test_lich_khong_co_gio_lam_thi_khong_bao_gio_toi_han(session):
    session.execute(
        text("INSERT INTO work_calendars (code, label, time_zone) VALUES ('trong', 'Trống', 'UTC')")
    )
    session.flush()
    assert _moc_sau(session, _moc(10, 19, 8), GIO, "trong") is None
    assert _giay(session, _moc(10, 19, 8), _moc(10, 26, 8), "trong") == 0


# ---------------------------------------------------------------------------
# Lịch mẫu nạp từ infra/seed/03-lich-lam-viec.sql
# ---------------------------------------------------------------------------


def test_lich_mau_la_lich_mac_dinh(session):
    """Bỏ trống tên lịch là dùng lịch mặc định — lịch mẫu cho ra đúng ví dụ của issue."""
    assert _giay(session, _moc(10, 16, 15), _moc(10, 19, 15), None) == 8 * GIO


def test_lich_mau_nghi_ngay_van_hoa_viet_nam(session):
    assert _giay(session, _moc(11, 24, 8), _moc(11, 24, 17), None) == 0


def _moc_2027(thang: int, ngay: int, gio: int) -> dt.datetime:
    return dt.datetime(2027, thang, ngay, gio, tzinfo=VN)


def test_lich_mau_co_ngay_le_2027(session):
    """#439: dữ liệu mẫu (tệp 08) có ngày nghỉ của năm 2027, kể cả nghỉ bù."""
    for thang, ngay in [(2, 4), (2, 10), (4, 16), (4, 30), (5, 3), (9, 2), (9, 3), (11, 24)]:
        assert _giay(session, _moc_2027(thang, ngay, 8), _moc_2027(thang, ngay, 17), None) == 0, (thang, ngay)


def test_ho_so_gui_truoc_tet_2027_lui_han_qua_ky_nghi(session):
    """Gửi sáng thứ Tư 3/2/2027, trước kỳ nghỉ Tết 4/2–10/2: một ngày làm việc (8 giờ) sau đó là hết
    ngày 3/2, còn 16 giờ thì hạn rơi vào 17:00 thứ Năm 11/2 — lùi đúng năm ngày làm việc bị nghỉ."""
    assert _giay(session, _moc_2027(2, 3, 8), _moc_2027(2, 11, 8), None) == 8 * GIO
    assert _moc_sau(session, _moc_2027(2, 3, 8), 16 * GIO, None) == _moc_2027(2, 11, 17)


# ---------------------------------------------------------------------------
# Đồng hồ SLA đo bằng giờ làm việc
# ---------------------------------------------------------------------------


def _den_dang_xu_ly(session, phong_ban: str):
    loai = session.scalars(
        select(RequestType).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    ho_so = create_case(session, title="Hồ sơ thử lịch làm việc", requester_id="nguoi-tao-199")
    pl = Actor(id="pl-199", roles=frozenset({"classifier"}))
    xd = Actor(id="xd-199", roles=frozenset({"approver"}), departments=frozenset({phong_ban}))
    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=pl,
        changes={"priority_code": uu_tien, "request_type_code": loai.code},
    )
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="awaiting-acceptance",
        actor=pl,
        changes={"department_code": phong_ban},
    )
    perform_transition(session, case_id=ho_so.id, to_state="in-progress", actor=xd)
    return ho_so


def _lich_mac_dinh_chi_lam(session, thu: int) -> None:
    """Lịch mặc định chỉ còn một khung trọn ngày vào thứ `thu`, bỏ ngày nghỉ."""
    mac_dinh = "(SELECT code FROM work_calendars WHERE is_default)"
    session.execute(text(f"DELETE FROM holidays WHERE calendar_code = {mac_dinh}"))
    session.execute(text(f"DELETE FROM work_hours WHERE calendar_code = {mac_dinh}"))
    session.execute(
        text(
            "INSERT INTO work_hours (calendar_code, iso_weekday, start_time, end_time) "
            "SELECT code, :thu, TIME '00:00', TIME '24:00' FROM work_calendars WHERE is_default"
        ),
        {"thu": thu},
    )
    session.flush()


def test_ngoai_gio_lam_dong_ho_khong_troi_va_khong_qua_han(session, phong_ban):
    """Bốn mươi giờ lịch rơi trọn vào ngày không làm việc: đồng hồ đứng yên, không leo
    thang. Cùng hồ sơ đó với lịch cả tuần thì đã quá hạn — bộ quét đọc đúng lịch."""
    hom_nay = _hom_nay(session)
    # Ba ngày sau hôm nay, cũng là bốn ngày trước — bốn mươi giờ lùi lại không chạm tới
    _lich_mac_dinh_chi_lam(session, (hom_nay + 2) % 7 + 1)

    ho_so = _den_dang_xu_ly(session, phong_ban)
    assert gioi_han_giay(session, ho_so) < 40 * GIO
    ho_so.sla_segment_since = bay_gio(session) - dt.timedelta(hours=40)
    session.flush()

    assert da_chay_giay(session, ho_so) == 0
    assert ho_so.id not in [h.id for h in ho_so_qua_han(session)]

    _lich_mac_dinh_chi_lam(session, hom_nay)
    session.execute(
        text(
            "INSERT INTO work_hours (calendar_code, iso_weekday, start_time, end_time) "
            "SELECT code, thu, TIME '00:00', TIME '24:00' FROM work_calendars, "
            "generate_series(1, 7) AS thu WHERE is_default AND thu <> :hom_nay"
        ),
        {"hom_nay": hom_nay},
    )
    session.flush()
    assert da_chay_giay(session, ho_so) >= 40 * GIO - 60
    assert ho_so.id in [h.id for h in ho_so_qua_han(session)]


def _hom_nay(session) -> int:
    return int(
        session.scalar(text("SELECT EXTRACT(ISODOW FROM now() AT TIME ZONE 'Asia/Ho_Chi_Minh')"))
    )


def test_chuyen_trang_thai_chot_doan_bang_gio_lam_viec(session, phong_ban):
    """Đoạn vừa qua cộng vào đồng hồ theo giờ làm việc lúc hồ sơ đổi trạng thái — bốn mươi
    giờ rơi trọn vào ngày nghỉ thì không cộng gì."""
    _lich_mac_dinh_chi_lam(session, (_hom_nay(session) + 2) % 7 + 1)
    ho_so = _den_dang_xu_ly(session, phong_ban)
    ho_so.sla_segment_since = bay_gio(session) - dt.timedelta(hours=40)
    session.flush()

    xl = Actor(id="xl-199", roles=frozenset({"handler"}), departments=frozenset({phong_ban}))
    perform_transition(session, case_id=ho_so.id, to_state="completed", actor=xl)
    assert ho_so.sla_running_seconds == 0


def test_an_han_dem_bang_gio_lam_viec(session, phong_ban):
    """Hồ sơ đã quá hạn vừa vào lại trạng thái đếm giờ: ân hạn chỉ hao theo giờ làm việc,
    nên bốn mươi giờ nghỉ không ăn vào ân hạn và bộ quét chưa leo thang lại."""
    _lich_mac_dinh_chi_lam(session, (_hom_nay(session) + 2) % 7 + 1)
    ho_so = _den_dang_xu_ly(session, phong_ban)
    loai = session.get(RequestType, ho_so.request_type_code)
    assert loai.sla_grace_hours > 0, "loại mẫu đầu tiên phải có ân hạn để bài này có nghĩa"
    ho_so.sla_running_seconds = gioi_han_giay(session, ho_so) + GIO
    ho_so.sla_segment_since = bay_gio(session) - dt.timedelta(hours=40)
    session.flush()

    assert an_han_con_lai_giay(session, ho_so) == loai.sla_grace_hours * GIO
    assert ho_so.id not in [h.id for h in ho_so_qua_han(session)]


@pytest.mark.usefixtures("lich_ca_ngay")
def test_han_chot_la_moc_sau_phan_cam_ket_con_lai(session, phong_ban):
    ho_so = _den_dang_xu_ly(session, phong_ban)
    # Đã chạy nửa giờ ở một đoạn trước: hạn phải trừ phần đó
    ho_so.sla_running_seconds = 1800
    ho_so.sla_segment_since = bay_gio(session) - dt.timedelta(hours=2)
    session.flush()

    con = gioi_han_giay(session, ho_so) - 1800
    assert han_chot(session, ho_so) == ho_so.sla_segment_since + dt.timedelta(seconds=con)


def test_chua_phan_loai_thi_chua_co_han_chot(session):
    ho_so = create_case(session, title="Chưa phân loại", requester_id="nguoi-tao-199")
    assert han_chot(session, ho_so) is None
