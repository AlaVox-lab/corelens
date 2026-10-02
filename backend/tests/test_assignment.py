# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử danh sách người nhận việc (#84).
#
# Hai tầng, giống test_auth.py:
#
#   Đơn vị — danh bạ giả thay cho Keycloak. Kiểm cửa vào, bộ lọc vai trò, và việc
#            danh bạ hỏng phải thành 503 chứ không thành danh sách rỗng.
#   Tích hợp — danh bạ thật gọi Keycloak đang chạy. Kiểm dữ liệu realm mẫu, và kiểm
#              tài khoản dịch vụ KHÔNG làm được gì ngoài đọc. Tự bỏ qua nếu không có cụm.

from __future__ import annotations

import json
import socket
import threading
import time
import urllib.error
import urllib.request

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.auth.dependencies import current_actor
from app.auth.directory import (
    DirectoryUnavailable,
    KeycloakDirectory,
    Person,
    get_directory,
)
from app.config import get_settings
from app.db import get_session
from app.main import app
from app.models.workflow_config import (
    Role,
    Transition,
    TransitionGuard,
    TransitionRole,
)
from app.rules.guards import GUARD_REGISTRY
from app.workflow.assignment import vai_tro_giao_viec, vai_tro_nhan_viec
from app.workflow.context import Actor

# ---------------------------------------------------------------------------
# Đáp án tra từ dữ liệu, bằng đường khác với mã được kiểm
# ---------------------------------------------------------------------------

_RANG_BUOC_QUAN_NGUOI_XU_LY = frozenset(
    ma for ma, g in GUARD_REGISTRY.items() if "assignee_id" in g.governs
)


def _canh_giao_viec(session, rule_set) -> list[Transition]:
    """Đi từ bảng `transition_guards` và cờ `governs` của từng ràng buộc, thay vì qua
    `permitted_fields()` như mã được kiểm."""
    return list(
        session.scalars(
            select(Transition)
            .join(TransitionGuard, TransitionGuard.transition_id == Transition.id)
            .where(
                Transition.rule_set_id == rule_set.id,
                Transition.is_system.is_(False),
                TransitionGuard.guard_code.in_(_RANG_BUOC_QUAN_NGUOI_XU_LY),
            )
        ).all()
    )


def _canh_ra_khoi_dich(session, rule_set) -> list[Transition]:
    dich = {t.to_state for t in _canh_giao_viec(session, rule_set)}
    return list(
        session.scalars(
            select(Transition).where(
                Transition.rule_set_id == rule_set.id,
                Transition.is_system.is_(False),
                Transition.from_state.in_(dich),
            )
        ).all()
    )


@pytest.fixture
def hai_tap(session, rule_set) -> tuple[frozenset[str], frozenset[str]]:
    """(vai trò giao việc, vai trò nhận việc) theo đáp án độc lập."""
    giao = frozenset(r for t in _canh_giao_viec(session, rule_set) for r in t.role_codes)
    nhan = frozenset(
        r for t in _canh_ra_khoi_dich(session, rule_set) for r in t.role_codes
    )
    if not giao or not nhan:
        pytest.skip("Bộ quy tắc hiện tại không có cạnh nào cho giao người xử lý.")
    return giao, nhan


# ---------------------------------------------------------------------------
# Danh bạ giả và máy khách HTTP
# ---------------------------------------------------------------------------


class DanhBaGia:
    """Thay Keycloak. Ghi lại đã bị hỏi phòng nào, để kiểm cửa chặn TRƯỚC khi hỏi."""

    def __init__(self, nguoi: list[Person] | None = None, loi: str | None = None):
        self.nguoi = nguoi or []
        self.loi = loi
        self.da_hoi: list[str] = []

    def department_members(self, department_code: str) -> list[Person]:
        self.da_hoi.append(department_code)
        if self.loi:
            raise DirectoryUnavailable(self.loi)
        return self.nguoi


@pytest.fixture
def client(session):
    """Máy khách HTTP đổi được người gọi và danh bạ. Mặc định: danh bạ giả rỗng."""
    trang_thai = {"actor": None, "danh_ba": DanhBaGia()}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: trang_thai["actor"]
    app.dependency_overrides[get_directory] = lambda: trang_thai["danh_ba"]
    with TestClient(app) as c:
        c.trang_thai = trang_thai
        yield c
    app.dependency_overrides.clear()


def _goi(client, actor: Actor, phong: str, danh_ba=None):
    client.trang_thai["actor"] = actor
    if danh_ba is not None:
        client.trang_thai["danh_ba"] = danh_ba
    return client.get(f"/departments/{phong}/assignees")


def _truong_phong(hai_tap, phong: str) -> Actor:
    giao, _ = hai_tap
    return Actor(
        id="nd-tp-001", name="Trưởng Phòng", roles=giao, departments=frozenset({phong})
    )


# ---------------------------------------------------------------------------
# Suy vai trò từ bộ quy tắc
# ---------------------------------------------------------------------------


def test_vai_tro_giao_va_nhan_viec_suy_tu_bo_quy_tac(session, rule_set, hai_tap):
    giao, nhan = hai_tap
    assert vai_tro_giao_viec(session, rule_set.id) == giao
    assert vai_tro_nhan_viec(session, rule_set.id) == nhan
    assert not (giao & nhan), "người giao việc và người nhận việc là hai vai khác nhau"


def test_them_vai_tro_vao_ma_tran_thi_nguoi_do_nhan_duoc_viec(session, rule_set, hai_tap):
    """Đổi dữ liệu, không đổi mã: cho một vai trò mới đi một cạnh ra khỏi trạng thái
    mà hồ sơ tới sau khi được giao, thì vai trò đó nhận được việc."""
    _, nhan = hai_tap
    session.add(Role(code="vai-tro-thu-nghiem", label="Vai trò thử nghiệm"))
    session.flush()
    canh = _canh_ra_khoi_dich(session, rule_set)[0]
    session.add(TransitionRole(transition_id=canh.id, role_code="vai-tro-thu-nghiem"))
    session.flush()
    session.expire_all()

    assert vai_tro_nhan_viec(session, rule_set.id) == nhan | {"vai-tro-thu-nghiem"}


def test_go_rang_buoc_giao_nguoi_thi_khong_ai_mo_duoc_danh_sach(
    client, session, rule_set, hai_tap, phong_ban
):
    """Cửa vào cũng suy từ dữ liệu: không cạnh nào cho đặt người xử lý thì không ai
    có lý do xem danh sách người nhận việc — kể cả trưởng phòng."""
    session.execute(
        delete(TransitionGuard).where(
            TransitionGuard.guard_code.in_(_RANG_BUOC_QUAN_NGUOI_XU_LY)
        )
    )
    session.commit()
    session.expire_all()

    assert vai_tro_giao_viec(session, rule_set.id) == frozenset()
    danh_ba = DanhBaGia()
    r = _goi(client, _truong_phong(hai_tap, phong_ban), phong_ban, danh_ba)
    assert r.status_code == 403
    assert danh_ba.da_hoi == []


# ---------------------------------------------------------------------------
# Cửa
# ---------------------------------------------------------------------------


def test_nguoi_khong_giao_duoc_viec_bi_chan(client, hai_tap, phong_ban):
    """Người xử lý thuộc đúng phòng vẫn không xem được: họ nhận việc chứ không giao."""
    _, nhan = hai_tap
    nguoi_xu_ly = Actor(id="nd-xl-001", roles=nhan, departments=frozenset({phong_ban}))
    danh_ba = DanhBaGia()

    r = _goi(client, nguoi_xu_ly, phong_ban, danh_ba)

    assert r.status_code == 403
    assert danh_ba.da_hoi == [], "bị chặn thì Keycloak không được hỏi tới"


def test_truong_phong_khong_xem_duoc_nguoi_phong_khac(client, hai_tap, phong_ban):
    danh_ba = DanhBaGia()
    r = _goi(client, _truong_phong(hai_tap, phong_ban), phong_ban + "-khac", danh_ba)
    assert r.status_code == 403
    assert danh_ba.da_hoi == []


def test_phong_ban_khong_ton_tai_tra_404(client, hai_tap):
    danh_ba = DanhBaGia()
    r = _goi(client, _truong_phong(hai_tap, "khong-co-phong-nay"), "khong-co-phong-nay", danh_ba)
    assert r.status_code == 404
    assert danh_ba.da_hoi == []


# ---------------------------------------------------------------------------
# Kết quả
# ---------------------------------------------------------------------------


def test_chi_tra_nguoi_nhan_duoc_viec_cua_dung_phong(client, hai_tap, phong_ban):
    giao, nhan = hai_tap
    danh_ba = DanhBaGia(
        [
            Person("sub-001", "xu.ly.mot", "Xử Lý Một", frozenset(nhan) | {"offline_access"}),
            Person("sub-002", "truong.phong", "Trưởng Phòng", frozenset(giao)),
            Person("sub-003", "chua.co.vai", "Chưa Có Vai", frozenset({"offline_access"})),
        ]
    )

    r = _goi(client, _truong_phong(hai_tap, phong_ban), phong_ban, danh_ba)

    assert r.status_code == 200
    than = r.json()
    assert danh_ba.da_hoi == [phong_ban]
    assert than["department"]["code"] == phong_ban
    assert than["department"]["label"], "nhãn phòng lấy từ bảng dữ liệu"
    assert than["people"] == [
        {"id": "sub-001", "name": "Xử Lý Một", "username": "xu.ly.mot"}
    ]


def test_danh_ba_hong_tra_503_chu_khong_tra_danh_sach_rong(client, hai_tap, phong_ban):
    """Danh sách rỗng nghĩa là phòng không có ai. 503 nghĩa là không biết phòng có
    ai. Gộp hai điều đó làm một là giả vờ ổn."""
    danh_ba = DanhBaGia(loi="Không gọi được Keycloak: Connection refused")

    r = _goi(client, _truong_phong(hai_tap, phong_ban), phong_ban, danh_ba)

    assert r.status_code == 503
    assert r.json()["detail"] == {
        "code": "directory-unavailable",
        "message": "Không gọi được Keycloak: Connection refused",
    }


# ---------------------------------------------------------------------------
# Máy khách Keycloak — các đường hỏng, không cần Keycloak
# ---------------------------------------------------------------------------


def _danh_ba(base_url: str, *, bi_mat: str = "bi-mat", tran: float = 3.0) -> KeycloakDirectory:
    return KeycloakDirectory(
        base_url=base_url,
        realm="dx-os-lab",
        client_id="dx-directory",
        client_secret=bi_mat,
        department_prefix="/phong-ban/",
        timeout_seconds=tran,
    )


def _cong_dang_dong() -> int:
    """Một cổng chắc chắn không ai nghe."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_keycloak_tat_thi_bao_khong_phan_hoi():
    with pytest.raises(DirectoryUnavailable, match="Không gọi được Keycloak"):
        _danh_ba(f"http://127.0.0.1:{_cong_dang_dong()}").department_members("it")


def test_keycloak_treo_thi_dung_dung_tran_thoi_gian():
    """Keycloak nhận kết nối rồi im lặng — kiểu hỏng tệ nhất, vì không có lỗi nào để
    bắt. Trần thời gian là thứ duy nhất cứu trang khỏi treo theo."""
    may_chu = socket.socket()
    may_chu.bind(("127.0.0.1", 0))
    may_chu.listen()
    ket_noi: list[socket.socket] = []
    threading.Thread(target=lambda: ket_noi.append(may_chu.accept()[0]), daemon=True).start()

    bat_dau = time.monotonic()
    try:
        with pytest.raises(DirectoryUnavailable):
            _danh_ba(f"http://127.0.0.1:{may_chu.getsockname()[1]}", tran=0.5).department_members("it")
    finally:
        for k in ket_noi:
            k.close()
        may_chu.close()

    assert time.monotonic() - bat_dau < 2


def test_dns_treo_van_tra_loi_dung_han(monkeypatch):
    """Tắt Keycloak trong cụm Compose thì tên `keycloak` hết người trả lời và bước tra
    DNS treo — đo thật được 8 giây. `timeout` của urllib không phủ bước này, nên trần
    thời gian phải giữ ở vòng ngoài."""

    def dns_treo(*_a, **_k):
        time.sleep(3)
        raise socket.gaierror("giả lập DNS không trả lời")

    monkeypatch.setattr(socket, "getaddrinfo", dns_treo)

    bat_dau = time.monotonic()
    with pytest.raises(DirectoryUnavailable, match="không trả lời xong"):
        _danh_ba("http://keycloak:8080", tran=0.5).department_members("it")
    assert time.monotonic() - bat_dau < 1.5


def test_thieu_bi_mat_thi_bao_ro_ma_khong_goi_mang():
    with pytest.raises(DirectoryUnavailable, match="DXLAB_DIRECTORY_CLIENT_SECRET"):
        _danh_ba(f"http://127.0.0.1:{_cong_dang_dong()}", bi_mat="").department_members("it")


# ---------------------------------------------------------------------------
# Tích hợp với Keycloak thật
# ---------------------------------------------------------------------------


def test_danh_ba_that_tra_dung_nguoi_cua_tung_phong(danh_ba_that):
    """Kiểm cả những thứ danh bạ giả không kiểm được: tài khoản dịch vụ có đủ quyền
    không, đường dẫn nhóm có đúng không, và tên ghép có khớp claim `name` không."""
    it = {p.username: p for p in danh_ba_that.department_members("it")}
    hr = {p.username: p for p in danh_ba_that.department_members("hr")}

    assert "tuan.ngo" not in it, "tài khoản đã khóa — người đã nghỉ việc — không được giao việc"
    assert set(it) == {"cuong.le", "dung.pham", "lan.vu"}
    assert set(hr) == {"ha.do"}
    assert it["cuong.le"].name == "Cường Lê"
    assert "handler" in it["cuong.le"].roles
    assert "approver" in it["dung.pham"].roles
    assert len(it["cuong.le"].id) == 36, "định danh là sub dạng UUID, không phải tên"


def test_danh_ba_that_phong_chua_co_nhom_thi_rong(danh_ba_that):
    assert danh_ba_that.department_members("khong-co-phong-nay") == []


def test_diem_cuoi_voi_keycloak_that(client, danh_ba_that, hai_tap):
    """Định nghĩa hoàn thành của #84 ở tầng dịch vụ: trưởng phòng CNTT thấy đúng hai
    người xử lý của phòng, kèm tên thật, không thấy chính mình hay người phòng khác."""
    truong_phong = Actor(
        id="nd-tp-001", roles=hai_tap[0], departments=frozenset({"it"})
    )
    r = _goi(client, truong_phong, "it", danh_ba_that)

    assert r.status_code == 200
    assert [(p["username"], p["name"]) for p in r.json()["people"]] == [
        ("cuong.le", "Cường Lê"),
        ("lan.vu", "Lan Vũ"),
    ]


def test_tai_khoan_dich_vu_chi_doc_duoc(danh_ba_that):
    """Quyền tối thiểu phải được kiểm, không chỉ được khai: tài khoản dịch vụ không
    đọc được cấu hình client — nơi chứa bí mật — và không tạo được người dùng."""
    cau_hinh = get_settings()
    token = danh_ba_that._lay_token(time.monotonic() + 5)
    goc = f"{cau_hinh.keycloak_internal_url.rstrip('/')}/admin/realms/{cau_hinh.keycloak_realm}"

    def goi(duong_dan: str, than: dict | None = None) -> int:
        yc = urllib.request.Request(
            goc + duong_dan,
            data=json.dumps(than).encode() if than is not None else None,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(yc, timeout=5) as ph:
                return ph.status
        except urllib.error.HTTPError as loi:
            return loi.code

    assert goi("/users?max=1") == 200, "đọc danh bạ thì được"
    assert goi("/clients") == 403
    assert goi("/users", {"username": "ke-gian", "enabled": True}) == 403


def test_bi_mat_sai_thi_bao_khong_cap_token(danh_ba_that):
    cau_hinh = get_settings()
    sai = _danh_ba(cau_hinh.keycloak_internal_url, bi_mat="bi-mat-sai")
    with pytest.raises(DirectoryUnavailable, match="không cấp token"):
        sai.department_members("it")
