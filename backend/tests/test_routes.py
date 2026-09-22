# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử các điểm cuối nghiệp vụ của cổng người dùng (#44).
#
# Phần định danh được thay bằng một tác nhân giả, vì chuỗi kiểm chữ ký token đã có bộ
# kiểm thử riêng ở test_auth.py. Ở đây cần kiểm chuyện khác: điểm cuối có trả đúng
# những gì engine cho phép không, và có chặn hồ sơ của người khác không.
#
# Điểm quan trọng nhất của tệp này: **danh sách nút bấm mà giao diện nhận được phải
# khớp khít với ma trận phân quyền trong dữ liệu**. Đây chính là chỗ bản thiết kế vẽ
# sai — nó đặt nút "Hủy yêu cầu" ở hai trạng thái không có cạnh đó.

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.dependencies import current_actor
from app.db import get_session
from app.main import app
from app.models.workflow_config import Department, Priority, RequestType, State
from app.workflow.context import Actor
from app.workflow.engine import perform_transition

NGUOI_TAO = "nd-cong-001"
NGUOI_KHAC = "nd-cong-002"


@pytest.fixture
def client(session):
    """Máy khách HTTP dùng chung phiên cơ sở dữ liệu của bài kiểm thử.

    Nhờ dùng chung phiên, mọi thứ điểm cuối ghi vào đều nằm trong giao dịch được hoàn
    tác ở cuối bài — kể cả khi mã nguồn gọi `commit`, vì phiên gắn vào một điểm lưu
    bên trong một giao dịch lớn hơn.

    HỆ QUẢ PHẢI NHỚ: phần dựng cảnh của mỗi bài phải `commit`, không được dừng ở
    `flush`. Điểm cuối chuyển trạng thái gọi `session.rollback()` khi engine từ chối
    — trong đời thật mỗi yêu cầu HTTP có phiên riêng nên cú hoàn tác đó chỉ chạm vào
    phần dở dang của chính nó, nhưng ở đây phiên dùng chung nên nó cuốn luôn mọi thứ
    chưa đóng. Bài nào cố tình gọi một thao tác bị từ chối rồi gọi tiếp sẽ thấy hồ sơ
    tụt về trạng thái đầu. Dùng `commit` cũng đúng với đời thật hơn: mỗi lần chuyển
    trạng thái là một giao dịch đã đóng trước khi yêu cầu sau đi tới.
    """
    actor = Actor(
        id=NGUOI_TAO,
        name="Nguyễn Minh Anh",
        roles=frozenset({"requester"}),
    )
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: actor
    with TestClient(app) as c:
        c.actor = actor
        yield c
    app.dependency_overrides.clear()


def _tao(client, title="Máy in phòng kế toán kẹt giấy") -> dict:
    """Gửi một yêu cầu CÓ chọn loại — trường hợp thường gặp trên biểu mẫu ba bước.

    Có loại thì hồ sơ đi tiếp được qua cạnh phân loại, vì ràng buộc `set-request-type`
    đòi hồ sơ phải có loại khi rời tay người phân loại (#78).
    """
    loai = client.get("/request-types").json()[0]["code"]
    r = client.post(
        "/requests",
        json={"title": title, "description": "Mô tả thử.", "request_type_code": loai},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Danh mục
# ---------------------------------------------------------------------------


def test_danh_muc_loai_yeu_cau_lay_tu_du_lieu(client, session, rule_set):
    """Giao diện dựng lựa chọn từ đây, không viết cứng bốn loại vào mã."""
    r = client.get("/request-types")
    assert r.status_code == 200

    tu_api = {x["code"] for x in r.json()}
    tu_bang = set(
        session.scalars(
            select(RequestType.code).where(RequestType.is_active)
        ).all()
    )
    assert tu_api == tu_bang

    for x in r.json():
        assert x["label"], "mọi loại phải có nhãn hiển thị"
        assert x["sla_hours"] > 0


# ---------------------------------------------------------------------------
# Gửi và tra cứu
# ---------------------------------------------------------------------------


def test_gui_yeu_cau_vao_dung_trang_thai_dau(client, rule_set):
    ho_so = _tao(client)

    assert ho_so["state"]["code"] == "submitted"
    assert ho_so["state"]["label"] == "Đã gửi"
    assert ho_so["code"].startswith("YC-")
    assert ho_so["history"] == [], "tạo hồ sơ không sinh sự kiện"


def test_gui_yeu_cau_khong_dat_duoc_muc_uu_tien(client, rule_set):
    """Poka-yoke: người gửi không tự đặt mức ưu tiên.

    Biểu mẫu không có ô đó, và lược đồ dữ liệu vào cũng không nhận trường đó — gửi
    kèm cũng bị bỏ qua chứ không ghi vào hồ sơ.
    """
    r = client.post(
        "/requests",
        json={"title": "Thử đặt ưu tiên", "priority_code": "urgent"},
    )
    assert r.status_code == 201
    chi_tiet = client.get(f"/requests/{r.json()['id']}").json()
    assert chi_tiet.get("priority_code") is None


def test_gui_yeu_cau_dat_duoc_loai_tu_danh_muc(client, session, rule_set):
    """Người gửi chọn loại yêu cầu — trường quyết định duy nhất họ tự đặt được."""
    ma_loai = client.get("/request-types").json()[0]["code"]

    r = client.post(
        "/requests",
        json={"title": "Máy chiếu phòng họp không lên hình", "request_type_code": ma_loai},
    )
    assert r.status_code == 201
    assert r.json()["request_type"]["code"] == ma_loai
    assert r.json()["request_type"]["label"], "nhãn hiển thị đi kèm mã"

    # Có loại thì có ngưỡng cam kết ngay từ lúc gửi, không phải đợi phân loại
    assert r.json()["sla_limit_seconds"] > 0


def test_gui_yeu_cau_khong_chon_loai_van_duoc(client, rule_set):
    """Bỏ trống vẫn gửi được: người phân loại sẽ đặt loại ở cạnh kế tiếp."""
    r = client.post("/requests", json={"title": "Chưa rõ nên xếp vào loại nào"})
    assert r.status_code == 201
    assert r.json()["request_type"] is None
    assert r.json()["sla_limit_seconds"] is None


def test_gui_yeu_cau_tu_choi_loai_ngoai_danh_muc(client, rule_set):
    """Mã lạ bị chặn ở lớp ứng dụng, không để khóa ngoại nổ thành lỗi 500."""
    r = client.post(
        "/requests",
        json={"title": "Loại bịa ra", "request_type_code": "khong-co-that"},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "unknown-request-type"


def test_chi_thay_ho_so_cua_minh(client, session, rule_set):
    cua_toi = _tao(client, "Hồ sơ của tôi")

    # Một hồ sơ của người khác, tạo thẳng qua engine
    from app.workflow.engine import create_case

    cua_nguoi_khac = create_case(
        session, title="Hồ sơ người khác", requester_id=NGUOI_KHAC
    )
    session.commit()

    ma_trong_danh_sach = {h["id"] for h in client.get("/requests").json()}
    assert cua_toi["id"] in ma_trong_danh_sach
    assert cua_nguoi_khac.id not in ma_trong_danh_sach

    # Mở thẳng bằng định danh cũng không được, và trả 404 chứ không 403 —
    # 403 sẽ xác nhận hồ sơ đó tồn tại cho người dò số
    assert client.get(f"/requests/{cua_nguoi_khac.id}").status_code == 404


def test_khong_chuyen_duoc_trang_thai_ho_so_nguoi_khac(client, session, rule_set):
    from app.workflow.engine import create_case

    cua_nguoi_khac = create_case(session, title="Của người khác", requester_id=NGUOI_KHAC)
    session.commit()

    r = client.post(
        f"/requests/{cua_nguoi_khac.id}/transitions",
        json={"to_state": "cancelled"},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Nút bấm phải khớp ma trận phân quyền
# ---------------------------------------------------------------------------


def test_nut_bam_khop_voi_du_lieu_o_trang_thai_dau(client, rule_set):
    """Ở `Đã gửi`, người tạo chỉ hủy được — đúng một cạnh trong dữ liệu."""
    ho_so = _tao(client)
    di_duoc = {t["to_state"] for t in ho_so["allowed_transitions"]}
    assert di_duoc == {"cancelled"}

    canh = ho_so["allowed_transitions"][0]
    assert canh["to_state_label"] == "Đã hủy"
    assert canh["activity_label"] == "Hủy yêu cầu"


def test_khong_hien_nut_huy_khi_dang_xu_ly(client, session, rule_set, phong_ban):
    """Đây là chỗ bản thiết kế vẽ sai, và là lý do nút bấm phải lấy từ API.

    Ràng buộc Poka-yoke *chỉ hủy trước khi vào xử lý* được thực thi bằng sự VẮNG MẶT
    của cạnh. Bản mockup đặt nút "Hủy yêu cầu" ở `Đang xử lý` và `Đã leo thang`; dữ
    liệu không có cạnh nào như vậy, nên danh sách trả về phải rỗng phần hủy.
    """
    ho_so = _tao(client)
    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()
    pl = Actor(id="pl-01", roles=frozenset({"classifier"}), name="Trần Thu Hà")
    xd = Actor(
        id="xd-01",
        roles=frozenset({"approver"}),
        departments=frozenset({phong_ban}),
        name="Lê Quốc Dũng",
    )

    perform_transition(
        session, case_id=ho_so["id"], to_state="classified", actor=pl,
        changes={"priority_code": uu_tien},
    )
    perform_transition(
        session, case_id=ho_so["id"], to_state="awaiting-acceptance", actor=pl,
        changes={"department_code": phong_ban},
    )
    perform_transition(
        session, case_id=ho_so["id"], to_state="in-progress", actor=xd
    )
    session.commit()

    di_duoc = {
        t["to_state"]
        for t in client.get(f"/requests/{ho_so['id']}").json()["allowed_transitions"]
    }
    assert "cancelled" not in di_duoc
    assert di_duoc == set(), "người tạo không đi được cạnh nào khi đang xử lý"

    # Và nếu cố tình gọi thẳng API thì engine chặn
    r = client.post(
        f"/requests/{ho_so['id']}/transitions", json={"to_state": "cancelled"}
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "transition-not-allowed"


def test_trang_thai_hoan_tat_cho_hai_lua_chon(client, session, rule_set, phong_ban):
    """`Hoàn tất` là trạng thái đòi người dùng quyết: xác nhận đạt, hoặc mở lại."""
    ho_so = _tao(client)
    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()
    pl = Actor(id="pl-01", roles=frozenset({"classifier"}))
    xd = Actor(id="xd-01", roles=frozenset({"approver"}), departments=frozenset({phong_ban}))
    xl = Actor(id="xl-01", roles=frozenset({"handler"}), departments=frozenset({phong_ban}))

    for den, ai, doi in (
        ("classified", pl, {"priority_code": uu_tien}),
        ("awaiting-acceptance", pl, {"department_code": phong_ban}),
        ("in-progress", xd, None),
        ("completed", xl, None),
    ):
        perform_transition(
            session, case_id=ho_so["id"], to_state=den, actor=ai, changes=doi
        )
    session.commit()

    canh = client.get(f"/requests/{ho_so['id']}").json()["allowed_transitions"]
    assert {t["to_state"] for t in canh} == {"closed", "in-progress"}

    # Mở lại bắt buộc ghi lý do, xác nhận đạt thì không
    theo_dich = {t["to_state"]: t for t in canh}
    assert theo_dich["in-progress"]["requires_note"] is True
    assert theo_dich["closed"]["requires_note"] is False


# ---------------------------------------------------------------------------
# Thực hiện thao tác
# ---------------------------------------------------------------------------


def test_huy_yeu_cau_thanh_cong_va_sinh_su_kien(client, rule_set):
    ho_so = _tao(client)

    r = client.post(
        f"/requests/{ho_so['id']}/transitions", json={"to_state": "cancelled"}
    )
    assert r.status_code == 200

    sau = r.json()
    assert sau["state"]["code"] == "cancelled"
    assert sau["state"]["is_terminal"] is True
    assert len(sau["history"]) == 1
    assert sau["allowed_transitions"] == [], "trạng thái kết thúc không còn thao tác nào"

    su_kien = sau["history"][0]
    assert su_kien["from_state_label"] == "Đã gửi"
    assert su_kien["to_state_label"] == "Đã hủy"
    assert su_kien["actor_label"] == "Nguyễn Minh Anh", "nhật ký ghi TÊN, không phải mã"
    assert su_kien["is_system"] is False


def test_canh_bat_buoc_ly_do_bi_chan_khi_thieu(client, session, rule_set, phong_ban):
    ho_so = _tao(client)
    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()
    pl = Actor(id="pl-01", roles=frozenset({"classifier"}))
    xd = Actor(id="xd-01", roles=frozenset({"approver"}), departments=frozenset({phong_ban}))
    xl = Actor(id="xl-01", roles=frozenset({"handler"}), departments=frozenset({phong_ban}))

    for den, ai, doi in (
        ("classified", pl, {"priority_code": uu_tien}),
        ("awaiting-acceptance", pl, {"department_code": phong_ban}),
        ("in-progress", xd, None),
        ("completed", xl, None),
    ):
        perform_transition(session, case_id=ho_so["id"], to_state=den, actor=ai, changes=doi)
    session.commit()

    thieu = client.post(
        f"/requests/{ho_so['id']}/transitions", json={"to_state": "in-progress"}
    )
    assert thieu.status_code == 422
    assert thieu.json()["detail"]["code"] == "note-required"

    du = client.post(
        f"/requests/{ho_so['id']}/transitions",
        json={"to_state": "in-progress", "note": "Máy vẫn kẹt giấy như cũ."},
    )
    assert du.status_code == 200
    assert du.json()["history"][-1]["note"] == "Máy vẫn kẹt giấy như cũ."


def test_dong_thoi_gian_giu_ca_doan_quay_lui(client, session, rule_set, phong_ban):
    """Dòng thời gian phải kể được cả những lần hồ sơ đi vòng.

    Đây là điểm đặc sắc của đề tài: một thanh tiến trình tuyến tính sẽ giấu mất đoạn
    bị từ chối rồi định tuyến lại, mà đó đúng là mẫu lệch chuẩn đáng giá nhất.
    """
    ho_so = _tao(client)
    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()
    pl = Actor(id="pl-01", roles=frozenset({"classifier"}), name="Trần Thu Hà")
    xd = Actor(
        id="xd-01", roles=frozenset({"approver"}),
        departments=frozenset({phong_ban}), name="Lê Quốc Dũng",
    )

    perform_transition(session, case_id=ho_so["id"], to_state="classified", actor=pl,
                       changes={"priority_code": uu_tien})
    perform_transition(session, case_id=ho_so["id"], to_state="awaiting-acceptance",
                       actor=pl, changes={"department_code": phong_ban})
    perform_transition(session, case_id=ho_so["id"], to_state="rejected-by-department",
                       actor=xd, note="Sai chuyên môn, thuộc phòng khác.")
    perform_transition(session, case_id=ho_so["id"], to_state="classified", actor=pl)
    session.commit()

    lich_su = client.get(f"/requests/{ho_so['id']}").json()["history"]
    duong_di = [(e["from_state"], e["to_state"]) for e in lich_su]

    assert duong_di == [
        ("submitted", "classified"),
        ("classified", "awaiting-acceptance"),
        ("awaiting-acceptance", "rejected-by-department"),
        ("rejected-by-department", "classified"),
    ]
    assert lich_su[2]["note"].startswith("Sai chuyên môn")
    assert lich_su[3]["activity_label"] == "Định tuyến lại phòng khác"

    # Hồ sơ quay lại `classified` lần thứ hai — đoạn quay lui nằm nguyên trong nhật ký
    assert duong_di.count(("submitted", "classified")) == 1
    assert [t for _, t in duong_di].count("classified") == 2


def test_su_kien_he_thong_phan_biet_duoc_voi_nguoi(client, session, rule_set, phong_ban):
    ho_so = _tao(client)
    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()
    pl = Actor(id="pl-01", roles=frozenset({"classifier"}), name="Trần Thu Hà")
    xd = Actor(id="xd-01", roles=frozenset({"approver"}),
               departments=frozenset({phong_ban}), name="Lê Quốc Dũng")

    perform_transition(session, case_id=ho_so["id"], to_state="classified", actor=pl,
                       changes={"priority_code": uu_tien})
    perform_transition(session, case_id=ho_so["id"], to_state="awaiting-acceptance",
                       actor=pl, changes={"department_code": phong_ban})
    perform_transition(session, case_id=ho_so["id"], to_state="in-progress", actor=xd)
    perform_transition(session, case_id=ho_so["id"], to_state="escalated",
                       actor=Actor.system("sla-watcher"))
    session.commit()

    cuoi = client.get(f"/requests/{ho_so['id']}").json()["history"][-1]
    assert cuoi["is_system"] is True
    assert cuoi["actor_label"] == "Hệ thống"
    assert cuoi["to_state_label"] == "Đã leo thang"


def test_dong_ho_sla_hien_ra_trong_phan_hoi(client, session, rule_set, phong_ban):
    ho_so = _tao(client)
    loai = session.scalars(
        select(RequestType).order_by(RequestType.display_order)
    ).first()
    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()
    pl = Actor(id="pl-01", roles=frozenset({"classifier"}))
    xd = Actor(id="xd-01", roles=frozenset({"approver"}), departments=frozenset({phong_ban}))

    perform_transition(session, case_id=ho_so["id"], to_state="classified", actor=pl,
                       changes={"priority_code": uu_tien, "request_type_code": loai.code})
    perform_transition(session, case_id=ho_so["id"], to_state="awaiting-acceptance",
                       actor=pl, changes={"department_code": phong_ban})
    perform_transition(session, case_id=ho_so["id"], to_state="in-progress", actor=xd)
    session.commit()

    d = client.get(f"/requests/{ho_so['id']}").json()
    assert d["sla_limit_seconds"] == loai.sla_hours * 3600
    assert d["sla_overdue"] is False
    assert d["sla_paused"] is False
    assert d["request_type"]["label"] == loai.label
    assert d["department"]["code"] == phong_ban


def test_danh_muc_trang_thai_du_cho_bang_chu_giai(client, session, rule_set):
    """Bảng chú giải cần cả trạng thái người dùng chưa từng đi qua."""
    r = client.get("/states")
    assert r.status_code == 200

    tu_api = [x["code"] for x in r.json()]
    tu_bang = session.scalars(
        select(State.code)
        .where(State.rule_set_id == rule_set.id)
        .order_by(State.display_order)
    ).all()

    assert tu_api == list(tu_bang), "đúng danh sách và đúng thứ tự hiển thị"
    assert any(x["is_terminal"] for x in r.json()), "phải có ít nhất một trạng thái đóng"


def test_loi_truong_khong_duoc_phep_dich_sang_422():
    """Nội dung gửi kèm sai, không phải xung đột trạng thái — nên 422 chứ không 409.

    Cổng #44 không nhận trường `changes` nên không kích được lỗi này qua HTTP, nhưng
    buồng lái #45 sẽ nhận, và bảng `MA_HTTP` phải sẵn sàng từ trước.
    """
    from app.workflow.errors import FieldNotPermitted
    from app.workflow.routes import _bao_loi

    loi = _bao_loi(FieldNotPermitted({"priority_code"}, "không đặt được"))
    assert loi.status_code == 422
    assert loi.detail["code"] == "field-not-permitted"
