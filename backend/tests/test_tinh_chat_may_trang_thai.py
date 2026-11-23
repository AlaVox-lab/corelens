# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử dựa trên tính chất cho máy trạng thái (#441).
#
# Bài theo ví dụ ở test_engine.py đi những đường người viết nghĩ ra. Bài này để Hypothesis tự sinh chuỗi
# thao tác ngẫu nhiên — tạo hồ sơ ở mọi quy trình đang bật, rồi cho một tác nhân bất kỳ (kể cả người không
# có vai của cạnh, kể cả tác nhân hệ thống) thử đi một cạnh bất kỳ của bảng `transitions`, kèm nhập liệu
# đúng lẫn sai — và kiểm bất biến của cửa chuyển trạng thái duy nhất sau MỖI bước:
#
#   a. chuyển thành công ⇒ đúng MỘT dòng nhật ký mới, của đúng hồ sơ đó; `from_state`/`to_state` khớp trạng
#      thái trước và sau; dòng đó ứng với một cạnh có thật trong bộ quy tắc của hồ sơ, và tác nhân có vai của
#      cạnh (tác nhân hệ thống chỉ đi cạnh hệ thống); rời trạng thái kết thúc chỉ bằng cạnh dữ liệu khai
#      `from_is_terminal` (cạnh mở lại);
#   b. bị từ chối (lỗi của app/workflow/errors.py) ⇒ không dòng nhật ký nào mới, trạng thái và mọi trường
#      một lần chuyển đặt được của hồ sơ giữ nguyên;
#   c. trạng thái hiện tại của mọi hồ sơ luôn thuộc bộ quy tắc mà hồ sơ ghim;
#   d. `allowed_transitions` chỉ trả cạnh đi ra từ trạng thái hiện tại mà tác nhân có vai.
#
# Lỗi khác `TransitionError` — lỗi cơ sở dữ liệu, `TypeError`… — không bị bắt: nó làm bài đỏ, vì cửa chuyển
# trạng thái chỉ được từ chối bằng lỗi có mã.
#
# Lựa chọn ngẫu nhiên nghiêng về phía "gần đúng" (đa số lần: cạnh đi ra từ trạng thái hiện tại, tác nhân có
# một vai của cạnh, giá trị lấy từ danh mục) để chuỗi thao tác đi sâu được vào luồng; phần còn lại là cạnh,
# vai, giá trị sai. Cuối bài tự kiểm nó không rỗng: mọi bộ quy tắc đang bật đều có lần chuyển thành công.
#
# Mọi mã trạng thái, mã quy trình, vai, phòng ban, loại yêu cầu đọc từ cơ sở dữ liệu lúc chạy (CLAUDE.md mục
# 1.2); trong bài chỉ có mã tác nhân giả và vài giá trị cố ý SAI.
#
# Mỗi ví dụ chạy trong một điểm lưu riêng, hoàn tác ở `teardown`, bên trong giao dịch của fixture `session`
# — không hồ sơ nào còn lại sau bài. Cơ sở dữ liệu ví dụ của Hypothesis tắt (`database=None`): lượt sau không
# phát lại phản ví dụ cũ một cách ngầm định — phản ví dụ đọc thẳng trên đầu ra của pytest, lặp lại bằng seed.
# Hypothesis vẫn ghi bộ đệm hằng số vào `.hypothesis/` lúc chạy, nên thư mục đó nằm trong .gitignore và
# backend/.dockerignore.
#
# Mặc định là bản nhanh cho CI. Bản dài (gấp mười số ví dụ), chọn seed, và in thống kê (`-s`) — trong
# container:
#
#     docker exec -e DXLAB_TINH_CHAT_DAI=1 dxlab-backend python -m pytest -p no:cacheprovider -q -s \
#         tests/test_tinh_chat_may_trang_thai.py --hypothesis-seed=12345

from __future__ import annotations

import os
from collections import Counter, defaultdict
from dataclasses import dataclass

from hypothesis import HealthCheck, settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    precondition,
    rule,
    run_state_machine_as_test,
)
from sqlalchemy import func, select

from app.models.case import MO_TA_TOI_DA, TIEU_DE_TOI_DA, TIEU_DE_TOI_THIEU, EventLog, Request
from app.models.workflow_config import (
    Department,
    Priority,
    RequestType,
    RequestTypeField,
    Role,
    RuleSet,
    State,
    Transition,
)
from app.rules.guards import permitted_fields
from app.workflow.context import Actor
from app.workflow.engine import CHANGEABLE_FIELDS, allowed_transitions, create_case, perform_transition
from app.workflow.errors import TransitionError

# Bản nhanh cho CI; DXLAB_TINH_CHAT_DAI=1 nhân số ví dụ lên mười cho lượt thử tay.
SO_VI_DU = 80 * (10 if os.environ.get("DXLAB_TINH_CHAT_DAI") == "1" else 1)
SO_BUOC = 50
# Tối đa bốn hồ sơ chưa kết thúc cùng lúc (hồ sơ kết thúc thì mở được hồ sơ mới), hai mươi hồ sơ mỗi ví dụ
SO_HO_SO_MO = 4
SO_HO_SO_TOI_DA = 20

CAU_HINH = settings(
    max_examples=SO_VI_DU,
    stateful_step_count=SO_BUOC,
    # Cơ sở dữ liệu thật: một bước có thể chậm hơn ngưỡng mặc định 200 ms mà không có gì sai
    deadline=None,
    database=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large, HealthCheck.filter_too_much],
)

# Mã tác nhân giả. Người gửi hồ sơ lấy từ cùng tập, để ràng buộc "chính người gửi" có lúc đạt, có lúc không.
TAC_NHAN = ("tc-01", "tc-02", "tc-03")

# Chữ cho ô nhập: bỏ ký tự điều khiển (Cc, gồm NUL mà cột TEXT của PostgreSQL không nhận) và nửa cặp thay thế
# (Cs, không mã hóa được UTF-8) — kiểm ký tự đầu vào là việc của lớp điểm cuối, không phải của máy trạng thái.
BANG_CHU = st.characters(blacklist_categories=("Cc", "Cs"))
CHU = st.text(alphabet=BANG_CHU, max_size=40)
SAI = st.sampled_from([None, "", "  ", "khong-co-trong-danh-muc", 7])

# Những cột một lần chuyển có thể đổi — bị từ chối thì không cột nào được đổi (bất biến b)
COT_HO_SO = (
    Request.rule_set_id,
    Request.current_state,
    Request.assignee_label,
    *(getattr(Request, truong) for truong in sorted(CHANGEABLE_FIELDS)),
)


@dataclass(frozen=True)
class Canh:
    """Bản chụp một dòng `transitions`, tách khỏi phiên ORM để không lệ thuộc việc hoàn tác điểm lưu."""

    rule_set_id: int
    from_state: str
    to_state: str
    activity: str
    is_system: bool
    vai: frozenset[str]
    rang_buoc: tuple[str, ...]
    from_is_terminal: bool
    # Dữ liệu khai cạnh là bước chính của trạng thái (`primary_scope`) — đường xuôi của luồng
    buoc_chinh: bool


@dataclass(frozen=True)
class DanhMuc:
    canh: tuple[Canh, ...]
    # rule_set_id → {mã trạng thái: là trạng thái kết thúc}
    trang_thai: dict[int, dict[str, bool]]
    quy_trinh_cua_bo: dict[int, str]
    loai_cua_quy_trinh: dict[str, tuple[str, ...]]
    # Loại yêu cầu đang dùng → các trường riêng (mã, kiểu, bắt buộc, lựa chọn)
    truong_loai: dict[str, tuple[tuple[str, str, bool, tuple[str, ...]], ...]]
    vai: tuple[str, ...]
    phong: tuple[str, ...]
    muc: tuple[str, ...]


@dataclass(frozen=True)
class BoiCanh:
    """Những gì của hồ sơ mà phép chọn tác nhân và giá trị cần biết."""

    rule_set_id: int
    current_state: str
    requester_id: str
    department_code: str | None
    request_type_code: str | None


def _doc_danh_muc(session) -> DanhMuc:
    canh = tuple(
        Canh(
            rule_set_id=c.rule_set_id,
            from_state=c.from_state,
            to_state=c.to_state,
            activity=c.activity_code,
            is_system=c.is_system,
            vai=frozenset(c.role_codes),
            rang_buoc=tuple(c.guard_codes),
            from_is_terminal=c.from_is_terminal,
            buoc_chinh=c.primary_scope is not None,
        )
        for c in session.scalars(select(Transition).order_by(Transition.id))
    )
    trang_thai: dict[int, dict[str, bool]] = defaultdict(dict)
    for s in session.scalars(select(State)):
        trang_thai[s.rule_set_id][s.code] = s.is_terminal

    loai_cua_quy_trinh: dict[str, list[str]] = defaultdict(list)
    for ma, quy_trinh in session.execute(
        select(RequestType.code, RequestType.process_code)
        .where(
            RequestType.is_active,
            RequestType.process_code.in_(select(RuleSet.process_code).where(RuleSet.is_active)),
        )
        .order_by(RequestType.code)
    ):
        loai_cua_quy_trinh[quy_trinh].append(ma)
    truong: dict[str, list] = {ma: [] for ds in loai_cua_quy_trinh.values() for ma in ds}
    for t in session.scalars(
        select(RequestTypeField).order_by(RequestTypeField.request_type_code, RequestTypeField.display_order)
    ):
        if t.request_type_code in truong:
            truong[t.request_type_code].append((t.code, t.kind, t.required, tuple(t.options or ())))

    return DanhMuc(
        canh=canh,
        trang_thai=dict(trang_thai),
        quy_trinh_cua_bo=dict(session.execute(select(RuleSet.id, RuleSet.process_code)).all()),
        loai_cua_quy_trinh={q: tuple(ds) for q, ds in loai_cua_quy_trinh.items()},
        truong_loai={ma: tuple(ds) for ma, ds in truong.items()},
        vai=tuple(session.scalars(select(Role.code).order_by(Role.code))),
        phong=tuple(session.scalars(select(Department.code).where(Department.is_active).order_by(Department.code))),
        muc=tuple(session.scalars(select(Priority.code).order_by(Priority.code))),
    )


def _gia_tri_truong_rieng(kieu: str, lua_chon: tuple[str, ...]) -> st.SearchStrategy:
    """Giá trị HỢP LỆ cho một trường riêng theo kiểu khai báo. Số trải hai phía các ngưỡng thường gặp."""
    if kieu == "number":
        return st.integers(min_value=0, max_value=20_000_000)
    if kieu == "date":
        return st.dates().map(lambda d: d.isoformat())
    if kieu == "text":
        return st.text(alphabet=BANG_CHU, min_size=1, max_size=40).filter(lambda s: s.strip())
    return st.sampled_from(lua_chon) if lua_chon else st.nothing()


def _chi_tiet_hop_le(dm: DanhMuc, loai: str | None) -> st.SearchStrategy:
    """Một bộ trường riêng hợp lệ cho loại yêu cầu: đủ trường bắt buộc, trường tùy chọn có hay không."""
    if loai is None:
        return st.just({})
    bat_buoc = {ma: _gia_tri_truong_rieng(k, lc) for ma, k, req, lc in dm.truong_loai[loai] if req}
    tuy_chon = {ma: _gia_tri_truong_rieng(k, lc) for ma, k, req, lc in dm.truong_loai[loai] if not req}
    return st.fixed_dictionaries(bat_buoc, optional=tuy_chon)


def _gia_tri_dung(dm: DanhMuc, truong: str, hs: BoiCanh) -> st.SearchStrategy:
    """Giá trị đúng cho một trường gửi kèm, lấy từ danh mục trong CSDL."""
    if truong == "department_code":
        return st.sampled_from(dm.phong)
    if truong == "priority_code":
        return st.sampled_from(dm.muc)
    if truong == "request_type_code":
        return st.sampled_from(dm.loai_cua_quy_trinh[dm.quy_trinh_cua_bo[hs.rule_set_id]])
    if truong == "assignee_id":
        return st.sampled_from(TAC_NHAN)
    if truong == "title":
        return st.text(alphabet=BANG_CHU, min_size=TIEU_DE_TOI_THIEU, max_size=40).filter(
            lambda s: len(s.strip()) >= TIEU_DE_TOI_THIEU
        )
    if truong == "description":
        return st.none() | CHU
    if truong == "details":
        return _chi_tiet_hop_le(dm, hs.request_type_code)
    if truong == "sla_extension_hours":
        return st.integers(min_value=1, max_value=8)
    return CHU


def _gia_tri_sai(dm: DanhMuc, truong: str) -> st.SearchStrategy:
    """Giá trị nhiều khả năng bị từ chối — không bảo đảm, bất biến không dựa vào kỳ vọng nào."""
    if truong == "request_type_code":
        return SAI | st.sampled_from(sorted(dm.truong_loai))
    if truong == "title":
        return SAI | st.just("x" * (TIEU_DE_TOI_DA + 1))
    if truong == "description":
        return st.sampled_from([7, "y" * (MO_TA_TOI_DA + 1)])
    if truong == "details":
        return SAI | st.sampled_from([{"khong-co-truong-nay": 1}, "khong-phai-bo"])
    if truong == "sla_extension_hours":
        return st.sampled_from([0, -2, "3", " 2 ", "abc", True, 10**9])
    return SAI


def _di_duoc(tac_nhan: Actor, canh: Canh) -> bool:
    """Tác nhân có vai của cạnh không — đặc tả viết lại độc lập với engine, không gọi hàm của engine."""
    if canh.is_system or tac_nhan.is_system:
        return canh.is_system and tac_nhan.is_system
    return bool(tac_nhan.roles & canh.vai)


def _thuong(data, nhan: str) -> bool:
    """Đúng phần lớn số lần — để nghiêng lựa chọn về phía gần đúng mà vẫn còn nhánh sai. Nhánh đúng ứng với
    giá trị 0, giá trị Hypothesis hay chọn và thu gọn về, nên phản ví dụ thu gọn cũng đi đường thường."""
    return data.draw(st.integers(min_value=0, max_value=9), label=nhan) != 9


class MayTrangThai(RuleBasedStateMachine):
    """Chuỗi thao tác ngẫu nhiên trên cửa chuyển trạng thái. `phien`, `dm` do bài gán trước khi chạy."""

    phien = None
    dm: DanhMuc | None = None
    # Đếm kết quả qua mọi ví dụ, để bài tự kiểm nó không rỗng
    thong_ke: Counter = Counter()

    def __init__(self) -> None:
        super().__init__()
        self.diem_luu = self.phien.begin_nested()
        self.cua_toi: list[int] = []
        self.ket_thuc: set[int] = set()
        self.so_buoc = 0
        # Số lần đã thử trên từng hồ sơ — độ xoay khi chọn cạnh và tác nhân cho hồ sơ đó
        self.lan_thu: Counter = Counter()

    @staticmethod
    def _chon(data, ds: list | tuple, nhan: str, xoay: int):
        """Một phần tử của `ds`. Hypothesis nghiêng về phần tử đầu danh sách (và hay lặp lại lựa chọn cũ), nên
        danh sách được xoay theo một bộ đếm của người gọi: phần tử "đầu" đổi qua từng lần, chuỗi thao tác
        không kẹt mãi ở một cạnh. Mỗi loại lựa chọn xoay theo bộ đếm riêng để chúng không đổi cùng nhịp."""
        k = xoay % len(ds)
        return data.draw(st.sampled_from([*ds[k:], *ds[:k]]), label=nhan)

    def teardown(self) -> None:
        self.diem_luu.rollback()

    # --- Đọc hồ sơ bằng câu truy vấn, không qua bản đồ định danh của phiên ---------------------------

    def _chup(self, ma: int) -> tuple:
        return tuple(self.phien.execute(select(*COT_HO_SO).where(Request.id == ma)).one())

    def _boi_canh(self, ma: int) -> BoiCanh:
        return BoiCanh(
            *self.phien.execute(
                select(
                    Request.rule_set_id,
                    Request.current_state,
                    Request.requester_id,
                    Request.department_code,
                    Request.request_type_code,
                ).where(Request.id == ma)
            ).one()
        )

    def _so_dong(self, ma: int | None = None) -> int:
        cau = select(func.count()).select_from(EventLog)
        if ma is not None:
            cau = cau.where(EventLog.case_id == ma)
        return self.phien.scalar(cau)

    def _tac_nhan(self, data, hs: BoiCanh, canh: Canh | None = None, xoay: int = 0) -> Actor:
        """Tác nhân hệ thống, hay một người với tập vai và phòng ngẫu nhiên. Đa số lần: đúng loại tác nhân
        của cạnh (người hay hệ thống), có một vai của cạnh, thuộc phòng đang giữ hồ sơ. Mã là người gửi hay
        người khác, xoay theo `xoay`."""
        if _thuong(data, "dung_loai_tac_nhan") == (canh is not None and canh.is_system):
            return Actor.system()
        vai = set(data.draw(st.frozensets(st.sampled_from(self.dm.vai)), label="vai"))
        if canh is not None and canh.vai and _thuong(data, "them_vai_cua_canh"):
            vai.add(data.draw(st.sampled_from(sorted(canh.vai)), label="vai_cua_canh"))
        phong = set(data.draw(st.frozensets(st.sampled_from(self.dm.phong)), label="phong"))
        if hs.department_code and _thuong(data, "them_phong_cua_ho_so"):
            phong.add(hs.department_code)
        ma = self._chon(
            data, [hs.requester_id, *(ma for ma in TAC_NHAN if ma != hs.requester_id)], "ma_tac_nhan", xoay
        )
        return Actor(id=ma, roles=frozenset(vai), departments=frozenset(phong))

    # --- Quy tắc -------------------------------------------------------------------------------------

    def _tao(self, data) -> None:
        # Loại yêu cầu của mọi quy trình đang bật; thỉnh thoảng không loại (lối gọi nội bộ, quy trình mặc định)
        co_loai = _thuong(data, "co_loai")
        loai = self._chon(data, sorted(self.dm.truong_loai), "loai", len(self.cua_toi)) if co_loai else None
        ho_so = create_case(
            self.phien,
            title="Hồ sơ của kiểm thử tính chất",
            requester_id=data.draw(st.sampled_from(TAC_NHAN), label="nguoi_gui"),
            request_type_code=loai,
            details=data.draw(_chi_tiet_hop_le(self.dm, loai), label="chi_tiet") if loai else None,
        )
        self.cua_toi.append(ho_so.id)

    def _chon_ho_so(self, data) -> int:
        """Đa số lần một hồ sơ chưa kết thúc; thỉnh thoảng hồ sơ đã kết thúc — chỉ cạnh mở lại đi được."""
        dang_chay = [ma for ma in self.cua_toi if ma not in self.ket_thuc]
        nguon = dang_chay if dang_chay and _thuong(data, "ho_so_dang_chay") else self.cua_toi
        self.so_buoc += 1
        return self._chon(data, nguon, "ho_so", self.so_buoc)

    @initialize(data=st.data())
    def tao_ho_so_dau(self, data) -> None:
        self._tao(data)

    @precondition(
        lambda self: len(self.cua_toi) < SO_HO_SO_TOI_DA and len(self.cua_toi) - len(self.ket_thuc) < SO_HO_SO_MO
    )
    @rule(data=st.data())
    def tao_ho_so(self, data) -> None:
        self._tao(data)

    def _con_viec(self) -> bool:
        """Còn hồ sơ chưa kết thúc — hết thì tạo hồ sơ mới trước, trừ khi đã đủ số hồ sơ của ví dụ."""
        return len(self.ket_thuc) < len(self.cua_toi) or len(self.cua_toi) >= SO_HO_SO_TOI_DA

    @precondition(_con_viec)
    @rule(data=st.data())
    def chuyen_trang_thai(self, data) -> None:
        ma = self._chon_ho_so(data)
        self.lan_thu[ma] += 1
        truoc = self._chup(ma)
        hs = self._boi_canh(ma)
        dong_truoc, dong_ho_so_truoc = self._so_dong(), self._so_dong(ma)

        canh_ra = [c for c in self.dm.canh if (c.rule_set_id, c.from_state) == (hs.rule_set_id, hs.current_state)]
        nguon = canh_ra if canh_ra and _thuong(data, "canh_tu_trang_thai_hien_tai") else self.dm.canh
        # Nửa số lần chỉ xét bước chính, để chuỗi thao tác đi sâu tới cuối luồng thay vì sớm rẽ ra hủy, rút
        buoc_chinh = [c for c in nguon if c.buoc_chinh]
        if buoc_chinh and data.draw(st.booleans(), label="chi_buoc_chinh"):
            nguon = buoc_chinh
        # Mỗi lần thử trên hồ sơ này đổi cạnh "đầu"; hết một vòng cạnh thì đổi tác nhân "đầu" — đủ mọi cặp
        canh = self._chon(data, nguon, "canh", self.lan_thu[ma])
        # Thỉnh thoảng một đích không có trong bảng nào
        den = canh.to_state if _thuong(data, "dich_cua_canh") else data.draw(CHU, label="dich_la")
        tac_nhan = self._tac_nhan(data, hs, canh, self.lan_thu[ma] // len(nguon))

        thay_doi = {}
        for truong in sorted(permitted_fields(canh.rang_buoc)):
            if _thuong(data, f"gui_{truong}"):
                gia_tri = _gia_tri_dung(self.dm, truong, hs) if _thuong(data, f"dung_{truong}") else _gia_tri_sai(
                    self.dm, truong
                )
                thay_doi[truong] = data.draw(gia_tri, label=truong)
        # Thỉnh thoảng một trường cạnh không quản, hay trường không bao giờ được đặt qua cửa này
        if not _thuong(data, "khong_truong_thua"):
            thua = data.draw(
                st.sampled_from(sorted(CHANGEABLE_FIELDS | {"current_state", "suggested_priority_code"})),
                label="truong_thua",
            )
            thay_doi.setdefault(thua, data.draw(_gia_tri_dung(self.dm, thua, hs) | SAI, label=thua))
        ghi_chu = (
            "Ghi chú của kiểm thử tính chất"
            if _thuong(data, "co_ghi_chu")
            else data.draw(st.sampled_from([None, "", "   "]), label="ghi_chu_rong")
        )

        try:
            perform_transition(
                self.phien, case_id=ma, to_state=den, actor=tac_nhan, note=ghi_chu, changes=thay_doi
            )
        except TransitionError as loi:
            self.thong_ke["tu-choi", ":".join(filter(None, (loi.code, getattr(loi, "guard_code", None))))] += 1
            # Bất biến b: bị từ chối thì không dòng nhật ký nào, hồ sơ giữ nguyên
            assert self._so_dong() == dong_truoc, "bị từ chối mà vẫn có dòng nhật ký mới"
            assert self._chup(ma) == truoc, "bị từ chối mà hồ sơ vẫn đổi"
            return

        # Bất biến a: thành công thì đúng một dòng, của đúng hồ sơ này, khớp một cạnh có thật
        sau = self._chup(ma)
        assert self._so_dong(ma) == dong_ho_so_truoc + 1, "một lần chuyển phải ghi đúng một dòng nhật ký"
        assert self._so_dong() == dong_truoc + 1, "lần chuyển ghi nhật ký cho hồ sơ khác"
        dong = self.phien.scalars(
            select(EventLog).where(EventLog.case_id == ma).order_by(EventLog.id.desc()).limit(1)
        ).one()
        self.thong_ke["thanh-cong", hs.rule_set_id] += 1
        self.thong_ke["canh", dong.activity] += 1
        if self.dm.trang_thai[hs.rule_set_id][sau[1]]:
            self.ket_thuc.add(ma)
        else:
            self.ket_thuc.discard(ma)
        assert sau[0] == hs.rule_set_id, "hồ sơ đổi bộ quy tắc"
        assert (dong.from_state, dong.to_state) == (hs.current_state, sau[1]), "nhật ký lệch trạng thái thật"
        assert sau[1] == den, "hồ sơ không tới đúng đích được yêu cầu"
        assert dong.actor == tac_nhan.id, "nhật ký ghi sai tác nhân"
        khop = [
            c
            for c in self.dm.canh
            if (c.rule_set_id, c.from_state, c.to_state, c.activity)
            == (hs.rule_set_id, dong.from_state, dong.to_state, dong.activity)
        ]
        assert khop, "nhật ký ghi một cạnh không có trong bộ quy tắc của hồ sơ"
        assert any(_di_duoc(tac_nhan, c) for c in khop), "tác nhân đi được cạnh không thuộc vai của mình"
        if self.dm.trang_thai[hs.rule_set_id][hs.current_state]:
            assert any(c.from_is_terminal for c in khop), "rời trạng thái kết thúc bằng cạnh không phải mở lại"

    @precondition(_con_viec)
    @rule(data=st.data())
    def kiem_canh_duoc_phep(self, data) -> None:
        # Bất biến d: mọi cạnh được chào đều đi ra từ trạng thái hiện tại và tác nhân có vai
        ma = self._chon_ho_so(data)
        tac_nhan = self._tac_nhan(data, self._boi_canh(ma), xoay=self.so_buoc)
        ho_so = self.phien.get(Request, ma)
        for t in allowed_transitions(self.phien, ho_so, tac_nhan):
            assert (t.rule_set_id, t.from_state) == (ho_so.rule_set_id, ho_so.current_state)
            assert t.is_system == tac_nhan.is_system and (
                tac_nhan.is_system or tac_nhan.roles & t.role_codes
            ), f"chào cạnh {t.activity_code} cho tác nhân không có vai"

    # --- Bất biến sau mọi bước ----------------------------------------------------------------------

    @invariant()
    def trang_thai_thuoc_bo_quy_tac(self) -> None:
        # Bất biến c
        for ma, rule_set_id, trang_thai in self.phien.execute(
            select(Request.id, Request.rule_set_id, Request.current_state).where(Request.id.in_(self.cua_toi))
        ):
            assert trang_thai in self.dm.trang_thai[rule_set_id], f"hồ sơ {ma} ở trạng thái lạ {trang_thai}"


def test_bat_bien_may_trang_thai(session):
    """Hypothesis không tìm được chuỗi thao tác nào phá bất biến của cửa chuyển trạng thái duy nhất."""
    dm = _doc_danh_muc(session)
    assert dm.canh and dm.truong_loai, "dữ liệu khởi tạo chưa có cạnh hay loại yêu cầu nào"
    # Mọi quy trình đang bật đều có loại yêu cầu để bài tạo được hồ sơ của nó
    bo_dang_bat = dict(session.execute(select(RuleSet.id, RuleSet.process_code).where(RuleSet.is_active)).all())
    assert set(bo_dang_bat.values()) == set(dm.loai_cua_quy_trinh)

    MayTrangThai.phien = session
    MayTrangThai.dm = dm
    MayTrangThai.thong_ke = Counter()
    run_state_machine_as_test(MayTrangThai, settings=CAU_HINH)

    # Bài không được xanh vì không bước nào đi được: mỗi bộ quy tắc đang bật phải có lần chuyển thành công,
    # và phải có lần bị từ chối. In thống kê để đọc khi chạy với `-s`.
    thong_ke = MayTrangThai.thong_ke
    print("\nThống kê kiểm thử tính chất:", dict(sorted(thong_ke.items(), key=str)))
    assert set(bo_dang_bat) <= {bo for (loai, bo) in thong_ke if loai == "thanh-cong"}, thong_ke
    assert any(loai == "tu-choi" for (loai, _) in thong_ke), thong_ke
