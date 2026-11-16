# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# PHẦN CHẠY TRONG CONTAINER của công cụ tạo hồ sơ thử (#249) — không chạy trực tiếp ở máy chủ.
# scripts/kiem_chung/tao_ho_so_thu.py chép tệp này vào container dịch vụ ứng dụng của cụm thử rồi
# `docker exec` nó, nên được dùng gói `app` và SQLAlchemy sẵn có ở đó (không thêm phụ thuộc nào).
#
# Hồ sơ được tạo và đẩy tới trạng thái đích CHỈ qua engine: `create_case` rồi `perform_transition`.
# Không INSERT vào bảng hồ sơ hay nhật ký, nên mỗi hồ sơ mang đủ nhật ký sự kiện như hồ sơ thật và
# mọi ràng buộc Poka-yoke đều chạy.
#
# Không có tên trạng thái, vai trò, phòng ban hay mã ràng buộc nào viết cứng ở đây. Đường đi tìm trên
# đồ thị các cạnh của người trong bộ quy tắc ĐANG BẬT; tác nhân mỗi bước dựng từ vai trò đi được cạnh
# đó; trường nhập lấy giá trị mặc định từ dữ liệu theo trường mà ràng buộc trên cạnh quản.
#
# Vào: một đối tượng JSON trên đầu vào chuẩn. Ra: một dòng `KET_QUA_JSON {...}` trên đầu ra chuẩn.
from __future__ import annotations

import json
import sys
from collections import deque

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models.case import Request
from app.models.workflow_config import (
    Department,
    Priority,
    RequestType,
    RequestTypeRouting,
    Role,
    State,
    Transition,
)
from app.rules.guards import permitted_fields
from app.workflow.context import Actor
from app.workflow.engine import create_case, get_active_rule_set, ma_quy_trinh_ung_dung, perform_transition

GHI_CHU_THU = "Ghi chú do công cụ kiểm chứng tạo khi dựng hồ sơ thử."
# Giới hạn tìm đường: đồ thị vài chục cạnh nên dư sức, mà không để một bộ quy tắc nhiều vòng treo công cụ
DO_DAI_TOI_DA = 14
SO_DUONG_THU_TOI_DA = 40
SO_BUOC_DUYET_TOI_DA = 60000


class BuocLoi(Exception):
    def __init__(self, chi_so: int, canh: Transition, ly_do: str) -> None:
        super().__init__(ly_do)
        self.chi_so, self.canh, self.ly_do = chi_so, canh, ly_do


def thong_bao_loi(loi: Exception) -> str:
    noi_dung = getattr(loi, "message", None) or str(loi) or type(loi).__name__
    ma = getattr(loi, "code", None)
    return f"{noi_dung} [{ma}]" if ma else noi_dung


def main() -> int:
    ts = json.loads(sys.stdin.read())
    tien_to: str = ts["tien_to"]
    with SessionLocal() as s:
        bo = get_active_rule_set(s, ma_quy_trinh_ung_dung(s))
        trang_thai = {
            st.code: st
            for st in s.scalars(
                select(State).where(State.rule_set_id == bo.id).order_by(State.display_order, State.code)
            )
        }
        dau = [st.code for st in trang_thai.values() if st.is_initial]
        if len(dau) != 1:
            return ket_thuc({"loi": f"Bộ quy tắc phải có đúng một trạng thái bắt đầu, đang có {len(dau)}."})
        ma_dau = dau[0]

        # Chặn chạy trên cụm có hồ sơ thật (học theo scripts/nap_du_lieu_trinh_dien.py)
        that = s.scalar(select(func.count()).select_from(Request).where(~Request.title.startswith(tien_to)))
        if that and not ts.get("cho_tron"):
            return ket_thuc({"chan": int(that)})

        canh = [
            c for c in s.scalars(
                select(Transition).where(Transition.rule_set_id == bo.id).order_by(Transition.display_order, Transition.id)
            )
            if not c.is_system and c.from_state != c.to_state
        ]
        canh_ra: dict[str, list[Transition]] = {}
        for c in canh:
            canh_ra.setdefault(c.from_state, []).append(c)
        canh_he_thong_toi: dict[str, list[str]] = {}
        for c in s.scalars(select(Transition).where(Transition.rule_set_id == bo.id, Transition.is_system)):
            canh_he_thong_toi.setdefault(c.to_state, []).append(c.activity_label)

        # --- Giá trị mặc định đọc từ dữ liệu ---
        uu_tien = s.scalar(select(Priority.code).where(Priority.is_default)) or s.scalar(
            select(Priority.code).order_by(Priority.display_order).limit(1)
        )
        loai = ts.get("loai") or s.scalar(
            select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order).limit(1)
        )
        loai_ban_ghi = s.get(RequestType, loai) if loai else None
        if loai_ban_ghi is None or not loai_ban_ghi.is_active:
            return ket_thuc({"loi": f"Loại yêu cầu {loai!r} không có trong danh mục đang dùng."})
        phong_mac_dinh = s.scalar(
            select(RequestTypeRouting.department_code)
            .where(RequestTypeRouting.request_type_code == loai, RequestTypeRouting.is_default)
            .limit(1)
        ) or s.scalar(select(Department.code).where(Department.is_active).order_by(Department.display_order).limit(1))
        nhan_vai_tro = {r.code: r.label for r in s.scalars(select(Role))}

        def thay_doi_cho(c: Transition, ho_so: Request) -> dict:
            """Trường nhập mà ràng buộc trên cạnh quản và ta biết điền gì. Trường khác bỏ trống:
            nếu cạnh đòi thì engine sẽ từ chối, và lời từ chối được báo nguyên văn."""
            duoc_phep = permitted_fields(c.guard_codes)
            ra: dict = {}
            if "priority_code" in duoc_phep and uu_tien:
                ra["priority_code"] = uu_tien
            if "department_code" in duoc_phep:
                phong = ho_so.department_code or phong_mac_dinh
                if phong:
                    ra["department_code"] = phong
            return ra

        def di_mot_buoc(chi_so: int, c: Transition, ho_so: Request) -> None:
            vai_tro = sorted(c.role_codes)
            if not vai_tro:
                raise BuocLoi(chi_so, c, "Cạnh này không có vai trò nào đi được.")
            loi_gap: list[str] = []
            for vai in vai_tro:
                # Hai ứng viên: người khác với người gửi (các cạnh của điều phối cấm tự điều phối hồ sơ
                # của mình), rồi chính người gửi (cạnh dành cho chủ hồ sơ)
                for ma_nguoi, ten in ((f"nguoi-thu-{vai}", f"Người thử ({nhan_vai_tro.get(vai, vai)})"),
                                      (ho_so.requester_id, ho_so.requester_label)):
                    tac_nhan = Actor(
                        id=ma_nguoi, name=ten, roles=frozenset({vai}),
                        departments=frozenset({ho_so.department_code} if ho_so.department_code else ()),
                    )
                    try:
                        with s.begin_nested():
                            perform_transition(
                                s, case_id=ho_so.id, to_state=c.to_state, actor=tac_nhan,
                                note=GHI_CHU_THU if c.requires_note else None,
                                changes=thay_doi_cho(c, ho_so),
                            )
                        s.refresh(ho_so)
                        return
                    except Exception as loi:  # noqa: BLE001 - mọi lỗi của engine đều là lý do cần báo
                        thong = thong_bao_loi(loi)
                        if thong not in loi_gap:
                            loi_gap.append(thong)
            raise BuocLoi(chi_so, c, " | ".join(loi_gap))

        def cac_duong(dich: str) -> list[list[Transition]]:
            hang = deque([(ma_dau, [])])
            ra: list[list[Transition]] = []
            dem = 0
            while hang and len(ra) < SO_DUONG_THU_TOI_DA and dem < SO_BUOC_DUYET_TOI_DA:
                dem += 1
                tt, duong = hang.popleft()
                if duong and tt == dich:
                    ra.append(duong)
                    continue
                if len(duong) >= DO_DAI_TOI_DA:
                    continue
                da_qua = {ma_dau, *(c.to_state for c in duong)}
                for c in canh_ra.get(tt, []):
                    if c.to_state not in da_qua:
                        hang.append((c.to_state, [*duong, c]))
            return ra

        def tao_toi(dich: str) -> dict:
            st = trang_thai[dich]
            ket_qua = {"ma": dich, "nhan": st.label, "ho_so": None, "buoc": [], "ly_do": None}
            if dich == ma_dau:
                duong_ung_vien: list[list[Transition]] = [[]]
            else:
                duong_ung_vien = cac_duong(dich)
            if not duong_ung_vien:
                ly_do = "Không có cạnh nào của người dẫn tới trạng thái này từ trạng thái bắt đầu."
                if dich in canh_he_thong_toi:
                    ly_do += (" Chỉ bước hệ thống dẫn tới: "
                              + ", ".join(f"“{n}”" for n in canh_he_thong_toi[dich]) + ".")
                ket_qua["ly_do"] = ly_do
                return ket_qua

            loi_dau = None
            for duong in duong_ung_vien:
                try:
                    with s.begin_nested():
                        ho_so = create_case(
                            s, title=f"{tien_to} {st.label} — hồ sơ do công cụ kiểm chứng tạo",
                            description="Hồ sơ thử (#249). Xóa cùng cụm thử.",
                            requester_id=ts["nguoi_gui"], requester_label=ts["nhan_nguoi_gui"],
                            request_type_code=loai,
                        )
                        for i, c in enumerate(duong):
                            di_mot_buoc(i, c, ho_so)
                        ket_qua["ho_so"] = ho_so.id
                    ket_qua["buoc"] = [c.activity_label for c in duong]
                    return ket_qua
                except BuocLoi as loi:
                    if loi_dau is None:
                        loi_dau = (
                            f"Bước {loi.chi_so + 1}/{len(duong)} “{loi.canh.activity_label}” "
                            f"({loi.canh.from_state} → {loi.canh.to_state}) bị engine từ chối: {loi.ly_do}"
                        )
                except Exception as loi:  # noqa: BLE001
                    if loi_dau is None:
                        loi_dau = f"Lỗi khi tạo hồ sơ: {thong_bao_loi(loi)}"
            ket_qua["ly_do"] = f"{loi_dau} (đã thử {len(duong_ung_vien)} đường đi)"
            return ket_qua

        muc_tieu = ts.get("trang_thai") or list(trang_thai)
        la = [m for m in muc_tieu if m not in trang_thai]
        if la:
            return ket_thuc({"loi": f"Bộ quy tắc đang bật không có trạng thái: {', '.join(la)}. "
                                    f"Có: {', '.join(trang_thai)}."})
        ket_qua_tung_trang_thai = [tao_toi(m) for m in muc_tieu]
        s.commit()
        return ket_thuc({"bo_quy_tac": f"{bo.version} — {bo.label}", "loai": loai,
                         "ket_qua": ket_qua_tung_trang_thai})


def ket_thuc(noi_dung: dict) -> int:
    print("KET_QUA_JSON " + json.dumps(noi_dung, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
