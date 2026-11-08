# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử gợi ý của hệ thống và dấu giữ hay ghi đè (#239).
#
# Điều phải đúng, theo định nghĩa hoàn thành của issue:
#
#   1. Giữ gợi ý ghi "không ghi đè", đổi giá trị ghi "ghi đè" — vào cột riêng của nhật ký,
#      qua đúng cửa chuyển trạng thái, cột `changes` không có khóa lạ.
#   2. Không nguồn gợi ý nào có gì thì thao tác vẫn đi được và không ghi gì về gợi ý.
#   3. Thứ màn điều phối hiện trên thẻ là thứ được đem so — cùng một hàm.
#   4. Lớp báo cáo đọc được dấu đó, mang `ma_phong` để bản nhúng lọc theo phòng.
#
# Đáp án tra từ bảng ánh xạ của dữ liệu khởi tạo, không chép mã phòng vào đây.

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text, update

from app.auth.dependencies import current_actor
from app.db import get_session
from app.intelligence.goi_y import (
    NGUON_BANG_ANH_XA,
    NGUON_MO_HINH,
    ghi_nhan_goi_y,
    goi_y_phong,
)
from app.main import app
from app.models.case import EventLog, Request
from app.models.workflow_config import Department, Priority, RequestType, RequestTypeRouting
from app.workflow.context import Actor
from app.workflow.coordination import VAI_TRO_DIEU_PHOI
from app.workflow.engine import create_case

NGUOI_GUI = Actor(id="nd-gui-239", name="An Nguyễn", roles=frozenset({"requester"}))
DIEU_PHOI = Actor(id="nd-dp-239", name="Bình Trần", roles=frozenset({VAI_TRO_DIEU_PHOI}))


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: DIEU_PHOI
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _loai_co_anh_xa(session) -> tuple[str, str]:
    """Một loại yêu cầu đang bật có phòng mặc định, và phòng đó."""
    dong = session.execute(
        select(RequestType.code, RequestTypeRouting.department_code)
        .join(RequestTypeRouting, RequestTypeRouting.request_type_code == RequestType.code)
        .join(Department, Department.code == RequestTypeRouting.department_code)
        .where(RequestType.is_active, RequestTypeRouting.is_default, Department.is_active)
        .order_by(RequestType.display_order)
    ).first()
    assert dong, "dữ liệu khởi tạo phải có ít nhất một loại có phòng mặc định"
    return dong[0], dong[1]


def _phong_khac(session, ma: str) -> str:
    return session.scalar(
        select(Department.code).where(Department.is_active, Department.code != ma).limit(1)
    )


def _tao_va_phan_loai(client, session, ma_loai: str) -> tuple[Request, str]:
    """Hồ sơ mới đã phân loại, đứng ở trạng thái có cạnh chuyển phòng; trả kèm trạng thái đích."""
    ho_so = create_case(
        session,
        title="Máy in tầng 3 không nhận lệnh in",
        requester_id=NGUOI_GUI.id,
        requester_label=NGUOI_GUI.label,
        request_type_code=ma_loai,
    )
    session.commit()
    mac_dinh = session.scalar(select(Priority.code).where(Priority.is_default))
    chi_tiet = client.get(f"/coordination/requests/{ho_so.id}").json()
    phan_loai = next(c for c in chi_tiet["allowed_transitions"] if "priority_code" in c["fields"])
    r = client.post(
        f"/coordination/requests/{ho_so.id}/transitions",
        json={"to_state": phan_loai["to_state"], "changes": {"priority_code": mac_dinh}},
    )
    assert r.status_code == 200, r.text
    ve_phong = next(c for c in r.json()["allowed_transitions"] if "department_code" in c["fields"])
    return ho_so, ve_phong["to_state"]


def _su_kien_cuoi(session, ma_ho_so: int) -> EventLog:
    session.expire_all()
    return session.scalars(
        select(EventLog).where(EventLog.case_id == ma_ho_so).order_by(EventLog.id.desc()).limit(1)
    ).one()


# ---------------------------------------------------------------------------
# Thẻ gợi ý: dữ liệu một gợi ý
# ---------------------------------------------------------------------------


def test_chi_tiet_dieu_phoi_tra_ly_do_va_nguon_khong_co_do_tin_cay(client, session, rule_set):
    ma_loai, ma_phong = _loai_co_anh_xa(session)
    ho_so, _ = _tao_va_phan_loai(client, session, ma_loai)

    goi_y = client.get(f"/coordination/requests/{ho_so.id}").json()["suggested_department"]

    assert goi_y["code"] == ma_phong
    assert goi_y["source"] == NGUON_BANG_ANH_XA
    assert goi_y["source_label"]
    nhan_loai = session.get(RequestType, ma_loai).label
    assert nhan_loai in goi_y["reason"]
    # Bảng ánh xạ không có con số thật — không được bịa độ tin cậy
    assert goi_y["confidence"] is None


def test_danh_muc_loai_mang_phong_goi_y_de_the_doi_theo_loai(client, session, rule_set):
    ma_loai, ma_phong = _loai_co_anh_xa(session)
    cac_loai = {l["code"]: l for l in client.get("/request-types").json()}
    assert cac_loai[ma_loai]["suggested_department"]["code"] == ma_phong
    assert cac_loai[ma_loai]["suggested_department"]["source"] == NGUON_BANG_ANH_XA


# ---------------------------------------------------------------------------
# Giữ hay ghi đè — qua cửa chuyển trạng thái
# ---------------------------------------------------------------------------


def test_giu_goi_y_ghi_khong_ghi_de(client, session, rule_set):
    ma_loai, ma_phong = _loai_co_anh_xa(session)
    ho_so, ve_phong = _tao_va_phan_loai(client, session, ma_loai)

    r = client.post(
        f"/coordination/requests/{ho_so.id}/transitions",
        json={"to_state": ve_phong, "changes": {"department_code": ma_phong}},
    )
    assert r.status_code == 200, r.text

    su_kien = _su_kien_cuoi(session, ho_so.id)
    assert su_kien.suggestion == {
        "department_code": {
            "suggested": ma_phong,
            "chosen": ma_phong,
            "overridden": False,
            "source": NGUON_BANG_ANH_XA,
            "confidence": None,
        }
    }
    # Cột `changes` giữ đúng một nghĩa: trường đổi từ gì sang gì
    assert set(su_kien.changes) == {"department_code"}


def test_doi_phong_ghi_ghi_de(client, session, rule_set):
    ma_loai, ma_phong = _loai_co_anh_xa(session)
    khac = _phong_khac(session, ma_phong)
    ho_so, ve_phong = _tao_va_phan_loai(client, session, ma_loai)

    r = client.post(
        f"/coordination/requests/{ho_so.id}/transitions",
        json={"to_state": ve_phong, "changes": {"department_code": khac}},
    )
    assert r.status_code == 200, r.text

    dau = _su_kien_cuoi(session, ho_so.id).suggestion["department_code"]
    assert dau["suggested"] == ma_phong
    assert dau["chosen"] == khac
    assert dau["overridden"] is True


def test_khong_co_nguon_goi_y_thi_van_di_duoc_va_khong_ghi_gi(client, session, rule_set):
    ma_loai, ma_phong = _loai_co_anh_xa(session)
    ho_so, ve_phong = _tao_va_phan_loai(client, session, ma_loai)
    # Bảng ánh xạ không còn phòng mặc định cho loại này
    session.execute(
        update(RequestTypeRouting)
        .where(RequestTypeRouting.request_type_code == ma_loai)
        .values(is_default=False)
    )
    session.commit()
    assert client.get(f"/coordination/requests/{ho_so.id}").json()["suggested_department"] is None

    r = client.post(
        f"/coordination/requests/{ho_so.id}/transitions",
        json={"to_state": ve_phong, "changes": {"department_code": ma_phong}},
    )
    assert r.status_code == 200, r.text
    assert _su_kien_cuoi(session, ho_so.id).suggestion is None


def test_thao_tac_khong_gui_truong_co_goi_y_thi_khong_ghi_gi(client, session, rule_set):
    ma_loai, _ = _loai_co_anh_xa(session)
    ho_so, _ = _tao_va_phan_loai(client, session, ma_loai)
    # Bước phân loại chỉ đặt mức ưu tiên — chưa có gợi ý nào cho trường đó
    assert _su_kien_cuoi(session, ho_so.id).suggestion is None


# ---------------------------------------------------------------------------
# Thứ tự nguồn và loại vừa đổi
# ---------------------------------------------------------------------------


def test_cot_goi_y_cua_tang_i_dung_truoc_bang_anh_xa(client, session, rule_set):
    ma_loai, ma_phong = _loai_co_anh_xa(session)
    khac = _phong_khac(session, ma_phong)
    ho_so, ve_phong = _tao_va_phan_loai(client, session, ma_loai)
    # Tầng I ghi trường gợi ý — không bao giờ trường quyết định
    session.execute(
        update(Request).where(Request.id == ho_so.id).values(suggested_department_code=khac)
    )
    session.commit()

    goi_y = client.get(f"/coordination/requests/{ho_so.id}").json()["suggested_department"]
    assert (goi_y["code"], goi_y["source"]) == (khac, NGUON_MO_HINH)

    r = client.post(
        f"/coordination/requests/{ho_so.id}/transitions",
        json={"to_state": ve_phong, "changes": {"department_code": khac}},
    )
    assert r.status_code == 200, r.text
    dau = _su_kien_cuoi(session, ho_so.id).suggestion["department_code"]
    assert (dau["source"], dau["overridden"]) == (NGUON_MO_HINH, False)


def test_doi_loai_trong_cung_thao_tac_thi_so_theo_loai_moi(session, rule_set):
    """Thẻ đổi theo loại vừa chọn, nên phép so cũng phải theo loại cuối cùng."""
    cac_dong = session.execute(
        select(RequestTypeRouting.request_type_code, RequestTypeRouting.department_code)
        .join(Department, Department.code == RequestTypeRouting.department_code)
        .where(RequestTypeRouting.is_default, Department.is_active)
    ).all()
    theo_phong: dict[str, str] = {}
    for loai, phong in cac_dong:
        theo_phong.setdefault(phong, loai)
    if len(theo_phong) < 2:
        pytest.skip("dữ liệu khởi tạo cần hai loại về hai phòng khác nhau")
    (phong_cu, loai_cu), (phong_moi, loai_moi) = list(theo_phong.items())[:2]

    ho_so = create_case(
        session,
        title="Đổi loại khi chuyển phòng",
        requester_id=NGUOI_GUI.id,
        requester_label=NGUOI_GUI.label,
        request_type_code=loai_cu,
    )
    session.flush()

    dau = ghi_nhan_goi_y(
        session, ho_so, {"request_type_code": loai_moi, "department_code": phong_moi}
    )
    assert dau["department_code"]["suggested"] == phong_moi
    assert dau["department_code"]["overridden"] is False
    assert goi_y_phong(session, ho_so, ho_so.request_type_code).code == phong_cu


# ---------------------------------------------------------------------------
# Lớp báo cáo
# ---------------------------------------------------------------------------


def test_lop_bao_cao_dem_giu_va_ghi_de_theo_phong(client, session, rule_set):
    ma_loai, ma_phong = _loai_co_anh_xa(session)
    khac = _phong_khac(session, ma_phong)
    giu, ve_phong = _tao_va_phan_loai(client, session, ma_loai)
    doi, _ = _tao_va_phan_loai(client, session, ma_loai)
    for ho_so, phong in ((giu, ma_phong), (doi, khac)):
        r = client.post(
            f"/coordination/requests/{ho_so.id}/transitions",
            json={"to_state": ve_phong, "changes": {"department_code": phong}},
        )
        assert r.status_code == 200, r.text

    dong = {
        d.ma_ho_so: d
        for d in session.execute(
            text(
                "SELECT ma_ho_so, ma_truong, ma_nguon, ghi_de, so_ghi_de, ma_phong, nguon, truong"
                " FROM bao_cao_goi_y WHERE ma_ho_so IN (:a, :b)"
            ),
            {"a": giu.id, "b": doi.id},
        )
    }
    assert (dong[giu.id].ghi_de, dong[giu.id].so_ghi_de) == (False, 0)
    assert (dong[doi.id].ghi_de, dong[doi.id].so_ghi_de) == (True, 1)
    assert dong[giu.id].ma_phong == ma_phong and dong[doi.id].ma_phong == khac
    assert {d.ma_truong for d in dong.values()} == {"department_code"}
    assert {d.ma_nguon for d in dong.values()} == {NGUON_BANG_ANH_XA}
    # Nhãn tiếng Việt cho bảng điều khiển, không phải mã
    assert dong[giu.id].truong != "department_code" and dong[giu.id].nguon != NGUON_BANG_ANH_XA
