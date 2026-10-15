# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Sinh nhật ký sự kiện ảo theo ĐÚNG bộ quy tắc đang chạy trong cụm (#124).
#
# Dùng cho khảo sát khai phá quy trình (#48), và về sau cho dữ liệu trình diễn và bảng
# điều khiển Superset. Thay cho bộ sinh dựng thử ở khảo sát #21, vốn viết theo mô hình
# trước ngày 10/09 và xuất ra tệp SQL xóa bảng nhật ký.
#
# Ba nguyên tắc:
#
#   1. Bộ quy tắc ĐỌC TỪ CƠ SỞ DỮ LIỆU, không chép vào tệp này. Trạng thái, cạnh, ma
#      trận phân quyền, ràng buộc, loại yêu cầu, phòng ban — tra từ bộ quy tắc đang kích
#      hoạt. Doanh nghiệp đổi bộ quy tắc thì bộ sinh tự đi theo.
#   2. CHỈ ĐỌC cơ sở dữ liệu — đúng một câu SELECT qua psql trong container — và CHỈ GHI
#      tệp CSV ra một thư mục NGOÀI kho mã. Không bao giờ ghi vào cơ sở dữ liệu.
#   3. Đi đúng luật của engine: chỉ đi cạnh có trong bảng, người đi mang đúng vai trò,
#      bổ sung thông tin xong quay về đúng chỗ đã hỏi (#79), quá hạn thì leo thang theo
#      đồng hồ SLA có ân hạn (#94). Nhật ký sinh ra phải là thứ hệ thống thật CÓ THỂ ghi.
#
# Thứ duy nhất không nằm trong cơ sở dữ liệu là KỊCH BẢN — người dùng hay rẽ nhánh nào,
# hồ sơ nằm ở mỗi trạng thái bao lâu. Đó là giả định về hành vi người dùng, không phải
# quy tắc nghiệp vụ, nên nằm riêng ở KICH_BAN_MAC_DINH và thay được bằng --kich-ban.
#
# Cách dùng, ở gốc kho mã, khi cụm đang chạy:
#
#     python scripts/sinh_nhat_ky_ao.py --ra ..\thu-48\du-lieu
#
# Chỉ cần Python 3.10 trở lên và lệnh `docker` — không cài thêm thư viện nào.

from __future__ import annotations

import argparse
import csv
import json
import random
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Mã ràng buộc là hợp đồng giữa dữ liệu và mã nguồn — đúng các mã mà
# backend/app/rules/guards.py cài đặt. Bộ sinh cần hiểu chúng để đi đúng luật như engine.
RB_NGUOI_TAO = "requester-owns-case"
RB_CUNG_PHONG = "actor-in-case-department"
RB_VE_CHO_CU = "return-to-previous-state"
RB_UU_TIEN = "set-priority"
RB_LOAI = "set-request-type"
RB_PHONG = "select-department"
RB_GIAO_NGUOI = "assign-handler"
RB_SUA_NOI_DUNG = "edit-content"
RB_TU_NHAN = "assign-self"
# Gia hạn xử lý (#101): bộ sinh chưa mô phỏng — không đi cạnh mang ràng buộc này, nên mọi
# hồ sơ ảo giữ hạn gốc. Hệ số theo mức ưu tiên cũng chưa mô phỏng: hạn ảo là hạn chuẩn.
RB_GIA_HAN = "extend-deadline"

# Tác nhân hệ thống khi leo thang — cùng giá trị với TAC_NHAN_SLA trong
# backend/app/workflow/escalation.py, và nhãn "Hệ thống" giao diện dùng để nhận ra nó.
TAC_NHAN_HE_THONG = "sla-watcher"
NHAN_HE_THONG = "Hệ thống"
# Tác nhân hệ thống khi hồ sơ nằm im quá hạn chờ (#142) — cùng giá trị với TAC_NHAN_HAN_CHO
TAC_NHAN_HAN_CHO = "wait-watcher"

# Bộ quét leo thang chạy mỗi phút, nên hồ sơ leo thang trễ hơn lúc quá hạn tối đa một phút.
TRE_BO_QUET_GIAY = 60

# Chặn vòng lặp vô tận khi kịch bản đặt trọng số quá cao cho các nhánh quay lui.
SO_BUOC_TOI_DA = 60

KICH_BAN_MAC_DINH: dict = {
    # Trọng số tương đối khi một người đứng trước nhiều cạnh, tra theo mã hoạt động.
    # Mã không có ở đây nhận "trong_so_mac_dinh". Cạnh hệ thống không có trọng số: nó đi
    # khi đồng hồ SLA nói phải đi.
    "trong_so": {
        "classify": 20,
        "route-to-department": 20,
        "accept": 16,
        "complete": 18,
        "provide-info": 20,
        "confirm": 18,
        "reroute": 20,
        "reassign": 20,
        # Hồ sơ chưa giao ai thì người xử lý hay tự nhận trước khi làm (#127)
        "claim": 8,
        "request-info": 2,
        "edit-content": 0.8,
        "reopen": 1.5,
        "cancel": 0.35,
        "reject": 0.5,
        "close-unrouted": 0.3,
        # Điều phối viên hiếm khi rút hồ sơ khỏi phòng ban trước hạn chờ (#142)
        "withdraw": 0.3,
    },
    "trong_so_mac_dinh": 1.0,
    # Hồ sơ bị chuyển nhầm phòng thì phòng đó rất hay trả lại — nhân trọng số các hoạt
    # động này khi phòng đang giữ khác phòng mặc định của loại yêu cầu. Đây là nguồn của
    # vòng lặp định tuyến sai mà khai phá quy trình cần tìm ra.
    "khi_sai_phong": {"reject": 40},
    "ty_le_chon_dung_phong": 0.82,
    "ty_le_chon_dung_phong_lan_sau": 0.95,
    "ty_le_nguoi_gui_chon_dung_loai": 0.88,
    "ty_le_giao_nguoi_xu_ly": 0.75,
    "ty_le_uu_tien_mac_dinh": 0.55,
    # Tỷ lệ loại yêu cầu. Mã không có trong bộ quy tắc bị bỏ qua; không mã nào khớp thì
    # chia đều.
    "ty_le_loai": {
        "device-incident": 0.38,
        "software-access": 0.27,
        "hr-certificate": 0.17,
        "supply-purchase": 0.18,
    },
    # Giờ nằm trung bình ở từng trạng thái, phân phối mũ. Trạng thái chạy đồng hồ mà không
    # có ở đây thì tính theo ngưỡng SLA — xem "he_so_xu_ly_theo_sla".
    "gio_cho": {
        "submitted": 3,
        "classified": 1.5,
        "awaiting-acceptance": 5,
        "awaiting-info": 18,
        "rejected-by-department": 2,
        "completed": 14,
        "escalated": 2.5,
    },
    "gio_cho_mac_dinh": 4,
    # Ở trạng thái chạy đồng hồ, thời gian xử lý trung bình bằng ngưỡng SLA nhân hệ số
    # này. Với phân phối mũ, 0,55 cho khoảng 16 % lượt xử lý đầu vượt ngưỡng.
    "he_so_xu_ly_theo_sla": 0.55,
    # Hồ sơ đã quá hạn — vừa được phân công lại, mở lại, hay bổ sung xong — thì người nhận
    # làm gấp: thời gian xử lý trung bình bằng ÂN HẠN nhân hệ số này. Thiếu nó, người nhận
    # vẫn làm chậm như với hạn gốc, và hồ sơ bị leo thang lặp tới mười mấy lần.
    "he_so_xu_ly_khi_qua_han": 0.5,
    "so_nguoi_moi_vai_tro": 3,
    "so_nguoi_gui": 40,
}

CAU_TRUY_VAN = """
WITH bo AS (SELECT id, version FROM rule_sets WHERE is_active)
SELECT json_build_object(
  'phien_ban', (SELECT version FROM bo),
  'trang_thai', (
    SELECT json_agg(json_build_object(
             'ma', s.code, 'nhan', s.label, 'bat_dau', s.is_initial,
             'ket_thuc', s.is_terminal, 'chay_dong_ho', s.sla_running)
           ORDER BY s.display_order)
    FROM states s WHERE s.rule_set_id = (SELECT id FROM bo)),
  'canh', (
    SELECT json_agg(json_build_object(
             'tu', t.from_state, 'den', t.to_state, 'hoat_dong', t.activity_code,
             'nhan_hoat_dong', t.activity_label,
             'he_thong', t.is_system, 'can_ghi_chu', t.requires_note,
             'tu_di_sau_gio', t.auto_after_hours,
             'vai_tro', COALESCE((SELECT json_agg(r.role_code ORDER BY r.role_code)
                                  FROM transition_roles r WHERE r.transition_id = t.id),
                                 '[]'::json),
             'rang_buoc', COALESCE((SELECT json_agg(g.guard_code ORDER BY g.guard_code)
                                    FROM transition_guards g WHERE g.transition_id = t.id),
                                   '[]'::json))
           ORDER BY t.display_order)
    FROM transitions t WHERE t.rule_set_id = (SELECT id FROM bo)),
  'loai_yeu_cau', (
    SELECT json_agg(json_build_object(
             'ma', code, 'sla_gio', sla_hours, 'an_han_gio', sla_grace_hours)
           ORDER BY display_order)
    FROM request_types WHERE is_active),
  'phong_ban', (SELECT json_agg(code ORDER BY display_order) FROM departments WHERE is_active),
  'phong_mac_dinh', (SELECT json_object_agg(request_type_code, department_code)
                     FROM request_type_routing WHERE is_default),
  'muc_uu_tien', (SELECT json_agg(json_build_object('ma', code, 'mac_dinh', is_default)
                                  ORDER BY display_order)
                  FROM priorities)
);
"""

COT_NHAT_KY = [
    "id", "case_id", "activity", "timestamp", "actor", "actor_label",
    "from_state", "to_state", "note", "changes",
]
COT_HO_SO = [
    "id", "current_state", "requester_id", "request_type_code", "department_code",
    "priority_code", "assignee_id", "created_at", "sla_running_seconds",
    "sla_paused_seconds", "sla_segment_since",
]


@dataclass(frozen=True)
class Canh:
    tu: str
    den: str
    hoat_dong: str
    he_thong: bool
    can_ghi_chu: bool
    vai_tro: tuple[str, ...]
    rang_buoc: tuple[str, ...]
    # Cạnh hệ thống tự đi sau chừng này giờ nằm ở trạng thái nguồn (#142). None: cạnh leo
    # thang do đồng hồ SLA quyết, hoặc cạnh của người.
    tu_di_sau_gio: int | None = None


@dataclass
class HoSo:
    ma: int
    nguoi_gui: str
    loai_that: str
    loai: str | None
    tao_luc: datetime
    trang_thai: str
    mo_ta: str = ""
    phong: str | None = None
    uu_tien: str | None = None
    nguoi_xu_ly: str | None = None
    chay_giay: float = 0.0
    dung_giay: float = 0.0
    doan_mo_tu: datetime | None = None
    so_lan_chon_phong: int = 0
    cham_tran_buoc: bool = False


def doc_quy_tac_tu_cum(container: str, nguoi_dung: str, csdl: str) -> dict:
    """Đọc bộ quy tắc đang kích hoạt bằng một câu SELECT chạy trong container."""
    lenh = [
        "docker", "exec", container, "psql", "-U", nguoi_dung, "-d", csdl,
        "-At", "-v", "ON_ERROR_STOP=1", "-c", CAU_TRUY_VAN,
    ]
    try:
        kq = subprocess.run(lenh, capture_output=True, check=False)
    except FileNotFoundError:
        sys.exit("Không tìm thấy lệnh docker. Bật Docker Desktop rồi chạy lại.")
    if kq.returncode != 0:
        sys.exit(
            f"Không đọc được bộ quy tắc từ container {container}. Cụm đã chạy chưa?\n"
            + kq.stderr.decode("utf-8", "replace")
        )
    return json.loads(kq.stdout.decode("utf-8"))


class BoSinh:
    def __init__(self, quy_tac: dict, kich_ban: dict, hat_giong: int) -> None:
        self.kb = kich_ban
        self.rng = random.Random(hat_giong)

        self.trang_thai = {s["ma"]: s for s in quy_tac["trang_thai"]}
        dau = [s["ma"] for s in quy_tac["trang_thai"] if s["bat_dau"]]
        if len(dau) != 1:
            sys.exit("Bộ quy tắc phải có đúng một trạng thái bắt đầu.")
        self.trang_thai_dau = dau[0]

        self.canh = [
            Canh(c["tu"], c["den"], c["hoat_dong"], c["he_thong"], c["can_ghi_chu"],
                 tuple(c["vai_tro"]), tuple(c["rang_buoc"]), c.get("tu_di_sau_gio"))
            for c in quy_tac["canh"]
        ]
        self.canh_ra: dict[str, list[Canh]] = defaultdict(list)
        for c in self.canh:
            self.canh_ra[c.tu].append(c)

        self.loai = {l["ma"]: l for l in quy_tac["loai_yeu_cau"] or []}
        if not self.loai:
            sys.exit("Bộ quy tắc chưa có loại yêu cầu nào đang dùng.")
        self.phong_ban = list(quy_tac["phong_ban"] or [])
        self.phong_mac_dinh = dict(quy_tac["phong_mac_dinh"] or {})
        self.muc_uu_tien = [m["ma"] for m in quy_tac["muc_uu_tien"] or []]
        self.uu_tien_mac_dinh = next(
            (m["ma"] for m in quy_tac["muc_uu_tien"] or [] if m["mac_dinh"]), None
        )

        # Vai trò của người gửi: vai trò đi được cạnh mang ràng buộc "người tạo hồ sơ".
        self.vai_tro_nguoi_gui = next(
            (v for c in self.canh if RB_NGUOI_TAO in c.rang_buoc for v in c.vai_tro),
            "requester",
        )
        # Người nhận việc: vai trò đi được cạnh người ra khỏi trạng thái mà hồ sơ tới sau
        # khi được giao — cùng cách suy với vai_tro_nhan_viec ở app/workflow/assignment.py.
        self.vai_tro_nhan_viec: dict[str, list[str]] = {}
        for c in self.canh:
            if RB_GIAO_NGUOI in c.rang_buoc:
                self.vai_tro_nhan_viec[c.den] = sorted({
                    v for ra in self.canh_ra[c.den] if not ra.he_thong for v in ra.vai_tro
                })

    # --- Chọn ngẫu nhiên theo kịch bản ---------------------------------------

    def _chon_loai(self) -> str:
        ty_le = {m: t for m, t in self.kb["ty_le_loai"].items() if m in self.loai}
        if not ty_le:
            return self.rng.choice(list(self.loai))
        return self.rng.choices(list(ty_le), weights=list(ty_le.values()))[0]

    def _gio_cho(self, hs: HoSo) -> float:
        """Số giây hồ sơ nằm ở trạng thái hiện tại trước khi có người hành động."""
        tt = self.trang_thai[hs.trang_thai]
        if hs.trang_thai in self.kb["gio_cho"]:
            trung_binh = self.kb["gio_cho"][hs.trang_thai]
        elif tt["chay_dong_ho"] and hs.loai:
            loai = self.loai[hs.loai]
            if hs.chay_giay > loai["sla_gio"] * 3600 and loai["an_han_gio"] > 0:
                trung_binh = loai["an_han_gio"] * self.kb["he_so_xu_ly_khi_qua_han"]
            else:
                trung_binh = loai["sla_gio"] * self.kb["he_so_xu_ly_theo_sla"]
        else:
            trung_binh = self.kb["gio_cho_mac_dinh"]
        return max(60.0, self.rng.expovariate(1 / trung_binh) * 3600)

    def _di_duoc(self, c: Canh, truoc: str | None, hs: HoSo) -> bool:
        """Ràng buộc không cần nhập liệu — cùng phần engine chạy lúc chào nút (#79).

        Hai ràng buộc về người thao tác luôn thỏa vì người được chọn theo đúng chúng ở
        `_tac_nhan`. Còn lại luật quay về chỗ cũ, và luật chỉ tự nhận hồ sơ chưa giao ai
        (#127).
        """
        if RB_VE_CHO_CU in c.rang_buoc and c.den != truoc:
            return False
        if RB_GIA_HAN in c.rang_buoc:
            return False
        return not (RB_TU_NHAN in c.rang_buoc and hs.nguoi_xu_ly)

    def _chon_canh(self, ung_vien: list[Canh], hs: HoSo) -> Canh:
        phong_dung = self.phong_mac_dinh.get(hs.loai_that)
        sai_phong = hs.phong is not None and hs.phong != phong_dung
        trong_so = []
        for c in ung_vien:
            w = self.kb["trong_so"].get(c.hoat_dong, self.kb["trong_so_mac_dinh"])
            if sai_phong:
                w *= self.kb["khi_sai_phong"].get(c.hoat_dong, 1)
            trong_so.append(w)
        if sum(trong_so) <= 0:
            return self.rng.choice(ung_vien)
        return self.rng.choices(ung_vien, weights=trong_so)[0]

    def _nguoi(self, vai_tro: str, phong: str | None = None) -> str:
        so = self.rng.randint(1, self.kb["so_nguoi_moi_vai_tro"])
        return f"{vai_tro}-{phong}-{so}" if phong else f"{vai_tro}-{so}"

    def _tac_nhan(self, hs: HoSo, c: Canh) -> tuple[str, str]:
        if c.he_thong:
            return (TAC_NHAN_HAN_CHO if c.tu_di_sau_gio else TAC_NHAN_HE_THONG), NHAN_HE_THONG
        if RB_NGUOI_TAO in c.rang_buoc:
            return hs.nguoi_gui, hs.nguoi_gui
        vai = self.rng.choice(c.vai_tro) if c.vai_tro else "khong-ro-vai-tro"
        if RB_CUNG_PHONG in c.rang_buoc and hs.phong:
            # Hồ sơ đã giao cho một người mang đúng vai trò này thì chính người đó làm
            if hs.nguoi_xu_ly and hs.nguoi_xu_ly.startswith(f"{vai}-{hs.phong}-"):
                return hs.nguoi_xu_ly, hs.nguoi_xu_ly
            ma = self._nguoi(vai, hs.phong)
        else:
            ma = self._nguoi(vai)
        return ma, ma

    def _dat_truong(self, hs: HoSo, c: Canh, tac_nhan: str) -> dict:
        """Trường mà cạnh này đặt, ghi theo khuôn cột `changes` của #100."""
        thay_doi: dict = {}

        def ghi(truong: str, cu: str | None, moi: str | None, co_nhan: bool = False) -> None:
            if cu == moi:
                return
            muc = {"from": cu, "to": moi}
            if co_nhan:
                muc.update({"from_label": cu, "to_label": moi})
            thay_doi[truong] = muc

        # Người gửi chọn nhầm loại thì người phân loại sửa lại ở cạnh đầu tiên cho sửa loại
        if RB_LOAI in c.rang_buoc and hs.loai != hs.loai_that:
            ghi("request_type_code", hs.loai, hs.loai_that)
            hs.loai = hs.loai_that

        # Người gửi sửa nội dung trước khi tới phòng ban (#127): bổ sung mô tả, và tự sửa
        # loại nếu lúc gửi chọn nhầm. Engine đòi phải thật sự đổi một thứ gì đó, nên mô
        # tả luôn đổi.
        if RB_SUA_NOI_DUNG in c.rang_buoc:
            mo_ta_moi = f"{hs.mo_ta} Bổ sung thêm chi tiết."
            ghi("description", hs.mo_ta, mo_ta_moi)
            hs.mo_ta = mo_ta_moi
            if hs.loai != hs.loai_that:
                ghi("request_type_code", hs.loai, hs.loai_that)
                hs.loai = hs.loai_that

        # Tự nhận việc (#127): tác động của ràng buộc, người xử lý là chính người thao tác
        if RB_TU_NHAN in c.rang_buoc:
            ghi("assignee_id", hs.nguoi_xu_ly, tac_nhan, co_nhan=True)
            hs.nguoi_xu_ly = tac_nhan

        if RB_UU_TIEN in c.rang_buoc and self.muc_uu_tien:
            if self.uu_tien_mac_dinh and self.rng.random() < self.kb["ty_le_uu_tien_mac_dinh"]:
                moi = self.uu_tien_mac_dinh
            else:
                moi = self.rng.choice(self.muc_uu_tien)
            ghi("priority_code", hs.uu_tien, moi)
            hs.uu_tien = moi

        if RB_PHONG in c.rang_buoc and self.phong_ban:
            dung = self.phong_mac_dinh.get(hs.loai_that)
            ty_le = (
                self.kb["ty_le_chon_dung_phong"] if hs.so_lan_chon_phong == 0
                else self.kb["ty_le_chon_dung_phong_lan_sau"]
            )
            if dung and self.rng.random() < ty_le:
                moi = dung
            else:
                phong_khac = [p for p in self.phong_ban if p != dung] or self.phong_ban
                moi = self.rng.choice(phong_khac)
            hs.so_lan_chon_phong += 1
            ghi("department_code", hs.phong, moi)
            hs.phong = moi

        if (
            RB_GIAO_NGUOI in c.rang_buoc
            and hs.phong
            and self.vai_tro_nhan_viec.get(c.den)
            and self.rng.random() < self.kb["ty_le_giao_nguoi_xu_ly"]
        ):
            moi = self._nguoi(self.rng.choice(self.vai_tro_nhan_viec[c.den]), hs.phong)
            ghi("assignee_id", hs.nguoi_xu_ly, moi, co_nhan=True)
            hs.nguoi_xu_ly = moi

        return thay_doi

    def _cap_nhat_dong_ho(self, hs: HoSo, c: Canh, luc: datetime) -> None:
        """Chốt đoạn đồng hồ đang mở rồi mở đoạn mới — như cap_nhat_dong_ho ở
        backend/app/rules/sla.py."""
        tu, den = self.trang_thai[c.tu], self.trang_thai[c.den]
        if hs.doan_mo_tu is not None:
            giay = (luc - hs.doan_mo_tu).total_seconds()
            if tu["chay_dong_ho"]:
                hs.chay_giay += giay
            else:
                hs.dung_giay += giay
        da_khoi_dong = hs.doan_mo_tu is not None or den["chay_dong_ho"]
        hs.doan_mo_tu = None if den["ket_thuc"] or not da_khoi_dong else luc

    def _giay_toi_leo_thang(self, hs: HoSo) -> float | None:
        """Giây kể từ lúc vào trạng thái hiện tại cho tới khi bộ quét leo thang.

        Cùng năm điều kiện của ho_so_qua_han: trạng thái chạy đồng hồ, đã có loại, tổng
        giờ chạy vượt ngưỡng, có cạnh hệ thống để đi, và đã hết ân hạn tính từ lúc vào
        trạng thái hiện tại.
        """
        tt = self.trang_thai[hs.trang_thai]
        if not tt["chay_dong_ho"] or not hs.loai:
            return None
        leo = self.canh_ra[hs.trang_thai]
        if not any(c.he_thong and c.tu_di_sau_gio is None for c in leo):
            return None
        nguong = self.loai[hs.loai]["sla_gio"] * 3600
        an_han = self.loai[hs.loai]["an_han_gio"] * 3600
        return max(nguong - hs.chay_giay, an_han) + TRE_BO_QUET_GIAY

    # --- Một hồ sơ ------------------------------------------------------------

    def sinh_ho_so(
        self, ma: int, tao_luc: datetime, chot_luc: datetime
    ) -> tuple[HoSo, list[dict]]:
        loai_that = self._chon_loai()
        khac = [m for m in self.loai if m != loai_that]
        chon_dung = not khac or self.rng.random() < self.kb["ty_le_nguoi_gui_chon_dung_loai"]
        loai = loai_that if chon_dung else self.rng.choice(khac)
        so = self.rng.randint(1, self.kb["so_nguoi_gui"])
        hs = HoSo(ma, f"{self.vai_tro_nguoi_gui}-{so:03d}", loai_that, loai, tao_luc,
                  self.trang_thai_dau, mo_ta=f"Mô tả ảo của hồ sơ số {ma}.")

        su_kien: list[dict] = []
        luc = tao_luc
        # Trạng thái ngay trước trạng thái hiện tại — thứ engine đọc từ nhật ký cho luật
        # quay về chỗ cũ
        truoc: str | None = None

        for _ in range(SO_BUOC_TOI_DA):
            if self.trang_thai[hs.trang_thai]["ket_thuc"]:
                break
            ung_vien = [
                c for c in self.canh_ra[hs.trang_thai]
                if not c.he_thong and self._di_duoc(c, truoc, hs)
            ]
            canh = self._chon_canh(ung_vien, hs) if ung_vien else None
            cho = self._gio_cho(hs)

            den_leo = self._giay_toi_leo_thang(hs)
            if den_leo is not None and (canh is None or den_leo < cho):
                canh = next(
                    c for c in self.canh_ra[hs.trang_thai]
                    if c.he_thong and c.tu_di_sau_gio is None
                )
                cho = den_leo

            # Không ai thao tác trước hạn chờ thì hệ thống tự đi (#142, #144). Hạn đếm bằng giờ
            # lịch ở đây — bộ sinh chưa mô phỏng lịch làm việc của #199.
            tu_di = next(
                (c for c in self.canh_ra[hs.trang_thai] if c.he_thong and c.tu_di_sau_gio), None
            )
            if tu_di is not None:
                den_tu_di = tu_di.tu_di_sau_gio * 3600 + TRE_BO_QUET_GIAY
                if canh is None or den_tu_di < cho:
                    canh, cho = tu_di, den_tu_di
            if canh is None:
                break

            luc_moi = luc + timedelta(seconds=cho)
            if luc_moi > chot_luc:
                # Hồ sơ còn dở lúc chốt dữ liệu — đúng như trong một hệ thống đang chạy
                break

            self._cap_nhat_dong_ho(hs, canh, luc_moi)
            # Người thao tác chọn trước, vì tác động tự nhận việc đặt người xử lý bằng họ
            tac_nhan, nhan = self._tac_nhan(hs, canh)
            thay_doi = self._dat_truong(hs, canh, tac_nhan)
            su_kien.append({
                "case_id": ma,
                "activity": canh.hoat_dong,
                "timestamp": luc_moi,
                "actor": tac_nhan,
                "actor_label": nhan,
                "from_state": canh.tu,
                "to_state": canh.den,
                "note": f"(ghi chú ảo cho {canh.hoat_dong})" if canh.can_ghi_chu else "",
                "changes": json.dumps(thay_doi, ensure_ascii=False) if thay_doi else "",
            })
            # Dòng tự trỏ không đưa hồ sơ vào trạng thái nào, nên không đổi "chỗ cũ" —
            # đúng như engine bỏ qua nó (#127)
            if canh.tu != canh.den:
                truoc = hs.trang_thai
            hs.trang_thai, luc = canh.den, luc_moi
        else:
            hs.cham_tran_buoc = True

        return hs, su_kien

    def sinh(
        self, so_ho_so: int, bat_dau: datetime, so_ngay: int
    ) -> tuple[list[HoSo], list[dict]]:
        chot_luc = bat_dau + timedelta(days=so_ngay)
        luc_tao = sorted(
            bat_dau + timedelta(
                days=self.rng.randint(0, so_ngay - 1),
                hours=self.rng.randint(7, 17),
                minutes=self.rng.randint(0, 59),
            )
            for _ in range(so_ho_so)
        )
        ho_so, su_kien = [], []
        for ma, tao_luc in enumerate(luc_tao, start=1):
            hs, ds = self.sinh_ho_so(ma, tao_luc, chot_luc)
            ho_so.append(hs)
            su_kien.extend(ds)
        return ho_so, su_kien


# --- Tự kiểm ------------------------------------------------------------------


def tu_kiem(bo: BoSinh, ho_so: list[HoSo], su_kien: list[dict]) -> list[str]:
    """Mọi sự kiện phải là thứ engine thật cho phép ghi. Trả về danh sách lỗi."""
    # Một cặp trạng thái có thể có cả cạnh người lẫn cạnh hệ thống (#142): nhận diện cạnh
    # theo cả loại tác nhân, như engine
    canh = {(c.tu, c.den, c.he_thong): c for c in bo.canh}
    he_thong = {TAC_NHAN_HE_THONG, TAC_NHAN_HAN_CHO}
    theo_ho_so: dict[int, list[dict]] = defaultdict(list)
    for e in su_kien:
        theo_ho_so[e["case_id"]].append(e)

    loi: list[str] = []
    for hs in ho_so:
        hien_tai, truoc, luc = bo.trang_thai_dau, None, hs.tao_luc
        nguoi_giu: str | None = None
        for e in theo_ho_so[hs.ma]:
            c = canh.get((e["from_state"], e["to_state"], e["actor"] in he_thong))
            noi = f"hồ sơ {hs.ma}, {e['from_state']} → {e['to_state']}"
            if c is None:
                loi.append(f"{noi}: không có cạnh này trong bộ quy tắc")
                continue
            if e["from_state"] != hien_tai:
                loi.append(f"{noi}: hồ sơ đang ở {hien_tai}")
            if bo.trang_thai[hien_tai]["ket_thuc"]:
                loi.append(f"{noi}: đi tiếp sau trạng thái kết thúc")
            if RB_VE_CHO_CU in c.rang_buoc and e["to_state"] != truoc:
                loi.append(f"{noi}: không về đúng chỗ đã hỏi ({truoc})")
            dung_tac_nhan = TAC_NHAN_HAN_CHO if c.tu_di_sau_gio else TAC_NHAN_HE_THONG
            if c.he_thong and e["actor"] != dung_tac_nhan:
                loi.append(f"{noi}: cạnh hệ thống đi bằng nhầm tác nhân hệ thống")
            if e["timestamp"] < luc:
                loi.append(f"{noi}: thời điểm đi lùi")

            thay_doi = json.loads(e["changes"]) if e["changes"] else {}
            # Hai ràng buộc của #127: sửa nội dung phải đổi một thứ gì đó, và tự nhận chỉ
            # khi hồ sơ chưa ai giữ, người được giao là chính người bấm
            if RB_SUA_NOI_DUNG in c.rang_buoc and not thay_doi:
                loi.append(f"{noi}: sửa nội dung mà không đổi gì")
            if RB_TU_NHAN in c.rang_buoc:
                if nguoi_giu:
                    loi.append(f"{noi}: tự nhận hồ sơ đã có {nguoi_giu} giữ")
                if thay_doi.get("assignee_id", {}).get("to") != e["actor"]:
                    loi.append(f"{noi}: tự nhận mà người được giao không phải người bấm")
            if "assignee_id" in thay_doi:
                nguoi_giu = thay_doi["assignee_id"]["to"]

            if e["from_state"] != e["to_state"]:
                truoc = hien_tai
            hien_tai, luc = e["to_state"], e["timestamp"]
        if hien_tai != hs.trang_thai:
            loi.append(f"hồ sơ {hs.ma}: nhật ký dừng ở {hien_tai}, hồ sơ ghi {hs.trang_thai}")
    return loi


def in_thong_ke(bo: BoSinh, ho_so: list[HoSo], su_kien: list[dict]) -> None:
    ket_thuc = {m for m, s in bo.trang_thai.items() if s["ket_thuc"]}
    dem_cuoi = Counter(hs.trang_thai for hs in ho_so)
    theo_ho_so: dict[int, list[dict]] = defaultdict(list)
    for e in su_kien:
        theo_ho_so[e["case_id"]].append(e)

    quay_lui = sum(
        1 for ds in theo_ho_so.values()
        if len({e["to_state"] for e in ds}) < len(ds)
    )
    doi_phong = sum(
        1 for ds in theo_ho_so.values()
        if sum('"department_code"' in e["changes"] for e in ds) >= 2
    )
    leo_thang = sum(1 for e in su_kien if e["actor"] == TAC_NHAN_HE_THONG)
    tu_di = sum(1 for e in su_kien if e["actor"] == TAC_NHAN_HAN_CHO)
    co_dong_ho = [hs for hs in ho_so if hs.chay_giay > 0 and hs.loai]
    qua_han = sum(
        1 for hs in co_dong_ho if hs.chay_giay > bo.loai[hs.loai]["sla_gio"] * 3600
    )
    con_do = sum(1 for hs in ho_so if hs.trang_thai not in ket_thuc)

    print(f"  hồ sơ                       : {len(ho_so)}")
    print(f"  sự kiện                     : {len(su_kien)} "
          f"(trung bình {len(su_kien) / max(1, len(ho_so)):.1f} mỗi hồ sơ)")
    print(f"  còn dở lúc chốt dữ liệu     : {con_do}")
    print(f"  có quay lui                 : {quay_lui}")
    print(f"  chuyển phòng từ hai lần     : {doi_phong}")
    print(f"  lần leo thang               : {leo_thang}")
    print(f"  lần tự đi khi hết hạn chờ   : {tu_di}")
    if co_dong_ho:
        print(f"  quá hạn SLA (đã chạy đồng hồ): {qua_han}/{len(co_dong_ho)} "
              f"= {100 * qua_han / len(co_dong_ho):.1f} %")
    print("  trạng thái cuối             : "
          + ", ".join(f"{m}={n}" for m, n in sorted(dem_cuoi.items())))
    cham = sum(1 for hs in ho_so if hs.cham_tran_buoc)
    if cham:
        print(f"  CẢNH BÁO: {cham} hồ sơ chạm trần {SO_BUOC_TOI_DA} bước — "
              "kịch bản cho quay lui quá nhiều")


# --- Ghi tệp --------------------------------------------------------------------


def _gio(luc: datetime | None) -> str:
    return "" if luc is None else luc.isoformat(timespec="seconds")


def ghi_tep(
    thu_muc: Path, quy_tac: dict, kich_ban: dict, ho_so: list[HoSo], su_kien: list[dict]
) -> None:
    thu_muc.mkdir(parents=True, exist_ok=True)

    with open(thu_muc / "event_log.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COT_NHAT_KY, lineterminator="\n")
        w.writeheader()
        for so, e in enumerate(su_kien, start=1):
            w.writerow({**e, "id": so, "timestamp": _gio(e["timestamp"])})

    with open(thu_muc / "requests.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COT_HO_SO, lineterminator="\n")
        w.writeheader()
        for hs in ho_so:
            w.writerow({
                "id": hs.ma,
                "current_state": hs.trang_thai,
                "requester_id": hs.nguoi_gui,
                "request_type_code": hs.loai or "",
                "department_code": hs.phong or "",
                "priority_code": hs.uu_tien or "",
                "assignee_id": hs.nguoi_xu_ly or "",
                "created_at": _gio(hs.tao_luc),
                "sla_running_seconds": int(hs.chay_giay),
                "sla_paused_seconds": int(hs.dung_giay),
                "sla_segment_since": _gio(hs.doan_mo_tu),
            })

    # Ghi lại đúng bộ quy tắc và kịch bản đã dùng, để kết quả khảo sát dựng lại được
    for ten, noi_dung in (("quy_tac.json", quy_tac), ("kich_ban.json", kich_ban)):
        with open(thu_muc / ten, "w", encoding="utf-8", newline="\n") as f:
            json.dump(noi_dung, f, ensure_ascii=False, indent=2)
            f.write("\n")


# --- Điểm vào -----------------------------------------------------------------


def phan_tich_tham_so() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Sinh nhật ký sự kiện ảo theo bộ quy tắc đang chạy trong cụm.",
    )
    p.add_argument("--ra", required=True,
                   help="Thư mục ghi kết quả. Phải nằm NGOÀI kho mã.")
    p.add_argument("--so-ho-so", type=int, default=1000)
    p.add_argument("--so-ngay", type=int, default=180,
                   help="Khoảng thời gian hồ sơ được tạo, tính bằng ngày.")
    p.add_argument("--bat-dau", default="2026-03-01",
                   help="Ngày bắt đầu, dạng YYYY-MM-DD, theo giờ UTC.")
    p.add_argument("--hat-giong", type=int, default=20260924,
                   help="Cùng hạt giống thì cùng kết quả.")
    p.add_argument("--kich-ban",
                   help="Tệp JSON ghi đè kịch bản mặc định. Khóa dạng bảng như "
                        "trong_so, gio_cho thì ghi đè từng mục, các mục khác giữ nguyên.")
    p.add_argument("--quy-tac",
                   help="Đọc bộ quy tắc từ tệp JSON — ví dụ quy_tac.json của lần chạy "
                        "trước — thay vì từ cụm.")
    p.add_argument("--container", default="dxlab-postgres")
    p.add_argument("--nguoi-dung", default="dxlab")
    p.add_argument("--csdl", default="dxlab")
    return p.parse_args()


def main() -> int:
    # Công cụ AI và đường ống đọc kết quả qua pipe, và trên Windows pipe mặc định không
    # phải UTF-8 — in chữ có dấu sẽ làm chương trình dừng giữa chừng.
    for luong in (sys.stdout, sys.stderr):
        luong.reconfigure(encoding="utf-8")

    ts = phan_tich_tham_so()

    ra = Path(ts.ra).resolve()
    goc_kho = Path(__file__).resolve().parent.parent
    if ra == goc_kho or goc_kho in ra.parents:
        sys.exit(f"Thư mục đầu ra {ra} nằm trong kho mã. Chọn một thư mục bên ngoài, "
                 "để dữ liệu thử không bị commit nhầm.")

    if ts.quy_tac:
        quy_tac = json.loads(Path(ts.quy_tac).read_text(encoding="utf-8"))
    else:
        quy_tac = doc_quy_tac_tu_cum(ts.container, ts.nguoi_dung, ts.csdl)

    kich_ban = json.loads(json.dumps(KICH_BAN_MAC_DINH))
    if ts.kich_ban:
        # Khóa dạng bảng thì gộp từng mục: ghi đè trọng số của "cancel" không được xóa
        # mất trọng số của mọi hoạt động còn lại
        for khoa, gia_tri in json.loads(Path(ts.kich_ban).read_text(encoding="utf-8")).items():
            if isinstance(gia_tri, dict) and isinstance(kich_ban.get(khoa), dict):
                kich_ban[khoa].update(gia_tri)
            else:
                kich_ban[khoa] = gia_tri

    bat_dau = datetime.strptime(ts.bat_dau, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    bo = BoSinh(quy_tac, kich_ban, ts.hat_giong)
    ho_so, su_kien = bo.sinh(ts.so_ho_so, bat_dau, ts.so_ngay)
    loi = tu_kiem(bo, ho_so, su_kien)
    ghi_tep(ra, quy_tac, kich_ban, ho_so, su_kien)

    print(f"Bộ quy tắc {quy_tac.get('phien_ban')}: {len(bo.trang_thai)} trạng thái, "
          f"{len(bo.canh)} cạnh. Đã ghi vào {ra}")
    in_thong_ke(bo, ho_so, su_kien)

    if loi:
        print(f"\nTỰ KIỂM THẤY {len(loi)} LỖI — nhật ký này KHÔNG khớp bộ quy tắc:")
        for dong in loi[:20]:
            print(f"  {dong}")
        return 1
    print("\nTự kiểm: mọi sự kiện đi đúng một cạnh của bộ quy tắc, đúng luật quay về chỗ cũ.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
